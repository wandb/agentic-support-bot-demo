# Technical Design Review (TDR) — Tyler Playground API Endpoint

**Author**: AI Agent  
**Date**: 2025-10-14  
**Links**: 
- Spec: `/directive/specs/tyler-playground-api/spec.md`
- Impact: `/directive/specs/tyler-playground-api/impact.md`
- Tyler Raw Streaming Docs: https://slide.mintlify.app/guides/streaming-responses
- Weave Playground: https://docs.wandb.ai/guides/weave/playground

---

## 1. Summary

We are building a FastAPI server that exposes the Tyler support bot agent through an OpenAI-compatible HTTP API endpoint. This enables developers to interact with the agent through Weave Playground's visual interface rather than only via CLI, completing the "UI Approach" for Step 3 (Vibe Check) in the onboarding README.

The server will accept standard OpenAI `/v1/chat/completions` requests, leverage Tyler's new `stream="raw"` mode to get LiteLLM chunks directly, serialize them to Server-Sent Events format, and stream responses back to Weave Playground. All interactions will be logged to Weave for observability. The server will be exposed publicly via ngrok for local testing, allowing developers to configure it as a custom model provider in Weave Playground.

## 2. Decision Drivers & Non‑Goals

### Drivers:
- **Complete onboarding flow**: Enable Step 3 UI approach that's currently blocked
- **Visual experimentation**: Allow developers to test agents in Playground without writing code
- **Leverage Tyler's raw streaming**: Use Tyler's new `stream="raw"` capability (already implemented)
- **OpenAI compatibility**: Follow standard format for easy integration with Weave Playground
- **Observability**: Maintain full Weave tracing for all interactions

### Non‑Goals:
- Production-grade authentication/authorization (local development focus)
- Persistent conversation storage (Playground manages state)
- Horizontal scaling or load balancing (single-instance local server)
- Custom Playground UI components (use standard Playground interface)
- WebSocket or alternative streaming protocols (stick with SSE/OpenAI format)
- Deployment to cloud infrastructure (ngrok for local testing only)

## 3. Current State — Codebase Map (concise)

### Key modules/services:
- **`main.py`** (159 lines): Programmatic agent execution with Tyler Agent, demonstrates streaming with ExecutionEvent handling
- **`tools.py`** (75 lines): Custom tools (`create_issue`, `get_issue`) with mock implementations, exports `TOOLS` list
- **`tyler-chat-config.yaml`** (25 lines): Agent configuration for tyler chat CLI (name, purpose, model, tools)
- **`tests/test_main.py`**: Test suite for agent setup and tool functionality

### Existing data models:
- **Tyler Thread/Message**: Conversation management (no persistence currently)
- **Tool response format**: Mock dictionaries with issue data (id, title, description, status, priority, timestamps)

### External contracts:
- **Tyler Agent API**: `agent.go(thread, stream="raw")` yields LiteLLM chunks
- **Weave API**: `weave.init()` for observability, automatic tracing
- **OpenAI API**: LLM provider (configurable via model_name in config)
- **Environment variables**: `WANDB_API_KEY` (required), `OPENAI_API_KEY` (or other provider keys)

### Observability:
- Weave instrumentation active when `weave.init()` is called
- Tyler Agent automatically creates traces for all interactions
- Traces include: messages, tool calls, token usage, latency

## 4. Proposed Design (high level, implementation‑agnostic)

### Overall Approach:

**OpenAI-Compatible Gateway**: A thin FastAPI server that translates between OpenAI API format and Tyler Agent's Python API.

```
Client (Weave Playground)
  ↓ HTTP POST /v1/chat/completions
  ↓ OpenAI format: {"model": "...", "messages": [...], "stream": true}
FastAPI Server (playground_server.py)
  ↓ Convert to Tyler Thread/Message
  ↓ Load config from tyler-chat-config.yaml
  ↓ Load tools from tools.py
Tyler Agent
  ↓ agent.go(thread, stream="raw")
  ↓ LiteLLM chunks (raw OpenAI format)
FastAPI Server
  ↓ Serialize to SSE: data: {json}\n\n
  ↓ StreamingResponse
Client (Weave Playground)
  ↓ Display streaming response
Weave
  ↓ Trace stored automatically
```

### Component Responsibilities:

| Component | Responsibility |
|-----------|----------------|
| **FastAPI Server** | HTTP routing, request validation, SSE serialization, error handling |
| **Request Converter** | OpenAI messages → Tyler Thread/Message objects |
| **Config Loader** | Read tyler-chat-config.yaml, instantiate Tyler Agent |
| **Tool Loader** | Import tools.py dynamically, attach to agent |
| **SSE Serializer** | LiteLLM chunks → Server-Sent Events format |
| **Tyler Agent** | Execute agent logic, call tools, stream raw LiteLLM chunks |
| **Weave** | Capture traces automatically (no manual instrumentation) |

### Interfaces & Data Contracts:

**HTTP API Contract** (`POST /v1/chat/completions`):

Request body (Pydantic model):
```python
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: Optional[str] = None  # For tool messages

class ChatCompletionRequest(BaseModel):
    model: str  # Required by OpenAI spec (not used by our server)
    messages: List[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
```

Response (streaming - SSE format):
```
data: {"id": "chatcmpl-abc123", "object": "chat.completion.chunk", "created": 1697000000, "model": "gpt-4o", "choices": [{"index": 0, "delta": {"content": "Hello"}, "finish_reason": null}]}

data: {"id": "chatcmpl-abc123", "object": "chat.completion.chunk", "created": 1697000000, "model": "gpt-4o", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}

data: [DONE]
```

Response (non-streaming - JSON):
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1697000000,
  "model": "gpt-4o",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "Full response text"},
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}
```

**Health Check** (`GET /health`):
```json
{"status": "ok", "agent_name": "Buzz", "model": "gpt-4o"}
```

### SSE Serialization Logic:

Tyler's `stream="raw"` yields LiteLLM chunk objects. We need to serialize them:

```python
def serialize_chunk_to_sse(chunk) -> str:
    """
    Convert LiteLLM chunk to Server-Sent Events format.
    
    LiteLLM chunks have attributes like:
    - chunk.id
    - chunk.object
    - chunk.created
    - chunk.model
    - chunk.choices[0].delta.content
    - chunk.choices[0].finish_reason
    - chunk.usage (in final chunk)
    """
    chunk_dict = {
        "id": getattr(chunk, 'id', 'chatcmpl-unknown'),
        "object": getattr(chunk, 'object', 'chat.completion.chunk'),
        "created": getattr(chunk, 'created', int(time.time())),
        "model": getattr(chunk, 'model', 'unknown'),
        "choices": []
    }
    
    if hasattr(chunk, 'choices') and chunk.choices:
        for choice in chunk.choices:
            choice_dict = {
                "index": getattr(choice, 'index', 0),
                "delta": {},
                "finish_reason": getattr(choice, 'finish_reason', None)
            }
            
            # Extract delta content
            if hasattr(choice, 'delta'):
                delta = choice.delta
                if isinstance(delta, dict):
                    choice_dict["delta"] = delta
                else:
                    # Delta is an object
                    if hasattr(delta, 'content') and delta.content:
                        choice_dict["delta"]["content"] = delta.content
                    if hasattr(delta, 'role') and delta.role:
                        choice_dict["delta"]["role"] = delta.role
            
            chunk_dict["choices"].append(choice_dict)
    
    # Include usage in final chunk if present
    if hasattr(chunk, 'usage') and chunk.usage:
        chunk_dict["usage"] = {
            "prompt_tokens": getattr(chunk.usage, 'prompt_tokens', 0),
            "completion_tokens": getattr(chunk.usage, 'completion_tokens', 0),
            "total_tokens": getattr(chunk.usage, 'total_tokens', 0)
        }
    
    return f"data: {json.dumps(chunk_dict)}\n\n"
```

### Agent Initialization:

Load agent from configuration file at server startup:

```python
import yaml
from tyler import Agent, Thread, Message
import importlib.util
import weave

# Load config
with open("tyler-chat-config.yaml") as f:
    config = yaml.safe_load(f)

# Initialize Weave
weave.init("agentic-support-bot-demo")

# Load tools dynamically
tool_path = config["tools"][0]  # "./tools.py"
spec = importlib.util.spec_from_file_location("custom_tools", tool_path)
tools_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools_module)
tools = tools_module.TOOLS  # List of tool functions

# Create agent
agent = Agent(
    name=config["name"],
    model_name=config["model_name"],
    purpose=config["purpose"],
    tools=tools,
    temperature=config.get("temperature", 0.7),
    max_tool_iterations=config.get("max_tool_iterations", 10)
)
```

### Streaming Endpoint:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    # Convert request to Tyler thread
    thread = Thread()
    for msg in request.messages:
        thread.add_message(Message(role=msg.role, content=msg.content))
    
    if request.stream:
        # Streaming response
        async def generate():
            async for chunk in agent.go(thread, stream="raw"):
                yield serialize_chunk_to_sse(chunk)
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
    else:
        # Non-streaming response
        result = await agent.go(thread, stream=False)
        # Extract final message and format as OpenAI response
        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": config["model_name"],
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result.messages[-1].content
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 0,  # Not available in non-streaming
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
```

### Error Handling:

**Configuration Errors** (startup):
- Missing tyler-chat-config.yaml → 500 error, log "Config file not found"
- Invalid YAML syntax → 500 error, log parsing error
- Missing required fields → 500 error, log which field is missing
- Tool loading failure → 500 error, log import error

**Request Errors** (runtime):
- Empty messages array → 400 error: "messages array cannot be empty"
- Invalid message format → 422 error (Pydantic validation)
- Missing required fields → 422 error (Pydantic validation)

**Agent Errors** (runtime):
- Tool execution failure → Agent acknowledges in response (Tyler handles this)
- LLM API error → 500 error, log error details
- Timeout → 504 error after 60 seconds

**Graceful Degradation**:
- If Weave init fails → Log warning, continue (observability degraded but functional)
- If tool fails → Agent communicates failure to user in conversation

### Performance Expectations:

- **Latency**: First token within 1-2 seconds (LLM dependent)
- **Throughput**: Single server handles 5-10 concurrent requests (async FastAPI)
- **Streaming**: Chunks sent as received from LiteLLM (no buffering)
- **Memory**: Minimal (stateless server, no conversation storage)

### CORS Configuration:

Enable CORS for browser-based Playground access:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 5. Alternatives Considered

### Option A: Convert Tyler ExecutionEvent to OpenAI format in server

**Approach**: Use Tyler's default `stream=True` (ExecutionEvent), manually convert to OpenAI chunks

**Pros**:
- Access to rich ExecutionEvent data (TOOL_SELECTED, TOOL_RESULT)
- Could surface tool usage in custom way

**Cons**:
- Complex conversion logic (mapping ExecutionEvent types to OpenAI chunks)
- Potential for bugs and format mismatches
- More code to maintain
- Reinventing what Tyler's `stream="raw"` already does

**Decision**: Not chosen; Tyler's `stream="raw"` is the right abstraction

### Option B: Enhance Tyler to add OpenAI-compatible mode

**Approach**: Add parameter to Tyler like `format="openai"` to return OpenAI format

**Pros**:
- Clean separation of concerns
- Other Tyler users could benefit

**Cons**:
- Already done! Tyler has `stream="raw"` mode
- Would be redundant

**Decision**: Not needed; Tyler already has this capability

### Option C: Use WebSocket instead of SSE

**Approach**: Implement WebSocket endpoint for bidirectional streaming

**Pros**:
- More efficient for bidirectional communication
- Better connection management

**Cons**:
- Weave Playground expects OpenAI format (SSE)
- More complex implementation
- Not compatible with standard OpenAI API

**Decision**: Not chosen; SSE is OpenAI standard and what Playground expects

### Option D: Create proxy that wraps existing Tyler CLI

**Approach**: Run `tyler chat` as subprocess, capture output, expose via HTTP

**Pros**:
- Reuses existing CLI implementation

**Cons**:
- Complex subprocess management
- Hard to capture structured output from interactive CLI
- Poor error handling
- Performance overhead

**Decision**: Not chosen; direct API usage is cleaner

### Chosen Approach: FastAPI + Tyler Raw Streaming

**Why**:
- Leverages Tyler's existing `stream="raw"` capability (already implemented)
- Clean, straightforward implementation (thin translation layer)
- OpenAI-compatible by design
- FastAPI provides async support out of the box
- Easy to test and maintain

## 6. Data Model & Contract Changes

### No Data Model Changes:
- No persistent storage (stateless API)
- No database migrations needed
- Tool response formats unchanged

### New HTTP API Contract:
As documented in Section 4 (Interfaces & Data Contracts)

Key points:
- Follows OpenAI `/v1/chat/completions` specification
- Supports both streaming (SSE) and non-streaming (JSON) modes
- Compatible with Weave Playground's custom model provider feature

### Configuration File Usage:
- Server reads `tyler-chat-config.yaml` at startup (existing file, no changes)
- No new configuration format needed

### Tool Loading Mechanism:
- Server dynamically imports `tools.py` using Python's `importlib`
- Expects `TOOLS` list export (already present in tools.py)
- No changes to tool format or signatures

### Environment Variables:
- **Existing**: `WANDB_API_KEY`, `OPENAI_API_KEY` (unchanged)
- **New (optional)**: 
  - `PLAYGROUND_SERVER_PORT` (default: 8000)
  - `PLAYGROUND_SERVER_HOST` (default: 0.0.0.0)
  - `PLAYGROUND_LOG_LEVEL` (default: INFO)

### Backward Compatibility:
- No breaking changes to existing functionality
- `main.py` and tyler CLI continue to work unchanged
- New server is additive (opt-in)

## 7. Security, Privacy, Compliance

### AuthN/AuthZ Model:

**Current Approach** (MVP):
- No authentication required for local development
- Server binds to 0.0.0.0:8000 (accessible on local network)
- ngrok URL should be kept private (not committed to git)

**Future Enhancement** (optional):
- Add API key validation via `Authorization: Bearer <key>` header
- Weave Playground supports team secrets for API keys
- Can add simple middleware to check header against environment variable

```python
# Optional: Simple API key validation
async def verify_api_key(authorization: str = Header(None)):
    expected_key = os.getenv("PLAYGROUND_API_KEY")
    if expected_key and authorization != f"Bearer {expected_key}":
        raise HTTPException(status_code=401, detail="Invalid API key")
```

### Secrets Management:

- **API keys**: Stored in `.env` file (not committed to git)
- **Config files**: No secrets in YAML (reference-only)
- **Environment**: Server process has access to all env vars (standard practice)

**Best Practices**:
- Add `.env` to `.gitignore` (already done)
- Document in README not to share ngrok URLs publicly
- Keep ngrok sessions short-lived (terminate after testing)

### PII Handling:

- **No PII in current implementation**: Mock tools return synthetic data
- **Conversation data**: Not persisted server-side (Weave Playground manages state)
- **Weave traces**: May contain conversation content (follow Weave's privacy policies)

**Considerations for future**:
- If real support issues added, sanitize PII before logging
- Weave traces should not include sensitive data (API keys, passwords)

### Threat Model:

**Attack Vectors**:

1. **Unauthorized API access via ngrok**
   - **Mitigation**: Keep URL private, use optional API key validation
   - **Risk**: Medium (API credits consumed, not data breach)

2. **Malicious input in messages**
   - **Mitigation**: Tyler Agent handles LLM safety, tools are sandboxed
   - **Risk**: Low (tools have no external side effects)

3. **Tool injection via LLM prompt**
   - **Mitigation**: Tools are predefined, LLM can only call existing tools
   - **Risk**: Low (current tools are read-only/mock)

4. **Denial of service (many requests)**
   - **Mitigation**: Rate limiting (can add if needed), ngrok has connection limits
   - **Risk**: Low (local dev tool, not public service)

5. **Dependency vulnerabilities**
   - **Mitigation**: Regular dependency updates, use `uv` for lockfile
   - **Risk**: Low (standard practice)

**Not in Threat Model** (out of scope for local dev tool):
- DDoS protection
- SQL injection (no database)
- XSS/CSRF (no user-facing UI in server)
- Data exfiltration (no sensitive data)

## 8. Observability & Operations

### Logs:

**Startup Logs** (INFO level):
```
[2025-10-14 12:00:00] INFO - Loading configuration from tyler-chat-config.yaml
[2025-10-14 12:00:00] INFO - Agent initialized: Buzz (gpt-4o)
[2025-10-14 12:00:00] INFO - Loaded 2 tools: create_issue, get_issue
[2025-10-14 12:00:00] INFO - Weave initialized: project=agentic-support-bot-demo
[2025-10-14 12:00:01] INFO - Server listening on http://0.0.0.0:8000
[2025-10-14 12:00:01] INFO - Health check available at http://0.0.0.0:8000/health
```

**Request Logs** (INFO level):
```
[2025-10-14 12:05:30] INFO - POST /v1/chat/completions (stream=true, messages=3)
[2025-10-14 12:05:35] INFO - Request completed (duration=5.2s, chunks=42)
```

**Error Logs** (ERROR level):
```
[2025-10-14 12:10:00] ERROR - Failed to load config: File not found: tyler-chat-config.yaml
[2025-10-14 12:15:30] ERROR - Agent execution failed: OpenAI API error: Rate limit exceeded
```

**Logging Implementation**:
```python
import logging

logging.basicConfig(
    level=os.getenv("PLAYGROUND_LOG_LEVEL", "INFO"),
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)
```

### Metrics:

**Weave Metrics** (automatic):
- Token usage per request (prompt + completion)
- Latency per request (end-to-end)
- Tool calls (name, arguments, results, duration)
- Model performance metrics
- Cost estimates (if available)

**Server Metrics** (nice-to-have, not MVP):
- Request count by endpoint
- Response time histogram
- Error rate by status code
- Active concurrent requests

**Access Metrics**:
- Weave dashboard at https://wandb.ai/
- Filter by project: "agentic-support-bot-demo"
- View traces for each API request

### Traces:

Each API request creates a Weave trace with:
- **Inputs**: Request messages, model configuration
- **Outputs**: Assistant response
- **Metadata**: Token usage, latency, cost
- **Tool calls**: Each tool invocation with arguments and results
- **Errors**: Exceptions and error messages (if any)

Tyler Agent automatically creates traces when `weave.init()` is called at startup.

### Dashboards/Alerts:

**None required for MVP** (local development tool):
- No production deployment
- No uptime monitoring
- No alerting infrastructure

**Manual monitoring**:
- Server logs visible in terminal
- Weave dashboard for trace exploration
- Health check endpoint for liveness: `curl http://localhost:8000/health`

### Runbooks:

**Starting the server**:
```bash
# Ensure environment is set up
source .env  # or equivalent
uv run playground_server.py
```

**Exposing via ngrok**:
```bash
ngrok http 8000
# Copy the https URL
```

**Configuring Weave Playground**:
1. Go to Weave Playground
2. Add custom model provider
3. Provider name: `tyler-support-bot`
4. Base URL: `https://abc123.ngrok-free.app/v1/`
5. API key: (optional, can use dummy value or configure on server)
6. Model name: `support-bot` (can be anything, not used by our server)

**Troubleshooting**:
- "Connection refused" → Check server is running, ngrok is active
- "Config file not found" → Run from project root where tyler-chat-config.yaml exists
- "Missing API key" → Set WANDB_API_KEY and OPENAI_API_KEY in .env
- "No traces in Weave" → Check weave.init() succeeded at startup

## 9. Rollout & Migration

### Feature Flags:
- **Not applicable**: Additive feature, no conditional logic needed
- Users opt-in by running the server

### Rollout Strategy:

**Phase 1: Implementation & Unit Testing** (Day 1-2)
- Implement playground_server.py
- Add unit tests for serialization and conversion logic
- Test locally with curl

**Phase 2: Integration Testing** (Day 3)
- Test with ngrok + Weave Playground
- Verify streaming works correctly
- Check Weave traces appear

**Phase 3: Documentation** (Day 4)
- Update README Step 3 with server instructions
- Add troubleshooting section
- Create example curl commands

**Phase 4: User Validation** (Day 5)
- Share with 2-3 internal users for feedback
- Collect usability feedback
- Fix any issues found

### Migration Strategy:
- **No migration needed**: New additive feature
- Existing workflows (CLI, programmatic) unchanged
- Users can adopt at their own pace

### Revert Plan:

**Easy rollback**:
1. Delete playground_server.py
2. Remove fastapi/uvicorn from pyproject.toml
3. Revert README changes

**No data to migrate**:
- Stateless server (no database)
- No persistent state
- No user data

**Blast radius**: Minimal
- Only affects users who explicitly run the server
- No impact on existing CLI or programmatic usage
- No production systems

### Deployment:

**Not applicable for MVP**: Local development tool only

**Future considerations** (if deploying to shared environment):
- Containerize with Docker
- Add authentication (API keys)
- Configure reverse proxy (nginx)
- Set up monitoring and alerting
- Use persistent ngrok domain or proper DNS

## 10. Test Strategy & Spec Coverage (TDD)

### TDD Commitment:

For each acceptance criterion:
1. **Write failing test** that encodes expected behavior
2. **Run test** to confirm failure (proves test is meaningful)
3. **Implement minimal code** to pass the test
4. **Refactor** while keeping tests green
5. **Map to spec** acceptance criterion (traceability)

### Spec→Test Mapping:

| Acceptance Criterion | Test ID | Test Type | Description |
|---------------------|---------|-----------|-------------|
| Given valid OpenAI-compatible request, when endpoint receives it, then returns proper format | `test_chat_completions_non_streaming` | Integration | Full request/response cycle (mocked agent) |
| Given request with tool-requiring prompt, when processed, then agent calls tool | `test_tool_usage_in_request` | Integration | Verify tool execution in response |
| Given multi-turn conversation, when messages include history, then agent maintains context | `test_multi_turn_conversation` | Integration | Pass multiple messages, verify context |
| Given server running, when configured in Playground, then users can send/receive | **Manual** | Manual | End-to-end Playground testing |
| Given agent interaction, when completed, then trace appears in Weave | **Manual** | Manual | Verify Weave integration |
| Given tyler-chat-config.yaml, when server starts, then loads config correctly | `test_load_config_file` | Unit | Config parsing and validation |
| Given invalid request format, when endpoint receives it, then returns 400 error | `test_invalid_request_validation` | Integration | Pydantic validation errors |
| Given agent error, when processing, then returns 500 without crash | `test_agent_error_handling` | Integration | Mock agent exception |
| Given missing API key, when server starts, then logs clear error | `test_missing_env_vars` | Integration | Environment validation |
| Given simple request, when processed, then first chunk arrives within 2s | **Manual** | Manual | Latency testing (LLM dependent) |
| Given streaming enabled, when agent responds, then tokens stream progressively | `test_streaming_response_sse` | Integration | Verify SSE format |
| Given empty messages array, when endpoint receives it, then returns 400 | `test_empty_messages_validation` | Integration | Edge case validation |

### Test Tiers:

**Unit Tests** (`tests/test_playground_server.py`):

1. `test_serialize_chunk_to_sse()`
   - Input: Mock LiteLLM chunk object
   - Output: Properly formatted SSE string
   - Validates: JSON structure, SSE format (`data: {}\n\n`)

2. `test_load_config_file()`
   - Input: tyler-chat-config.yaml path
   - Output: Parsed config dict
   - Validates: Required fields present, types correct

3. `test_openai_to_tyler_conversion()`
   - Input: OpenAI messages array
   - Output: Tyler Thread with Message objects
   - Validates: Role mapping, content preservation

4. `test_tyler_to_openai_response()`
   - Input: Tyler AgentResult
   - Output: OpenAI completion format
   - Validates: Response structure, message extraction

**Integration Tests** (`tests/test_playground_server.py`):

1. `test_chat_completions_non_streaming()`
   - Mock Tyler agent to return fixed response
   - POST request to `/v1/chat/completions` with `stream=false`
   - Assert: Response matches OpenAI format

2. `test_chat_completions_streaming()`
   - Mock Tyler agent to yield chunks
   - POST request with `stream=true`
   - Assert: SSE format correct, [DONE] sent

3. `test_health_check_endpoint()`
   - GET request to `/health`
   - Assert: 200 status, JSON with agent info

4. `test_cors_headers_present()`
   - POST request to `/v1/chat/completions`
   - Assert: CORS headers in response

5. `test_invalid_request_validation()`
   - POST with missing required fields
   - Assert: 422 status (Pydantic validation error)

6. `test_empty_messages_array()`
   - POST with `{"messages": []}`
   - Assert: 400 status, helpful error message

7. `test_agent_error_handling()`
   - Mock agent to raise exception
   - Assert: 500 status, error logged, server doesn't crash

8. `test_tool_usage_in_request()`
   - Mock agent to call create_issue tool
   - Assert: Tool appears in response/trace

**Manual Tests**:

1. **Local server startup**
   - Run: `uv run playground_server.py`
   - Verify: Logs show successful initialization
   - Verify: Health check returns 200

2. **curl request (non-streaming)**
   ```bash
   curl -X POST http://localhost:8000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"gpt-4o","messages":[{"role":"user","content":"Hello"}],"stream":false}'
   ```
   - Verify: JSON response with assistant message

3. **curl request (streaming)**
   ```bash
   curl -X POST http://localhost:8000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"gpt-4o","messages":[{"role":"user","content":"Hello"}],"stream":true}'
   ```
   - Verify: SSE chunks stream progressively, ends with [DONE]

4. **ngrok + Weave Playground**
   - Start server locally
   - Expose via ngrok
   - Configure in Weave Playground
   - Send messages, verify responses
   - Check Weave dashboard for traces

5. **Tool usage**
   - In Playground: "Create an issue for API timeout"
   - Verify: Agent calls create_issue tool
   - Verify: Response includes issue details

6. **Multi-turn conversation**
   - In Playground: "Create issue X"
   - Then: "What was the ID?"
   - Verify: Agent remembers context

### Negative & Edge Cases:

| Test Case | Expected Behavior | Test Type |
|-----------|------------------|-----------|
| Empty messages array | 400 error: "messages cannot be empty" | Integration |
| Invalid message role | 422 error (Pydantic validation) | Integration |
| Missing required field (model) | 422 error | Integration |
| Server started without config file | 500 error at startup | Manual |
| Invalid YAML syntax in config | 500 error at startup | Manual |
| WANDB_API_KEY not set | Warning logged, server continues | Manual |
| OPENAI_API_KEY not set | First request fails with LLM error | Manual |
| Tyler agent timeout | 504 error after 60 seconds | Manual |
| Tool execution fails | Agent acknowledges failure in response | Manual |
| ngrok connection drops | Client sees connection error, server continues | Manual |
| Concurrent requests | Both complete successfully (async) | Load test |

### Performance Tests:

**Not in MVP** (nice-to-have):

1. **Load test**: 10 concurrent requests
   - Tool: `locust` or `hey`
   - Target: All complete within 30 seconds
   - Validate: No errors, Weave traces created

2. **Streaming latency test**
   - Measure: Time to first chunk
   - Target: <2 seconds
   - Note: Depends on LLM API latency

3. **Memory usage test**
   - Monitor: Server memory during 100 requests
   - Target: No memory leaks, stable usage

### CI Requirements:

**Test execution**:
```bash
# Run all tests
uv run pytest tests/ -v

# Run only playground server tests
uv run pytest tests/test_playground_server.py -v

# Run with coverage
uv run pytest tests/ --cov=playground_server --cov-report=term
```

**Coverage target**: 80%+ for playground_server.py

**CI pipeline**:
1. Install dependencies (`uv sync`)
2. Run linter (`ruff check`)
3. Run formatter check (`ruff format --check`)
4. Run type checker (`mypy playground_server.py`)
5. Run tests (`pytest`)
6. Check coverage threshold

**Mocking strategy**:
- Mock Tyler Agent responses (no real LLM calls in CI)
- Mock Weave init (no network calls)
- Use `pytest-asyncio` for async test support
- Use `httpx.AsyncClient` for FastAPI endpoint testing

## 11. Risks & Open Questions

### Risks:

| Risk | Severity | Mitigation | Status |
|------|----------|------------|--------|
| Tyler `stream="raw"` output format differs from expectations | **HIGH** | Test immediately with actual Tyler; adjust serialization if needed | **BLOCKING** |
| SSE format incompatible with Weave Playground | **MEDIUM** | Follow OpenAI spec exactly; manual test in Playground before release | **BLOCKING** |
| Weave tracing doesn't work with server | **MEDIUM** | Test weave.init() at startup; verify traces appear | **BLOCKING** |
| ngrok free tier too limited for testing | **LOW** | Document ngrok limitations; paid tier optional | Accepted |
| Config file path issues (relative vs absolute) | **LOW** | Use absolute paths or require server run from project root | Accepted |
| Concurrent requests cause race conditions | **LOW** | Tyler Agent should be thread-safe; test with concurrent requests | Testing |
| LiteLLM chunk format varies by provider | **MEDIUM** | Test with OpenAI (primary target); document limitations | Testing |
| Playwright UI doesn't display tool calls | **LOW** | Weave team can clarify expected format for function calling | Nice-to-have |

### Open Questions:

| Question | Proposed Resolution | Owner | Status |
|----------|-------------------|-------|--------|
| Does Tyler's `stream="raw"` work exactly as documented? | Test with simple agent, inspect chunks | Engineer | **BLOCKING** |
| Should we support non-streaming mode? | Yes (simpler for testing, may be useful) | Resolved | ✅ |
| How to handle tool result streaming? | Tyler handles this automatically in raw mode (finish_reason="tool_calls") | Resolved | ✅ |
| Should server validate model name against config? | No, accept any model name (OpenAI API requirement, ignored by our server) | Resolved | ✅ |
| How to handle temperature/max_tokens overrides? | Accept in request, but don't override agent config (not supported by Tyler currently) | Resolved | ✅ |
| Should we add API key authentication? | Optional, can add later if needed | Deferred | - |
| Should server support multiple agents/configs? | No (MVP: single agent only), can add via path parameter later | Deferred | - |
| How to handle conversation history limits? | No limit (Playground manages history, sends full context each time) | Resolved | ✅ |

### Decision Log:

**Decision 1**: Use Tyler's `stream="raw"` mode instead of converting ExecutionEvent
- **Rationale**: Tyler already provides OpenAI-compatible streaming
- **Alternatives**: Manual conversion from ExecutionEvent (too complex)
- **Outcome**: Simpler implementation, leverages framework capability

**Decision 2**: Support both streaming and non-streaming modes
- **Rationale**: Non-streaming easier to test, may be useful for debugging
- **Alternatives**: Streaming-only (less flexible)
- **Outcome**: Implement both, minor additional code

**Decision 3**: No authentication in MVP
- **Rationale**: Local development tool, ngrok provides some obscurity
- **Alternatives**: API key validation (can add later)
- **Outcome**: Simpler MVP, document security considerations

**Decision 4**: Load config at startup (not per-request)
- **Rationale**: Configuration doesn't change during server lifetime
- **Alternatives**: Reload config per request (unnecessary overhead)
- **Outcome**: Better performance, simpler code

**Decision 5**: Accept but ignore model name in request
- **Rationale**: OpenAI API requires it, but we use model from config
- **Alternatives**: Validate against config (breaks OpenAI compatibility)
- **Outcome**: Full OpenAI compatibility

## 12. Milestones / Plan (post‑approval)

### Task Breakdown:

#### Task 1: Validate Tyler Raw Streaming (SPIKE)
**Goal**: Confirm Tyler's `stream="raw"` works as expected and produces OpenAI-compatible chunks

**DoD**:
- [ ] Create minimal test script with Tyler agent
- [ ] Call `agent.go(thread, stream="raw")`
- [ ] Inspect chunk objects (attributes, types, structure)
- [ ] Document chunk format for serialization
- [ ] Verify tool calls work in raw mode

**Tests**: Manual validation, inspect output

**Dependencies**: None

**Owner**: Engineer

**Duration**: 2 hours

**Blocking**: YES (entire implementation depends on this)

---

#### Task 2: Implement Core Server Structure
**Goal**: Create FastAPI app with basic routing and request models

**DoD**:
- [ ] Create `playground_server.py` with FastAPI app
- [ ] Define Pydantic models (ChatMessage, ChatCompletionRequest)
- [ ] Implement `/health` endpoint
- [ ] Implement `/v1/chat/completions` route (stub)
- [ ] Add CORS middleware
- [ ] Add logging configuration

**Tests**: 
- `test_health_check_endpoint()` passes
- Manual: `curl http://localhost:8000/health`

**Dependencies**: Task 1 (understanding of chunk format)

**Commit**: `feat: add playground server with FastAPI routing`

**Owner**: Engineer

**Duration**: 2 hours

---

#### Task 3: Implement Config and Agent Initialization
**Goal**: Load tyler-chat-config.yaml and create Tyler Agent at startup

**DoD**:
- [ ] Implement config loading from tyler-chat-config.yaml
- [ ] Validate required config fields
- [ ] Dynamically import tools from tools.py
- [ ] Create Tyler Agent instance
- [ ] Initialize Weave
- [ ] Add startup logging

**Tests**:
- `test_load_config_file()` passes
- Manual: Server starts without errors

**Dependencies**: Task 2 (server structure exists)

**Commit**: `feat: add config loading and agent initialization`

**Owner**: Engineer

**Duration**: 3 hours

---

#### Task 4: Implement SSE Serialization
**Goal**: Convert LiteLLM chunks to Server-Sent Events format

**DoD**:
- [ ] Implement `serialize_chunk_to_sse()` function
- [ ] Handle different chunk types (content, finish_reason, usage)
- [ ] Handle dict vs object delta formats
- [ ] Add proper error handling

**Tests**:
- `test_serialize_chunk_to_sse()` passes (multiple chunk types)

**Dependencies**: Task 1 (chunk format documented)

**Commit**: `feat: add SSE serialization for LiteLLM chunks`

**Owner**: Engineer

**Duration**: 2 hours

---

#### Task 5: Implement Request Conversion
**Goal**: Convert OpenAI messages to Tyler Thread/Message objects

**DoD**:
- [ ] Implement conversion from request.messages to Thread
- [ ] Handle all message roles (user, assistant, system, tool)
- [ ] Preserve message content and metadata

**Tests**:
- `test_openai_to_tyler_conversion()` passes

**Dependencies**: Task 2 (request models defined)

**Commit**: `feat: add OpenAI to Tyler message conversion`

**Owner**: Engineer

**Duration**: 1 hour

---

#### Task 6: Implement Streaming Endpoint
**Goal**: Complete `/v1/chat/completions` streaming implementation

**DoD**:
- [ ] Implement streaming response generator
- [ ] Call agent.go() with `stream="raw"`
- [ ] Serialize chunks to SSE
- [ ] Send [DONE] message at end
- [ ] Set proper headers (Cache-Control, Connection, etc.)
- [ ] Handle errors gracefully

**Tests**:
- `test_chat_completions_streaming()` passes
- Manual: curl streaming request works

**Dependencies**: Tasks 3, 4, 5 (config, serialization, conversion)

**Commit**: `feat: implement streaming chat completions endpoint`

**Owner**: Engineer

**Duration**: 3 hours

---

#### Task 7: Implement Non-Streaming Endpoint
**Goal**: Support non-streaming mode for `/v1/chat/completions`

**DoD**:
- [ ] Handle `stream=false` in request
- [ ] Call agent.go() without streaming
- [ ] Format response as OpenAI completion
- [ ] Include usage info (if available)

**Tests**:
- `test_chat_completions_non_streaming()` passes

**Dependencies**: Task 6 (streaming works)

**Commit**: `feat: add non-streaming chat completions support`

**Owner**: Engineer

**Duration**: 2 hours

---

#### Task 8: Add Error Handling
**Goal**: Gracefully handle all error cases

**DoD**:
- [ ] Handle empty messages array (400)
- [ ] Handle agent exceptions (500)
- [ ] Handle config errors (500 at startup)
- [ ] Handle tool failures (pass through to agent)
- [ ] Add error logging
- [ ] Return helpful error messages

**Tests**:
- `test_invalid_request_validation()` passes
- `test_empty_messages_array()` passes
- `test_agent_error_handling()` passes

**Dependencies**: Task 7 (endpoints implemented)

**Commit**: `feat: add comprehensive error handling`

**Owner**: Engineer

**Duration**: 2 hours

---

#### Task 9: Integration Testing
**Goal**: Write integration tests for full request/response cycles

**DoD**:
- [ ] Set up test fixtures (mock agent, test config)
- [ ] Write all integration tests from spec mapping
- [ ] All tests pass
- [ ] Coverage >80% for playground_server.py

**Tests**: All integration tests green

**Dependencies**: Task 8 (implementation complete)

**Commit**: `test: add integration tests for playground server`

**Owner**: Engineer

**Duration**: 4 hours

---

#### Task 10: Manual Testing with Playground
**Goal**: Validate end-to-end flow with actual Weave Playground

**DoD**:
- [ ] Start server locally
- [ ] Expose via ngrok
- [ ] Configure in Weave Playground
- [ ] Test: Simple conversation
- [ ] Test: Tool usage (create issue, get issue)
- [ ] Test: Multi-turn conversation
- [ ] Verify: Weave traces appear
- [ ] Document any issues found

**Tests**: All manual acceptance criteria validated

**Dependencies**: Task 9 (tests passing)

**Owner**: Engineer

**Duration**: 2 hours

---

#### Task 11: Update README Documentation
**Goal**: Document Step 3 UI approach with server instructions

**DoD**:
- [ ] Add server startup instructions
- [ ] Document ngrok setup
- [ ] Add Weave Playground configuration steps
- [ ] Include troubleshooting section
- [ ] Add example curl commands
- [ ] Include screenshots or examples

**Tests**: README is clear and actionable (peer review)

**Dependencies**: Task 10 (validation complete)

**Commit**: `docs: update README with playground server instructions`

**Owner**: Engineer

**Duration**: 2 hours

---

#### Task 12: Polish and Finalize
**Goal**: Clean up code, ensure production-ready

**DoD**:
- [ ] Run linter and formatter
- [ ] Add docstrings to all functions
- [ ] Remove debug code
- [ ] Add type hints
- [ ] Update .gitignore if needed
- [ ] All tests pass
- [ ] CI green

**Tests**: CI pipeline passes

**Dependencies**: Task 11 (documentation complete)

**Commit**: `chore: polish playground server implementation`

**Owner**: Engineer

**Duration**: 2 hours

---

### Total Effort Estimate: 27 hours (~3-4 days)

### Critical Path:
1. Task 1 (SPIKE - blocking) → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → rest

### Risk Mitigation:
- Task 1 is a blocker - do first to validate assumptions
- If Task 1 reveals issues, may need to revisit design
- Tasks 2-8 are linear, can't parallelize much
- Task 9-12 can proceed in parallel if multiple people

---

**Approval Gate**: Do not start coding until this TDR is reviewed and approved.

