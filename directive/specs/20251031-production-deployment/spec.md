# Spec (per PR)

**Feature name**: Step 5: Production Deployment  
**One-line summary**: Deploy the support bot to Modal cloud platform, enabling production monitoring with Weave  
**Date**: 2025-11-03

---

## Problem

Users have built and evaluated their agent locally, but they haven't experienced Weave's production observability capabilities. Without a real cloud deployment:
- Users can't experience the full dev→production workflow
- No production traces to monitor (needed for Step 6)
- Missing the key insight that Weave works identically in development and production
- Can't demonstrate monitoring, feedback collection, and continuous improvement

The deployment needs to be:
- Simple enough to complete in ~15 minutes
- Actually deployed to the cloud (not just local with ngrok)
- Cheap/free to run
- No complex third-party integrations that could block users

## Goal

Deploy the agent to Modal cloud platform and use Weave Playground to generate production traffic. Users will experience the same agent running in the cloud and see that Weave traces work identically in production.

## Success Criteria

- [ ] Users can deploy their agent to Modal in under 15 minutes
- [ ] Users can connect Weave Playground to production Modal deployment
- [ ] Users can chat with production agent via Weave Playground
- [ ] Production conversations appear in Weave Traces automatically
- [ ] Same agent config from workspace works in production without changes
- [ ] Setup runs on Modal's free tier (no paid accounts required)
- [ ] Deployment stays up even when user's laptop is closed

## User Story

As a developer who has built and evaluated an agent locally, I want to deploy it to production and see real usage in Weave, so that I can experience the full development lifecycle and set up production monitoring.

## Flow / States

**Happy Path:**
1. User completes Step 4 (has evaluated agent)
2. User creates free Modal account at modal.com
3. User configures Modal secrets:
   - `WANDB_API_KEY`
   - `PLAYGROUND_API_KEY`
4. User deploys server: `modal deploy workspace/server.py`
5. User gets Modal deployment URL from `modal app list`
6. User tests health endpoint: `curl https://modal-url/health`
7. User configures Weave Playground with Modal URL as custom provider
8. User chats with production agent in Weave Playground
9. User sees production conversation trace in Weave
10. User continues to Step 6 (monitoring and feedback)

**Edge Cases:**
- **Modal deployment fails**: Check Modal logs, verify secrets are set
- **Health endpoint fails**: Verify deployment is running with `modal app list`
- **Playground can't connect**: Check URL format, verify API key matches
- **Agent errors**: Check Weave traces for errors, review Modal logs

**Optional Bonus (Slack Integration):**
- User can optionally set up Slack bot for additional production traffic
- Requires Slack app creation, webhook configuration
- Same server supports both Playground and Slack
- Documented as bonus/advanced section

## UX Links

- Modal Documentation: https://modal.com/docs
- Weave Playground: https://docs.wandb.ai/weave/playground
- Modal Secrets: https://modal.com/docs/guide/secrets

## Requirements

**Must:**
- Deploy to Modal (cloud service, not local)
- Use unified `server.py` from Step 2 (works locally and on Modal)
- Reuse same `tyler-chat-config.yaml` from workspace
- Work on Modal's free tier
- Support OpenAI-compatible endpoint for Weave Playground
- Automatically trace all production conversations to Weave
- Provide clear README instructions for Modal deployment
- Health check endpoint for deployment verification

**Must not:**
- Require paid accounts or credit cards
- Change the agent configuration between development and production
- Require Slack or other third-party services for main path
- Create complexity that blocks users from reaching Step 6

**Should:**
- Keep Slack integration code in server (optional, gracefully skipped if not configured)
- Document Slack setup as bonus/advanced option
- Make deployment fast (<15 minutes)

## Acceptance Criteria

### Modal Deployment
- **Given** a user has a Modal account with secrets configured
- **When** they run `modal deploy workspace/server.py`
- **Then** the server deploys successfully and returns a public URL

### Health Check Works
- **Given** the server is deployed to Modal
- **When** the user accesses the `/health` endpoint
- **Then** they receive a healthy status with timestamp
- **And** can confirm the deployment is running

### Weave Playground Connection
- **Given** the server is deployed to Modal
- **When** a user configures Weave Playground with the Modal URL + API key
- **Then** they can chat with the production deployment via Playground UI
- **And** the agent responds correctly

### Production Conversation
- **Given** Weave Playground is connected to Modal deployment
- **When** a user sends a message: "How do I initialize Weave?"
- **Then** the agent responds with relevant answer
- **And** the conversation appears in Weave Traces

### Same Configuration Works
- **Given** a user has `workspace/tyler-chat-config.yaml` working locally
- **When** they deploy to Modal with the same config
- **Then** the agent behaves identically in production
- **And** no config changes are needed

### Production Traces Visible
- **Given** a user has chatted with production bot via Playground
- **When** they navigate to Weave Traces
- **Then** they can see production conversations
- **And** traces include full conversation context, tool calls, and timing
- **And** traces show the same detail as local development

### Deployment Persistence
- **Given** the user closes their laptop
- **When** they open it again later
- **Then** the Modal deployment is still running
- **And** they can still chat with the agent via Playground

### Environment Tagging
- **Given** the user chats with the production agent via Playground
- **When** they view the trace in Weave
- **Then** the trace includes an `env: production` attribute
- **And** they can filter traces by environment in Weave UI

## Non-Goals

- Autoscaling or handling high traffic (this is a demo)
- CI/CD pipelines or automated deployments
- Multiple environments (staging, production)
- Database persistence for conversation history
- Custom domain setup
- Production hardening (rate limiting, DDoS protection, etc.)
- Cost optimization beyond using free tier
- Custom chat UI (Weave Playground is sufficient)
- Slack integration as required path (bonus only)

## Technical Notes

### Server Architecture
The `server.py` (unified from Step 2) handles:
1. **OpenAI-compatible endpoint** (core)
   - POST /v1/chat/completions
   - Used by Weave Playground (local in Step 2, production in Step 5)
   - Requires PLAYGROUND_API_KEY authentication
2. **Health check** (core)
   - GET /health
   - For Modal deployment verification
   - Returns {"status": "healthy", "timestamp": "..."}
3. **Slack webhook endpoint** (optional bonus)
   - POST /slack/events
   - Only activates if SLACK_BOT_TOKEN is configured
   - Gracefully skipped if not configured

### Modal Secrets Required
**Core (required):**
- `WANDB_API_KEY` - For Weave tracing and LLM API
- `PLAYGROUND_API_KEY` - For OpenAI endpoint authentication

**Optional (for Slack bonus):**
- `SLACK_BOT_TOKEN` - For Slack bot API calls
- `SLACK_SIGNING_SECRET` - For Slack webhook verification

### Weave Attributes for Environment Tagging
All agent calls are automatically tagged with metadata using `weave.attributes()`:
- **Local calls**: `{'env': 'local'}` - When running with ngrok
- **Production calls**: `{'env': 'production'}` - When running on Modal
- **Slack calls** (bonus): `{'env': 'production', 'channel': 'slack'}`

This enables filtering in Weave UI:
- Filter by `env = production` to see only production traffic
- Filter by `env = local` to see only development traces
- Compare metrics across environments

### Deployment Flow

**Main Path (15 minutes):**
1. User has `server.py` in workspace from Step 2
2. User creates Modal account at modal.com (free tier)
3. User authenticates Modal: `modal setup`
4. User sets Modal secrets:
   ```bash
   modal secret create wandb-secrets \
     WANDB_API_KEY=... \
     PLAYGROUND_API_KEY=...
   ```
5. User deploys: `modal deploy workspace/server.py`
6. User gets Modal URL: `modal app list`
7. User tests health: `curl https://modal-url/health`
8. User connects Weave Playground to Modal URL
9. User chats with production agent in Playground
10. User sees production traces in Weave (tagged with `env: production`)
11. User continues to Step 6 (monitoring)

**Note**: Modal is already in project dependencies from Step 1 (`uv sync`).

**Optional Slack Bonus:**
- User can add Slack secrets and configure webhook
- Enables @ mentions in Slack channels
- Same server supports both Playground and Slack

### File Structure
```
examples/step-2/part-b/
└── server.py              # Unified server (works locally + Modal + Slack)
                           # Copied to workspace in Step 2, deployed to Modal in Step 5
```

## Open Questions

1. **Should we include Slack integration instructions in Step 5?**
   - **Answer**: No - make it optional bonus. Focus on Modal + Playground for main path
   - Keeps Step 5 simple and removes potential blocker
   - Users can still set up Slack if desired

2. **Is Weave Playground sufficient for generating production traffic?**
   - **Answer**: Yes - production traces are identical whether from Playground or Slack
   - Playground is already familiar from Step 2
   - Monitoring in Step 6 works the same regardless of traffic source

3. **Should we warm Modal containers to avoid cold starts?**
   - **Answer**: No - document cold starts as expected behavior
   - Free tier limitation, acceptable for demo purposes


