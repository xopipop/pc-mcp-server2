#!/usr/bin/env python3
"""
Тестовый сервер с детальной обработкой ошибок.
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

print("DEBUG: Starting test_server.py")

async def test_server():
    """Test server with detailed error handling."""
    
    print("DEBUG: Importing modules...")
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.server.models import InitializationOptions
        print("✅ MCP modules imported successfully")
    except Exception as e:
        print(f"❌ Failed to import MCP modules: {e}")
        traceback.print_exc()
        return
    
    print("\nDEBUG: Creating minimal server...")
    try:
        server = Server("test-server")
        print("✅ Server instance created")
        
        # Register a simple tool
        @server.list_tools()
        async def list_tools():
            return []
        
        @server.call_tool()
        async def call_tool(name: str, arguments: dict):
            return [{"type": "text", "text": f"Tool {name} called"}]
        
        print("✅ Tools registered")
        
    except Exception as e:
        print(f"❌ Failed to create server: {e}")
        traceback.print_exc()
        return
    
    print("\nDEBUG: Attempting to start stdio server...")
    try:
        print("Creating stdio_server context...")
        
        # Try to understand what stdio_server does
        print(f"stdio_server function: {stdio_server}")
        print(f"stdio_server module: {stdio_server.__module__}")
        
        # Try different approaches
        try:
            # Approach 1: Normal usage
            print("\nApproach 1: Normal async with...")
            async with stdio_server() as (read_stream, write_stream):
                print(f"✅ Stdio server created!")
                print(f"   read_stream: {read_stream}")
                print(f"   write_stream: {write_stream}")
                
                # Don't actually run the server, just test the setup
                print("✅ Stdio server test successful!")
                
        except Exception as e:
            print(f"❌ Approach 1 failed: {type(e).__name__}: {e}")
            traceback.print_exc()
            
            # Try approach 2
            print("\nApproach 2: Manual creation...")
            try:
                stdio_ctx = stdio_server()
                print(f"stdio_ctx type: {type(stdio_ctx)}")
                print(f"stdio_ctx: {stdio_ctx}")
                
                # Try to enter the context manually
                streams = await stdio_ctx.__aenter__()
                print(f"✅ Manual entry successful: {streams}")
                
                # Exit the context
                await stdio_ctx.__aexit__(None, None, None)
                
            except Exception as e2:
                print(f"❌ Approach 2 failed: {type(e2).__name__}: {e2}")
                traceback.print_exc()
    
    except Exception as e:
        print(f"❌ Stdio server test failed: {type(e).__name__}: {e}")
        traceback.print_exc()

async def main():
    """Main entry point."""
    try:
        await test_server()
    except Exception as e:
        print(f"\n❌ Unhandled exception: {type(e).__name__}: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("DEBUG: Running asyncio event loop...")
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Failed to run event loop: {type(e).__name__}: {e}")
        traceback.print_exc()