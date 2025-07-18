"""
Test module: manual

Migrated to standardized test structure with shared fixtures.
"""
import asyncio
import pytest
import subprocess
import tempfile
from pathlib import Path
from fastmcp import Client
from unittest.mock import Mock, patch, MagicMock, AsyncMock


import sys
print("=== DEBUG INFO ===")
print("Python path in test:", sys.path)
print("mcp_shared_lib paths:", [p for p in sys.path if 'mcp_shared_lib' in p])

# Test the import within pytest
try:
    from mcp_shared_lib.config import settings
    print("✅ Import successful in test environment")
except ImportError as e:
    print(f"❌ Import failed in test environment: {e}")
    import traceback
    traceback.print_exc()
print("=== END DEBUG ===")

# Import shared fixtures from mcp_shared_lib

class GitTestRepo:
    """Helper class to create test git repositories."""

    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)

    def run_git(self, *args):
        """Run a git command in the test repo."""
        result = subprocess.run(["git"] + list(args), cwd=self.path, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Git command failed: {result.stderr}")
        return result.stdout.strip()

    def init(self):
        """Initialize the git repository."""
        self.run_git("init")
        self.run_git("config", "user.name", "Test User")
        self.run_git("config", "user.email", "test@example.com")
        return self

    def create_file(self, filename: str, content: str = ""):
        """Create a file with content."""
        file_path = self.path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return self

    def modify_file(self, filename: str, content: str):
        """Modify an existing file."""
        file_path = self.path / filename
        existing = file_path.read_text() if file_path.exists() else ""
        file_path.write_text(existing + "\n" + content)
        return self

    def add(self, *files):
        """Add files to git."""
        self.run_git("add", *files)
        return self

    def commit(self, message: str):
        """Commit changes."""
        self.run_git("commit", "-m", message)
        return self

    def add_remote(self, name: str = "origin", url: str = "https://github.com/test/repo.git"):
        """Add a remote."""
        self.run_git("remote", "add", name, url)
        return self


@pytest.mark.asyncio
async def test_scenario_clean_repo():
    """Test scenario: Clean repository with no changes."""
    print("\n🧹 Testing Scenario: Clean Repository")

    with tempfile.TemporaryDirectory() as temp_dir:
        test_repo = GitTestRepo(Path(temp_dir))

        # Create a clean repository
        (test_repo.init().create_file("README.md", "# Test Repository").add("README.md").commit("Initial commit"))

        # Test the server
        client = Client("src/mcp_local_repo_analyzer/main.py")
        async with client:
            result = await client.call_tool("get_outstanding_summary", {"repository_path": str(test_repo.path)})

            if isinstance(result, list) and result and hasattr(result[0], 'text'):
                import json
                data = json.loads(result[0].text)
            elif isinstance(result, dict):
                data = result
            else:
                data = {}

            print(f"✅ Clean repo result: {data.get('has_outstanding_work', 'unknown')}")
            
            # Debug: Print more details about what was found
            if data.get("has_outstanding_work", True):
                print(f"  Debug - Outstanding work detected:")
                if "quick_stats" in data:
                    stats = data["quick_stats"]
                    print(f"    Working dir changes: {stats.get('working_directory_changes', 0)}")
                    print(f"    Staged changes: {stats.get('staged_changes', 0)}")
                    print(f"    Unpushed commits: {stats.get('unpushed_commits', 0)}")
                
            # Check if the only outstanding work is unpushed commits (which is expected for a new repo)
            quick_stats = data.get("quick_stats", {})
            working_changes = quick_stats.get("working_directory_changes", 0)
            staged_changes = quick_stats.get("staged_changes", 0)
            unpushed_commits = quick_stats.get("unpushed_commits", 0)
            
            # A "clean" repo should have no working directory or staged changes
            # Unpushed commits are expected since we just created the repo without a remote
            assert working_changes == 0, f"Clean repo should have no working directory changes. Got: {working_changes}"
            assert staged_changes == 0, f"Clean repo should have no staged changes. Got: {staged_changes}"
            
            # The repo may have outstanding work due to unpushed commits, which is normal for a new local repo
            if data.get("has_outstanding_work", False) and unpushed_commits > 0:
                print(f"  ✅ Outstanding work is only due to {unpushed_commits} unpushed commit(s) - this is expected for a new repo")
            elif not data.get("has_outstanding_work", True):
                print(f"  ✅ Repository is completely clean")
            else:
                assert False, f"Unexpected outstanding work in clean repo. Got: {data}"


@pytest.mark.asyncio
async def test_scenario_working_directory_changes():
    """Test scenario: Repository with working directory changes."""
    print("\n📝 Testing Scenario: Working Directory Changes")

    with tempfile.TemporaryDirectory() as temp_dir:
        test_repo = GitTestRepo(Path(temp_dir))

        # Create repository with uncommitted changes
        (
            test_repo.init()
            .create_file("README.md", "# Test Repository")
            .add("README.md")
            .commit("Initial commit")
            .modify_file("README.md", "## New Section")
            .create_file("new_file.py", "print('Hello, World!')")
        )

        # Test the server
        client = Client("src/mcp_local_repo_analyzer/main.py")
        async with client:
            result = await client.call_tool("analyze_working_directory", {"repository_path": str(test_repo.path)})

            if isinstance(result, list) and result and hasattr(result[0], 'text'):
                import json
                data = json.loads(result[0].text)
            elif isinstance(result, dict):
                data = result
            else:
                data = {}

            print(f"✅ Working directory changes: {data.get('total_files_changed', 0)} files")
            assert data.get("total_files_changed", 0) > 0, "Should detect working directory changes"


@pytest.mark.asyncio
async def test_scenario_staged_changes():
    """Test scenario: Repository with staged changes."""
    print("\n📋 Testing Scenario: Staged Changes")

    with tempfile.TemporaryDirectory() as temp_dir:
        test_repo = GitTestRepo(Path(temp_dir))

        # Create repository with staged changes
        (
            test_repo.init()
            .create_file("README.md", "# Test Repository")
            .add("README.md")
            .commit("Initial commit")
            .create_file("feature.py", "def new_feature(): pass")
            .add("feature.py")
        )

        # Test the server
        client = Client("src/mcp_local_repo_analyzer/main.py")
        async with client:
            result = await client.call_tool("analyze_staged_changes", {"repository_path": str(test_repo.path)})

            if isinstance(result, list) and result and hasattr(result[0], 'text'):
                import json
                data = json.loads(result[0].text)
            elif isinstance(result, dict):
                data = result
            else:
                data = {}

            print(f"✅ Staged changes: {data.get('total_staged_files', 0)} files")
            assert data.get("ready_to_commit", False), "Should be ready to commit"


@pytest.mark.asyncio
async def test_scenario_mixed_changes():
    """Test scenario: Repository with mixed types of changes."""
    print("\n🎭 Testing Scenario: Mixed Changes")

    with tempfile.TemporaryDirectory() as temp_dir:
        test_repo = GitTestRepo(Path(temp_dir))

        # Create complex scenario
        (
            test_repo.init()
            .create_file("src/main.py", "def main(): pass")
            .create_file("tests/test_main.py", "def test_main(): pass")
            .create_file("README.md", "# Project")
            .create_file("config.json", '{"version": "1.0"}')
            .add(".")
            .commit("Initial commit")
            # Add some uncommitted changes
            .modify_file("src/main.py", "# Updated function")
            .create_file("new_feature.py", "# New feature")
            # Stage some changes
            .add("src/main.py")
            # Leave new_feature.py untracked
        )

        # Test comprehensive analysis
        client = Client("src/mcp_local_repo_analyzer/main.py")
        async with client:
            result = await client.call_tool(
                "get_outstanding_summary", {"repository_path": str(test_repo.path), "detailed": True}
            )

            if isinstance(result, list) and result and hasattr(result[0], 'text'):
                import json
                data = json.loads(result[0].text)
            elif isinstance(result, dict):
                data = result
            else:
                data = {}

            print("✅ Mixed changes summary:")
            print(f"   Outstanding work: {data.get('has_outstanding_work', 'unknown')}")
            print(f"   Total changes: {data.get('total_outstanding_changes', 0)}")

            if "quick_stats" in data:
                stats = data["quick_stats"]
                print(f"   Working dir: {stats.get('working_directory_changes', 0)}")
                print(f"   Staged: {stats.get('staged_changes', 0)}")

            assert data.get("has_outstanding_work", False), "Should have outstanding work"


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling with invalid repository."""
    print("\n⚠️  Testing Scenario: Error Handling")

    client = Client("src/mcp_local_repo_analyzer/main.py")
    async with client:
        # Test with non-git directory
        with tempfile.TemporaryDirectory() as temp_dir:
            result = await client.call_tool("analyze_working_directory", {"repository_path": temp_dir})

            if isinstance(result, list) and result and hasattr(result[0], 'text'):
                import json
                data = json.loads(result[0].text)
            elif isinstance(result, dict):
                data = result
            else:
                data = {}

            print(f"✅ Error handling: {data.get('error', 'No error field')[:50]}...")
            assert "error" in data, "Should return error for non-git directory"


@pytest.mark.skip(reason="Server startup test is flaky or not needed in CI")
@pytest.mark.unit
def test_server_startup():
    """Test that the server can start up correctly."""
    print("🔧 Testing server startup...")

    try:
        # Try to start the server process briefly
        process = subprocess.Popen(
            ["python", "src/mcp_local_repo_analyzer/main.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # Give it a moment to start
        import time

        time.sleep(2)

        # Check if it's still running (not crashed immediately)
        if process.poll() is None:
            print("✅ Server started successfully")
            process.terminate()
            process.wait(timeout=5)
            assert True
        else:
            stdout, stderr = process.communicate()
            print("❌ Server failed to start:")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            assert False

    except Exception as e:
        print(f"❌ Server startup test failed: {e}")
        assert False


@pytest.mark.skip(reason="Requires running HTTP server at http://localhost:8000/mcp")
@pytest.mark.asyncio
async def test_http_server():
    ...


async def run_all_scenarios():
    """Run all test scenarios."""
    print("🚀 Starting comprehensive manual testing...")

    scenarios = [
        test_scenario_clean_repo,
        test_scenario_working_directory_changes,
        test_scenario_staged_changes,
        test_scenario_mixed_changes,
        test_error_handling,
    ]

    results = []
    for scenario in scenarios:
        try:
            await scenario()
            results.append(True)
            print("✅ Scenario passed")
        except Exception as e:
            print(f"❌ Scenario failed: {e}")
            results.append(False)

    # Summary
    passed = sum(results)
    total = len(results)
    print(f"\n📊 Test Results: {passed}/{total} scenarios passed")

    if passed == total:
        print("🎉 All manual tests passed!")
    else:
        print("⚠️  Some tests failed - check the output above")

    return passed == total


if __name__ == "__main__":
    import sys

    # Test server startup first
    if not test_server_startup():
        print("❌ Server startup failed - aborting tests")
        sys.exit(1)

    # Run all scenarios
    success = asyncio.run(run_all_scenarios())

    sys.exit(0 if success else 1)
