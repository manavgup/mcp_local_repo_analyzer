"""FastMCP tools for staging area analysis."""

import time
from pathlib import Path
from typing import Any

from fastmcp import Context, FastMCP
from pydantic import Field

from ..models.repository import LocalRepository
from ..utils import find_git_root, is_git_repository


def register_staging_area_tools(mcp: FastMCP):
    """Register staging area analysis tools."""

    @mcp.tool()
    async def analyze_staged_changes(
        ctx: Context,
        repository_path: str = Field(default=".", description="Path to git repository"),
        include_diffs: bool = Field(True, description="Include diff content for staged files"),
    ) -> dict[str, Any]:
        """Analyze changes staged for commit.

        Returns information about all files that have been staged (added to index)
        and are ready to be committed.
        """
        start_time = time.time()
        await ctx.info(f"Starting staged changes analysis for: {repository_path}")

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

            repo = LocalRepository(path=repo_path, name=repo_path.name, current_branch="main", head_commit="unknown")

            await ctx.report_progress(1, 4)
            await ctx.debug("Detecting staged changes")

            staged_changes = await mcp.change_detector.detect_staged_changes(repo)

            await ctx.report_progress(2, 4)
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
                ],
            }

            # Add diffs if requested
            if include_diffs and staged_changes.staged_files:
                await ctx.debug(f"Generating diffs for {min(10, len(staged_changes.staged_files))} staged files")
                diffs = []
                files_to_process = staged_changes.staged_files[:10]  # Limit to 10 files

                for i, file_status in enumerate(files_to_process):
                    await ctx.report_progress(2.5 + (i / len(files_to_process)) * 0.5, 4)

                    try:
                        if file_status.is_binary:
                            await ctx.debug(f"Skipping binary file: {file_status.path}")
                            diffs.append(
                                {
                                    "file_path": file_status.path,
                                    "is_binary": True,
                                    "message": "Binary file - no diff available",
                                }
                            )
                            continue

                        await ctx.debug(f"Getting staged diff for: {file_status.path}")
                        diff_content = await mcp.git_client.get_diff(repo_path, staged=True, file_path=file_status.path)

                        # Truncate long diffs
                        lines = diff_content.split("\n")
                        if len(lines) > 100:
                            diff_content = "\n".join(lines[:100]) + "\n... (truncated)"
                            await ctx.debug(f"Truncated diff for {file_status.path} from {len(lines)} to 100 lines")

                        diffs.append({"file_path": file_status.path, "diff_content": diff_content})

                    except Exception as e:
                        await ctx.warning(f"Failed to get diff for {file_status.path}: {str(e)}")
                        diffs.append({"file_path": file_status.path, "error": f"Failed to get diff: {str(e)}"})

                result["diffs"] = diffs

            await ctx.report_progress(4, 4)
            duration = time.time() - start_time
            await ctx.info(f"Staged changes analysis completed in {duration:.2f} seconds")

            return result

        except Exception as e:
            duration = time.time() - start_time
            await ctx.error(f"Staged changes analysis failed after {duration:.2f} seconds: {str(e)}")
            return {"error": f"Failed to analyze staged changes: {str(e)}"}

    @mcp.tool()
    async def preview_commit(
        ctx: Context,
        repository_path: str = Field(default=".", description="Path to git repository"),
    ) -> dict[str, Any]:
        """Preview what would be committed.

        Shows a summary of staged changes that would be included in the next commit.
        """
        await ctx.info(f"Previewing commit for: {repository_path}")

        repo_path = Path(repository_path).resolve()
        if not is_git_repository(repo_path):
            git_root = find_git_root(repo_path)
            if not git_root:
                await ctx.error(f"No git repository found at or above {repo_path}")
                return {"error": f"No git repository found at or above {repo_path}"}
            repo_path = git_root

        try:
            await ctx.debug("Creating repository model")
            repo = LocalRepository(path=repo_path, name=repo_path.name, current_branch="main", head_commit="unknown")

            await ctx.debug("Detecting staged changes")
            staged_changes = await mcp.change_detector.detect_staged_changes(repo)

            if not staged_changes.ready_to_commit:
                await ctx.info("No changes staged for commit")
                return {
                    "repository_path": str(repo_path),
                    "ready_to_commit": False,
                    "message": "No changes staged for commit",
                }

            await ctx.debug("Categorizing staged changes")
            # Categorize changes
            categories = mcp.diff_analyzer.categorize_changes(staged_changes.staged_files)

            await ctx.debug("Analyzing file types")
            # Get file types
            file_types = {}
            for file_status in staged_changes.staged_files:
                ext = Path(file_status.path).suffix.lower() or "no_extension"
                file_types[ext] = file_types.get(ext, 0) + 1

            await ctx.info(
                f"Commit preview ready: {staged_changes.total_staged} files, \
                           {categories.total_files} categorized"
            )

            return {
                "repository_path": str(repo_path),
                "ready_to_commit": True,
                "summary": {
                    "total_files": staged_changes.total_staged,
                    "total_additions": staged_changes.total_additions,
                    "total_deletions": staged_changes.total_deletions,
                },
                "file_categories": {
                    "critical_files": len(categories.critical_files),
                    "source_code": len(categories.source_code),
                    "documentation": len(categories.documentation),
                    "tests": len(categories.tests),
                    "configuration": len(categories.configuration),
                    "other": len(categories.other),
                },
                "file_types": file_types,
                "files_by_status": {
                    "added": [f.path for f in staged_changes.staged_files if f.status_code == "A"],
                    "modified": [f.path for f in staged_changes.staged_files if f.status_code == "M"],
                    "deleted": [f.path for f in staged_changes.staged_files if f.status_code == "D"],
                    "renamed": [f.path for f in staged_changes.staged_files if f.status_code == "R"],
                },
            }

        except Exception as e:
            await ctx.error(f"Failed to preview commit: {str(e)}")
            return {"error": f"Failed to preview commit: {str(e)}"}

    @mcp.tool()
    async def validate_staged_changes(
        ctx: Context,
        repository_path: str = Field(default=".", description="Path to git repository"),
    ) -> dict[str, Any]:
        """Validate staged changes for common issues.

        Checks staged changes for potential problems like large files,
        critical file changes, or other issues before committing.
        """
        start_time = time.time()
        await ctx.info(f"Starting staged changes validation for: {repository_path}")

        repo_path = Path(repository_path).resolve()
        if not is_git_repository(repo_path):
            git_root = find_git_root(repo_path)
            if not git_root:
                await ctx.error(f"No git repository found at or above {repo_path}")
                return {"error": f"No git repository found at or above {repo_path}"}
            repo_path = git_root

        try:
            await ctx.debug("Creating repository model")
            repo = LocalRepository(path=repo_path, name=repo_path.name, current_branch="main", head_commit="unknown")

            await ctx.debug("Detecting staged changes")
            staged_changes = await mcp.change_detector.detect_staged_changes(repo)

            if not staged_changes.ready_to_commit:
                await ctx.info("No changes staged for commit - validation not applicable")
                return {"repository_path": str(repo_path), "valid": False, "message": "No changes staged for commit"}

            await ctx.debug("Performing risk assessment")
            # Perform validation
            risk_assessment = mcp.diff_analyzer.assess_risk(staged_changes.staged_files)

            await ctx.debug("Categorizing changes for validation")
            categories = mcp.diff_analyzer.categorize_changes(staged_changes.staged_files)

            warnings = []
            errors = []

            # Check for high-risk changes
            if risk_assessment.is_high_risk:
                warning_msg = f"High-risk changes detected: {', '.join(risk_assessment.risk_factors)}"
                warnings.append(warning_msg)
                await ctx.warning(warning_msg)

            # Check for large changes
            if risk_assessment.large_changes:
                warning_msg = f"Large changes in {len(risk_assessment.large_changes)} files"
                warnings.append(warning_msg)
                await ctx.warning(warning_msg)

            # Check for critical files
            if categories.has_critical_changes:
                warning_msg = f"Critical files changed: {len(categories.critical_files)}"
                warnings.append(warning_msg)
                await ctx.warning(warning_msg)

            # Check for binary files
            binary_files = [f.path for f in staged_changes.staged_files if f.is_binary]
            if binary_files:
                warning_msg = f"Binary files included: {len(binary_files)}"
                warnings.append(warning_msg)
                await ctx.warning(warning_msg)

            # Check for potential conflicts
            if risk_assessment.potential_conflicts:
                error_msg = f"Potential conflicts detected in: {', '.join(risk_assessment.potential_conflicts)}"
                errors.append(error_msg)
                await ctx.error(error_msg)

            # Overall validation result
            is_valid = len(errors) == 0

            duration = time.time() - start_time
            await ctx.info(f"Validation completed in {duration:.2f} seconds - {'VALID' if is_valid else 'INVALID'}")

            return {
                "repository_path": str(repo_path),
                "valid": is_valid,
                "risk_level": risk_assessment.risk_level,
                "risk_score": risk_assessment.risk_score,
                "warnings": warnings,
                "errors": errors,
                "recommendations": [
                    "Review large changes carefully before committing" if risk_assessment.large_changes else None,
                    "Double-check critical file changes" if categories.has_critical_changes else None,
                    "Consider splitting large commits into smaller ones" if staged_changes.total_staged > 10 else None,
                    "Add tests for new functionality" if categories.source_code and not categories.tests else None,
                ],
                "summary": {
                    "total_files": staged_changes.total_staged,
                    "high_risk_files": len(risk_assessment.large_changes),
                    "critical_files": len(categories.critical_files),
                    "binary_files": len(binary_files),
                },
            }

        except Exception as e:
            duration = time.time() - start_time
            await ctx.error(f"Staged changes validation failed after {duration:.2f} seconds: {str(e)}")
            return {"error": f"Failed to validate staged changes: {str(e)}"}
