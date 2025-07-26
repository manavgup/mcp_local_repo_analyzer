#!/usr/bin/env python3
"""
Clean FastMCP 2.0 Server using proper async patterns
Following FastMCP documentation for streamable-http transport
"""

import os
import asyncio
import logging
import sys
from pathlib import Path

from fastmcp import FastMCP, Context
from pydantic import Field

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp_shared_lib.config import settings
from mcp_shared_lib.services import GitClient
from mcp_shared_lib.models import LocalRepository
from mcp_shared_lib.utils import find_git_root, is_git_repository
from mcp_local_repo_analyzer.services.git import ChangeDetector, DiffAnalyzer, StatusTracker

# Configure logging
log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
# Let's ensure FastMCP's internal logs are at the specified level
logging.getLogger("fastmcp").setLevel(getattr(logging, log_level_str))
# And any other top-level loggers you use in your application (e.g., if you have `mcp_shared_lib`)
logging.getLogger("mcp_shared_lib").setLevel(getattr(logging, log_level_str))
logging.getLogger("mcp_local_repo_analyzer").setLevel(getattr(logging, log_level_str))

logger = logging.getLogger(__name__)

# Create the FastMCP server instance
# We create it globally so it can be imported by uvicorn
mcp_instance = None # Initialize as None to be set once
app = None # This will hold our ASGI application

def create_fastmcp_server() -> FastMCP:
    """Create a FastMCP server with tools and custom routes."""
    
    # Initialize services
    logger.info("Initializing git analysis services...")
    git_client = GitClient(settings)
    change_detector = ChangeDetector(git_client)
    diff_analyzer = DiffAnalyzer(settings)
    status_tracker = StatusTracker(git_client, change_detector)
    logger.info("✅ Services initialized")
    
    # Create FastMCP server
    # Note: FastMCP constructor accepts a 'version' parameter if you want to explicitly set it.
    # Otherwise, it might be inferred or default.
    mcp = FastMCP(
        name="Local Git Changes Analyzer",
        instructions="""
        This server analyzes outstanding local git changes that haven't made their way to GitHub yet.

        Available tools:
        - analyze_working_directory: Check uncommitted changes in working directory
        - analyze_staged_changes: Check staged changes ready for commit
        - get_outstanding_summary: Get comprehensive summary of all outstanding changes

        Provide a repository path to analyze, or the tool will attempt to find a git repository
        in the current directory or use the default configured path.
        """
    )
    
    # Store services on the server for access in tools
    mcp.git_client = git_client
    mcp.change_detector = change_detector
    mcp.diff_analyzer = diff_analyzer
    mcp.status_tracker = status_tracker
    
    # Add custom health endpoints using FastMCP's @custom_route
    # These remain as they are standard practice and don't conflict with /mcp POST.
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    
    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "Local Git Changes Analyzer"})
    
    @mcp.custom_route("/healthz", methods=["GET"]) 
    async def health_check_z(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "Local Git Changes Analyzer"})

    # The problematic mcp_get_probe custom_route has been removed from here.

    @mcp.tool()
    async def analyze_working_directory(
        ctx: Context,
        repository_path: str = Field(default=".", description="Path to git repository"),
        include_diffs: bool = Field(True, description="Include diff content in analysis"),
    ) -> dict:
        """Analyze uncommitted changes in working directory."""
        await ctx.info(f"Starting working directory analysis for: {repository_path}")
        
        try:
            repo_path = Path(repository_path).resolve()
            if not is_git_repository(repo_path):
                git_root = find_git_root(repo_path)
                if not git_root:
                    await ctx.error(f"No git repository found at or above {repo_path}")
                    return {"error": f"No git repository found at or above {repo_path}"}
                repo_path = git_root
                await ctx.debug(f"Found git repository at: {repo_path}")

            repo = LocalRepository(
                path=repo_path,
                name=repo_path.name,
                current_branch="main",
                head_commit="unknown"
            )

            await ctx.debug("Detecting working directory changes")
            changes = await change_detector.detect_working_directory_changes(repo, ctx)
            await ctx.info(f"Found {changes.total_files} changed files")

            result = {
                "repository_path": str(repo_path),
                "total_files_changed": changes.total_files,
                "has_changes": changes.has_changes,
                "summary": {
                    "modified": len(changes.modified_files),
                    "added": len(changes.added_files),
                    "deleted": len(changes.deleted_files),
                    "renamed": len(changes.renamed_files),
                    "untracked": len(changes.untracked_files),
                }
            }

            await ctx.info("Working directory analysis completed")
            return result

        except Exception as e:
            await ctx.error(f"Working directory analysis failed: {str(e)}")
            return {"error": f"Failed to analyze working directory: {str(e)}"}

    @mcp.tool()
    async def analyze_staged_changes(
        ctx: Context,
        repository_path: str = Field(default=".", description="Path to git repository"),
        include_diffs: bool = Field(True, description="Include diff content for staged files"),
    ) -> dict:
        """Analyze changes staged for commit."""
        await ctx.info(f"Starting staged changes analysis for: {repository_path}")
        
        try:
            repo_path = Path(repository_path).resolve()
            if not is_git_repository(repo_path):
                git_root = find_git_root(repo_path)
                if not git_root:
                    await ctx.error(f"No git repository found at or above {repo_path}")
                    return {"error": f"No git repository found at or above {repo_path}"}
                repo_path = git_root

            repo = LocalRepository(
                path=repo_path,
                name=repo_path.name,
                current_branch="main",
                head_commit="unknown"
            )

            await ctx.debug("Detecting staged changes")
            staged_changes = await change_detector.detect_staged_changes(repo, ctx)
            await ctx.info(f"Found {staged_changes.total_staged} staged files")

            result = {
                "repository_path": str(repo_path),
                "total_staged_files": staged_changes.total_staged,
                "ready_to_commit": staged_changes.ready_to_commit,
                "statistics": {
                    "total_additions": staged_changes.total_additions,
                    "total_deletions": staged_changes.total_deletions,
                },
                "staged_files": [
                    {
                        "path": f.path,
                        "status": f.status_code,
                        "status_description": f.status_description,
                        "lines_added": f.lines_added,
                        "lines_deleted": f.lines_deleted,
                        "total_changes": f.total_changes,
                        "is_binary": f.is_binary,
                    }
                    for f in staged_changes.staged_files
                ]
            }

            await ctx.info("Staged changes analysis completed")
            return result

        except Exception as e:
            await ctx.error(f"Staged changes analysis failed: {str(e)}")
            return {"error": f"Failed to analyze staged changes: {str(e)}"}

    @mcp.tool()
    async def get_outstanding_summary(
        ctx: Context,
        repository_path: str = Field(default=".", description="Path to git repository"),
        detailed: bool = Field(True, description="Include detailed analysis and recommendations"),
    ) -> dict:
        """Get comprehensive summary of all outstanding changes."""
        await ctx.info(f"Starting comprehensive repository analysis for: {repository_path}")
        
        try:
            repo_path = Path(repository_path).resolve()
            if not is_git_repository(repo_path):
                git_root = find_git_root(repo_path)
                if not git_root:
                    await ctx.error(f"No git repository found at or above {repo_path}")
                    return {"error": f"No git repository found at or above {repo_path}"}
                repo_path = git_root
                await ctx.debug(f"Found git repository at: {repo_path}")

            # Get branch info
            branch_info = await git_client.get_branch_info(repo_path, ctx)

            repo = LocalRepository(
                path=repo_path,
                name=repo_path.name,
                current_branch=branch_info.get("current_branch", "main"),
                head_commit="unknown",
            )

            await ctx.info("Analyzing all repository components...")

            # Get complete repository status
            repo_status = await status_tracker.get_repository_status(repo, ctx)

            await ctx.debug("Categorizing and analyzing file changes")

            # Analyze all files together for categorization and risk
            all_changed_files = repo_status.working_directory.all_files + repo_status.staged_changes.staged_files

            await ctx.debug(f"Analyzing {len(all_changed_files)} total changed files")
            categories = diff_analyzer.categorize_changes(all_changed_files)
            risk_assessment = diff_analyzer.assess_risk(all_changed_files)

            await ctx.debug("Generating recommendations and summary")

            # Generate recommendations
            recommendations = []
            if repo_status.working_directory.has_changes:
                if risk_assessment.risk_level == "high":
                    recommendations.append("⚠️  Review high-risk changes carefully before committing")
                recommendations.append("📝 Commit working directory changes when ready")

            if repo_status.staged_changes.ready_to_commit:
                recommendations.append("✅ Commit staged changes")

            if len(repo_status.unpushed_commits) > 0:
                if len(repo_status.unpushed_commits) > 5:
                    recommendations.append("🚀 Push commits to remote (many commits waiting)")
                else:
                    recommendations.append("🚀 Push commits to remote when ready")

            if repo_status.branch_status.behind_by > 0:
                recommendations.append("⬇️  Pull latest changes from remote")

            if len(repo_status.stashed_changes) > 0:
                recommendations.append("📦 Review and apply/clean up stashed changes")

            # Create summary text
            if not repo_status.has_outstanding_work:
                summary_text = "✅ Repository is clean - no outstanding changes detected."
            else:
                parts = []
                if repo_status.working_directory.has_changes:
                    wd = repo_status.working_directory
                    parts.append(f"📝 {wd.total_files} file(s) with uncommitted changes")
                if repo_status.staged_changes.ready_to_commit:
                    parts.append(f"📋 {repo_status.staged_changes.total_staged} file(s) staged for commit")
                if len(repo_status.unpushed_commits) > 0:
                    parts.append(f"🚀 {len(repo_status.unpushed_commits)} unpushed commit(s)")
                if not repo_status.branch_status.is_up_to_date:
                    parts.append(f"🔄 Branch {repo_status.branch_status.sync_status}")
                if risk_assessment.risk_level == "high":
                    parts.append("⚠️  High-risk changes detected")
                elif risk_assessment.risk_level == "medium":
                    parts.append("⚡ Medium-risk changes detected")
                summary_text = " | ".join(parts) if parts else "Repository has outstanding work."

            result = {
                "repository_path": str(repo_path),
                "repository_name": repo.name,
                "current_branch": repo_status.branch_status.current_branch,
                "analysis_timestamp": "2025-07-25T03:00:00Z",
                "has_outstanding_work": repo_status.has_outstanding_work,
                "total_outstanding_changes": repo_status.total_outstanding_changes,
                "summary": summary_text,
                "quick_stats": {
                    "working_directory_changes": repo_status.working_directory.total_files,
                    "staged_changes": repo_status.staged_changes.total_staged,
                    "unpushed_commits": len(repo_status.unpushed_commits),
                    "stashed_changes": len(repo_status.stashed_changes),
                },
                "branch_status": {
                    "current": repo_status.branch_status.current_branch,
                    "upstream": repo_status.branch_status.upstream_branch,
                    "sync_status": repo_status.branch_status.sync_status,
                    "ahead_by": repo_status.branch_status.ahead_by,
                    "behind_by": repo_status.branch_status.behind_by,
                    "needs_push": repo_status.branch_status.needs_push,
                    "needs_pull": repo_status.branch_status.needs_pull,
                },
                "risk_assessment": {
                    "risk_level": risk_assessment.risk_level,
                    "score": risk_assessment.risk_score,
                    "factors": risk_assessment.risk_factors,
                    "large_changes": risk_assessment.large_changes,
                    "potential_conflicts": risk_assessment.potential_conflicts,
                },
                "recommendations": recommendations,
            }

            if detailed:
                await ctx.debug("Adding detailed breakdown to results")
                result["detailed_breakdown"] = {
                    "working_directory": {
                        "modified": len(repo_status.working_directory.modified_files),
                        "added": len(repo_status.working_directory.added_files),
                        "deleted": len(repo_status.working_directory.deleted_files),
                        "renamed": len(repo_status.working_directory.renamed_files),
                        "untracked": len(repo_status.working_directory.untracked_files),
                    },
                    "file_categories": {
                        "critical": len(categories.critical_files),
                        "source_code": len(categories.source_code),
                        "documentation": len(categories.documentation),
                        "tests": len(categories.tests),
                        "configuration": len(categories.configuration),
                        "other": len(categories.other),
                    },
                    "risk_factors": {
                        "large_changes": risk_assessment.large_changes,
                        "potential_conflicts": risk_assessment.potential_conflicts,
                        "binary_changes": risk_assessment.binary_changes,
                    },
                }

            # Log summary insights
            if repo_status.has_outstanding_work:
                await ctx.info(f"Analysis complete: {repo_status.total_outstanding_changes} outstanding changes found")
                if risk_assessment.risk_level == "high":
                    await ctx.warning("High-risk changes detected - review carefully before proceeding")
                elif len(repo_status.unpushed_commits) > 10:
                    await ctx.warning(f"Many unpushed commits ({len(repo_status.unpushed_commits)}) - consider pushing soon")
            else:
                await ctx.info("Repository is clean - no outstanding changes detected")

            await ctx.info("Comprehensive analysis completed")
            return result

        except Exception as e:
            await ctx.error(f"Comprehensive analysis failed: {str(e)}")
            return {"error": f"Failed to get outstanding summary: {str(e)}"}

    return mcp


# Configure logging once globally
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Create the FastMCP server instance globally
mcp_instance = create_fastmcp_server()

# The ASGI application that Uvicorn (or PM2) will serve
# This is crucial for lifespan management
app = mcp_instance.http_app(
    path="/mcp",  # Default MCP endpoint path
    transport="streamable-http"  # Explicitly specify transport
)


# Main entry point for running the server using uvicorn (or via pm2)
if __name__ == "__main__":
    import uvicorn
    # Get port and host from environment variables or use defaults
    port = int(os.environ.get("PORT", 9070))
    host = os.environ.get("HOST", "127.0.0.1")
    log_level = os.environ.get("LOG_LEVEL", "INFO").lower()

    logger.info(f"🚀 Starting Local Repo Analyzer (FastMCP 2.0) with Uvicorn on {host}:{port}")
    logger.info(f"🌐 MCP endpoint: http://{host}:{port}/mcp")
    logger.info(f"🏥 Health endpoints: http://{host}:{port}/health, http://{host}:{port}/healthz")

    uvicorn.run(app, host=host, port=port, log_level=log_level)