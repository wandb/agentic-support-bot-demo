# Impact Analysis — Production Deployment

## Modules/packages likely touched

### Existing Files Modified:
- `examples/step-2/part-b/playground_server.py` 
  - **Change**: Replaced with unified `server.py`
  - **Additions**: Modal deployment decorators, optional Slack support
  - **Impact**: Works locally (Step 2) and on Modal (Step 5) with same code

### New Files Created:
- `examples/step-2/part-b/server.py`
  - Unified server that replaces playground_server.py
  - Works locally with ngrok OR deployed to Modal
  - Handles Weave Playground endpoint (core)
  - Optional Slack webhook support (bonus)

### Dependencies to Add (pyproject.toml):
- `modal` - Cloud deployment platform (required for Step 5)
- `slack-bolt` - Slack bot SDK (optional, for bonus feature)
- `slack-sdk` - Slack API client (optional, for bonus feature)

### Configuration Files:
- No changes to `tyler-chat-config.yaml` - reused as-is
- No changes to `.env` - Modal secrets system used instead

### Documentation:
- `README.md` - Add Step 5 section with deployment instructions
- Update prerequisites to mention Modal account (free tier)

## Contracts to update (APIs, events, schemas, migrations)

### API Endpoints (server.py):

**GET /health** (New)
- **Purpose**: Health check for Modal deployment verification
- **Response**: `{"status": "healthy", "timestamp": "2025-11-03T12:00:00Z"}`
- **Authentication**: None (public)
- **Use**: Verify deployment is running

**POST /v1/chat/completions** (Existing - No Changes)
- **Purpose**: OpenAI-compatible chat endpoint
- **Request/Response**: OpenAI format (unchanged from Step 2)
- **Authentication**: PLAYGROUND_API_KEY (Bearer token)
- **Use**: Weave Playground (local in Step 2, production on Modal in Step 5)

**POST /slack/events** (Optional Bonus)
- **Purpose**: Slack event webhook receiver (if user configures Slack)
- **Activation**: Only if SLACK_BOT_TOKEN is configured
- **Note**: Not required for main Step 5 path

### No Schema/Migration Changes:
- No database involved (ephemeral conversations)
- Weave traces are the source of truth for conversation history
- No data models to migrate

## Risks

### Security:
- **Public Internet Exposure**: 
  - Server deployed to public Modal URL
  - **Mitigation**: API key authentication on /v1/chat/completions endpoint
  - **Mitigation**: Modal secrets for sensitive credentials (never in code)
  - **Impact**: Low risk - only Weave Playground traffic expected
  
- **API Key Leakage**:
  - WANDB_API_KEY and PLAYGROUND_API_KEY in Modal secrets
  - **Mitigation**: Clear documentation on setting secrets properly
  - **Mitigation**: Never log or expose secrets in responses
  
- **Unauthorized LLM Usage**:
  - Someone could discover Modal URL and spam requests
  - **Mitigation**: API key required on /v1/chat/completions
  - **Mitigation**: Modal free tier limits resource usage
  - **Impact**: Low risk for demo purposes (users control API key)

### Performance/Availability:
- **Modal Cold Starts**: 
  - First request after idle may be slow (5-10 seconds)
  - **Impact**: User may see delayed first response in Weave Playground
  - **Mitigation**: Document this behavior, note Modal warm containers help after first request
  
- **LLM API Timeouts**:
  - W&B Inference or other LLM APIs may timeout
  - **Mitigation**: Tyler handles retries internally
  - **Mitigation**: Weave traces show failures for debugging
  - **Impact**: User sees error in Playground, can check traces

### Data Integrity:
- **No Conversation Persistence**:
  - Conversations not stored in database
  - Each Playground conversation is independent (stateless)
  - **Impact**: Weave Playground doesn't persist multi-turn context
  - **Mitigation**: This is acceptable for demo. Weave traces provide full conversation history
  
- **Concurrent Requests**:
  - Multiple users could use Playground simultaneously
  - **Impact**: Minimal - each request is independent
  - **Mitigation**: Stateless agent design handles this naturally
  
- **Config Drift**:
  - Production uses tyler-chat-config.yaml from workspace
  - Local changes don't auto-deploy
  - **Impact**: User must manually redeploy after config changes
  - **Mitigation**: Document that config changes require `modal deploy workspace/server.py`

## Observability needs

### Logs:
- **Modal Application Logs**:
  - `modal app logs <app-name>` - View server logs
  - Includes Python print statements, errors, agent execution
  - **Use**: Debug deployment issues, cold start timing
  
- **Weave Traces** (Primary Observability):
  - All agent conversations automatically traced
  - Tool calls, LLM requests, timing, costs captured
  - **Use**: Monitor production behavior, analyze failures, track performance
  - **Access**: Weave UI → Traces tab
  - **Note**: This is the main learning objective of Step 5

### Metrics:
- **Weave-Provided Metrics**:
  - Latency per conversation (automatic)
  - Token usage per request (automatic)
  - Cost per conversation (automatic)
  - Tool usage frequency (queryable via traces)
  
- **Modal Metrics**:
  - Container invocations
  - Cold start frequency
  - Memory/CPU usage
  - **Access**: Modal dashboard
  
- **Custom Metrics** (Step 6):
  - User feedback (thumbs up/down)
  - Conversation volume over time
  - Error rates by type
  - **Built in**: Step 6 (monitoring dashboard)

### Alerts:
- **No Built-in Alerts** (Step 5):
  - This step focuses on deployment
  - Monitoring/alerting covered in Step 6
  
- **Future Alert Opportunities** (Step 6+):
  - Modal: Email on deployment failures
  - Weave Monitors: Alert on quality degradation
  - Custom: Slack message on high error rate
  
- **Manual Monitoring** (Step 5):
  - Users check Modal logs for errors
  - Users check Weave traces for failures
  - Document where to look when things break


