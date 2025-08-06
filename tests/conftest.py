"""
Test configuration and fixtures for mcp_local_repo_analyzer.

This module provides analyzer-specific fixtures while importing shared
fixtures from mcp_shared_lib.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from unittest.mock import Mock

import pytest

# Import shared fixtures from mcp_shared_lib
# Note: Direct import instead of pytest_plugins due to package structure
try:
    import sys
    from pathlib import Path

    # Add the mcp_shared_lib tests directory to the path
    shared_lib_tests_path = (
        Path(__file__).parent.parent.parent / "mcp_shared_lib" / "tests"
    )
    if shared_lib_tests_path.exists():
        sys.path.insert(0, str(shared_lib_tests_path))
        from conftest import *
    else:
        # Fallback: define essential fixtures locally
        @pytest.fixture
        def sample_config():
            return {
                "git_client": {"timeout": 30},
                "analyzer": {"scan_depth": 10},
            }

        @pytest.fixture
        def temp_dir():
            import shutil
            import tempfile

            temp_dir = Path(tempfile.mkdtemp(prefix="test_"))
            yield temp_dir
            shutil.rmtree(temp_dir, ignore_errors=True)

except ImportError:
    # Fallback: define essential fixtures locally
    @pytest.fixture
    def sample_config():
        return {
            "git_client": {"timeout": 30},
            "analyzer": {"scan_depth": 10},
        }

    @pytest.fixture
    def temp_dir():
        import shutil
        import tempfile

        temp_dir = Path(tempfile.mkdtemp(prefix="test_"))
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)


try:
    from git import Repo

    HAS_GIT = True
except ImportError:
    HAS_GIT = False

try:
    from fastmcp import FastMCP

    HAS_FASTMCP = True
except ImportError:
    HAS_FASTMCP = False


@pytest.fixture
def analyzer_config(sample_config):
    """Extended configuration specific to the analyzer."""
    config = sample_config.copy()
    config.update(
        {
            "analyzer": {
                "scan_depth": 10,
                "ignore_patterns": ["*.log", "*.tmp", "node_modules/"],
                "risk_weights": {
                    "file_size": 0.3,
                    "complexity": 0.4,
                    "test_coverage": 0.3,
                },
                "change_detection": {
                    "include_untracked": True,
                    "include_stashes": False,
                    "max_commits_to_analyze": 50,
                },
            },
            "git_client": {
                "timeout": 30,
                "max_diff_size": 1000000,
                "binary_file_threshold": 1024,
            },
            "risk_assessment": {
                "critical_files": ["config/", "migrations/", "Dockerfile"],
                "high_risk_extensions": [".sql", ".json", ".yaml", ".yml"],
                "complexity_threshold": 15,
                "size_threshold_mb": 5,
            },
        }
    )
    return config


@pytest.fixture
def mock_git_client():
    """Mock GitClient for testing analyzer services."""
    client = Mock()

    # Repository state methods
    client.get_repo_root.return_value = Path("/test/repo")
    client.get_current_branch.return_value = "feature/test-branch"
    client.has_uncommitted_changes.return_value = True
    client.has_unpushed_commits.return_value = True
    client.get_remote_url.return_value = "https://github.com/test/repo.git"

    # File change methods
    client.get_modified_files.return_value = [
        "src/models/user.py",
        "tests/test_user.py",
    ]
    client.get_untracked_files.return_value = ["src/new_feature.py", "temp_notes.txt"]
    client.get_staged_files.return_value = ["README.md", "docs/api.md"]
    client.get_deleted_files.return_value = ["deprecated/old_module.py"]

    # Commit history
    client.get_unpushed_commits.return_value = [
        {
            "hash": "abc123",
            "message": "feat: add user authentication",
            "author": "John Doe",
            "timestamp": datetime.now() - timedelta(hours=2),
            "files": ["src/auth.py", "tests/test_auth.py"],
        },
        {
            "hash": "def456",
            "message": "fix: resolve login bug",
            "author": "Jane Smith",
            "timestamp": datetime.now() - timedelta(hours=4),
            "files": ["src/auth.py"],
        },
    ]

    # Stash operations
    client.get_stashes.return_value = [
        {
            "index": 0,
            "message": "WIP: experimental feature",
            "timestamp": datetime.now() - timedelta(hours=1),
            "files": ["src/experimental.py"],
        }
    ]

    # Diff operations
    client.get_file_diff.return_value = {
        "additions": 25,
        "deletions": 5,
        "diff_text": "@@ -1,3 +1,28 @@\n class User:\n+    def __init__(self):\n+        pass",
    }

    # Branch operations
    client.get_all_branches.return_value = ["main", "develop", "feature/test-branch"]
    client.get_merge_conflicts.return_value = []

    return client


@pytest.fixture
def mock_change_detector():
    """Mock ChangeDetector for testing."""
    detector = Mock()

    detector.detect_all_changes.return_value = {
        "modified": ["src/main.py", "tests/test_main.py"],
        "untracked": ["new_file.py"],
        "staged": ["README.md"],
        "deleted": [],
        "conflicted": [],
    }

    detector.analyze_file_changes.return_value = [
        {
            "file_path": "src/main.py",
            "change_type": "modified",
            "lines_added": 15,
            "lines_removed": 3,
            "risk_score": 0.4,
            "size_change": 12,
        },
        {
            "file_path": "new_file.py",
            "change_type": "added",
            "lines_added": 50,
            "lines_removed": 0,
            "risk_score": 0.6,
            "size_change": 50,
        },
    ]

    detector.get_change_summary.return_value = {
        "total_files": 3,
        "total_additions": 65,
        "total_deletions": 3,
        "net_change": 62,
        "risk_level": "medium",
    }

    return detector


@pytest.fixture
def mock_risk_assessor():
    """Mock RiskAssessor for testing."""
    assessor = Mock()

    assessor.assess_file_risk.return_value = {
        "risk_score": 0.7,
        "factors": {
            "file_size": 0.3,
            "complexity": 0.5,
            "critical_path": True,
            "test_coverage": 0.8,
        },
        "recommendations": [
            "Add more unit tests",
            "Consider breaking into smaller modules",
        ],
    }

    assessor.assess_overall_risk.return_value = {
        "overall_risk": 0.6,
        "high_risk_files": ["config/database.json", "src/core/processor.py"],
        "risk_distribution": {"low": 3, "medium": 4, "high": 2, "critical": 1},
        "recommendations": [
            "Review critical configuration changes",
            "Ensure adequate test coverage for high-risk files",
        ],
    }

    assessor.check_push_readiness.return_value = {
        "ready": False,
        "blockers": [
            "Uncommitted changes in critical files",
            "Missing tests for new features",
        ],
        "warnings": ["Large number of file changes", "Complex modifications detected"],
        "score": 0.3,
    }

    return assessor


@pytest.fixture
def sample_repository_state():
    """Sample repository state for testing."""
    return {
        "working_directory": {
            "clean": False,
            "modified_files": 5,
            "untracked_files": 2,
            "deleted_files": 1,
        },
        "staging_area": {"staged_files": 3, "ready_to_commit": True},
        "commit_history": {"unpushed_commits": 4, "ahead_by": 4, "behind_by": 0},
        "branches": {
            "current": "feature/analytics",
            "tracking": "origin/feature/analytics",
            "merge_conflicts": False,
        },
        "stashes": {"count": 1, "latest_message": "WIP: refactoring data layer"},
    }


@pytest.fixture
def mock_file_analyzer():
    """Mock file analyzer for individual file analysis."""
    analyzer = Mock()

    analyzer.analyze_file.return_value = {
        "file_path": "src/example.py",
        "size_bytes": 2048,
        "line_count": 150,
        "complexity_score": 8,
        "test_coverage": 0.75,
        "dependencies": ["os", "json", "typing"],
        "functions": 12,
        "classes": 2,
        "risk_indicators": {
            "large_function": False,
            "high_complexity": False,
            "missing_docstrings": True,
            "security_patterns": [],
        },
    }

    analyzer.get_file_metrics.return_value = {
        "cyclomatic_complexity": 8,
        "maintainability_index": 72,
        "halstead_metrics": {"volume": 1250, "difficulty": 15.2, "effort": 19000},
        "code_to_comment_ratio": 0.15,
    }

    return analyzer


if HAS_FASTMCP:

    @pytest.fixture
    async def fastmcp_analyzer_server():
        """FastMCP server instance configured for analyzer testing."""
        server = FastMCP("LocalRepoAnalyzer")

        @server.tool
        def analyze_changes(repo_path: str, include_untracked: bool = False) -> dict:
            """Analyze repository changes."""
            return {
                "status": "success",
                "changes": {
                    "modified": ["src/main.py"],
                    "untracked": ["temp.py"] if include_untracked else [],
                    "staged": ["README.md"],
                },
                "risk_score": 0.4,
            }

        @server.tool
        def check_push_readiness(repo_path: str) -> dict:
            """Check if repository is ready for push."""
            return {
                "status": "success",
                "ready": True,
                "checks": {
                    "no_conflicts": True,
                    "tests_passing": True,
                    "no_critical_issues": True,
                },
            }

        @server.tool
        def analyze_commit_history(repo_path: str, max_commits: int = 10) -> dict:
            """Analyze recent commit history."""
            return {
                "status": "success",
                "commits": [
                    {
                        "hash": "abc123",
                        "message": "feat: add new feature",
                        "author": "Test User",
                        "files_changed": 3,
                    }
                ],
                "summary": {"total_commits": 1, "average_files_per_commit": 3.0},
            }

        return server

else:

    @pytest.fixture
    def fastmcp_analyzer_server():
        """Fallback fixture when FastMCP is not available."""
        pytest.skip("FastMCP not available for testing")


@pytest.fixture
def mock_analyzer_tools():
    """Mock collection of analyzer tools."""
    tools = Mock()

    # Analyze changes tool
    tools.analyze_changes = Mock()
    tools.analyze_changes.return_value = {
        "modified_files": ["src/main.py", "tests/test_main.py"],
        "untracked_files": ["new_feature.py"],
        "staged_files": ["README.md"],
        "risk_assessment": {"overall_risk": 0.5, "high_risk_files": []},
        "recommendations": [
            "Consider adding tests for new_feature.py",
            "Review changes in main.py for potential impacts",
        ],
    }

    # Push readiness tool
    tools.check_push_readiness = Mock()
    tools.check_push_readiness.return_value = {
        "ready": True,
        "score": 0.85,
        "checks": {
            "has_uncommitted_changes": False,
            "has_untracked_files": True,
            "has_merge_conflicts": False,
            "tests_exist": True,
            "critical_files_changed": False,
        },
        "recommendations": [
            "Consider tracking new files before push",
            "Run full test suite before pushing",
        ],
    }

    # Stash analysis tool
    tools.analyze_stashes = Mock()
    tools.analyze_stashes.return_value = {
        "stash_count": 2,
        "stashes": [
            {
                "index": 0,
                "message": "WIP: experimental changes",
                "files": ["src/experimental.py"],
                "age_hours": 24,
            },
            {
                "index": 1,
                "message": "temp: debugging session",
                "files": ["debug.py", "test_output.log"],
                "age_hours": 72,
            },
        ],
        "recommendations": [
            "Review old stashes for relevant changes",
            "Clean up temporary debugging files",
        ],
    }

    return tools


@pytest.fixture
def analyzer_test_repo(temp_git_repo, create_test_files, sample_project_structure):
    """Create a test repository with analyzer-specific structure."""
    if not HAS_GIT:
        pytest.skip("Git not available for testing")

    # Create the project structure
    create_test_files(temp_git_repo, sample_project_structure)

    # Initialize git repository with the files
    repo = Repo(temp_git_repo)

    # Add all files and make initial commit
    repo.git.add(".")
    repo.index.commit("Initial commit with full project structure")

    # Create some changes for testing
    # Modify existing file
    main_file = temp_git_repo / "src" / "main.py"
    main_file.write_text(
        "#!/usr/bin/env python3\n\ndef main():\n    print('Hello, Modified World!')\n\nif __name__ == '__main__':\n    main()\n"
    )

    # Add new untracked file
    new_feature = temp_git_repo / "src" / "new_feature.py"
    new_feature.write_text(
        "def new_feature():\n    '''New feature implementation.'''\n    return 'new feature'\n"
    )

    # Stage some changes
    readme = temp_git_repo / "README.md"
    readme.write_text(
        "# Test Project\n\nUpdated main readme with more information.\n\n## Features\n- Main functionality\n- New features\n"
    )
    repo.index.add([str(readme)])

    # Create a config change (high risk)
    config_file = temp_git_repo / "config" / "settings.json"
    import json

    updated_config = {
        "database": {"host": "production.db.com", "port": 5432},
        "api": {"version": "v2", "timeout": 60},
        "security": {"encryption": True, "auth_required": True},
    }
    config_file.write_text(json.dumps(updated_config, indent=2))

    return temp_git_repo


@pytest.fixture
def sample_analysis_request():
    """Sample analysis request for testing."""
    return {
        "repo_path": "/test/repo",
        "options": {
            "include_untracked": True,
            "include_stashes": False,
            "max_commits": 20,
            "risk_assessment": True,
            "detailed_analysis": True,
        },
        "filters": {
            "file_patterns": ["*.py", "*.js", "*.json"],
            "exclude_patterns": ["*.log", "*.tmp", "node_modules/"],
            "min_file_size": 0,
            "max_file_size": 10485760,  # 10MB
        },
    }


@pytest.fixture
def expected_analysis_response():
    """Expected analysis response structure for testing."""
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "repository": {
            "path": "/test/repo",
            "branch": "feature/test",
            "remote": "origin",
            "clean": False,
        },
        "changes": {
            "modified": [
                {
                    "file": "src/main.py",
                    "lines_added": 10,
                    "lines_removed": 2,
                    "risk_score": 0.3,
                }
            ],
            "untracked": [
                {"file": "src/new_feature.py", "size": 1024, "risk_score": 0.5}
            ],
            "staged": [
                {
                    "file": "README.md",
                    "lines_added": 5,
                    "lines_removed": 1,
                    "risk_score": 0.1,
                }
            ],
            "deleted": [],
        },
        "risk_assessment": {
            "overall_risk": 0.4,
            "risk_factors": {
                "config_changes": False,
                "large_changes": False,
                "new_dependencies": False,
                "test_coverage_impact": True,
            },
            "recommendations": [
                "Add tests for new features",
                "Review modified core files",
            ],
        },
        "push_readiness": {
            "ready": False,
            "score": 0.7,
            "blockers": ["Untracked files present"],
            "warnings": ["Large changeset"],
        },
        "summary": {
            "total_files_changed": 3,
            "total_lines_added": 15,
            "total_lines_removed": 3,
            "estimated_review_time": "15 minutes",
        },
    }


@pytest.fixture
def mock_server_context():
    """Mock server context for testing FastMCP integration."""
    context = Mock()
    context.session_id = "test-session-123"
    context.client_info = {"name": "test-client", "version": "1.0.0"}
    context.request_id = "req-456"
    return context


@pytest.fixture
def integration_test_scenarios():
    """Test scenarios for integration testing."""
    return {
        "clean_repo": {
            "description": "Repository with no changes",
            "setup": {"modified_files": [], "untracked_files": [], "staged_files": []},
            "expected": {"changes_count": 0, "risk_score": 0.0, "push_ready": True},
        },
        "small_changes": {
            "description": "Small, low-risk changes",
            "setup": {
                "modified_files": ["README.md"],
                "untracked_files": [],
                "staged_files": ["docs/changelog.md"],
            },
            "expected": {"changes_count": 2, "risk_score": 0.2, "push_ready": True},
        },
        "risky_changes": {
            "description": "High-risk configuration changes",
            "setup": {
                "modified_files": ["config/production.json", "src/core/auth.py"],
                "untracked_files": ["migration_script.sql"],
                "staged_files": [],
            },
            "expected": {"changes_count": 3, "risk_score": 0.9, "push_ready": False},
        },
        "large_changeset": {
            "description": "Large number of changes",
            "setup": {
                "modified_files": [f"src/module_{i}.py" for i in range(20)],
                "untracked_files": [f"new_file_{i}.py" for i in range(5)],
                "staged_files": ["package.json", "requirements.txt"],
            },
            "expected": {"changes_count": 27, "risk_score": 0.7, "push_ready": False},
        },
    }


# Utility functions specific to analyzer testing
def create_mock_git_status(modified=None, untracked=None, staged=None, deleted=None):
    """Create a mock git status response."""
    return {
        "modified": modified or [],
        "untracked": untracked or [],
        "staged": staged or [],
        "deleted": deleted or [],
        "clean": not any([modified, untracked, staged, deleted]),
    }


def create_mock_commit(
    hash_id: Optional[str] = None,
    message: Optional[str] = None,
    author: Optional[str] = None,
    timestamp: Optional[datetime] = None,
    files: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Create a mock commit object."""
    return {
        "hash": hash_id or "abc123def456",
        "message": message or "Test commit message",
        "author": author or "Test User",
        "timestamp": timestamp or datetime.now(),
        "files": files or ["test_file.py"],
    }


@pytest.fixture
def git_status_factory():
    """Factory for creating git status mocks."""
    return create_mock_git_status


@pytest.fixture
def commit_factory():
    """Factory for creating commit mocks."""
    return create_mock_commit


# Make analyzer-specific fixtures available
__all__ = [
    "analyzer_config",
    "mock_git_client",
    "mock_change_detector",
    "mock_risk_assessor",
    "sample_repository_state",
    "mock_file_analyzer",
    "fastmcp_analyzer_server",
    "mock_analyzer_tools",
    "analyzer_test_repo",
    "sample_analysis_request",
    "expected_analysis_response",
    "mock_server_context",
    "integration_test_scenarios",
    "git_status_factory",
    "commit_factory",
]
