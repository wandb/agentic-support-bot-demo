# Impact Analysis — Production Deployment

## Modules/packages likely touched

### Existing Files Modified:
- `examples/step-2/part-b/playground_server.py` 
  - **Change**: Rename to `examples/step-5/server.py`
  - **Additions**: Add Slack webhook endpoints, Modal deployment decorators, health check
  - **Impact**: No breaking changes to existing OpenAI-compatible endpoint

### New Files Created:
- `examples/step-5/server.py`
  - Extended version of playground_server.py with Slack support and Modal deployment
  - Handles both Weave Playground endpoint and Slack webhooks

### Dependencies to Add (pyproject.toml):
- `modal` - Cloud deployment platform
- `slack-bolt` - Slack bot SDK for webhook handling

### Configuration Files:
- No changes to `tyler-chat-config.yaml` - reused as-is
- No changes to `.env` - Modal secrets system used instead

### Documentation:
- `README.md` - Add Step 5 section with deployment instructions
- Update prerequisites to mention Modal account (free tier)

## Contracts to update (APIs, events, schemas, migrations)

### New API Endpoints (server.py):

**POST /slack/events** (New)
- **Purpose**: Slack event webhook receiver
- **Request**: Slack event payload (JSON)
  ```json
  {
    "type": "event_callback",
    "event": {
      "type": "app_mention",
      "user": "U123456",
      "text": "@bot help me",
      "channel": "C123456",
      "ts": "1234567890.123456"
    }
  }
  ```
- **Response**: 200 OK (acknowledges receipt)
- **Authentication**: Slack signing secret verification
- **Side effects**: Async response posted to Slack thread

**GET /health** (New)
- **Purpose**: Health check for Modal deployment
- **Response**: `{"status": "healthy"}`
- **Authentication**: None (public)

**POST /v1/chat/completions** (Existing - No Changes)
- Keeps existing OpenAI-compatible format
- Still used by Weave Playground
- API key authentication unchanged

### Slack Integration Events:
- **app_mention**: When bot is @ mentioned in a channel
- **message**: Direct messages to bot (optional)

### No Schema/Migration Changes:
- No database involved (ephemeral conversations)
- Weave traces are the source of truth for conversation history
- No data models to migrate

## Risks

### Security:
- **Public Internet Exposure**: 
  - Server deployed to public Modal URL
  - **Mitigation**: API key authentication on /v1/chat/completions endpoint
  - **Mitigation**: Slack signing secret verification on /slack/events
  - **Mitigation**: Modal secrets for sensitive credentials (never in code)
  
- **API Key Leakage**:
  - WANDB_API_KEY and PLAYGROUND_API_KEY in Modal secrets
  - **Mitigation**: Clear documentation on setting secrets properly
  - **Mitigation**: Never log or expose secrets in responses
  
- **Unauthorized LLM Usage**:
  - Someone could spam the bot and incur W&B Inference costs
  - **Mitigation**: API key required for non-Slack endpoints
  - **Mitigation**: Slack webhook verified with signing secret
  - **Mitigation**: Modal free tier limits resource usage
  - **Note**: This is a demo, not hardened for production abuse

### Performance/Availability:
- **Modal Cold Starts**: 
  - First request after idle may be slow (5-10 seconds)
  - **Impact**: User may see delayed first response in Slack
  - **Mitigation**: Document this behavior, note Modal warm containers help after first request
  
- **Slack 3-second Timeout**:
  - Slack expects acknowledgment within 3 seconds
  - Agent responses may take longer (LLM calls, tool execution)
  - **Mitigation**: Acknowledge immediately, respond asynchronously via chat.postMessage API
  
- **LLM API Timeouts**:
  - W&B Inference or other LLM APIs may timeout
  - **Mitigation**: Catch exceptions, send error message to Slack
  - **Mitigation**: Weave traces show failures for debugging

### Data Integrity:
- **No Conversation Persistence**:
  - Conversations not stored in database
  - Each @ mention is independent (stateless)
  - **Impact**: No multi-turn conversation context
  - **Mitigation**: This is acceptable for demo. Weave traces provide full conversation history
  
- **Concurrent Requests**:
  - Multiple users could @ mention bot simultaneously
  - **Impact**: Minimal - each request is independent
  - **Mitigation**: Stateless agent design handles this naturally
  
- **Config Drift**:
  - Production uses tyler-chat-config.yaml from workspace
  - Local changes don't auto-deploy
  - **Impact**: User must manually redeploy after config changes
  - **Mitigation**: Document that config changes require `modal deploy workspace/server.py` to update

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
  
- **Slack Delivery Logs**:
  - Slack API errors logged to Modal
  - **Use**: Debug webhook delivery issues

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


