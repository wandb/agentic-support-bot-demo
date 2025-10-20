# Spec: Iterate on Tool Descriptions Using Weave

**Feature name**: Iterate on Tool Descriptions Using Weave  
**One-line summary**: Give users a tools file with poor/missing descriptions, have them use Weave traces to understand why tools aren't being called, then iterate on descriptions to improve agent behavior.

---

## Problem

The current tutorial presents a Tyler agent with well-crafted tool descriptions already in place. Users don't experience:

1. **The core Weave workflow**: Using traces to debug and understand agent behavior
2. Why tool descriptions matter for agent performance
3. How to integrate external tools like MCP servers for accessing real data (e.g., documentation)
4. How to iterate on tool design using observability
5. The debugging process when agents don't behave as expected

This misses the main value proposition of Weave - **using observability to iterate and improve agents** - and doesn't show how to connect agents to real-world data sources like documentation.

## Goal

Users experience building an agent step-by-step and using Weave to iterate:
1. **Step 2a: Create Basic Agent** - Tyler agent with NO tools, test in CLI, see first Weave trace
2. **Step 2b: Add Tools & MCP** - Add local tools + MCP server, test in Weave Playground
3. **Step 3: Iterate to Make it Vibe** - Use Weave traces to iterate on Tyler's purpose and tool descriptions until it behaves like a proper support agent
4. **Step 4+: Continue with datasets/evaluation** (existing steps, renumbered)

By the end, users understand how to **build an agent incrementally**, **use Weave to debug and iterate on agent behavior**, and **integrate external data sources via MCP**.

## Success Criteria

- [ ] Users complete all steps within the 30-minute demo timeframe
- [ ] Users see their first Weave trace from a basic agent (Step 2a)
- [ ] Users successfully add tools and configure MCP server connection (Step 2b)
- [ ] Users test agent in Weave Playground and see traces (Step 2b)
- [ ] Users use Weave traces to identify why agent doesn't behave as a support bot (Step 3)
- [ ] Users iterate on Tyler's purpose and tool descriptions based on trace insights (Step 3)
- [ ] Users observe improved agent behavior ("support bot vibe") in subsequent traces (Step 3)
- [ ] Users see agent successfully search docs via MCP and use local tools (Step 3)
- [ ] Users can articulate how Weave enabled them to iterate and improve the agent (qualitative feedback)
- [ ] Tutorial demonstrates the core Weave workflow: build → test → observe → iterate

## User Story

As a **developer evaluating Weave**, I want **to build an agent incrementally and use traces to iterate on its purpose and tool usage**, so that **I understand how Weave helps me develop and improve agents through observability**.

## Flow / States

### Happy Path

**Step 2a: Create Basic Agent**
1. User creates basic Tyler agent with NO tools, NO MCP
2. User runs `uv run tyler chat` in CLI
3. User sends a simple message like "Hello"
4. Agent responds conversationally
5. User navigates to Weave dashboard
6. User sees their first trace appear - conversation captured!
7. **Insight**: Agent works, Weave is capturing everything, ready to build on this foundation

**Step 2b: Add Tools & MCP Server**
1. User creates `tools.py` with basic tool functions (get_weather, create_issue, get_issue)
2. Tools have NO or POOR docstrings initially
3. User configures Mintlify MCP server connection for docs search
4. User updates Tyler config to reference tools and MCP server
5. User starts playground server (`uv run playground_server.py`)
6. User connects Weave Playground to the agent via ngrok
7. User tests in Weave Playground - agent responds but doesn't use tools well (if at all)
8. User checks Weave dashboard - sees traces from Playground
9. **Insight**: Infrastructure is in place (tools + MCP), but agent doesn't know how to use them properly yet

**Step 3: Iterate to Make it Vibe as Support Agent**

*Part A: Identify the Problem*
1. User tries support bot prompts in Playground:
   - "How do I use Weave to log predictions?" (should search docs via MCP)
   - "What's the weather in SF?" (should use local tool)
   - "Create a support ticket for API timeouts" (should use local tool)
2. Agent responds but doesn't use tools correctly - doesn't feel like a support bot
3. User opens Weave dashboard and examines traces
4. User notices: Few or no tool calls, or wrong tool selection
5. User examines Tyler's purpose statement and tool descriptions in traces
6. User realizes: The agent doesn't know it's a support bot, and doesn't know when to use each tool
7. **Insight**: Weave traces reveal the gap - purpose is unclear, tool descriptions are missing

*Part B: Iterate on Purpose & Tool Descriptions*
1. User updates Tyler's purpose in config: "You are a support bot for Weave. Help users with questions about Weave and manage support tickets."
2. User improves tool docstrings in `tools.py`:
   - `get_weather`: "Get current weather for a city. Use when user asks about weather."
   - `create_issue`: "Create a support ticket. Use when user reports a problem or requests help."
3. User improves MCP tool description: "Search Weave documentation when users ask how-to questions about Weave features."
4. User restarts agent with improvements
5. **Insight**: Purpose and tool descriptions guide the agent's behavior

*Part C: Verify with Weave*
1. User tests same prompts in Playground
2. "How do I use Weave to log predictions?" → Agent NOW searches MCP docs and gives accurate answer ✅
3. "Create a support ticket for API timeouts" → Agent NOW calls create_issue ✅
4. Agent feels like a support bot now - knows its role, uses tools appropriately
5. User opens Weave traces and sees tool calls with proper context
6. User compares old trace (bad) to new trace (good) - clear improvement
7. User may iterate further based on trace insights if agent still doesn't vibe perfectly
8. **Insight**: Weave enabled the full cycle: observe → diagnose → fix → verify. This is the core development workflow!

**Step 4+: Continue** (existing steps, renumbered)
- Create datasets to systematically test support bot scenarios
- Continue iterating based on trace insights
- Measure improvements over time

### Edge Case

**Agent still doesn't vibe perfectly after first iteration**: User uses Weave traces AGAIN to understand why, continues iterating on purpose and descriptions. This demonstrates the real iterative workflow that Weave enables.

## Project Structure

```
.
├── examples/                          # Completed files for skip-ahead
│   ├── step-2a-basic-agent/
│   │   └── tyler-chat-config.yaml    # Minimal config, no tools
│   ├── step-2b-with-tools/
│   │   ├── tyler-chat-config.yaml    # Config with tools & MCP
│   │   └── tools.py                  # Well-documented tools
│   └── step-3-complete/
│       ├── tyler-chat-config.yaml    # Support bot purpose + tools
│       └── tools.py                  # Final polished tools
├── tyler-chat-config.yaml             # Starter (minimal/empty)
├── tools.py                           # Starter (basic functions, no/poor docstrings)
├── playground_server.py               # Existing
├── main.py                            # Existing
├── README.md                          # Updated with new steps + skip-ahead callouts
└── ...
```

## UX Links

- Example files directory structure: See project structure above
- Skip-ahead callout boxes: Will be added to README at each step
- Example Weave traces: Screenshots showing before (no tool calls) and after (tool calls visible) in README
- Tool descriptions comparison: Show bad vs. good docstrings side-by-side (can reference example files)
- Debugging workflow: Step-by-step guide on using Weave to diagnose issues

## Requirements

### Must
- **Repo structure**: Create `examples/` directory with completed files for each step:
  - `examples/step-2a-basic-agent/` (minimal config, no tools)
  - `examples/step-2b-with-tools/` (config + tools.py with good docstrings + MCP)
  - `examples/step-3-complete/` (support bot purpose + well-documented tools)
- **Starter files**: Provide minimal starter files in repo root:
  - `tyler-chat-config.yaml` (minimal/empty starter)
  - `tools.py` (basic functions with NO/POOR docstrings)
- **Skip-ahead instructions**: Add callout boxes in README at each step showing how to copy example files to skip ahead
- **Step 2a**: Guide users to create basic Tyler agent with NO tools, test in CLI, see trace in Weave
- **Step 2b**: Guide users to create `tools.py` with 2-3 functions (get_weather, create_issue, get_issue) with NO or POOR docstrings
- **Step 2b**: Configure Mintlify MCP server connection for Weave docs search
- **Step 2b**: Ensure MCP tools are available but have poor/missing descriptions initially
- **Step 2b**: Include existing playground server setup instructions from README (ngrok, Weave Playground connection)
- **Step 3**: Provide example support bot prompts that highlight poor behavior (not using tools, not acting like support bot)
- **Step 3**: Show in README how to navigate Weave dashboard, find traces, and interpret purpose/tool-related data
- **Step 3**: Include before/after examples of Tyler's purpose statement and tool descriptions (poor → good)
- **Step 3**: Guide users to iterate on both Tyler's purpose AND tool descriptions based on trace insights
- **Step 3**: Show side-by-side trace comparison highlighting improvements (before vs after iteration)
- Ensure at least 2-3 local tools AND the MCP docs search work correctly after improvements
- Include specific prompts that should trigger different tools (for consistent testing)
- Renumber existing Steps 4-9 to become Steps 5-10

### Must not
- Give users a clear purpose statement initially (they should iterate to "support bot")
- Give users perfect tool descriptions initially (defeats the learning objective)
- Skip the Weave iteration workflow (this is the core value prop)
- Make it too easy (users should experience real iteration)
- Make users write tool functions from scratch (provide basic functions, they improve descriptions)
- Make MCP or playground setup overly complex (should be straightforward configuration)

## Acceptance Criteria

### Step 2a: Create Basic Agent
- Given a user creates basic Tyler agent config, when agent has NO tools and NO MCP configured, then config is minimal
- Given a user runs `uv run tyler chat`, when the agent starts, then it launches successfully
- Given a user sends "Hello", when the agent responds, then response is conversational
- Given Weave is configured, when the chat runs, then traces appear in Weave dashboard
- Given a user navigates to Weave dashboard, when they view their trace, then they see the conversation captured
- Given this success, when user proceeds, then they understand the baseline: agent works, Weave is observing

### Step 2b: Add Tools & MCP Server
- Given a user creates `tools.py` with basic functions, when functions have NO/POOR docstrings, then they're intentionally incomplete
- Given a user configures Mintlify MCP server, when setup completes, then MCP connection is established
- Given a user updates Tyler config to reference tools and MCP, when saved, then configuration includes both
- Given a user starts playground server, when running, then server is accessible
- Given a user sets up ngrok and Weave Playground connection, when connected, then Playground can communicate with agent
- Given a user tests in Weave Playground, when agent responds, then responses appear but tool usage is poor/absent
- Given a user checks Weave dashboard, when they view traces, then Playground interactions are captured
- Given this setup, when user proceeds, then infrastructure is in place but agent doesn't "vibe" as support bot yet

### Step 3: Iterate to Make it Vibe as Support Agent

**Part A: Identify the Problem**
- Given a user tries "How do I use Weave to log predictions?" in Playground, when the agent responds, then it does NOT effectively search docs via MCP
- Given a user tries "Create a support ticket for API timeouts", when the agent responds, then it does NOT call create_issue properly
- Given a user opens Weave dashboard, when they examine traces, then they can see what agent is (or isn't) doing
- Given a user looks at Tyler's purpose in trace, when they read it, then they realize it's vague/generic (not "support bot")
- Given a user looks at tool descriptions in trace, when they read them, then they realize they're missing or unclear
- Given this insight, when user understands the gap, then they proceed to improve purpose and descriptions

**Part B: Iterate on Purpose & Tool Descriptions**
- Given a user updates Tyler's purpose, when they make it "support bot for Weave", then purpose is clear
- Given a user improves tool docstrings in `tools.py`, when they add descriptions of what each tool does and when to use it, then tools are well-documented
- Given a user improves MCP tool description, when they clarify it's for Weave docs search, then MCP tool purpose is clear
- Given example improvements in README, when user refers to them, then they understand good vs. bad descriptions
- Given a user restarts agent with improvements, when agent launches, then all improvements are active

**Part C: Verify with Weave**
- Given a user tests "How do I use Weave to log predictions?" again, when the agent responds, then it NOW searches MCP docs and provides accurate answer
- Given a user tests "Create a support ticket", when the agent responds, then it NOW calls create_issue appropriately
- Given agent behavior, when user interacts, then agent "vibes" as a support bot (knows its role, uses tools)
- Given a user opens Weave traces, when they examine new traces, then they see proper tool calls with context
- Given side-by-side comparison, when user compares old trace to new trace, then improvement is obvious
- Given this experience, when user reflects, then they understand how Weave enabled the full cycle: observe → diagnose → fix → verify

### Skip-Ahead Functionality
- Given a user wants to skip to Step 2b, when they run `cp examples/step-2b-with-tools/* .`, then working files are copied
- Given copied files, when user runs agent, then it works with tools and MCP configured
- Given a user wants to skip to evaluations (Step 4+), when they use `examples/step-3-complete/`, then they have a working support bot to evaluate
- Given README callout boxes, when user reads them, then skip-ahead options are clear at each step

### Negative Cases
- Given agent still doesn't vibe perfectly after first iteration, when user checks traces again, then user uses Weave to iterate FURTHER (demonstrates real workflow)
- Given a tool (local or MCP) fails during execution, when an error occurs, then the error is visible in Weave traces for debugging
- Given MCP connection issues, when they occur, then they're visible in Weave traces
- Given user gets stuck, when they reference example files, then they can compare and unstick themselves

## Non-Goals

### Out of Scope for This PR
- Teaching users how to write Python functions from scratch (provide the functions)
- Building custom MCP servers (use existing Mintlify MCP server)
- Explaining MCP protocol internals (focus on using MCP tools, not building them)
- Explaining Tyler's internal tool calling mechanism (focus on Weave debugging)
- Building agents from scratch (Tyler handles this - focus on Weave workflow)
- Complex tool examples beyond 2-3 simple local tools + MCP docs search (keep it focused)
- Teaching system prompt engineering or advanced agent design
- Deep dive into Weave features beyond traces (save for later steps)
- Adding RAG beyond MCP docs search
- Creating a UI (CLI only)  
- Fine-tuning or customizing models
- Changing the content of Steps 5-10 (just renumber them)

