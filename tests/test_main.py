"""Tests for the agentic support bot agent."""

import os
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch
import importlib.util
import tempfile
from tinydb import TinyDB


def load_tools_module_for_test(db_path):
    """Load tools module with a specific DB path for testing."""
    os.environ["TICKETS_DB_PATH"] = str(db_path)
    tools_path = Path(__file__).parent.parent / "examples" / "step-3" / "tools.py"
    spec = importlib.util.spec_from_file_location("tools_test", tools_path)
    tools = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tools)
    return tools


class TestEnvironmentValidation:
    """Test environment variable validation.
    
    Note: These tests are skipped as the main.py module with validate_environment
    has been refactored out in favor of YAML-based agent configuration.
    """

    @pytest.mark.skip(reason="main.py module no longer exists - validation moved to YAML config")
    def test_missing_wandb_key_raises_error(self):
        """AC-4: Test that missing WANDB_API_KEY raises clear error."""
        pass

    @pytest.mark.skip(reason="main.py module no longer exists - validation moved to YAML config")
    def test_all_keys_present_succeeds(self):
        """AC-4: Test that validation succeeds when required keys present."""
        pass


class TestCreateIssueTool:
    """Test create_issue tool stub."""

    def test_create_issue_returns_required_fields(self):
        """AC-2: Test that create_issue returns all required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_tickets.json"
            # Create empty DB
            TinyDB(str(db_path)).close()
            
            tools = load_tools_module_for_test(db_path)
            
            result = tools.create_issue(
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
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_tickets.json"
            # Create empty DB
            TinyDB(str(db_path)).close()
            
            tools = load_tools_module_for_test(db_path)
            
            result = tools.create_issue(
                title="Urgent Bug",
                description="Critical bug needs fixing",
                priority="high"
            )
            
            assert result["priority"] == "high"
            assert result["title"] == "Urgent Bug"


class TestGetIssueTool:
    """Test get_issue tool with persistence."""

    def test_get_issue_returns_required_fields(self):
        """AC-3: Test that get_issue returns all required fields for existing ticket."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_tickets.json"
            # Create empty DB
            TinyDB(str(db_path)).close()
            
            tools = load_tools_module_for_test(db_path)
            
            # Create a ticket first
            created = tools.create_issue(
                title="Test Issue",
                description="This is a test issue"
            )
            
            # Now retrieve it
            result = tools.get_issue(issue_id=created["id"])
            
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
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_tickets.json"
            # Create empty DB
            TinyDB(str(db_path)).close()
            
            tools = load_tools_module_for_test(db_path)
            
            # Create a ticket
            created = tools.create_issue(
                title="Test Issue",
                description="This is a test issue"
            )
            
            # Retrieve it
            result = tools.get_issue(issue_id=created["id"])
            
            # Should return the created ticket
            assert result["id"] == created["id"]
            assert isinstance(result["title"], str)
            assert isinstance(result["description"], str)


class TestToolsIntegration:
    """Test that tools are properly structured for Tyler CLI."""

    def test_tools_module_exports_tools_list(self):
        """Test that tools.py exports a TOOLS list for tyler chat."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_tickets.json"
            # Create empty DB
            TinyDB(str(db_path)).close()
            
            tools = load_tools_module_for_test(db_path)
            
            assert hasattr(tools, "TOOLS")
            assert isinstance(tools.TOOLS, list)
            assert len(tools.TOOLS) == 2  # create_issue, get_issue

    def test_tools_are_callable_functions(self):
        """Test that TOOLS contains callable functions or proper tool definitions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_tickets.json"
            # Create empty DB
            TinyDB(str(db_path)).close()
            
            tools = load_tools_module_for_test(db_path)
            
            for tool in tools.TOOLS:
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
        """Get path to configuration file (checks possible names)."""
        base_path = Path(__file__).parent.parent / "examples" / "step-2"
        # Check for various config file names in order of preference
        for filename in ["basic-agent-config.yaml", "tyler-chat-config.yaml", "support-bot.yaml"]:
            config_file = base_path / filename
            if config_file.exists():
                return config_file
        # Default to basic-agent-config.yaml for the assertion error
        return base_path / "basic-agent-config.yaml"

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
