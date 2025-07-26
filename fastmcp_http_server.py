#!/usr/bin/env python3
"""
Pure FastMCP HTTP Server - using FastMCP patterns consistently
This uses your existing FastMCP-based tools and services
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

import click
import uvicorn
from fastmcp import FastMCP

# Add src to path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp_local_repo_analyzer.main import create_server, register_tools

# Configure logging
logger = logging.getLogger(__name__)

@click.command()
@click.option("--port", default=9070, help="Port to listen on for HTTP")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option(
    "--log-level",
    default="INFO",
    help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
)
def main(port: int, host: str, log_level: str) -> int:
    """Main entry point for FastMCP HTTP server."""
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    logger.info("🚀 Starting Local Repo Analyzer (FastMCP HTTP)")
    
    try:
        # Create FastMCP server using your existing code
        logger.info("Creating FastMCP server and services...")
        mcp, services = create_server()
        
        # Set up service dependencies (from your main.py)
        mcp.git_client = services['git_client']
        mcp.change_detector = services['change_detector']  
        mcp.diff_analyzer = services['diff_analyzer']
        mcp.status_tracker = services['status_tracker']
        
        # Register tools using your existing registration functions
        logger.info("Registering tools...")
        register_tools(mcp)
        logger.info("✅ FastMCP server and tools ready")
        
        # Run FastMCP in HTTP mode
        logger.info(f"🚀 Starting FastMCP server on http://{host}:{port}")
        logger.info(f"🏥 Health will be available at: http://{host}:{port}/health")
        
        # Use FastMCP's built-in HTTP transport
        mcp.run(transport="streamable-http", host=host, port=port)
        
        return 0
        
    except Exception as e:
        logger.error(f"💥 Server startup failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    sys.exit(main())