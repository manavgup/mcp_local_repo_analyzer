#!/usr/bin/env python3
"""FastMCP Local Git Changes Analyzer Server.

Copyright 2025
SPDX-License-Identifier: Apache-2.0
Author: Manav Gupta <manavg@gmail.com>

Main entry point for the local git changes analyzer server.
Provides server setup, tool registration, and server execution.
"""

import sys

from fastmcp import FastMCP
from mcp_shared_lib.config import settings
from mcp_shared_lib.services import GitClient
from mcp_local_repo_analyzer.services.git import ChangeDetector, DiffAnalyzer, StatusTracker
from mcp_shared_lib.utils import logging_service

logger = logging_service.get_logger(__name__)


def create_server() -> FastMCP:
    """Create and configure the FastMCP server.

    Returns:
        Configured FastMCP server instance.
    """

    # Create the FastMCP server
    mcp = FastMCP(
        name="Local Git Changes Analyzer",
        instructions=""" \
        This server analyzes outstanding local git changes that haven't made their way to GitHub yet.

        Available tools:
        - analyze_working_directory: Check uncommitted changes in working directory
        - analyze_staged_changes: Check staged changes ready for commit
        - analyze_unpushed_commits: Check commits not pushed to remote
        - analyze_stashed_changes: Check stashed changes
        - get_outstanding_summary: Get comprehensive summary of all outstanding changes
        - compare_with_remote: Compare local branch with remote branch
        - get_repository_health: Get overall repository health metrics

        Provide a repository path to analyze, or the tool will attempt to find a git repository
        in the current directory or use the default configured path.
        """,
    )

    # Initialize services
    git_client = GitClient(settings)
    change_detector = ChangeDetector(git_client)
    diff_analyzer = DiffAnalyzer(settings)
    status_tracker = StatusTracker(git_client, change_detector)

    # Store services in the server context for tools to access
    mcp.git_client = git_client
    mcp.change_detector = change_detector
    mcp.diff_analyzer = diff_analyzer
    mcp.status_tracker = status_tracker

    return mcp


def register_tools(mcp: FastMCP):
    """Register all tools with the FastMCP server.

    Args:
        mcp: FastMCP server instance.
    """
    # Import and register tool modules
    from mcp_local_repo_analyzer.tools.staging_area import register_staging_area_tools
    from mcp_local_repo_analyzer.tools.summary import register_summary_tools
    from mcp_local_repo_analyzer.tools.unpushed_commits import register_unpushed_commits_tools
    from mcp_local_repo_analyzer.tools.working_directory import register_working_directory_tools

    # Register all tool groups
    register_working_directory_tools(mcp)
    register_staging_area_tools(mcp)
    register_unpushed_commits_tools(mcp)
    register_summary_tools(mcp)


def main():
    """Main entry point."""
    try:
        # Create server
        mcp = create_server()

        # Register tools
        register_tools(mcp)

        # Run the server
        mcp.run()

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
