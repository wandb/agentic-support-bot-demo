# Spec (per PR)

**Feature name**: Tyler Playground API Endpoint  
**One-line summary**: Expose the Tyler agent through an OpenAI-compatible API endpoint to enable testing and experimentation in Weave Playground.  

---

## Problem
Currently, users can only interact with the Tyler agent through the CLI (`tyler chat`). To complete Step 3 of the onboarding experience ("Vibe Check - Experiment in the Playground"), users need a way to test the agent through the Weave Playground UI. This requires exposing the Tyler agent via an OpenAI-compatible HTTP API endpoint.

Without this capability:
- Users cannot test the agent in Weave Playground
- The UI-based workflow in Step 3 of the README is blocked
- Users miss out on the visual debugging and experimentation features that Playground provides
- Non-technical users have no way to interact with the agent

## Goal
Create a FastAPI server that exposes the Tyler support bot agent through an OpenAI-compatible `/v1/chat/completions` endpoint, enabling users to interact with the agent through Weave Playground.

## Success Criteria
- [ ] Users can run a local API server that exposes the Tyler agent
- [ ] The API endpoint is OpenAI-compatible and works with Weave Playground
- [ ] The agent maintains all existing capabilities (tool usage, conversation context)
- [ ] Streaming responses work correctly
- [ ] All agent interactions are logged to Weave for observability
- [ ] Setup takes less than 5 minutes with clear instructions

## User Story
As a developer testing the Tyler support bot, I want to interact with the agent through Weave Playground, so that I can visually experiment with prompts, see token usage, and test different configurations without writing code.

## Flow / States

### Happy Path
1. User runs the API server locally: `uv run playground_server.py`
2. Server starts on `http://localhost:8000`
3. User exposes the endpoint publicly via ngrok: `ngrok http 8000`
4. User configures Weave Playground with the ngrok URL as a custom model provider
5. User selects the Tyler agent from the model dropdown
6. User sends a message in Playground
7. API receives the request, invokes the Tyler agent with tools
8. Agent processes the request, potentially calling `create_issue` or `get_issue` tools
9. Response streams back to Playground
10. Interaction is logged to Weave for observability

### Edge Case: Tool Usage During Conversation
1. User asks to create a support ticket
2. Agent calls `create_issue` tool with appropriate parameters
3. Tool result is incorporated into the agent's response
4. Final response with ticket details streams back to user
5. Full trace (including tool calls) visible in Weave

## UX Links
- Weave Playground documentation: https://docs.wandb.ai/guides/weave/playground
- Example reference from user: OpenAI-compatible chat completions API format
- No UI designs needed (API endpoint only)

## Technical Approach

Tyler already supports OpenAI-compatible streaming via `stream="raw"` mode ([docs](https://slide.mintlify.app/guides/streaming-responses)), which yields raw LiteLLM chunks instead of `ExecutionEvent` objects. This feature builds a FastAPI server that exposes Tyler through an OpenAI-compatible API endpoint.

### Key Components:

**1. Tyler Agent Configuration**
- Load agent config from `tyler-chat-config.yaml` (model, purpose, etc.)
- Load custom tools from `tools.py` (create_issue, get_issue)
- Initialize with Weave for observability

**2. OpenAI-Compatible API Endpoint**
- Accept OpenAI-format requests at `/v1/chat/completions`
- Convert request messages to Tyler Thread/Message format
- Invoke agent with `stream="raw"` for streaming requests
- Serialize raw chunks to SSE format: `data: {json}\n\n`
- Handle both streaming and non-streaming responses

**3. SSE Serialization**
Raw chunks from Tyler need to be formatted as Server-Sent Events:
```python
def serialize_chunk_to_sse(chunk) -> str:
    chunk_dict = {
        "id": getattr(chunk, 'id', 'unknown'),
        "object": "chat.completion.chunk",
        "choices": [{"delta": {"content": ...}, ...}]
    }
    return f"data: {json.dumps(chunk_dict)}\n\n"
```

**4. Tool Execution**
Tyler's raw mode executes tools fully (multi-turn iteration) - the frontend sees `finish_reason: "tool_calls"` in chunks during tool execution, which is standard OpenAI behavior.

## Requirements

### Must
- Implement a `/v1/chat/completions` POST endpoint that accepts OpenAI-compatible request format
- Support streaming responses using Tyler's `stream="raw"` mode when `stream: true` in request
- Serialize raw LiteLLM chunks to SSE format (`data: {json}\n\n`)
- Support non-streaming responses (return complete JSON) when `stream: false` in request
- Integrate with the existing Tyler agent configuration from `tyler-chat-config.yaml`
- Load and execute custom tools from `tools.py` (create_issue, get_issue)
- Maintain conversation context across messages (pass full message history to Tyler Thread)
- Initialize Weave for observability on server startup
- Log all interactions to Weave with proper trace metadata
- Handle errors gracefully with appropriate HTTP status codes (400 for bad requests, 500 for server errors)
- Support CORS for browser-based Playground access
- Include health check endpoint (`/health` or `/`) that returns 200 OK

### Must not
- Require authentication for local development (optional for production)
- Modify existing `main.py` or `tools.py` functionality
- Break compatibility with existing CLI interface
- Store conversation state on the server (stateless API)
- Hard-code agent configuration (use config file)

## Acceptance Criteria

### API Functionality
- **Given** a valid OpenAI-compatible chat request, **when** the endpoint receives it, **then** it returns a properly formatted streaming or non-streaming response
- **Given** a request with tool-requiring prompt (e.g., "create a ticket"), **when** processed, **then** the agent calls the appropriate tool and includes results in response
- **Given** a multi-turn conversation, **when** messages include conversation history, **then** the agent maintains context across turns

### Integration
- **Given** the server is running, **when** configured in Weave Playground as a custom provider, **then** users can send messages and receive responses
- **Given** any agent interaction, **when** it completes, **then** a trace appears in the Weave project dashboard
- **Given** the existing `tyler-chat-config.yaml`, **when** the server starts, **then** it loads the agent configuration correctly

### Error Handling
- **Given** an invalid request format, **when** the endpoint receives it, **then** it returns a 400 error with helpful message
- **Given** the agent encounters an error, **when** processing a request, **then** it returns a 500 error without crashing the server
- **Given** a missing API key, **when** the server starts, **then** it logs a clear error message

### Performance
- **Given** a simple request, **when** processed, **then** the first response chunk arrives within 2 seconds
- **Given** streaming is enabled, **when** the agent responds, **then** tokens stream progressively (not all at once)

### Negative Cases
- **Given** an empty messages array, **when** the endpoint receives it, **then** it returns a 400 error
- **Given** ngrok is not running, **when** Playground tries to connect, **then** user sees a clear connection error (not an API issue)
- **Given** required environment variables are missing, **when** server starts, **then** it fails fast with clear error message

## Non-Goals
- Production-ready authentication/authorization (use Weave Playground's built-in secrets for API keys if needed)
- Horizontal scaling or load balancing (single-instance local development focus)
- Persistent conversation storage (Playground manages conversation history)
- Custom Playground UI components (use standard Weave Playground interface)
- Support for non-OpenAI API formats (Weave Playground expects OpenAI format)
- Rate limiting or usage quotas (local development tool)
- Deployment documentation for production environments (focus on local ngrok setup)
- WebSocket or SSE alternatives to HTTP streaming (stick with OpenAI standard)
