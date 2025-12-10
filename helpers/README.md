# Helpers Directory

Utility scripts for the agentic support bot demo.

## marimo_helpers.py

Reusable helper functions for `marimo-guide.py` to reduce code duplication and improve maintainability.

### Constants

- `WEAVE_TRACE_API` - Weave trace streaming API endpoint
- `WEAVE_OBJS_API` - Weave objects query API endpoint  
- `WANDB_BASE_URL` - Base URL for W&B web interface
- `DEFAULT_CHAT_PROMPTS` - Standard prompts used across chat widgets
- `TOOL_CHAT_PROMPTS` - Shorter prompts for steps with tools

### URL Builders

```python
from helpers import weave_traces_url, weave_evals_url, trace_peek_url

# Build URLs for Weave pages
traces_url = weave_traces_url("entity", "project")
evals_url = weave_evals_url("entity", "project")
trace_url = trace_peek_url("entity", "project", "trace-id-123")
```

### Environment Helpers

```python
from helpers import save_env_var

# Save a single env var to .env file
save_env_var("WANDB_API_KEY", "your-key")
```

### File Operations

```python
from helpers import auto_copy_step_files

# Auto-copy step files to workspace (skips if config already exists)
copied_files = auto_copy_step_files(2)  # copies examples/step-2/* to workspace/step-2/
```

### Trace Fetching

```python
from helpers import fetch_traces_data, build_traces_table_ui, build_traces_section

# Fetch trace data from Weave API
table_data, error = fetch_traces_data(
    weave_entity="entity",
    weave_project="project", 
    session_start_time="2024-01-01T00:00:00+00:00",
    wandb_token="your-token"
)

# Build marimo table UI (requires mo from notebook context)
if table_data:
    traces_table = build_traces_table_ui(mo, table_data)

# Build complete traces section UI
components = build_traces_section(mo, traces_table, error, chat_widget, traces_url)
```

### Chat Widget Helpers

```python
from helpers import create_step_chat_widget, DEFAULT_CHAT_PROMPTS

# Create chat widget with status display
status_display, chat_widget = create_step_chat_widget(
    mo=mo,
    agent=loaded_agent,
    agent_status="✅ Agent loaded: Buzz",
    config_path=Path("workspace/step-2/tyler-chat-config.yaml"),
    chat_adapter_fn=create_chat_adapter_subprocess,
    prompts=DEFAULT_CHAT_PROMPTS
)
```

### Model Fetching

```python
from helpers import fetch_weave_models

# Get available models for evaluation dropdown
models_dict = fetch_weave_models("entity", "project", "wandb-token")
# Returns: {"Buzz": ["v4", "v3", "v2"], "OtherAgent": ["v1"]}
```

---

## isolated_agent_runner.py

A helper script that runs the Tyler Agent in an isolated subprocess to ensure fresh Weave trace context.

### Purpose

In persistent Python environments like Marimo notebooks, the execution context persists across multiple function calls. This causes Weave traces to nest under a parent context from the initial cell execution. Running the agent in a subprocess ensures each chat message creates its own root trace, similar to how the FastAPI server achieves isolation (each HTTP request runs in its own context).

### Usage

The script is designed to be called via subprocess from Marimo (or other persistent environments):

```python
import subprocess
import json
import sys

# Prepare input
input_data = {
    "messages": [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi!"},
        {"role": "user", "content": "How are you?"}
    ],
    "config_path": "/path/to/tyler-chat-config.yaml"
}

# Run in subprocess
process = subprocess.run(
    [sys.executable, "helpers/isolated_agent_runner.py"],
    input=json.dumps(input_data),
    capture_output=True,
    text=True
)

# Parse output (newline-delimited JSON)
for line in process.stdout.strip().split('\n'):
    chunk = json.loads(line)
    if "content" in chunk:
        print(chunk["content"], end="", flush=True)
    elif "error" in chunk:
        print(f"Error: {chunk['error']}")
```

### Input Format

JSON object via stdin:

```json
{
    "messages": [
        {"role": "user", "content": "message text"},
        ...
    ],
    "config_path": "/absolute/path/to/tyler-chat-config.yaml"
}
```

### Output Format

Newline-delimited JSON to stdout:

```json
{"content": "response chunk 1"}
{"content": "response chunk 2"}
{"content": "response chunk 3"}
```

Or on error:

```json
{"error": "error message"}
```

### Benefits

1. **Fresh Weave Context**: Each subprocess gets a fresh Python process with its own Weave trace context
2. **Independent Root Traces**: Every chat message creates its own root trace in Weave UI
3. **Mirrors Production**: Works the same way as the FastAPI server (request isolation)
4. **Reusable**: Can be used across different steps in the demo (Step 2A, Step 3, Step 4)

### Trade-offs

- **Startup Overhead**: ~100-500ms per message (negligible compared to LLM latency)
- **Memory**: Brief spike while subprocess runs (not an issue for local dev)
- **Complexity**: Requires JSON serialization and subprocess management

---

## isolated_eval_runner.py

Similar to `isolated_agent_runner.py`, but for running Weave evaluations in an isolated subprocess context.

### Purpose

Ensures each evaluation run creates its own root trace in Weave, avoiding nested traces from persistent notebook environments.

### Usage

Called via subprocess with JSON input containing:
- `config_path`: Path to agent config
- `model_ref`: Model reference (e.g., "Buzz:v4")
- `sample_size`: Optional number of samples to evaluate

---

## Testing

Run the test suite:

```bash
pytest tests/test_marimo_helpers.py -v
pytest tests/test_isolated_agent_runner.py -v
```
