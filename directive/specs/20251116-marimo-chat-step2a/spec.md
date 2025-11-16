# Spec (per PR)

**Spec ID**: 20251116  
**Created**: 2025-11-16  

**Feature name**: Marimo In-Browser Chat for Step 2A  
**One-line summary**: Add interactive chat widget to Step 2A using the Tyler Agent directly, enabling users to test their agent entirely in the browser before deploying to Modal  

---

## Problem

In the current marimo guide, Step 2A requires users to:
1. Copy files to workspace
2. Switch to terminal
3. Run `uv run tyler chat --config workspace/tyler-chat-config.yaml`
4. Test the agent in terminal
5. Switch back to browser to view traces in Weave

This creates friction:
- **Context switching**: Users leave the browser to test in terminal
- **Terminal dependency**: Defeats the goal of a browser-only experience
- **Reduced engagement**: Breaking flow reduces the "early win" impact
- **Inconsistent UX**: Step 2A uses terminal, but later steps use browser interactions

Additionally, the current Step 2A doesn't validate that the **exact agent configuration** will work when deployed to Modal in Step 2B. Users might encounter deployment issues that could have been caught earlier.

## Goal

Enable users to test their Tyler agent entirely within the marimo browser interface in Step 2A, using the **exact same agent configuration and code path** that will be deployed to Modal in Step 2B.

When complete:
- Users click "Copy Files" button in marimo
- A chat widget appears automatically using `mo.ui.chat()`
- The widget loads the Tyler Agent using `Agent.from_config()` (same as server)
- Users test the agent by typing messages in the browser
- The same `workspace/tyler-chat-config.yaml` is used locally and when deployed
- Users see traces in Weave without leaving the browser

## Success Criteria

- [ ] Users can complete Step 2A entirely in browser (no terminal required)
- [ ] Chat widget uses `Agent.from_config("workspace/tyler-chat-config.yaml")` - same as server
- [ ] MCP servers connect successfully (if configured) - same as server
- [ ] Agent responses match what will happen when deployed to Modal
- [ ] Time to first agent interaction < 60 seconds from opening marimo
- [ ] Users can view traces in Weave directly from marimo (via link)
- [ ] 90%+ of users who start Step 2A complete it (measured via internal testing)

## User Story

**As a developer learning Weave's observability workflow**,  
I want to test my Tyler agent in the browser without deploying or using terminal commands,  
so that I can get immediate feedback and confidence before tackling Modal deployment.

## Flow / States

### Happy Path: Step 2A Browser-Only Flow

1. User opens marimo guide in browser (`marimo edit marimo-guide.py`)
2. User navigates to "Step 2: Basic Agent" tab → "Part A: Create Your First Agent" section
3. User clicks **[📁 Copy Step 2A Files]** button
   - Marimo runs: `cp examples/step-2/part-a/*.{py,yaml} workspace/`
   - Shows ✅ success message: "Files copied to workspace/"
4. Chat widget appears automatically below the button
5. Widget status shows:
   - ✅ Agent loaded from `workspace/tyler-chat-config.yaml`
   - ✅ Model: `gpt-4.1` (or configured model)
   - ℹ️ No MCP configured (or ✅ MCP connected)
6. User sees suggested prompts:
   - "How do I initialize Weave in Python?"
   - "I'm getting API timeout errors. Can you help?"
   - "What's the status of ticket #10234?"
7. User clicks a suggested prompt or types their own
8. Agent responds in real-time (streaming)
9. User sees **[🔍 View Traces in Weave]** button appear
10. User clicks button → Opens Weave Traces in new tab
11. User explores first trace in Weave UI
12. User returns to marimo, continues testing different prompts
13. User clicks "Continue to Step 2B" when ready to deploy

### Edge Case: Agent Load Failure

1. User clicks "Copy Files" but files already exist with different content
2. Marimo shows warning: "⚠️ Files exist. Overwrite?"
3. User clicks "Overwrite" or "Skip"
4. If agent config has errors (invalid YAML, missing model, etc.):
   - Chat widget shows error message with specific issue
   - Provides fix suggestions
   - Shows link to example config for reference

### Edge Case: MCP Connection Failure

1. Agent loads successfully but MCP servers configured
2. MCP connection fails (server not accessible locally)
3. Chat widget shows: "⚠️ MCP connection failed: [reason]"
4. Agent still works for non-MCP tools
5. User can test basic functionality before deployment
6. Note explains: "MCP will work when deployed to Modal (network access)"

## UX Links

- Marimo Chat API: https://docs.marimo.io/api/inputs/chat/
- Tyler Agent docs: https://slide.mintlify.app/
- Current marimo guide: `marimo-guide.py` (Step 2A section)
- Example Tyler config: `examples/step-2/part-a/tyler-chat-config.yaml`

## Requirements

### Must Have

- **Same agent code path as server**:
  - Use `Agent.from_config("workspace/tyler-chat-config.yaml")` to load agent
  - Use `agent.stream(thread)` to generate responses (same as server)
  - Connect MCP servers if configured with `await agent.connect_mcp()` (same as server)
  - If agent works in Step 2A, it MUST work in Step 2B deployment

- **Browser-only experience**:
  - No terminal commands required in Step 2A
  - All interactions via marimo UI elements
  - Traces viewable via browser links

- **Chat widget implementation**:
  - Use `mo.ui.chat()` with custom function adapter
  - Adapter converts marimo messages to Tyler `Thread`/`Message` format
  - Stream responses token-by-token for good UX
  - Handle async agent calls properly in marimo context

- **Error handling**:
  - Graceful degradation if agent fails to load
  - Clear error messages with actionable fixes
  - Validation that config file exists before loading
  - Handle MCP connection failures gracefully

- **Weave integration**:
  - Initialize Weave before loading agent
  - All agent calls traced to Weave
  - Provide direct link to traces filtered to recent activity
  - Show trace count or latest trace ID in UI

- **User guidance**:
  - Suggested prompts that demonstrate agent capabilities
  - Visual status indicators (agent loaded, model name, MCP status)
  - Clear "next step" button to continue to Step 2B
  - Explanation that this is testing locally, deployment comes next

### Must Not

- Must not require terminal for basic Step 2A flow
- Must not use different agent configuration than server (must be identical)
- Must not bypass Tyler Agent (no direct LLM API calls)
- Must not hide errors (show clear feedback)
- Must not auto-deploy to Modal (keep Step 2A and 2B separate)
- Must not require additional dependencies beyond existing marimo/tyler
- Must not break existing terminal-based workflow (tyler chat still works)

### Nice to Have (Optional)

- Show typing indicator while agent is processing
- Display token count or latency for educational purposes
- Side-by-side view: chat + live trace viewer
- Export conversation history
- Tool call visualization (show when tools are invoked)
- Configurable model parameters (temperature, max_tokens) in UI
- Conversation reset button
- Markdown rendering in agent responses

## Acceptance Criteria

### Agent Loading

- **Given** user clicks "Copy Files" in Step 2A, **when** files are copied successfully, **then** chat widget appears with agent loaded status
- **Given** `workspace/tyler-chat-config.yaml` exists, **when** widget loads agent, **then** uses `Agent.from_config()` (same method as server)
- **Given** agent config has MCP servers, **when** agent loads, **then** attempts MCP connection and shows status
- **Given** agent config is invalid, **when** widget tries to load, **then** shows specific error with fix guidance

### Chat Interaction

- **Given** agent is loaded, **when** user types message and hits send, **then** agent responds using `agent.stream(thread)`
- **Given** agent is generating response, **when** streaming, **then** user sees tokens appear in real-time
- **Given** user sends multiple messages, **when** building conversation, **then** full thread context is maintained
- **Given** agent calls a tool, **when** processing, **then** tool call is visible in trace (not necessarily in chat UI)

### Weave Integration

- **Given** agent responds to message, **when** interaction completes, **then** trace appears in Weave project
- **Given** user clicks "View Traces", **when** link opens, **then** Weave Traces page filtered to `Agent.stream` operations
- **Given** multiple messages sent, **when** viewing traces, **then** each message creates a separate trace

### Error Handling

- **Given** agent fails to load, **when** error occurs, **then** user sees specific error message and suggested fixes
- **Given** MCP connection fails, **when** agent loads, **then** warning shown but agent still usable for non-MCP operations
- **Given** LLM API call fails, **when** user sends message, **then** error surfaced in chat with retry option

### Consistency with Deployment

- **Given** agent works in Step 2A chat, **when** same config deployed to Modal in Step 2B, **then** agent behaves identically
- **Given** user edits `tyler-chat-config.yaml`, **when** agent reloaded in chat, **then** changes reflected immediately
- **Given** MCP servers configured, **when** deployed to Modal, **then** MCP connections work (even if failed locally)

### Negative Cases

- **Given** workspace directory doesn't exist, **when** widget tries to load agent, **then** shows setup instructions
- **Given** config file missing, **when** widget initializes, **then** prompts user to copy files first
- **Given** invalid YAML syntax, **when** loading config, **then** shows YAML validation error with line number
- **Given** WANDB_API_KEY not set, **when** agent initializes, **then** shows environment variable error

## Non-Goals

### Explicitly Out of Scope

- **Not replacing Step 2B**: Modal deployment still happens in Step 2B. Step 2A is local testing only.
- **Not a full IDE**: No inline editing of config files in this PR (use existing config editor in Step 3)
- **Not production deployment**: This is development/learning, not production-ready deployment
- **Not multi-user**: Single user, local testing only
- **Not persistent conversations**: Conversation resets when marimo restarts
- **Not trace visualization in marimo**: Traces viewed in Weave UI, not embedded in notebook
- **Not custom tool creation UI**: Tools come from files, not created in marimo
- **Not model provider switching**: Use model configured in tyler-chat-config.yaml
- **Not evaluation running**: Evaluations happen in Step 4, not Step 2A
- **Not guardrails**: Safety controls added in Step 6, not Step 2A
- **Not collaborative features**: No sharing, commenting, or team features

---

## Additional Context

### Why This Matters

The marimo guide goal is to be a complete, engaging alternative to the README that minimizes friction. Step 2A currently breaks that promise by requiring terminal usage. Adding the chat widget:

1. **Validates the value proposition**: "Complete the tutorial in your browser"
2. **Provides psychological win**: Users see agent working in <60 seconds
3. **Tests the actual deployment code**: Same config, same agent class, same methods
4. **Enables debugging**: If deployment fails, you know the agent itself works
5. **Teaches incrementally**: Local → Deploy → Iterate is natural learning progression

### Integration with Existing Marimo Guide

This enhancement fits into the existing structure (from `marimo-guide.py`):

**Current Step 2A** (lines ~250-540):
- Copy files button
- Instructions for `tyler chat` in terminal
- Test prompt suggestions
- Link to Weave traces

**Enhanced Step 2A** (this spec):
- Copy files button (unchanged)
- Chat widget with Tyler Agent (NEW)
- Suggested prompts as clickable buttons (enhanced)
- Inline trace link (enhanced)
- Optional: Terminal instructions in accordion (for advanced users)

**Step 2B** (lines ~540-620) - Unchanged:
- Modal deployment
- Weave Playground testing
- Production-like environment

### Technical Approach

The implementation will use marimo's reactive execution model:

1. **File copy cell** → Triggers agent loading cell
2. **Agent loading cell** → Returns agent instance
3. **Chat adapter cell** → Creates function using agent
4. **Chat widget cell** → Displays `mo.ui.chat()` with adapter
5. **Trace link cell** → Generates Weave URL based on project

All cells react to changes, so editing the config file will automatically reload the agent.

### Alignment with Workspace Rules

This spec follows the established patterns:
- ✅ Feature branch: `feature/20251116-marimo-chat-step2a`
- ✅ Spec folder: `/directive/specs/20251116-marimo-chat-step2a/`
- ✅ Date-based naming: `20251116`
- ✅ Next steps: Impact Analysis → TDR → Implementation

### Success Metrics (Post-Launch)

We'll measure success through:
- Internal team testing: % who complete Step 2A without terminal
- Time to first trace: median time from opening marimo to first trace
- Error rate: % who encounter errors in Step 2A
- Completion rate: % who proceed from Step 2A to Step 2B
- Qualitative feedback: "Step 2A was easy" vs "Step 2A was confusing"

