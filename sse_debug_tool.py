#!/usr/bin/env python3
"""
Fixed test for the MCP server - handles both stateful and stateless servers
"""

import asyncio
import json

import httpx


async def parse_sse_response(response):
    """Parse SSE response and return the JSON data, handling notifications properly."""
    if response.headers.get("content-type", "").startswith("text/event-stream"):
        result_message = None
        notifications = []

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])

                    # Check if this is a notification
                    if "method" in data and data["method"].startswith("notifications/"):
                        notifications.append(data)
                        continue

                    # Check if this is the result we want (has id and result)
                    if "result" in data and "id" in data:
                        result_message = data
                        break

                    # If it has an error, that's also a result
                    if "error" in data and "id" in data:
                        result_message = data
                        break

                except json.JSONDecodeError:
                    continue

        # Return the result message, or the last notification if no result found
        return result_message if result_message else (notifications[-1] if notifications else None)
    else:
        # Regular JSON response
        return response.json()
    return None

async def send_mcp_request(base_url, message, session_id=None):
    """Send an MCP request and handle both JSON and SSE responses."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }

    if session_id:
        headers["Mcp-Session-Id"] = session_id

    async with httpx.AsyncClient(timeout=30.0) as client:  # Increased timeout
        response = await client.post(f"{base_url}/mcp/", json=message, headers=headers)

        if response.status_code == 200:
            data = await parse_sse_response(response)
            # Check for session ID in headers
            new_session_id = (
                response.headers.get("mcp-session-id") or
                response.headers.get("Mcp-Session-Id") or
                response.headers.get("MCP-Session-ID")
            )
            return True, data, new_session_id
        else:
            return False, f"HTTP {response.status_code}: {response.text}", None

async def test_mcp_server():
    """Test the MCP server with proper SSE handling."""
    base_url = "http://localhost:9070"

    print("🧪 MCP Server Test (SSE + Stateless Support)")
    print("=" * 50)

    # Test 1: Health
    print("1️⃣ Testing health...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/healthz")
        if response.status_code == 200:
            print(f"✅ Health: {response.json()}")
        else:
            print(f"❌ Health failed: {response.status_code}")
            return False

    # Test 2: Initialize
    print("\n2️⃣ Testing initialize...")
    init_msg = {
        "jsonrpc": "2.0",
        "id": "test-init",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        }
    }

    success, data, session_id = await send_mcp_request(base_url, init_msg)
    if not success:
        print(f"❌ Initialize failed: {data}")
        return False

    print("✅ Initialize successful!")
    if session_id:
        print(f"📝 Session ID: {session_id} (stateful server)")
    else:
        print("📝 No session ID (stateless server - this is fine)")

    if data and "result" in data:
        server_info = data["result"].get("serverInfo", {})
        print(f"📋 Server: {server_info.get('name', 'Unknown')} v{server_info.get('version', 'Unknown')}")
        capabilities = data["result"].get("capabilities", {})
        print(f"📋 Capabilities: {list(capabilities.keys())}")

    # Test 3: Tools list
    print("\n3️⃣ Testing tools/list...")
    tools_msg = {
        "jsonrpc": "2.0",
        "id": "test-tools",
        "method": "tools/list",
        "params": {}
    }

    success, data, _ = await send_mcp_request(base_url, tools_msg, session_id)
    if not success:
        print(f"❌ Tools list failed: {data}")
        return False

    print("✅ Tools list successful!")
    if data and "result" in data and "tools" in data["result"]:
        tools = data["result"]["tools"]
        print(f"📋 Found {len(tools)} tools:")
        for tool in tools:
            print(f"   • {tool['name']}: {tool['description']}")

    # Test 4: Call a tool
    print("\n4️⃣ Testing tool call (get_outstanding_summary)...")
    tool_msg = {
        "jsonrpc": "2.0",
        "id": "test-tool-call",
        "method": "tools/call",
        "params": {
            "name": "get_outstanding_summary",
            "arguments": {
                "repository_path": ".",
                "detailed": False
            }
        }
    }

    success, data, _ = await send_mcp_request(base_url, tool_msg, session_id)
    if not success:
        print(f"❌ Tool call failed: {data}")
        return False

    print("✅ Tool call successful!")
    if data and "result" in data:
        result = data["result"]
        if "content" in result and result["content"]:
            # Parse the tool result from FastMCP format
            content = result["content"][0].get("text", "")
            try:
                # FastMCP returns JSON strings in the text field
                tool_result = json.loads(content) if isinstance(content, str) else content
                if isinstance(tool_result, dict):
                    print(f"📋 Repository: {tool_result.get('repository_name', 'Unknown')}")
                    print(f"📋 Outstanding work: {tool_result.get('has_outstanding_work', 'Unknown')}")
                    stats = tool_result.get('quick_stats', {})
                    if stats:
                        print(f"📋 Quick stats: {stats}")
                else:
                    print(f"📋 Tool result: {str(content)[:200]}...")
            except json.JSONDecodeError:
                print(f"📋 Raw result: {content[:200]}...")
    elif data and "method" in data:
        # This was a notification, not the actual result
        print(f"⚠️  Received notification instead of result: {data.get('method')}")
        return False

    print("\n🎉 All tests passed!")
    return True

async def test_specific_scenario():
    """Test a specific git analysis scenario."""
    base_url = "http://localhost:9070"

    print("\n5️⃣ Testing specific git scenario...")

    # First initialize
    init_msg = {
        "jsonrpc": "2.0",
        "id": "scenario-init",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "scenario-test", "version": "1.0.0"}
        }
    }

    success, data, session_id = await send_mcp_request(base_url, init_msg)
    if not success:
        print(f"❌ Scenario init failed: {data}")
        return False

    # Test working directory analysis
    wd_msg = {
        "jsonrpc": "2.0",
        "id": "test-wd",
        "method": "tools/call",
        "params": {
            "name": "analyze_working_directory",
            "arguments": {
                "repository_path": "."
            }
        }
    }

    success, data, _ = await send_mcp_request(base_url, wd_msg, session_id)
    if success and data and "result" in data:
        print("✅ Working directory analysis successful!")
        content = data["result"]["content"][0].get("text", "")
        try:
            result = eval(content)
            if isinstance(result, dict) and "has_changes" in result:
                print(f"📋 Has changes: {result['has_changes']}")
                print(f"📋 Total files: {result.get('total_files_changed', 0)}")
                summary = result.get('summary', {})
                if summary:
                    print(f"📋 Summary: {summary}")
        except:
            print(f"📋 Raw result: {content[:200]}...")
    else:
        print(f"❌ Working directory analysis failed: {data}")
        return False

    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_mcp_server())
        if success:
            scenario_success = asyncio.run(test_specific_scenario())
            success = success and scenario_success

        print(f"\n🏁 Overall test {'PASSED' if success else 'FAILED'}")
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
