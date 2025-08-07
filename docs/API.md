# PC Control MCP Server API Documentation

## Overview

The PC Control MCP Server provides a comprehensive set of tools for system management through the Model Context Protocol (MCP). All tools follow consistent patterns for input/output and error handling.

## Common Response Format

All tools return JSON responses with the following structure:

```json
{
  "success": true,
  "data": {
    // Tool-specific data
  },
  "error": null,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## System Tools

### get_system_info

Get comprehensive system information.

**Parameters:**
- `info_type` (string, optional): Type of information to retrieve
  - `all`: All system information (default)
  - `basic`: Basic system info only
  - `cpu`: CPU information
  - `memory`: Memory information
  - `disk`: Disk information
  - `network`: Network information

**Response:**
```json
{
  "system": {
    "hostname": "pc-name",
    "platform": "Windows",
    "version": "10.0.19044",
    "architecture": "x86_64"
  },
  "cpu": {
    "model": "Intel Core i7-9700K",
    "cores": 8,
    "threads": 8,
    "frequency": 3600
  },
  "memory": {
    "total": 17179869184,
    "available": 8589934592,
    "percent": 50.0
  }
}
```

### execute_command

Execute a system command with security validation.

**Parameters:**
- `command` (string, required): Command to execute
- `shell` (boolean, default: true): Use shell execution
- `timeout` (integer, optional): Command timeout in seconds
- `working_directory` (string, optional): Working directory

**Response:**
```json
{
  "command": "echo hello",
  "exit_code": 0,
  "stdout": "hello\n",
  "stderr": "",
  "duration": 0.05
}
```

## Process Tools

### list_processes

List running processes with optional filters.

**Parameters:**
- `filters` (object, optional):
  - `name` (string): Filter by process name
  - `user` (string): Filter by username
  - `status` (string): Filter by status
  - `min_cpu` (float): Minimum CPU usage
  - `min_memory` (float): Minimum memory usage
  - `sort_by` (string): Sort field
  - `limit` (integer): Maximum results

**Response:**
```json
{
  "processes": [
    {
      "pid": 1234,
      "name": "chrome.exe",
      "username": "user",
      "cpu_percent": 2.5,
      "memory_percent": 3.2,
      "status": "running",
      "create_time": 1704067200
    }
  ],
  "total": 150,
  "filtered": 10
}
```

### get_process_info

Get detailed information about a specific process.

**Parameters:**
- `pid` (integer, required): Process ID

**Response:**
```json
{
  "pid": 1234,
  "name": "chrome.exe",
  "exe": "C:\\Program Files\\Google\\Chrome\\chrome.exe",
  "cmdline": ["chrome.exe", "--flag"],
  "create_time": 1704067200,
  "cpu": {
    "percent": 2.5,
    "times": {
      "user": 100.5,
      "system": 50.2
    }
  },
  "memory": {
    "rss": 104857600,
    "vms": 209715200,
    "percent": 3.2
  }
}
```

### kill_process

Terminate a process.

**Parameters:**
- `pid` (integer, required): Process ID
- `force` (boolean, default: false): Force kill
- `timeout` (integer, default: 30): Timeout in seconds

**Response:**
```json
{
  "pid": 1234,
  "name": "app.exe",
  "action": "terminated",
  "success": true
}
```

## File Tools

### read_file

Read file contents with size limits.

**Parameters:**
- `path` (string, required): File path
- `encoding` (string, default: "utf-8"): File encoding
- `max_size` (integer, optional): Maximum file size

**Response:**
```json
{
  "path": "/path/to/file.txt",
  "content": "File contents...",
  "size": 1024,
  "encoding": "utf-8"
}
```

### write_file

Write content to a file.

**Parameters:**
- `path` (string, required): File path
- `content` (string, required): Content to write
- `encoding` (string, default: "utf-8"): File encoding
- `create_dirs` (boolean, default: false): Create parent directories

**Response:**
```json
{
  "path": "/path/to/file.txt",
  "size": 1024,
  "action": "created",
  "success": true
}
```

### list_directory

List directory contents.

**Parameters:**
- `path` (string, required): Directory path
- `recursive` (boolean, default: false): List recursively
- `include_hidden` (boolean, default: false): Include hidden files
- `pattern` (string, optional): Filter pattern

**Response:**
```json
{
  "path": "/directory",
  "entries": [
    {
      "name": "file.txt",
      "type": "file",
      "size": 1024,
      "modified": "2024-01-01T00:00:00Z",
      "permissions": "rw-r--r--"
    }
  ],
  "total_size": 10240,
  "file_count": 5,
  "dir_count": 2
}
```

## Network Tools

### get_network_interfaces

Get all network interfaces.

**Parameters:**
- `include_stats` (boolean, default: true): Include interface statistics

**Response:**
```json
{
  "interfaces": [
    {
      "name": "eth0",
      "is_up": true,
      "speed": 1000,
      "mtu": 1500,
      "addresses": [
        {
          "family": "AF_INET",
          "address": "192.168.1.100",
          "netmask": "255.255.255.0"
        }
      ],
      "statistics": {
        "bytes_sent": 1048576,
        "bytes_recv": 2097152,
        "packets_sent": 1000,
        "packets_recv": 2000
      }
    }
  ]
}
```

### ping_host

Ping a host to test connectivity.

**Parameters:**
- `host` (string, required): Host to ping
- `count` (integer, default: 4): Number of pings
- `timeout` (integer, default: 5): Timeout per ping
- `packet_size` (integer, default: 32): Packet size

**Response:**
```json
{
  "host": "google.com",
  "ip_address": "142.250.185.78",
  "success": true,
  "statistics": {
    "packets_sent": 4,
    "packets_received": 4,
    "packet_loss": 0.0,
    "min_ms": 10.5,
    "avg_ms": 15.2,
    "max_ms": 20.1
  }
}
```

### port_scan

Scan ports on a host.

**Parameters:**
- `host` (string, required): Host to scan
- `ports` (array, required): List of ports to scan
- `timeout` (float, default: 1.0): Timeout per port

**Response:**
```json
{
  "host": "localhost",
  "ip_address": "127.0.0.1",
  "ports": {
    "80": {
      "state": "open",
      "service": "HTTP"
    },
    "443": {
      "state": "closed"
    }
  },
  "open_ports": [80],
  "closed_ports": [443]
}
```

## Service Tools

### list_services

List system services.

**Parameters:**
- `include_drivers` (boolean, default: false): Include driver services (Windows)

**Response:**
```json
{
  "services": [
    {
      "name": "nginx",
      "display_name": "Nginx Web Server",
      "status": "running",
      "startup_type": "automatic",
      "pid": 1234
    }
  ]
}
```

### control_service

Control a system service.

**Parameters:**
- `service_name` (string, required): Service name
- `action` (string, required): Action to perform
  - `start`: Start the service
  - `stop`: Stop the service
  - `restart`: Restart the service

**Response:**
```json
{
  "service": "nginx",
  "action": "restart",
  "success": true,
  "status": "running"
}
```

## Registry Tools (Windows Only)

### read_registry

Read a registry value.

**Parameters:**
- `key_path` (string, required): Registry key path
- `value_name` (string, required): Value name

**Response:**
```json
{
  "key": "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion",
  "name": "ProgramFilesDir",
  "value": "C:\\Program Files",
  "type": "REG_SZ"
}
```

### write_registry

Write a registry value.

**Parameters:**
- `key_path` (string, required): Registry key path
- `value_name` (string, required): Value name
- `value` (any, required): Value to write
- `value_type` (string, default: "REG_SZ"): Registry value type

**Response:**
```json
{
  "key": "HKCU\\Software\\MyApp",
  "name": "Setting",
  "type": "REG_DWORD",
  "action": "write",
  "success": true
}
```

## GUI Automation Tools

### move_mouse

Move mouse to specified position.

**Parameters:**
- `x` (integer, required): X coordinate
- `y` (integer, required): Y coordinate
- `duration` (float, default: 0): Movement duration
- `relative` (boolean, default: false): Relative movement

**Response:**
```json
{
  "action": "move_mouse",
  "target": {"x": 500, "y": 300},
  "final": {"x": 500, "y": 300},
  "success": true
}
```

### click_mouse

Click mouse at position.

**Parameters:**
- `x` (integer, optional): X coordinate
- `y` (integer, optional): Y coordinate
- `button` (string, default: "left"): Mouse button
- `clicks` (integer, default: 1): Number of clicks

**Response:**
```json
{
  "action": "click_mouse",
  "position": {"x": 500, "y": 300},
  "button": "left",
  "success": true
}
```

### take_screenshot

Take a screenshot.

**Parameters:**
- `region` (array, optional): Region [x, y, width, height]
- `save_path` (string, optional): Path to save file

**Response:**
```json
{
  "action": "take_screenshot",
  "size": {"width": 1920, "height": 1080},
  "saved_to": "/path/to/screenshot.png",
  "success": true
}
```

## Error Handling

All tools use consistent error responses:

```json
{
  "success": false,
  "error": {
    "type": "ValidationException",
    "message": "Invalid path: contains parent directory reference",
    "code": "INVALID_PATH"
  }
}
```

### Error Types

- `SecurityException`: Security policy violation
- `ValidationException`: Invalid input parameters
- `SystemException`: System operation failed
- `NetworkException`: Network operation failed
- `FileOperationException`: File operation failed
- `ProcessException`: Process operation failed
- `ServiceException`: Service operation failed
- `RegistryException`: Registry operation failed
- `AutomationException`: GUI automation failed
- `RateLimitException`: Rate limit exceeded
- `TimeoutException`: Operation timed out

## Rate Limiting

API calls are subject to rate limiting:

- Default: 100 requests per minute
- Burst: 20 requests
- Per-user limits configurable

Rate limit headers:
- `X-RateLimit-Limit`: Request limit
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset timestamp