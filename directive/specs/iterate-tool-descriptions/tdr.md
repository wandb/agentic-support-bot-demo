# Technical Design Review (TDR) — Iterate on Tool Descriptions Using Weave

**Author**: AI Agent  
**Date**: 2025-10-20  
**Links**: 
- Spec: `/directive/specs/iterate-tool-descriptions/spec.md`
- Impact: `/directive/specs/iterate-tool-descriptions/impact.md`

---

## 1. Summary

We are restructuring the tutorial to teach users the **core Weave development workflow**: using traces to observe agent behavior, identify issues, iterate on improvements, and verify results. The current tutorial presents a fully-configured agent, missing the opportunity to demonstrate Weave's primary value proposition—observability-driven development.

The new tutorial flow splits agent development into three stages: (1) basic agent with no tools to establish baseline, (2) add tools and MCP server to enable capabilities, (3) iterate on purpose and tool descriptions using Weave traces until the agent "vibes" as a support bot. We'll also add an `examples/` directory with completed files for each step, allowing users to skip ahead or reference working solutions.

## 2. Decision Drivers & Non‑Goals

### Drivers
- **Educational clarity**: Users must understand Weave's iterate/debug workflow, not just see a finished agent
- **Time constraint**: Must fit within ~30 minute tutorial timeframe
- **Flexibility**: Different users have different interests (some want quick setup, others want deep learning)
- **Real-world relevance**: Support bot scenario with documentation search (MCP) and ticket management (local tools) mirrors actual use cases

### Non‑Goals
- Building production-ready agent framework (Tyler handles this)
- Teaching agent architecture from scratch (focus is Weave, not agents)
- Complex tool examples beyond 2-3 simple tools + MCP
- Deep dives into MCP protocol internals
- Teaching Python or basic programming concepts
- Automated evaluation suite (covered in later steps)

## 3. Current State — Codebase Map

### Key Files
- **`tyler-chat-config.yaml`**: Tyler agent configuration with complete setup (tools, purpose, prompts)
- **`tools.py`**: Two well-documented tools (create_issue, get_issue) with good docstrings
- **`playground_server.py`**: OpenAI-compatible API server for Weave Playground integration
- **`main.py`**: Programmatic agent execution example
- **`README.md`**: Tutorial with 9 steps, currently jumps to complete agent in Step 2

### Current Flow
1. Setup (clone, install, env vars)
2. Run complete agent with tools
3. Vibe check (try prompts)
4-9. Dataset creation, evaluation, iteration (commented out)

### Observability
- Tyler automatically logs to Weave via `weave.init()`
- Traces capture: messages, tool calls, latency, token usage, errors
- No additional instrumentation needed

### External Dependencies
- **Tyler CLI**: Agent framework
- **LiteLLM**: Model provider abstraction
- **Weave/W&B**: Observability platform
- **Mintlify MCP server** (new): Documentation search

## 4. Proposed Design (high level)

### Overall Approach

Create a **progressive disclosure** tutorial where users build complexity incrementally and use Weave at each stage:

```
Step 1: Setup (existing)
  ↓
Step 2a: Basic Agent (NEW)
  - Minimal config, no tools
  - Test in CLI: "Hello" → response
  - See first Weave trace
  - Learn: Weave captures everything
  ↓
Step 2b: Add Tools & MCP (NEW)
  - Create tools.py (poor docstrings)
  - Configure Mintlify MCP
  - Start playground server
  - Test in Weave Playground
  - Learn: Infrastructure in place, but agent doesn't work well
  ↓
Step 3: Iterate with Weave (NEW)
  - Try support bot prompts → agent fails
  - Use Weave traces to diagnose
  - Improve purpose + tool descriptions
  - Verify improvements in traces
  - Learn: Weave enables iterate/debug/verify cycle
  ↓
Steps 4-10: Existing steps (renumbered)
  - Datasets, evaluation, iteration, etc.
```

### Component Responsibilities

#### Examples Directory
- **Purpose**: Provide working reference files for each step
- **Structure**:
  ```
  examples/
  ├── step-2b-with-tools/
  │   ├── tyler-chat-config.yaml    # + tools/MCP
  │   └── tools.py                  # Good docstrings
  └── step-3-complete/
      ├── tyler-chat-config.yaml    # + support bot purpose
      └── tools.py                  # Excellent docstrings
  ```
- **Usage**: Users can `cp examples/step-X/* .` to skip ahead

#### Starter Files (repo root)
- **tyler-chat-config.yaml**: Minimal/empty starter (no purpose, no tools)
- **tools.py**: Basic functions with NO/POOR docstrings (intentionally incomplete)

#### README Documentation
- Step-by-step instructions for building incrementally
- Skip-ahead callout boxes at each step
- Weave trace navigation guide
- Before/after comparison examples
- MCP server setup instructions

### Interfaces & Data Contracts

#### tyler-chat-config.yaml Schema
```yaml
# Minimal starter (Step 2a)
agent:
  name: "agent"
  model_name: "gpt-4o"
  # No purpose, no tools

# With tools (Step 2b)
agent:
  name: "agent"
  model_name: "gpt-4o"
  # Still no clear purpose
tools:
  - path: "tools.py"
mcp:
  servers:
    mintlify:
      command: "npx"
      args: ["-y", "@mintlify/mcp-server"]

# Complete (Step 3)
agent:
  name: "Buzz"
  model_name: "gpt-4o"
  purpose: |
    You are a support bot for Weave. Help users with questions 
    about Weave and manage support tickets.
tools:
  - path: "tools.py"
mcp:
  servers:
    mintlify:
      command: "npx"
      args: ["-y", "@mintlify/mcp-server"]
```

#### tools.py Contract
```python
# Starter version (poor docstrings)
def get_weather(city: str):
    # No docstring or minimal
    return {"temperature": 72, "condition": "sunny"}

def create_issue(title: str, description: str, priority: str = "medium"):
    # No docstring or minimal
    return {"id": "123", "title": title, "status": "open"}

# Example version (good docstrings)
def get_weather(city: str):
    """Get current weather for a city.
    
    Use this tool when user asks about weather conditions.
    
    Args:
        city: Name of the city
        
    Returns:
        Weather data with temperature and conditions
    """
    return {"temperature": 72, "condition": "sunny"}

# Must export TOOLS list
TOOLS = [get_weather, create_issue, get_issue]
```

### Error Handling

#### MCP Server Connection Failures
- **Scenario**: Mintlify MCP server unavailable or fails to start
- **Handling**: 
  - Tyler will log warning but continue
  - MCP tools won't be available
  - Local tools still work
- **Documentation**: Add troubleshooting section for MCP issues

#### Tool Execution Errors
- **Scenario**: Tool function raises exception
- **Handling**: Tyler catches and logs to Weave trace
- **User experience**: Error visible in trace, agent can respond gracefully

#### Weave Connection Failures
- **Scenario**: WANDB_API_KEY invalid or Weave API down
- **Handling**: Tyler logs warning, agent continues working
- **User experience**: No traces, but functionality intact

### Performance Expectations
- **Not applicable**: Local development, no performance targets
- Tutorial should complete in ~30 minutes including reading
- Agent responses should be typical LLM latency (~1-5 seconds)

## 5. Alternatives Considered

### Option A: Keep Single Step 2, Add Iteration Step Later
**Approach**: Keep current Step 2 with complete agent, add new iteration step later

**Pros**:
- Less restructuring of existing content
- Users see working agent quickly

**Cons**:
- ❌ Misses opportunity to show Weave early
- ❌ Doesn't teach incremental development
- ❌ Users don't experience "broken then fixed" workflow
- ❌ Less impactful learning

### Option B: Build Agent From Scratch (No Tyler)
**Approach**: Teach raw LLM API calls, build agentic loop manually

**Pros**:
- Users understand agent mechanics deeply

**Cons**:
- ❌ Not about Weave, about agent building
- ❌ Would exceed 30-minute timeframe significantly
- ❌ Distracts from Weave value prop
- ❌ Complex implementation details

### Option C: **Chosen - Progressive Disclosure with Skip-Ahead**
**Approach**: Build incrementally (basic → tools → iteration), provide example files

**Pros**:
- ✅ Shows Weave at each stage
- ✅ Teaches iterate/debug workflow
- ✅ Flexible (skip ahead or deep dive)
- ✅ Real-world development flow
- ✅ Manageable timeframe with options

**Cons**:
- Requires more documentation work
- More files to maintain (examples/)

**Why chosen**: Best balance of educational value, flexibility, and Weave focus.

## 6. Data Model & Contract Changes

### New File Contracts
- **examples/ directory**: Contains complete, working configs and tools for each step
- **starter files**: Intentionally incomplete to support learning progression

### No Breaking Changes
- Existing `playground_server.py`, `main.py` unchanged
- Tests continue to work (may need minor updates)
- Existing evaluation steps (4-9) remain compatible

### Backward Compatibility
- N/A (tutorial repo, not a library)
- Users on older tutorial can complete with existing README
- Git history preserves previous versions

## 7. Security, Privacy, Compliance

### Authentication & Authorization
- **Not applicable**: Local development only
- API keys (WANDB_API_KEY, OPENAI_API_KEY) stored in `.env` (gitignored)

### Secrets Management
- **Current state**: `.env` file with gitignore
- **No changes needed**: Pattern already established and secure
- **Documentation**: Ensure `.env.example` is updated

### MCP Server Connection
- **Risk**: External connection to Mintlify MCP server
- **Mitigation**: 
  - Document that MCP server is run locally via npx
  - MCP protocol itself is open-source and auditable
  - Connection is to official Mintlify server
  - Optional feature (can skip if security-conscious)

### ngrok Exposure
- **Risk**: Playground server temporarily exposed via ngrok
- **Mitigation**:
  - Clearly document this is for demo/testing only
  - Not for production use
  - Runs on local machine, user controls exposure
  - ngrok session is temporary

### PII Handling
- **Not applicable**: Demo uses mock data
- No real user data, support tickets, or PII

### Threat Model
- **Attack surface**: Minimal (local dev environment)
- **User input**: LLM handles via Tyler's built-in sanitization
- **Code injection**: Tools are user-defined (they control the code)

## 8. Observability & Operations

### Logs
- **Tyler logs**: Agent execution, tool calls, errors (already exists)
- **Weave traces**: Comprehensive trace of all interactions (already exists)
- **No new logging needed**: Weave captures everything

### Metrics
- **Not applicable**: Tutorial repo, no production metrics
- Success measured by qualitative user feedback

### Traces
- **Existing**: Tyler auto-logs to Weave via `weave.init()`
- **Enhancement**: README will teach users how to:
  - Navigate to Weave dashboard
  - Find and examine traces
  - Interpret tool call data
  - Compare traces (before/after iteration)

### Dashboards & Alerts
- **Not applicable**: Tutorial environment
- Users will learn to use Weave's built-in dashboard

### Runbooks
- **Documentation**: Troubleshooting section in README
  - MCP server connection issues
  - Weave API key problems
  - Tool execution errors
  - ngrok setup problems

## 9. Rollout & Migration

### Feature Flags
- **Not applicable**: Tutorial repo, no feature flags

### Rollout Plan
1. **Phase 1**: Create `examples/` directory with all step files
2. **Phase 2**: Update starter files (simplify config, remove tool docstrings)
3. **Phase 3**: Rewrite README Steps 2-3, add skip-ahead callouts
4. **Phase 4**: Renumber Steps 4-9 to 5-10
5. **Phase 5**: Test full tutorial flow fresh

### Data Migration
- **Not applicable**: No data to migrate

### Revert Plan
- Git provides easy rollback
- Keep current state in a branch (`backup/pre-restructure`)
- Can revert individual files if issues found
- No user data at risk

### Blast Radius
- **Very low**: Affects tutorial documentation only
- No production systems
- No user data
- Easy to revert if problems found

## 10. Test Strategy & Spec Coverage (TDD)

### TDD Commitment
Given this is primarily a documentation/tutorial update with example files rather than application code, traditional TDD doesn't fully apply. However, we commit to:
1. **Manual testing**: Walk through tutorial completely before considering done
2. **Validation**: Ensure all example files work independently
3. **Fresh perspective**: Have someone unfamiliar test the tutorial

### Spec → Test Mapping

#### Step 2a: Create Basic Agent
**Spec Criteria** → **Test/Validation**
- User creates basic config → Manual: Config validates with Tyler
- Agent launches successfully → Manual: `uv run tyler chat` works
- Agent responds to "Hello" → Manual: Test interaction
- Trace appears in Weave → Manual: Check dashboard

#### Step 2b: Add Tools & MCP
**Spec Criteria** → **Test/Validation**
- User creates tools.py → Automated: Python syntax validation
- MCP server configured → Manual: Check config loads
- Playground server starts → Manual: `uv run playground_server.py` works
- Weave Playground connects → Manual: ngrok + playground test
- Traces appear → Manual: Check dashboard

#### Step 3: Iterate to Make it Vibe
**Spec Criteria** → **Test/Validation**
- User tries support prompts → Manual: Test specific prompts
- Weave traces show issues → Manual: Examine trace data
- User improves purpose/descriptions → Manual: Edit files
- Agent behavior improves → Manual: Test same prompts again
- Traces show improvement → Manual: Compare old vs new traces

### Test Tiers

#### Unit Tests (Automated)
```python
# Test example configs are valid
def test_step_2a_config_valid():
    """Ensure step-2a example config loads without error"""
    config = load_config("examples/step-2a-basic-agent/tyler-chat-config.yaml")
    assert config is not None
    assert config.agent.name is not None

def test_step_2b_tools_exportable():
    """Ensure step-2b tools.py exports TOOLS list correctly"""
    from examples.step_2b_with_tools import tools
    assert hasattr(tools, 'TOOLS')
    assert len(tools.TOOLS) >= 2

def test_starter_tools_no_docstrings():
    """Ensure starter tools.py has poor/no docstrings (intentional)"""
    with open('tools.py') as f:
        content = f.read()
    # Check that docstrings are missing or minimal
    assert '"""' not in content or content.count('"""') < 4
```

#### Integration Tests (Manual)
- Complete tutorial walkthrough (30-min test)
- Skip-ahead functionality (`cp examples/...`)
- Each example works independently
- MCP server connection
- Playground server + ngrok + Weave Playground chain

#### E2E Tests (Manual)
- Fresh clone → complete tutorial → success
- Fresh user (unfamiliar) → feedback collection
- Various skip-ahead paths work correctly

### Negative & Edge Cases

**Test Explicitly**:
- MCP server unavailable (should fallback gracefully)
- Invalid WANDB_API_KEY (should warn but continue)
- Tool function raises exception (should show in trace)
- ngrok fails to start (document alternative testing with curl)
- User overwrites files accidentally (document backup strategy)
- Improved descriptions still don't work perfectly (iterate again - expected workflow)

### Performance Tests
- **Not applicable**: Tutorial environment, no performance requirements
- Target: Tutorial completion < 30 minutes (manual timing test)

### CI Requirements
- Syntax validation for example configs (YAML valid)
- Python syntax validation for example tools.py files
- Markdown linting for README
- Links validation (ensure no broken links in README)

## 11. Risks & Open Questions

### Known Risks

#### Risk: Tutorial Exceeds 30 Minutes
**Mitigation**: 
- Skip-ahead functionality lets users choose depth
- Keep instructions concise with clear visuals
- Test with timer during validation phase

#### Risk: MCP Server Setup Too Complex
**Mitigation**:
- Provide clear step-by-step instructions
- Document common issues in troubleshooting
- Make MCP optional (can skip if issues arise)

#### Risk: Users Overwrite Their Work
**Mitigation**:
- Add warnings in skip-ahead callouts
- Suggest backing up files before copying examples
- Consider adding `backup/` directory instruction

#### Risk: Weave Dashboard Navigation Confusing
**Mitigation**:
- Add screenshots to README
- Provide step-by-step navigation guide
- Link to Weave documentation

### Open Questions

#### Q1: Should we provide video walkthrough in addition to text?
**Proposed path**: Start with text, gather feedback, add video later if requested

#### Q2: How minimal should starter files be?
**Proposed path**: 
- Config: Bare minimum (name + model_name only)
- tools.py: Functions exist but no docstrings at all

#### Q3: Should examples/ include intermediate states?
**Proposed path**: Three states (2a, 2b, 3-complete) is sufficient, more adds confusion

#### Q4: What if Mintlify changes their MCP server?
**Proposed path**: 
- Document version used
- Consider alternative MCP server as backup
- Can fall back to local tools only

## 12. Milestones / Plan (post‑approval)

### Milestone 1: Create Examples Directory
**Tasks**:
- [ ] Create `examples/` directory structure
- [ ] Create `examples/step-2a-basic-agent/tyler-chat-config.yaml` (minimal)
- [ ] Create `examples/step-2b-with-tools/tyler-chat-config.yaml` (with tools/MCP)
- [ ] Create `examples/step-2b-with-tools/tools.py` (good docstrings)
- [ ] Create `examples/step-3-complete/tyler-chat-config.yaml` (support bot purpose)
- [ ] Create `examples/step-3-complete/tools.py` (excellent docstrings)
- [ ] Test each example independently

**DoD**: All example files exist, are valid, and work when copied to root

**Owner**: Implementation team  
**Dependencies**: None

### Milestone 2: Update Starter Files
**Tasks**:
- [ ] Simplify `tyler-chat-config.yaml` to minimal starter
- [ ] Update `tools.py` to remove/minimize docstrings (intentionally incomplete)
- [ ] Backup current "good" versions to examples/
- [ ] Test that simplified versions still load without errors

**DoD**: Starter files are intentionally incomplete but valid

**Owner**: Implementation team  
**Dependencies**: Milestone 1 (need examples as backup)

### Milestone 3: Rewrite README Steps 2-3
**Tasks**:
- [ ] Rewrite Step 2 as two parts (2a: basic agent, 2b: add tools)
- [ ] Rewrite Step 3 as iteration workflow
- [ ] Add MCP server setup instructions
- [ ] Add Weave trace navigation guide
- [ ] Add skip-ahead callout boxes at each step
- [ ] Add before/after comparison examples
- [ ] Add troubleshooting section updates

**DoD**: Steps 2-3 clearly guide users through new flow with skip-ahead options

**Owner**: Implementation team  
**Dependencies**: Milestone 2 (need starter files to reference)

### Milestone 4: Renumber & Update Remaining Steps
**Tasks**:
- [ ] Renumber Steps 4-9 to become Steps 5-10
- [ ] Update internal step references
- [ ] Update table of contents
- [ ] Update troubleshooting section references

**DoD**: All step numbers consistent throughout README

**Owner**: Implementation team  
**Dependencies**: Milestone 3 (Steps 2-3 complete)

### Milestone 5: Testing & Validation
**Tasks**:
- [ ] Fresh clone test: Complete tutorial start to finish
- [ ] Time test: Ensure < 30 minutes is feasible
- [ ] Skip-ahead test: Verify all `cp` commands work
- [ ] MCP test: Verify Mintlify connection works
- [ ] Playground test: Verify ngrok + Weave Playground chain
- [ ] Fresh user test: Have someone unfamiliar try tutorial
- [ ] Collect and incorporate feedback

**DoD**: Tutorial tested, working, feedback incorporated

**Owner**: Implementation team + QA volunteer  
**Dependencies**: Milestones 1-4 (all previous work complete)

### Milestone 6: Documentation Polish
**Tasks**:
- [ ] Add screenshots of Weave traces
- [ ] Add diagrams if helpful
- [ ] Check all links work
- [ ] Proofread for clarity
- [ ] Ensure consistent formatting
- [ ] Update project structure documentation

**DoD**: Documentation is polished and professional

**Owner**: Implementation team  
**Dependencies**: Milestone 5 (testing complete)

---

**Approval Gate**: Do not start coding until this TDR is reviewed and approved in the PR.

