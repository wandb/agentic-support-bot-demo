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
        import sys
        from pathlib import Path
        
        # Add step-2/part-a to path
        step1_dir = Path(__file__).parent.parent / "examples" / "step-2" / "part-a"
        sys.path.insert(0, str(step1_dir))
        
        import main as main_module
        
        with patch.dict(os.environ, {}, clear=True):
            importlib.reload(main_module)
            
            with pytest.raises(ValueError) as exc_info:
                main_module.validate_environment()
            
            assert "WANDB_API_KEY" in str(exc_info.value)
        
        # Clean up
        sys.path.remove(str(step1_dir))

    def test_all_keys_present_succeeds(self):
        """AC-4: Test that validation succeeds when required keys present."""
        import sys
        from pathlib import Path
        
        # Add step-2/part-a to path
        step1_dir = Path(__file__).parent.parent / "examples" / "step-2" / "part-a"
        sys.path.insert(0, str(step1_dir))
        
        with patch.dict(
            os.environ,
            {"WANDB_API_KEY": "test-wandb-key"},
            clear=True,
        ):
            from main import validate_environment
            
            # Should not raise any exception
            validate_environment()
        
        # Clean up
        sys.path.remove(str(step1_dir))


class TestCreateIssueTool:
    """Test create_issue tool stub."""

    def test_create_issue_returns_required_fields(self):
        """AC-2: Test that create_issue returns all required fields."""
        import sys
        from pathlib import Path
        
        # Add step-2/part-b to path (tools.py is in part-b)
        step2_partb_dir = Path(__file__).parent.parent / "examples" / "step-2" / "part-b"
        sys.path.insert(0, str(step2_partb_dir))
        
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
        import sys
        from pathlib import Path
        
        # Add step-2/part-b to path (tools.py is in part-b)
        step2_partb_dir = Path(__file__).parent.parent / "examples" / "step-2" / "part-b"
        sys.path.insert(0, str(step2_partb_dir))
        
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
        import sys
        from pathlib import Path
        
        # Add step-2/part-b to path (tools.py is in part-b)
        step2_partb_dir = Path(__file__).parent.parent / "examples" / "step-2" / "part-b"
        sys.path.insert(0, str(step2_partb_dir))
        
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
        import sys
        from pathlib import Path
        
        # Add step-2/part-b to path (tools.py is in part-b)
        step2_partb_dir = Path(__file__).parent.parent / "examples" / "step-2" / "part-b"
        sys.path.insert(0, str(step2_partb_dir))
        
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
        import sys
        from pathlib import Path
        
        # Add step-2/part-b to path (tools.py is in part-b)
        step2_partb_dir = Path(__file__).parent.parent / "examples" / "step-2" / "part-b"
        sys.path.insert(0, str(step2_partb_dir))
        
        from tools import TOOLS
        
        assert isinstance(TOOLS, list)
        assert len(TOOLS) == 2  # create_issue, get_issue

    def test_tools_are_callable_functions(self):
        """Test that TOOLS contains callable functions or proper tool definitions."""
        import sys
        from pathlib import Path
        
        # Add step-2/part-b to path (tools.py is in part-b)
        step2_partb_dir = Path(__file__).parent.parent / "examples" / "step-2" / "part-b"
        sys.path.insert(0, str(step2_partb_dir))
        
        from tools import TOOLS
        
        for tool in TOOLS:
            # Support both direct function exports and Slide framework format
            if isinstance(tool, dict):
                # Slide framework format with definition and implementation
                assert "definition" in tool
                assert "implementation" in tool
                assert callable(tool["implementation"])
                # Verify the function has metadata
                impl = tool["implementation"]
                assert hasattr(impl, '__name__')
            else:
                # Direct function export
                assert callable(tool)
                assert hasattr(tool, '__name__')


class TestConfigurationFile:
    """Test that tyler chat configuration file is valid."""

    @pytest.fixture
    def config_path(self):
        """Get path to configuration file (checks both possible names)."""
        base_path = Path(__file__).parent.parent / "examples" / "step-2" / "part-a"
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
        
        # Extract agent config (handle nested structure)
        agent_config = config.get("agent", config)
        
        # Required agent fields
        agent_required = ["name", "model_name", "purpose"]
        for field in agent_required:
            assert field in agent_config, f"Missing required agent field: {field}"
            assert agent_config[field], f"Field {field} is empty"

    def test_config_name_is_valid(self, config_path):
        """Test that agent name is configured correctly."""
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        # Extract agent config (handle nested structure)
        agent_config = config.get("agent", config)
        
        # Agent name should be a non-empty string
        assert isinstance(agent_config["name"], str)
        assert len(agent_config["name"]) > 0

    def test_config_model_is_valid(self, config_path):
        """Test that model name is configured correctly."""
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        # Extract agent config (handle nested structure)
        agent_config = config.get("agent", config)
        
        # Model name should be a non-empty string
        assert isinstance(agent_config["model_name"], str)
        assert len(agent_config["model_name"]) > 0

    def test_config_purpose_is_string(self, config_path):
        """Test that purpose is a non-empty string."""
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        # Extract agent config (handle nested structure)
        agent_config = config.get("agent", config)
        
        assert isinstance(agent_config["purpose"], str)
        assert len(agent_config["purpose"]) > 0

    def test_config_tools_references_tools_file(self, config_path):
        """Test that tools configuration references tools.py if present."""
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        # Tools are optional in starter config
        if "tools" in config:
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
