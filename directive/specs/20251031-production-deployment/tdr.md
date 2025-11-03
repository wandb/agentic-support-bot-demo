# Technical Design Review (TDR) — Production Deployment

**Author**: AI Agent  
**Date**: 2025-11-03  
**Links**: 
- Spec: `/directive/specs/20251031-production-deployment/spec.md`
- Impact: `/directive/specs/20251031-production-deployment/impact.md`

---

## 1. Summary

We are building Step 5 of the agentic support bot demo, which deploys the agent to production on Modal cloud platform. This enables users to experience the full development lifecycle: build locally → evaluate systematically → deploy to production → monitor real usage (Step 6).

The deployment uses the unified `server.py` from Step 2, which already includes Modal deployment decorators. Users will configure Modal secrets, deploy with `modal deploy workspace/server.py`, and chat with their production agent via Weave Playground. The key learning: production traces look identical to development traces, demonstrating that Weave provides seamless observability across environments.

This step is intentionally simple (~15 minutes) to avoid blockers and get users quickly to Step 6 (monitoring), where the Weave value really shines.

## 2. Decision Drivers & Non‑Goals

### Decision Drivers:
- **Realistic production experience**: Users must deploy to real cloud infrastructure (not local with ngrok)
- **Weave observability showcase**: Production traces should work identically to development traces
- **Accessibility**: Free tiers only (Modal), no credit cards required
- **Simplicity**: Complete deployment in ~15 minutes
- **Remove blockers**: No complex third-party integrations required
- **Focus on Weave**: The tutorial is about Weave, not infrastructure/integrations
- **Fast path to Step 6**: Monitoring is where Weave value shines - get there quickly

### Non‑Goals:
- Production-grade hardening (rate limiting, DDoS protection, autoscaling)
- Multiple environments (staging, production)
- CI/CD pipelines or automated deployments
- Database persistence or multi-turn conversation context
- Messaging platform integration as required path (Slack is optional bonus)
- Custom domain or SSL certificate management
- Custom chat UI (Weave Playground is sufficient)

## 3. Current State — Codebase Map (concise)

### Key Modules Relevant to This Feature:

**`examples/step-2/part-b/server.py`** (~500 lines)
- Unified server that works locally (Step 2) and on Modal (Step 5)
- FastAPI with OpenAI-compatible `/v1/chat/completions` endpoint
- ngrok tunnel setup for local development
- Modal deployment decorators (conditionally loaded)
- API key authentication via `PLAYGROUND_API_KEY`
- Streams responses from tyler agent
- Optional Slack support (gracefully skipped if not configured)
- Used by Weave Playground UI (local or production)

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
  - Used by: Weave Playground (local in Step 2, production in Step 5)

### Observability Currently Available:
- **Weave traces**: Automatic tracing of all agent calls via `@weave.op` decorators
- **Console logs**: Print statements in server.py
- **No metrics dashboard yet** (Step 6)
- **Key insight**: Same traces work locally and in production

## 4. Proposed Design (high level, implementation‑agnostic)

### Overall Architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Modal Cloud                             │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  server.py (same as Step 2, now on Modal)                 │ │
│  │                                                           │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  POST /v1/chat/completions                          │ │ │
│  │  │  - OpenAI-compatible                                │ │ │
│  │  │  - Requires PLAYGROUND_API_KEY                      │ │ │
│  │  │  - Used by Weave Playground                         │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │                                                           │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  GET /health                                        │ │ │
│  │  │  - Returns {"status": "healthy"}                    │ │ │
│  │  │  - For deployment verification                      │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │                                                           │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  Tyler Agent (from tyler-chat-config.yaml)          │ │ │
│  │  │  - Same config as local                             │ │ │
│  │  │  - Tools: create_issue, get_issue                   │ │ │
│  │  │  - MCP: W&B docs search                             │ │ │
│  │  │  - Traced by Weave automatically                    │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                          │                    │
                          │                    │
               ┌──────────▼─────────┐   ┌──────▼────────┐
               │ Weave Playground   │   │ Weave Traces  │
               │  (chat interface)  │   │ (observability│
               └────────────────────┘   └───────────────┘
```

**Key Insight**: Users point Weave Playground to the Modal URL instead of ngrok URL. Everything else stays the same - same agent, same config, same traces!

### Component Responsibilities:

**1. Modal ASGI App Wrapper**
- Wraps FastAPI app with `@modal.asgi_app()` decorator
- Configures secrets, image dependencies, timeouts
- Handles container lifecycle and cold starts
- Exposes public HTTPS endpoint

**2. OpenAI-Compatible Endpoint** (Unchanged from Step 2)
- Maintains existing behavior for Weave Playground
- API key authentication still required
- Streaming response format unchanged
- Works on Modal exactly as it did locally

**3. Tyler Agent Loader**
- Reads `tyler-chat-config.yaml` at startup
- Initializes agent with tools and MCP servers
- Weave initialization handled automatically
- Same agent instance serves all requests

### Interfaces & Data Contracts:

**Health Check** (GET /health):
```json
{
  "status": "healthy",
  "timestamp": "2025-11-03T12:00:00Z",
  "agent_name": "agent",
  "model": "openai/deepseek-ai/DeepSeek-R1-0528"
}
```

**OpenAI Chat Endpoint** (POST /v1/chat/completions):
- No changes from Step 2
- Same request/response format
- See playground_server.py for details

### Error Handling:

**Agent Execution Failure**:
- Catch all exceptions during agent streaming
- Return error in SSE stream format
- Log full stack trace to Modal logs
- Trace appears in Weave with error details

**LLM API Timeout**:
- Tyler handles this internally with retries
- If all retries fail, agent raises exception
- Handled by agent execution failure path above

**Modal Deployment Failure**:
- Check Modal logs for container errors
- Common causes: missing secrets, syntax errors, import failures
- Fix and redeploy

### Performance Expectations:

**Cold Start**: 5-10 seconds on first request after idle
- Modal pulls container image
- Python dependencies load
- Agent initializes
- **Mitigation**: Document this behavior

**Warm Request**: 1-5 seconds typical
- Depends on LLM API latency
- Tool calls add overhead
- SSE streaming provides progressive feedback

**Concurrency**: Modal handles multiple requests naturally
- Each request gets container or shares warm containers
- No shared state between requests
- Stateless design scales horizontally

## 5. Alternatives Considered

### Alternative 1: Keep ngrok + Local Only

**Approach**: Skip cloud deployment, keep using ngrok from Step 2

**Pros**:
- No new platform to learn
- Zero setup time
- Works immediately

**Cons**:
- ❌ Not "real" production (goal is cloud deployment)
- ❌ User's laptop must stay running
- ❌ Doesn't demonstrate production observability patterns
- ❌ Misses the point: experiencing Weave in actual production

**Decision**: Rejected. Cloud deployment is the whole point of Step 5.

---

### Alternative 2: Deploy to AWS Lambda / Cloud Run

**Approach**: Use traditional serverless platforms

**Pros**:
- More "production-like" platform
- More familiar to some users

**Cons**:
- ❌ More complex setup (IAM roles, VPC, etc.)
- ❌ Requires credit card even for free tier
- ❌ Cold starts worse than Modal
- ❌ Not optimized for ML/LLM workloads
- ❌ More configuration needed

**Decision**: Rejected. Modal is simpler and ML-focused.

---

### Alternative 3: Slack Bot as Primary Interface

**Approach**: Require users to set up Slack app for production traffic

**Pros**:
- Most realistic for support bot use case
- Natural feedback mechanism (reactions)

**Cons**:
- ❌ Slack setup takes 20+ minutes (OAuth, webhooks, etc.)
- ❌ Potential blocker for users without Slack
- ❌ Orthogonal to Weave learning (this is about Slack, not Weave)
- ❌ Delays getting to Step 6 where Weave value shines

**Decision**: Rejected for main path. Make it optional bonus.

---

### Alternative 4: Build Custom Chat UI

**Approach**: Create custom web interface for production traffic

**Pros**:
- Clean, branded experience
- No third-party dependencies

**Cons**:
- ❌ Requires frontend code (React, etc.)
- ❌ More complexity
- ❌ Weave Playground already provides this
- ❌ Not the focus of this tutorial

**Decision**: Rejected. Weave Playground is sufficient.

---

### Why the Chosen Option (Modal + Playground):

1. **Modal**: Best balance of simplicity and real cloud deployment
2. **Weave Playground**: Already familiar from Step 2, zero additional setup
3. **Fast**: 15 minutes to production, immediately ready for Step 6
4. **Focused**: About Weave observability, not infrastructure complexity

This achieves the goal (production deployment with Weave observability) with minimal friction.

## 6. Data Model & Contract Changes

### No Database Schema Changes:
- No database in use
- Tickets still in `db/tickets.json` (unchanged)
- No migrations needed

### API Contract Changes:

**Existing Endpoint: POST /v1/chat/completions** (No Changes)
- Maintains OpenAI-compatible format
- API key authentication unchanged
- Used by Weave Playground (now pointing to Modal URL instead of ngrok)

**New Endpoint: GET /health**
- **Request**: None
- **Response**: 
  ```json
  {
    "status": "healthy",
    "timestamp": "2025-11-03T12:00:00Z",
    "agent_name": "agent",
    "model": "openai/deepseek-ai/DeepSeek-R1-0528"
  }
  ```

### Backward Compatibility:

**From Step 2 to Step 5**:
- OpenAI endpoint remains 100% compatible
- Existing Weave Playground configurations continue to work
- Just update Base URL from ngrok to Modal
- API key auth mechanism unchanged
- Same response format

**No Deprecation Needed**:
- Local server with ngrok still works (users can run both)
- Modal deployment is additive, not replacement
- Both can coexist

## 7. Security, Privacy, Compliance

### Authentication & Authorization:

**API Key Authentication**:
- **Mechanism**: Bearer token via `PLAYGROUND_API_KEY`
- **Flow**:
  1. Client sends `Authorization: Bearer <key>` header
  2. Server validates against `PLAYGROUND_API_KEY` secret
  3. Reject 401 if invalid
- **Existing**: Already implemented in Step 2

**No User-Level Auth**:
- Playground handles user identity
- Agent doesn't distinguish between users
- Same behavior for all requests

### Secrets Management:

**Modal Secrets System**:
- All secrets stored in Modal's encrypted secrets storage
- Never committed to git
- Never logged or exposed in responses
- Accessed via environment variables at runtime

**Required Secrets**:
- `WANDB_API_KEY` - For Weave tracing and W&B Inference
- `PLAYGROUND_API_KEY` - For API authentication

**Optional Secrets (Bonus Feature)**:
- `SLACK_BOT_TOKEN` - For Slack bot if user configures it
- `SLACK_SIGNING_SECRET` - For webhook verification

**Rotation Strategy**:
- Secrets updated via `modal secret create --force`
- Requires redeployment for server to pick up new values
- No automated rotation (demo purposes)

### PII Handling:

**User Messages in Playground**:
- Messages may contain PII
- Sent to LLM API (W&B Inference)
- Stored in Weave traces
- **Mitigation**: Document this in README
- **Note**: Demo purposes, users should use test data

**Weave Trace Data**:
- Full conversation history stored in Weave
- Includes tool calls, LLM responses, user messages
- Accessible to anyone with W&B project access
- **Mitigation**: Users should use demo data

### Threat Model & Mitigations:

**Threat: Unauthorized LLM Access**:
- **Attack**: Someone discovers Modal URL and spams requests
- **Mitigation**: API key required on /v1/chat/completions
- **Mitigation**: Modal free tier limits container hours
- **Residual Risk**: Low - users control their API key

**Threat: API Key Leakage**:
- **Attack**: API keys exposed in logs or code
- **Mitigation**: Never log secrets, use Modal secrets system
- **Residual Risk**: Low - secrets are environment variables only

**Threat: LLM Prompt Injection**:
- **Attack**: User crafts malicious message to manipulate agent
- **Mitigation**: None specifically in this step
- **Residual Risk**: Medium - acceptable for demo

**Threat: DoS via High Volume**:
- **Attack**: Spam requests to run up costs
- **Mitigation**: Modal free tier limits
- **Residual Risk**: Low - demo usage only

### Compliance Considerations:
- Not applicable (demo purposes only)
- Users responsible for their own compliance if used beyond demo

## 8. Observability & Operations

### Logs:

**Modal Application Logs** (automatic):
- Python `print()` / `logger` statements → Modal logs
- Exceptions and stack traces → Modal logs
- Access via `modal app logs tyler-production-server`

**Weave Traces** (automatic via @weave.op):
- All agent calls automatically traced
- Tool executions captured
- LLM requests logged with latency, tokens, cost
- No additional code needed
- **This is the primary learning objective**

### Metrics:

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
- User feedback
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
- Will build monitoring dashboard
- Aggregate metrics over time
- User feedback analysis

### Runbooks:

**Deployment Failed**:
```
1. Check Modal logs: modal app logs tyler-production-server
2. Verify secrets are set: modal secret list
3. Check image build logs in Modal dashboard
4. Common issues:
   - Missing secrets (wandb-secrets not created)
   - Syntax error in server.py
   - Dependencies not in Modal image
```

**Health Endpoint Returns Error**:
```
1. Verify deployment is running: modal app list
2. Check Modal logs: modal app logs tyler-production-server
3. Test locally first: uv run workspace/server.py --no-ngrok
4. Redeploy: modal deploy workspace/server.py
```

**Playground Can't Connect**:
```
1. Verify Modal URL is correct (check modal app list)
2. Verify API key matches PLAYGROUND_API_KEY
3. Test health endpoint: curl https://modal-url/health
4. Check Weave Playground provider configuration
```

**Slow Response Times**:
```
1. Check if cold start (first request): Check Modal logs
2. Check Weave traces for slow LLM calls
3. Check W&B Inference status
4. Subsequent requests should be faster
```

### SLOs (Targets):

**Not formal SLOs** (demo purposes), but expectations:

- **Availability**: 99% (Modal platform reliability)
- **Latency**: 
  - Cold start: <10 seconds
  - Warm request: <5 seconds (p95)
- **Error Rate**: <5% (agent execution failures)
- **Cost**: <$0 (stay within free tier)

## 9. Rollout & Migration

### Feature Flags:
**Not Needed** - Users opt-in by deploying to Modal

### Data Backfill / Sync:
**Not Applicable** - Stateless deployment, no data to migrate

### Revert Plan:
1. `modal app stop tyler-production-server` - Stop immediately
2. Fix issue in `workspace/server.py`
3. Test locally: `uv run workspace/server.py --no-ngrok`
4. Redeploy: `modal deploy workspace/server.py`

### Blast Radius:
- Only affects user's own deployment
- No shared infrastructure
- Each Modal deployment is isolated
- Failure doesn't affect other users

## 10. Test Strategy & Spec Coverage (TDD)

### TDD Commitment:

- Write failing tests **before** implementing
- Confirm test fails for the right reason
- Implement minimal code to make test pass
- Refactor while keeping tests green

### Spec→Test Mapping:

#### AC1: Modal Deployment
- **Test ID**: `test_modal_deployment_success`
- **Type**: Integration (requires Modal account)

#### AC2: Health Check Works  
- **Test ID**: `test_health_endpoint`
- **Type**: Unit (mock agent config)

#### AC3: Weave Playground Connection
- **Test ID**: `test_openai_endpoint_on_modal`
- **Type**: Integration

#### AC4: Production Conversation
- **Test ID**: `test_production_conversation_trace`
- **Type**: E2E (requires Modal + Weave)

#### AC5: Same Configuration Works
- **Test ID**: `test_config_loads_on_modal`
- **Type**: Integration

#### AC6: Production Traces Visible
- **Test ID**: `test_weave_traces_show_production`
- **Type**: E2E

#### AC7: Deployment Persistence
- **Test ID**: `test_deployment_stays_up`
- **Type**: Manual (wait period, verify still running)

### Test Tiers:

**Unit Tests** (fast, no external dependencies):
- `test_health_endpoint`
- `test_api_key_validation`
- `test_message_conversion`

**Integration Tests** (requires Modal setup):
- `test_modal_deployment_success`
- `test_openai_endpoint_on_modal`
- `test_config_loads_on_modal`

**E2E Tests** (full flow):
- `test_production_conversation_trace`
- `test_weave_traces_show_production`
- `test_deployment_stays_up` (manual)

### Negative & Edge Cases:

**Modal Deployment**:
- ❌ Missing secrets → deployment fails with clear error
- ❌ Syntax error in server.py → deployment fails
- ❌ Import error → container fails to start

**OpenAI Endpoint**:
- ❌ Missing API key → 401
- ❌ Invalid API key → 401
- ❌ Malformed JSON → 400
- ❌ Agent fails → return error in stream

**Agent Execution**:
- ❌ LLM API timeout → retry, then fail gracefully
- ❌ Tool execution fails → agent handles and responds
- ❌ Config file missing → startup fails

### CI Requirements:

**All tests must**:
- Run in GitHub Actions on every PR
- Pass before merge allowed
- Include linting (ruff) and formatting

**Integration tests** run manually before release (require Modal credentials).

## 11. Risks & Open Questions

### Known Risks & Mitigations:

**Risk: Modal Platform Outage**
- **Impact**: Bot unavailable until Modal recovers
- **Mitigation**: Document Modal status page
- **Likelihood**: Low (Modal has good uptime)

**Risk: Cold Start UX**
- **Impact**: First request takes 10+ seconds
- **Mitigation**: Document this behavior
- **Likelihood**: High (Modal free tier cold starts are normal)

**Risk: LLM Cost Overrun**
- **Impact**: User exceeds W&B Inference free tier
- **Mitigation**: Modal free tier limits container hours
- **Likelihood**: Low (demo usage won't hit limits)

**Risk: User Confusion**
- **Impact**: Users can't complete Modal setup
- **Mitigation**: Clear step-by-step instructions
- **Likelihood**: Low (Modal setup is straightforward)

### Open Questions:

**Q1: Is Weave Playground sufficient for generating production traffic?**
- **Answer**: Yes - production traces are identical regardless of source
- **Decision**: Approved in this TDR

**Q2: Should we include Slack instructions in Step 5?**
- **Answer**: No - make it optional bonus to avoid blocker
- **Decision**: Approved in this TDR

**Q3: Should we warm Modal containers to avoid cold starts?**
- **Answer**: No - document as expected behavior
- **Decision**: Approved in this TDR

## 12. Milestones / Plan (post‑approval)

### Task 1: Verify Unified Server Works

**Definition of Done**:
- [ ] `server.py` in `examples/step-2/part-b/` includes Modal support
- [ ] Server runs locally: `uv run workspace/server.py`
- [ ] Server can run without ngrok: `uv run workspace/server.py --no-ngrok`
- [ ] Modal decorators present but optional (graceful import)
- [ ] Slack code present but optional (graceful import)
- [ ] Lint passes, code formatted

**Dependencies**: None  
**Owner**: Implementation team

---

### Task 2: Update Documentation for Simplified Flow

**Definition of Done**:
- [ ] README Step 5 updated to remove Slack from main path
- [ ] Instructions focus on: Modal setup → Deploy → Playground → Traces
- [ ] Slack documented as optional bonus section
- [ ] Prerequisites updated (Modal required, Slack optional)
- [ ] Time estimate updated to ~15 minutes
- [ ] Spec, Impact, TDR updated to reflect simplified approach

**Dependencies**: Task 1  
**Owner**: Documentation team

---

### Task 3: End-to-End Verification

**Definition of Done**:
- [ ] Fresh Modal deployment completed
- [ ] Health endpoint returns 200 OK
- [ ] Weave Playground connects to Modal URL
- [ ] Chat with agent via Playground → receives responses
- [ ] Conversation appears in Weave traces
- [ ] All acceptance criteria from spec.md verified
- [ ] Sign-off from spec author

**Dependencies**: Task 2  
**Owner**: QA / Implementation team

---

**Total Estimated Time**: 1 day (mostly documentation)

**Critical Path**: Tasks 1 → 2 → 3 (sequential)

---

**Approval Gate**: Do not start coding until this TDR is reviewed and approved in the PR.
