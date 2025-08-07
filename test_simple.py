#!/usr/bin/env python3
"""Simple test script that demonstrates the proper way to test the MCP server.

This script shows why the manual pipe approach has limitations and provides
a working alternative.
"""

import asyncio
import subprocess
import sys
from pathlib import Path


def test_manual_pipe_approach() -> bool:
    """Demonstrate why the manual pipe approach has timing issues."""
    print("🔍 Testing manual pipe approach (this may fail due to timing)...")

    try:
        # This is the problematic approach - it doesn't wait for proper initialization
        cmd = [
            "bash",
            "-c",
            '(echo \'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}\'; sleep 2; echo \'{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}\') | poetry run local-git-analyzer',
        ]

        result = subprocess.run(
            cmd, cwd=Path(__file__).parent, capture_output=True, text=True, timeout=10
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


async def test_proper_client_approach() -> bool:
    """Test using the proper FastMCP client approach."""
    print("\n🔍 Testing proper FastMCP client approach...")

    try:
        # Import here to avoid dependency issues
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        # Create proper transport
        transport = StdioTransport(command="poetry", args=["run", "local-git-analyzer"])
        client = Client(transport)

        async with client:
            print("✅ Server connection established")

            # Test ping
            await client.ping()
            print("✅ Server ping successful")

            # Test tools list
            tools = await client.list_tools()
            print(f"✅ Available tools: {len(tools)}")

            # Test a tool call
            await client.call_tool(
                "analyze_working_directory",
                {"repository_path": ".", "include_diffs": False},
            )
            print("✅ Tool call successful")

        print("✅ Proper client approach succeeded")
        return True

    except ImportError:
        print("❌ FastMCP not available - install with: pip install fastmcp")
        return False
    except Exception as e:
        print(f"❌ Proper client approach error: {e}")
        return False


def main() -> bool:
    """Main test runner."""
    print("MCP Server Testing Comparison")
    print("=" * 50)

    # Test manual pipe approach
    manual_success = test_manual_pipe_approach()

    # Test proper client approach
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
        print("\n🎯 RECOMMENDATION: Use the FastMCP client for testing")
        print("   Command: poetry run python test_client.py")

    return client_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
