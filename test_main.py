"""Tests for the agentic support bot agent."""

import os
import pytest
from unittest.mock import patch, MagicMock


class TestEnvironmentValidation:
    """Test environment variable validation."""

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
            {
                "WANDB_API_KEY": "test-wandb-key",
            },
            clear=True,
        ):
            from main import validate_environment
            
            # Should not raise any exception
            validate_environment()


class TestWeaveIntegration:
    """Test Weave observability integration."""

    @patch("main.weave")
    def test_weave_initialized_with_correct_project(self, mock_weave):
        """AC-1: Test that Weave is initialized with correct project name."""
        with patch.dict(
            os.environ,
            {
                "WANDB_API_KEY": "test-wandb-key",
            },
            clear=True,
        ):
            from main import initialize_weave
            
            initialize_weave()
            
            # Verify weave.init was called with the correct project name
            mock_weave.init.assert_called_once_with("agentic-support-bot-demo")


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


class TestTylerAgentInitialization:
    """Test Tyler agent creation and configuration."""

    def test_agent_created_with_correct_model(self):
        """Test that agent is created with gpt-4.1 model."""
        with patch.dict(
            os.environ,
            {
                "WANDB_API_KEY": "test-wandb-key",
            },
            clear=True,
        ):
            from main import create_agent
            import weave
            
            agent = create_agent()
            
            assert agent.model_name == "gpt-4.1"
            assert agent.name == "support-bot"
            # Verify purpose is a Weave StringPrompt object
            assert isinstance(agent.purpose, weave.StringPrompt)

    def test_agent_has_both_tools_registered(self):
        """Test that agent has create_issue and get_issue tools."""
        with patch.dict(
            os.environ,
            {
                "WANDB_API_KEY": "test-wandb-key",
            },
            clear=True,
        ):
            from main import create_agent
            
            agent = create_agent()
            
            # Agent should have tools registered
            assert agent.tools is not None
            assert len(agent.tools) >= 2  # At least our two custom tools

