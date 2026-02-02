"""
Helper utilities for the agentic support bot demo.
"""

from .marimo_helpers import (
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
    # Agent Config Storage (Weave Objects)
    AgentConfig,
    publish_agent_config,
    fetch_weave_configs,
    fetch_config_details,
    # Model Fetching (deprecated - use fetch_weave_configs)
    fetch_weave_models,
)

__all__ = [
    # Constants
    "WEAVE_TRACE_API",
    "WEAVE_OBJS_API",
    "WANDB_BASE_URL",
    "DEFAULT_CHAT_PROMPTS",
    "TOOL_CHAT_PROMPTS",
    # URL Builders
    "weave_traces_url",
    "weave_evals_url",
    "weave_playground_url",
    "trace_peek_url",
    # Environment Helpers
    "save_env_var",
    # File Operations
    "auto_copy_step_files",
    # Trace Fetching
    "fetch_traces_data",
    "build_traces_table_ui",
    "build_traces_section",
    # Chat Widget Helpers
    "create_step_chat_widget",
    # Agent Config Storage (Weave Objects)
    "AgentConfig",
    "publish_agent_config",
    "fetch_weave_configs",
    "fetch_config_details",
    # Model Fetching (deprecated - use fetch_weave_configs)
    "fetch_weave_models",
]
