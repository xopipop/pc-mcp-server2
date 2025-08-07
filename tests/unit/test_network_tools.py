"""
Unit tests for NetworkTools.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from src.tools import NetworkTools
from src.core import NetworkException, ValidationException


@pytest.fixture
def network_tools():
    """Create NetworkTools instance."""
    return NetworkTools()


@pytest.fixture
def mock_security():
    """Create mock security manager."""
    security = Mock()
    security.validate_input = Mock(side_effect=lambda _, value: value)
    return security


class TestNetworkTools:
    """Test NetworkTools class."""
    
    @pytest.mark.asyncio
    async def test_get_network_interfaces(self, network_tools):
        """Test getting network interfaces."""
        interfaces = await network_tools.get_network_interfaces()
        
        assert isinstance(interfaces, list)
        assert len(interfaces) > 0
        
        # Check first interface
        interface = interfaces[0]
        assert 'name' in interface
        assert 'is_up' in interface
        assert 'addresses' in interface
        assert isinstance(interface['addresses'], list)
    
    @pytest.mark.asyncio
    async def test_get_network_stats(self, network_tools):
        """Test getting network statistics."""
        stats = await network_tools.get_network_stats()
        
        assert isinstance(stats, dict)
        assert 'global' in stats
        assert 'per_interface' in stats
        assert 'connections' in stats
        assert 'timestamp' in stats
        
        # Check global stats
        global_stats = stats['global']
        assert 'bytes_sent' in global_stats
        assert 'bytes_recv' in global_stats
        assert 'packets_sent' in global_stats
        assert 'packets_recv' in global_stats
    
    @pytest.mark.asyncio
    async def test_ping_host_localhost(self, network_tools):
        """Test pinging localhost."""
        result = await network_tools.ping_host('localhost', count=2)
        
        assert result['success'] is True
        assert result['host'] == 'localhost'
        assert result['count'] == 2
        assert 'statistics' in result
        
        stats = result['statistics']
        assert stats['packets_sent'] == 2
        assert stats['packet_loss'] < 100  # Should have some success
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self, network_tools):
        """Test successful TCP connection test."""
        # Test connection to a common port
        result = await network_tools.test_connection('127.0.0.1', 80, timeout=2)
        
        assert isinstance(result, dict)
        assert 'host' in result
        assert 'port' in result
        assert 'success' in result
        assert 'duration_ms' in result
    
    @pytest.mark.asyncio
    async def test_test_connection_blocked_port(self, network_tools):
        """Test connection to blocked port."""
        # Mock config to block port 25
        with patch.object(network_tools, 'config') as mock_config:
            mock_config.get.return_value = [25]  # blocked_ports
            
            with pytest.raises(NetworkException) as exc_info:
                await network_tools.test_connection('localhost', 25)
            
            assert "blocked by policy" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_active_connections(self, network_tools):
        """Test getting active connections."""
        # Test without filters
        connections = await network_tools.get_active_connections()
        
        assert isinstance(connections, list)
        
        if connections:  # May be empty on some systems
            conn = connections[0]
            assert 'type' in conn
            assert 'status' in conn
            assert 'family' in conn
    
    @pytest.mark.asyncio
    async def test_get_active_connections_with_filters(self, network_tools):
        """Test getting active connections with filters."""
        filters = {
            'type': 'tcp',
            'status': 'ESTABLISHED'
        }
        
        connections = await network_tools.get_active_connections(filters)
        
        assert isinstance(connections, list)
        
        # All connections should match filters
        for conn in connections:
            if conn['type'] == 'SOCK_STREAM':  # TCP
                assert conn.get('status') == 'ESTABLISHED'
    
    @pytest.mark.asyncio
    async def test_get_dns_info(self, network_tools):
        """Test getting DNS information."""
        result = await network_tools.get_dns_info('google.com')
        
        assert result['success'] is True
        assert result['domain'] == 'google.com'
        assert 'addresses' in result
        assert isinstance(result['addresses'], list)
        assert len(result['addresses']) > 0
    
    @pytest.mark.asyncio
    async def test_get_dns_info_invalid_domain(self, network_tools):
        """Test DNS lookup for invalid domain."""
        result = await network_tools.get_dns_info('thisisnotavaliddomain123456.com')
        
        assert 'error' in result
        assert result.get('success') is False
    
    @pytest.mark.asyncio
    async def test_port_scan(self, network_tools):
        """Test port scanning."""
        # Scan common ports on localhost
        ports = [80, 443, 22]
        result = await network_tools.port_scan('localhost', ports, timeout=0.5)
        
        assert result['host'] == 'localhost'
        assert 'ports' in result
        assert 'open_ports' in result
        assert 'closed_ports' in result
        assert 'scan_start' in result
        assert 'scan_end' in result
        
        # Check that we scanned all requested ports
        assert len(result['ports']) == len(ports)
    
    @pytest.mark.asyncio
    async def test_port_scan_too_many_ports(self, network_tools, mock_security):
        """Test port scan with too many ports."""
        network_tools.security = mock_security
        
        # Try to scan more than 100 ports
        ports = list(range(1, 102))
        
        with pytest.raises(ValidationException) as exc_info:
            await network_tools.port_scan('localhost', ports)
        
        assert "Too many ports" in str(exc_info.value)
    
    def test_identify_service(self, network_tools):
        """Test service identification by port."""
        assert network_tools._identify_service(22) == 'SSH'
        assert network_tools._identify_service(80) == 'HTTP'
        assert network_tools._identify_service(443) == 'HTTPS'
        assert network_tools._identify_service(3389) == 'RDP'
        assert network_tools._identify_service(9999) is None  # Unknown port