#!/usr/bin/env python3
"""Debug script to check what's available in mcp.types."""

import logging

# Set a basic logger for the debug script itself
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Add project src to path if needed for broader imports, though for mcp/fastmcp direct imports are usually enough
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


try:
    import mcp.types as types

    print("✅ Successfully imported mcp.types")

    print("\n📋 Available attributes in mcp.types:")
    attributes = [attr for attr in dir(types) if not attr.startswith("_")]
    for attr in sorted(attributes):
        try:
            obj = getattr(types, attr)
            # Use repr for object types for more detail if not a simple built-in type
            if isinstance(obj, type):
                print(f"  {attr}: {obj.__name__} (type)")
                if hasattr(obj, "__annotations__"):
                    print(f"    Fields: {list(obj.__annotations__.keys())}")
            else:
                print(f"  {attr}: {type(obj).__name__}")
        except Exception as e:
            print(f"  {attr}: Error - {e}")

    print("\n🔍 Looking for content-related types:")
    content_attrs = [
        attr
        for attr in attributes
        if "content" in attr.lower()
        or "text" in attr.lower()
        or "resource" in attr.lower()
    ]
    for attr in content_attrs:
        print(f"  ✓ {attr}")

    print("\n🔍 Looking for tool-related types:")
    tool_attrs = [attr for attr in attributes if "tool" in attr.lower()]
    for attr in tool_attrs:
        print(f"  ✓ {attr}")

    # Try to find the correct content type
    print("\n🎯 Testing common content types:")
    test_types = [
        "TextContent",
        "BlobResourceContents",
        "ImageContent",
        "AudioContent",
        "ContentBlock",
        "CallToolResult",
        "ReadResourceResult",
    ]  # Added more relevant types
    for test_type in test_types:
        if hasattr(types, test_type):
            print(f"  ✅ {test_type} exists")
            try:
                cls = getattr(types, test_type)
                print(f"     Type: {type(cls)}")
                if hasattr(cls, "__annotations__"):  # For Pydantic models/dataclasses
                    print(
                        f"     Fields (annotations): {list(cls.__annotations__.keys())}"
                    )
                elif hasattr(cls, "__dataclass_fields__"):  # For dataclasses
                    print(
                        f"     Fields (dataclass): {list(cls.__dataclass_fields__.keys())}"
                    )
                elif hasattr(cls, "model_fields"):  # For Pydantic V2 models
                    print(f"     Fields (Pydantic V2): {list(cls.model_fields.keys())}")
            except Exception as e:
                print(f"     Error inspecting: {e}")
        else:
            print(f"  ❌ {test_type} not found")

except ImportError as e:
    print(f"❌ Failed to import mcp.types: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

# Also check if we can import the lowlevel server
try:
    from mcp.server.lowlevel import Server

    print("\n✅ Successfully imported mcp.server.lowlevel.Server")

    # Check Server class methods
    print("\n📋 Server class methods:")
    methods = [method for method in dir(Server) if not method.startswith("_")]
    for method in sorted(methods):
        print(f"  {method}")

except ImportError as e:
    print(f"\n❌ Failed to import Server: {e}")
except Exception as e:
    print(f"\n❌ Unexpected error inspecting mcp.server.lowlevel.Server: {e}")


# Check streamable http manager
try:
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

    print("\n✅ Successfully imported StreamableHTTPSessionManager")

    print("\n📋 StreamableHTTPSessionManager attributes:")
    attributes = [
        attr for attr in dir(StreamableHTTPSessionManager) if not attr.startswith("_")
    ]
    for attr in sorted(attributes):
        print(f"  {attr}")

except ImportError as e:
    print(f"\n❌ Failed to import StreamableHTTPSessionManager: {e}")
except Exception as e:
    print(f"\n❌ Unexpected error inspecting StreamableHTTPSessionManager: {e}")

print("\n🔍 Checking MCP package version:")
try:
    import mcp

    if hasattr(mcp, "__version__"):
        print(f"  MCP version: {mcp.__version__}")
    else:
        print("  MCP version: unknown")
except Exception as e:
    print(f"  Error checking version: {e}")

print("\n🔍 Checking if this is FastMCP or official MCP:")
try:
    import fastmcp

    print("  FastMCP is installed")
    if hasattr(fastmcp, "__version__"):
        print(f"  FastMCP version: {fastmcp.__version__}")
except ImportError:
    print("  FastMCP not found")

# Re-check official MCP version if fastmcp isn't found or different
try:
    from mcp import __version__ as mcp_version

    print(f"  Official MCP version: {mcp_version}")
except ImportError:
    print(
        "  Could not determine official MCP version (mcp package not found or version not exposed)"
    )
except Exception as e:
    print(f"  Error checking official MCP version: {e}")

print("\n--- Script Finished ---")
