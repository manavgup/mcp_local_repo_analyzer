"""Git command execution client with error handling."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from fastmcp.server.dependencies import get_context

from ..config import GitAnalyzerSettings


class GitCommandError(Exception):
    """Exception raised when git command fails."""

    def __init__(self, command: list[str], return_code: int, stderr: str):
        self.command = command
        self.return_code = return_code
        self.stderr = stderr
        super().__init__(f"Git command failed: {' '.join(command)}\nError: {stderr}")


class GitClient:
    """Git command execution client with error handling."""

    def __init__(self, settings: GitAnalyzerSettings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)

    def _get_context(self):
        """Get FastMCP context if available."""
        try:
            return get_context()
        except RuntimeError:
            # No context available (e.g., during testing)
            return None

    async def execute_command(self, repo_path: Path, command: list[str], check: bool = True) -> str:
        """Execute a git command in the given repository."""
        ctx = self._get_context()
        full_command = ["git", "-C", str(repo_path)] + command

        if ctx:
            await ctx.debug(f"Executing git command: {' '.join(full_command)}")

        try:
            result = await asyncio.create_subprocess_exec(
                *full_command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=repo_path
            )

            stdout, stderr = await result.communicate()
            stdout_str = stdout.decode("utf-8").strip()
            stderr_str = stderr.decode("utf-8").strip()

            if check and result.returncode != 0:
                if ctx:
                    await ctx.error(f"Git command failed (exit {result.returncode}): {stderr_str}")
                raise GitCommandError(full_command, result.returncode, stderr_str)

            if ctx and stdout_str:
                await ctx.debug(f"Git command output: {len(stdout_str)} characters")

            return stdout_str

        except FileNotFoundError:
            error_msg = "Git command not found - is git installed?"
            if ctx:
                await ctx.error(error_msg)
            raise GitCommandError(full_command, -1, error_msg)
        except Exception as e:
            if ctx:
                await ctx.error(f"Unexpected error executing git command: {str(e)}")
            raise

    async def get_status(self, repo_path: Path) -> dict[str, Any]:
        """Get git status information."""
        ctx = self._get_context()

        if ctx:
            await ctx.debug("Getting git status (porcelain format)")

        # Get porcelain status for parsing
        status_output = await self.execute_command(repo_path, ["status", "--porcelain=v1"])

        files = []
        for line in status_output.split("\n"):
            if line.strip():
                index_status = line[0] if line[0] != " " else None
                working_status = line[1] if line[1] != " " else None
                filename = line[3:] if len(line) > 3 else ""

                files.append(
                    {
                        "filename": filename,
                        "index_status": index_status,
                        "working_status": working_status,
                        "status_code": index_status or working_status or "?",
                    }
                )

        if ctx:
            await ctx.debug(f"Parsed {len(files)} file status entries")

        return {"files": files}

    async def get_diff(self, repo_path: Path, staged: bool = False, file_path: str | None = None) -> str:
        """Get diff output."""
        ctx = self._get_context()

        command = ["diff"]
        if staged:
            command.append("--cached")
        if file_path:
            command.extend(["--", file_path])

        if ctx:
            diff_type = "staged" if staged else "working tree"
            target = f" for {file_path}" if file_path else ""
            await ctx.debug(f"Getting {diff_type} diff{target}")

        diff_output = await self.execute_command(repo_path, command)

        if ctx:
            lines_count = len(diff_output.split("\n")) if diff_output else 0
            await ctx.debug(f"Retrieved diff with {lines_count} lines")

        return diff_output

    async def get_unpushed_commits(self, repo_path: Path, remote: str = "origin") -> list[dict[str, Any]]:
        """Get commits that haven't been pushed to remote."""
        ctx = self._get_context()

        if ctx:
            await ctx.debug(f"Getting unpushed commits for remote '{remote}'")

        try:
            # Get current branch
            current_branch = await self.execute_command(repo_path, ["branch", "--show-current"])

            if ctx:
                await ctx.debug(f"Current branch: {current_branch}")

            # Get unpushed commits
            log_format = '--pretty=format:{"sha":"%H","message":"%s","author":"%an","email":"%ae","date":"%ai"}'
            upstream = f"{remote}/{current_branch}"

            try:
                if ctx:
                    await ctx.debug(f"Checking for commits ahead of {upstream}")

                output = await self.execute_command(repo_path, ["log", f"{upstream}..HEAD", log_format])
            except GitCommandError:
                # If upstream doesn't exist, get all commits (limited)
                if ctx:
                    await ctx.warning(f"Upstream {upstream} not found, getting recent commits")

                output = await self.execute_command(repo_path, ["log", log_format, "--max-count=10"])

            commits = []
            for line in output.split("\n"):
                if line.strip():
                    try:
                        commit_data = json.loads(line)
                        commits.append(commit_data)
                    except json.JSONDecodeError:
                        if ctx:
                            await ctx.warning(f"Failed to parse commit JSON: {line[:50]}...")
                        continue

            if ctx:
                await ctx.debug(f"Found {len(commits)} unpushed commits")

            return commits

        except GitCommandError as e:
            if ctx:
                await ctx.warning(f"Failed to get unpushed commits: {e}")
            return []

    async def get_stash_list(self, repo_path: Path) -> list[dict[str, Any]]:
        """Get list of stashed changes."""
        ctx = self._get_context()

        if ctx:
            await ctx.debug("Getting git stash list")

        try:
            output = await self.execute_command(repo_path, ["stash", "list", "--pretty=format:%gd|%s|%cr"])

            stashes = []
            for i, line in enumerate(output.split("\n")):
                if line.strip():
                    parts = line.split("|", 2)
                    if len(parts) >= 2:
                        stashes.append(
                            {
                                "index": i,
                                "name": parts[0],
                                "message": parts[1],
                                "date": parts[2] if len(parts) > 2 else "",
                            }
                        )

            if ctx:
                await ctx.debug(f"Found {len(stashes)} stashed changes")

            return stashes

        except GitCommandError as e:
            if ctx:
                await ctx.warning(f"Failed to get stash list: {e}")
            return []

    async def get_branch_info(self, repo_path: Path) -> dict[str, Any]:
        """Get branch information."""
        ctx = self._get_context()

        if ctx:
            await ctx.debug("Getting branch information")

        try:
            # Get current branch
            current_branch = await self.execute_command(repo_path, ["branch", "--show-current"])

            if ctx:
                await ctx.debug(f"Current branch: {current_branch}")

            # Get upstream info
            upstream = None
            try:
                upstream = await self.execute_command(repo_path, ["rev-parse", "--abbrev-ref", "@{upstream}"])
                if ctx:
                    await ctx.debug(f"Upstream branch: {upstream}")
            except GitCommandError:
                if ctx:
                    await ctx.debug("No upstream branch configured")

            # Get ahead/behind counts
            ahead, behind = 0, 0
            if upstream:
                try:
                    counts = await self.execute_command(
                        repo_path, ["rev-list", "--left-right", "--count", f"{upstream}...HEAD"]
                    )
                    behind, ahead = map(int, counts.split())

                    if ctx:
                        await ctx.debug(f"Branch status: {ahead} ahead, {behind} behind")

                except (GitCommandError, ValueError) as e:
                    if ctx:
                        await ctx.warning(f"Failed to get ahead/behind counts: {e}")

            # Get HEAD commit SHA
            try:
                head_commit = await self.execute_command(repo_path, ["rev-parse", "HEAD"])
                if ctx:
                    await ctx.debug(f"HEAD commit: {head_commit[:8]}...")
            except GitCommandError:
                head_commit = "unknown"
                if ctx:
                    await ctx.warning("Failed to get HEAD commit SHA")

            return {
                "current_branch": current_branch,
                "upstream": upstream,
                "ahead": ahead,
                "behind": behind,
                "head_commit": head_commit,
            }

        except GitCommandError as e:
            if ctx:
                await ctx.error(f"Failed to get branch info: {e}")
            return {"current_branch": "unknown", "upstream": None, "ahead": 0, "behind": 0, "head_commit": "unknown"}

    async def get_repository_info(self, repo_path: Path) -> dict[str, Any]:
        """Get general repository information."""
        ctx = self._get_context()

        if ctx:
            await ctx.debug("Getting repository information")

        try:
            # Check if it's a bare repository
            try:
                await self.execute_command(repo_path, ["rev-parse", "--is-bare-repository"])
                is_bare = True
            except GitCommandError:
                is_bare = False

            # Get remote URLs
            remotes = {}
            try:
                remote_output = await self.execute_command(repo_path, ["remote", "-v"])
                for line in remote_output.split("\n"):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            remote_name = parts[0]
                            remote_url = parts[1]
                            remote_type = parts[2].strip("()")

                            if remote_name not in remotes:
                                remotes[remote_name] = {}
                            remotes[remote_name][remote_type] = remote_url

            except GitCommandError:
                if ctx:
                    await ctx.debug("No remotes configured")

            # Check if repository is dirty (has uncommitted changes)
            try:
                status_output = await self.execute_command(repo_path, ["status", "--porcelain"])
                is_dirty = bool(status_output.strip())
            except GitCommandError:
                is_dirty = False

            if ctx:
                await ctx.debug(f"Repository info: bare={is_bare}, dirty={is_dirty}, remotes={len(remotes)}")

            return {"is_bare": is_bare, "is_dirty": is_dirty, "remotes": remotes, "root_path": str(repo_path)}

        except Exception as e:
            if ctx:
                await ctx.error(f"Failed to get repository info: {e}")
            return {"is_bare": False, "is_dirty": False, "remotes": {}, "root_path": str(repo_path)}
