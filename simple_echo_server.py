#!/usr/bin/env python3
"""Simple FastMCP echo server for testing.

Based on FastMCP documentation.
"""

from fastmcp import FastMCP

# Create a simple FastMCP server
mcp = FastMCP(name="Simple Echo Server")


@mcp.tool()  # type: ignore[misc]
def echo_tool(message: str = "hello") -> str:
    """Echo back the message you send."""
    return f"Echo: {message}"


@mcp.tool()  # type: ignore[misc]
def uppercase_echo(message: str = "hello") -> str:
    """Echo back the message in uppercase."""
    return f"ECHO: {message.upper()}"


@mcp.tool()  # type: ignore[misc]
def reverse_echo(message: str = "hello") -> str:
    """Echo back the message reversed."""
    return f"Echo: {message[::-1]}"


if __name__ == "__main__":
    # Run the server - default is stdio transport
    mcp.run()
