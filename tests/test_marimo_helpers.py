"""
Tests for marimo_helpers module.

Tests the helper functions used by marimo-guide.py for trace fetching,
URL building, file operations, and other utilities.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helpers.marimo_helpers import (
    # Constants
    WEAVE_TRACE_API,
    WEAVE_OBJS_API,
    WANDB_BASE_URL,
    DEFAULT_CHAT_PROMPTS,
    TOOL_CHAT_PROMPTS,
    # URL Builders
    weave_traces_url,
    weave_evals_url,
    weave_playground_url,
    trace_peek_url,
    # Environment Helpers
    save_env_var,
    # File Operations
    auto_copy_step_files,
    # Trace Fetching
    fetch_traces_data,
    build_traces_table_ui,
    build_traces_section,
    # Chat Widget Helpers
    create_step_chat_widget,
    # Model Fetching
    fetch_weave_models,
)


# =============================================================================
# CONSTANTS TESTS
# =============================================================================

class TestConstants:
    """Test that constants are defined correctly."""
    
    def test_api_endpoints_defined(self):
        """API endpoints should be valid URLs."""
        assert WEAVE_TRACE_API.startswith("https://")
        assert WEAVE_OBJS_API.startswith("https://")
        assert WANDB_BASE_URL.startswith("https://")
    
    def test_default_prompts_not_empty(self):
        """Default prompts should have content."""
        assert len(DEFAULT_CHAT_PROMPTS) > 0
        assert all(isinstance(p, str) for p in DEFAULT_CHAT_PROMPTS)
        assert all(len(p) > 0 for p in DEFAULT_CHAT_PROMPTS)
    
    def test_tool_prompts_not_empty(self):
        """Tool prompts should have content."""
        assert len(TOOL_CHAT_PROMPTS) > 0
        assert all(isinstance(p, str) for p in TOOL_CHAT_PROMPTS)


# =============================================================================
# URL BUILDER TESTS
# =============================================================================

class TestURLBuilders:
    """Test URL building functions."""
    
    def test_weave_traces_url(self):
        """Should build correct traces URL."""
        url = weave_traces_url("test-entity", "test-project")
        assert url == "https://wandb.ai/test-entity/test-project/weave/traces"
    
    def test_weave_evals_url(self):
        """Should build correct evaluations URL."""
        url = weave_evals_url("my-entity", "my-project")
        assert url == "https://wandb.ai/my-entity/my-project/weave/evaluations"
    
    def test_weave_playground_url(self):
        """Should build correct playground URL."""
        url = weave_playground_url("entity", "project")
        assert url == "https://wandb.ai/entity/project/weave/playground"
    
    def test_trace_peek_url(self):
        """Should build correct trace peek URL with encoded path."""
        url = trace_peek_url("entity", "project", "trace-123")
        assert "wandb.ai/entity/project/weave/traces" in url
        assert "peekPath=" in url
        assert "trace-123" in url


# =============================================================================
# ENVIRONMENT HELPERS TESTS
# =============================================================================

class TestSaveEnvVar:
    """Test save_env_var function."""
    
    def test_save_new_var(self, tmp_path, monkeypatch):
        """Should add new variable to .env file."""
        monkeypatch.chdir(tmp_path)
        
        # Create empty .env
        env_file = tmp_path / ".env"
        env_file.write_text("")
        
        save_env_var("TEST_KEY", "test_value")
        
        content = env_file.read_text()
        assert "TEST_KEY=test_value" in content
    
    def test_update_existing_var(self, tmp_path, monkeypatch):
        """Should update existing variable."""
        monkeypatch.chdir(tmp_path)
        
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_KEY=old_value\nOTHER_KEY=other")
        
        save_env_var("TEST_KEY", "new_value")
        
        content = env_file.read_text()
        assert "TEST_KEY=new_value" in content
        assert "old_value" not in content
        assert "OTHER_KEY=other" in content
    
    def test_creates_env_from_example(self, tmp_path, monkeypatch):
        """Should create .env from .env.example if it doesn't exist."""
        monkeypatch.chdir(tmp_path)
        
        # Create .env.example
        example_file = tmp_path / ".env.example"
        example_file.write_text("EXAMPLE_VAR=example")
        
        save_env_var("NEW_KEY", "new_value")
        
        env_file = tmp_path / ".env"
        assert env_file.exists()
        content = env_file.read_text()
        assert "EXAMPLE_VAR=example" in content
        assert "NEW_KEY=new_value" in content


# =============================================================================
# FILE OPERATIONS TESTS
# =============================================================================

class TestAutoCopyStepFiles:
    """Test auto_copy_step_files function."""
    
    def test_copies_files_when_config_missing(self, tmp_path, monkeypatch):
        """Should copy files when config doesn't exist."""
        monkeypatch.chdir(tmp_path)
        
        # Create source directory with files
        source_dir = tmp_path / "examples" / "step-2"
        source_dir.mkdir(parents=True)
        (source_dir / "main.py").write_text("# main")
        (source_dir / "tyler-chat-config.yaml").write_text("name: test")
        
        # Run auto-copy
        copied = auto_copy_step_files(2)
        
        # Check files were copied
        dest_dir = tmp_path / "workspace" / "step-2"
        assert dest_dir.exists()
        assert (dest_dir / "main.py").exists()
        assert (dest_dir / "tyler-chat-config.yaml").exists()
        assert "main.py" in copied
        assert "tyler-chat-config.yaml" in copied
    
    def test_skips_existing_files_but_copies_new_ones(self, tmp_path, monkeypatch):
        """Should skip files that exist but copy files that don't."""
        monkeypatch.chdir(tmp_path)
        
        # Create source directory
        source_dir = tmp_path / "examples" / "step-3"
        source_dir.mkdir(parents=True)
        (source_dir / "new_file.py").write_text("# new")
        (source_dir / "tyler-chat-config.yaml").write_text("name: source")
        
        # Create destination with existing config (simulates user customization)
        dest_dir = tmp_path / "workspace" / "step-3"
        dest_dir.mkdir(parents=True)
        (dest_dir / "tyler-chat-config.yaml").write_text("name: existing")
        
        # Run auto-copy
        copied = auto_copy_step_files(3)
        
        # Should copy new_file.py but NOT overwrite existing config
        assert "new_file.py" in copied
        assert "tyler-chat-config.yaml" not in copied
        # Verify existing config was NOT overwritten
        assert (dest_dir / "tyler-chat-config.yaml").read_text() == "name: existing"
        # Verify new file was copied
        assert (dest_dir / "new_file.py").exists()
        assert (dest_dir / "new_file.py").read_text() == "# new"
    
    def test_returns_empty_when_no_source_files(self, tmp_path, monkeypatch):
        """Should return empty list when no source files exist."""
        monkeypatch.chdir(tmp_path)
        
        # No source directory
        copied = auto_copy_step_files(99)
        
        assert copied == []


# =============================================================================
# TRACE FETCHING TESTS
# =============================================================================

class TestFetchTracesData:
    """Test fetch_traces_data function."""
    
    def test_returns_error_when_no_token(self):
        """Should return error when no token provided."""
        table_data, error = fetch_traces_data(
            "entity", "project", "2024-01-01T00:00:00+00:00", ""
        )
        
        assert table_data is None
        assert error == "WANDB_API_KEY not set"
    
    @patch("requests.post")
    def test_returns_error_on_api_failure(self, mock_post):
        """Should return error on API failure."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        table_data, error = fetch_traces_data(
            "entity", "project", "2024-01-01T00:00:00+00:00", "token"
        )
        
        assert table_data is None
        assert "500" in error
    
    @patch("requests.post")
    def test_returns_data_on_success(self, mock_post):
        """Should return table data on success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            "id": "trace-123",
            "started_at": "2024-01-01T12:00:00Z",
            "summary": {
                "weave": {
                    "status": "success",
                    "latency_ms": 1500,
                    "costs": {
                        "gpt-4": {
                            "prompt_tokens_total_cost": 0.01,
                            "completion_tokens_total_cost": 0.02
                        }
                    }
                }
            }
        })
        mock_post.return_value = mock_response
        
        table_data, error = fetch_traces_data(
            "entity", "project", "2024-01-01T00:00:00+00:00", "token"
        )
        
        assert error is None
        assert len(table_data) == 1
        assert table_data[0]["Trace ID"] == "trace-123"
        assert table_data[0]["Latency"] == "1.500s"
        assert table_data[0]["Cost"] == "$0.0300"  # 0.01 + 0.02


# =============================================================================
# MODEL FETCHING TESTS
# =============================================================================

class TestFetchWeaveModels:
    """Test fetch_weave_models function."""
    
    def test_returns_empty_when_no_token(self):
        """Should return empty dict when no token."""
        result = fetch_weave_models("entity", "project", "")
        assert result == {}
    
    @patch("requests.post")
    def test_excludes_judge_models(self, mock_post):
        """Should exclude safety-judge and accuracy-judge models."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "objs": [
                {"object_id": "my-agent", "version_index": 0},
                {"object_id": "safety-judge", "version_index": 0},
                {"object_id": "accuracy-judge", "version_index": 0},
            ]
        }
        mock_post.return_value = mock_response
        
        result = fetch_weave_models("entity", "project", "token")
        
        assert "my-agent" in result
        assert "safety-judge" not in result
        assert "accuracy-judge" not in result
    
    @patch("requests.post")
    def test_groups_versions_correctly(self, mock_post):
        """Should group versions by model name."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "objs": [
                {"object_id": "buzz", "version_index": 0},
                {"object_id": "buzz", "version_index": 1},
                {"object_id": "buzz", "version_index": 2},
            ]
        }
        mock_post.return_value = mock_response
        
        result = fetch_weave_models("entity", "project", "token")
        
        assert "buzz" in result
        assert result["buzz"] == ["v2", "v1", "v0"]  # Sorted descending


# =============================================================================
# UI BUILDER TESTS
# =============================================================================

class TestBuildTracesSection:
    """Test build_traces_section function."""
    
    def test_shows_table_when_available(self):
        """Should include traces table when available."""
        mo = MagicMock()
        mo.md.return_value = "markdown"
        traces_table = MagicMock()
        
        components = build_traces_section(
            mo, traces_table, None, MagicMock(), "http://traces"
        )
        
        assert traces_table in components
    
    def test_no_traces_yet_shows_nothing(self):
        """Should not show anything when no traces yet - just the header."""
        mo = MagicMock()
        mo.md.return_value = "markdown"
        mo.callout.return_value = "callout"
        
        # Chat widget with messages (so we're waiting for traces)
        chat_widget = MagicMock()
        chat_widget.value = [{"role": "user", "content": "test"}]
        
        # When no traces and no error, we pass None for both
        components = build_traces_section(
            mo, None, None, chat_widget, "http://traces"
        )
        
        # Should NOT have called callout
        mo.callout.assert_not_called()
        # Components should just have the header (1 item)
        assert len(components) == 1


class TestCreateStepChatWidget:
    """Test create_step_chat_widget function."""
    
    def test_returns_empty_when_no_agent(self):
        """Should return empty display when agent is None."""
        mo = MagicMock()
        mo.md.return_value = "markdown"
        
        status, widget = create_step_chat_widget(
            mo, None, "", Path("config.yaml"), lambda x: x
        )
        
        assert widget is None
    
    def test_returns_error_display_on_error(self):
        """Should return error callout when agent_status indicates error."""
        mo = MagicMock()
        mo.callout.return_value = "error_callout"
        mo.md.return_value = "markdown"
        
        status, widget = create_step_chat_widget(
            mo, None, "❌ Failed to load", Path("config.yaml"), lambda x: x
        )
        
        assert widget is None
        mo.callout.assert_called()
    
    def test_creates_widget_when_agent_exists(self):
        """Should create chat widget when agent is provided."""
        mo = MagicMock()
        mo.callout.return_value = "status"
        mo.md.return_value = "markdown"
        mo.ui.chat.return_value = "chat_widget"
        
        agent = MagicMock()
        adapter_fn = MagicMock(return_value="chat_function")
        
        status, widget = create_step_chat_widget(
            mo, agent, "✅ Loaded", Path("config.yaml"), adapter_fn
        )
        
        assert widget == "chat_widget"
        adapter_fn.assert_called_once()
        mo.ui.chat.assert_called_once()
