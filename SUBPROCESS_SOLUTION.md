# Solution: Subprocess-based Agent Execution for Marimo

## Problem

In Marimo notebooks, the cell execution context persists across multiple chat message submissions. This causes Weave traces to nest under the initial parent context, resulting in all chat messages appearing as nested traces under the first message instead of as independent root traces.

## Root Cause

- **Weave's trace context** uses Python's `contextvars` which propagate through async calls by design
- **Marimo cells** execute once and persist their context
- **Each chat message** reuses the same cell context, causing Tyler's `@weave.op` decorated methods to nest under the parent
- This differs from the **FastAPI server** where each HTTP request creates a fresh context

## Solution

Run the Tyler Agent in an isolated subprocess for each chat message. This ensures:
1. Fresh Python process with new Weave context
2. Each message creates its own root trace
3. Behavior matches production (FastAPI server)

## Implementation

### 1. Helper Script: `helpers/isolated_agent_runner.py`

A standalone script that:
- Accepts message history and config path via stdin (JSON)
- Initializes Weave in the fresh process
- Loads Tyler Agent from config
- Streams agent response as newline-delimited JSON to stdout
- Handles errors gracefully

### 2. Chat Adapter: Modified in `marimo-guide.py`

The `create_chat_adapter_subprocess()` function:
- Spawns a subprocess running the helper script
- Sends messages as JSON via stdin
- Streams output from subprocess line-by-line
- Parses JSON chunks and yields content to Marimo chat UI
- Used in Steps 2A, 3, and 4

### 3. Test Suite: `tests/test_isolated_agent_runner.py`

Basic tests verifying:
- Error handling for invalid input
- Error handling for missing config
- Proper JSON output format

## Files Created/Modified

### Created:
- `helpers/__init__.py` - Package marker
- `helpers/isolated_agent_runner.py` - Subprocess runner script
- `helpers/README.md` - Documentation
- `tests/test_isolated_agent_runner.py` - Test suite

### Modified:
- `marimo-guide.py`:
  - Renamed `create_chat_adapter()` → `create_chat_adapter_subprocess()`
  - Updated to use subprocess approach
  - Updated Steps 3 and 4 to use new adapter

## Trade-offs

### Pros
✅ Guaranteed context isolation (fresh Python process)  
✅ Clean Weave traces (each message = root trace)  
✅ Uses documented Weave APIs (no internal manipulation)  
✅ Reusable across multiple steps  
✅ Mirrors production architecture  

### Cons
⚠️ ~100-500ms startup overhead per message (negligible vs LLM latency 1-10s)  
⚠️ Brief memory spike per subprocess (not an issue for local dev)  
⚠️ Added complexity (JSON serialization, subprocess management)  

## Why This Works

1. **Process Isolation**: Each subprocess is a completely new Python interpreter
2. **Fresh contextvars**: Python's contextvars don't persist across processes
3. **Weave Initialization**: `weave.init()` in subprocess creates new root context
4. **No Parent Context**: Tyler's `@weave.op` finds no parent, creates root trace

## Alternative Approaches Considered

1. **Context variable manipulation** - Not supported by Weave, would break tracing
2. **`set_tracing_enabled(False/True)`** - Would disable tracing entirely
3. **Manual call tracking** - Would conflict with Tyler's `@weave.op` decorator
4. **Thread-based isolation** - Complex with async generators, performance issues

## Testing

```bash
# Run basic tests
python tests/test_isolated_agent_runner.py

# Test in Marimo (requires environment setup)
marimo edit marimo-guide.py
# Navigate to Step 2A, send multiple chat messages
# Check Weave UI - each message should be a root trace
```

## Success Criteria

- ✅ Helper script created and tested
- ✅ Marimo guide updated to use subprocess approach
- ✅ All three chat widgets (Steps 2A, 3, 4) use new approach
- ✅ Documentation created
- ⏳ Integration test pending (requires full environment setup)
- ⏳ Weave UI verification pending (user will test)

## Next Steps

1. User tests in Marimo with actual environment setup
2. Verify traces appear as independent roots in Weave UI
3. If successful, document this pattern for other notebook environments


