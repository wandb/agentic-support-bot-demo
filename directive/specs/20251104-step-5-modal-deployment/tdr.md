# Technical Design Review (TDR) — Modal-Based Server Deployment

**Author**: AI Assistant  
**Date**: 2025-11-04  
**Links**: 
- Spec: `/directive/specs/step-5-modal-deployment/spec.md`
- Impact: `/directive/specs/step-5-modal-deployment/impact.md`

---

## 1. Summary

We are replacing ngrok-based tunneling with Modal deployment for the Tyler playground server, introducing this change in Step 2 Part B and making production deployment trivial in Step 5. Users will run `modal serve` for local development (with auto-reload) and `modal deploy` for persistent production deployment—same code, same configuration, just different Modal commands.

This simplifies the tutorial by eliminating ngrok account setup, provides better observability through persistent logs, and creates a clear mental model: development and production are just different deployment modes of the same server. We're also consolidating all runtime files (config, tools, database) into the `workspace/` directory for a single Modal mount point, and adding environment tagging (`env=dev` or `env=prod`) to all Weave traces.

## 2. Decision Drivers & Non‑Goals

**Drivers:**
- **Simplicity**: Tutorial should be as simple as possible for first-time users
- **Free tier**: Must work on Modal's free tier (no paid features required)
- **Single file**: Same `server.py` works for both dev and prod deployment
- **Observability**: Weave traces must work identically in both environments
- **Just-in-time learning**: Introduce Modal in Step 2B when needed, not earlier

**Non‑Goals:**
- Slack bot integration (future Step 6)
- Advanced Modal features (volumes, GPUs, scheduled tasks)
- Custom domains or complex networking
- High-availability production configuration
- Backwards compatibility with ngrok setup

## 3. Current State — Codebase Map (concise)

**Key modules:**
- `examples/step-2/part-b/playground_server.py` (445 lines) - Current ngrok-based server
- `examples/step-2/part-b/tools.py` - Support ticket tools (creates/retrieves tickets)
- `examples/step-2/part-b/tyler-chat-config.yaml` - Tyler agent configuration
- `db/tickets.json` - TinyDB database for support tickets (currently at root)

**External contracts:**
- OpenAI-compatible `/v1/chat/completions` endpoint (used by Weave Playground)
- `/health` endpoint for status checks
- MCP server for W&B documentation search (configured in tyler-chat-config.yaml)

**Current deployment:**
- `uvicorn` runs FastAPI server locally on port 8000
- `ngrok` creates tunnel with authtoken from `.env`
- Users configure Weave Playground with ngrok URL
- Agent loads from workspace, db from `db/tickets.json` at root

**Observability:**
- Weave traces all agent interactions automatically
- Python logging to stdout (captured by uvicorn)
- No persistence of logs (lost when server stops)

## 4. Proposed Design (high level, implementation‑agnostic)

### Overall Architecture

```
User runs: modal serve workspace/server.py
    ↓
Modal:
  1. Builds image (Python 3.12 + dependencies from pyproject.toml)
  2. Mounts workspace/ directory into container
  3. Loads secrets (WANDB_API_KEY, PLAYGROUND_API_KEY) as env vars
  4. Starts FastAPI app
  5. Provides public HTTPS URL
    ↓
Server startup:
  1. Detect environment (modal.is_local() → dev vs prod)
  2. Initialize Weave with env attribute
  3. Load Tyler agent from workspace/tyler-chat-config.yaml
  4. Connect to MCP servers
  5. Verify Modal secrets are set
    ↓
Request flow (unchanged):
  POST /v1/chat/completions
    → verify API key
    → convert messages to Tyler thread
    → stream agent response
    → SSE format back to client
```

### Component Responsibilities

**Modal App Definition:**
- Define app name: `agentic-support-bot`
- Mount workspace directory at `/workspace` in container
- Load secrets from Modal secret store
- Configure FastAPI app with ASGI handler

**Environment Detection:**
- Use `modal.is_local()` to detect dev vs prod
- Set `ENV` variable for logging and Weave tagging
- Log detected environment at startup

**Weave Integration:**
- Initialize Weave in `load_agent()` before agent creation
- Set environment attribute on Weave client: `weave.init(project, attributes={"env": env})`
- All traces automatically tagged with environment

**File Access:**
- All files accessed relative to `/workspace` mount point
- Tyler config: `/workspace/tyler-chat-config.yaml`
- Tools: `/workspace/tools.py`
- Database: `/workspace/db/tickets.json`

**Error Handling:**
- Fail fast at startup if required secrets missing
- Log clear error messages with remediation steps
- Health endpoint returns deployment status

### Data Contracts

**Modal Secrets (required):**
```
wandb-secrets:
  WANDB_API_KEY: <user's W&B API key>
  PLAYGROUND_API_KEY: <user's chosen API key for auth>
```

**Weave Trace Attributes (new):**
```json
{
  "env": "dev" | "prod"
}
```

**File Paths (changed):**
- Before: `db/tickets.json` (root level)
- After: `workspace/db/tickets.json` (inside workspace)

## 5. Alternatives Considered

### Option A: Keep ngrok, add Modal for Step 5 only
**Pros:** Less change to existing tutorial
**Cons:** Users learn ngrok only to throw it away; duplicate documentation; confusing mental model

### Option B: Multiple server files (dev vs prod)
**Pros:** Clearer separation of concerns
**Cons:** Code duplication; harder to maintain; users must manage multiple files

### Option C: Use Modal Volumes for database
**Pros:** Persistent storage across deployments
**Cons:** Over-engineered for demo; requires understanding Modal volumes; free tier limitations

### **Chosen: Single server file with Modal from Step 2B**
**Pros:** 
- Simplest mental model (one file, two commands)
- No ngrok complexity
- Clear dev→prod path
- Better logging and observability
- Free tier friendly

**Cons:**
- Breaking change for existing users (acceptable - main branch update)
- Requires Modal account (still simpler than ngrok)

## 6. Data Model & Contract Changes

### Database Location Change

**Migration required:**
```bash
# Old location
db/tickets.json

# New location  
workspace/db/tickets.json

# Migration command
mkdir -p workspace/db && mv db/tickets.json workspace/db/tickets.json
```

**Tools.py update:**
```python
# Old
DB_PATH = "db/tickets.json"

# New
DB_PATH = "workspace/db/tickets.json"
```

### API Contracts (unchanged)

**OpenAI-compatible endpoint:**
```
POST /v1/chat/completions
Authorization: Bearer <PLAYGROUND_API_KEY>

Request: { model, messages, stream?, temperature?, max_tokens? }
Response: SSE stream or JSON (unchanged)
```

**Health endpoint:**
```
GET /health

Response: { status: "ok", agent_name, model }
```

### Backward Compatibility

**Breaking changes:**
- ngrok removed entirely (no backwards compatibility)
- Database path changes (migration required)
- Modal required (new dependency)

**Deprecation plan:**
- Update main branch (no version tagging needed for tutorial)
- Add migration notes to README changelog section
- Keep `db/tickets.sample.json` at root as reference

## 7. Security, Privacy, Compliance

### Authentication & Authorization

**No changes to API auth:**
- PLAYGROUND_API_KEY still required via Bearer token
- Verified on every `/v1/chat/completions` request
- 401 if missing or invalid

**Modal secrets storage:**
- Secrets stored encrypted in Modal secret store
- Injected as environment variables at runtime
- More secure than `.env` files (which could be committed)

### Secrets Management

**Required secrets:**
```bash
modal secret create wandb-secrets \
  WANDB_API_KEY=xxx \
  PLAYGROUND_API_KEY=xxx
```

**Secret validation at startup:**
```python
# Fail fast if missing
required_secrets = ["WANDB_API_KEY", "PLAYGROUND_API_KEY"]
for secret in required_secrets:
    if not os.getenv(secret):
        raise ValueError(f"Missing required secret: {secret}")
```

### Threat Model

**Public URL exposure:**
- Modal provides public HTTPS URLs (like ngrok)
- Mitigated by PLAYGROUND_API_KEY requirement
- Free tier rate limits prevent abuse
- Can delete deployment anytime

**Data privacy:**
- TinyDB stores tickets in workspace (ephemeral on Modal)
- No PII in demo data (synthetic tickets)
- Weave traces may contain user queries (expected for observability)

## 8. Observability & Operations

### Logging Enhancements

**Startup logging:**
```python
logger.info(f"🚀 Modal environment: {env}")
logger.info(f"📊 Weave initialized: project={project}, env={env}")
logger.info(f"🤖 Agent loaded: {agent_name} ({model_name})")
logger.info(f"✅ All systems ready")
```

**Error logging:**
```python
# Clear remediation steps
logger.error("❌ Missing WANDB_API_KEY")
logger.error("Run: modal secret create wandb-secrets WANDB_API_KEY=xxx")
```

### Metrics & Traces

**Weave traces (enhanced):**
- All traces include `env` attribute
- Filterable in Weave UI: `env=dev` or `env=prod`
- Token usage, latency, tool calls tracked identically

**Modal metrics (automatic):**
- Request count per deployment
- Cold start latency
- Container restarts
- Available in Modal dashboard

### Dashboards & Alerts

**No automated alerts needed (tutorial/demo context)**

**Manual monitoring:**
- Modal dashboard: Deployment status, logs, metrics
- Weave UI: Trace quality, token costs, tool usage
- Health endpoint: Smoke test availability

### Runbooks

**Common operations:**

1. **View logs:**
   ```bash
   modal app logs agentic-support-bot
   ```

2. **Redeploy after config change:**
   ```bash
   # Development (auto-reloads)
   modal serve workspace/server.py
   
   # Production
   modal deploy workspace/server.py --name agentic-support-bot
   ```

3. **Update secrets:**
   ```bash
   modal secret create wandb-secrets WANDB_API_KEY=new_key --force
   ```

4. **Delete deployment:**
   ```bash
   modal app stop agentic-support-bot
   ```

## 9. Rollout & Migration

### Feature Flags

None needed - clean cut-over on main branch update.

### Migration Path

**For existing users mid-tutorial:**

1. **Backup workspace:**
   ```bash
   cp -r workspace workspace.backup
   ```

2. **Install Modal:**
   ```bash
   uv sync  # Gets updated dependencies
   ```

3. **Move database:**
   ```bash
   mkdir -p workspace/db
   mv db/tickets.json workspace/db/tickets.json
   ```

4. **Authenticate Modal:**
   ```bash
   modal setup
   ```

5. **Create secrets:**
   ```bash
   modal secret create wandb-secrets \
     WANDB_API_KEY=$WANDB_API_KEY \
     PLAYGROUND_API_KEY=$PLAYGROUND_API_KEY
   ```

6. **Test:**
   ```bash
   modal serve workspace/server.py
   ```

### Revert Plan

**If Modal deployment fails catastrophically:**

1. Checkout previous commit with ngrok setup
2. Users can finish tutorial on old branch
3. No data loss (workspace is gitignored, users have local copies)

**Blast radius:** Low - tutorial users, not production system

## 10. Test Strategy & Spec Coverage (TDD)

### TDD Commitment

- Write failing tests first for each acceptance criterion
- Confirm failure with assertions
- Implement minimal code to pass
- Refactor while keeping tests green

### Spec→Test Mapping

| Acceptance Criterion | Test ID | Type |
|---------------------|---------|------|
| Modal setup succeeds and stores secrets | `test_modal_secrets_required` | Unit |
| `modal serve` mounts workspace and provides URL | `test_workspace_mount` | Unit |
| Agent can access config, tools, db from workspace | `test_file_access_from_workspace` | Unit |
| Weave traces include `env=dev` attribute | `test_weave_env_attribute_dev` | Unit |
| Weave traces include `env=prod` attribute | `test_weave_env_attribute_prod` | Unit |
| Playground integration works with Modal URL | `test_chat_completions_endpoint` | Integration |
| Environment filtering works in Weave UI | Manual verification | Manual |
| Production deployment creates stable URL | `test_modal_deploy_url` | Unit |
| Config updates reflect in redeployment | Manual verification | Manual |
| Missing secrets fail at startup with clear error | `test_missing_secrets_fail_fast` | Unit |
| Invalid config fails gracefully | `test_invalid_config_error_message` | Unit |

### Test Tiers

**Unit tests (fast, isolated):**
- Environment detection logic
- Weave attribute setting
- Secret validation
- File path resolution
- Error message generation

**Integration tests (no Modal deployment):**
- FastAPI endpoint responses
- Agent loading from config
- Tyler thread conversion
- SSE serialization
- API key verification

**NO Modal integration tests:**
- Too slow for CI
- Requires Modal account
- Manual verification sufficient for tutorial

### Negative & Edge Cases

| Scenario | Expected Behavior | Test |
|----------|-------------------|------|
| WANDB_API_KEY missing | Fail at startup with clear error | `test_missing_wandb_key` |
| PLAYGROUND_API_KEY missing | Fail at startup with clear error | `test_missing_playground_key` |
| Invalid tyler-chat-config.yaml | Fail at startup with YAML parse error | `test_invalid_yaml` |
| workspace/db/tickets.json missing | TinyDB creates new empty file | `test_missing_db_creates_new` |
| Modal secrets wrong format | Fail at startup with format error | `test_malformed_secrets` |
| Request without auth header | 401 Unauthorized | `test_missing_auth_header` |
| Request with wrong API key | 401 Invalid API key | `test_wrong_api_key` |

### Performance Tests

**Not needed for tutorial** - Modal handles scaling automatically.

**Manual verification:**
- Cold start < 3 seconds (acceptable for demo)
- Request latency similar to ngrok setup
- No degradation with multiple requests

### CI Requirements

**All tests must:**
- Run in CI (GitHub Actions or equivalent)
- Pass before merge
- Complete in < 2 minutes
- Not require Modal account (unit tests only)

## 11. Risks & Open Questions

### Known Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Modal free tier limits | Users hit concurrency limits | Document limits; each user has own quota |
| Cold starts on free tier | 1-3s delay on first request | Document expected behavior; acceptable for tutorial |
| Database resets on redeploy | Support tickets lost | Document as expected; this is a demo database |
| Multiple containers race to write db | Data corruption possible | Single container sufficient for demo traffic; document limitation |
| Breaking change for mid-tutorial users | Users must migrate manually | Provide clear migration guide; acceptable for main branch update |

### Mitigation Strategies

1. **Free tier limits:**
   - Each user creates their own Modal account
   - Limits are per-account, not shared
   - Tutorial usage well within free tier

2. **Cold starts:**
   - Document in README as expected behavior
   - Production deployments stay warmer than dev
   - 1-3s is acceptable for demo

3. **Database persistence:**
   - Clearly document that db resets on redeploy
   - Provide `tickets.sample.json` to repopulate
   - For real production, users would use external DB

4. **Concurrent writes:**
   - Acceptable for tutorial (low traffic)
   - TinyDB has file locking for single-container safety
   - Document as limitation if using at scale

### Open Questions

✅ **Resolved:**
- ~~Modal app name?~~ → `agentic-support-bot`
- ~~Environment detection method?~~ → `modal.is_local()`
- ~~Workspace mount path?~~ → Whatever works, user runs from root
- ~~Modal image strategy?~~ → Default Python + pyproject.toml (simplest)
- ~~Error handling for missing secrets?~~ → Fail at startup
- ~~Test strategy?~~ → Unit tests only, no Modal integration tests

**No remaining open questions.**

## 12. Milestones / Plan (post‑approval)

### Phase 1: Dependencies & Database Migration

**Task 1.1: Update pyproject.toml**
- Add `modal` dependency
- Upgrade `slide-tyler>=5.2.0`, `slide-lye>=5.2.0`
- Upgrade `weave` to latest
- Remove `ngrok>=1.4.0`
- Run `uv sync` and verify lockfile
- **DoD:** Dependencies install cleanly, all existing tests pass

**Task 1.2: Move database to workspace**
- Delete `db/tickets.json` (no longer needed)
- Update `.gitignore` to ignore `workspace/db/`
- Update `examples/step-2/part-b/tools.py`: `db/tickets.json` → `workspace/db/tickets.json`
- Update README Step 1: document new db setup command
- **DoD:** Tests pass with new db path, gitignore correct

### Phase 2: Modal Server Implementation

**Task 2.1: Create Modal server file**
- Rename `examples/step-2/part-b/playground_server.py` → `server.py`
- Add Modal app definition and configuration
- Add workspace mount
- Add environment detection
- Remove ngrok code
- **DoD:** Server file has Modal structure, imports work

**Task 2.2: Implement environment tagging**
- Detect environment using `modal.is_local()`
- Pass environment to Weave initialization
- Add startup logging for environment
- Verify secret validation at startup
- **DoD:** Tests pass for environment detection and Weave attributes

**Task 2.3: Update file paths for workspace mount**
- Update config loading to use workspace paths
- Update tools loading to use workspace paths
- Update db path in tools.py
- Test all file access patterns
- **DoD:** All files accessible from workspace mount, tests pass

### Phase 3: Testing

**Task 3.1: Write unit tests**
- Environment detection tests
- Secret validation tests
- Weave attribute tests
- File path resolution tests
- Error message tests
- **DoD:** All acceptance criteria covered, tests pass, >80% coverage

**Task 3.2: Update existing tests**
- Rename `tests/test_playground_server.py` → `test_server.py`
- Update imports and paths
- Mock Modal decorators where needed
- Ensure all tests still pass
- **DoD:** Full test suite passes, no broken tests

### Phase 4: Documentation

**Task 4.1: Update README Step 2 Part B**
- Remove ngrok prerequisites and setup
- Add Modal setup instructions
- Document `modal setup` authentication
- Document secret creation
- Document `modal serve` workflow
- Update test prompts section
- **DoD:** Step 2B documentation complete and accurate

**Task 4.2: Update README Step 5**
- Replace "COMING SOON" with production deployment guide
- Document `modal deploy` workflow
- Explain dev vs prod differences
- Show how to update deployments
- Add troubleshooting section
- **DoD:** Step 5 documentation complete and accurate

**Task 4.3: Update README Step 1**
- Remove ngrok from prerequisites
- Add Modal to prerequisites
- Update db setup command
- Update `.env.example` (remove NGROK_AUTHTOKEN)
- **DoD:** Step 1 prerequisites accurate

### Phase 5: Validation

**Task 5.1: Manual end-to-end test**
- Fresh checkout of repo
- Follow Step 1 setup
- Follow Step 2 Part B with Modal
- Verify Weave Playground integration
- Verify traces have `env=dev`
- **DoD:** Tutorial works end-to-end for new user

**Task 5.2: Production deployment test**
- Run `modal deploy`
- Verify stable URL
- Update Weave Playground with prod URL
- Verify traces have `env=prod`
- Verify environment filtering in Weave
- **DoD:** Production deployment works, environment tagging verified

### Dependencies

- No external team dependencies
- All work can be done independently
- Modal account needed for manual testing (free tier)

---

**Approval Gate**: Do not start coding until this TDR is reviewed and approved.

