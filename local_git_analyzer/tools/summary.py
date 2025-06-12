"""FastMCP tools for comprehensive analysis and summaries."""

import time
from pathlib import Path
from typing import Any

from fastmcp import Context, FastMCP
from pydantic import Field

from ..models.repository import LocalRepository
from ..utils import find_git_root, is_git_repository


def register_summary_tools(mcp: FastMCP):
    """Register summary and analysis tools."""

    @mcp.tool()
    async def get_outstanding_summary(
        ctx: Context,
        repository_path: str = Field(default=".", description="Path to git repository"),
        detailed: bool = Field(True, description="Include detailed analysis and recommendations"),
    ) -> dict[str, Any]:
        """Get comprehensive summary of all outstanding changes.

        Provides a complete overview of working directory changes, staged changes,
        unpushed commits, stashed changes, and overall repository health.
        """
        start_time = time.time()
        await ctx.info(f"Starting comprehensive repository analysis for: {repository_path}")

        repo_path = Path(repository_path).resolve()
        if not is_git_repository(repo_path):
            git_root = find_git_root(repo_path)
            if not git_root:
                await ctx.error(f"No git repository found at or above {repo_path}")
                return {"error": f"No git repository found at or above {repo_path}"}
            repo_path = git_root
            await ctx.debug(f"Found git repository at: {repo_path}")

        try:
            await ctx.report_progress(0, 6)
            await ctx.debug("Getting branch information")

            # Get branch info
            branch_info = await mcp.git_client.get_branch_info(repo_path)

            await ctx.report_progress(1, 6)
            await ctx.debug("Creating repository model")

            repo = LocalRepository(
                path=repo_path,
                name=repo_path.name,
                current_branch=branch_info.get("current_branch", "main"),
                head_commit="unknown",
            )

            await ctx.report_progress(2, 6)
            await ctx.info("Analyzing all repository components...")

            # Get complete repository status
            repo_status = await mcp.status_tracker.get_repository_status(repo)

            await ctx.report_progress(3, 6)
            await ctx.debug("Categorizing and analyzing file changes")

            # Analyze all files together for categorization and risk
            all_changed_files = repo_status.working_directory.all_files + repo_status.staged_changes.staged_files

            await ctx.debug(f"Analyzing {len(all_changed_files)} total changed files")
            categories = mcp.diff_analyzer.categorize_changes(all_changed_files)
            risk_assessment = mcp.diff_analyzer.assess_risk(all_changed_files)

            await ctx.report_progress(4, 6)
            await ctx.debug("Generating recommendations and summary")

            # Generate recommendations
            recommendations = _generate_recommendations(repo_status, risk_assessment, categories)

            # Create summary text
            summary_text = _create_summary_text(repo_status, risk_assessment, categories)

            await ctx.report_progress(5, 6)
            await ctx.debug("Compiling final results")

            result = {
                "repository_path": str(repo_path),
                "repository_name": repo.name,
                "current_branch": repo_status.branch_status.current_branch,
                "analysis_timestamp": "now",
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
                    "level": risk_assessment.risk_level,
                    "score": risk_assessment.risk_score,
                    "factors": risk_assessment.risk_factors,
                    "large_changes": len(risk_assessment.large_changes),
                    "potential_conflicts": len(risk_assessment.potential_conflicts),
                },
                "recommendations": recommendations,
            }

            if detailed:
                await ctx.debug("Adding detailed breakdown to results")
                result.update(
                    {
                        "detailed_breakdown": {
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
                    }
                )

            await ctx.report_progress(6, 6)
            duration = time.time() - start_time

            # Log summary insights
            if repo_status.has_outstanding_work:
                await ctx.info(f"Analysis complete: {repo_status.total_outstanding_changes} outstanding changes found")
                if risk_assessment.risk_level == "high":
                    await ctx.warning("High-risk changes detected - review carefully before proceeding")
                elif len(repo_status.unpushed_commits) > 10:
                    await ctx.warning(
                        f"Many unpushed commits ({len(repo_status.unpushed_commits)}) - consider pushing soon"
                    )
            else:
                await ctx.info("Repository is clean - no outstanding changes detected")

            await ctx.info(f"Comprehensive analysis completed in {duration:.2f} seconds")
            return result

        except Exception as e:
            duration = time.time() - start_time
            await ctx.error(f"Comprehensive analysis failed after {duration:.2f} seconds: {str(e)}")
            return {"error": f"Failed to get outstanding summary: {str(e)}"}

    @mcp.tool()
    async def analyze_repository_health(
        ctx: Context,
        repository_path: str = Field(default=".", description="Path to git repository"),
    ) -> dict[str, Any]:
        """Analyze overall repository health and status.

        Provides a health check of the repository including sync status,
        outstanding work, and potential issues that need attention.
        """
        start_time = time.time()
        await ctx.info(f"Starting repository health analysis for: {repository_path}")

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

            await ctx.debug("Gathering health metrics")
            health_metrics = await mcp.status_tracker.get_health_metrics(repo)

            await ctx.debug("Calculating health score")
            # Determine overall health score (0-100)
            health_score = 100
            issues = []

            if health_metrics["has_uncommitted_changes"]:
                health_score -= 20
                issues.append("Uncommitted changes in working directory")
                await ctx.warning("Uncommitted changes detected")

            if health_metrics["unpushed_commits_count"] > 5:
                health_score -= 15
                issues.append(f"{health_metrics['unpushed_commits_count']} unpushed commits")
                await ctx.warning(f"Many unpushed commits: {health_metrics['unpushed_commits_count']}")
            elif health_metrics["unpushed_commits_count"] > 0:
                health_score -= 5

            if health_metrics["stashed_changes_count"] > 0:
                health_score -= 10
                issues.append(f"{health_metrics['stashed_changes_count']} stashed changes")
                await ctx.info(f"Stashed changes present: {health_metrics['stashed_changes_count']}")

            if "behind" in health_metrics["branch_sync_status"]:
                health_score -= 15
                issues.append("Branch is behind remote")
                await ctx.warning("Branch is behind remote")

            if "diverged" in health_metrics["branch_sync_status"]:
                health_score -= 25
                issues.append("Branch has diverged from remote")
                await ctx.error("Branch has diverged from remote")

            # Determine health status
            if health_score >= 90:
                health_status = "excellent"
            elif health_score >= 75:
                health_status = "good"
            elif health_score >= 50:
                health_status = "fair"
            else:
                health_status = "needs_attention"

            duration = time.time() - start_time
            await ctx.info(f"Health analysis complete: {health_status} ({health_score}/100) in {duration:.2f} seconds")

            return {
                "repository_path": str(repo_path),
                "health_score": max(0, health_score),
                "health_status": health_status,
                "issues": issues,
                "metrics": health_metrics,
                "recommendations": _generate_health_recommendations(health_metrics, issues),
            }

        except Exception as e:
            duration = time.time() - start_time
            await ctx.error(f"Repository health analysis failed after {duration:.2f} seconds: {str(e)}")
            return {"error": f"Failed to analyze repository health: {str(e)}"}

    @mcp.tool()
    async def get_push_readiness(
        ctx: Context,
        repository_path: str = Field(default=".", description="Path to git repository"),
    ) -> dict[str, Any]:
        """Assess if repository is ready for push to remote.

        Checks if the repository state is suitable for pushing to remote,
        including checking for uncommitted changes, conflicts, and other blockers.
        """
        await ctx.info(f"Assessing push readiness for: {repository_path}")

        repo_path = Path(repository_path).resolve()
        if not is_git_repository(repo_path):
            git_root = find_git_root(repo_path)
            if not git_root:
                await ctx.error(f"No git repository found at or above {repo_path}")
                return {"error": f"No git repository found at or above {repo_path}"}
            repo_path = git_root

        try:
            await ctx.debug("Getting branch information")
            branch_info = await mcp.git_client.get_branch_info(repo_path)

            await ctx.debug("Creating repository model")
            repo = LocalRepository(
                path=repo_path,
                name=repo_path.name,
                current_branch=branch_info.get("current_branch", "main"),
                head_commit="unknown",
            )

            await ctx.debug("Getting repository status for push readiness check")
            repo_status = await mcp.status_tracker.get_repository_status(repo, ctx)

            await ctx.debug("Checking push readiness criteria")
            # Check readiness criteria
            blockers = []
            warnings = []

            # Check for uncommitted changes
            if repo_status.working_directory.has_changes:
                blocker_msg = "Uncommitted changes in working directory"
                blockers.append(blocker_msg)
                await ctx.warning(blocker_msg)

            # Check for staged changes
            if repo_status.staged_changes.ready_to_commit:
                blocker_msg = "Staged changes not yet committed"
                blockers.append(blocker_msg)
                await ctx.warning(blocker_msg)

            # Check if there are commits to push
            has_commits_to_push = len(repo_status.unpushed_commits) > 0
            if not has_commits_to_push:
                warning_msg = "No new commits to push"
                warnings.append(warning_msg)
                await ctx.info(warning_msg)

            # Check if behind remote
            if repo_status.branch_status.behind_by > 0:
                blocker_msg = f"Branch is {repo_status.branch_status.behind_by} commits behind remote"
                blockers.append(blocker_msg)
                await ctx.warning(blocker_msg)

            # Check for stashed changes (warning, not blocker)
            if repo_status.stashed_changes:
                warning_msg = f"{len(repo_status.stashed_changes)} stashed changes present"
                warnings.append(warning_msg)
                await ctx.info(warning_msg)

            # Determine readiness
            is_ready = len(blockers) == 0 and has_commits_to_push

            await ctx.debug("Generating action plan")
            # Generate action plan
            action_plan = []
            if blockers:
                if "Uncommitted changes" in str(blockers):
                    action_plan.append("Commit or stash uncommitted changes")
                if "Staged changes" in str(blockers):
                    action_plan.append("Commit staged changes")
                if "behind remote" in str(blockers):
                    action_plan.append("Pull latest changes from remote")
            elif has_commits_to_push:
                action_plan.append("Ready to push!")
            else:
                action_plan.append("No commits to push")

            readiness_status = "READY" if is_ready else "NOT READY"
            await ctx.info(f"Push readiness assessment: {readiness_status}")

            return {
                "repository_path": str(repo_path),
                "branch": repo_status.branch_status.current_branch,
                "ready_to_push": is_ready,
                "has_commits_to_push": has_commits_to_push,
                "unpushed_commits": len(repo_status.unpushed_commits),
                "blockers": blockers,
                "warnings": warnings,
                "action_plan": action_plan,
                "branch_status": {
                    "ahead_by": repo_status.branch_status.ahead_by,
                    "behind_by": repo_status.branch_status.behind_by,
                    "upstream": repo_status.branch_status.upstream_branch,
                },
            }

        except Exception as e:
            await ctx.error(f"Failed to assess push readiness: {str(e)}")
            return {"error": f"Failed to assess push readiness: {str(e)}"}

    @mcp.tool()
    async def analyze_stashed_changes(
        ctx: Context,
        repository_path: str = Field(default=".", description="Path to git repository"),
    ) -> dict[str, Any]:
        """Analyze stashed changes.

        Provides information about all stashed changes in the repository,
        including when they were created and what files they affect.
        """
        await ctx.info(f"Analyzing stashed changes for: {repository_path}")

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

            await ctx.debug("Detecting stashed changes")
            stashed_changes = await mcp.change_detector.detect_stashed_changes(repo, ctx)

            if not stashed_changes:
                await ctx.info("No stashed changes found")
                return {
                    "repository_path": str(repo_path),
                    "has_stashes": False,
                    "total_stashes": 0,
                    "message": "No stashed changes found",
                }

            await ctx.info(f"Found {len(stashed_changes)} stashed changes")
            await ctx.debug("Processing stash information")

            stashes_data = []
            for stash in stashed_changes:
                stash_data = {
                    "index": stash.stash_index,
                    "name": stash.stash_name,
                    "message": stash.message,
                    "branch": stash.branch,
                    "date": stash.date.isoformat(),
                    "files_affected": stash.files_affected,
                }
                stashes_data.append(stash_data)

            return {
                "repository_path": str(repo_path),
                "has_stashes": True,
                "total_stashes": len(stashed_changes),
                "stashes": stashes_data,
                "recommendations": [
                    "Review and apply relevant stashes",
                    "Clean up old stashes that are no longer needed",
                    "Consider committing stashed changes if they're ready",
                ],
            }

        except Exception as e:
            await ctx.error(f"Failed to analyze stashed changes: {str(e)}")
            return {"error": f"Failed to analyze stashed changes: {str(e)}"}

    @mcp.tool()
    async def detect_conflicts(
        ctx: Context,
        repository_path: str = Field(default=".", description="Path to git repository"),
        target_branch: str = Field("main", description="Branch to check conflicts against"),
    ) -> dict[str, Any]:
        """Detect potential merge conflicts.

        Analyzes potential conflicts that might occur when merging
        the current branch with the target branch.
        """
        await ctx.info(f"Detecting potential conflicts with branch '{target_branch}' for: {repository_path}")

        repo_path = Path(repository_path).resolve()
        if not is_git_repository(repo_path):
            git_root = find_git_root(repo_path)
            if not git_root:
                await ctx.error(f"No git repository found at or above {repo_path}")
                return {"error": f"No git repository found at or above {repo_path}"}
            repo_path = git_root

        try:
            await ctx.debug("Getting branch information")
            branch_info = await mcp.git_client.get_branch_info(repo_path)
            current_branch = branch_info.get("current_branch", "main")

            if current_branch == target_branch:
                await ctx.info("Already on target branch - no conflicts to check")
                return {
                    "repository_path": str(repo_path),
                    "current_branch": current_branch,
                    "target_branch": target_branch,
                    "has_conflicts": False,
                    "message": "Cannot check conflicts - already on target branch",
                }

            await ctx.debug("Creating repository model")
            repo = LocalRepository(
                path=repo_path, name=repo_path.name, current_branch=current_branch, head_commit="unknown"
            )

            await ctx.debug("Getting working directory and staged changes")
            # Get working directory and staged changes
            working_changes = await mcp.change_detector.detect_working_directory_changes(repo)
            staged_changes = await mcp.change_detector.detect_staged_changes(repo)

            await ctx.debug("Analyzing potential conflicts")
            # Simple conflict detection based on file changes
            all_files = working_changes.all_files + staged_changes.staged_files

            # Assess risk of conflicts
            risk_assessment = mcp.diff_analyzer.assess_risk(all_files)
            potential_conflicts = risk_assessment.potential_conflicts

            await ctx.debug("Applying conflict detection heuristics")
            # Additional heuristics for conflict detection
            high_risk_files = []
            for file_status in all_files:
                if (
                    file_status.total_changes > 50
                    or file_status.status_code in ["R", "C"]
                    or file_status.path.endswith((".json", ".xml", ".yaml", ".yml"))
                ):
                    high_risk_files.append(file_status.path)

            has_potential_conflicts = len(potential_conflicts) > 0 or len(high_risk_files) > 0

            if has_potential_conflicts:
                await ctx.warning(
                    f"Potential conflicts detected: {len(potential_conflicts)} direct conflicts, \
                                  {len(high_risk_files)} high-risk files"
                )
            else:
                await ctx.info("No obvious conflict risks detected")

            return {
                "repository_path": str(repo_path),
                "current_branch": current_branch,
                "target_branch": target_branch,
                "has_potential_conflicts": has_potential_conflicts,
                "potential_conflict_files": potential_conflicts,
                "high_risk_files": high_risk_files,
                "risk_level": risk_assessment.risk_level,
                "total_changed_files": len(all_files),
                "recommendations": [
                    "Test merge in a separate branch first" if has_potential_conflicts else None,
                    "Commit all changes before merging" if working_changes.has_changes else None,
                    "Pull latest changes from target branch" if target_branch != current_branch else None,
                    "Review large file changes carefully" if risk_assessment.large_changes else None,
                ],
            }

        except Exception as e:
            await ctx.error(f"Failed to detect conflicts: {str(e)}")
            return {"error": f"Failed to detect conflicts: {str(e)}"}


def _generate_recommendations(repo_status, risk_assessment, categories) -> list[str]:
    """Generate recommendations based on repository status."""
    recommendations = []

    # Working directory recommendations
    if repo_status.working_directory.has_changes:
        if risk_assessment.risk_level == "high":
            recommendations.append("⚠️  Review high-risk changes carefully before committing")
        recommendations.append("📝 Commit working directory changes when ready")

    # Staged changes recommendations
    if repo_status.staged_changes.ready_to_commit:
        recommendations.append("✅ Commit staged changes")

    # Unpushed commits recommendations
    if len(repo_status.unpushed_commits) > 0:
        if len(repo_status.unpushed_commits) > 5:
            recommendations.append("🚀 Push commits to remote (many commits waiting)")
        else:
            recommendations.append("🚀 Push commits to remote when ready")

    # Branch sync recommendations
    if repo_status.branch_status.behind_by > 0:
        recommendations.append("⬇️  Pull latest changes from remote")

    # Stash recommendations
    if len(repo_status.stashed_changes) > 0:
        recommendations.append("📦 Review and apply/clean up stashed changes")

    # File category recommendations
    if categories.has_critical_changes:
        recommendations.append("🔍 Extra review needed for critical file changes")

    if len(categories.source_code) > 0 and len(categories.tests) == 0:
        recommendations.append("🧪 Consider adding tests for code changes")

    return recommendations


def _create_summary_text(repo_status, risk_assessment, categories) -> str:
    """Create a human-readable summary text."""
    parts = []

    # Overall status
    if not repo_status.has_outstanding_work:
        return "✅ Repository is clean - no outstanding changes detected."

    # Working directory
    if repo_status.working_directory.has_changes:
        wd = repo_status.working_directory
        parts.append(f"📝 {wd.total_files} file(s) with uncommitted changes")

    # Staged changes
    if repo_status.staged_changes.ready_to_commit:
        parts.append(f"📋 {repo_status.staged_changes.total_staged} file(s) staged for commit")

    # Unpushed commits
    if len(repo_status.unpushed_commits) > 0:
        parts.append(f"🚀 {len(repo_status.unpushed_commits)} unpushed commit(s)")

    # Branch status
    if not repo_status.branch_status.is_up_to_date:
        parts.append(f"🔄 Branch {repo_status.branch_status.sync_status}")

    # Risk assessment
    if risk_assessment.risk_level == "high":
        parts.append("⚠️  High-risk changes detected")
    elif risk_assessment.risk_level == "medium":
        parts.append("⚡ Medium-risk changes detected")

    return " | ".join(parts) if parts else "Repository has outstanding work."


def _generate_health_recommendations(health_metrics, issues) -> list[str]:
    """Generate health improvement recommendations."""
    recommendations = []

    for issue in issues:
        if "uncommitted changes" in issue.lower():
            recommendations.append("Commit or stash uncommitted changes")
        elif "unpushed commits" in issue.lower():
            recommendations.append("Push commits to remote repository")
        elif "stashed changes" in issue.lower():
            recommendations.append("Review and clean up stashed changes")
        elif "behind remote" in issue.lower():
            recommendations.append("Pull latest changes from remote")
        elif "diverged" in issue.lower():
            recommendations.append("Resolve branch divergence (merge or rebase)")

    if not recommendations:
        recommendations.append("Repository health is good!")

    return recommendations
