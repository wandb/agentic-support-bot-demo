# Technical Design Review (TDR) — Tyler Chat CLI Integration

**Author**: AI Agent  
**Date**: 2025-10-10  
**Links**: 
- Spec: `/directive/specs/tyler-chat-cli/spec.md`
- Impact: `/directive/specs/tyler-chat-cli/impact.md`
- Tyler CLI Docs: https://slide.mintlify.app/apps/tyler-cli

---

## 1. Summary

We are migrating the support bot agent from a programmatic Python script (`main.py`) to an interactive CLI-based approach using the Slide Framework's built-in `tyler chat` command. This change enables developers to interact with the support bot conversationally in a terminal session rather than running a fixed demo script.

The tyler chat CLI provides a production-ready interactive interface with conversation management, streaming responses, and graceful error handling out of the box. We will create a YAML configuration file that defines the agent's behavior, model, purpose, and custom tools, allowing the agent to be launched with a single command: `tyler chat --config support-bot.yaml`.

## 2. Decision Drivers & Non‑Goals

### Drivers:
- **Developer experience**: Reduce friction for testing and iterating on agent behavior
- **Leverage framework features**: Use tyler chat's built-in interactive UI and conversation management
- **Configuration over code**: Enable agent behavior changes without code modifications
- **Maintainability**: Reduce custom streaming and CLI code in favor of framework-provided solutions

### Non‑Goals:
- Building a custom REPL or chat interface (using tyler chat's existing UI)
- Persistent conversation storage across sessions (keeping in-session context only for MVP)
- Web UI or API server (remaining CLI-focused)
- Real issue system integration (tools remain stubs)
- Production deployment or monitoring

## 3. Current State — Codebase Map (concise)

### Key modules/services:
- **`main.py`** (108 lines): Entry point that creates a Tyler Agent programmatically, executes a demo interaction with streaming event handling
- **`tools.py`** (118 lines): Defines custom tools (`create_issue`, `get_issue`) with Tyler-format tool definitions via `get_tools()` function
- **`tests/test_main.py`**: Basic test structure for the agent setup
- **`pyproject.toml`**: Dependencies include `slide-tyler>=0.1.0`, `slide-lye>=0.1.0`, `weave>=0.51.0`

### Existing data models:
- No persistent data models (all mock/stub data)
- Tools return mock issue dictionaries with fields: `id`, `title`, `description`, `status`, `priority`, `created_at`, `updated_at`

### External contracts:
- **Weave API**: Observability via `weave.init("agentic-support-bot-demo")`
- **OpenAI API**: LLM provider (gpt-4.1 model)
- **Environment variables**: `WANDB_API_KEY` (required), `OPENAI_API_KEY` (optional based on provider)

### Observability:
- Weave instrumentation enabled in `main.py` via `weave.init()`
- Automatic tracing of agent interactions, tool calls, token usage, latency

## 4. Proposed Design (high level, implementation‑agnostic)

### Overall Approach:

**Configuration-First Design**: Define agent behavior in a declarative YAML file that tyler chat consumes at runtime.

```yaml
# support-bot.yaml
name: "support-bot"
model_name: "gpt-4.1"
purpose: |
  You are a helpful support bot assistant that helps users manage support issues.
  You can create new issues and retrieve existing ones.
  Always be friendly, clear, and helpful in your responses.

temperature: 0.7
max_tool_iterations: 10

tools:
  - "./tools.py"
```

**Tool Loading**: tyler chat will load custom tools from the Python file path reference (`"./tools.py"`). The `get_tools()` function in `tools.py` returns Tyler-format tool definitions that include both the OpenAI function schema and implementation.

**Weave Integration**: tyler chat uses Tyler Agent internally, which means Weave instrumentation should work automatically if `weave.init()` is called before the CLI starts. Two approaches:
1. **Option A**: Call `weave.init()` in `tools.py` at module level (executes when tools are imported)
2. **Option B**: Create a wrapper script that calls `weave.init()` then invokes tyler chat
3. **Option C**: Check if tyler chat supports initialization hooks or config options for observability

**Invocation**: Developers run `uv run tyler chat --config support-bot.yaml` to start an interactive session.

### Component Responsibilities:

| Component | Responsibility |
|-----------|---------------|
| `support-bot.yaml` | Declarative agent configuration (name, model, purpose, tools) |
| `tools.py` | Custom tool definitions and implementations; Weave initialization |
| `tyler chat` CLI | Interactive UI, conversation management, streaming, error handling |
| Tyler Agent | LLM orchestration, tool execution, context management |
| Weave | Observability, tracing, metrics collection |

### Interfaces & Data Contracts:

**Configuration Schema** (support-bot.yaml):
```yaml
name: string                    # Agent identity
model_name: string              # LiteLLM-compatible model identifier
purpose: string                 # Agent system prompt
temperature: float (0.0-2.0)    # LLM temperature setting
max_tool_iterations: int        # Prevent infinite tool loops
tools: list[string]             # Tool module paths or built-in names
notes: string (optional)        # Additional context for agent
```

**Tool Definition Format** (from tools.py):
```python
{
    "definition": {
        "type": "function",
        "function": {
            "name": str,
            "description": str,
            "parameters": JSONSchema
        }
    },
    "implementation": callable
}
```

**Environment Variables**:
- `WANDB_API_KEY`: Required for Weave observability
- `OPENAI_API_KEY`: Required for OpenAI models (or appropriate key for other providers)

### Error Handling:

**Configuration Errors**: 
- tyler chat validates YAML syntax and required fields
- Missing config file → clear error message with usage instructions
- Invalid tool paths → error indicating which tool file couldn't be loaded

**Runtime Errors**:
- Missing env vars → fail fast with clear message about which variables are needed
- Tool execution errors → tyler chat catches and surfaces to user in conversation
- LLM API errors → tyler chat retries with exponential backoff (framework default)

**Graceful Degradation**:
- If Weave init fails, log warning but continue (observability shouldn't block usage)
- If a tool fails, agent can acknowledge failure and continue conversation

### Performance Expectations:

- **Latency**: Same as current implementation (determined by LLM API and tool execution)
- **Streaming**: tyler chat provides built-in streaming of LLM responses
- **Context window**: gpt-4.1 context limits apply (no conversation truncation needed for MVP)
- **Tool execution**: Sequential or parallel based on Tyler Agent's default behavior

## 5. Alternatives Considered

### Option A: Keep programmatic approach with main.py
**Pros**:
- No changes needed; current implementation works
- Full control over streaming and event handling
- Easy to customize behavior programmatically

**Cons**:
- Requires code changes to modify agent behavior
- Less interactive; requires editing prompts and re-running script
- Reinventing interaction patterns that tyler chat provides
- More code to maintain (streaming logic, event handling)

**Decision**: Not chosen; tyler chat provides better developer experience

### Option B: Build custom REPL on top of Tyler Agent
**Pros**:
- Full control over UI and interaction patterns
- Could customize beyond tyler chat capabilities

**Cons**:
- Significant development effort
- Reinventing what tyler chat already provides
- More code to maintain and test
- Doesn't leverage framework features

**Decision**: Not chosen; wasteful when tyler chat exists

### Option C: Use tyler init scaffolding approach
**Pros**:
- tyler init generates a complete project structure with agent.py and config
- Follows framework conventions from the start

**Cons**:
- Would require restructuring existing code
- May generate files we don't need
- Overkill for our simple use case

**Decision**: Not chosen; manual config file is simpler for our existing project

### Chosen Approach: Tyler Chat CLI with YAML Config
**Why**:
- Minimal changes to existing code (keep tools.py, main.py as reference)
- Leverages framework features (UI, streaming, error handling)
- Configuration-first approach enables easy iteration
- Best developer experience for interactive testing
- Maintains observability with minimal changes

## 6. Data Model & Contract Changes

### No Data Model Changes:
- No persistent storage (in-session conversations only)
- Mock tool responses remain unchanged
- No database migrations needed

### Configuration Contract:
**New**: `support-bot.yaml` file defining agent behavior
- Schema follows tyler chat conventions (documented at https://slide.mintlify.app/apps/tyler-cli)
- Must include: `name`, `model_name`, `purpose`, `tools`
- Optional: `temperature`, `max_tool_iterations`, `notes`

### Tool Loading Contract:
**Assumption**: tyler chat can load tools from Python file paths like `"./tools.py"`
- `tools.py` must export `get_tools()` function returning list of tool definitions
- Tool definitions follow Tyler format (definition + implementation)

**Validation Needed**: Confirm tyler chat's tool loading mechanism supports:
1. Custom Python file paths in config
2. Calling a function like `get_tools()` to retrieve tools
3. Alternative: Tools may need to be module-level exports

### API/Event Changes:
**None**: This is a CLI interface change, not a programmatic API change
- `tools.py` functions and signatures remain unchanged
- No REST API, webhooks, or event contracts

### Backward Compatibility:
- `main.py` remains as alternative invocation method
- Existing tests continue to work
- No deprecation needed; both approaches can coexist

## 7. Security, Privacy, Compliance

### AuthN/AuthZ:
- **No changes**: Local CLI tool, no authentication needed
- LLM provider API keys remain in environment variables
- Weave API key remains in environment variables

### Secrets Management:
- **No changes**: Environment variables only (`.env` file for local development)
- tyler chat respects environment variables automatically
- No secrets in configuration files or code

### PII Handling:
- **No changes**: No real user data processed
- Mock tool responses contain no PII
- Agent conversations not persisted (in-session only)

### Threat Model:
- **Minimal risk**: Local development tool
- Code execution risk: tyler chat loads and executes tools.py (same as current main.py)
- Supply chain: tyler chat and dependencies come from trusted Slide Framework packages
- No new attack surface introduced

## 8. Observability & Operations

### Logs/Metrics/Traces:

**Weave Integration**:
- **Requirement**: `weave.init("agentic-support-bot-demo")` must be called before tyler chat starts
- **Approach**: Add Weave initialization to `tools.py` at module level
  ```python
  # At top of tools.py
  import os
  from dotenv import load_dotenv
  import weave
  
  load_dotenv()
  if os.getenv("WANDB_API_KEY"):
      weave.init("agentic-support-bot-demo")
  ```
- **Benefit**: When tyler chat imports tools, Weave gets initialized automatically

**Metrics Tracked** (unchanged from current):
- Token usage per interaction
- Latency per LLM call
- Tool execution success/failure
- Model performance metrics

### Dashboards/Alerts:
- **Not applicable**: Local development tool
- Developers view traces at https://wandb.ai/ in project "agentic-support-bot-demo"

### CLI Output:
- tyler chat provides built-in output for:
  - Agent responses (streamed)
  - Tool usage indicators
  - Errors and warnings
  - Session start/end messages

### Runbooks:
- **Setup**: Environment variable configuration documented in README
- **Troubleshooting**: Common errors and solutions in README
- **No SLOs**: Development tool, no uptime requirements

## 9. Rollout & Migration

### Feature Flags:
- **Not applicable**: No production deployment or gradual rollout
- Developers can choose between `python main.py` (old) or `tyler chat` (new)

### Migration Strategy:
1. **Phase 1**: Create configuration file and test tyler chat locally
2. **Phase 2**: Update README to recommend tyler chat as primary interface
3. **Phase 3**: Keep main.py as alternative/reference implementation
4. **No forced migration**: Both approaches remain valid

### Revert Plan:
- **Easy revert**: Keep main.py functional
- If tyler chat doesn't work, developers can fall back to `uv run main.py`
- No database or persistent state to roll back

### Blast Radius:
- **Minimal**: Local development environment only
- No production systems affected
- No user-facing changes

## 10. Test Strategy & Spec Coverage (TDD)

### TDD Commitment:
For each acceptance criterion, we will:
1. Write a failing test that encodes the expected behavior
2. Run tests to confirm failure (proves test is meaningful)
3. Implement minimal changes to pass the test
4. Refactor while keeping test suite green

### Spec→Test Mapping:

| Acceptance Criterion | Test ID | Test Type | Description |
|---------------------|---------|-----------|-------------|
| Given developer has WANDB_API_KEY, when they run tyler chat, then interactive session starts | `test_config_valid_yaml` | Unit | Validate YAML config structure |
| Given chat session is active, when developer asks to create issue, then agent uses create_issue tool | `test_tool_create_issue_format` | Unit | Verify tool definition format |
| Given chat session is active, when developer asks for issue #123, then agent uses get_issue tool | `test_tool_get_issue_format` | Unit | Verify tool definition format |
| Given chat session has prior context, when developer asks follow-up, then agent maintains history | **Manual** | Manual | Tyler chat handles conversation context (framework feature) |
| Given required env vars missing, when developer runs CLI, then clear error message shown | **Manual** | Manual | Tyler chat CLI error handling (framework feature) |
| Given tests run, when CI executes, then config file structure is validated | `test_config_schema_validation` | Unit | YAML schema validation |

### Test Tiers:

**Unit Tests** (pytest):
- `test_config_valid_yaml()`: Parse support-bot.yaml and validate required fields
- `test_config_schema_validation()`: Ensure YAML matches expected schema
- `test_tool_definitions_format()`: Verify `get_tools()` returns valid Tyler format
- `test_create_issue_tool()`: Verify create_issue function behavior (existing)
- `test_get_issue_tool()`: Verify get_issue function behavior (existing)
- `test_weave_init_in_tools()`: Verify weave.init() is called when tools are imported

**Integration Tests**:
- **Not applicable**: Interactive CLI sessions not suitable for automated testing
- Framework (tyler chat) handles conversation flow, streaming, and error handling

**Manual Tests**:
- Start tyler chat with valid config → session starts successfully
- Create issue via chat → tool executes and returns mock data
- Retrieve issue via chat → tool executes and returns mock data
- Multi-turn conversation → context maintained across messages
- Missing env var → clear error message displayed
- Invalid config file → validation error shown

### Negative & Edge Cases:

| Test Case | Expected Behavior | Test Type |
|-----------|------------------|-----------|
| Missing support-bot.yaml | tyler chat error: "Config file not found" | Manual |
| Invalid YAML syntax | tyler chat error: "Failed to parse config" | Manual |
| Missing required field in YAML | tyler chat error: "Missing required field: name" | Unit |
| WANDB_API_KEY not set | Warning logged, agent continues (degraded observability) | Manual |
| OPENAI_API_KEY not set | tyler chat error: "LLM provider credentials missing" | Manual |
| Tool execution fails | Agent acknowledges failure in conversation | Manual |
| Invalid tool path in config | tyler chat error: "Failed to load tool from path" | Manual |

### Performance Tests:
- **Not applicable**: No performance requirements beyond LLM API latency
- Tyler Agent handles LLM interactions same as current main.py implementation

### CI Requirements:
- All unit tests must pass (`pytest tests/`)
- YAML config file must be valid (validated by unit test)
- No real API calls in CI (use mocked LLM responses if needed)
- Lint and format checks pass

## 11. Risks & Open Questions

### Risks:

| Risk | Severity | Mitigation |
|------|----------|------------|
| tyler chat cannot load tools from `"./tools.py"` path | **MEDIUM** | **Action**: Test immediately; if unsupported, explore alternatives (module-level exports, tyler init scaffolding) |
| Weave initialization doesn't work with tyler chat | **MEDIUM** | **Action**: Test Weave integration; if broken, create wrapper script to init Weave before CLI |
| tyler chat config schema differs from assumptions | **LOW** | **Action**: Follow official docs; adjust config as needed |
| Users confused by CLI change | **LOW** | **Action**: Clear README documentation with examples |
| Configuration file format changes in future tyler versions | **LOW** | **Action**: Pin slide-tyler version in pyproject.toml; document version requirements |

### Open Questions:

| Question | Proposed Resolution | Owner |
|----------|-------------------|-------|
| Does tyler chat support loading tools from Python file paths? | Test with `tools: ["./tools.py"]` in config; check if `get_tools()` is called or if tools must be module-level | Engineer (blocking) |
| How to initialize Weave before tyler chat starts? | Test module-level `weave.init()` in tools.py; alternative: wrapper script | Engineer (blocking) |
| Should we use tyler init scaffolding instead? | Decision: No (overkill for existing project); manual config is simpler | Resolved |
| Should README show both approaches or only tyler chat? | Decision: Recommend tyler chat as primary, mention main.py as alternative | Resolved |
| Do we need ThreadStore for conversation persistence? | Decision: No (out of scope for MVP); may add later | Resolved |

## 12. Milestones / Plan (post‑approval)

### Task Breakdown:

#### Task 1: Research & Validation (Spike)
**Goal**: Validate that tyler chat can load custom tools from Python file paths
**DoD**:
- [ ] Create minimal test config with `tools: ["./tools.py"]`
- [ ] Run `tyler chat --config test.yaml` and verify tools are loaded
- [ ] Document tool loading mechanism (function name, module-level exports, etc.)
- [ ] Test Weave initialization approach (module-level in tools.py)
**Test**: Manual verification that agent can use custom tools
**Dependencies**: None
**Owner**: Engineer

#### Task 2: Create Configuration File
**Goal**: Create `support-bot.yaml` with agent configuration
**DoD**:
- [ ] Write YAML config with name, model, purpose, tools
- [ ] Validate config loads without errors
- [ ] Test that agent behavior matches spec (friendly support bot)
**Test**: `test_config_valid_yaml()` passes
**Dependencies**: Task 1 (tool loading mechanism understood)
**Commit**: `feat: add support-bot.yaml config for tyler chat`
**Owner**: Engineer

#### Task 3: Update tools.py for Weave Integration
**Goal**: Ensure Weave initializes when tools are loaded
**DoD**:
- [ ] Add `weave.init()` call at module level in tools.py
- [ ] Handle missing WANDB_API_KEY gracefully (log warning, continue)
- [ ] Load environment variables with `python-dotenv`
- [ ] Verify Weave traces appear in wandb.ai dashboard
**Test**: `test_weave_init_in_tools()` passes; manual verification of traces
**Dependencies**: Task 1
**Commit**: `feat: add weave initialization to tools.py`
**Owner**: Engineer

#### Task 4: Add Configuration Validation Tests
**Goal**: Write tests to validate config file structure
**DoD**:
- [ ] Write `test_config_schema_validation()` - parse YAML, check required fields
- [ ] Write `test_config_valid_yaml()` - ensure YAML syntax is valid
- [ ] Tests pass in CI
**Test**: pytest suite green
**Dependencies**: Task 2 (config file exists)
**Commit**: `test: add config validation tests`
**Owner**: Engineer

#### Task 5: Update README Documentation
**Goal**: Document tyler chat as primary interface
**DoD**:
- [ ] Add "Quick Start" section with `tyler chat --config support-bot.yaml`
- [ ] Document environment variable requirements
- [ ] Add troubleshooting section for common errors
- [ ] Mention main.py as alternative approach
- [ ] Add example conversation snippets
**Test**: README is clear and actionable (manual review)
**Dependencies**: Tasks 2, 3 (config and Weave integration working)
**Commit**: `docs: update README for tyler chat CLI usage`
**Owner**: Engineer

#### Task 6: Manual Testing & Validation
**Goal**: Verify all acceptance criteria through manual testing
**DoD**:
- [ ] Start interactive session successfully with config
- [ ] Create issue through conversation → tool executes correctly
- [ ] Retrieve issue through conversation → tool executes correctly
- [ ] Multi-turn conversation maintains context
- [ ] Missing env var produces clear error
- [ ] Verify Weave traces in wandb.ai dashboard
**Test**: All spec acceptance criteria validated
**Dependencies**: Tasks 2, 3, 5 (config, Weave, docs complete)
**Owner**: Engineer

#### Task 7: Clean Up & Polish
**Goal**: Ensure codebase is clean and professional
**DoD**:
- [ ] Remove any temporary test files
- [ ] Ensure all tests pass in CI
- [ ] Lint and format all code
- [ ] Update .gitignore if needed (e.g., ignore local chat DB files)
**Test**: CI green, no linter errors
**Dependencies**: All above tasks
**Commit**: `chore: clean up and polish tyler chat integration`
**Owner**: Engineer

---

**Approval Gate**: Do not start coding until this TDR is reviewed and approved in the PR.

