#!/usr/bin/env python3
"""
Improved CLI module for mcp_local_repo_analyzer with better transport handling
"""

import argparse
import logging
import sys
import traceback

from mcp_shared_lib.utils import logging_service
from mcp_shared_lib.transports.config import TransportConfig
from mcp_shared_lib.server.runner import run_server
from mcp_local_repo_analyzer.main import create_server, register_tools

logger = logging_service.get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="MCP Local Repository Analyzer Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--transport",
        type=str,
        default="stdio",
        choices=["stdio", "http", "websocket", "sse"],
        help="Transport type"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to transport config YAML"
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Port to run the server on (overrides config/env)"
    )
    parser.add_argument(
        "--host",
        type=str,
        help="Host to bind the server to (overrides config/env)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    return parser.parse_args()


def main():
    """Main CLI entry point with improved transport handling"""
    args = parse_args()
    
    # Set up logging
    logging.basicConfig(level=getattr(logging, args.log_level))
    
    try:
        logger.info("Starting MCP Local Repository Analyzer Server")
        logger.info(f"Transport: {args.transport}")
        logger.info(f"Python version: {sys.version}")
        
        # Handle stdio transport specially (for FastMCP compatibility)
        if args.transport == "stdio" or not args.transport:
            logger.info("Using FastMCP stdio mode")
            try:
                # Import and run FastMCP main directly for stdio
                from mcp_local_repo_analyzer.main import main as fastmcp_main
                fastmcp_main()
                return
            except Exception as e:
                logger.error(f"FastMCP stdio mode failed: {e}")
                logger.error("Falling back to mcp_shared_lib stdio transport")
                # Continue with mcp_shared_lib transport as fallback

        # Load config for non-stdio transports or stdio fallback
        if args.config:
            config = TransportConfig.from_file(args.config)
        else:
            config = TransportConfig.from_env()
            if args.transport:
                config.type = args.transport
                
            # Apply command line overrides
            if args.port:
                if config.type == "http":
                    if not config.http:
                        from mcp_shared_lib.transports.config import HTTPConfig
                        config.http = HTTPConfig()
                    config.http.port = args.port
                elif config.type == "websocket":
                    if not config.websocket:
                        from mcp_shared_lib.transports.config import WebSocketConfig
                        config.websocket = WebSocketConfig()
                    config.websocket.port = args.port
                elif config.type == "sse":
                    if not config.sse:
                        from mcp_shared_lib.transports.config import SSEConfig
                        config.sse = SSEConfig()
                    config.sse.port = args.port
                    
            if args.host:
                if config.type == "http":
                    if not config.http:
                        from mcp_shared_lib.transports.config import HTTPConfig
                        config.http = HTTPConfig()
                    config.http.host = args.host
                elif config.type == "websocket":
                    if not config.websocket:
                        from mcp_shared_lib.transports.config import WebSocketConfig
                        config.websocket = WebSocketConfig()
                    config.websocket.host = args.host
                elif config.type == "sse":
                    if not config.sse:
                        from mcp_shared_lib.transports.config import SSEConfig
                        config.sse = SSEConfig()
                    config.sse.host = args.host

        # Create and register server for mcp_shared_lib transports
        logger.info(f"Creating server for {config.type} transport")
        mcp, services = create_server()
        
        # Set up service dependencies
        mcp.git_client = services['git_client']
        mcp.change_detector = services['change_detector']
        mcp.diff_analyzer = services['diff_analyzer']
        mcp.status_tracker = services['status_tracker']
        
        # Register tools
        register_tools(mcp)

        # Run server with the configured transport
        logger.info(f"Starting server with {config.type} transport")
        run_server(mcp, config, server_name="Local Git Analyzer")
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
