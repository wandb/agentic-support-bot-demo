# Helpers Directory

Utility scripts for the agentic support bot demo.

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

### Testing

Run the test suite:

```bash
python tests/test_isolated_agent_runner.py
```

Or with pytest:

```bash
pytest tests/test_isolated_agent_runner.py -v
```


