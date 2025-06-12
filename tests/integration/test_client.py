#!/usr/bin/env python3
"""
Simple test client for the Local Git Changes Analyzer FastMCP server.
"""

import asyncio
import json
import sys

from fastmcp import Client


async def test_server():
    """Test the git analyzer server with various scenarios."""

    # Create client with explicit Python stdio transport
    # This ensures the server runs with proper Python path
    import os

    from fastmcp.client.transports import PythonStdioTransport

    transport = PythonStdioTransport(
        script_path="local_git_analyzer/main.py",
        python_cmd="python",  # Use the current Python interpreter
        env={**os.environ, "PYTHONPATH": os.getcwd()},  # Add current dir to Python path
    )
    client = Client(transport)

    async with client:
        try:
            print(f"📡 Transport type: {client.transport}")
            print("✅ Connected to Local Git Changes Analyzer server")

            # Test 1: Get available tools
            print("\n📋 Available Tools:")
            tools = await client.list_tools()
            for tool in tools:
                # Handle both dict and object formats
                if hasattr(tool, "name"):
                    tool_name = tool.name
                    tool_desc = getattr(tool, "description", "No description")
                else:
                    tool_name = tool.get("name", "Unknown")
                    tool_desc = tool.get("description", "No description")
                print(f"  - {tool_name}: {tool_desc}")

            # Test 2: Analyze working directory
            print("\n🔍 Testing working directory analysis...")
            try:
                result = await client.call_tool(
                    "analyze_working_directory", {"repository_path": ".", "include_diffs": True, "max_diff_lines": 50}
                )
                print("✅ Working directory analysis:")
                print_result_summary(result)
            except Exception as e:
                print(f"❌ Working directory analysis failed: {e}")

            # Test 3: Analyze staged changes
            print("\n📋 Testing staged changes analysis...")
            try:
                result = await client.call_tool(
                    "analyze_staged_changes", {"repository_path": ".", "include_diffs": False}
                )
                print("✅ Staged changes analysis:")
                print_result_summary(result)
            except Exception as e:
                print(f"❌ Staged changes analysis failed: {e}")

            # Test 4: Get outstanding summary
            print("\n📊 Testing comprehensive summary...")
            try:
                result = await client.call_tool("get_outstanding_summary", {"repository_path": ".", "detailed": True})
                print("✅ Outstanding summary:")
                print_result_summary(result)
            except Exception as e:
                print(f"❌ Outstanding summary failed: {e}")

            # Test 5: Analyze unpushed commits
            print("\n🚀 Testing unpushed commits analysis...")
            try:
                result = await client.call_tool("analyze_unpushed_commits", {"repository_path": ".", "max_commits": 10})
                print("✅ Unpushed commits analysis:")
                print_result_summary(result)
            except Exception as e:
                print(f"❌ Unpushed commits analysis failed: {e}")

            # Test 6: Check repository health
            print("\n💚 Testing repository health analysis...")
            try:
                result = await client.call_tool("analyze_repository_health", {"repository_path": "."})
                print("✅ Repository health analysis:")
                print_result_summary(result)
            except Exception as e:
                print(f"❌ Repository health analysis failed: {e}")

            # Test 7: Check push readiness
            print("\n🎯 Testing push readiness assessment...")
            try:
                result = await client.call_tool("get_push_readiness", {"repository_path": "."})
                print("✅ Push readiness assessment:")
                print_result_summary(result)
            except Exception as e:
                print(f"❌ Push readiness assessment failed: {e}")

            print("\n✨ All tests completed!")
            return True

        except Exception as e:
            print(f"❌ Failed to connect or test server: {e}")
            return False


def print_result_summary(result):
    """Print a summary of the tool result."""
    if isinstance(result, dict):
        if "error" in result:
            print(f"  ❌ Error: {result['error']}")
            return

        # Print key metrics
        metrics = []

        # Common fields to look for
        if "total_files_changed" in result:
            metrics.append(f"Files changed: {result['total_files_changed']}")
        if "total_staged_files" in result:
            metrics.append(f"Staged files: {result['total_staged_files']}")
        if "total_unpushed_commits" in result:
            metrics.append(f"Unpushed commits: {result['total_unpushed_commits']}")
        if "health_score" in result:
            metrics.append(f"Health score: {result['health_score']}/100")
        if "ready_to_push" in result:
            status = "✅ Ready" if result["ready_to_push"] else "⏳ Not ready"
            metrics.append(f"Push status: {status}")
        if "has_outstanding_work" in result:
            work_status = "📝 Has work" if result["has_outstanding_work"] else "✅ Clean"
            metrics.append(f"Work status: {work_status}")

        if metrics:
            print(f"  📊 {' | '.join(metrics)}")

        # Print summary or message if available
        if "summary" in result and isinstance(result["summary"], str):
            print(f"  💬 {result['summary']}")
        elif "message" in result:
            print(f"  💬 {result['message']}")

        # Print any recommendations
        if "recommendations" in result and result["recommendations"]:
            print("  🔧 Recommendations:")
            for rec in result["recommendations"][:3]:  # Show first 3
                if rec:  # Skip None values
                    print(f"    • {rec}")
    else:
        print(f"  📄 Result: {str(result)[:100]}...")


async def test_specific_tool(tool_name: str, **kwargs):
    """Test a specific tool with given parameters."""
    import os

    from fastmcp.client.transports import PythonStdioTransport

    transport = PythonStdioTransport(
        script_path="local_git_analyzer/main.py", python_cmd="python", env={**os.environ, "PYTHONPATH": os.getcwd()}
    )
    client = Client(transport)

    async with client:
        try:
            print(f"🧪 Testing tool: {tool_name}")

            result = await client.call_tool(tool_name, kwargs)
            print(f"✅ Result for {tool_name}:")
            print(json.dumps(result, indent=2, default=str))

        except Exception as e:
            print(f"❌ Test failed: {e}")


async def test_connection():
    """Test basic connection and server info."""
    import os

    from fastmcp.client.transports import PythonStdioTransport

    transport = PythonStdioTransport(
        script_path="local_git_analyzer/main.py", python_cmd="python", env={**os.environ, "PYTHONPATH": os.getcwd()}
    )
    client = Client(transport)

    async with client:
        try:
            print("🔌 Testing basic connection...")
            print(f"📡 Transport: {client.transport}")

            # Test basic ping instead of server info
            await client.ping()
            print("🏓 Server ping successful")

            # Test available tools
            tools = await client.list_tools()
            print(f"🔧 Available tools: {len(tools)}")
            for tool in tools:
                # Handle both dict and object formats
                if hasattr(tool, "name"):
                    # Tool object format
                    tool_name = tool.name
                    tool_desc = getattr(tool, "description", "No description")
                else:
                    # Dict format
                    tool_name = tool.get("name", "Unknown")
                    tool_desc = tool.get("description", "No description")
                print(f"   - {tool_name}: {tool_desc}")

            return True

        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False


def main():
    """Main entry point for the test client."""
    import argparse

    parser = argparse.ArgumentParser(description="Test the Local Git Changes Analyzer server")
    parser.add_argument("--tool", help="Test a specific tool (e.g., analyze_working_directory)")
    parser.add_argument("--repository-path", default=".", help="Repository path to analyze")
    parser.add_argument("--detailed", action="store_true", help="Include detailed analysis")
    parser.add_argument("--connection-only", action="store_true", help="Test connection only")

    args = parser.parse_args()

    if args.connection_only:
        # Test connection only
        success = asyncio.run(test_connection())
        sys.exit(0 if success else 1)
    elif args.tool:
        # Test specific tool
        kwargs = {"repository_path": args.repository_path}
        if args.detailed:
            kwargs["detailed"] = True

        asyncio.run(test_specific_tool(args.tool, **kwargs))
    else:
        # Run full test suite
        asyncio.run(test_server())


if __name__ == "__main__":
    main()
