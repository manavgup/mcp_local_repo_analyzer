"""FastMCP tools for working directory analysis."""

import time
from pathlib import Path

from fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any

from ..models.changes import FileStatus
from ..models.repository import LocalRepository
from ..utils import find_git_root, is_git_repository


def register_working_directory_tools(mcp: FastMCP) -> None:
    """Register working directory analysis tools."""

    @mcp.tool()
    async def analyze_working_directory(
        ctx: Context,
        repository_path: str = Field(default=".", description="Path to git repository (default: current directory)"),
        include_diffs: bool = Field(True, description="Include diff content in analysis"),
        max_diff_lines: int = Field(100, ge=10, le=1000, description="Maximum lines per diff to include"),
    ) -> dict[str, Any]:
        """Analyze uncommitted changes in working directory.

        Returns detailed information about modified, added, deleted, renamed,
        and untracked files in the working directory.
        """
        start_time = time.time()
        await ctx.info(f"Starting working directory analysis for: {repository_path}")

        # Resolve repository path
        repo_path = Path(repository_path).resolve()
        if not is_git_repository(repo_path):
            git_root = find_git_root(repo_path)
            if not git_root:
                await ctx.error(f"No git repository found at or above {repo_path}")
                return {"error": f"No git repository found at or above {repo_path}"}
            repo_path = git_root
            await ctx.debug(f"Found git repository at: {repo_path}")

        try:
            await ctx.report_progress(0, 4)
            await ctx.debug("Creating repository model")

            # Create repository model
            repo = LocalRepository(
                path=repo_path,
                name=repo_path.name,
                current_branch="main",  # Will be updated by git client
                head_commit="unknown",  # Will be updated by git client
            )

            await ctx.report_progress(1, 4)
            await ctx.debug("Detecting working directory changes")

            # Detect working directory changes
            changes = await mcp.change_detector.detect_working_directory_changes(repo)

            await ctx.report_progress(2, 4)
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
                },
                "files": {
                    "modified": [_format_file_status(f) for f in changes.modified_files],
                    "added": [_format_file_status(f) for f in changes.added_files],
                    "deleted": [_format_file_status(f) for f in changes.deleted_files],
                    "renamed": [_format_file_status(f) for f in changes.renamed_files],
                    "untracked": [_format_file_status(f) for f in changes.untracked_files],
                },
            }

            # Add diffs if requested
            if include_diffs and changes.has_changes:
                await ctx.debug(f"Generating diffs for {min(10, len(changes.all_files))} files")
                result["diffs"] = await _get_file_diffs(mcp, repo_path, changes.all_files[:10], max_diff_lines, ctx)

            await ctx.report_progress(4, 4)
            duration = time.time() - start_time
            await ctx.info(f"Working directory analysis completed in {duration:.2f} seconds")

            return result

        except Exception as e:
            duration = time.time() - start_time
            await ctx.error(f"Working directory analysis failed after {duration:.2f} seconds: {str(e)}")
            return {"error": f"Failed to analyze working directory: {str(e)}"}

    @mcp.tool()
    async def get_file_diff(
        ctx: Context,
        file_path: str = Field(..., description="Path to specific file relative to repository root"),
        repository_path: str = Field(default=".", description="Path to git repository"),
        staged: bool = Field(False, description="Get staged diff instead of working tree diff"),
        max_lines: int = Field(200, ge=10, le=2000, description="Maximum lines to include in diff"),
    ) -> dict[str, Any]:
        """Get detailed diff for a specific file.

        Returns the diff content, statistics, and metadata for a single file.
        """
        await ctx.info(f"Getting diff for file: {file_path} (staged: {staged})")

        repo_path = Path(repository_path).resolve()
        if not is_git_repository(repo_path):
            git_root = find_git_root(repo_path)
            if not git_root:
                await ctx.error(f"No git repository found at or above {repo_path}")
                return {"error": f"No git repository found at or above {repo_path}"}
            repo_path = git_root

        try:
            await ctx.debug(f"Executing git diff command for {file_path}")

            # Get diff from git
            diff_content = await mcp.git_client.get_diff(repo_path, staged=staged, file_path=file_path)

            if not diff_content.strip():
                await ctx.debug(f"No changes found for file: {file_path}")
                return {"file_path": file_path, "has_changes": False, "message": "No changes found for this file"}

            await ctx.debug("Parsing diff content")

            # Parse diff
            file_diffs = mcp.diff_analyzer.parse_diff(diff_content)

            if not file_diffs:
                await ctx.warning(f"Failed to parse diff for {file_path}, returning raw content")
                return {
                    "file_path": file_path,
                    "has_changes": False,
                    "raw_diff": diff_content[: max_lines * 50],  # Fallback
                }

            file_diff = file_diffs[0]  # Should only be one file

            # Truncate diff content if too long
            if len(diff_content.split("\n")) > max_lines:
                lines = diff_content.split("\n")
                truncated_diff = "\n".join(lines[:max_lines])
                truncated_diff += f"\n... (truncated, {len(lines) - max_lines} more lines)"
                await ctx.debug(f"Truncated diff from {len(lines)} to {max_lines} lines")
            else:
                truncated_diff = diff_content

            await ctx.info(f"Successfully generated diff for {file_path} ({file_diff.total_changes} total changes)")

            return {
                "file_path": file_diff.file_path,
                "old_path": file_diff.old_path,
                "has_changes": True,
                "is_binary": file_diff.is_binary,
                "statistics": {
                    "lines_added": file_diff.lines_added,
                    "lines_deleted": file_diff.lines_deleted,
                    "total_changes": file_diff.total_changes,
                },
                "hunks": len(file_diff.hunks),
                "diff_content": truncated_diff,
                "is_large_change": file_diff.is_large_change,
            }

        except Exception as e:
            await ctx.error(f"Failed to get diff for {file_path}: {str(e)}")
            return {"error": f"Failed to get diff for {file_path}: {str(e)}"}

    @mcp.tool()
    async def get_untracked_files(
        ctx: Context,
        repository_path: str = Field(default=".", description="Path to git repository"),
        include_ignored: bool = Field(False, description="Include ignored files in the list"),
    ) -> dict[str, Any]:
        """Get list of untracked files.

        Returns all files that are not tracked by git, optionally including ignored files.
        """
        await ctx.info(f"Getting untracked files for: {repository_path}")

        repo_path = Path(repository_path).resolve()
        if not is_git_repository(repo_path):
            git_root = find_git_root(repo_path)
            if not git_root:
                await ctx.error(f"No git repository found at or above {repo_path}")
                return {"error": f"No git repository found at or above {repo_path}"}
            repo_path = git_root

        try:
            repo = LocalRepository(path=repo_path, name=repo_path.name, current_branch="main", head_commit="unknown")

            await ctx.debug("Detecting working directory changes to find untracked files")
            changes = await mcp.change_detector.detect_working_directory_changes(repo)

            untracked_files = [_format_file_status(f) for f in changes.untracked_files]

            await ctx.info(f"Found {len(untracked_files)} untracked files")

            return {
                "repository_path": str(repo_path),
                "untracked_count": len(untracked_files),
                "files": untracked_files,
            }

        except Exception as e:
            await ctx.error(f"Failed to get untracked files: {str(e)}")
            return {"error": f"Failed to get untracked files: {str(e)}"}


def _format_file_status(file_status: FileStatus) -> dict[str, Any]:
    """Format a FileStatus object for JSON serialization."""
    return {
        "path": file_status.path,
        "status": file_status.status_code,
        "status_description": file_status.status_description,
        "staged": file_status.staged,
        "lines_added": file_status.lines_added,
        "lines_deleted": file_status.lines_deleted,
        "total_changes": file_status.total_changes,
        "is_binary": file_status.is_binary,
        "old_path": file_status.old_path,
    }


async def _get_file_diffs(
    mcp: FastMCP, repo_path: Path, files: list[FileStatus], max_lines: int, ctx: Context
) -> list[dict[str, Any]]:
    """Get diffs for a list of files."""
    diffs = []
    total_files = len(files)

    for i, file_status in enumerate(files):
        try:
            await ctx.report_progress(i, total_files)

            if file_status.is_binary:
                await ctx.debug(f"Skipping binary file: {file_status.path}")
                diffs.append(
                    {"file_path": file_status.path, "is_binary": True, "message": "Binary file - no diff available"}
                )
                continue

            await ctx.debug(f"Getting diff for file: {file_status.path}")
            diff_content = await mcp.git_client.get_diff(
                repo_path, staged=file_status.staged, file_path=file_status.path
            )

            if diff_content.strip():
                # Truncate if too long
                lines = diff_content.split("\n")
                if len(lines) > max_lines:
                    diff_content = "\n".join(lines[:max_lines])
                    diff_content += "\n... (truncated)"

                diffs.append({"file_path": file_status.path, "diff_content": diff_content, "is_binary": False})

        except Exception as e:
            await ctx.warning(f"Failed to get diff for {file_status.path}: {str(e)}")
            diffs.append({"file_path": file_status.path, "error": f"Failed to get diff: {str(e)}"})

    await ctx.report_progress(total_files, total_files)
    return diffs
