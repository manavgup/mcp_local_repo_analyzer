#!/usr/bin/env python3
"""
Test client for HTTP-based git analyzer server.
"""

import asyncio

from fastmcp import Client


async def test_http_server():
    """Test the HTTP server."""
    # Connect to HTTP server
    client = Client("http://localhost:8000/mcp")

    async with client:
        print("✅ Connected to HTTP server")

        # Test tools
        tools = await client.list_tools()
        print(f"🔧 Found {len(tools)} tools")

        # Test a simple tool
        result = await client.call_tool("analyze_working_directory", {"repository_path": "."})
        print(f"📊 Result: {result.get('total_files_changed', 'unknown')} files changed")


if __name__ == "__main__":
    print("Make sure to run 'python run_http_server.py' first!")
    asyncio.run(test_http_server())
