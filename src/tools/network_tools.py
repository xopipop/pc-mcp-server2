"""
Network operation tools for PC Control MCP Server.
"""

import socket
import asyncio
import struct
import platform
import subprocess
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import psutil
import aiohttp

from ..core import (
    StructuredLogger,
    SecurityManager,
    Operation,
    NetworkException,
    TimeoutException,
    ValidationException,
    get_config
)
from ..utils.platform_utils import is_windows, is_linux, is_macos

log = StructuredLogger(__name__)


class NetworkInfo:
    """Network information container."""
    
    def __init__(self, interface_name: str):
        self.interface_name = interface_name
        self._stats = None
        self._addrs = None
    
    def get_info(self) -> Dict[str, Any]:
        """Get network interface information."""
        try:
            # Get interface stats
            if self.interface_name in psutil.net_if_stats():
                self._stats = psutil.net_if_stats()[self.interface_name]
            
            # Get interface addresses
            if self.interface_name in psutil.net_if_addrs():
                self._addrs = psutil.net_if_addrs()[self.interface_name]
            
            info = {
                'name': self.interface_name,
                'is_up': self._stats.isup if self._stats else False,
                'speed': self._stats.speed if self._stats else None,
                'mtu': self._stats.mtu if self._stats else None,
                'addresses': self._get_addresses()
            }
            
            # Get additional info if available
            if self._stats and hasattr(self._stats, 'duplex'):
                info['duplex'] = self._stats.duplex.name if self._stats.duplex else None
            
            return info
            
        except Exception as e:
            raise NetworkException(f"Failed to get network interface info: {str(e)}")
    
    def _get_addresses(self) -> List[Dict[str, Any]]:
        """Get interface addresses."""
        addresses = []
        
        if not self._addrs:
            return addresses
        
        for addr in self._addrs:
            addr_info = {
                'family': addr.family.name,
                'address': addr.address
            }
            
            if addr.netmask:
                addr_info['netmask'] = addr.netmask
            if addr.broadcast:
                addr_info['broadcast'] = addr.broadcast
            if addr.ptp:
                addr_info['ptp'] = addr.ptp
            
            addresses.append(addr_info)
        
        return addresses


class NetworkTools:
    """Network operation tools."""
    
    def __init__(self, security_manager: Optional[SecurityManager] = None):
        self.security = security_manager
        self.config = get_config()
    
    async def get_network_interfaces(self, include_stats: bool = True) -> List[Dict[str, Any]]:
        """Get all network interfaces.
        
        Args:
            include_stats: Include interface statistics
            
        Returns:
            List of network interface information
        """
        try:
            interfaces = []
            
            # Get all interface names
            for interface_name in psutil.net_if_addrs().keys():
                try:
                    net_info = NetworkInfo(interface_name)
                    interface_data = net_info.get_info()
                    
                    if include_stats:
                        # Add I/O statistics
                        io_counters = psutil.net_io_counters(pernic=True)
                        if interface_name in io_counters:
                            io = io_counters[interface_name]
                            interface_data['statistics'] = {
                                'bytes_sent': io.bytes_sent,
                                'bytes_recv': io.bytes_recv,
                                'packets_sent': io.packets_sent,
                                'packets_recv': io.packets_recv,
                                'errin': io.errin,
                                'errout': io.errout,
                                'dropin': io.dropin,
                                'dropout': io.dropout
                            }
                    
                    interfaces.append(interface_data)
                    
                except Exception as e:
                    log.warning(f"Failed to get info for interface {interface_name}: {e}")
                    continue
            
            # Sort interfaces by name
            interfaces.sort(key=lambda x: x['name'])
            
            return interfaces
            
        except Exception as e:
            log.error(f"Failed to get network interfaces: {e}", exception=e)
            raise NetworkException(f"Failed to get network interfaces: {str(e)}")
    
    async def get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics.
        
        Returns:
            Dictionary with network statistics
        """
        try:
            # Get global network I/O counters
            global_io = psutil.net_io_counters()
            
            # Get per-interface counters
            per_interface = {}
            for name, counters in psutil.net_io_counters(pernic=True).items():
                per_interface[name] = {
                    'bytes_sent': counters.bytes_sent,
                    'bytes_recv': counters.bytes_recv,
                    'packets_sent': counters.packets_sent,
                    'packets_recv': counters.packets_recv,
                    'errors_in': counters.errin,
                    'errors_out': counters.errout,
                    'drops_in': counters.dropin,
                    'drops_out': counters.dropout
                }
            
            # Get connection statistics
            connections = psutil.net_connections()
            conn_stats = {
                'total': len(connections),
                'tcp': len([c for c in connections if c.type.name == 'SOCK_STREAM']),
                'udp': len([c for c in connections if c.type.name == 'SOCK_DGRAM']),
                'established': len([c for c in connections if c.status == 'ESTABLISHED']),
                'listening': len([c for c in connections if c.status == 'LISTEN'])
            }
            
            return {
                'global': {
                    'bytes_sent': global_io.bytes_sent,
                    'bytes_recv': global_io.bytes_recv,
                    'packets_sent': global_io.packets_sent,
                    'packets_recv': global_io.packets_recv,
                    'errors_in': global_io.errin,
                    'errors_out': global_io.errout,
                    'drops_in': global_io.dropin,
                    'drops_out': global_io.dropout
                },
                'per_interface': per_interface,
                'connections': conn_stats,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            log.error(f"Failed to get network stats: {e}", exception=e)
            raise NetworkException(f"Failed to get network stats: {str(e)}")
    
    async def ping_host(self, host: str, count: int = 4, 
                       timeout: int = 5, packet_size: int = 32) -> Dict[str, Any]:
        """Ping a host.
        
        Args:
            host: Host to ping (IP or hostname)
            count: Number of pings
            timeout: Timeout per ping in seconds
            packet_size: Packet size in bytes
            
        Returns:
            Dictionary with ping results
        """
        try:
            # Validate host
            if self.security:
                host = self.security.validate_input('command', host)
            
            # Resolve hostname if needed
            try:
                ip_address = socket.gethostbyname(host)
            except socket.gaierror:
                raise NetworkException(f"Cannot resolve hostname: {host}")
            
            # Build ping command based on platform
            if is_windows():
                cmd = ['ping', '-n', str(count), '-w', str(timeout * 1000), 
                       '-l', str(packet_size), host]
            else:
                cmd = ['ping', '-c', str(count), '-W', str(timeout), 
                       '-s', str(packet_size), host]
            
            # Execute ping
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Parse results
            output = stdout.decode('utf-8', errors='replace')
            
            # Extract statistics (platform-specific parsing)
            stats = self._parse_ping_output(output)
            
            return {
                'host': host,
                'ip_address': ip_address,
                'count': count,
                'packet_size': packet_size,
                'success': process.returncode == 0,
                'output': output,
                'statistics': stats
            }
            
        except Exception as e:
            log.error(f"Failed to ping host {host}: {e}", exception=e)
            raise NetworkException(f"Failed to ping host: {str(e)}")
    
    def _parse_ping_output(self, output: str) -> Dict[str, Any]:
        """Parse ping output to extract statistics."""
        stats = {
            'packets_sent': 0,
            'packets_received': 0,
            'packet_loss': 100.0,
            'min_ms': None,
            'avg_ms': None,
            'max_ms': None
        }
        
        try:
            lines = output.split('\n')
            
            if is_windows():
                # Windows ping output parsing
                for line in lines:
                    if 'Packets:' in line:
                        # Extract packet statistics
                        parts = line.split(',')
                        for part in parts:
                            if 'Sent' in part:
                                stats['packets_sent'] = int(part.split('=')[1].strip())
                            elif 'Received' in part:
                                stats['packets_received'] = int(part.split('=')[1].strip())
                            elif 'Lost' in part:
                                lost = int(part.split('=')[1].split()[0].strip())
                                if stats['packets_sent'] > 0:
                                    stats['packet_loss'] = (lost / stats['packets_sent']) * 100
                    elif 'Minimum' in line and 'Maximum' in line:
                        # Extract RTT statistics
                        parts = line.split(',')
                        for part in parts:
                            if 'Minimum' in part:
                                stats['min_ms'] = float(part.split('=')[1].replace('ms', '').strip())
                            elif 'Maximum' in part:
                                stats['max_ms'] = float(part.split('=')[1].replace('ms', '').strip())
                            elif 'Average' in part:
                                stats['avg_ms'] = float(part.split('=')[1].replace('ms', '').strip())
            else:
                # Unix-like ping output parsing
                for line in lines:
                    if 'packets transmitted' in line:
                        parts = line.split(',')
                        stats['packets_sent'] = int(parts[0].split()[0])
                        stats['packets_received'] = int(parts[1].split()[0])
                        # Calculate packet loss
                        if stats['packets_sent'] > 0:
                            stats['packet_loss'] = ((stats['packets_sent'] - stats['packets_received']) / 
                                                   stats['packets_sent']) * 100
                    elif 'min/avg/max' in line or 'round-trip' in line:
                        # Extract RTT statistics
                        if '=' in line:
                            rtt_part = line.split('=')[1].strip()
                            values = rtt_part.split('/')[0:3]
                            if len(values) >= 3:
                                stats['min_ms'] = float(values[0])
                                stats['avg_ms'] = float(values[1])
                                stats['max_ms'] = float(values[2])
        except Exception as e:
            log.warning(f"Failed to parse ping statistics: {e}")
        
        return stats
    
    async def test_connection(self, host: str, port: int, 
                            timeout: int = 5) -> Dict[str, Any]:
        """Test TCP connection to host:port.
        
        Args:
            host: Host to connect to
            port: Port number
            timeout: Connection timeout in seconds
            
        Returns:
            Dictionary with connection test results
        """
        try:
            # Validate inputs
            if self.security:
                host = self.security.validate_input('command', host)
            
            if not 1 <= port <= 65535:
                raise ValidationException(f"Invalid port number: {port}")
            
            # Check if port is blocked
            blocked_ports = self.config.get('network.blocked_ports', [])
            if port in blocked_ports:
                raise NetworkException(f"Port {port} is blocked by policy")
            
            # Resolve hostname
            try:
                ip_address = socket.gethostbyname(host)
            except socket.gaierror:
                return {
                    'host': host,
                    'port': port,
                    'success': False,
                    'error': 'Cannot resolve hostname',
                    'duration_ms': 0
                }
            
            # Test connection
            start_time = asyncio.get_event_loop().time()
            
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip_address, port),
                    timeout=timeout
                )
                
                # Connection successful
                writer.close()
                await writer.wait_closed()
                
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                
                return {
                    'host': host,
                    'ip_address': ip_address,
                    'port': port,
                    'success': True,
                    'duration_ms': round(duration_ms, 2),
                    'service': self._identify_service(port)
                }
                
            except asyncio.TimeoutError:
                return {
                    'host': host,
                    'ip_address': ip_address,
                    'port': port,
                    'success': False,
                    'error': 'Connection timeout',
                    'duration_ms': timeout * 1000
                }
            except ConnectionRefusedError:
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                return {
                    'host': host,
                    'ip_address': ip_address,
                    'port': port,
                    'success': False,
                    'error': 'Connection refused',
                    'duration_ms': round(duration_ms, 2)
                }
            except Exception as e:
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                return {
                    'host': host,
                    'ip_address': ip_address,
                    'port': port,
                    'success': False,
                    'error': str(e),
                    'duration_ms': round(duration_ms, 2)
                }
                
        except Exception as e:
            log.error(f"Failed to test connection to {host}:{port}: {e}", exception=e)
            raise NetworkException(f"Failed to test connection: {str(e)}")
    
    def _identify_service(self, port: int) -> Optional[str]:
        """Identify common service by port number."""
        common_ports = {
            20: 'FTP-DATA',
            21: 'FTP',
            22: 'SSH',
            23: 'Telnet',
            25: 'SMTP',
            53: 'DNS',
            80: 'HTTP',
            110: 'POP3',
            143: 'IMAP',
            443: 'HTTPS',
            445: 'SMB',
            3306: 'MySQL',
            3389: 'RDP',
            5432: 'PostgreSQL',
            5900: 'VNC',
            8080: 'HTTP-Proxy',
            8443: 'HTTPS-Alt'
        }
        return common_ports.get(port)
    
    async def get_active_connections(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get active network connections.
        
        Args:
            filters: Optional filters:
                    - type: Connection type (tcp, udp)
                    - status: Connection status
                    - pid: Process ID
                    - local_port: Local port
                    - remote_port: Remote port
        
        Returns:
            List of active connections
        """
        try:
            connections = []
            filters = filters or {}
            
            # Get all connections
            for conn in psutil.net_connections():
                try:
                    conn_info = {
                        'fd': conn.fd,
                        'family': conn.family.name,
                        'type': conn.type.name,
                        'status': conn.status if conn.status else 'NONE',
                        'pid': conn.pid
                    }
                    
                    # Add local address
                    if conn.laddr:
                        conn_info['local_address'] = conn.laddr.ip
                        conn_info['local_port'] = conn.laddr.port
                    
                    # Add remote address
                    if conn.raddr:
                        conn_info['remote_address'] = conn.raddr.ip
                        conn_info['remote_port'] = conn.raddr.port
                    
                    # Apply filters
                    if filters.get('type'):
                        if filters['type'].upper() == 'TCP' and conn.type.name != 'SOCK_STREAM':
                            continue
                        elif filters['type'].upper() == 'UDP' and conn.type.name != 'SOCK_DGRAM':
                            continue
                    
                    if filters.get('status') and conn_info['status'] != filters['status']:
                        continue
                    
                    if filters.get('pid') and conn_info['pid'] != filters['pid']:
                        continue
                    
                    if filters.get('local_port') and conn_info.get('local_port') != filters['local_port']:
                        continue
                    
                    if filters.get('remote_port') and conn_info.get('remote_port') != filters['remote_port']:
                        continue
                    
                    # Try to get process name
                    if conn.pid:
                        try:
                            process = psutil.Process(conn.pid)
                            conn_info['process_name'] = process.name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            conn_info['process_name'] = None
                    
                    connections.append(conn_info)
                    
                except Exception as e:
                    log.warning(f"Failed to get connection info: {e}")
                    continue
            
            # Sort by local port
            connections.sort(key=lambda x: x.get('local_port', 0))
            
            return connections
            
        except Exception as e:
            log.error(f"Failed to get active connections: {e}", exception=e)
            raise NetworkException(f"Failed to get active connections: {str(e)}")
    
    async def get_dns_info(self, domain: str) -> Dict[str, Any]:
        """Get DNS information for a domain.
        
        Args:
            domain: Domain name to lookup
            
        Returns:
            Dictionary with DNS information
        """
        try:
            # Validate domain
            if self.security:
                domain = self.security.validate_input('command', domain)
            
            dns_info = {
                'domain': domain,
                'addresses': []
            }
            
            # Get IP addresses
            try:
                # Get all IP addresses
                addr_info = socket.getaddrinfo(domain, None)
                ips = set()
                for info in addr_info:
                    ip = info[4][0]
                    ips.add(ip)
                
                dns_info['addresses'] = list(ips)
                
                # Try to get canonical name
                try:
                    dns_info['canonical_name'] = socket.getfqdn(domain)
                except Exception:
                    pass
                
                # Try reverse DNS for first IP
                if dns_info['addresses']:
                    try:
                        hostname, _, _ = socket.gethostbyaddr(dns_info['addresses'][0])
                        dns_info['reverse_dns'] = hostname
                    except Exception:
                        pass
                
            except socket.gaierror as e:
                dns_info['error'] = f"DNS lookup failed: {e}"
                dns_info['success'] = False
                return dns_info
            
            # Get additional DNS records using nslookup
            if is_windows():
                cmd = ['nslookup', domain]
            else:
                cmd = ['host', domain]
            
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, _ = await asyncio.wait_for(
                    process.communicate(),
                    timeout=10
                )
                
                output = stdout.decode('utf-8', errors='replace')
                dns_info['dns_output'] = output
                
                # Parse additional records
                dns_info['records'] = self._parse_dns_output(output)
                
            except Exception as e:
                log.warning(f"Failed to get detailed DNS info: {e}")
            
            dns_info['success'] = True
            return dns_info
            
        except Exception as e:
            log.error(f"Failed to get DNS info for {domain}: {e}", exception=e)
            raise NetworkException(f"Failed to get DNS info: {str(e)}")
    
    def _parse_dns_output(self, output: str) -> Dict[str, List[str]]:
        """Parse DNS command output."""
        records = {
            'A': [],
            'AAAA': [],
            'MX': [],
            'TXT': [],
            'NS': []
        }
        
        try:
            lines = output.split('\n')
            
            for line in lines:
                line = line.strip()
                
                # Look for IPv4 addresses
                if 'Address:' in line and '.' in line:
                    addr = line.split('Address:')[1].strip()
                    if '.' in addr and addr not in records['A']:
                        records['A'].append(addr)
                
                # Look for IPv6 addresses
                elif 'Address:' in line and ':' in line:
                    addr = line.split('Address:')[1].strip()
                    if ':' in addr and addr not in records['AAAA']:
                        records['AAAA'].append(addr)
                
                # Look for mail servers
                elif 'mail exchanger' in line.lower() or 'mx' in line.lower():
                    parts = line.split()
                    for part in parts:
                        if '.' in part and part.endswith('.'):
                            records['MX'].append(part.rstrip('.'))
                
                # Look for name servers
                elif 'name server' in line.lower() or 'ns' in line.lower():
                    parts = line.split()
                    for part in parts:
                        if '.' in part and part.endswith('.'):
                            records['NS'].append(part.rstrip('.'))
        
        except Exception as e:
            log.warning(f"Failed to parse DNS output: {e}")
        
        # Remove empty record types
        return {k: v for k, v in records.items() if v}
    
    async def port_scan(self, host: str, ports: List[int], 
                       timeout: float = 1.0) -> Dict[str, Any]:
        """Scan specific ports on a host.
        
        Args:
            host: Host to scan
            ports: List of ports to scan
            timeout: Timeout per port in seconds
            
        Returns:
            Dictionary with scan results
        """
        try:
            # Security check
            if self.security:
                host = self.security.validate_input('command', host)
                
                # Limit number of ports
                if len(ports) > 100:
                    raise ValidationException("Too many ports to scan (max 100)")
            
            # Validate ports
            for port in ports:
                if not 1 <= port <= 65535:
                    raise ValidationException(f"Invalid port number: {port}")
            
            # Resolve hostname
            try:
                ip_address = socket.gethostbyname(host)
            except socket.gaierror:
                raise NetworkException(f"Cannot resolve hostname: {host}")
            
            results = {
                'host': host,
                'ip_address': ip_address,
                'scan_start': datetime.now(timezone.utc).isoformat(),
                'ports': {},
                'open_ports': [],
                'closed_ports': [],
                'filtered_ports': []
            }
            
            # Scan ports concurrently
            tasks = []
            for port in ports:
                task = self._scan_single_port(ip_address, port, timeout)
                tasks.append(task)
            
            port_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for port, result in zip(ports, port_results):
                if isinstance(result, Exception):
                    results['ports'][port] = {
                        'state': 'error',
                        'error': str(result)
                    }
                    results['filtered_ports'].append(port)
                else:
                    results['ports'][port] = result
                    if result['state'] == 'open':
                        results['open_ports'].append(port)
                    elif result['state'] == 'closed':
                        results['closed_ports'].append(port)
                    else:
                        results['filtered_ports'].append(port)
            
            results['scan_end'] = datetime.now(timezone.utc).isoformat()
            
            return results
            
        except Exception as e:
            log.error(f"Failed to scan ports on {host}: {e}", exception=e)
            raise NetworkException(f"Failed to scan ports: {str(e)}")
    
    async def _scan_single_port(self, host: str, port: int, 
                               timeout: float) -> Dict[str, Any]:
        """Scan a single port."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )
            
            # Port is open
            writer.close()
            await writer.wait_closed()
            
            duration = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return {
                'state': 'open',
                'service': self._identify_service(port),
                'response_time_ms': round(duration, 2)
            }
            
        except asyncio.TimeoutError:
            return {
                'state': 'filtered',
                'reason': 'timeout'
            }
        except ConnectionRefusedError:
            duration = (asyncio.get_event_loop().time() - start_time) * 1000
            return {
                'state': 'closed',
                'response_time_ms': round(duration, 2)
            }
        except Exception as e:
            return {
                'state': 'filtered',
                'reason': str(e)
            }
    
    async def get_routing_table(self) -> List[Dict[str, Any]]:
        """Get system routing table.
        
        Returns:
            List of routing table entries
        """
        try:
            routes = []
            
            if is_windows():
                # Windows route command
                cmd = ['route', 'print']
            elif is_macos():
                # macOS netstat command
                cmd = ['netstat', '-rn']
            else:
                # Linux ip command
                cmd = ['ip', 'route', 'show']
            
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise NetworkException(f"Failed to get routing table: {stderr.decode()}")
            
            output = stdout.decode('utf-8', errors='replace')
            
            # Parse routing table (simplified)
            # This would need platform-specific parsing
            routes_info = {
                'raw_output': output,
                'routes': self._parse_routing_table(output),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            return routes_info
            
        except Exception as e:
            log.error(f"Failed to get routing table: {e}", exception=e)
            raise NetworkException(f"Failed to get routing table: {str(e)}")
    
    def _parse_routing_table(self, output: str) -> List[Dict[str, Any]]:
        """Parse routing table output (simplified)."""
        routes = []
        
        try:
            lines = output.split('\n')
            
            if is_linux():
                # Parse Linux ip route output
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            route = {
                                'destination': parts[0],
                                'gateway': None,
                                'interface': None
                            }
                            
                            for i, part in enumerate(parts):
                                if part == 'via' and i + 1 < len(parts):
                                    route['gateway'] = parts[i + 1]
                                elif part == 'dev' and i + 1 < len(parts):
                                    route['interface'] = parts[i + 1]
                            
                            routes.append(route)
        
        except Exception as e:
            log.warning(f"Failed to parse routing table: {e}")
        
        return routes