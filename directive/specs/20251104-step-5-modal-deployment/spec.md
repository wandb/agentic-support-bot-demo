# Spec (per PR)

**Feature name**: Modal-Based Server Deployment (Step 2 Part B + Step 5)  
**One-line summary**: Replace ngrok with Modal for both development and production server deployments, simplifying the path from local testing to 24/7 production availability

---

## Problem

Currently, the tutorial uses ngrok to expose the local playground server in Step 2 Part B. This creates unnecessary complexity:
- Users must set up ngrok accounts and auth tokens
- Tunnels are ephemeral and require keeping a local process running
- There's a confusing mental model: "local server" + "tunnel" vs just "deployed server"
- The gap between "development" (Step 2) and "production" (Step 5) feels arbitrary
- Users learn ngrok just to throw it away in Step 5

Modal provides a simpler, unified approach for both development and production deployment.

## Goal

Replace ngrok with Modal for all server deployments from Step 2 Part B onwards, providing a unified development-to-production workflow where `modal serve` is used for local development with auto-reload and `modal deploy` creates persistent production deployments.

## Success Criteria

- [ ] Step 2 Part B uses Modal instead of ngrok (no ngrok setup required)
- [ ] Users can run `modal serve` for local development with auto-reload
- [ ] Users can run `modal deploy` to create a persistent production deployment
- [ ] Both local and production deployments work with Weave Playground
- [ ] Weave traces are captured identically in both environments
- [ ] README Step 2 Part B and Step 5 documentation clearly explain Modal workflow
- [ ] First-time Modal setup (auth + deploy) completes in under 5 minutes
- [ ] ngrok is completely removed from dependencies and documentation

## User Story

**Step 2 Part B**: As a developer building an agent, I want a simple way to expose my local server to Weave Playground, so that I can test my agent interactively without complex tunnel setup.

**Step 5**: As a developer who has built and evaluated a support bot, I want to deploy it to a production environment accessible 24/7, so that I can share it with my team and monitor real-world performance without keeping my laptop running.

## Flow / States

**Step 2 Part B - Happy Path:**
1. User completes Step 2 Part A (has basic agent in CLI)
2. User copies example files: `cp examples/step-2/part-b/*.{py,yaml} workspace/`
3. User ensures db is in workspace: `workspace/db/tickets.json` exists from Step 1 setup
4. User authenticates with Modal: `modal setup`
5. User creates Modal secret: `modal secret create wandb-secrets WANDB_API_KEY=xxx PLAYGROUND_API_KEY=xxx`
6. User runs `modal serve workspace/server.py`
   - Modal mounts workspace directory (all runtime files accessible: config, tools, db)
   - Modal provides HTTPS URL automatically (no ngrok needed)
   - Server auto-reloads when code changes
7. User configures Weave Playground with Modal dev URL and PLAYGROUND_API_KEY
8. User tests agent in Playground, sees traces in Weave
9. User proceeds to Step 3 for iteration (continues using `modal serve`)

**Step 5 - Happy Path:**
1. User completes Step 4 (has working agent with evaluation)
2. User runs `modal deploy workspace/server.py` for production
   - Modal creates persistent deployment with stable URL
   - Same code, same config, just persistent instead of ephemeral
3. User updates Weave Playground with production URL
4. Agent is now accessible 24/7
5. User can still use `modal serve` locally for development

**Edge Case - Missing Secrets:**
1. User runs `modal serve` without creating Modal secrets
2. Server starts but agent initialization fails with clear error about missing WANDB_API_KEY
3. User creates secret: `modal secret create wandb-secrets WANDB_API_KEY=xxx PLAYGROUND_API_KEY=xxx`
4. User restarts `modal serve` successfully

**Edge Case - Workspace Files:**
1. User modifies `tools.py` in workspace to change ticket logic
2. User runs `modal serve` with the changes
3. Modal mounts the updated workspace directory
4. Server auto-reloads and uses the modified tools

## UX Links

- Modal documentation: https://modal.com/docs
- Weave Playground: https://wandb.ai (project → Playground)
- N/A (terminal-based workflow, no UI mockups needed)

## Requirements

**Must:**
- Completely replace ngrok in Step 2 Part B and all subsequent steps
- Support both `modal serve` (development) and `modal deploy` (production) modes in a single server file
- Rename `examples/step-2/part-b/playground_server.py` → `server.py` and add Modal support
- Detect environment and tag Weave traces with `env=dev` for `modal serve` and `env=prod` for `modal deploy`
- Mount workspace directory in Modal (single mount containing all runtime files: config, tools, db)
- Update Step 2 Part B README: Modal setup, authentication, and secrets creation
- Update Step 5 README: Production deployment with `modal deploy`
- Maintain OpenAI-compatible `/v1/chat/completions` endpoint (no breaking changes)
- Preserve all existing Weave observability (traces, tokens, etc.)
- Document Modal authentication and secrets setup in Step 2 Part B (just-in-time learning)
- Keep PLAYGROUND_API_KEY authentication requirement (API key validation)
- Keep the same agent configuration format (`tyler-chat-config.yaml`)
- Update `tools.py` to use `workspace/db/tickets.json` path (consolidates all runtime files in workspace)
- Update README Step 1: Change db setup to `mkdir -p workspace/db && cp db/tickets.sample.json workspace/db/tickets.json`
- Update `pyproject.toml`: add `modal`, upgrade Slide packages to 5.2.0, upgrade Weave to latest, remove ngrok
- Remove all ngrok references from `.env.example` and documentation
- All changes to example files in `examples/step-2/part-b/` (users copy once to workspace, use throughout)

**Must not:**
- Include Slack integration (out of scope for this simplified version)
- Require changes to agent configuration structure
- Break existing Step 2 Part A, Step 3, or Step 4 functionality
- Add complex infrastructure dependencies beyond Modal
- Require paid Modal features (must work on free tier)
- Use complex persistence solutions (Modal volumes, databases) - simple file mounting is sufficient for this demo
- Over-engineer the solution - prioritize simplicity and ease of understanding

## Acceptance Criteria

**Step 2 Part B - Modal Setup:**  
**Given** the user has completed Step 2 Part A and copied example files to workspace,  
**When** they run `modal setup` and create Modal secrets with `modal secret create`,  
**Then** Modal authentication succeeds and secrets are stored securely.

**Step 2 Part B - Development Server:**  
**Given** the user has set up Modal secrets,  
**When** they run `modal serve workspace/server.py`,  
**Then** Modal mounts the workspace directory, provides an HTTPS URL, and the server auto-reloads on code changes.

**Step 2 Part B - File Access:**  
**Given** the Modal dev server is running,  
**When** the agent needs to load `tyler-chat-config.yaml`, `tools.py`, or `workspace/db/tickets.json`,  
**Then** all files are accessible via the mounted workspace directory (single mount point).

**Step 2 Part B - Ticket Operations:**  
**Given** the user has set up `workspace/db/tickets.json` from the sample,  
**When** they create or retrieve tickets via the agent,  
**Then** operations succeed and data persists in `workspace/db/tickets.json`.

**Step 2 Part B - Playground Integration:**  
**Given** the user has `modal serve` running,  
**When** they configure Weave Playground with the Modal dev URL, PLAYGROUND_API_KEY, and send a message,  
**Then** the agent responds correctly and a complete trace appears in Weave with all tool calls, MCP server interactions, and `env=dev` attribute.

**Step 2 Part B - Environment Tagging:**  
**Given** the user has `modal serve` running,  
**When** any agent interaction occurs,  
**Then** Weave traces include the attribute `env=dev` for filtering and analysis.

**Step 5 - Production Deployment:**  
**Given** the user has completed Step 4 and tested with `modal serve`,  
**When** they run `modal deploy workspace/server.py`,  
**Then** Modal creates a persistent deployment with a stable HTTPS URL accessible 24/7.

**Step 5 - Production Testing:**  
**Given** the user has deployed to production,  
**When** they update Weave Playground with the production URL and send messages,  
**Then** the agent behaves identically to local development with all traces captured in Weave and tagged with `env=prod`.

**Step 5 - Environment Filtering:**  
**Given** the user has both dev and prod deployments,  
**When** they view traces in Weave,  
**Then** they can filter by `env=dev` or `env=prod` to separate development from production traffic.

**Configuration Updates:**  
**Given** the user wants to update their deployed agent,  
**When** they modify `tyler-chat-config.yaml` or `tools.py` and re-run `modal deploy`,  
**Then** the production deployment updates with the new configuration within 1 minute.

**Negative Case - Missing Secrets:**  
**Given** the user forgot to set the `WANDB_API_KEY` Modal secret,  
**When** they run `modal serve` or `modal deploy`,  
**Then** the server fails to initialize with a clear error message explaining which secrets are required.

**Negative Case - Invalid Configuration:**  
**Given** the user provides an invalid value in `tyler-chat-config.yaml`,  
**When** the agent tries to initialize,  
**Then** it fails gracefully with a helpful error message (not a cryptic stack trace).

## Non-Goals

- Slack bot integration (future Step 6)
- Other deployment platforms (Kubernetes, Cloud Run, AWS Lambda, etc.)
- Custom domain configuration for Modal endpoints
- Advanced Modal features (scheduled tasks, distributed workloads, GPU support, Modal volumes)
- Production monitoring dashboards (covered in future Step 6)
- Rate limiting beyond Modal's built-in capabilities
- Authentication mechanisms beyond API key validation
- Database migrations or persistent storage beyond `tickets.json` (file resets on redeploy are acceptable for demo)
- Shared state across Modal containers (single container is sufficient for demo traffic)
- Load balancing configuration (Modal handles this automatically)
- CI/CD pipelines for automated deployments (can be added later)
- Backwards compatibility with ngrok (complete replacement)
- Moving `db/tickets.json` location (keep current structure for simplicity)

