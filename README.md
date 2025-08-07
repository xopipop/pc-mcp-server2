# PC Control MCP Server v2.0

A secure and powerful PC Control MCP (Model Context Protocol) Server that provides comprehensive system control capabilities through a standardized interface.

## 🚀 Features

### System Information
- **Hardware Info**: CPU, memory, disk, network interfaces
- **OS Details**: Version, platform, distribution info
- **Real-time Metrics**: CPU usage, memory usage, disk I/O
- **Environment Variables**: With sensitive data masking
- **System Uptime**: Boot time and uptime statistics

### Process Management
- **List Processes**: With filtering and sorting capabilities
- **Process Control**: Start, stop, suspend, resume processes
- **Resource Monitoring**: CPU, memory, I/O usage per process
- **Process Search**: Find processes by name or attributes
- **Priority Management**: Adjust process priorities

### File Operations
- **File Management**: Read, write, copy, move, delete files
- **Directory Operations**: List, create, search directories
- **Advanced Search**: Glob and regex pattern matching
- **Metadata Preservation**: Permissions, timestamps, ownership
- **Disk Usage**: Monitor disk space and file sizes

### Security Features
- **Path Validation**: Prevent path traversal attacks
- **Input Sanitization**: Command and path validation
- **Access Control**: Configurable allowed/blocked paths
- **Audit Logging**: Track all operations
- **Rate Limiting**: Prevent abuse

## 📋 Requirements

- Python 3.8 or higher
- Windows, Linux, or macOS
- Administrator/root privileges for some operations

## 🛠️ Installation

### ⚠️ Known Issue: ImportError with MCP

If you encounter:
```
ImportError: cannot import name 'stdio_transport' from 'mcp.server'
```

This has been fixed in the code. The import in `main.py` has been updated from:
```python
from mcp.server import Server, stdio_transport
```
to:
```python
from mcp.server import Server
from mcp.server.stdio import stdio_transport
```

### Using pip
```bash
pip install -r requirements.txt
python setup.py install
```

### Using virtual environment (recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 🔧 Configuration

The server uses YAML configuration files located in the `config/` directory:

- `default.yaml`: Main configuration
- `security.yaml`: Security policies and rules

### Basic Configuration
```yaml
server:
  name: "pc-control-mcp"
  version: "2.0.0"
  log_level: "INFO"
  
security:
  enabled: true
  authentication:
    type: "none"  # none, basic, token
```

### Security Configuration
Configure allowed/blocked operations:
```yaml
file_operations:
  blocked_paths:
    - "/etc"
    - "C:\\Windows\\System32"
  blocked_extensions: [".exe", ".dll", ".sys"]
  
process_management:
  blocked_processes: ["systemd", "init", "kernel"]
```

## 🚀 Usage

### Start the Server
```bash
python main.py
```

### Connect with MCP Client
The server uses stdio transport. Configure your MCP client to connect:

```json
{
  "mcpServers": {
    "pc-control": {
      "command": "python",
      "args": ["path/to/main.py"],
      "env": {}
    }
  }
}
```

## 📚 Available Tools

### System Information Tools
- `get_system_info` - Get comprehensive system information
- `get_hardware_info` - Get hardware details
- `get_os_info` - Get operating system information
- `get_environment_variables` - List environment variables
- `get_system_uptime` - Get system uptime
- `execute_command` - Execute system commands

### Process Management Tools
- `list_processes` - List running processes
- `get_process_info` - Get detailed process information
- `kill_process` - Terminate a process
- `start_process` - Start a new process
- `suspend_process` - Suspend a process
- `resume_process` - Resume a suspended process
- `get_process_resources` - Get process resource usage
- `find_processes_by_name` - Find processes by name

### File Operation Tools
- `read_file` - Read file contents
- `write_file` - Write content to file
- `delete_file` - Delete a file
- `copy_file` - Copy a file
- `move_file` - Move a file
- `list_directory` - List directory contents
- `create_directory` - Create a directory
- `get_file_info` - Get file metadata
- `search_files` - Search for files
- `get_disk_usage` - Get disk usage information

## 🔒 Security

### Access Control
- Path-based access control for file operations
- Process whitelist/blacklist
- Command validation and sanitization

### Audit Logging
All operations are logged with:
- Timestamp
- Operation type
- User/session info
- Operation result
- Error details (if any)

### Best Practices
1. Run with minimal required privileges
2. Configure strict access controls
3. Enable audit logging
4. Use authentication in production
5. Regularly review audit logs

## 🧪 Testing

Run the test suite:
```bash
pytest tests/
```

With coverage:
```bash
pytest --cov=src tests/
```

## 📈 Performance

- Asynchronous operations for better performance
- Efficient file streaming for large files
- Process caching to reduce system calls
- Configurable timeouts and limits

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This server provides powerful system control capabilities. Use with caution and ensure proper security measures are in place. The authors are not responsible for any damage or data loss resulting from the use of this software.

## 📞 Support

- GitHub Issues: [Report bugs or request features]
- Documentation: See the `docs/` directory
- Examples: Check the `examples/` directory

## 🔄 Changelog

### v2.0.0 (2024)
- Complete rewrite with modular architecture
- Enhanced security features
- Comprehensive tool coverage
- Improved error handling
- Better logging and monitoring

### v1.0.0 (Initial Release)
- Basic system control functionality
- Simple file operations
- Process management