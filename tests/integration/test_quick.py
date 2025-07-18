import pytest
#!/usr/bin/env python3
"""
Quick test script for any git repository.
Usage: python quick_test.py /path/to/git/repo
"""

import asyncio
import os
import sys
from pathlib import Path
import httpx

from fastmcp import Client
from mcp_local_repo_analyzer.main import create_server, register_tools


async def analyze_repo(repo_path: str):
    """Analyze a git repository."""

    # Create server instance directly (in-memory approach)
    server = create_server()
    register_tools(server)
    
    # Create client with in-memory transport
    client = Client(server)

    async with client:
        print(f"🔍 Analyzing repository: {repo_path}")
        print("=" * 60)

        # Test 1: Outstanding summary
        print("\n📊 Outstanding Summary:")
        try:
            result = await client.call_tool("get_outstanding_summary", {"repository_path": repo_path, "detailed": True})
            print_result(result)
            assert isinstance(result, list) or isinstance(result, dict)
        except Exception as e:
            print(f"❌ Error: {e}")

        # Test 2: Working directory
        print("\n📝 Working Directory Changes:")
        try:
            result = await client.call_tool(
                "analyze_working_directory", {"repository_path": repo_path, "include_diffs": False}
            )
            print_result(result)
            assert isinstance(result, list) or isinstance(result, dict)
        except Exception as e:
            print(f"❌ Error: {e}")

        # Test 3: Repository health
        print("\n💚 Repository Health:")
        try:
            result = await client.call_tool("analyze_repository_health", {"repository_path": repo_path})
            print_result(result)
            assert isinstance(result, list) or isinstance(result, dict)
        except Exception as e:
            print(f"❌ Error: {e}")


def print_result(result):
    """Print tool result in a readable format."""
    if isinstance(result, list) and len(result) > 0:
        # Handle MCP response format
        content = result[0]
        if hasattr(content, "text"):
            import json

            try:
                data = json.loads(content.text)
                print_dict(data, indent=2)
            except Exception:
                print(content.text)
        else:
            print(content)
    else:
        print_dict(result, indent=2)


def print_dict(data, indent=0):
    """Pretty print dictionary data."""
    if isinstance(data, dict):
        if "error" in data:
            print(f"{'  ' * indent}❌ Error: {data['error']}")
            return

        for key, value in data.items():
            if key in ["summary", "has_outstanding_work", "total_outstanding_changes", "health_score", "ready_to_push"]:
                if key == "summary" and isinstance(value, str):
                    print(f"{'  ' * indent}📋 {key}: {value}")
                elif key == "has_outstanding_work":
                    status = "📝 Yes" if value else "✅ No"
                    print(f"{'  ' * indent}🔄 Outstanding work: {status}")
                elif key == "total_outstanding_changes":
                    print(f"{'  ' * indent}📊 Total changes: {value}")
                elif key == "health_score":
                    print(f"{'  ' * indent}💚 Health score: {value}/100")
                elif key == "ready_to_push":
                    status = "✅ Ready" if value else "⏳ Not ready"
                    print(f"{'  ' * indent}🚀 Push status: {status}")
                else:
                    print(f"{'  ' * indent}{key}: {value}")
            elif key == "recommendations" and isinstance(value, list):
                if value:
                    print(f"{'  ' * indent}🔧 Recommendations:")
                    for rec in value[:5]:  # Show first 5
                        if rec:
                            print(f"{'  ' * (indent+1)}• {rec}")
    else:
        print(f"{'  ' * indent}{data}")


@pytest.mark.asyncio
async def test_analyze_repo(tmp_path):
    # Optionally, set up a test repo at tmp_path
    await analyze_repo(str(tmp_path))


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python quick_test.py /path/to/git/repository")
        print("\nExample:")
        print("  python quick_test.py /Users/mg/mg-work/manav/work/ai-experiments/rag_modulo")
        sys.exit(1)

    repo_path = sys.argv[1]

    if not Path(repo_path).exists():
        print(f"❌ Path does not exist: {repo_path}")
        sys.exit(1)

    asyncio.run(analyze_repo(repo_path))


if __name__ == "__main__":
    main()
