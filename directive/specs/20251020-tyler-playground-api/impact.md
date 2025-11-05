# Impact Analysis — Tyler Playground API Endpoint

## Modules/packages likely touched

### New files:
- **`playground_server.py`** - FastAPI server implementing OpenAI-compatible `/v1/chat/completions` endpoint
  - SSE serialization logic for streaming responses
  - Request/response models (Pydantic)
  - Tyler agent initialization from config
  - Error handling and CORS middleware

### Modified files:
- **`pyproject.toml`** - Add new dependencies:
  - `fastapi` - Web framework
  - `uvicorn` - ASGI server
  - Additional dependencies already present: `slide-tyler`, `python-dotenv`, `weave`
  
- **`README.md`** - Update Step 3 "Vibe Check - Experiment in the Playground":
  - Add instructions to run playground server: `uv run playground_server.py`
  - Document ngrok setup: `ngrok http 8000`
  - Add Weave Playground configuration steps
  - Include screenshots or examples of Playground UI

### Unchanged (existing functionality preserved):
- **`main.py`** - Programmatic agent usage example remains unchanged
- **`tools.py`** - Tool implementations unchanged (loaded by server)
- **`tyler-chat-config.yaml`** - Config format unchanged (read by server)
- **`tests/`** - Existing tests unaffected

## Contracts to update (APIs, events, schemas, migrations)

### New HTTP API Contract (OpenAI-compatible):

**Request Schema** (`POST /v1/chat/completions`):
```json
{
  "model": "string",
  "messages": [
    {"role": "user|assistant|system|tool", "content": "string"}
  ],
  "stream": true|false,
  "temperature": 0.0-2.0 (optional),
  "max_tokens": integer (optional)
}
```

**Response Schema (streaming)** - Server-Sent Events:
```
data: {"id": "...", "object": "chat.completion.chunk", "choices": [{"delta": {"content": "..."}}]}

data: [DONE]
```

**Response Schema (non-streaming)** - JSON:
```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "gpt-4o",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "..."},
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
}
```

**Health Check** (`GET /health`):
```json
{"status": "ok", "agent": "support-bot"}
```

### Tyler Integration Contract:
- Server reads `tyler-chat-config.yaml` at startup to configure agent
- Dynamically loads tools from `tools.py` via Python import
- Uses Tyler's `stream="raw"` mode for OpenAI-compatible streaming
- Converts OpenAI messages format to Tyler `Thread`/`Message` objects

### Environment Variables:
- **Existing**: `WANDB_API_KEY`, `OPENAI_API_KEY` (or other LLM provider keys)
- **Optional new**: `PLAYGROUND_SERVER_PORT` (default: 8000), `PLAYGROUND_SERVER_HOST` (default: 0.0.0.0)

### No database migrations:
- Server is stateless (no persistence layer)
- Weave handles all observability data

## Risks

### Security:

**Medium Risk - Public API Exposure**:
- **Issue**: Server endpoint exposed via ngrok becomes publicly accessible
- **Impact**: Anyone with the ngrok URL can use the agent and consume API credits
- **Mitigation**: 
  - Document that ngrok URLs should be kept private (not committed to git)
  - Add optional API key validation middleware (check `Authorization` header)
  - Weave Playground supports team secrets for API keys
  - Rate limiting can be added if abuse becomes an issue
  - Default to local-only development (ngrok as opt-in step)

**Low Risk - Tool Execution**:
- **Issue**: Tools run arbitrary Python code based on LLM output
- **Impact**: Current tools (create_issue, get_issue) are mock implementations with no side effects
- **Mitigation**: 
  - Tools already sandboxed to safe operations
  - Future tools should follow principle of least privilege
  - Document tool security considerations

**Low Risk - Environment Variable Exposure**:
- **Issue**: Server process has access to all environment variables
- **Impact**: API keys loaded from `.env` could leak if server has debug endpoints
- **Mitigation**: 
  - No debug/env-dump endpoints in implementation
  - Follow FastAPI security best practices
  - Document not to deploy with debug mode enabled

### Performance/Availability:

**Medium Risk - Single-Threaded Bottleneck**:
- **Issue**: FastAPI with default uvicorn config may not handle concurrent requests well
- **Impact**: Multiple users in Playground could experience slowdowns
- **Mitigation**: 
  - uvicorn supports async by default (FastAPI is async-native)
  - Document scaling options if needed: `uvicorn playground_server:app --workers 4`
  - For local development (1-2 users), single worker is sufficient

**Medium Risk - LLM Latency**:
- **Issue**: OpenAI/LLM API calls can take 2-10+ seconds for complex queries
- **Impact**: Playground users may experience delays, especially with tool usage
- **Mitigation**: 
  - Streaming provides immediate feedback (first token within 1-2 seconds)
  - Document expected latency in README
  - Tyler's raw streaming mode minimizes transformation overhead

**Low Risk - ngrok Reliability**:
- **Issue**: Free ngrok tier has connection limits and may disconnect
- **Impact**: Playground connection drops during testing
- **Mitigation**: 
  - Document ngrok limitations
  - ngrok auto-reconnect on paid tier (optional upgrade)
  - Server restarts are fast (<5 seconds)

### Data integrity:

**Low Risk - Stateless API**:
- **Issue**: Server doesn't persist conversation state between requests
- **Impact**: Playground must send full conversation history in each request
- **Mitigation**: 
  - This is standard OpenAI API behavior (expected by Playground)
  - Weave Playground handles conversation state management
  - No data loss risk since there's no server-side state

**Low Risk - Message Ordering**:
- **Issue**: If concurrent requests arrive out of order, context could be wrong
- **Impact**: Each request is independent, so no risk
- **Mitigation**: Stateless design prevents this issue entirely

### Compatibility:

**Medium Risk - Tyler Raw Streaming Format Changes**:
- **Issue**: If Tyler's `stream="raw"` output format changes, SSE serialization breaks
- **Impact**: Playground stops working until server code is updated
- **Mitigation**: 
  - Pin `slide-tyler` version in `pyproject.toml`
  - Monitor Tyler changelog for breaking changes
  - Add integration test that validates chunk format

**Low Risk - Weave Playground API Expectations**:
- **Issue**: Playground might have specific OpenAI format requirements we miss
- **Impact**: Some features might not work (e.g., function calling display)
- **Mitigation**: 
  - Follow OpenAI spec closely (well-documented)
  - Manual testing in actual Weave Playground before release
  - Weave team can provide feedback on compatibility

**Low Risk - LiteLLM Version Compatibility**:
- **Issue**: Tyler uses LiteLLM, which could have breaking changes
- **Impact**: Raw streaming chunks might change format
- **Mitigation**: 
  - Tyler team manages LiteLLM compatibility
  - We depend on Tyler's abstraction, not directly on LiteLLM

### User Experience:

**Low Risk - Setup Complexity**:
- **Issue**: Users need to install ngrok and configure Playground (multi-step)
- **Impact**: Friction in onboarding, possible errors at each step
- **Mitigation**: 
  - Clear step-by-step README instructions with examples
  - Screenshots of Playground configuration
  - Troubleshooting section for common issues
  - Future: Could use localtunnel or similar alternatives

**Low Risk - Error Messages**:
- **Issue**: Generic FastAPI errors may not be helpful for debugging
- **Impact**: Users struggle to diagnose configuration issues
- **Mitigation**: 
  - Custom error handling with clear messages
  - Validate config file at startup with helpful errors
  - Log detailed errors server-side for debugging

## Observability needs

### Logs:

**Existing - Weave Integration**:
- Tyler agent already logs to Weave when `weave.init()` is called
- Each API request will create a Weave trace with:
  - Input messages, output response
  - Token usage, latency
  - Tool calls and results
  - Model reasoning (if available)

**New - Server Logs**:
- **Startup logs**: 
  - Config file loaded successfully
  - Agent initialized with model name and tools
  - Server listening on host:port
  - Weave project name
  
- **Request logs**:
  - Incoming request method, path, timestamp
  - Request ID for correlation
  - Stream mode (true/false)
  - Number of messages in conversation
  
- **Error logs**:
  - Config file parsing errors
  - Tool loading failures
  - Tyler agent exceptions
  - HTTP error responses (4xx, 5xx) with details

**Logging Implementation**:
- Use Python `logging` module with structured output
- Log level configurable via env var (default: INFO)
- Example: `[2025-10-14 12:34:56] INFO - Chat completion request received (stream=true, messages=3)`

### Metrics:

**Existing - Weave Metrics**:
- Token usage per request (prompt + completion)
- Latency per request (end-to-end)
- Tool call frequency and duration
- Model used per request
- Cost estimation (if Weave supports)

**New - Server Metrics** (nice-to-have, not MVP):
- Request count by endpoint
- Response time histogram (p50, p95, p99)
- Error rate by status code
- Active connections (concurrent requests)
- Streaming vs non-streaming ratio

**Metrics Implementation** (future):
- FastAPI middleware can track request metrics
- Could integrate Prometheus or OpenTelemetry
- For MVP: Rely on Weave for observability

### Alerts:

**None required for MVP**:
- Local development tool (not production service)
- Developers will see errors in server logs immediately
- Weave dashboard shows failures in traces

**Future considerations** (if deployed to shared environment):
- Alert on high error rate (>10% 5xx responses)
- Alert on API key unauthorized attempts (potential abuse)
- Alert on server crash/restart

## Testing considerations

### What to test:

**Unit tests**:
- SSE serialization function (chunk → `data: {json}\n\n`)
- OpenAI request → Tyler Thread/Message conversion
- Error handling for invalid requests (missing fields, wrong types)
- Config file loading and validation

**Integration tests**:
- Full request/response cycle (mock Tyler agent)
- Streaming endpoint returns proper SSE format
- Non-streaming endpoint returns proper JSON
- Health check endpoint returns 200
- CORS headers present in responses

**Manual testing**:
- Start server locally, verify startup logs
- Test with curl: `curl -X POST http://localhost:8000/v1/chat/completions -d '...'`
- Expose via ngrok, configure in Weave Playground
- Test chat interactions in Playground
- Verify Weave traces appear for each request
- Test tool usage (create issue, get issue)

### What NOT to test:

**Out of scope for unit/integration tests**:
- Tyler agent internals (tested by Tyler package)
- Weave trace creation (tested by Weave SDK)
- ngrok connectivity (external service)
- Actual LLM responses (non-deterministic)
- Weave Playground UI behavior (separate product)

### CI implications:

**New test file**:
- `tests/test_playground_server.py` - Test API endpoints and logic

**Existing tests**:
- No changes to existing test files
- Tools tests remain valid

**CI requirements**:
- No additional services needed (tests use mocks)
- Tests should complete in <10 seconds
- No external network calls (mock Tyler agent)

**Test coverage target**:
- 80%+ coverage for `playground_server.py`
- Focus on error paths and edge cases

## Dependencies

### New dependencies to add:
```toml
# pyproject.toml additions
fastapi = "^0.115.0"
uvicorn = {extras = ["standard"], version = "^0.32.0"}
```

### Existing dependencies (already in project):
- `slide-tyler` - Tyler agent runtime
- `python-dotenv` - Environment variable loading
- `weave` - Observability
- `pydantic` - Data validation (used by FastAPI)

## Rollout plan

### Phase 1: Development
1. Implement `playground_server.py` with basic `/v1/chat/completions` endpoint
2. Add unit tests for serialization and conversion logic
3. Manual testing with curl/Postman

### Phase 2: Integration
4. Test with ngrok + Weave Playground
5. Update README with setup instructions
6. Collect feedback from 2-3 internal users

### Phase 3: Documentation
7. Add troubleshooting section to README
8. Create example curl commands and screenshots
9. Document limitations and known issues

### Rollback plan:
- If server doesn't work, users can still use CLI (`tyler chat`)
- No impact on existing functionality
- New file can be removed without side effects

