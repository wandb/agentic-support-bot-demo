# Spec (per PR)

**Feature name**: Tyler Agent Foundation  
**One-line summary**: Create a basic Tyler agent with stubbed issue management tools and Weave observability

---

## Problem
The agentic support bot demo currently has no agent implementation. We need a foundational agent setup with basic tooling and observability to serve as the starting point for building out support bot capabilities.

## Goal
A working Tyler agent script that can be executed, has placeholder tooling for issue management, and is instrumented with Weights & Biases Weave for observability.

## Success Criteria
- [ ] Script runs successfully and initializes a Tyler agent
- [ ] Agent has access to two custom tools: `create_issue` and `get_issue`
- [ ] Weave is initialized and tracking is enabled for the agent
- [ ] Project name in Weave matches the repository name

## User Story
As a developer working on the support bot, I want a basic Tyler agent with stub tools and observability, so that I can iterate on agent behavior and tool implementations without starting from scratch.

## Flow / States
**Happy Path**:
1. Run the script
2. Weave initializes with project "agentic-support-bot-demo"
3. Tyler agent initializes with custom tools registered
4. Agent can receive a prompt and attempt to use the stubbed tools
5. Weave captures the agent interaction

**Edge Case**:
- If Weave API key is missing, script should fail gracefully with a clear error message

## UX Links
- N/A (script/CLI only)

## Requirements
- Must use Tyler agent framework with gpt-4.1 model
- Must use Weave StringPrompt for agent purpose
- Must register two custom tools: `create_issue` and `get_issue`
- Must initialize Weave with project name "agentic-support-bot-demo"
- Must stub out tool implementations (no actual issue system integration yet)
- Tools should return placeholder responses that demonstrate structure
- Must use streaming execution for real-time feedback
- Tools must be separated into dedicated tools.py file
- Only WANDB_API_KEY required (LLM provider keys optional)

## Acceptance Criteria
- Given the script is executed, when the agent initializes, then Weave tracking is enabled with the correct project name
- Given the agent receives a prompt about creating an issue, when it attempts to use `create_issue`, then the stub returns a mock issue ID
- Given the agent receives a prompt about retrieving an issue, when it attempts to use `get_issue`, then the stub returns mock issue data
- Given Weave credentials are missing, when the script runs, then it fails with a clear error message before attempting agent operations
- Given the agent executes, when tool calls are made, then real-time streaming feedback is displayed
- Given tests are run, when executed in CI, then no real API calls are made

## Non-Goals
- Actual issue system integration (GitHub, Jira, etc.)
- Complex agent workflows or multi-step reasoning
- User interface or web service
- Authentication/authorization for the agent
- Production-ready error handling
- Multiple LLM provider support (focused on OpenAI for MVP)

