# Fix for InitializationOptions Error

## Problem

The server was failing with a `pydantic` validation error when trying to create an `InitializationOptions` object:

```
pydantic_core._pydantic_core.ValidationError: 3 validation errors for InitializationOptions
server_name
  Field required [type=missing, input_value={}, input_type=dict]
server_version
  Field required [type=missing, input_value={}, input_type=dict]
capabilities
  Field required [type=missing, input_value={}, input_type=dict]
```

## Root Cause

In `main.py` line 635, the code was trying to instantiate `InitializationOptions` without any parameters:

```python
InitializationOptions()
```

However, `InitializationOptions` is a Pydantic model that requires three mandatory fields:
- `server_name`: The name of the MCP server
- `server_version`: The version of the server
- `capabilities`: A dictionary describing the server's capabilities

## Solution

The fix was to provide all required fields when creating the `InitializationOptions` object:

```python
InitializationOptions(
    server_name=self.config.server.name,
    server_version=self.config.server.version,
    capabilities=self.server.get_capabilities()
)
```

This change was applied to `main.py` at lines 635-639.

## Implementation Details

The fix uses:
- `self.config.server.name`: Gets the server name from the configuration (default: "pc-control-mcp")
- `self.config.server.version`: Gets the server version from the configuration (default: "2.0.0")
- `self.server.get_capabilities()`: Calls the server's method to get its capabilities dynamically

## Expected Result

After this fix, the server should successfully initialize and run without the validation error. The server will properly communicate its identity and capabilities to MCP clients.

## Additional Notes

This is a common pattern in MCP servers where the `InitializationOptions` must be properly populated with the server's metadata. The MCP protocol uses this information during the handshake process to establish what features the server supports.