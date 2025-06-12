"""Git changes related data models.

Copyright 2025
SPDX-License-Identifier: Apache-2.0
Author: Manav Gupta <manavg@gmail.com>

This module defines data models representing git file statuses, diffs,
working directory changes, staged changes, unpushed commits, and stashed changes.
"""

from datetime import datetime
from typing import Literal, cast

from pydantic import BaseModel, Field


class FileStatus(BaseModel):
    """Represents the status of a single file."""

    path: str = Field(..., description="File path relative to repository root")
    status_code: str = Field(..., description="Git status code (M, A, D, R, etc.)")
    staged: bool = Field(False, description="File is staged for commit")
    working_tree_status: str | None = Field(None, description="Working tree status")
    index_status: str | None = Field(None, description="Index status")
    lines_added: int = Field(0, ge=0, description="Lines added")
    lines_deleted: int = Field(0, ge=0, description="Lines deleted")
    is_binary: bool = Field(False, description="File is binary")
    old_path: str | None = Field(None, description="Original path for renames")

    @property
    def total_changes(self) -> int:
        """Total number of line changes."""
        return self.lines_added + self.lines_deleted

    @property
    def status_description(self) -> str:
        """Human-readable status description."""
        status_map = {
            "M": "Modified",
            "A": "Added",
            "D": "Deleted",
            "R": "Renamed",
            "C": "Copied",
            "U": "Unmerged",
            "?": "Untracked",
            "!": "Ignored",
        }
        return status_map.get(self.status_code, self.status_code)

    @property
    def change_type(
        self,
    ) -> Literal["addition", "modification", "deletion", "rename", "copy", "untracked"]:
        """Categorize the type of change."""
        mapping = {
            "A": "addition",
            "M": "modification",
            "D": "deletion",
            "R": "rename",
            "C": "copy",
            "?": "untracked",
        }
        return cast(
            Literal["addition", "modification", "deletion", "rename", "copy", "untracked"],
            mapping.get(self.status_code, "modification"),
        )


class DiffHunk(BaseModel):
    """Represents a single diff hunk."""

    old_start: int = Field(..., ge=0, description="Starting line in old file")
    old_lines: int = Field(..., ge=0, description="Number of lines in old file")
    new_start: int = Field(..., ge=0, description="Starting line in new file")
    new_lines: int = Field(..., ge=0, description="Number of lines in new file")
    content: str = Field(..., description="Hunk content")
    context_lines: list[str] = Field(default_factory=list, description="Context lines")


class FileDiff(BaseModel):
    """Represents a file diff with detailed information."""

    file_path: str = Field(..., description="File path")
    old_path: str | None = Field(None, description="Original path for renames")
    diff_content: str = Field(..., description="Full diff content")
    hunks: list[DiffHunk] = Field(default_factory=list, description="Diff hunks")
    is_binary: bool = Field(False, description="Is binary file")
    lines_added: int = Field(0, ge=0, description="Lines added")
    lines_deleted: int = Field(0, ge=0, description="Lines deleted")
    file_mode_old: str | None = Field(None, description="Old file mode")
    file_mode_new: str | None = Field(None, description="New file mode")

    @property
    def total_changes(self) -> int:
        """Total number of line changes."""
        return self.lines_added + self.lines_deleted

    @property
    def is_large_change(self) -> bool:
        """Check if this is a large change (>100 lines)."""
        return self.total_changes > 100


class WorkingDirectoryChanges(BaseModel):
    """Status of working directory changes."""

    modified_files: list[FileStatus] = Field(default_factory=list, description="Modified files")
    added_files: list[FileStatus] = Field(default_factory=list, description="Added files")
    deleted_files: list[FileStatus] = Field(default_factory=list, description="Deleted files")
    renamed_files: list[FileStatus] = Field(default_factory=list, description="Renamed files")
    untracked_files: list[FileStatus] = Field(default_factory=list, description="Untracked files")

    @property
    def total_files(self) -> int:
        """Total number of changed files."""
        return (
            len(self.modified_files)
            + len(self.added_files)
            + len(self.deleted_files)
            + len(self.renamed_files)
            + len(self.untracked_files)
        )

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return self.total_files > 0

    @property
    def all_files(self) -> list[FileStatus]:
        """Get all changed files as a single list."""
        return self.modified_files + self.added_files + self.deleted_files + self.renamed_files + self.untracked_files


class StagedChanges(BaseModel):
    """Changes staged for commit."""

    staged_files: list[FileStatus] = Field(default_factory=list, description="Staged files")

    @property
    def total_staged(self) -> int:
        """Total number of staged files."""
        return len(self.staged_files)

    @property
    def ready_to_commit(self) -> bool:
        """Check if there are staged changes ready to commit."""
        return self.total_staged > 0

    @property
    def total_additions(self) -> int:
        """Total lines added across all staged files."""
        return sum(f.lines_added for f in self.staged_files)

    @property
    def total_deletions(self) -> int:
        """Total lines deleted across all staged files."""
        return sum(f.lines_deleted for f in self.staged_files)


class UnpushedCommit(BaseModel):
    """Represents a commit that hasn't been pushed to remote."""

    sha: str = Field(..., description="Commit SHA")
    message: str = Field(..., description="Commit message")  # Ensure this is a string
    author: str = Field(..., description="Author name")
    author_email: str = Field(..., description="Author email")
    date: datetime = Field(..., description="Commit date")
    files_changed: list[str] = Field(default_factory=list, description="List of changed files")
    insertions: int = Field(0, ge=0, description="Number of insertions")
    deletions: int = Field(0, ge=0, description="Number of deletions")

    @property
    def short_sha(self) -> str:
        """Get short version of SHA."""
        return self.sha[:8]

    @property
    def short_message(self) -> str:
        """Get first line of commit message."""
        return str(self.message).split("\n", maxsplit=1)[0]  # Convert to string before splitting

    @property
    def total_changes(self) -> int:
        """Total number of changes."""
        return self.insertions + self.deletions


class StashedChanges(BaseModel):
    """Represents stashed changes."""

    stash_index: int = Field(..., ge=0, description="Stash index")
    message: str = Field(..., description="Stash message")
    branch: str = Field(..., description="Branch where stash was created")
    date: datetime = Field(..., description="Stash creation date")
    files_affected: list[str] = Field(default_factory=list, description="Files affected by stash")

    @property
    def stash_name(self) -> str:
        """Get stash name (stash@{index})."""
        return f"stash@{{{self.stash_index}}}"
