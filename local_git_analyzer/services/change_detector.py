"""Service for detecting different types of git changes."""

import logging
from datetime import datetime

from fastmcp.server.dependencies import get_context

from ..models.changes import FileStatus, StagedChanges, StashedChanges, UnpushedCommit, WorkingDirectoryChanges
from ..models.repository import LocalRepository
from .git_client import GitClient


class ChangeDetector:
    """Service for detecting different types of git changes."""

    def __init__(self, git_client: GitClient):
        self.git_client = git_client
        self.logger = logging.getLogger(__name__)

    def _get_context(self):
        """Get FastMCP context if available."""
        try:
            return get_context()
        except RuntimeError:
            # No context available (e.g., during testing)
            return None

    async def detect_working_directory_changes(self, repo: LocalRepository) -> WorkingDirectoryChanges:
        """Detect uncommitted changes in working directory."""
        ctx = self._get_context()

        if ctx:
            await ctx.debug("Detecting working directory changes")

        try:
            status_info = await self.git_client.get_status(repo.path)

            # Initialize lists for different types of changes
            modified_files = []
            added_files = []
            deleted_files = []
            renamed_files = []
            untracked_files = []

            if ctx:
                await ctx.debug(f"Processing {len(status_info['files'])} file status entries")

            for file_info in status_info["files"]:
                # Create FileStatus object
                index_status = file_info.get("index_status")
                status_code = file_info["status_code"]

                # A file is staged only if it has index_status AND is not untracked
                is_staged = bool(index_status) and status_code != "?"

                file_status = FileStatus(
                    path=file_info["filename"],
                    status_code=file_info["status_code"],
                    working_tree_status=file_info.get("working_status"),
                    index_status=file_info.get("index_status"),
                    staged=is_staged,
                )

                # Categorize by status code
                if file_status.status_code == "M":
                    modified_files.append(file_status)
                elif file_status.status_code == "A":
                    added_files.append(file_status)
                elif file_status.status_code == "D":
                    deleted_files.append(file_status)
                elif file_status.status_code == "R":
                    renamed_files.append(file_status)
                elif file_status.status_code == "?":
                    untracked_files.append(file_status)
                # Handle other status codes by default behavior

            changes = WorkingDirectoryChanges(
                modified_files=modified_files,
                added_files=added_files,
                deleted_files=deleted_files,
                renamed_files=renamed_files,
                untracked_files=untracked_files,
            )

            if ctx:
                total_files = changes.total_files
                await ctx.debug(f"Detected working directory changes: {total_files} total files")
                if total_files > 0:
                    await ctx.info(
                        f"Working directory summary: "
                        f"{len(modified_files)} modified, "
                        f"{len(added_files)} added, "
                        f"{len(deleted_files)} deleted, "
                        f"{len(renamed_files)} renamed, "
                        f"{len(untracked_files)} untracked"
                    )

            return changes

        except Exception as e:
            if ctx:
                await ctx.error(f"Failed to detect working directory changes: {str(e)}")
            raise

    async def detect_staged_changes(self, repo: LocalRepository) -> StagedChanges:
        """Detect changes staged for commit."""
        ctx = self._get_context()

        if ctx:
            await ctx.debug("Detecting staged changes")

        try:
            status_info = await self.git_client.get_status(repo.path)

            staged_files = []

            if ctx:
                await ctx.debug(f"Processing {len(status_info['files'])} file status entries for staged changes")

            for file_info in status_info["files"]:
                # FIXED: Only include files that have index status (staged)
                # AND exclude untracked files (status_code "?")
                index_status = file_info.get("index_status")
                status_code = file_info.get("status_code", "")

                # A file is staged if:
                # 1. It has an index_status (something in the staging area)
                # 2. It's NOT an untracked file (status_code != "?")
                if index_status and status_code != "?":
                    file_status = FileStatus(
                        path=file_info["filename"],
                        status_code=index_status,  # Use index_status for staged files
                        staged=True,
                        index_status=index_status,
                        working_tree_status=file_info.get("working_status"),
                    )
                    staged_files.append(file_status)

            changes = StagedChanges(staged_files=staged_files)

            if ctx:
                if changes.ready_to_commit:
                    await ctx.info(f"Found {changes.total_staged} staged files ready for commit")
                    await ctx.debug(
                        f"Staged changes summary: "
                        f"{changes.total_additions} additions, "
                        f"{changes.total_deletions} deletions"
                    )
                else:
                    await ctx.debug("No staged changes found")

            return changes

        except Exception as e:
            if ctx:
                await ctx.error(f"Failed to detect staged changes: {str(e)}")
            raise

    async def detect_unpushed_commits(self, repo: LocalRepository) -> list[UnpushedCommit]:
        """Detect commits that haven't been pushed to remote."""
        ctx = self._get_context()

        if ctx:
            await ctx.debug("Detecting unpushed commits")

        try:
            commits_data = await self.git_client.get_unpushed_commits(repo.path)

            unpushed_commits = []

            if ctx:
                await ctx.debug(f"Processing {len(commits_data)} unpushed commits")

            for commit_data in commits_data:
                try:
                    # Parse the date string
                    date_str = commit_data["date"]
                    # Handle different date formats
                    try:
                        # Try ISO format with timezone
                        if "+" in date_str or "Z" in date_str:
                            commit_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        else:
                            # Try without timezone
                            commit_date = datetime.fromisoformat(date_str)
                    except ValueError:
                        # Fallback to current time if parsing fails
                        commit_date = datetime.now()
                        if ctx:
                            await ctx.warning(f"Failed to parse commit date: {date_str}")

                    unpushed_commit = UnpushedCommit(
                        sha=commit_data["sha"],
                        message=commit_data["message"],
                        author=commit_data["author"],
                        author_email=commit_data["email"],
                        date=commit_date,
                        files_changed=[],  # TODO: Get changed files if needed
                        insertions=0,  # TODO: Get stats if needed
                        deletions=0,  # TODO: Get stats if needed
                    )
                    unpushed_commits.append(unpushed_commit)

                except (KeyError, ValueError) as e:
                    if ctx:
                        await ctx.warning(f"Failed to parse commit data: {e}")
                    continue

            if ctx:
                if unpushed_commits:
                    # Removed unused variable 'authors'
                    await ctx.info(f"Found {len(unpushed_commits)} unpushed commits")

                    # Log commit summary
                    recent_commits = unpushed_commits[:3]  # Show first 3
                    for commit in recent_commits:
                        await ctx.debug(f"Unpushed: {commit.short_sha} - {commit.short_message}")
                else:
                    await ctx.debug("No unpushed commits found")

            return unpushed_commits

        except Exception as e:
            if ctx:
                await ctx.error(f"Failed to detect unpushed commits: {str(e)}")
            raise

    async def detect_stashed_changes(self, repo: LocalRepository) -> list[StashedChanges]:
        """Detect stashed changes."""
        ctx = self._get_context()

        if ctx:
            await ctx.debug("Detecting stashed changes")

        try:
            stashes_data = await self.git_client.get_stash_list(repo.path)

            stashed_changes = []

            if ctx:
                await ctx.debug(f"Processing {len(stashes_data)} stashed changes")

            for stash_data in stashes_data:
                try:
                    # Parse stash creation date (approximate)
                    try:
                        # Try to parse relative date (e.g., "2 hours ago")
                        # For now, just use current time as approximation
                        stash_date = datetime.now()
                    except Exception:
                        stash_date = datetime.now()

                    stashed_change = StashedChanges(
                        stash_index=stash_data["index"],
                        message=stash_data["message"],
                        branch=repo.current_branch,  # Approximate - stash doesn't store original branch
                        date=stash_date,
                        files_affected=[],  # TODO: Get affected files if needed
                    )
                    stashed_changes.append(stashed_change)

                except (KeyError, ValueError) as e:
                    if ctx:
                        await ctx.warning(f"Failed to parse stash data: {e}")
                    continue

            if ctx:
                if stashed_changes:
                    await ctx.info(f"Found {len(stashed_changes)} stashed changes")
                    for stash in stashed_changes[:3]:  # Show first 3
                        await ctx.debug(f"Stash {stash.stash_index}: {stash.message}")
                else:
                    await ctx.debug("No stashed changes found")

            return stashed_changes

        except Exception as e:
            if ctx:
                await ctx.error(f"Failed to detect stashed changes: {str(e)}")
            raise
