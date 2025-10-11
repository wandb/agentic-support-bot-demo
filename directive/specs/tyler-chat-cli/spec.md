# Spec (per PR)

**Feature name**: Tyler Chat CLI Integration  
**One-line summary**: Replace programmatic agent execution with `tyler chat` CLI for interactive support bot sessions

---

## Problem
The current implementation requires running a Python script (`main.py`) with hardcoded prompts and streaming logic. This creates friction for developers who want to interactively test and use the support bot. The Slide Framework provides `tyler chat`, a built-in CLI that offers an interactive chat interface, but we're not leveraging it.

## Goal
A configuration-based approach where developers can launch an interactive support bot session using `tyler chat --config <config-file>`, with the agent's behavior, tools, and purpose defined in a YAML configuration file.

## Success Criteria
- [ ] Support bot can be launched with a single command: `tyler chat --config support-bot.yaml`
- [ ] Configuration file defines agent name, model, purpose, and tools
- [ ] Interactive chat session maintains conversation context across multiple messages
- [ ] All tool calls (create_issue, get_issue) work correctly in the CLI
- [ ] Weave observability is configured and tracking agent interactions

## User Story
As a developer working on the support bot, I want to launch an interactive chat session with a simple CLI command, so that I can test the agent's behavior and tools without writing or modifying Python scripts.

## Flow / States
**Happy Path**:
1. Developer runs `uv run tyler chat --config support-bot.yaml`
2. CLI starts and displays welcome message
3. Developer types questions about creating or retrieving issues
4. Agent responds and uses tools as needed
5. Developer continues conversation with context maintained
6. Developer types `exit` or `quit` to end session

**Edge Cases**:
- If config file is missing, CLI shows clear error message
- If required environment variables (WANDB_API_KEY) are missing, fail gracefully with instructions
- If tools fail during execution, agent handles errors and reports to user

## UX Links
- CLI Reference: https://slide.mintlify.app/apps/tyler-cli
- Configuration docs: https://slide.mintlify.app/apps/tyler-cli#configuration

## Requirements
- Must create a YAML configuration file (e.g., `support-bot.yaml`) that defines:
  - Agent name: "support-bot"
  - Model: "gpt-4.1"
  - Purpose/instructions for the agent
  - Tools: reference to custom tools from tools.py
- Must maintain the existing custom tools (create_issue, get_issue) from tools.py
- Must initialize Weave with project name "agentic-support-bot-demo"
- Must document how to run the CLI in README
- Must remove or deprecate the programmatic main.py approach
- CLI must support multi-turn conversations with context
- Must validate environment variables before starting agent

## Acceptance Criteria
- Given a developer has set WANDB_API_KEY, when they run `uv run tyler chat --config support-bot.yaml`, then an interactive chat session starts successfully
- Given the chat session is active, when the developer asks to "create an issue for API timeout", then the agent uses the create_issue tool and returns a mock issue ID
- Given the chat session is active, when the developer asks to "get details for issue #123", then the agent uses the get_issue tool and returns mock issue data
- Given the chat session has prior context, when the developer asks a follow-up question, then the agent maintains conversation history
- Given required environment variables are missing, when the developer runs the CLI, then a clear error message explains what's missing
- Given tests are run, when the CI executes, then tests validate configuration file structure (not interactive sessions)

## Non-Goals
- Creating a web interface or API server for the bot
- Implementing real issue system integrations (GitHub, Jira, etc.)
- Building a custom REPL or chat interface (using tyler chat's built-in UI)
- Multi-agent orchestration or delegation
- Persistent conversation storage across sessions (tyler chat handles in-session context only)
- Custom styling or branding of the CLI interface

