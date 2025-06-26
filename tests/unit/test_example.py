"""
Example test file for mcp_local_repo_analyzer.
"""

import pytest


class TestExample:
    """Example test class."""
    
    @pytest.mark.unit
    def test_example(self):
        """Example test method."""
        assert True
    
    @pytest.mark.unit
    def test_string_operations(self):
        """Test string operations."""
        text = "mcp_local_repo_analyzer"
        assert "analyzer" in text
        assert len(text) > 0
