#!/usr/bin/env python3
"""Simple test script that demonstrates the proper way to test the MCP server.

This script shows why the manual pipe approach has limitations and provides
a working alternative.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path


def test_manual_pipe_approach():
    """Demonstrate why the manual pipe approach has timing issues."""
    print("🔍 Testing manual pipe approach (this may fail due to timing)...")

    try:
        # This is the problematic approach - it doesn't wait for proper initialization
        cmd = [
            "bash", "-c",
            '(echo \'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}\'; sleep 2; echo \'{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}\') | poetry run local-git-analyzer'
        ]

        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print("✅ Manual pipe approach succeeded")
            return True
        else:
            print("❌ Manual pipe approach failed (expected due to timing issues)")
            if "TaskGroup" in result.stderr:
                print("   - TaskGroup error detected (timing issue)")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Manual pipe approach timed out")
        return False
    except Exception as e:
        print(f"❌ Manual pipe approach error: {e}")
        return False


async def test_proper_client_approach():
    """Test using the proper FastMCP client approach by connecting to HTTP."""
    print("\n🔍 Testing proper FastMCP client approach (connecting to HTTP server)...")

    try:
        # Import necessary types for clarity
        from fastmcp import Client
        from mcp.types import (  # Import mcp.types specifically
            BlobResourceContents,
            CallToolResult,
            TextContent,
        )

        # Assume server is running on http://127.0.0.1:9070
        server_url = "http://127.0.0.1:9070/mcp"

        # The Client will infer StreamableHttpTransport from the URL
        client = Client(server_url)

        async with client:
            print("✅ Server connection established")

            # Test ping
            await client.ping()
            print("✅ Server ping successful")

            # Test tools list
            tools = await client.list_tools()
            print(f"✅ Available tools: {len(tools)}")
            # Optional: Print tool names to confirm
            # for tool in tools:
            #     print(f"   - {tool.name}")

            # Test a tool call
            # Assuming you have a git repository in the current directory for testing
            tool_name = "analyze_working_directory"
            tool_params = {
                "repository_path": ".",
                "include_diffs": False
            }

            print(f"🚀 Calling tool: {tool_name} with params: {tool_params}")
            # The client.call_tool method in FastMCP 2.10.6+ should return FastMCP's own CallToolResult,
            # which *does* have a .data attribute. The debug script indicates your *mcp.types.CallToolResult*
            # doesn't have it. This is a subtle but important distinction between FastMCP's client abstraction
            # and the raw MCP types.
            # Let's keep `raw_result` and rely on FastMCP's client to give us the "hydrated" data.
            # The previous error 'list' object has no attribute 'data' might still be an unexpected
            # scenario if FastMCP's client abstraction somehow failed to produce its own CallToolResult.

            raw_result = await client.call_tool(tool_name, tool_params) # Keep this as is for now

            # We need to make sure 'raw_result' is indeed the FastMCP client's CallToolResult
            # If the client.call_tool itself is returning a bare list, that's an issue with fastmcp client setup.
            # Re-adding the explicit check for CallToolResult for robust debugging.
            from fastmcp.client.client import (
                CallToolResult as FastMCPCallToolResult,  # Import FastMCP's CallToolResult
            )

            if not isinstance(raw_result, FastMCPCallToolResult):
                print(f"❌ Unexpected return type from client.call_tool: {type(raw_result)}")
                print(f"Received content (if not FastMCPCallToolResult): {raw_result}")
                return False

            # Check for tool-specific errors first
            if raw_result.is_error:
                print(f"❌ Tool call failed on server side. Error: {raw_result.content}")
                if raw_result.structured_content:
                    print(f"   Structured error: {json.dumps(raw_result.structured_content, indent=2)}")
                return False

            print("✅ Tool call successful")
            print("\n--- Tool Call Result Data ---")

            # Now, based on the FastMCP client's CallToolResult, '.data' should contain the hydrated object
            # if the tool's output schema allowed for it, or fall back to structured_content if not.
            # Since your tool returns dict, FastMCP should put it in .data by default.

            tool_output_data = None
            if raw_result.data is not None:
                tool_output_data = raw_result.data
                print(json.dumps(tool_output_data, indent=2))
            elif raw_result.structured_content is not None:
                tool_output_data = raw_result.structured_content
                print("Using structured_content (raw JSON) as .data was None:")
                print(json.dumps(tool_output_data, indent=2))
            else:
                print("No structured data (.data or .structured_content) found. Checking raw .content blocks:")
                for content_block in raw_result.content:
                    if isinstance(content_block, TextContent):
                        print(f"Text Content: {content_block.text}")
                    elif isinstance(content_block, BlobResourceContents):
                        print(f"Binary Content (mimeType: {content_block.mimeType}): {len(content_block.blob)} bytes")
                    else:
                        print(f"Other content type: {type(content_block)}")
                print("❌ Tool result did not contain expected structured data.")
                return False # Fail the test if no structured data found

            print("-----------------------------\n")

            # Add a basic assertion to confirm the tool's output structure
            if not isinstance(tool_output_data, dict):
                print(f"❌ Expected tool_output_data to be a dictionary, but got {type(tool_output_data)}")
                return False

            # Now assert on the *content* of the dictionary
            if 'repository_path' not in tool_output_data or 'total_files_changed' not in tool_output_data:
                print("❌ Tool result is missing expected keys ('repository_path' or 'total_files_changed').")
                return False

            # Example of a more specific assertion
            if not isinstance(tool_output_data.get('total_files_changed'), int):
                print(f"❌ 'total_files_changed' expected to be an int, got {type(tool_output_data.get('total_files_changed'))}")
                return False

            print("✅ Tool result data structure confirmed.")

        print("✅ Proper client approach succeeded")
        return True

    except ImportError:
        print("❌ FastMCP or mcp library not available. Ensure they are installed in your environment.")
        return False
    except Exception as e:
        print(f"❌ Proper client approach error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test runner."""
    print("MCP Server Testing Comparison")
    print("=" * 50)

    # Test manual pipe approach
    manual_success = test_manual_pipe_approach()

    print("\n--- ATTENTION ---")
    print("Please ensure your 'local_repo_analyzer_streamable_http.py' server is running")
    print("e.g., by executing: poetry run uvicorn local_repo_analyzer_streamable_http:app --host 127.0.0.1 --port 9070 --log-level debug")
    print("Or if using pm2: pm2 start 'poetry run uvicorn local_repo_analyzer_streamable_http:app --host 127.0.0.1 --port 9070 --log-level debug' --name local-repo-analyzer-fastmcp-fixed")
    print("-----------------\n")

    client_success = asyncio.run(test_proper_client_approach())

    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"Manual pipe approach: {'✅ Success' if manual_success else '❌ Failed'}")
    print(f"Proper client approach: {'✅ Success' if client_success else '❌ Failed'}")

    if not manual_success and client_success:
        print("\n💡 EXPLANATION:")
        print("The manual pipe approach fails because:")
        print("1. It doesn't wait for proper server initialization")
        print("2. The timing is unpredictable and race-condition prone")
        print("3. It doesn't handle the MCP protocol correctly")
        print("\nThe proper FastMCP client approach succeeds because:")
        print("1. It waits for initialization to complete")
        print("2. It handles the MCP protocol correctly")
        print("3. It manages the connection lifecycle properly")
        print("\n🎯 RECOMMENDATION: Use the FastMCP client for testing, connecting to the HTTP endpoint directly.")

    return client_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
