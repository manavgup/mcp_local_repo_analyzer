"""FastMCP tools for working directory analysis with enhanced return types."""

import time
from pathlib import Path
from typing import Any

from fastmcp import Context, FastMCP
from mcp_shared_lib.models import FileStatus, LocalRepository
from mcp_shared_lib.utils import find_git_root, is_git_repository
from pydantic import Field


def register_working_directory_tools(mcp: FastMCP) -> None:
    """Register enhanced working directory analysis tools."""

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

        **Return Type**: Dict with WorkingDirectoryChanges structure
        ```python
        {
            "repository_path": str,           # Pass to other repository tools
            "total_files_changed": int,       # Use for conditional workflow logic
            "has_changes": bool,              # Use to determine if staging/commit tools should run
            "summary": {                      # Change counts for analysis routing
                "modified": int, "added": int, "deleted": int,
                "renamed": int, "untracked": int
            },
            "files": {                        # Categorized file lists for targeted analysis
                "modified": List[FileStatus], "added": List[FileStatus],
                "deleted": List[FileStatus], "renamed": List[FileStatus],
                "untracked": List[FileStatus]
            },
            "diffs": List[dict] | None        # Diff content if include_diffs=True
        }
        ```

        **Key Fields for Chaining**:
        - `has_changes` (bool): Use to determine if staging/commit tools should be called
        - `repository_path` (str): Pass to other repository analysis tools
        - `total_files_changed` (int): Use for conditional workflow logic
        - `files.modified` (list): Get specific file types for targeted analysis
        - `summary` (dict): Change type counts for analysis routing

        **Common Chaining Patterns**:
        ```python
        # Basic workflow decision
        wd_result = await analyze_working_directory(repo_path)
        if wd_result["has_changes"]:
            staged_result = await analyze_staged_changes(wd_result["repository_path"])

        # Risk-based routing
        if wd_result["total_files_changed"] > 10:
            validation = await validate_staged_changes(wd_result["repository_path"])

        # File-specific analysis
        for file_info in wd_result["files"]["modified"]:
            if file_info["total_changes"] > 100:
                diff_result = await get_file_diff(file_info["path"], wd_result["repository_path"])
        ```

        **Decision Points**:
        - `has_changes=True`: Repository has work → analyze staging status
        - `total_files_changed > 10`: Many changes → run validation
        - `summary.untracked > 0`: New files → check if should be staged
        - `files.modified`: Modified files → get detailed diffs if needed
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

            # Detect working directory changes - returns WorkingDirectoryChanges model
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

        **Return Type**: Dict with FileDiff structure
        ```python
        {
            "file_path": str,                 # Path to analyzed file
            "old_path": str | None,           # Original path if renamed
            "has_changes": bool,              # Whether file has changes - use for conditional processing
            "is_binary": bool,                # Whether file is binary - affects diff availability
            "is_large_change": bool,          # Whether change >100 lines - use for review prioritization
            "statistics": {                   # Line change statistics for impact assessment
                "lines_added": int, "lines_deleted": int, "total_changes": int
            },
            "hunks": int,                     # Number of diff hunks - indicates complexity
            "diff_content": str               # Actual diff content for code review
        }
        ```

        **Key Fields for Chaining**:
        - `has_changes` (bool): Whether file actually has changes
        - `is_large_change` (bool): Whether change is >100 lines (use for review prioritization)
        - `is_binary` (bool): Whether file is binary (affects further text analysis)
        - `statistics.total_changes` (int): Total line changes for impact assessment
        - `diff_content` (str): Actual diff for code review tools

        **Common Chaining Patterns**:
        ```python
        # Check if file needs detailed review
        diff_result = await get_file_diff("src/main.py", repo_path)
        if diff_result["is_large_change"]:
            validation = await validate_staged_changes(repo_path)

        # Route based on file type
        if not diff_result["is_binary"]:
            # Can do text-based analysis on diff_result["diff_content"]
            pass

        # Impact-based decisions
        if diff_result["statistics"]["total_changes"] > 50:
            # Large change - might need extra validation
            pass
        ```

        **Decision Points**:
        - `has_changes=False`: No diff content → skip further analysis
        - `is_binary=True`: Binary file → skip text-based tools
        - `is_large_change=True`: Large change → trigger validation workflows
        - `statistics.total_changes > X`: Impact-based routing
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

            # Parse diff using existing FileDiff model
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

        **Return Type**: Dict with untracked file information
        ```python
        {
            "repository_path": str,           # Path to analyzed repository
            "untracked_count": int,           # Number of untracked files (>0 means new work)
            "files": List[FileStatus]         # List of untracked file information
        }
        ```

        **Key Fields for Chaining**:
        - `untracked_count` (int): Number of untracked files (>0 means new work exists)
        - `repository_path` (str): Pass to other repository tools
        - `files` (list): Individual file information for iteration

        **Common Chaining Patterns**:
        ```python
        # Check for new work
        untracked_result = await get_untracked_files(repo_path)
        if untracked_result["untracked_count"] > 0:
            # Has new files - analyze working directory for staging decisions
            wd_result = await analyze_working_directory(untracked_result["repository_path"])

        # Process individual files
        for file_info in untracked_result["files"]:
            if not file_info["is_binary"]:
                # Can analyze text files further
                pass
        ```

        **Decision Points**:
        - `untracked_count > 0`: New files exist → check if should be staged
        - `untracked_count == 0`: No new files → focus on modified files
        - Individual files can be analyzed for staging decisions
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
