# Spec (per PR)

**Feature name**: Step 5: Production Deployment  
**One-line summary**: Deploy the support bot to Modal as a Slack bot, enabling production monitoring with Weave  
**Date**: 2025-10-31

---

## Problem

Users have built and evaluated their agent locally, but they haven't experienced Weave's production observability capabilities. Without a real cloud deployment:
- Users can't experience the full dev→production workflow
- No production traces to monitor (needed for Step 6)
- Missing the key insight that Weave works identically in development and production
- Can't demonstrate monitoring, feedback collection, and continuous improvement

The deployment needs to be:
- Simple enough to complete in ~20-30 minutes
- Actually deployed to the cloud (not just local with ngrok)
- Cheap/free to run
- Realistic for a support bot use case

## Goal

Deploy the agent to Modal as a Slack bot. Users will see their agent handling real production traffic in a Slack workspace and experience Weave's automatic production tracing.

## Success Criteria

- [ ] Users can deploy their agent to Modal as a Slack bot in under 30 minutes
- [ ] Users can @ mention the bot in Slack channels and get responses
- [ ] Production conversations appear in Weave Traces automatically
- [ ] Same agent config from workspace works in production without changes
- [ ] Server uses Slack signing secret for webhook authentication
- [ ] Setup runs on Modal's free tier (no paid accounts required)
- [ ] Bot responds asynchronously to avoid Slack's 3-second timeout

## User Story

As a developer who has built and evaluated an agent locally, I want to deploy it to production and see real usage in Weave, so that I can experience the full development lifecycle and set up production monitoring.

## Flow / States

**Happy Path:**
1. User completes Step 4 (has evaluated agent)
2. User creates free Modal account at modal.com
3. User creates free Slack workspace (or uses existing) at slack.com
4. User creates Slack app and gets credentials (bot token, signing secret)
5. User configures Modal secrets:
   - `WANDB_API_KEY`
   - `SLACK_BOT_TOKEN`
   - `SLACK_SIGNING_SECRET`
6. User deploys server: `modal deploy workspace/server.py`
7. User gets Modal deployment URL
8. User configures Slack webhook URL to point to Modal deployment
9. User installs Slack app to workspace
10. User @ mentions bot in Slack channel: "@buzz help me with Weave"
11. Bot responds in Slack thread with answer
12. User sees conversation trace in Weave with full context
13. User continues to Step 6 (monitoring and feedback)

**Edge Cases:**
- **Modal deployment fails**: Check Modal logs, verify secrets are set
- **Slack webhook fails**: Verify signing secret, check Modal URL is correct
- **Bot doesn't respond**: Check Weave traces for errors, verify Modal deployment is running

## UX Links

- Modal Documentation: https://modal.com/docs
- Slack Bolt SDK: https://slack.dev/bolt-python/
- Slack API: Creating Apps: https://api.slack.com/start

## Requirements

**Must:**
- Deploy to Modal (cloud service, not local)
- Rename `playground_server.py` → `server.py` and extend with Slack endpoints
- Support Slack bot interaction (POST /slack/events endpoint)
- Respond asynchronously to avoid Slack's 3-second timeout
- Reuse same `tyler-chat-config.yaml` from workspace
- Verify Slack requests using signing secret
- Work on Modal's free tier
- Automatically trace all production conversations to Weave
- Provide clear README instructions for Slack app setup
- Keep existing Weave Playground compatibility (POST /v1/chat/completions)

**Must not:**
- Require paid accounts or credit cards
- Change the agent configuration between development and production
- Create separate server files (extend existing playground_server.py)
- Block synchronously waiting for agent response (Slack timeout)

## Acceptance Criteria

### Modal Deployment
- **Given** a user has a Modal account with secrets configured
- **When** they run `modal deploy workspace/server.py`
- **Then** the server deploys successfully and returns a public URL

### Slack Bot Interaction
- **Given** a user has configured Slack app with webhook URL pointing to Modal
- **When** they @ mention the bot in a Slack channel: "@buzz how do I initialize Weave?"
- **Then** the bot responds in the thread within Slack with a relevant answer
- **And** the conversation appears in Weave Traces with full context and tool calls

### Asynchronous Response
- **Given** the agent response takes longer than 3 seconds
- **When** a user @ mentions the bot
- **Then** Slack receives acknowledgment within 3 seconds
- **And** the bot posts the response asynchronously when ready
- **And** no timeout errors occur

### Weave Playground Compatibility
- **Given** the server is deployed to Modal
- **When** a user configures Weave Playground with the Modal URL + API key
- **Then** they can chat with the production deployment via Playground UI
- **And** traces appear in Weave

### Slack Authentication
- **Given** the server receives a Slack webhook request
- **When** the signing secret is verified
- **Then** the request is processed
- **And** requests with invalid signatures are rejected

### Same Configuration Works
- **Given** a user has `workspace/tyler-chat-config.yaml` working locally
- **When** they deploy to Modal with the same config
- **Then** the agent behaves identically in production
- **And** no config changes are needed

### Production Traces Visible
- **Given** a user has sent messages to the production bot
- **When** they navigate to Weave Traces
- **Then** they can filter for production conversations
- **And** traces include full conversation context, tool calls, and timing
- **And** traces are distinguishable from local/playground traces

## Non-Goals

- Autoscaling or handling high traffic (this is a demo)
- CI/CD pipelines or automated deployments
- Multiple environments (staging, production)
- Database persistence for conversation history
- Custom domain setup
- Production hardening (rate limiting, DDoS protection, etc.)
- Cost optimization beyond using free tier
- Discord, Teams, or other messaging platforms (Slack only)
- Alternative chat interfaces (Slack bot only)

## Technical Notes

### Server Architecture
The `server.py` should handle:
1. **OpenAI-compatible endpoint** (existing from playground_server.py)
   - POST /v1/chat/completions
   - Used by Weave Playground
   - Requires PLAYGROUND_API_KEY authentication
2. **Slack webhook endpoint** (new)
   - POST /slack/events
   - Handles Slack events (app_mention, message)
   - Verifies Slack signing secret
   - Acknowledges within 3 seconds
   - Responds asynchronously via chat.postMessage API
3. **Health check** (new)
   - GET /health
   - For Modal deployment verification
   - Returns {"status": "healthy"}

### Modal Secrets Required
- `WANDB_API_KEY` - For Weave tracing and LLM API
- `PLAYGROUND_API_KEY` - For OpenAI endpoint authentication
- `SLACK_BOT_TOKEN` - For Slack bot API calls
- `SLACK_SIGNING_SECRET` - For Slack webhook verification

### Deployment Flow

1. User copies files: `cp examples/step-5/server.py workspace/`
2. User creates Modal account at modal.com (free tier)
3. User creates Slack app at api.slack.com/apps (free)
4. User gets Slack credentials (bot token, signing secret)
5. User sets Modal secrets:
   ```bash
   modal secret create wandb-secrets \
     WANDB_API_KEY=... \
     PLAYGROUND_API_KEY=... \
     SLACK_BOT_TOKEN=... \
     SLACK_SIGNING_SECRET=...
   ```
6. User deploys server: `modal deploy workspace/server.py`
7. User receives Modal deployment URL
8. User configures Slack app Event Subscriptions URL: `https://<modal-url>/slack/events`
9. User installs Slack app to workspace
10. Agent is live - ready to receive @ mentions in Slack
11. Production traces flow to Weave automatically

### File Structure
```
examples/step-5/
├── server.py              # Renamed/extended playground_server with Slack support
└── README.md              # Step 5 deployment instructions (added to main README)
```

## Open Questions

1. **Conversation persistence**: Do we need to persist chat history in a database?
   - **Answer**: No - ephemeral is fine. Weave traces contain full conversation history
   - Keeps implementation simple and focused on observability

2. **Slack rate limiting**: Do we need to handle Slack API rate limiting?
   - **Answer**: Document as limitation. Not expecting high traffic in demo usage
   - Users testing with 1-2 people won't hit limits

3. **Multi-turn conversations**: Should the bot maintain conversation context across messages?
   - **Answer**: Keep stateless for simplicity. Each @ mention is independent
   - Users can include context in their message if needed
   - Future: Could add thread context in Step 6/7 if valuable


