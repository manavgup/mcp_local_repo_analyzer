"""Analysis result data models.

Copyright 2025
SPDX-License-Identifier: Apache-2.0
Author: Manav Gupta <manavg@gmail.com>

This module defines data models for analysis results including branch status,
change categorization, risk assessment, repository status, and outstanding changes analysis.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from .changes import StagedChanges, StashedChanges, UnpushedCommit, WorkingDirectoryChanges
from .repository import LocalRepository


class BranchStatus(BaseModel):
    """Status of a git branch relative to its upstream."""

    current_branch: str = Field(..., description="Current branch name")
    upstream_branch: str | None = Field(None, description="Upstream branch reference")
    ahead_by: int = Field(0, ge=0, description="Commits ahead of upstream")
    behind_by: int = Field(0, ge=0, description="Commits behind upstream")
    is_up_to_date: bool = Field(True, description="Branch is up to date with upstream")
    needs_push: bool = Field(False, description="Branch needs to be pushed")
    needs_pull: bool = Field(False, description="Branch needs to be pulled")

    @property
    def sync_status(self) -> str:
        """Get a human-readable sync status."""
        if self.is_up_to_date:
            return "up to date"
        elif self.ahead_by > 0 and self.behind_by > 0:
            return f"diverged ({self.ahead_by} ahead, {self.behind_by} behind)"
        elif self.ahead_by > 0:
            return f"{self.ahead_by} commit(s) ahead"
        elif self.behind_by > 0:
            return f"{self.behind_by} commit(s) behind"
        else:
            return "unknown"


class ChangeCategorization(BaseModel):
    """Categorization of changed files by type."""

    critical_files: list[str] = Field(default_factory=list, description="Config, core files that are critical")
    source_code: list[str] = Field(default_factory=list, description="Source code files")
    documentation: list[str] = Field(default_factory=list, description="Documentation files")
    tests: list[str] = Field(default_factory=list, description="Test files")
    configuration: list[str] = Field(default_factory=list, description="Configuration files")
    other: list[str] = Field(default_factory=list, description="Other files that don't fit categories")

    @property
    def total_files(self) -> int:
        """Total number of categorized files."""
        return (
            len(self.critical_files)
            + len(self.source_code)
            + len(self.documentation)
            + len(self.tests)
            + len(self.configuration)
            + len(self.other)
        )

    @property
    def has_critical_changes(self) -> bool:
        """Check if there are changes to critical files."""
        return len(self.critical_files) > 0


class RiskAssessment(BaseModel):
    """Assessment of risk level for the current changes."""

    risk_level: Literal["low", "medium", "high"] = Field(..., description="Overall risk level of the changes")
    risk_factors: list[str] = Field(default_factory=list, description="Factors contributing to the risk level")
    large_changes: list[str] = Field(default_factory=list, description="Files with >100 line changes")
    potential_conflicts: list[str] = Field(default_factory=list, description="Files that might cause merge conflicts")
    binary_changes: list[str] = Field(default_factory=list, description="Binary files that have changed")

    @property
    def is_high_risk(self) -> bool:
        """Check if this is a high-risk change set."""
        return self.risk_level == "high"

    @property
    def risk_score(self) -> int:
        """Get a numeric risk score (0-10)."""
        risk_map = {"low": 2, "medium": 5, "high": 8}
        base_score = risk_map[self.risk_level]

        # Adjust based on risk factors
        if len(self.large_changes) > 5:
            base_score += 1
        if len(self.potential_conflicts) > 0:
            base_score += 1

        return min(base_score, 10)


class RepositoryStatus(BaseModel):
    """Complete status of a repository's outstanding changes."""

    repository: LocalRepository = Field(..., description="Repository information")
    working_directory: WorkingDirectoryChanges = Field(..., description="Working directory changes")
    staged_changes: StagedChanges = Field(..., description="Staged changes")
    unpushed_commits: list[UnpushedCommit] = Field(default_factory=list, description="Commits not yet pushed")
    stashed_changes: list[StashedChanges] = Field(default_factory=list, description="Stashed changes")
    branch_status: BranchStatus = Field(..., description="Branch status information")

    @property
    def has_outstanding_work(self) -> bool:
        """Check if there's any outstanding work in the repository."""
        return (
            self.working_directory.has_changes
            or self.staged_changes.ready_to_commit
            or len(self.unpushed_commits) > 0
            or len(self.stashed_changes) > 0
        )

    @property
    def total_outstanding_changes(self) -> int:
        """Total number of outstanding changes across all categories."""
        return (
            self.working_directory.total_files
            + self.staged_changes.total_staged
            + len(self.unpushed_commits)
            + len(self.stashed_changes)
        )


class OutstandingChangesAnalysis(BaseModel):
    """Comprehensive analysis of all outstanding changes in a repository."""

    repository_path: Path = Field(..., description="Path to the analyzed repository")
    analysis_timestamp: datetime = Field(default_factory=datetime.now, description="When this analysis was performed")
    total_outstanding_files: int = Field(0, ge=0, description="Total number of files with outstanding changes")
    categories: ChangeCategorization = Field(
        default_factory=ChangeCategorization,
        description="Categorization of changed files",
    )
    risk_assessment: RiskAssessment = Field(..., description="Risk assessment of the changes")
    recommendations: list[str] = Field(default_factory=list, description="Recommended actions based on analysis")
    summary: str = Field(..., description="Human-readable summary of the analysis")
    repository_status: RepositoryStatus | None = Field(None, description="Complete repository status (optional)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the analysis")

    @property
    def is_ready_for_commit(self) -> bool:
        """Check if changes are ready to be committed."""
        if not self.repository_status:
            return False
        return self.repository_status.working_directory.has_changes and not self.risk_assessment.is_high_risk

    @property
    def is_ready_for_push(self) -> bool:
        """Check if repository is ready to be pushed."""
        if not self.repository_status:
            return False
        return (
            len(self.repository_status.unpushed_commits) > 0
            and not self.repository_status.working_directory.has_changes
            and not self.repository_status.staged_changes.ready_to_commit
        )

    @property
    def needs_attention(self) -> bool:
        """Check if the repository needs immediate attention."""
        return (
            self.risk_assessment.is_high_risk
            or len(self.risk_assessment.potential_conflicts) > 0
            or self.total_outstanding_files > 50
        )

    class Config:
        arbitrary_types_allowed = True
