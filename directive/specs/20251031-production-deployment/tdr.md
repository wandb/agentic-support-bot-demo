# Technical Design Review (TDR) — Production Deployment

**Author**: AI Agent  
**Date**: 2025-10-31  
**Links**: 
- Spec: `/directive/specs/20251031-production-deployment/spec.md`
- Impact: `/directive/specs/20251031-production-deployment/impact.md`

---

## 1. Summary

We are building Step 5 of the agentic support bot demo, which deploys the agent to production on Modal as a Slack bot. This enables users to experience the full development lifecycle: build locally → evaluate systematically → deploy to production → monitor real usage (Step 6).

The deployment extends the existing `playground_server.py` with Slack webhook handling and Modal deployment decorators. Users will create a free Slack app, configure Modal secrets, deploy with a single `modal deploy` command, and immediately start chatting with their bot via @ mentions in Slack. All production conversations will automatically flow to Weave traces, setting up the foundation for monitoring and continuous improvement in Steps 6-7.

## 2. Decision Drivers & Non‑Goals

### Decision Drivers:
- **Realistic production experience**: Users must deploy to real cloud infrastructure (not local with ngrok)
- **Weave observability showcase**: Production traces should work identically to development traces
- **Accessibility**: Free tiers only (Modal, Slack), no credit cards required
- **Simplicity**: Complete deployment in ~30 minutes
- **Support bot realism**: Slack is the most realistic channel for support use cases

### Non‑Goals:
- Production-grade hardening (rate limiting, DDoS protection, autoscaling)
- Multiple environments (staging, production)
- CI/CD pipelines or automated deployments
- Database persistence or multi-turn conversation context
- Alternative messaging platforms (Teams, Discord)
- Custom domain or SSL certificate management

## 3. Current State — Codebase Map (concise)

### Key Modules Relevant to This Feature:

**`examples/step-2/part-b/playground_server.py`** (536 lines)
- FastAPI server with OpenAI-compatible `/v1/chat/completions` endpoint
- ngrok tunnel setup for local development
- API key authentication via `PLAYGROUND_API_KEY`
- Streams responses from tyler agent
- Used by Weave Playground UI

**`workspace/tyler-chat-config.yaml`**
- Agent configuration (purpose, tools, model settings)
- Reused across local development and production
- No changes needed for deployment

**`workspace/tools.py`**
- Support ticket tools: `create_issue`, `get_issue`
- Will be called by production agent (no changes)

### Existing Data Models:
- **No database** - Tickets stored in `db/tickets.json` (simple file-based)
- Agent is stateless - no conversation persistence
- Weave traces are the source of truth for conversation history

### External Contracts Currently in Scope:
- **OpenAI-compatible API**: `POST /v1/chat/completions`
  - Request: OpenAI chat format with messages array
  - Response: SSE stream of completion chunks
  - Used by: Weave Playground

### Observability Currently Available:
- **Weave traces**: Automatic tracing of all agent calls via `@weave.op` decorators
- **Console logs**: Print statements in playground_server.py
- **No metrics dashboard yet** (Step 6)

## 4. Proposed Design (high level, implementation‑agnostic)

### Overall Architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Modal Cloud                             │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  server.py (Modal ASGI App)                               │ │
│  │                                                           │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  POST /v1/chat/completions                          │ │ │
│  │  │  - OpenAI-compatible (existing)                     │ │ │
│  │  │  - Requires PLAYGROUND_API_KEY                      │ │ │
│  │  │  - Used by Weave Playground                         │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │                                                           │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  POST /slack/events (NEW)                           │ │ │
│  │  │  - Handles app_mention events                       │ │ │
│  │  │  - Verifies Slack signing secret                    │ │ │
│  │  │  - Acknowledges within 3 seconds                    │ │ │
│  │  │  - Processes async in background                    │ │ │
│  │  │  - Responds via chat.postMessage                    │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │                                                           │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  GET /health (NEW)                                  │ │ │
│  │  │  - Returns {"status": "healthy"}                    │ │ │
│  │  │  - For Modal deployment verification                │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │                                                           │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  Tyler Agent (from tyler-chat-config.yaml)          │ │ │
│  │  │  - Same config as local development                 │ │ │
│  │  │  - Tools: create_issue, get_issue                   │ │ │
│  │  │  - MCP: W&B docs search                             │ │ │
│  │  │  - Traced by Weave automatically                    │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                          │                    │
                          │                    │
               ┌──────────▼─────────┐   ┌──────▼────────┐
               │  Slack Workspace   │   │ Weave Traces  │
               │  (@ mentions)      │   │ (observability│
               └────────────────────┘   └───────────────┘
```

### Component Responsibilities:

**1. Modal ASGI App Wrapper**
- Wraps FastAPI app with `@app.function()` decorator
- Configures secrets, image dependencies, timeouts
- Handles container lifecycle and cold starts
- Exposes public HTTPS endpoint

**2. Slack Event Handler (`/slack/events`)**
- Receives webhook POST from Slack
- Verifies request signature using `SLACK_SIGNING_SECRET`
- Immediately acknowledges (200 OK) within 3 seconds
- Spawns async task to process event
- Calls tyler agent with user message
- Posts response to Slack via `chat.postMessage` API

**3. OpenAI-Compatible Endpoint (Unchanged)**
- Maintains existing behavior for Weave Playground
- API key authentication still required
- Streaming response format unchanged

**4. Tyler Agent Loader**
- Reads `tyler-chat-config.yaml` at startup
- Initializes agent with tools and MCP servers
- Weave initialization handled automatically
- Same agent instance serves both Slack and Playground

### Interfaces & Data Contracts:

**Slack Webhook Request** (POST /slack/events):
```json
{
  "token": "verification_token",
  "team_id": "T123456",
  "event": {
    "type": "app_mention",
    "user": "U123456",
    "text": "@buzz how do I initialize Weave?",
    "ts": "1234567890.123456",
    "channel": "C123456",
    "thread_ts": "1234567890.123456"  // optional, if in thread
  },
  "type": "event_callback"
}
```

**Slack Webhook Response** (Immediate):
```json
{
  "ok": true
}
```

**Slack API Response** (Async, via chat.postMessage):
```python
client.chat_postMessage(
    channel=event["channel"],
    thread_ts=event.get("thread_ts") or event["ts"],  # reply in thread
    text=agent_response
)
```

**Health Check** (GET /health):
```json
{
  "status": "healthy",
  "timestamp": "2025-10-31T12:00:00Z"
}
```

### Error Handling:

**Slack Signature Verification Failure**:
- Return 401 Unauthorized
- Log the failure (don't expose details to client)
- Alert: This should never happen in normal operation

**Agent Execution Failure**:
- Catch all exceptions in async task
- Post error message to Slack thread:
  ```
  Sorry, I encountered an error processing your request. 
  The error has been logged and you can check the Weave traces for details.
  ```
- Log full stack trace to Modal logs
- Trace appears in Weave with error details

**LLM API Timeout**:
- Tyler handles this internally with retries
- If all retries fail, agent raises exception
- Handled by agent execution failure path above

**Slack API Failure (posting response)**:
- Catch `SlackApiError`
- Log error with full context
- Don't crash - just skip this response
- Trace still appears in Weave

### Idempotency & Retries:

**Slack Event Deduplication**:
- Slack may retry webhook if no acknowledgment
- Modal should handle duplicate `event_id`
- Simple approach: Acknowledge immediately, process once
- No persistent state means duplicates are mostly harmless
- Each event_id is unique, could cache recent event_ids in memory

**No Retry Logic Needed**:
- Agent calls are not retried on failure
- User can just @ mention again if it fails
- This is acceptable for demo purposes

### Performance Expectations:

**Cold Start**: 5-10 seconds on first request after idle
- Modal pulls container image
- Python dependencies load
- Agent initializes
- **Mitigation**: Document this behavior

**Warm Request**: 1-5 seconds typical
- Depends on LLM API latency
- Tool calls add overhead
- Slack receives response asynchronously

**Concurrency**: Modal handles multiple requests naturally
- Each request gets its own container or shares warm containers
- No shared state between requests
- Stateless design scales horizontally

## 5. Alternatives Considered

### Alternative 1: Keep ngrok + Local Deployment

**Approach**: Continue using playground_server.py with ngrok, add Slack webhook handling locally

**Pros**:
- No new platform to learn (Modal)
- No cloud deployment complexity
- Faster iteration during development

**Cons**:
- ❌ Not "real" production (goal is cloud deployment)
- ❌ User's laptop must stay running
- ❌ Doesn't demonstrate production observability patterns
- ❌ ngrok free tier has session limits
- ❌ Misses the point of the demo (production deployment)

**Decision**: Rejected. The whole point of Step 5 is to deploy to actual cloud infrastructure.

---

### Alternative 2: Streamlit Chat Interface Instead of Slack

**Approach**: Deploy a Streamlit app to Modal with chat UI

**Pros**:
- No Slack app setup required
- Simpler for users without Slack
- Visual chat interface

**Cons**:
- ❌ Needs database for chat history (added complexity)
- ❌ Less realistic for support bot use case
- ❌ Harder to collect feedback naturally (Step 6)
- ❌ Streamlit session management complexity
- ❌ Not how real support bots are deployed

**Decision**: Rejected. Slack is more realistic, and free Slack accounts are easy to create.

---

### Alternative 3: Synchronous Slack Response (Block Until Agent Completes)

**Approach**: Wait for agent response and return it in webhook response body

**Pros**:
- Simpler code - no async task spawning
- Single request/response flow

**Cons**:
- ❌ Slack has 3-second timeout - agent calls take longer
- ❌ Would cause timeout errors frequently
- ❌ Poor user experience (no typing indicator)

**Decision**: Rejected. Must use async response pattern.

---

### Alternative 4: Deploy to AWS Lambda / Cloud Run Instead of Modal

**Approach**: Use traditional serverless platforms

**Pros**:
- More familiar to some users
- More "production-like" platform

**Cons**:
- ❌ More complex setup (IAM roles, VPC, etc.)
- ❌ Requires credit card even for free tier
- ❌ Cold starts worse than Modal
- ❌ Less optimized for ML/LLM workloads
- ❌ More configuration needed

**Decision**: Rejected. Modal is simpler, ML-focused, and has better free tier.

---

### Alternative 5: Conversation State / Multi-turn Context

**Approach**: Store conversation history in Redis/DB, pass context to agent

**Pros**:
- More realistic multi-turn conversations
- Better UX for complex questions

**Cons**:
- ❌ Adds database dependency (complexity)
- ❌ State management overhead
- ❌ Not needed for demo purposes
- ❌ Weave traces already show conversation history

**Decision**: Rejected. Keep stateless for simplicity. Users can include context in their @ mention if needed.

---

### Why the Chosen Option (Modal + Slack + Async + Stateless):

1. **Modal**: Best balance of simplicity and real cloud deployment
2. **Slack**: Most realistic channel for support bot
3. **Async response**: Only way to avoid Slack timeout
4. **Stateless**: Simplifies implementation, Weave has full history anyway

This combination achieves the goal (production deployment with Weave observability) with minimal complexity.

## 6. Data Model & Contract Changes

### No Database Schema Changes:
- No database in use
- Tickets still in `db/tickets.json` (unchanged)
- No migrations needed

### API Contract Changes:

**New Endpoint: POST /slack/events**
- **Request Headers**:
  - `X-Slack-Signature` - HMAC signature for verification
  - `X-Slack-Request-Timestamp` - Request timestamp
  - `Content-Type: application/json`

- **Request Body**: Slack event webhook payload (see section 4)

- **Response**: 
  - Status: 200 OK (acknowledgment)
  - Body: `{"ok": true}` or empty

**New Endpoint: GET /health**
- **Request**: None
- **Response**: 
  ```json
  {
    "status": "healthy",
    "timestamp": "2025-10-31T12:00:00Z"
  }
  ```

**Existing Endpoint: POST /v1/chat/completions** (No Changes)
- Maintains OpenAI-compatible format
- API key authentication unchanged
- Used by Weave Playground

### Backward Compatibility:

**playground_server.py → server.py**:
- OpenAI endpoint remains 100% compatible
- Existing Weave Playground configurations continue to work
- Just point to new Modal URL instead of ngrok URL
- API key auth mechanism unchanged

**tyler-chat-config.yaml**:
- No format changes
- Same config works locally and in production
- Version compatibility: N/A (just a YAML file)

### Deprecation Plan:

- `playground_server.py` remains in `examples/step-2/part-b/` for reference
- Users can still run locally if desired
- No deprecation needed - both can coexist

## 7. Security, Privacy, Compliance

### Authentication & Authorization:

**Slack Webhook Authentication**:
- **Mechanism**: HMAC signature verification using `SLACK_SIGNING_SECRET`
- **Flow**:
  1. Slack sends `X-Slack-Signature` header with each request
  2. Server computes expected signature: `HMAC-SHA256(signing_secret, timestamp:body)`
  3. Compare signatures using constant-time comparison
  4. Reject if mismatch or timestamp too old (>5 minutes)
- **Library**: `slack-bolt` SDK handles this automatically

**Weave Playground Endpoint**:
- **Mechanism**: Bearer token authentication via `PLAYGROUND_API_KEY`
- **Flow**: 
  1. Client sends `Authorization: Bearer <key>` header
  2. Server validates against `PLAYGROUND_API_KEY` secret
  3. Reject 401 if invalid
- **Existing**: Already implemented in playground_server.py

**No User-Level Auth**:
- Slack handles user identity
- Bot trusts Slack's authentication
- Agent doesn't distinguish between users (same for all)

### Secrets Management:

**Modal Secrets System**:
- All secrets stored in Modal's encrypted secrets storage
- Never committed to git
- Never logged or exposed in responses
- Accessed via environment variables at runtime

**Required Secrets**:
- `WANDB_API_KEY` - For Weave tracing and W&B Inference
- `PLAYGROUND_API_KEY` - For OpenAI endpoint auth
- `SLACK_BOT_TOKEN` - For Slack API calls (posting messages)
- `SLACK_SIGNING_SECRET` - For webhook verification

**Rotation Strategy**:
- Secrets can be updated via `modal secret create --force`
- Requires redeployment for server to pick up new values
- No automated rotation (demo purposes)

### PII Handling:

**User Messages in Slack**:
- Messages may contain PII (names, emails, etc.)
- Sent to LLM API (W&B Inference)
- Stored in Weave traces
- **Mitigation**: Document this in README
- **Note**: This is a demo, not production-hardened

**Weave Trace Data**:
- Full conversation history stored in Weave
- Includes tool calls, LLM responses, user messages
- Accessible to anyone with W&B project access
- **Mitigation**: Users should use demo data, not real PII

### Threat Model & Mitigations:

**Threat: Unauthorized LLM Access**:
- **Attack**: Someone discovers Modal URL and spams Slack endpoint
- **Mitigation**: Slack signing secret verification prevents non-Slack requests
- **Residual Risk**: Low - would need to forge Slack signatures

**Threat: API Key Leakage**:
- **Attack**: `PLAYGROUND_API_KEY` exposed in logs or code
- **Mitigation**: Never log secrets, use Modal secrets system
- **Residual Risk**: Low - secrets are environment variables only

**Threat: LLM Prompt Injection**:
- **Attack**: User crafts malicious Slack message to manipulate agent
- **Mitigation**: None specifically in this step
- **Residual Risk**: Medium - but acceptable for demo
- **Future**: Could add input validation in Step 6

**Threat: DoS via High Volume**:
- **Attack**: Spam bot with @ mentions to run up costs
- **Mitigation**: Modal free tier limits, Slack rate limiting
- **Residual Risk**: Low - demo usage only, free tier caps costs

**Threat: Secrets in Traces**:
- **Attack**: Agent might log API keys to Weave traces
- **Mitigation**: Weave automatically redacts common secret patterns
- **Residual Risk**: Low - but review traces for leakage

### Compliance Considerations:

- **GDPR**: Not applicable (demo purposes, no EU users expected)
- **CCPA**: Not applicable (demo purposes)
- **SOC2**: Not applicable (not a production service)
- **Note**: Users are responsible for their own compliance if they use this in production

## 8. Observability & Operations

### Logs to Add:

**Modal Application Logs** (automatic):
- Python `print()` statements → Modal logs
- Exceptions and stack traces → Modal logs
- Access via `modal app logs <app-name>`

**Structured Logging** (add to server.py):
```python
import logging
logger = logging.getLogger(__name__)

# Log Slack events
logger.info(f"Received Slack event: type={event['type']}, user={event['user']}")

# Log agent invocations
logger.info(f"Invoking agent for message: {message_preview}")

# Log errors
logger.error(f"Agent execution failed: {str(e)}", exc_info=True)
```

**Weave Traces** (automatic via @weave.op):
- All agent calls automatically traced
- Tool executions captured
- LLM requests logged with latency, tokens, cost
- No additional code needed

### Metrics to Track:

**Weave-Provided (automatic)**:
- Request latency (p50, p95, p99)
- Token usage per request
- Cost per request
- Tool call frequency
- Error rate

**Modal-Provided (automatic)**:
- Container invocations
- Cold start frequency
- Memory/CPU usage
- Request volume

**Custom Metrics** (Step 6):
- User feedback (thumbs up/down)
- Message volume over time
- Errors by type

### Dashboards:

**Modal Dashboard** (automatic):
- View at modal.com/apps
- Shows container metrics, logs, errors
- Deployment history

**Weave Traces UI** (automatic):
- Filter by date range, user, conversation
- Click into traces for full details
- Compare performance across runs

**Custom Dashboard** (Step 6):
- Streamlit app for production monitoring
- Aggregate metrics over time
- User feedback analysis

### Alerts:

**Not Implemented in Step 5**:
- No automated alerts
- Manual monitoring via dashboards

**Future (Step 6+)**:
- Weave Monitors: Alert on quality degradation
- Modal: Email on deployment failures
- Custom: Slack alert on high error rate

### Runbooks:

**Deployment Failed**:
```
1. Check Modal logs: modal app logs <app-name>
2. Verify secrets are set: modal secret list
3. Check image build logs in Modal dashboard
4. Common issues:
   - Missing secrets
   - Syntax error in server.py
   - Dependencies not in requirements.txt
```

**Bot Not Responding in Slack**:
```
1. Check Modal deployment is running: modal app list
2. Verify Slack webhook URL is correct in Slack app settings
3. Check Modal logs for errors: modal app logs <app-name>
4. Check Weave traces for agent errors
5. Test health endpoint: curl https://<modal-url>/health
```

**Slow Response Times**:
```
1. Check if cold start (first request): Check Modal logs for container startup
2. Check Weave traces for slow LLM calls
3. Check W&B Inference status
4. Consider warming containers (Modal config)
```

### SLOs (Targets):

**Not formal SLOs** (this is a demo), but expectations:

- **Availability**: 99% (Modal platform reliability)
- **Latency**: 
  - Cold start: <10 seconds
  - Warm request: <5 seconds (p95)
- **Error Rate**: <5% (agent execution failures)
- **Cost**: <$0 (stay within free tiers)

## 9. Rollout & Migration

### Feature Flags:

**Not Needed**:
- This is a new deployment, not a change to existing system
- Users opt-in by deploying
- No gradual rollout required

### Data Backfill / Sync:

**Not Applicable**:
- No data to migrate
- Stateless deployment
- Each deployment is independent

### Revert Plan:

**If deployment is broken**:
1. `modal app stop <app-name>` - Stop the deployment immediately
2. Fix issue in `workspace/server.py`
3. Test locally if possible (run FastAPI locally)
4. Redeploy: `modal deploy workspace/server.py`

**No data loss risk**:
- Weave traces are independent of deployment
- No persistent state to lose
- Slack conversations are in Slack (not affected)

### Blast Radius:

**Limited Impact**:
- Only affects the user's own bot deployment
- No shared infrastructure
- Each Modal deployment is isolated
- Failure doesn't affect other users

**Worst Case**:
- Bot stops responding
- User sees error messages in Slack
- Can redeploy or stop anytime

## 10. Test Strategy & Spec Coverage (TDD)

### TDD Commitment:

- Write failing tests **before** implementing each component
- Confirm test fails for the right reason
- Implement minimal code to make test pass
- Refactor while keeping tests green
- All tests run in CI and block merge

### Spec→Test Mapping:

Based on acceptance criteria in spec.md:

#### AC1: Modal Deployment
- **Test ID**: `test_modal_deployment_success`
- **Given**: Valid Modal configuration with secrets
- **When**: `modal deploy workspace/server.py` runs
- **Then**: Deployment succeeds and returns URL
- **Type**: Integration (requires Modal account)

#### AC2: Slack Bot Interaction
- **Test ID**: `test_slack_bot_responds_to_mention`
- **Given**: Slack webhook configured with valid signing secret
- **When**: POST /slack/events with app_mention event
- **Then**: 
  - Endpoint returns 200 OK within 3 seconds
  - Agent processes message asynchronously
  - Response posted to Slack thread
- **Type**: Integration (requires Slack test workspace)

- **Test ID**: `test_slack_bot_invalid_signature_rejected`
- **Given**: Slack webhook with invalid signature
- **When**: POST /slack/events
- **Then**: Returns 401 Unauthorized
- **Type**: Unit

#### AC3: Asynchronous Response
- **Test ID**: `test_slack_acknowledgment_within_timeout`
- **Given**: Slow agent response (>3 seconds)
- **When**: POST /slack/events
- **Then**: Acknowledgment returned in <3 seconds
- **Type**: Unit (mock agent delay)

- **Test ID**: `test_async_agent_invocation`
- **Given**: Slack event received
- **When**: Event processing starts
- **Then**: Agent runs in background task, not blocking response
- **Type**: Unit

#### AC4: Weave Playground Compatibility
- **Test ID**: `test_openai_endpoint_unchanged`
- **Given**: Weave Playground client
- **When**: POST /v1/chat/completions with valid API key
- **Then**: Returns SSE stream of completions
- **Type**: Integration

- **Test ID**: `test_openai_endpoint_requires_auth`
- **Given**: Request without API key
- **When**: POST /v1/chat/completions
- **Then**: Returns 401 Unauthorized
- **Type**: Unit

#### AC5: Slack Authentication
- **Test ID**: `test_slack_signature_verification`
- **Given**: Valid Slack webhook with correct signature
- **When**: Signature verified
- **Then**: Request processed
- **Type**: Unit

- **Test ID**: `test_slack_old_timestamp_rejected`
- **Given**: Slack webhook with timestamp >5 minutes old
- **When**: Signature verified
- **Then**: Request rejected
- **Type**: Unit

#### AC6: Same Configuration Works
- **Test ID**: `test_config_loads_in_production`
- **Given**: tyler-chat-config.yaml from workspace
- **When**: Agent initializes on Modal
- **Then**: Config loads successfully, tools available
- **Type**: Integration

#### AC7: Production Traces Visible
- **Test ID**: `test_weave_traces_production_conversation`
- **Given**: Slack message processed by agent
- **When**: Checking Weave UI
- **Then**: Trace appears with full context, tool calls, timing
- **Type**: E2E (requires Weave project)

### Test Tiers:

**Unit Tests** (fast, no external dependencies):
- `test_slack_signature_verification`
- `test_slack_invalid_signature_rejected`
- `test_slack_old_timestamp_rejected`
- `test_openai_endpoint_requires_auth`
- `test_async_agent_invocation`
- `test_health_endpoint`

**Integration Tests** (requires Modal/Slack test setup):
- `test_modal_deployment_success`
- `test_slack_bot_responds_to_mention`
- `test_openai_endpoint_unchanged`
- `test_config_loads_in_production`

**E2E Tests** (full flow, manual or automated):
- `test_weave_traces_production_conversation`
- `test_slack_thread_response`

### Negative & Edge Cases:

**Slack Webhook**:
- ❌ Invalid signature → 401
- ❌ Missing event field → 400
- ❌ Old timestamp → 401
- ❌ Unknown event type → log and ignore
- ❌ Agent fails → post error message to Slack

**OpenAI Endpoint**:
- ❌ Missing API key → 401
- ❌ Invalid API key → 401
- ❌ Malformed JSON → 400
- ❌ Agent fails → return error in stream

**Modal Deployment**:
- ❌ Missing secrets → deployment fails with clear error
- ❌ Syntax error in server.py → deployment fails
- ❌ Import error → container fails to start

**Agent Execution**:
- ❌ LLM API timeout → retry, then fail gracefully
- ❌ Tool execution fails → agent handles and responds
- ❌ Config file missing → startup fails with clear error

### Performance Tests:

**Not Formal Load Tests** (demo purposes), but manual testing:
- Cold start timing: Deploy, wait 10+ minutes, trigger first request
- Warm request timing: Trigger multiple requests in sequence
- Concurrent requests: @ mention bot from multiple users simultaneously

### CI Requirements:

**All tests must**:
- Run in GitHub Actions on every PR
- Pass before merge allowed
- Include linting (ruff) and formatting (black)
- Check type hints (mypy) if applicable

**CI Configuration** (`.github/workflows/test.yml`):
```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
      - name: Run unit tests
        run: |
          pytest tests/step-5/ -m "not integration"
      - name: Lint
        run: |
          ruff check examples/step-5/
```

**Integration tests** run manually before release (require Modal/Slack credentials).

## 11. Risks & Open Questions

### Known Risks & Mitigations:

**Risk: Modal Platform Outage**
- **Impact**: Bot unavailable until Modal recovers
- **Mitigation**: Document Modal status page, provide local fallback instructions
- **Likelihood**: Low (Modal has good uptime)

**Risk: Slack API Changes**
- **Impact**: Webhook format changes could break integration
- **Mitigation**: Use official `slack-bolt` SDK which handles versioning
- **Likelihood**: Low (Slack maintains backward compatibility)

**Risk: Cold Start User Experience**
- **Impact**: First @ mention after idle takes 10+ seconds
- **Mitigation**: Document this behavior, set expectations in README
- **Likelihood**: High (Modal free tier cold starts are normal)

**Risk: LLM Cost Overrun**
- **Impact**: User exceeds W&B Inference free tier
- **Mitigation**: Modal free tier limits container hours, document costs
- **Likelihood**: Low (demo usage won't hit limits)

**Risk: User Confusion with Setup**
- **Impact**: Users can't complete Slack app setup
- **Mitigation**: Detailed step-by-step instructions with screenshots
- **Likelihood**: Medium (Slack app setup has many steps)

### Open Questions:

**Q1: Should we pre-warm Modal containers to avoid cold starts?**
- **Options**:
  - A) Let them cold start naturally (simpler)
  - B) Add keep-warm configuration (costs money)
- **Proposed Path**: A - Document cold starts, accept this for demo
- **Decision Date**: Approved in this TDR

**Q2: Should we support slash commands in addition to @ mentions?**
- **Options**:
  - A) @ mentions only (simpler)
  - B) Add slash commands like `/buzz help`
- **Proposed Path**: A - @ mentions sufficient for demo
- **Decision Date**: Approved in this TDR

**Q3: Should we show typing indicator while agent is working?**
- **Options**:
  - A) No indicator (simpler)
  - B) Post "typing..." message, update when done
- **Proposed Path**: A - Keep simple for now, could add in Step 6
- **Decision Date**: Approved in this TDR

**Q4: What if user has existing Modal/Slack accounts with different settings?**
- **Options**:
  - A) Assume clean setup, document conflicts
  - B) Handle all edge cases (complex)
- **Proposed Path**: A - Document common conflicts in troubleshooting
- **Decision Date**: Approved in this TDR

## 12. Milestones / Plan (post‑approval)

### Task 1: Extend playground_server.py for Modal

**Definition of Done**:
- [ ] `server.py` created in `examples/step-5/`
- [ ] FastAPI app wrapped with `@app.function()` decorator
- [ ] Modal image includes slack-bolt dependency
- [ ] Modal secrets configured (WANDB_API_KEY, PLAYGROUND_API_KEY)
- [ ] Health endpoint added: GET /health
- [ ] Existing OpenAI endpoint unchanged and working
- [ ] Tests: `test_health_endpoint`, `test_openai_endpoint_unchanged`
- [ ] Lint passes, code formatted

**Dependencies**: None  
**Owner**: Implementation team

---

### Task 2: Add Slack Webhook Handler

**Definition of Done**:
- [ ] POST /slack/events endpoint added
- [ ] Slack signature verification implemented
- [ ] Acknowledgment returned within 3 seconds
- [ ] Event processing spawned as background task
- [ ] Tests: `test_slack_signature_verification`, `test_slack_invalid_signature_rejected`, `test_async_agent_invocation`
- [ ] Lint passes, code formatted

**Dependencies**: Task 1 (server.py exists)  
**Owner**: Implementation team

---

### Task 3: Integrate Tyler Agent with Slack Events

**Definition of Done**:
- [ ] Extract message text from Slack event
- [ ] Invoke tyler agent with message
- [ ] Post agent response to Slack via chat.postMessage
- [ ] Handle errors gracefully (post error message to Slack)
- [ ] Weave traces captured automatically
- [ ] Tests: `test_slack_bot_responds_to_mention`, `test_config_loads_in_production`
- [ ] Lint passes, code formatted

**Dependencies**: Task 2 (Slack endpoint exists)  
**Owner**: Implementation team

---

### Task 4: Modal Deployment Configuration

**Definition of Done**:
- [ ] Modal secrets documented (how to set)
- [ ] Deployment tested: `modal deploy workspace/server.py`
- [ ] Public URL accessible
- [ ] Health check returns 200 OK
- [ ] Tests: `test_modal_deployment_success` (integration)
- [ ] Deployment succeeds in CI

**Dependencies**: Task 3 (full server.py complete)  
**Owner**: Implementation team

---

### Task 5: Slack App Setup Documentation

**Definition of Done**:
- [ ] README section added for Step 5
- [ ] Screenshot guide for creating Slack app
- [ ] Instructions for getting bot token and signing secret
- [ ] Instructions for configuring Event Subscriptions URL
- [ ] Troubleshooting section added
- [ ] Sample Slack messages to test with
- [ ] Spec acceptance criteria verified

**Dependencies**: Task 4 (deployment working)  
**Owner**: Documentation team

---

### Task 6: End-to-End Verification

**Definition of Done**:
- [ ] Fresh Modal deployment completed
- [ ] Fresh Slack app created and configured
- [ ] @ mention bot in Slack → receives response
- [ ] Conversation appears in Weave traces
- [ ] Weave Playground still works with production URL
- [ ] All acceptance criteria from spec.md verified
- [ ] Tests: `test_weave_traces_production_conversation` (E2E)
- [ ] Sign-off from spec author

**Dependencies**: Task 5 (docs complete)  
**Owner**: QA / Implementation team

---

**Total Estimated Time**: 2-3 days (assuming no blockers)

**Critical Path**: Tasks 1 → 2 → 3 → 4 → 5 → 6 (sequential)

---

**Approval Gate**: Do not start coding until this TDR is reviewed and approved in the PR.

