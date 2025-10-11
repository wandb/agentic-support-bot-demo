"""Tests for the agentic support bot agent."""

import os
import pytest
import yaml
from pathlib import Path
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
    """Test that tools are properly structured for Tyler CLI."""

    def test_tools_module_exports_tools_list(self):
        """Test that tools.py exports a TOOLS list for tyler chat."""
        from tools import TOOLS
        
        assert isinstance(TOOLS, list)
        assert len(TOOLS) == 2

    def test_tools_are_callable_functions(self):
        """Test that TOOLS contains callable functions."""
        from tools import TOOLS
        
        for tool in TOOLS:
            assert callable(tool)
            # Functions decorated with @tool should have metadata
            assert hasattr(tool, '__name__')
            assert hasattr(tool, '__doc__')


class TestConfigurationFile:
    """Test that tyler chat configuration file is valid."""

    @pytest.fixture
    def config_path(self):
        """Get path to configuration file (checks both possible names)."""
        base_path = Path(__file__).parent.parent
        # Check for tyler-chat-config.yaml first, then support-bot.yaml
        for filename in ["tyler-chat-config.yaml", "support-bot.yaml"]:
            config_file = base_path / filename
            if config_file.exists():
                return config_file
        # Default to tyler-chat-config.yaml for the assertion error
        return base_path / "tyler-chat-config.yaml"

    def test_config_file_exists(self, config_path):
        """Test that support-bot.yaml exists."""
        assert config_path.exists(), f"Configuration file not found at {config_path}"

    def test_config_valid_yaml(self, config_path):
        """Test that configuration file is valid YAML."""
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        assert config is not None
        assert isinstance(config, dict)

    def test_config_has_required_fields(self, config_path):
        """Test that configuration has all required fields."""
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        # Required fields for tyler chat
        required_fields = ["name", "model_name", "purpose", "tools"]
        
        for field in required_fields:
            assert field in config, f"Missing required field: {field}"
            assert config[field], f"Field {field} is empty"

    def test_config_name_is_valid(self, config_path):
        """Test that agent name is configured correctly."""
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        # Agent name should be a non-empty string
        assert isinstance(config["name"], str)
        assert len(config["name"]) > 0

    def test_config_model_is_valid(self, config_path):
        """Test that model name is configured correctly."""
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        # Model name should be a non-empty string
        assert isinstance(config["model_name"], str)
        assert len(config["model_name"]) > 0

    def test_config_purpose_is_string(self, config_path):
        """Test that purpose is a non-empty string."""
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        assert isinstance(config["purpose"], str)
        assert len(config["purpose"]) > 0
        # Should mention support bot functionality
        assert "support" in config["purpose"].lower()

    def test_config_tools_references_tools_file(self, config_path):
        """Test that tools configuration references tools.py."""
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        assert isinstance(config["tools"], list)
        assert len(config["tools"]) > 0
        # Should reference tools.py
        assert any("tools.py" in str(tool) for tool in config["tools"])

    def test_config_optional_fields_have_valid_types(self, config_path):
        """Test that optional fields have correct types if present."""
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        # Optional fields and their expected types
        optional_fields = {
            "temperature": (int, float),
            "max_tool_iterations": int,
            "notes": str,
        }
        
        for field, expected_type in optional_fields.items():
            if field in config:
                assert isinstance(config[field], expected_type), \
                    f"Field {field} should be {expected_type}, got {type(config[field])}"
