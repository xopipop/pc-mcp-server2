#!/usr/bin/env python3
"""Test script to demonstrate the InitializationOptions fix"""

from pydantic import BaseModel
from typing import Dict, Any, Optional

# Simulating the InitializationOptions model based on the error
class InitializationOptions(BaseModel):
    server_name: str
    server_version: str
    capabilities: Dict[str, Any]

# Test the original code that was failing
try:
    print("Testing original code (should fail):")
    options = InitializationOptions()  # This should fail
except Exception as e:
    print(f"✗ Error (as expected): {type(e).__name__}")
    print(f"  Details: {e}")

# Test the fixed code
try:
    print("\nTesting fixed code (should work):")
    options = InitializationOptions(
        server_name="pc-control-mcp",
        server_version="2.0.0",
        capabilities={
            "tools": {"list": []},
            "resources": {"list": []},
            "prompts": {"list": []}
        }
    )
    print(f"✓ Success! Created InitializationOptions:")
    print(f"  - server_name: {options.server_name}")
    print(f"  - server_version: {options.server_version}")
    print(f"  - capabilities: {options.capabilities}")
except Exception as e:
    print(f"✗ Unexpected error: {type(e).__name__}: {e}")

# Show the fix that was applied
print("\n📝 The fix applied to main.py:")
print("BEFORE:")
print("  InitializationOptions()")
print("\nAFTER:")
print("  InitializationOptions(")
print("      server_name=self.config.server.name,")
print("      server_version=self.config.server.version,")
print("      capabilities=self.server.get_capabilities()")
print("  )")