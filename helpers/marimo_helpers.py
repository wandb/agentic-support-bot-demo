"""
Marimo Guide Helper Functions

Reusable helpers for the marimo-guide.py notebook to reduce code duplication
and improve maintainability.
"""

import json
import os
import shutil
from datetime import datetime
from glob import glob
from pathlib import Path
from typing import Any, Callable, Optional, Tuple, List, Dict
from urllib.parse import quote

# =============================================================================
# CONSTANTS
# =============================================================================

# API Endpoints
WEAVE_TRACE_API = "https://trace.wandb.ai/calls/stream_query"
WEAVE_OBJS_API = "https://trace.wandb.ai/objs/query"
WANDB_BASE_URL = "https://wandb.ai"

# Default prompts used across chat widgets in multiple steps
DEFAULT_CHAT_PROMPTS = [
    "How do I initialize Weave in Python?",
    "I'm getting API timeout errors. Can you help?",
    "What's the status of ticket #10234?",
    "Can you explain how to track model performance in wandb?",
    "I need to create a support ticket for authentication issues"
]

# Shorter prompts for steps with tools (Step 3)
TOOL_CHAT_PROMPTS = [
    "How do I initialize Weave in Python?",
    "I'm getting API timeout errors. Can you help?",
    "What's the status of ticket #10234?",
    "Can you create a ticket for my authentication issue?",
]


# =============================================================================
# URL BUILDERS
# =============================================================================

def weave_traces_url(entity: str, project: str) -> str:
    """Build URL to Weave traces page."""
    return f"{WANDB_BASE_URL}/{entity}/{project}/weave/traces"


def weave_evals_url(entity: str, project: str) -> str:
    """Build URL to Weave evaluations page."""
    return f"{WANDB_BASE_URL}/{entity}/{project}/weave/evaluations"


def weave_playground_url(entity: str, project: str) -> str:
    """Build URL to Weave playground page."""
    return f"{WANDB_BASE_URL}/{entity}/{project}/weave/playground"


def trace_peek_url(entity: str, project: str, trace_id: str) -> str:
    """Build URL to view a specific trace in Weave."""
    base = weave_traces_url(entity, project)
    # URL encode the path components
    peek_path = quote(f"/{entity}/{project}/calls/{trace_id}")
    return f"{base}?view=traces_default&peekPath={peek_path}"


# =============================================================================
# W&B INFERENCE HELPERS
# =============================================================================

WANDB_INFERENCE_API = "https://api.inference.wandb.ai/v1"

def fetch_wandb_inference_models(wandb_token: str) -> Tuple[List[str], Optional[str]]:
    """
    Fetch available models from W&B Inference API.
    
    Args:
        wandb_token: W&B API token for authentication
        
    Returns:
        Tuple of (model_ids, error_message) - error_message is None on success
    """
    import requests
    
    if not wandb_token:
        return [], "WANDB_API_KEY not set"
    
    try:
        response = requests.get(
            f"{WANDB_INFERENCE_API}/models",
            headers={
                "Authorization": f"Bearer {wandb_token}",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        if response.status_code != 200:
            return [], f"Failed to fetch models: HTTP {response.status_code}"
        
        data = response.json()
        models = data.get("data", [])
        
        # Extract model IDs
        model_ids = [m.get("id") for m in models if m.get("id")]
        
        return model_ids, None
        
    except requests.exceptions.Timeout:
        return [], "Request timed out"
    except Exception as e:
        return [], f"Error fetching models: {str(e)}"


# =============================================================================
# ENVIRONMENT HELPERS
# =============================================================================

def save_env_var(key: str, value: str) -> None:
    """
    Save a single environment variable to .env file AND os.environ.
    
    Creates .env from .env.example if it doesn't exist.
    Updates existing key or appends new one.
    Also updates os.environ so changes are immediately available.
    
    Args:
        key: Environment variable name
        value: Value to set
    """
    env_path = Path(".env")
    
    # Create .env from example if it doesn't exist
    if not env_path.exists():
        example_path = Path(".env.example")
        if example_path.exists():
            env_path.write_text(example_path.read_text())
    
    # Read current content
    content = env_path.read_text() if env_path.exists() else ""
    lines = content.split('\n') if content else []
    
    # Update or add the key
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    
    if not found:
        lines.append(f"{key}={value}")
    
    # Write back to .env file
    env_path.write_text('\n'.join(lines))
    
    # ALSO update os.environ so changes are immediately available
    # This ensures weave.init() and other code sees the new value
    os.environ[key] = value


# =============================================================================
# FILE OPERATIONS
# =============================================================================

def auto_copy_step_files(step_num: int, source_dir: Optional[str] = None) -> List[str]:
    """
    Auto-copy files for a step to workspace/step-{N}/.
    
    Only copies files that don't already exist in the destination.
    
    Args:
        step_num: Step number (2, 3, 4, 5, etc.)
        source_dir: Override source directory (default: examples/step-{N})
        
    Returns:
        List of filenames that were copied (empty if all files already exist)
    """
    source_dir = source_dir or f"examples/step-{step_num}"
    dest = Path(f"workspace/step-{step_num}")
    
    # Find source files
    source_files = glob(f"{source_dir}/*.py") + glob(f"{source_dir}/*.yaml")
    if not source_files:
        return []
    
    # Create destination and copy only files that don't exist
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    for src in source_files:
        filename = Path(src).name
        dest_file = dest / filename
        # Only copy if destination file doesn't already exist
        if not dest_file.exists():
            shutil.copy2(src, dest_file)
            copied.append(filename)
    
    return copied


# =============================================================================
# TRACE FETCHING
# =============================================================================

def fetch_traces_data(
    weave_entity: str,
    weave_project: str,
    session_start_time: str,
    wandb_token: str,
    limit: int = 50,
    display_limit: int = 10
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Fetch recent traces from Weave API.
    
    Args:
        weave_entity: Weave entity name
        weave_project: Weave project name
        session_start_time: ISO timestamp to filter traces after
        wandb_token: W&B API token for authentication
        limit: Max traces to fetch from API
        display_limit: Max traces to return for display
        
    Returns:
        Tuple of (table_data, error_message) - one will be None
        table_data is a list of dicts with keys: Time, Status, Latency, Cost, Trace ID, Link
    """
    import requests
    
    if not wandb_token:
        return None, "WANDB_API_KEY not set"
    
    try:
        headers = {"Content-Type": "application/json"}
        
        # Convert session start time to format without Z suffix (API requirement)
        session_start_no_tz = session_start_time.split('+')[0].rstrip('Z')
        
        query_payload = {
            "project_id": f"{weave_entity}/{weave_project}",
            "filter": {
                "trace_roots_only": True,
                "op_names": [f"weave:///{weave_entity}/{weave_project}/op/Agent.stream:*"]
            },
            "query": {
                "$expr": {
                    "$gte": [
                        {"$getField": "started_at"},
                        {"$literal": session_start_no_tz}
                    ]
                }
            },
            "limit": limit,
            "offset": 0,
            "sort_by": [{"field": "started_at", "direction": "desc"}],
            "include_costs": True,
            "include_feedback": False,
        }
        
        response = requests.post(
            WEAVE_TRACE_API,
            headers=headers,
            json=query_payload,
            auth=("api", wandb_token),
            timeout=10
        )
        
        if response.status_code != 200:
            return None, f"Failed to fetch traces: HTTP {response.status_code}"
        
        # Parse newline-delimited JSON response
        json_objects = response.text.strip().split("\n")
        traces = [json.loads(obj) for obj in json_objects if obj]
        
        if not traces:
            return None, None  # No traces yet - will just not show the table
        
        # Build table data
        table_data = []
        for trace in traces[:display_limit]:
            trace_id = trace.get('id', '')
            trace_url = trace_peek_url(weave_entity, weave_project, trace_id)
            
            # Format timestamp
            started_at = trace.get('started_at', '')
            if started_at:
                dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                time_str = 'N/A'
            
            # Get status from summary
            status = trace.get('summary', {}).get('weave', {}).get('status', 'unknown')
            
            # Get latency (convert from ms to seconds)
            latency_ms = trace.get('summary', {}).get('weave', {}).get('latency_ms', 0)
            latency_str = f"{latency_ms / 1000.0:.3f}s" if latency_ms else 'N/A'
            
            # Get cost
            costs = trace.get('costs', {})
            if costs:
                total_cost = sum(costs.values())
                cost_str = f"${total_cost:.4f}" if total_cost > 0 else "$0.00"
            else:
                cost_str = 'N/A'
            
            table_data.append({
                "Time": time_str,
                "Status": status,
                "Latency": latency_str,
                "Cost": cost_str,
                "Trace ID": trace_id,
                "Link": trace_url
            })
        
        return table_data, None
        
    except Exception as e:
        return None, f"Error fetching traces: {str(e)}"


def build_traces_table_ui(mo, table_data: List[Dict[str, Any]]):
    """
    Build a marimo table UI from trace data.
    
    Args:
        mo: marimo module (must be passed from notebook context)
        table_data: List of dicts from fetch_traces_data
        
    Returns:
        mo.ui.table with clickable trace links
    """
    return mo.ui.table(
        [
            {
                "Link": mo.md(f"[{row['Trace ID']}]({row['Link']})"),
                "Latency": row["Latency"],
                "Cost": row["Cost"]
            }
            for row in table_data
        ],
        selection=None
    )


def build_traces_section(
    mo,
    traces_table,
    traces_error: Optional[str],
    chat_widget,
    traces_url: str
) -> List[Any]:
    """
    Build the traces section UI components for a step.
    
    Args:
        mo: marimo module
        traces_table: The traces table widget (or None)
        traces_error: Error message (or None)
        chat_widget: The chat widget (to check message count)
        traces_url: URL to all traces page
        
    Returns:
        List of marimo UI components to render
    """
    components = [
        mo.md("""
        ## 
                   
        Each time you send a message to the chat above, Weave creates a trace of the agent's execution. Traces will appear below:
        """)
    ]
    
    if traces_table is not None:
        components.extend([
            traces_table,
            mo.md(f"""
            💡 **Tip:** Click on the trace link to view the full execution details in Weave, including inputs, outputs, and timing information, or view all traces in [your project]({traces_url})
            """)
        ])
    elif traces_error:
        # Show warning only for actual errors
        components.append(
            mo.callout(
                mo.md(f"⚠️ {traces_error}"),
                kind="warn"
            )
        )
    # Otherwise, just don't show anything - traces will appear when available
    
    return components


# =============================================================================
# CHAT WIDGET HELPERS
# =============================================================================

def create_step_chat_widget(
    mo,
    agent,
    agent_status: str,
    config_path: Path,
    chat_adapter_fn: Callable,
    prompts: Optional[List[str]] = None,
    object_name: str = "AgentConfig"
) -> Tuple[Any, Any]:
    """
    Create chat widget and status display for a step.
    
    Args:
        mo: marimo module
        agent: Loaded Tyler agent (or None)
        agent_status: Status message from agent loading
        config_path: Path to agent config file
        chat_adapter_fn: Function to create chat adapter (e.g., create_chat_adapter_subprocess)
        prompts: Optional list of suggested prompts (default: DEFAULT_CHAT_PROMPTS)
        object_name: Weave object name for config versioning (e.g., "BasicAgentConfig")
        
    Returns:
        Tuple of (status_display, chat_widget) - chat_widget may be None on error
    """
    prompts = prompts or DEFAULT_CHAT_PROMPTS
    
    if agent is not None:
        # Tyler vercel_objects mode yields Vercel AI SDK dicts
        # Marimo (0.19.3+) auto-detects via ChunkSerializer (PR #7837)
        chat_function = chat_adapter_fn(config_path, object_name)
        
        # Show agent status (success)
        status_display = mo.callout(
            mo.md(agent_status),
            kind="success"
        )
        
        chat_widget = mo.ui.chat(
            chat_function,
            prompts=prompts,
            show_configuration_controls=False
        )
        
        return status_display, chat_widget
    
    elif agent_status and agent_status.startswith("❌"):
        # Show error status if agent failed to load
        status_display = mo.callout(
            mo.md(agent_status),
            kind="danger"
        )
        return status_display, None
    
    else:
        # No agent, no error (files don't exist yet)
        return mo.md(""), None


# =============================================================================
# AGENT CONFIG STORAGE (Weave Objects)
# =============================================================================

# Import weave at module level for the weave.Object base class
import weave


class AgentConfig(weave.Object):
    """
    Agent configuration stored as a Weave Object.
    
    This allows versioning and tracking of agent configs in Weave without
    the serialization issues that come with storing the full Agent object.
    
    Attributes:
        name: Agent name (from config YAML)
        yaml: Full YAML configuration content
    """
    name: str
    yaml: str


def publish_agent_config(name: str, yaml_content: str, object_name: str = "AgentConfig") -> Optional[Any]:
    """
    Publish agent config to Weave.
    
    Publishes under the specified object name so all versions are tracked together.
    Different steps can use different object names (BasicAgentConfig, AgentWithToolsConfig, etc.)
    
    Args:
        name: Agent name (stored in the config)
        yaml_content: Full YAML configuration content
        object_name: Weave object name (e.g., "BasicAgentConfig", "SupportAgentConfig")
        
    Returns:
        Weave ref object on success, None on failure.
        Use ref.uri() to get URI string for weave.attributes()
        Use ref.get() to retrieve the object
    """
    
    try:
        # Check for valid credentials (skip if placeholders)
        project = os.getenv("WANDB_PROJECT", "")
        api_key = os.getenv("WANDB_API_KEY", "")
        
        # Skip if using placeholder values to avoid error spam
        is_placeholder = (
            not project or
            not api_key or
            "your-entity" in project.lower() or
            "yourname" in project.lower()
        )
        if is_placeholder:
            return None
        
        # Note: Weave should already be initialized at notebook level
        # No need to call weave.init() here - just publish directly
        
        # Create and publish config object (use specified object name)
        config = AgentConfig(name=name, yaml=yaml_content)
        ref = weave.publish(config, name=object_name)
        
        # Return the ref object (caller can use ref.uri(), ref.get(), etc.)
        return ref
        
    except Exception as e:
        # Log error but don't crash - auto-publish should be silent
        import sys
        print(f"Warning: Failed to publish config to Weave: {e}", file=sys.stderr)
        return None


def fetch_weave_configs(
    weave_entity: str,
    weave_project: str,
    wandb_token: str,
    excluded_configs: Optional[set] = None
) -> Dict[str, List[str]]:
    """
    Fetch all AgentConfig versions from Weave.
    
    Args:
        weave_entity: Weave entity name
        weave_project: Weave project name
        wandb_token: W&B API token
        excluded_configs: Set of config names to exclude (default: scoring judges)
        
    Returns:
        Dict mapping config name to list of versions (e.g., {"Buzz": ["v4", "v3", "v2"]})
    """
    import requests
    
    if excluded_configs is None:
        excluded_configs = {"safety-judge", "accuracy-judge"}
    
    if not wandb_token:
        return {}
    
    try:
        project_id = f"{weave_entity}/{weave_project}"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "project_id": project_id,
            "filter": {
                "base_object_classes": ["AgentConfig"],
                "latest_only": False
            },
            "sort_by": [{"field": "created_at", "direction": "desc"}],
            "limit": 100
        }
        
        response = requests.post(
            WEAVE_OBJS_API,
            headers=headers,
            json=payload,
            auth=("api", wandb_token),
            timeout=10
        )
        
        if response.status_code != 200:
            return {}
        
        data = response.json()
        
        # Group by config name, collect versions
        configs_dict = {}
        for obj in data.get("objs", []):
            object_id = obj.get("object_id", "")
            version_index = obj.get("version_index", 0)
            
            if object_id in excluded_configs:
                continue
            
            if object_id not in configs_dict:
                configs_dict[object_id] = []
            configs_dict[object_id].append(f"v{version_index}")
        
        # Sort versions descending (v4, v3, v2, ...)
        for config_name in configs_dict:
            configs_dict[config_name].sort(key=lambda v: int(v[1:]), reverse=True)
        
        return configs_dict
        
    except Exception:
        return {}


# =============================================================================
# MODEL FETCHING (for evaluations) - DEPRECATED, use fetch_weave_configs
# =============================================================================

def fetch_weave_models(
    weave_entity: str,
    weave_project: str,
    wandb_token: str,
    excluded_models: Optional[set] = None
) -> Dict[str, List[str]]:
    """
    DEPRECATED: Use fetch_weave_configs() instead.
    
    Fetch all Model versions from Weave.
    
    Args:
        weave_entity: Weave entity name
        weave_project: Weave project name
        wandb_token: W&B API token
        excluded_models: Set of model names to exclude (default: scoring judges)
        
    Returns:
        Dict mapping model name to list of versions (e.g., {"Buzz": ["v4", "v3", "v2"]})
    """
    import requests
    
    if excluded_models is None:
        excluded_models = {"safety-judge", "accuracy-judge"}
    
    if not wandb_token:
        return {}
    
    try:
        project_id = f"{weave_entity}/{weave_project}"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "project_id": project_id,
            "filter": {
                "base_object_classes": ["Model"],
                "latest_only": False
            },
            "sort_by": [{"field": "created_at", "direction": "desc"}],
            "limit": 100
        }
        
        response = requests.post(
            WEAVE_OBJS_API,
            headers=headers,
            json=payload,
            auth=("api", wandb_token),
            timeout=10
        )
        
        if response.status_code != 200:
            return {}
        
        data = response.json()
        
        # Group by model name, collect versions
        models_dict = {}
        for obj in data.get("objs", []):
            object_id = obj.get("object_id", "")
            version_index = obj.get("version_index", 0)
            
            if object_id in excluded_models:
                continue
            
            if object_id not in models_dict:
                models_dict[object_id] = []
            models_dict[object_id].append(f"v{version_index}")
        
        # Sort versions descending (v4, v3, v2, ...)
        for model_name in models_dict:
            models_dict[model_name].sort(key=lambda v: int(v[1:]), reverse=True)
        
        return models_dict
        
    except Exception:
        return {}


# =============================================================================
# TRACE FETCHING (COMBINED HELPER)
# =============================================================================

def fetch_and_build_traces_ui(
    mo,
    chat_widget,
    weave_entity: str,
    weave_project: str,
    session_start_time: str
) -> Tuple[Optional[Any], Optional[str]]:
    """
    Fetch traces and build table UI in one call.
    
    Combines fetch_traces_data and build_traces_table_ui for cleaner notebook code.
    
    Args:
        mo: marimo module (must be passed from notebook context)
        chat_widget: Chat widget (if None, returns None, None)
        weave_entity: Weave entity name
        weave_project: Weave project name
        session_start_time: ISO timestamp to filter traces after
        
    Returns:
        Tuple of (table_ui, error_message) - table_ui is None if no traces or error
    """
    if chat_widget is None:
        return None, None
    
    wandb_token = os.getenv("WANDB_API_KEY", "")
    table_data, error = fetch_traces_data(
        weave_entity, weave_project, session_start_time, wandb_token
    )
    
    if table_data:
        return build_traces_table_ui(mo, table_data), None
    return None, error


# =============================================================================
# TERMINAL COMMAND HELPERS
# =============================================================================

async def run_terminal_command(
    mo,
    run_button,
    command_args: List[str],
    command_display: Optional[str] = None,
    env_vars: Optional[Dict[str, str]] = None
) -> Any:
    """
    Generic terminal command runner with marimo UI.
    
    Creates a terminal-like display with command + run button, and shows
    output when the button is clicked.
    
    Args:
        mo: marimo module
        run_button: mo.ui.run_button instance
        command_args: Command arguments as list (e.g., ["uv", "run", "modal", "setup"])
        command_display: Optional display string (for hiding secrets). If None, joins command_args.
        env_vars: Optional dict of environment variables to pass to subprocess
        
    Returns:
        marimo vstack with command display and output (if run)
    """
    import asyncio
    
    # Build display command
    display_cmd = command_display or " ".join(command_args)
    
    # Terminal-like display: command + run button
    command_row = mo.hstack([
        mo.md(f"```bash\n{display_cmd}\n```"),
        run_button
    ], justify="start", align="center", gap=1)
    
    # Default: just show the command with run button
    if not run_button.value:
        return command_row
    
    # Execute command
    try:
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        
        process = await asyncio.create_subprocess_exec(
            *command_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env
        )
        
        stdout, _ = await process.communicate()
        output = stdout.decode() if stdout else ""
        
        # Show command + output below
        return mo.vstack([
            command_row,
            mo.md(f"```\n{output}\n```") if output else mo.md("")
        ])
    except FileNotFoundError:
        return mo.vstack([
            command_row,
            mo.md(f"```\nError: Command not found: {command_args[0]}\n```")
        ])
    except Exception as e:
        return mo.vstack([
            command_row,
            mo.md(f"```\nError: {str(e)}\n```")
        ])


async def run_modal_deploy(
    mo,
    run_button,
    config_selector,
    version_selector,
    refresh_btn,
    step_num: int,
    success_message: str = "Deployed successfully!"
) -> Any:
    """
    Execute Modal deploy command and return the terminal UI.
    
    Handles config selection, config.json saving, deploy execution, and
    URL extraction from Modal output.
    
    Args:
        mo: marimo module
        run_button: Run button UI element
        config_selector: Config dropdown selector
        version_selector: Version dropdown selector
        refresh_btn: Refresh button
        step_num: Step number (6 or 7)
        success_message: Custom success message (e.g., "Deployed with guardrails!")
    
    Returns:
        Terminal UI vstack with config selectors, command, and output
    """
    import asyncio
    import re
    
    command = f"uv run modal deploy workspace/step-{step_num}/server.py"
    
    # Get selected config for display
    config_name = config_selector.value
    version = version_selector.value
    config_ref = f"{config_name}:{version}" if config_name and version else "No config selected"
    
    # Config selector row (separate from command)
    config_selector_row = mo.hstack([
        config_selector,
        version_selector,
        refresh_btn
    ], justify="start", gap=1)
    
    # Command + deploy button row
    command_row = mo.hstack([
        mo.md(f"```bash\n{command}\n```"),
        run_button
    ], justify="start", align="center", gap=1)
    
    # Default: show config selector + command with run button
    if not run_button.value:
        return mo.vstack([config_selector_row, command_row], gap=1)
    
    # Validate config selection
    if not config_name or config_name == "No configs found" or not version:
        return mo.vstack([
            config_selector_row,
            command_row,
            mo.callout(mo.md("❌ Please select a config and version before deploying."), kind="danger")
        ], gap=1)
    
    # Save config to workspace/step-{N}/config.json
    config_json_path = Path(f"workspace/step-{step_num}/config.json")
    config_json_path.parent.mkdir(parents=True, exist_ok=True)
    config_data = {"config_ref": config_ref}
    config_json_path.write_text(json.dumps(config_data, indent=2))
    
    server_path = Path(f"workspace/step-{step_num}/server.py")
    if not server_path.exists():
        return mo.vstack([
            config_selector_row,
            command_row,
            mo.md(f"```\nError: Server file not found: {server_path}\nMake sure you've completed the previous steps.\n```")
        ], gap=1)
    
    try:
        process = await asyncio.create_subprocess_exec(
            "uv", "run", "modal", "deploy", str(server_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=os.environ.copy()
        )
        
        stdout, _ = await process.communicate()
        output = stdout.decode() if stdout else ""
        
        # Extract key info from Modal output (URL, success message)
        endpoint_url = ""
        view_url = ""
        success = False
        
        for line in output.split('\n'):
            # Look for endpoint URL - multiple patterns Modal might use
            if 'modal_endpoint' in line or 'web function' in line.lower() or 'web endpoint' in line.lower():
                match = re.search(r'https://[^\s]+', line)
                if match:
                    endpoint_url = match.group(0)
            # Also catch any modal.run URL as fallback
            if not endpoint_url and '.modal.run' in line:
                match = re.search(r'https://[^\s]+\.modal\.run[^\s]*', line)
                if match:
                    endpoint_url = match.group(0)
            if 'View Deployment:' in line or 'view deployment' in line.lower():
                match = re.search(r'https://[^\s]+', line)
                if match:
                    view_url = match.group(0)
            if 'App deployed' in line or 'deployed!' in line.lower() or '✓' in line:
                success = True
        
        # Build concise output - show success callout with URL
        if endpoint_url or success:
            # Auto-save URL to state file for persistence
            if endpoint_url:
                state_file = Path(".marimo-state.json")
                try:
                    state = {}
                    if state_file.exists():
                        state = json.loads(state_file.read_text())
                    state["modal_prod_url"] = endpoint_url
                    state_file.write_text(json.dumps(state, indent=2))
                except:
                    pass
            
            if endpoint_url:
                summary = f"**🎉 {success_message}**\n\n**Config:** `{config_ref}`\n\n**Endpoint URL:** `{endpoint_url}`\n\n*(URL auto-saved - reload notebook to see it in Playground instructions)*"
            else:
                summary = f"**🎉 {success_message}**\n\n**Config:** `{config_ref}`\n\n*(Could not extract endpoint URL - check Modal dashboard)*"
            if view_url:
                summary += f"\n\n[View deployment on Modal]({view_url})"
            return mo.vstack([
                config_selector_row,
                command_row,
                mo.callout(mo.md(summary), kind="success")
            ], gap=1)
        else:
            # Only show output if something went wrong (no success detected)
            lines = output.strip().split('\n')
            truncated = '\n'.join(lines[-15:]) if len(lines) > 15 else output
            return mo.vstack([
                config_selector_row,
                command_row,
                mo.callout(mo.md(f"⚠️ Deploy output (check for errors):"), kind="warn"),
                mo.md(f"```\n{truncated}\n```")
            ], gap=1)
    except FileNotFoundError:
        return mo.vstack([
            config_selector_row,
            command_row,
            mo.md("```\nError: Modal CLI not found. Run 'uv run modal setup' first.\n```")
        ], gap=1)
    except Exception as e:
        return mo.vstack([
            config_selector_row,
            command_row,
            mo.md(f"```\nError: {str(e)}\n```")
        ], gap=1)

