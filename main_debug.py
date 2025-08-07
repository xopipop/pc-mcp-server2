#!/usr/bin/env python3
"""
PC Control MCP Server - Debug version with enhanced error handling.
"""

import asyncio
import sys
import os
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

print("DEBUG: main_debug.py starting...")
print(f"DEBUG: Python {sys.version}")
print(f"DEBUG: Platform: {sys.platform}")
print(f"DEBUG: Working directory: {os.getcwd()}")
print(f"DEBUG: sys.stdin: {sys.stdin}")
print(f"DEBUG: sys.stdout: {sys.stdout}")
print(f"DEBUG: sys.stderr: {sys.stderr}")

# Import with error handling
try:
    from mcp.server import Server
    print("✅ Server imported")
except Exception as e:
    print(f"❌ Failed to import Server: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    from mcp.server.stdio import stdio_server
    print("✅ stdio_server imported")
except Exception as e:
    print(f"❌ Failed to import stdio_server: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    from mcp.server.models import InitializationOptions
    print("✅ InitializationOptions imported")
except Exception as e:
    print(f"❌ Failed to import InitializationOptions: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    from mcp.types import Tool, TextContent
    print("✅ MCP types imported")
except Exception as e:
    print(f"❌ Failed to import MCP types: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    from src import setup_logging, __version__
    print(f"✅ Local modules imported, version: {__version__}")
except Exception as e:
    print(f"❌ Failed to import local modules: {e}")
    traceback.print_exc()
    sys.exit(1)

# Setup logging
print("\nDEBUG: Setting up logging...")
setup_logging()

# Import logger after setup
from src import StructuredLogger
log = StructuredLogger(__name__)


class MinimalServer:
    """Minimal MCP Server for testing."""
    
    def __init__(self):
        print("DEBUG: MinimalServer.__init__()")
        self.server = Server("pc-control-debug")
        print("DEBUG: Server instance created")
        
        # Register minimal handlers
        self._register_handlers()
        print("DEBUG: Handlers registered")
        
    def _register_handlers(self):
        """Register minimal handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            print("DEBUG: list_tools() called")
            return [
                Tool(
                    name="test_tool",
                    description="A test tool",
                    inputSchema={"type": "object", "properties": {}}
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            print(f"DEBUG: call_tool() called - name: {name}, arguments: {arguments}")
            return [TextContent(type="text", text=f"Test response for {name}")]
    
    async def run(self):
        """Run the server with detailed error handling."""
        print("\nDEBUG: MinimalServer.run() called")
        
        # Check if we're in a proper terminal environment
        if not sys.stdin or not sys.stdout:
            print("WARNING: No stdin/stdout available")
            
        try:
            print("DEBUG: Attempting to create stdio_server...")
            
            # Add timeout to detect hanging
            async def create_stdio_with_timeout():
                print("DEBUG: Entering stdio_server context...")
                async with stdio_server() as (read_stream, write_stream):
                    print(f"✅ stdio_server created successfully")
                    print(f"   read_stream: {type(read_stream)}")
                    print(f"   write_stream: {type(write_stream)}")
                    
                    # Run the server
                    print("DEBUG: Starting server.run()...")
                    await self.server.run(
                        read_stream,
                        write_stream,
                        InitializationOptions()
                    )
            
            # Try with timeout if available (Python 3.11+)
            if hasattr(asyncio, 'timeout'):
                try:
                    async with asyncio.timeout(5):
                        await create_stdio_with_timeout()
                except asyncio.TimeoutError:
                    print("❌ Timeout creating stdio_server (5 seconds)")
                    raise
            else:
                # No timeout available, run directly
                print("DEBUG: Running without timeout (Python < 3.11)")
                await create_stdio_with_timeout()
            
        except Exception as e:
            print(f"\n❌ Error in run(): {type(e).__name__}: {e}")
            
            # Print detailed exception info
            import sys
            exc_type, exc_value, exc_tb = sys.exc_info()
            
            print("\nDetailed traceback:")
            for frame in traceback.extract_tb(exc_tb):
                print(f"  File: {frame.filename}")
                print(f"  Line {frame.lineno} in {frame.name}")
                print(f"  Code: {frame.line}")
            
            print(f"\nException type: {exc_type}")
            print(f"Exception value: {exc_value}")
            
            # Try to understand the error better
            if "TaskGroup" in str(e):
                print("\n💡 TaskGroup error detected. This might be due to:")
                print("   1. Incompatible asyncio/Python version")
                print("   2. MCP library expecting different async context")
                print("   3. Missing or incorrect stdio setup")
            
            traceback.print_exc()
            raise


async def main():
    """Main entry point with enhanced error handling."""
    print("\nDEBUG: main() called")
    
    try:
        server = MinimalServer()
        print("✅ MinimalServer instance created")
        
        await server.run()
        
    except KeyboardInterrupt:
        print("\n⏹️  Server stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {type(e).__name__}: {e}")
        traceback.print_exc()
        
        # Additional diagnostics
        print("\n=== Diagnostics ===")
        print(f"Python version: {sys.version}")
        print(f"asyncio version: {asyncio.__version__ if hasattr(asyncio, '__version__') else 'Unknown'}")
        
        # Check if we have TaskGroup support
        if hasattr(asyncio, 'TaskGroup'):
            print("✅ asyncio.TaskGroup is available")
        else:
            print("❌ asyncio.TaskGroup is NOT available (requires Python 3.11+)")
        
        sys.exit(1)


if __name__ == "__main__":
    print("\n=== Starting PC Control MCP Debug Server ===")
    
    # Run with explicit event loop policy
    if sys.platform == "win32":
        print("DEBUG: Setting Windows event loop policy")
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Failed to run async main: {type(e).__name__}: {e}")
        traceback.print_exc()