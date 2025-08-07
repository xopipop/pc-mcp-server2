#!/usr/bin/env python3
"""
Run PC Control MCP Server.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import and run main
from main import main
import asyncio

if __name__ == "__main__":
    print("Starting PC Control MCP Server v2.0...")
    print("=" * 50)
    print("Security: ENABLED")
    print("Logging: ~/.pc_control_mcp/logs/")
    print("Config: config/default.yaml")
    print("=" * 50)
    print("Press Ctrl+C to stop the server")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped.")
        sys.exit(0)