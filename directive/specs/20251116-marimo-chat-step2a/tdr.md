# Technical Design Review (TDR) — Marimo In-Browser Chat for Step 2A

**Spec ID**: 20251116  
**Created**: 2025-11-16  
**Author**: AI Agent  
**Links**: 
- Spec: `/directive/specs/20251116-marimo-chat-step2a/spec.md`
- Impact: `/directive/specs/20251116-marimo-chat-step2a/impact.md`
- Marimo Chat API: https://docs.marimo.io/api/inputs/chat/
- Tyler Agent: https://slide.mintlify.app/

---

## 1. Summary

We are adding an interactive chat widget to Step 2A of the marimo guide using `mo.ui.chat()` that connects directly to a Tyler Agent loaded from the same configuration file used by the deployed server. This enables users to test their agent entirely in the browser before deploying to Modal, providing an early win and validating that the agent configuration works correctly.

The implementation uses `Agent.from_config("workspace/tyler-chat-config.yaml")` to load the agent (identical to the server's approach) and wraps it with a custom chat adapter function that converts marimo's message format to Tyler's `Thread`/`Message` format. Users get immediate feedback via a loading indicator and complete responses using `agent.run()`, with all interactions traced to Weave for observability.

This enhances the marimo guide's goal of being a complete browser-based alternative to the README tutorial while maintaining consistency between local testing (Step 2A) and deployed agent (Step 2B+).

## 2. Decision Drivers & Non‑Goals

### Decision Drivers

**User Experience:**
- Eliminate terminal dependency for Step 2A
- Provide "early win" moment (<60 seconds to first interaction)
- Reduce context switching between browser and terminal
- Maintain consistency between local testing and deployment

**Technical Validation:**
- Use identical agent loading code as server (`Agent.from_config()`)
- Validate configuration works before Modal deployment
- Test MCP connections (or fail gracefully) in local environment
- Ensure all interactions are traced to Weave

**Implementation Constraints:**
- Work within marimo's reactive execution model
- Handle async agent calls properly in marimo context
- Use `agent.run()` since marimo custom functions don't support streaming
- Minimize code changes (isolated to Step 2A only)

### Non‑Goals

- ❌ **Not adding streaming to marimo** - Custom functions return complete strings, not generators
- ❌ **Not replacing Step 2B** - Modal deployment still necessary for production-like testing
- ❌ **Not adding inline config editing** - That's Step 3's responsibility
- ❌ **Not visualizing traces in marimo** - Traces viewed in Weave UI
- ❌ **Not persistent conversations** - Ephemeral, resets on marimo restart
- ❌ **Not multi-user or collaborative** - Single-user local testing only

## 3. Current State — Codebase Map (concise)

### Key Modules

**`marimo-guide.py`** (1619 lines):
- Step 2A section: Lines ~250-540
- Uses marimo cells with reactive execution
- Current Step 2A: File copy button + terminal instructions
- Step 2B: Modal deployment + Weave Playground testing

**`examples/step-2/part-a/`**:
- `tyler-chat-config.yaml` - Agent configuration (YAML format)
- `tools.py` - Custom tools (create_issue, get_issue)
- `main.py` - Example of programmatic agent usage

**`examples/step-2/part-b/server.py`** (530 lines):
- Reference implementation of agent server
- Uses `Agent.from_config()` to load agent (line 114)
- Uses `agent.stream(thread, mode="raw")` for HTTP streaming (line 505)
- Connects MCP servers via `await agent.connect_mcp()` (line 359)

### Existing Data Models

**Tyler Agent Configuration** (YAML):
```yaml
name: string
model_name: string  # LiteLLM format
purpose: string
temperature: float
max_tool_iterations: int
tools: list[string]  # Module paths or built-in names
notes: string (optional)
mcp: dict (optional)  # MCP server configs
```

**Marimo Chat Message** (dict):
```python
{
    "role": "user" | "assistant" | "system",
    "content": str
}
```

**Tyler Thread/Message**:
```python
thread = Thread()
thread.add_message(Message(role="user", content="..."))
```

### External Contracts

**Tyler Agent API** (used):
- `Agent.from_config(path)` → returns Agent instance
- `agent.run(thread)` → returns complete response string
- `agent.connect_mcp()` → async MCP connection setup
- `agent.cleanup()` → async MCP cleanup

**Marimo UI API** (used):
- `mo.ui.chat(function, prompts, ...)` → returns chat widget
- Custom function signature: `(messages: list[dict], config: dict) -> str`

**Weave API** (used):
- `weave.init(project)` → initialize tracing
- Automatic tracing of Tyler Agent calls

### Observability Currently Available

- ✅ Weave traces for all agent calls (existing)
- ✅ Tyler Agent internal logging
- ✅ Marimo UI status display
- ❌ No metrics collection (not needed for local tool)

## 4. Proposed Design (high level, implementation‑agnostic)

### Overall Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Marimo Notebook                      │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Step 2A Cell Flow (Reactive Execution)         │  │
│  │                                                  │  │
│  │  [1] File Copy Button                           │  │
│  │       ↓ (triggers)                               │  │
│  │  [2] Agent Loading Cell                          │  │
│  │       - Check if config exists                   │  │
│  │       - Agent.from_config()                      │  │
│  │       - await agent.connect_mcp()                │  │
│  │       ↓ (returns)                                │  │
│  │  [3] Chat Adapter Cell                           │  │
│  │       - Creates tyler_chat_function              │  │
│  │       - Wraps agent.run() with message convert   │  │
│  │       ↓ (provides)                               │  │
│  │  [4] Chat Widget Cell                            │  │
│  │       - mo.ui.chat(tyler_chat_function)          │  │
│  │       - Suggested prompts                        │  │
│  │       - User interaction                         │  │
│  │       ↓ (links to)                               │  │
│  │  [5] Weave Trace Links Cell                      │  │
│  │       - Dynamic URL generation                   │  │
│  │       - Filter to Agent.run operations           │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Component Responsibilities

**Cell 1: File Copy Button** (existing, minor enhancement)
- Copy files from `examples/step-2/part-a/` to `workspace/`
- Trigger agent loading on success
- Show status feedback

**Cell 2: Agent Loader** (new)
- **Input**: `config_path` from previous cell
- **Responsibility**: Load Tyler Agent using server's approach
- **Output**: `(agent, config, status_message)`
- **Error Handling**: Graceful failures with actionable messages

**Cell 3: Chat Adapter** (new)
- **Input**: `agent` instance from Cell 2
- **Responsibility**: Bridge marimo chat format to Tyler format
- **Output**: Function compatible with `mo.ui.chat()`
- **Async Handling**: Wrap async `agent.run()` with `asyncio.run()`

**Cell 4: Chat Widget** (new)
- **Input**: Chat function from Cell 3
- **Responsibility**: Display chat UI with suggested prompts
- **User Interaction**: Send/receive messages
- **State**: Conversation history maintained by marimo

**Cell 5: Trace Links** (new)
- **Input**: Weave project info from environment
- **Responsibility**: Generate filtered Weave URLs
- **Output**: Clickable links to recent traces

### Interfaces & Data Contracts

#### Agent Loading Interface

```python
async def load_agent_from_config(
    config_path: Path
) -> tuple[Agent | None, dict | None, str]:
    """
    Load Tyler Agent using same approach as Modal server.
    
    Args:
        config_path: Path to tyler-chat-config.yaml
        
    Returns:
        (agent, config_dict, status_message):
            - agent: Agent instance or None if loading failed
            - config_dict: Parsed YAML or None if failed
            - status_message: User-friendly status for display
            
    Example Success:
        (agent_instance, {"name": "buzz", ...}, "✅ Agent loaded: buzz (gpt-4.1)")
        
    Example Failure:
        (None, None, "❌ Config file not found: workspace/tyler-chat-config.yaml")
    """
    try:
        # Validate file exists
        if not config_path.exists():
            return None, None, f"❌ Config not found: {config_path}"
        
        # Load config dict
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        # Initialize Weave if not already done
        if not weave.is_initialized():
            project = os.getenv("WANDB_PROJECT", "agentic-support-bot-demo")
            weave.init(project)
        
        # Load agent (same as server)
        agent = Agent.from_config(str(config_path))
        
        # Connect MCP if configured
        mcp_status = ""
        if config.get("mcp"):
            try:
                await agent.connect_mcp()
                mcp_status = " | MCP connected"
            except Exception as e:
                mcp_status = f" | ⚠️ MCP failed: {str(e)[:50]}"
        
        status = f"✅ Agent loaded: {config['name']} ({config['model_name']}){mcp_status}"
        return agent, config, status
        
    except yaml.YAMLError as e:
        return None, None, f"❌ Invalid YAML syntax: {str(e)}"
    except KeyError as e:
        return None, None, f"❌ Missing required field in config: {e}"
    except Exception as e:
        return None, None, f"❌ Failed to load agent: {str(e)}"
```

#### Chat Adapter Interface

```python
def create_chat_adapter(agent: Agent) -> callable:
    """
    Create chat function for mo.ui.chat() that uses Tyler Agent.
    
    Args:
        agent: Loaded Tyler Agent instance
        
    Returns:
        Callable compatible with mo.ui.chat() signature
    """
    async def async_chat(messages: list[dict], config: dict) -> str:
        """
        Async chat function using Tyler Agent.
        
        Args:
            messages: List of {"role": str, "content": str}
            config: Model config from marimo (unused, for compatibility)
            
        Returns:
            Complete response string from agent
        """
        from tyler import Thread, Message
        
        # Convert marimo messages to Tyler Thread
        thread = Thread()
        for msg in messages:
            thread.add_message(Message(
                role=msg["role"],
                content=msg["content"]
            ))
        
        # Run agent (non-streaming, returns complete response)
        result = await agent.run(thread)
        
        # Extract final assistant message
        final_message = result.messages[-1].content
        return final_message
    
    # Wrap async function for marimo (which expects sync)
    def sync_chat(messages: list[dict], config: dict) -> str:
        import asyncio
        return asyncio.run(async_chat(messages, config))
    
    return sync_chat
```

#### Chat Widget Interface

```python
def create_chat_widget(chat_function: callable) -> mo.ui.chat:
    """
    Create mo.ui.chat widget with Tyler Agent.
    
    Args:
        chat_function: Function from create_chat_adapter()
        
    Returns:
        marimo chat widget
    """
    return mo.ui.chat(
        chat_function,
        prompts=[
            "How do I initialize Weave in Python?",
            "I'm getting API timeout errors. Can you help?",
            "What's the status of ticket #10234?",
            "Create a support ticket for authentication issues"
        ],
        show_configuration_controls=False,  # Don't show temp/max_tokens (agent config controls this)
        placeholder="Ask the support bot anything..."
    )
```

#### Weave URL Generation Interface

```python
def generate_weave_trace_url(
    entity: str,
    project: str,
    operation_filter: str = "Agent.run"
) -> str:
    """
    Generate Weave traces URL with filters.
    
    Args:
        entity: W&B entity (from WANDB_PROJECT)
        project: W&B project name
        operation_filter: Operation name to filter
        
    Returns:
        Full URL to filtered traces
        
    Example:
        "https://wandb.ai/myteam/demo/weave/traces?filter=op_name%3DAgent.run"
    """
    from urllib.parse import quote
    base_url = f"https://wandb.ai/{entity}/{project}/weave/traces"
    filter_param = quote(f"op_name={operation_filter}")
    return f"{base_url}?filter={filter_param}"
```

### Error Handling

**Configuration Errors:**
```python
# Missing config file
if not config_path.exists():
    return mo.callout(
        mo.md(f"""
        ⚠️ **Config file not found**
        
        Click "Copy Step 2A Files" button above to create `workspace/tyler-chat-config.yaml`
        """),
        kind="warn"
    )

# Invalid YAML syntax
try:
    config = yaml.safe_load(f)
except yaml.YAMLError as e:
    return mo.callout(
        mo.md(f"""
        ❌ **Invalid YAML syntax**
        
        Error: {str(e)}
        
        Fix the syntax error in `workspace/tyler-chat-config.yaml` or re-copy files.
        """),
        kind="danger"
    )

# Missing required fields
required_fields = ["name", "model_name", "purpose"]
missing = [f for f in required_fields if f not in config]
if missing:
    return mo.callout(
        mo.md(f"""
        ❌ **Missing required fields in config**
        
        Missing: {', '.join(missing)}
        
        Add these fields to `workspace/tyler-chat-config.yaml`
        """),
        kind="danger"
    )
```

**MCP Connection Errors:**
```python
# MCP connection failure (non-fatal)
if config.get("mcp"):
    try:
        await agent.connect_mcp()
        mcp_status = "✅ MCP connected"
    except Exception as e:
        mcp_status = f"⚠️ MCP connection failed: {str(e)[:80]}"
        # Show warning but continue - agent still works without MCP
        mo.callout(
            mo.md(f"""
            ⚠️ **MCP Connection Failed**
            
            {str(e)}
            
            The agent will work for local tools. MCP servers will work when deployed to Modal.
            """),
            kind="warn"
        )
```

**Runtime Errors:**
```python
# Agent execution failure
try:
    result = await agent.run(thread)
    return result.messages[-1].content
except Exception as e:
    # Return error message in chat
    return f"❌ Error: {str(e)}\n\nPlease check your configuration and try again."
```

### Performance Expectations

**Agent Loading:**
- Target: < 5 seconds
- Typical: 1-3 seconds without MCP, 2-4 seconds with MCP
- Acceptable: Up to 10 seconds with slow MCP connections
- Mitigation: Load once when files copied, cache in cell output

**Chat Response:**
- Target: < 10 seconds for typical queries
- Typical: 3-8 seconds depending on model and tools
- Loading indicator: Marimo shows spinner automatically
- No streaming: User waits for complete response

**Memory:**
- Agent instance: ~50-100MB
- Conversation history: Negligible (<1MB for typical session)
- Total impact: < 200MB additional memory

## 5. Alternatives Considered

### Alternative A: Use HTTP Endpoint (mo.ai.llm.openai)

**Approach**: 
```python
chatbot = mo.ui.chat(
    mo.ai.llm.openai(
        model="buzz",
        base_url="http://localhost:8000/v1",
        api_key=os.getenv("AGENTIC_SUPPORT_BOT_API_KEY")
    )
)
```

**Pros**:
- ✅ Real streaming support (token-by-token)
- ✅ Same code path as deployed server
- ✅ Could test local server before deploying

**Cons**:
- ❌ Requires running local server (defeats "browser-only" goal)
- ❌ More complex setup (FastAPI, uvicorn, port management)
- ❌ Not truly testing "config works" - testing "server works"
- ❌ Additional failure points (server startup, networking)

**Why Not Chosen**: Too complex for Step 2A's goal (validate config). Server testing is Step 2B's job.

### Alternative B: Embed Tyler CLI (`tyler chat`)

**Approach**: Run `tyler chat` in subprocess, capture output, display in marimo

**Pros**:
- ✅ Uses official Tyler CLI
- ✅ Proven to work

**Cons**:
- ❌ Not truly browser-only (subprocess = terminal usage)
- ❌ Complex I/O handling (stdin/stdout piping)
- ❌ Poor UX (can't use marimo chat widget features)
- ❌ Harder to debug than native Python

**Why Not Chosen**: Defeats purpose of browser-based experience. Direct Python integration is cleaner.

### Alternative C: Custom Streaming Implementation

**Approach**: Yield chunks from custom function, update marimo state incrementally

**Pros**:
- ✅ Real-time streaming UX

**Cons**:
- ❌ Marimo custom functions don't support generators
- ❌ Would require hacky state management
- ❌ Complex implementation for marginal benefit
- ❌ Not officially supported by marimo

**Why Not Chosen**: `agent.run()` is simpler, UX acceptable for local testing. Streaming available in deployed version (Step 2B).

### Alternative D: Inline Agent Definition (No Config File)

**Approach**: Define agent programmatically in marimo cell

**Pros**:
- ✅ No file dependency
- ✅ Immediate feedback

**Cons**:
- ❌ Doesn't test actual config file that will be deployed
- ❌ Duplicates agent definition
- ❌ Defeats "validate config" goal
- ❌ Users have to edit two places (inline + config file)

**Why Not Chosen**: Must use same config as deployment to validate it works.

## Why Chosen Option (Direct Tyler Agent with agent.run())

✅ **Simplest implementation** - Uses Tyler Agent API directly, no wrappers
✅ **Same config as deployment** - `Agent.from_config()` validates actual deployment config
✅ **Browser-only** - No subprocess, no local server needed  
✅ **Works within marimo constraints** - Custom function returns string (no streaming needed)
✅ **Acceptable UX** - 3-10 second responses fine for local testing
✅ **Proper error handling** - Clear feedback when things fail
✅ **Future-proof** - Can add streaming later if marimo adds support

## 6. Data Model & Contract Changes

### No External Data Models Changed

This feature doesn't modify any data models, schemas, or database structures.

### Internal State (Marimo Cells)

**Cell Outputs** (ephemeral, in-memory):
```python
# Cell 2 output
agent_state = {
    "agent": Agent | None,
    "config": dict | None,
    "status": str  # User-facing message
}

# Cell 4 output (managed by marimo)
chat_widget = mo.ui.chat(...)
chat_widget.value = [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."},
    # ... conversation history
]
```

### Backward Compatibility

**100% Backward Compatible:**
- ✅ No config format changes
- ✅ Terminal workflow (`tyler chat`) still works
- ✅ All existing files compatible
- ✅ Step 2B unchanged
- ✅ Can revert cleanly (no data migration needed)

**Forward Compatibility:**
- ✅ Config tested in Step 2A works in Step 2B
- ✅ Agent behavior identical between local and deployed
- ✅ Future marimo updates won't break (using stable APIs)

## 7. Security, Privacy, Compliance

### AuthN/AuthZ Model

**Not Applicable** - Local tool, no authentication:
- Runs in user's local Python process
- No network listeners
- No user accounts
- No access control needed

### Secrets Management

**Environment Variables** (existing approach):
- `WANDB_API_KEY` - Read from `.env` file
- `OPENAI_API_KEY` - Optional, for certain models
- No new secrets introduced
- Secrets never displayed in UI
- Same security as existing marimo cells

**Best Practices:**
```python
# ✅ DO: Read from environment
api_key = os.getenv("WANDB_API_KEY")

# ❌ DON'T: Hard-code or display
# api_key = "sk-..."  # NEVER DO THIS
# print(f"API key: {api_key}")  # NEVER DO THIS
```

### PII Handling

**No PII Collection:**
- Chat conversations ephemeral (not saved)
- No telemetry or analytics
- No data sent anywhere except:
  - LLM API (user's choice of provider)
  - Weave API (traces, user already consented)

**User Data:**
- Conversation history: In-memory only, cleared on restart
- Agent config: User's own files
- Weave traces: Already part of existing workflow

### Threat Model

**Threat: Malicious Config File**
- **Attack**: User modifies config to execute arbitrary code
- **Mitigation**: YAML parsing only loads data, doesn't execute code. Tools are Python files user explicitly maintains.
- **Risk**: Low - user has full control of their environment anyway

**Threat: API Key Exposure**
- **Attack**: API keys leaked in marimo UI
- **Mitigation**: Never display secret values, use `kind="password"` for inputs
- **Risk**: Very Low - same as existing marimo cells

**Threat: Dependency Vulnerability**
- **Attack**: Malicious package in Tyler/marimo dependencies
- **Mitigation**: Use pinned versions, standard supply chain security
- **Risk**: Low - same as any Python package

**Threat: Local Code Execution**
- **Attack**: Agent or tools execute malicious code
- **Mitigation**: User controls tools.py, agent only calls user's code
- **Risk**: Acceptable - user's own code, user's machine

## 8. Observability & Operations

### Logs

**Not Applicable** - Local development tool, no operational logs needed.

**User-Facing Feedback:**
- Status messages in marimo UI (callouts)
- Error messages with troubleshooting steps
- Loading indicators during agent processing

### Metrics

**Not Applicable** - No automated metrics collection.

**Manual Validation:**
- Time to first interaction (internal testing)
- Error rate (qualitative feedback)
- User satisfaction (team surveys)

### Traces

**Weave Tracing** (automatic):
- ✅ All `agent.run()` calls traced to Weave
- ✅ Tool calls visible in trace details
- ✅ Same observability as deployed version
- ✅ Links provided in UI to view traces

### Alerts

**Not Applicable** - No operational alerts for local tool.

## 9. Rollout & Migration

### Feature Flags

**Not needed** - Simple additive feature:
- Add new cells to Step 2A
- Existing terminal instructions remain
- Users can use either or both

**Optional Soft Launch:**
```python
# If we want gradual rollout
ENABLE_CHAT = os.getenv("MARIMO_CHAT_ENABLED", "true") == "true"
```

### Migration Strategy

**No Migration Needed:**
- No data to migrate
- No config format changes
- No breaking changes

**Rollout Steps:**
1. Merge PR to main
2. Users get update on `git pull`
3. Works immediately (no setup needed)

### Revert Plan

**If Critical Issues:**
```bash
# Option 1: Quick revert
git revert <commit-hash>
git push origin main

# Option 2: Feature flag
export MARIMO_CHAT_ENABLED=false
```

**Blast Radius:** Very Low
- Only affects Step 2A UI
- Terminal workflow unaffected
- No data loss possible
- Easy rollback (<5 minutes)

## 10. Test Strategy & Spec Coverage (TDD)

### TDD Approach

**Not Traditional TDD:**
- Marimo cells are UI components, not unit-testable functions
- No automated tests for cell execution
- Validation through manual testing

**Testing Philosophy:**
- Extract testable logic into helper functions
- Test helpers with unit tests
- Validate UI flow manually
- Verify against spec acceptance criteria

### Spec→Test Mapping

#### Agent Loading (Spec Section: Acceptance Criteria → Agent Loading)

| Acceptance Criterion | Test Method | Validator |
|---------------------|-------------|-----------|
| Files copied → agent loads → chat appears | Manual: Click button, verify widget appears | Dev |
| Uses `Agent.from_config()` | Code review: Verify method called | Dev |
| MCP servers connect → status shown | Manual: Config with MCP, check status | Dev |
| Invalid config → shows error | Manual: Corrupt YAML, verify error message | Dev |

#### Chat Interaction (Spec Section: Acceptance Criteria → Chat Interaction)

| Acceptance Criterion | Test Method | Validator |
|---------------------|-------------|-----------|
| User sends message → agent responds | Manual: Type message, verify response | Dev |
| Processing → loading indicator shown | Manual: Observe UI during agent.run() | Dev |
| Multi-turn → context maintained | Manual: Send 3+ messages, verify coherence | Dev |
| Tool calls → visible in trace | Manual: Trigger tool, check Weave UI | Dev |

#### Weave Integration (Spec Section: Acceptance Criteria → Weave Integration)

| Acceptance Criterion | Test Method | Validator |
|---------------------|-------------|-----------|
| Response complete → trace appears | Manual: Check Weave after chat | Dev |
| Click "View Traces" → filtered page | Manual: Click link, verify filter | Dev |
| Multiple messages → separate traces | Manual: Send 3 messages, count traces | Dev |

#### Error Handling (Spec Section: Acceptance Criteria → Error Handling)

| Acceptance Criterion | Test Method | Validator |
|---------------------|-------------|-----------|
| Agent fails → error message shown | Manual: Break config, verify error | Dev |
| MCP fails → warning but functional | Manual: Invalid MCP config, verify warning | Dev |
| LLM fails → error in chat with retry | Manual: Simulate API failure (bad key) | Dev |

#### Consistency Check (Spec Section: Acceptance Criteria → Consistency with Deployment)

| Acceptance Criterion | Test Method | Validator |
|---------------------|-------------|-----------|
| Step 2A works → Step 2B works | Manual: Same config both steps | Dev + User |
| Edit config → changes reflected | Manual: Edit, reload, verify | Dev |
| MCP works in deployment | Manual: Deploy after local test | User |

### Test Tiers

**Unit Tests** (for helper functions):
```python
# tests/test_marimo_helpers.py

def test_parse_wandb_project():
    """Parse entity/project from WANDB_PROJECT env var"""
    entity, project = parse_wandb_project("myteam/demo")
    assert entity == "myteam"
    assert project == "demo"

def test_generate_weave_url():
    """Generate Weave trace URL with filters"""
    url = generate_weave_trace_url("myteam", "demo", "Agent.run")
    assert "wandb.ai/myteam/demo/weave/traces" in url
    assert "op_name=Agent.run" in url or "op_name%3DAgent.run" in url
```

**Integration Tests** (manual):
- [ ] Complete Step 2A flow: copy → chat → traces
- [ ] Error handling: invalid config → clear error
- [ ] MCP integration: configured → connects or warns
- [ ] Weave integration: chat → trace appears

**E2E Tests** (manual):
- [ ] Fresh user flow: clone → uv sync → marimo edit → complete Step 2A
- [ ] Consistency test: Step 2A agent behavior === Step 2B deployed agent
- [ ] Cross-step test: Step 2A → Step 2B → Step 3 (config editing)

### Negative & Edge Cases

| Test Case | Expected Behavior | Priority |
|-----------|-------------------|----------|
| Config file missing | Show "Copy files first" message | High |
| Invalid YAML syntax | Show validation error with line number | High |
| Missing required field | List missing fields with examples | High |
| MCP connection timeout | Show warning, agent still works | Medium |
| LLM API key invalid | Error in chat with troubleshooting | High |
| Agent crashes mid-response | Error message with retry option | Medium |
| Very long response (>10k tokens) | Handles gracefully, no truncation | Low |
| Rapid consecutive messages | Queues properly, no race conditions | Medium |
| Marimo restart mid-chat | Conversation cleared, agent reloads | Low |

### Performance Tests

**Not Needed** - Acceptable performance for local tool:
- Agent loading: Measured during manual testing
- Chat response: Inherits Tyler Agent performance
- Memory usage: Monitored during development

### CI Requirements

**Not Applicable** - Marimo cells not CI-testable:
- No unit tests for cell logic (UI components)
- Manual validation against spec
- Code review ensures quality

**Linting** (existing CI):
- ✅ `ruff check marimo-guide.py`
- ✅ `black --check marimo-guide.py`
- ✅ All existing checks pass

## 11. Risks & Open Questions

### Known Risks & Mitigations

| Risk | Severity | Mitigation | Status |
|------|----------|------------|--------|
| Marimo reactive execution issues | Medium | Careful cell dependency design | ✅ Addressed in design |
| Agent loading slow (>10s) | Low | Acceptable for one-time load | ✅ Acceptable |
| Non-streaming UX feels sluggish | Low | Loading indicator, acceptable for local test | ✅ Acceptable |
| MCP failures hard to debug | Medium | Clear error messages with troubleshooting | ✅ Addressed in design |
| User confusion (local vs deployed) | Low | Clear messaging about Step 2A vs 2B | ✅ Addressed in spec |

### Open Questions & Resolutions

**Q1: Show tool calls in chat UI or traces only?**
- **Options**:
  - A) Show "[Using tool: create_issue]" in chat widget
  - B) Tool calls only visible in Weave traces
- **Decision**: **Option B** (traces only)
- **Rationale**: 
  - Simpler implementation (no custom message formatting)
  - Encourages users to explore Weave UI (learning objective)
  - Tool call details more useful in trace view anyway
  - Can add inline indicators later if needed

**Q2: How to handle config reloading?**
- **Options**:
  - A) Manual reload (user clicks button or refreshes marimo)
  - B) Automatic file watching with reload
- **Decision**: **Option A** (manual reload)
- **Rationale**:
  - Simpler implementation
  - More predictable behavior (no surprise reloads)
  - Marimo refresh is fast and familiar
  - Automatic watching can be added later if needed

**Q3: Error message detail level?**
- **Options**:
  - A) Show full stack traces
  - B) User-friendly messages only
  - C) User-friendly + expandable details
- **Decision**: **Option B** (user-friendly only, for MVP)
- **Rationale**:
  - Cleaner UI for typical users
  - Stack traces rarely helpful for config errors
  - Can add "Show details" expander in future iteration
  - Logs still available in terminal for debugging

**Q4: Handle async in marimo cells?**
- **Decision**: Wrap async functions with `asyncio.run()`
- **Rationale**: Marimo expects sync functions, standard wrapping pattern works
- **Implementation**:
  ```python
  def sync_wrapper(messages, config):
      import asyncio
      return asyncio.run(async_function(messages, config))
  ```

## 12. Milestones / Plan (post‑approval)

### Milestone 1: Core Implementation (2-3 hours)

**Task 1.1: Add Agent Loading Cell** (45 min)
- [ ] Create async `load_agent_from_config()` function
- [ ] Handle file existence check
- [ ] Load config with YAML parsing
- [ ] Initialize Weave if needed
- [ ] Call `Agent.from_config()`
- [ ] Attempt MCP connection with error handling
- [ ] Return `(agent, config, status)` tuple
- **DoD**: Cell loads agent from valid config, shows status

**Task 1.2: Add Chat Adapter Cell** (30 min)
- [ ] Create `create_chat_adapter()` function
- [ ] Convert marimo messages to Tyler `Thread`/`Message`
- [ ] Call `agent.run(thread)`
- [ ] Extract final message content
- [ ] Wrap async with `asyncio.run()`
- **DoD**: Function works with test agent, returns string

**Task 1.3: Add Chat Widget Cell** (30 min)
- [ ] Create `mo.ui.chat()` with adapter function
- [ ] Add suggested prompts from spec
- [ ] Configure widget options
- [ ] Test with mock agent
- **DoD**: Widget displays, prompts work, can send messages

**Task 1.4: Integration** (45 min)
- [ ] Connect cells via marimo reactive execution
- [ ] Test full flow: copy files → load agent → chat → response
- [ ] Verify Weave traces appear
- [ ] Test multi-turn conversation
- **DoD**: Complete flow works end-to-end

### Milestone 2: Error Handling & UX Polish (1-2 hours)

**Task 2.1: Error Handling** (45 min)
- [ ] Add config file missing check
- [ ] Add YAML validation with error messages
- [ ] Add required field validation
- [ ] Add MCP connection failure handling
- [ ] Add agent runtime error handling
- [ ] Test all error paths
- **DoD**: All error scenarios show clear, actionable messages

**Task 2.2: Status Display** (30 min)
- [ ] Add loading status during agent load
- [ ] Add agent info display (name, model, MCP status)
- [ ] Add callouts for warnings/errors
- [ ] Style with marimo callout types
- **DoD**: User always knows what's happening

**Task 2.3: Weave Links** (15 min)
- [ ] Create `generate_weave_trace_url()` function
- [ ] Parse entity/project from WANDB_PROJECT
- [ ] Add filtered link to Agent.run traces
- [ ] Add link to latest trace after chat
- **DoD**: Links open correct Weave pages with filters

### Milestone 3: Testing & Documentation (1 hour)

**Task 3.1: Manual Testing** (30 min)
- [ ] Test with valid config (happy path)
- [ ] Test with invalid config (error handling)
- [ ] Test with MCP configured
- [ ] Test multi-turn conversations
- [ ] Test Weave integration
- [ ] Verify consistency with Step 2B
- **DoD**: All acceptance criteria validated

**Task 3.2: Update Terminal Instructions** (15 min)
- [ ] Make terminal section optional (accordion)
- [ ] Add note about browser vs terminal options
- [ ] Keep instructions for advanced users
- **DoD**: Both options clearly presented

**Task 3.3: Git Commit** (15 min)
- [ ] Review all changes
- [ ] Run linting (ruff, black)
- [ ] Commit with conventional commit message
- [ ] Update TODO list
- **DoD**: Clean commit ready for PR

### Dependencies

**Sequential Dependencies:**
- M2 depends on M1 (need core implementation before polish)
- M3 depends on M2 (need complete feature before testing)

**No External Dependencies:**
- No waiting on other teams
- No infrastructure setup needed
- No new package versions needed

### Estimated Total Time: 4-6 hours

**Breakdown:**
- Implementation: 2-3 hours
- Error handling/UX: 1-2 hours  
- Testing/docs: 1 hour

**Developer:** AI Agent or engineer familiar with marimo + Tyler

---

**Approval Gate**: Do not start coding until this TDR is reviewed and approved in the PR.

