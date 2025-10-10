# Technical Design Review (TDR) — Tyler Agent Foundation

**Author**: AI Agent  
**Date**: 2025-10-09  
**Links**: 
- Spec: `/directive/specs/tyler-agent-foundation/spec.md`
- Impact: `/directive/specs/tyler-agent-foundation/impact.md`

---

## 1. Summary

We are building a foundational Tyler agent implementation that serves as the starting point for the agentic support bot. The script initializes a Tyler agent with two custom stub tools (`create_issue` and `get_issue`), integrates Weights & Biases Weave for observability with a StringPrompt-based purpose, and uses OpenAI's gpt-4.1 model for LLM capabilities. The implementation includes streaming execution for real-time feedback and comprehensive automated testing with GitHub Actions CI.

This establishes the core agent architecture, tool registration patterns, streaming execution, test infrastructure, and observability that will be extended in future iterations with real issue management integrations and more sophisticated agent behaviors.

## 2. Decision Drivers & Non‑Goals

**Drivers**:
- Quick iteration on agent behavior requires observability (Weave tracing)
- Streaming execution provides better UX and debugging visibility
- Stub tools enable agent development without external system dependencies
- Tyler framework provides production-ready agent orchestration
- Weave StringPrompt enables prompt versioning and optimization
- .env file approach simplifies local development setup
- Automated testing with CI ensures code quality and prevents regressions
- Only WANDB_API_KEY required reduces setup friction

**Non‑Goals**:
- No actual issue system integration (GitHub, Jira, Linear, etc.)
- No persistent storage or database
- No web interface or API endpoints
- No production deployment concerns (feature flags, rollback, etc.)
- No multi-agent coordination or delegation
- No complex retry logic or error recovery
- No multiple LLM provider switching (OpenAI only for MVP)

## 3. Current State — Codebase Map (concise)

**Key modules**:
- `main.py` — Simple "Hello World" print statement (replaced with Tyler agent)
- `pyproject.toml` — Basic project metadata with `directive>=0.0.9` dependency
- `directive/` — Contains Directive workflow templates and rules
- `tests/` — Created with 8 test cases and conftest.py for mocking
- `.github/workflows/` — GitHub Actions CI workflow added

**Existing data models**: None

**External contracts**: None

**Observability**: Weave integration added with automatic tracing

**Test infrastructure**: Comprehensive test suite with pytest, all API calls mocked

## 4. Proposed Design (high level, implementation‑agnostic)

### Overall Architecture

```
┌─────────────────────────────────────────┐
│           main.py                       │
│                                         │
│  1. Load .env (python-dotenv)          │
│  2. Validate environment                │
│  3. Initialize Weave                    │
│  4. Import tools from tools.py          │
│  5. Create Tyler Agent w/ StringPrompt  │
│  6. Execute agent with streaming        │
└─────────────────────────────────────────┘
         │
         ├──> Tyler Agent
         │    ├─ Model: gpt-4.1 (via LiteLLM)
         │    ├─ Purpose: weave.StringPrompt (versioned)
         │    └─ Tools: from tools.get_tools()
         │
         ├──> Weave (Observability)
         │    └─ Project: "agentic-support-bot-demo"
         │
         ├──> tools.py (Stubs)
         │    ├─ create_issue(title, description, priority?)
         │    ├─ get_issue(issue_id)
         │    └─ get_tools() -> Tyler format
         │
         └──> Streaming Execution
              ├─ Real-time LLM chunks
              ├─ Tool usage indicators
              └─ Tool completion feedback
```

### Component Responsibilities

**1. Environment Setup**
- Load API keys from `.env` file using `python-dotenv`
- Validate required keys are present (`OPENAI_API_KEY`, `WANDB_API_KEY`)
- Fail fast with clear error messages if keys are missing

**2. Weave Initialization**
- Initialize Weave with project name matching repository: "agentic-support-bot-demo"
- Enable automatic tracing for all agent interactions
- No custom configuration needed for MVP

**3. Custom Tool Definitions**
- Define tools using Lye utilities for proper schema registration
- Tools return structured mock data (dictionaries/dataclasses)
- Include docstrings that the LLM can use to understand tool purposes

**Tool Interfaces**:

```python
# create_issue tool
Input:
  - title: str (required)
  - description: str (required)
  - priority: str (optional, default="medium")

Output:
  {
    "id": str,  # Mock UUID or sequential ID
    "title": str,
    "description": str,
    "status": "open",
    "priority": str,
    "created_at": str  # ISO 8601 timestamp
  }

# get_issue tool
Input:
  - issue_id: str (required)

Output:
  {
    "id": str,
    "title": str,
    "description": str,
    "status": str,  # "open", "in_progress", "closed"
    "priority": str,
    "created_at": str,
    "updated_at": str
  }
  
  OR None/error if issue_id not found (stub can return mock data for any ID)
```

**4. Tyler Agent Configuration**
- `name`: "support-bot"
- `model_name`: "gpt-4.1"
- `purpose`: `weave.StringPrompt` object for versioned prompt management
- `tools`: List from `get_tools()` in Tyler's custom tool format

**5. Agent Execution with Streaming**
- Async execution using `agent.go(thread, stream=True)`
- Real-time event handling:
  - `EventType.LLM_STREAM_CHUNK` - Display response as it's generated
  - `EventType.TOOL_SELECTED` - Show when tools are being invoked
  - `EventType.TOOL_RESULT` - Confirm tool completion
- Test prompt demonstrates agent can understand and use both tools
- Enhanced UX with visual indicators for tool usage

### Error Handling

**Configuration errors** (missing API keys):
- Fail immediately during initialization
- Print clear error message indicating which key is missing
- Exit with non-zero status code

**Agent execution errors**:
- Allow Tyler's built-in error handling for LLM/tool failures
- Log errors via standard Python logging
- Weave will capture error traces automatically

### Performance Expectations

- Script should complete in < 30 seconds for typical agent interaction
- Initial Weave connection and agent initialization: < 5 seconds
- LLM response time: 2-15 seconds depending on complexity
- Tool execution: < 100ms (stubs are instant)

## 5. Alternatives Considered

### Alternative A: Manual Tool Registration (without Lye)
**Approach**: Define tools as plain Python functions without using slide-lye utilities

**Pros**:
- Fewer dependencies
- More explicit control over tool definitions

**Cons**:
- More boilerplate for schema definitions
- Misses best practices from Lye
- Harder to maintain consistency

**Decision**: Use Lye — it provides utilities specifically designed for Tyler tool integration and reduces boilerplate.

### Alternative B: Async Agent Execution with Streaming
**Approach**: Use async/await pattern for agent execution with streaming

**Pros**:
- Better for future scalability
- Non-blocking I/O
- Enables streaming for real-time feedback
- Better debugging and UX

**Cons**:
- Slightly more complex than synchronous

**Decision**: Use async with streaming - the benefits for debugging and UX outweigh the minimal complexity increase. Streaming is essential for good agent development experience.

### Alternative C: Store Tool Responses
**Approach**: Persist tool responses in SQLite or file for agent memory

**Pros**:
- More realistic agent behavior
- Could test retrieval of previously created issues

**Cons**:
- Adds complexity and dependencies
- Out of scope for stub tools
- Not needed for foundational setup

**Decision**: Keep tools stateless for MVP. Memory/persistence is explicitly out of scope.

## 6. Data Model & Contract Changes

**No database or persistent storage** for this iteration.

**In-memory data structures**:
- Tools return plain Python dictionaries
- No state maintained between invocations
- Each stub tool can use hardcoded mock data or generate random IDs

**API/Event changes**: N/A (no external APIs exposed)

**Backward compatibility**: N/A (greenfield implementation)

**File organization**:
- Tools separated into `tools.py` for modularity
- Main execution logic in `main.py`
- Tests in `tests/` directory with pytest fixtures

## 7. Security, Privacy, Compliance

### Authentication & Authorization
- Not applicable for local development script
- No user authentication required
- Agent runs with developer's API credentials

### Secrets Management
- **WANDB_API_KEY** (required) and **OPENAI_API_KEY** (optional) stored in `.env` file
- `.env` file is already in `.gitignore` ✓
- `.env.example` created with placeholder values as template
- Documented required environment variables in README
- CI uses environment variables with test values
- Test fixtures automatically mock API keys to prevent leakage

### PII Handling
- No real user data in stub tools
- Mock data should use obviously fake information
- Weave traces may contain prompts — ensure no real PII in test prompts

### Threat Model
- **Low risk**: Development script with no external exposure
- **Risk**: API keys could be leaked if .env is committed
  - Mitigation: .env in .gitignore, .env.example for template
- **Risk**: Prompt injection could cause agent to misuse tools
  - Mitigation: Tools are stubs with no real system access

## 8. Observability & Operations

### Logs
Python standard logging configured for:
- Agent initialization status
- Tool registration confirmation
- Environment validation (keys present)
- Agent execution start/completion
- Any errors during execution

**Log level**: INFO for normal operation, DEBUG for detailed tracing

### Metrics (via Weave)
Weave automatically captures:
- **LLM metrics**: Model used, tokens consumed, latency, cost
- **Tool metrics**: Tool calls made, success/failure, execution time
- **Agent metrics**: Total execution time, number of conversation turns

### Traces (via Weave)
Full execution traces in Weave UI showing:
- Complete conversation flow
- LLM prompts and responses
- Tool calls with inputs and outputs
- Error stack traces if failures occur

### Dashboards
- Use Weave's default dashboard for project "agentic-support-bot-demo"
- No custom dashboards needed for MVP

### Alerts
Not applicable for development script.

## 9. Rollout & Migration

**Not applicable** — This is a local development script, not a deployed service.

Future considerations when deploying:
- Environment variable management in production (secrets manager)
- Rate limiting and cost controls for OpenAI API
- Multi-tenancy considerations if exposed to users

## 10. Test Strategy & Spec Coverage (TDD)

### TDD Commitment
We will follow strict TDD:
1. Write failing test for each acceptance criterion
2. Run test to confirm it fails meaningfully
3. Implement minimal code to pass
4. Refactor while keeping tests green

### Spec → Test Mapping

From spec acceptance criteria:

**AC-1**: "Given the script is executed, when the agent initializes, then Weave tracking is enabled with the correct project name"
- **Test ID**: `test_weave_initialization`
- **Validates**: Weave.init called with project="agentic-support-bot-demo"

**AC-2**: "Given the agent receives a prompt about creating an issue, when it attempts to use `create_issue`, then the stub returns a mock issue ID"
- **Test ID**: `test_create_issue_tool_returns_mock_data`
- **Validates**: Tool returns dictionary with required fields including 'id'

**AC-3**: "Given the agent receives a prompt about retrieving an issue, when it attempts to use `get_issue`, then the stub returns mock issue data"
- **Test ID**: `test_get_issue_tool_returns_mock_data`
- **Validates**: Tool returns dictionary with all expected fields

**AC-4**: "Given Weave credentials are missing, when the script runs, then it fails with a clear error message before attempting agent operations"
- **Test ID**: `test_missing_api_keys_fails_gracefully`
- **Validates**: Script exits with error when OPENAI_API_KEY or WANDB_API_KEY missing

### Test Tiers

**Unit Tests** (pytest):
- `test_create_issue_tool_schema` — Validates tool function signature and return structure
- `test_get_issue_tool_schema` — Validates tool function signature and return structure
- `test_environment_validation` — Tests API key validation logic
- `test_weave_initialization` — Tests Weave init with correct project name

**Integration Tests** (pytest):
- `test_agent_initialization_with_tools` — Validates Tyler agent can be created with custom tools
- `test_agent_can_call_create_issue` — End-to-end test with mock prompt triggering create_issue
- `test_agent_can_call_get_issue` — End-to-end test with mock prompt triggering get_issue

### Negative & Edge Cases
- Missing OPENAI_API_KEY
- Missing WANDB_API_KEY
- Invalid API key format (if detectable before API call)
- Agent prompt that doesn't match any tool (general conversation)
- Tool called with missing required parameters (Tyler should handle)

### Test Fixtures & Mocking
- Mock environment variables for API keys in tests
- Mock Weave initialization to avoid actual API calls in unit tests
- Mock OpenAI API responses to avoid costs and flakiness in CI
- Consider using Tyler's built-in test utilities if available

### CI Requirements
- All tests must pass before merge
- GitHub Actions workflow runs on all PRs
- Tests run on Python 3.12 and 3.13
- No real API calls allowed (enforced by conftest.py and WANDB_MODE=disabled)
- Uses uv for fast, reproducible dependency management
- Code quality checks with ruff (format and lint)

### Performance Tests
Not required for MVP (local development script).

## 11. Risks & Open Questions

### Known Risks

**Risk 1**: OpenAI API rate limits or outages
- **Mitigation**: Acceptable for development; add retry logic in future iterations
- **Severity**: Low (development only)

**Risk 2**: Weave API costs or rate limits
- **Mitigation**: Weave free tier should be sufficient for development
- **Severity**: Low

**Risk 3**: Tyler framework API changes
- **Mitigation**: Pin slide-tyler version in pyproject.toml
- **Severity**: Medium (would require code updates)

**Risk 4**: Tool schema mismatches
- **Mitigation**: Write tests for tool schemas; use type hints
- **Severity**: Medium (could cause agent confusion)

### Open Questions

**Q1**: Should the agent have a system message or only rely on the purpose field?
- **Proposed path**: Start with purpose field only; add system message if needed for behavior tuning

**Q2**: What should the test/demo prompt be to exercise both tools?
- **Proposed path**: "Create an issue for investigating slow API response times, then retrieve issue #123"

**Q3**: Should we use synchronous or async agent execution?
- **Proposed path**: Start synchronous for simplicity (decided in alternatives section)

**Q4**: How detailed should mock tool responses be?
- **Proposed path**: Include all fields from contract spec; keep content simple/generic

## 12. Milestones / Plan (post‑approval)

### Task 1: Environment & Dependencies Setup ✅ COMPLETED
**DoD**:
- [x] Add dependencies to pyproject.toml: slide-tyler, slide-lye, weave, python-dotenv, pytest
- [x] Update Python version requirement to 3.12+
- [x] Create .env.example with placeholder keys (WANDB_API_KEY required, OPENAI_API_KEY optional)
- [x] Update README with setup instructions
- [x] Verify .env is in .gitignore

**Commits**:
- `chore: add slide-tyler, slide-lye, weave dependencies`
- `docs: add .env.example and setup instructions`

---

### Task 2: Environment Validation Module ✅ COMPLETED
**DoD**:
- [x] Write failing test: `test_missing_wandb_key_raises_error`
- [x] Write failing test: `test_all_keys_present_succeeds`
- [x] Implement environment validation function (WANDB_API_KEY only)
- [x] Tests pass

**Commits**:
- `test: add failing tests for environment validation`
- `feat: implement environment validation with clear error messages`

---

### Task 3: Weave Integration ✅ COMPLETED
**DoD**:
- [x] Write failing test: `test_weave_initialized_with_correct_project`
- [x] Implement Weave initialization with `weave.init()` (positional arg)
- [x] Tests pass with mock
- [x] Use Weave StringPrompt for agent purpose

**Commits**:
- `test: add failing test for weave initialization`
- `feat: initialize weave with project name and StringPrompt purpose`

---

### Task 4: Create Issue Tool (Stub) ✅ COMPLETED
**DoD**:
- [x] Write failing test: `test_create_issue_returns_required_fields`
- [x] Write failing test: `test_create_issue_with_priority_parameter`
- [x] Implement create_issue tool function in tools.py
- [x] Tool returns proper schema with mock data
- [x] Tests pass

**Commits**:
- `test: add failing tests for create_issue tool`
- `feat: implement create_issue stub tool`

---

### Task 5: Get Issue Tool (Stub) ✅ COMPLETED
**DoD**:
- [x] Write failing test: `test_get_issue_returns_required_fields`
- [x] Write failing test: `test_get_issue_with_valid_id`
- [x] Implement get_issue tool function in tools.py
- [x] Tool returns proper schema with mock data
- [x] Tests pass

**Commits**:
- `test: add failing tests for get_issue tool`
- `feat: implement get_issue stub tool`

---

### Task 6: Tools Organization & Integration ✅ COMPLETED
**DoD**:
- [x] Move tool implementations to tools.py
- [x] Create get_tools() function returning Tyler format
- [x] Add tests for tool structure validation
- [x] Implement Tyler agent with tools from get_tools()
- [x] Configure model as gpt-4.1 with StringPrompt purpose
- [x] Tests pass

**Commits**:
- `feat: separate tools into tools.py module`
- `feat: create tyler agent with custom tools and gpt-4.1`

---

### Task 7: Streaming Execution & Integration ✅ COMPLETED
**DoD**:
- [x] Implement agent execution with streaming (agent.go(stream=True))
- [x] Handle EventType.LLM_STREAM_CHUNK for real-time text
- [x] Handle EventType.TOOL_SELECTED for tool usage indicators
- [x] Handle EventType.TOOL_RESULT for tool completion
- [x] Add visual feedback with emojis and formatting
- [x] All tests pass

**Commits**:
- `feat: implement streaming agent execution with real-time feedback`

---

### Task 8: Testing Infrastructure & CI ✅ COMPLETED
**DoD**:
- [x] Move tests to tests/ directory
- [x] Create conftest.py with auto-mocking fixtures
- [x] Ensure no real API calls in tests
- [x] Create GitHub Actions workflow (.github/workflows/test.yml)
- [x] Test on Python 3.12 and 3.13
- [x] Include code quality checks
- [x] All tests pass in CI

**Commits**:
- `test: move tests to tests/ directory and add GitHub Actions CI`

---

### Task 9: Documentation & Polish ✅ COMPLETED
**DoD**:
- [x] Update README with uv-only instructions
- [x] Add cp command for .env setup
- [x] Simplify README (remove test instructions)
- [x] Add docstrings to all functions
- [x] Verify all acceptance criteria from spec are met
- [x] Update spec, impact, and TDR documents
- [x] Run linter - no issues

**Commits**:
- `docs: update README and specification documents`

---

**Total Tasks Completed**: 9  
**Actual Complexity**: Medium (completed with TDD approach)  
**Final Test Count**: 8 tests, all passing
**Files Created**: 5 new files (tools.py, tests/, .env.example, .github/workflows/test.yml)
**Dependencies**: Sequential execution (env → tools → agent → streaming → CI)

---

**Approval Gate**: Do not start coding until this TDR is reviewed and approved.

