"""Tests for the agentic support bot agent."""

import os
import pytest
from unittest.mock import patch


class TestEnvironmentValidation:
    """Test environment variable validation."""

    @pytest.mark.usefixtures()  # Don't use autofixtures for this test
    def test_missing_wandb_key_raises_error(self):
        """AC-4: Test that missing WANDB_API_KEY raises clear error."""
        import importlib
        import main as main_module
        
        with patch.dict(os.environ, {}, clear=True):
            importlib.reload(main_module)
            
            with pytest.raises(ValueError) as exc_info:
                main_module.validate_environment()
            
            assert "WANDB_API_KEY" in str(exc_info.value)

    def test_all_keys_present_succeeds(self):
        """AC-4: Test that validation succeeds when required keys present."""
        with patch.dict(
            os.environ,
            {"WANDB_API_KEY": "test-wandb-key"},
            clear=True,
        ):
            from main import validate_environment
            
            # Should not raise any exception
            validate_environment()


class TestCreateIssueTool:
    """Test create_issue tool stub."""

    def test_create_issue_returns_required_fields(self):
        """AC-2: Test that create_issue returns all required fields."""
        from tools import create_issue
        
        result = create_issue(
            title="Test Issue",
            description="This is a test issue"
        )
        
        # Verify all required fields are present
        assert "id" in result
        assert "title" in result
        assert "description" in result
        assert "status" in result
        assert "priority" in result
        assert "created_at" in result
        
        # Verify values
        assert result["title"] == "Test Issue"
        assert result["description"] == "This is a test issue"
        assert result["status"] == "open"
        assert result["priority"] == "medium"  # default

    def test_create_issue_with_priority_parameter(self):
        """AC-2: Test that create_issue accepts priority parameter."""
        from tools import create_issue
        
        result = create_issue(
            title="Urgent Bug",
            description="Critical bug needs fixing",
            priority="high"
        )
        
        assert result["priority"] == "high"
        assert result["title"] == "Urgent Bug"


class TestGetIssueTool:
    """Test get_issue tool stub."""

    def test_get_issue_returns_required_fields(self):
        """AC-3: Test that get_issue returns all required fields."""
        from tools import get_issue
        
        result = get_issue(issue_id="test-123")
        
        # Verify all required fields are present
        assert "id" in result
        assert "title" in result
        assert "description" in result
        assert "status" in result
        assert "priority" in result
        assert "created_at" in result
        assert "updated_at" in result

    def test_get_issue_with_valid_id(self):
        """AC-3: Test that get_issue accepts issue_id parameter."""
        from tools import get_issue
        
        test_id = "issue-456"
        result = get_issue(issue_id=test_id)
        
        # For stub, it should return mock data for any ID
        assert result["id"] == test_id
        assert isinstance(result["title"], str)
        assert isinstance(result["description"], str)


class TestToolsIntegration:
    """Test that tools are properly structured for Tyler."""

    def test_get_tools_returns_list(self):
        """Test that get_tools returns a list of tool definitions."""
        from tools import get_tools
        
        tools = get_tools()
        
        assert isinstance(tools, list)
        assert len(tools) == 2

    def test_tools_have_correct_structure(self):
        """Test that tools follow Tyler format."""
        from tools import get_tools
        
        tools = get_tools()
        
        for tool in tools:
            assert "definition" in tool
            assert "implementation" in tool
            assert "type" in tool["definition"]
            assert "function" in tool["definition"]
            assert tool["definition"]["type"] == "function"
            
            func_def = tool["definition"]["function"]
            assert "name" in func_def
            assert "description" in func_def
            assert "parameters" in func_def
