#!/usr/bin/env python3
"""
Проверка версии и состояния MCP.
"""

import sys
import importlib.metadata

print("=== MCP Version Check ===\n")

# Check Python version
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}\n")

# Check MCP installation
try:
    import mcp
    print(f"✅ MCP imported successfully")
    print(f"   MCP location: {mcp.__file__}")
    
    # Try to get version
    try:
        mcp_version = importlib.metadata.version('mcp')
        print(f"   MCP version: {mcp_version}")
    except:
        print(f"   MCP version: Unable to determine")
    
    # Check submodules
    try:
        from mcp.server import Server
        print(f"✅ mcp.server.Server imported")
    except Exception as e:
        print(f"❌ mcp.server.Server import failed: {e}")
    
    try:
        from mcp.server.stdio import stdio_server
        print(f"✅ mcp.server.stdio.stdio_server imported")
    except Exception as e:
        print(f"❌ mcp.server.stdio.stdio_server import failed: {e}")
    
    try:
        from mcp.server.models import InitializationOptions
        print(f"✅ mcp.server.models.InitializationOptions imported")
    except Exception as e:
        print(f"❌ mcp.server.models.InitializationOptions import failed: {e}")
        
except Exception as e:
    print(f"❌ MCP import failed: {e}")
    
print("\n=== Other Dependencies ===\n")

# Check other key dependencies
deps = ['psutil', 'pydantic', 'asyncio-mqtt', 'aiofiles', 'pyyaml']

for dep in deps:
    try:
        module = __import__(dep.replace('-', '_'))
        version = "Unknown"
        try:
            version = importlib.metadata.version(dep)
        except:
            if hasattr(module, '__version__'):
                version = module.__version__
        print(f"✅ {dep}: {version}")
    except Exception as e:
        print(f"❌ {dep}: Not installed or import failed")