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

Users experience the iterative debugging workflow that Weave enables:
1. **Step 2: Get a Basic Agent Running** - Tyler agent with tools (local Python functions + MCP server for docs) that have poor/missing descriptions
2. **Step 3: Vibe Check** - Agent doesn't use tools properly (or at all)
3. **NEW Step 4: Debug & Iterate with Weave** - Use traces to understand why, improve tool descriptions (including MCP tools), see improvements
4. **Step 5+: Continue with datasets/evaluation** (existing steps, renumbered)

By the end, users understand how to **use Weave to debug and iterate on agent behavior** and **integrate external data sources via MCP**, which demonstrates core Weave value prop.

## Success Criteria

- [ ] Users complete the iteration step within the 30-minute demo timeframe
- [ ] Users successfully configure MCP server connection for documentation search
- [ ] Users use Weave traces to identify why tools (both local and MCP) aren't being called
- [ ] Users iterate on tool descriptions based on trace insights
- [ ] Users observe improved agent behavior in subsequent traces
- [ ] Users see agent successfully search docs via MCP and use local tools
- [ ] Users can articulate how Weave enabled them to debug and improve the agent (qualitative feedback)
- [ ] Tutorial demonstrates the core Weave debugging/iteration workflow with multiple tool types

## User Story

As a **developer evaluating Weave**, I want **to use traces to debug why my agent isn't calling tools (including external MCP services) and iterate on improvements**, so that **I understand how Weave helps me improve agent behavior through observability across different tool types**.

## Flow / States

### Happy Path

**Step 2: Get a Basic Agent Running** (updated - tools with poor descriptions)
1. User configures Mintlify MCP server connection for docs search
2. User runs Tyler agent with tools configured (local tools + MCP tools)
3. Tools file has basic functions but missing/poor descriptions
4. MCP tools are available but also lack clear descriptions
5. User can chat naturally with the agent
6. **Insight**: Agent is up and running with multiple types of tools available (local + MCP)

**Step 3: Vibe Check** (updated - tools not being called)
1. User tries asking agent to do things that should use tools
2. "How do I use Weave to log predictions?" (should search docs via MCP)
3. "What's the weather in San Francisco?" (should use local weather tool)
4. "Create a support ticket for my API timeout issue" (should use local create_issue tool)
5. Agent responds conversationally but DOESN'T call tools (or calls them incorrectly)
6. User is confused - why aren't ANY of the tools being used?
7. **Insight**: Something's wrong - the agent has both local and MCP tools but isn't using them

**NEW Step 4: Debug & Iterate with Weave**

*Step 4a: Investigate with Weave Traces*
1. User opens Weave dashboard and finds recent traces
2. User examines traces to see what the agent is doing
3. User notices: no tool calls in the trace (or wrong tool selection)
4. User looks at the tools that were available to the agent (both local and MCP)
5. User realizes: tool descriptions are missing/unclear for BOTH types
6. **Insight**: Weave traces reveal WHY the agent isn't behaving correctly - the agent doesn't understand when to use any of the tools (local or MCP)

*Step 4b: Improve Tool Descriptions*
1. User opens `tools.py` (local tools)
2. User adds/improves docstrings for local tools: "Use this tool to get current weather for any city"
3. User reviews Tyler MCP configuration
4. User improves MCP tool descriptions/prompts: "Use this tool to search Weave documentation when users ask how-to questions"
5. User restarts agent with improved descriptions for both tool types
6. **Insight**: Tool descriptions (whether local functions or MCP services) are how you teach the agent when to use each tool

*Step 4c: Verify Improvements*
1. User asks same questions from Step 3
2. "How do I use Weave to log predictions?" → Agent now calls MCP docs search and provides accurate answer
3. "What's the weather in SF?" → Agent calls local `get_weather()` and provides real data
4. "Create a support ticket" → Agent calls local `create_issue()` and creates a ticket
5. User opens Weave traces and sees tool calls (both MCP and local) with inputs/outputs
6. User compares new trace to old trace - clear improvement across all tool types
7. **Insight**: Weave enables the iterate/debug/verify workflow across different tool types - this is how you improve agents!

**Step 5+: Continue** (existing steps, renumbered)
- Create datasets to systematically test tool calling
- Continue iterating based on trace insights
- Measure improvements over time

### Edge Case

**User's improved descriptions still don't work perfectly**: User uses Weave traces again to understand why, continues iterating. This demonstrates the real iterative workflow.

## UX Links

- Example Weave traces: Screenshots showing before (no tool calls) and after (tool calls visible) in README
- Tool descriptions comparison: Show bad vs. good docstrings side-by-side
- Debugging workflow: Step-by-step guide on using Weave to diagnose issues

## Requirements

### Must
- Configure Mintlify MCP server connection for Weave docs search in Step 2
- Ensure MCP tools are available but have poor/missing descriptions initially
- Create `tools.py` with 2-3 local functions (get_weather, create_issue, get_issue) that have NO or POOR docstrings initially
- Configure Tyler agent to use both poorly-described local tools and MCP tools in Step 2
- Ensure Step 3 (Vibe Check) prompts users to try actions requiring both local and MCP tools, observing failures
- Add clear documentation in Step 4a on how to use Weave traces to debug both tool types
- Show in README how to navigate Weave dashboard, find traces, and interpret tool-related data (including MCP tool calls)
- Include before/after examples of tool descriptions for both local and MCP tools (poor → good)
- Guide users to improve both local tool docstrings and MCP tool descriptions based on trace insights
- Show side-by-side trace comparison highlighting both tool types (before improvement vs after improvement)
- Ensure at least 2-3 local tools AND the MCP docs search work correctly after description improvements
- Update README with clear debugging workflow using Weave for multiple tool types
- Include specific prompts that should trigger each tool type (for consistent testing)
- Renumber existing Steps 4-9 to become Steps 5-10

### Must not
- Give users perfect tool descriptions initially (defeats the learning objective)
- Skip the Weave debugging step (this is the core value prop)
- Make it too easy (users should experience real debugging)
- Require users to write tool functions from scratch (provide the functions, bad descriptions)
- Make MCP setup overly complex (should be simple configuration in Step 2)

## Acceptance Criteria

### Step 2: Get a Basic Agent Running (updated)
- Given a user configures Mintlify MCP server, when setup completes, then MCP connection is established
- Given a user runs `uv run tyler chat`, when the agent starts, then it launches successfully WITH both local tools and MCP tools configured but poorly described
- Given a user chats with the agent, when they ask general questions, then the agent responds conversationally
- Given Weave is configured, when the chat runs, then traces appear in Weave dashboard

### Step 3: Vibe Check (updated)
- Given a user tries "How do I use Weave to log predictions?", when the agent responds, then it does NOT call the MCP docs search tool (poor description)
- Given a user tries "What's the weather in San Francisco?", when the agent responds, then it does NOT call the local weather tool (poor description)
- Given a user tries "Create a support ticket for API timeouts", when the agent responds, then it does NOT call local create_issue tool (poor description)
- Given a user is confused, when they wonder why ANY of the tools aren't working, then they understand there's a problem to debug
- Given README guides them, when instructed, then they proceed to investigate with Weave

### NEW Step 4a: Investigate with Weave Traces
- Given a user opens Weave dashboard, when they find their recent traces, then they can navigate successfully
- Given a user examines a trace, when they look for tool calls, then they see NONE (or incorrect ones) for both local and MCP tools
- Given a user views the tools available to the agent in the trace, when they see the descriptions (both local and MCP), then they realize they're missing or unclear
- Given this insight, when the user understands the issue, then they proceed to fix tool descriptions for both types

### NEW Step 4b: Improve Tool Descriptions  
- Given a user opens `tools.py`, when they add/improve docstrings for local tools, then they make it clear what each tool does and when to use it
- Given a user reviews MCP configuration, when they improve MCP tool descriptions, then they clarify when to use docs search
- Given improved descriptions for both tool types, when user restarts agent, then all tools are now properly described to the LLM
- Given example good descriptions in README, when user refers to them, then they understand what makes a good tool description for both local and MCP tools

### NEW Step 4c: Verify Improvements
- Given a user asks "How do I use Weave to log predictions?" again, when the agent responds, then it NOW calls the MCP docs search and provides accurate documentation-based answer
- Given a user asks "What's the weather in San Francisco?" again, when the agent responds, then it NOW calls `get_weather()` tool and provides real data
- Given a user asks to create an issue again, when the agent responds, then it NOW successfully calls `create_issue()` tool
- Given a user opens Weave traces, when they examine the new trace, then they see tool calls (both MCP and local) with inputs and outputs
- Given side-by-side comparison, when user compares old trace to new trace, then the improvement is obvious across all tool types
- Given this experience, when user reflects, then they understand how Weave enables debugging and iteration across different tool types

### Negative Cases
- Given improved descriptions still aren't perfect, when agent still doesn't call tools correctly, then user uses Weave traces AGAIN to iterate further (demonstrates real workflow)
- Given a tool (local or MCP) fails during execution, when an error occurs, then the error is visible in Weave traces for debugging
- Given MCP connection issues, when they occur, then they're visible in Weave traces

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

