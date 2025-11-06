# Impact Analysis — Modal-Based Server Deployment (Step 2 Part B + Step 5)

## Modules/packages likely touched

**Core files to modify:**
- `examples/step-2/part-b/playground_server.py` → rename to `server.py` and add Modal decorators/config
  - Single server file works for both `modal serve` (dev) and `modal deploy` (prod)
  - Users copy once in Step 2 Part B, use throughout tutorial
  - Add environment detection: set Weave attribute `env=dev` for serve, `env=prod` for deploy
- `pyproject.toml` → dependencies update:
  - Add `modal` package
  - Upgrade `slide-tyler>=5.2.0`, `slide-lye>=5.2.0`
  - Upgrade `weave` to latest version
  - Remove `ngrok>=1.4.0`
- `.env.example` → remove `NGROK_AUTHTOKEN`
- `README.md` → major updates:
  - Step 1: Remove ngrok prerequisites
  - Step 2 Part B: Replace ngrok setup with Modal setup and secrets
  - Step 5: Add production deployment section (replace "COMING SOON")

**Potentially impacted:**
- `examples/step-2/part-b/tyler-chat-config.yaml` → no changes
- `examples/step-2/part-b/tools.py` → update path from `db/tickets.json` to `workspace/db/tickets.json`
- `db/tickets.sample.json` → stays at root as reference template
- `db/tickets.json` → delete (no longer needed at root level)
- `.gitignore` → ensure `workspace/db/` is gitignored (user data, not committed)
- README Step 1 → update db setup: `mkdir -p workspace/db && cp db/tickets.sample.json workspace/db/tickets.json`

**Test files:**
- `tests/test_playground_server.py` → rename to `test_server.py`, update imports, add Modal-specific tests
- All existing tests should still pass (agent behavior unchanged)

## Contracts to update (APIs, events, schemas, migrations)

**External-facing changes:**
- **Server endpoint URL format changes:**
  - Before: `https://{random-id}.ngrok-free.app/v1` (ngrok tunnel)
  - After (dev): `https://{app-name}--dev.modal.run/v1` (Modal dev)
  - After (prod): `https://{app-name}--{deployment}.modal.run/v1` (Modal prod)
  - Impact: Users must update Weave Playground Base URL when switching between dev/prod
  - Contract: `/v1/chat/completions` endpoint remains unchanged

- **Authentication:**
  - No change to API contract - still uses `Bearer <PLAYGROUND_API_KEY>`
  - Change in configuration: API key now set as Modal secret instead of `.env`

- **Health check endpoint:**
  - No change to `/health` response schema
  - Same for `/` root endpoint

**Internal contracts:**
- **File system access pattern:**
  - Before: Server runs locally, direct filesystem access to both root and workspace
  - After: Server runs on Modal with only workspace directory mounted
  - Impact: All runtime files must be in workspace (`tyler-chat-config.yaml`, `tools.py`, `db/tickets.json`)
  - **Breaking change**: `db/tickets.json` path changes from `db/tickets.json` → `workspace/db/tickets.json`

- **Environment variables:**
  - Before: Loaded from `.env` via `python-dotenv`
  - After: Loaded from Modal secrets (which Modal injects as env vars)
  - Impact: Users must create Modal secrets, but code can still use `os.getenv()`

- **Weave trace attributes (enhancement):**
  - Before: No environment tagging
  - After: All traces include `env` attribute ("dev" or "prod")
  - Impact: Better trace filtering, no breaking changes to existing code
  - Implementation: Detect Modal deployment mode and set Weave attribute on initialization

**Schema/data changes:**
- `db/tickets.json` structure unchanged
- `db/tickets.json` location changes: `db/tickets.json` → `workspace/db/tickets.json`
- Weave trace format unchanged (enhanced with env attribute)
- Tyler agent configuration format unchanged

**Migration for existing users:**
- Move existing `db/tickets.json` → `workspace/db/tickets.json`
- Or re-copy from sample: `mkdir -p workspace/db && cp db/tickets.sample.json workspace/db/tickets.json`

## Risks

**Security:**
- **Modal URL exposure:** Modal dev URLs are publicly accessible (no firewall like localhost)
  - Mitigation: PLAYGROUND_API_KEY authentication already in place
  - Risk level: LOW - same security model as ngrok tunnels
  
- **Secrets management:** API keys now stored in Modal secrets instead of local `.env`
  - Mitigation: Modal secrets are encrypted at rest, better than `.env` in git
  - Risk level: LOW - improvement over current state
  
- **Broader attack surface:** Production deployment is always-on vs local dev only
  - Mitigation: API key required, rate limiting via Modal, can delete deployment
  - Risk level: LOW - standard for deployed services

**Performance/Availability:**
- **Modal cold starts:** First request after inactivity may be slower (free tier)
  - Impact: 1-3 second delay on first request, negligible after warmup
  - Mitigation: Document expected behavior, production deployments stay warmer
  - Risk level: LOW - acceptable for demo/tutorial
  
- **Modal free tier limits:** Free tier has concurrency and request limits
  - Impact: May hit limits if many users run tutorial simultaneously
  - Mitigation: Document limits, users get their own Modal accounts
  - Risk level: LOW - each user has their own quota
  
- **Network dependency:** Modal deployment requires internet connectivity
  - Impact: Cannot develop completely offline (unlike local uvicorn server)
  - Mitigation: Modal caches packages, most dev work is online anyway
  - Risk level: LOW - reasonable tradeoff for simplicity

**Data integrity:**
- **tickets.json persistence:** Modal containers are ephemeral, files reset on redeploy
  - Impact: Support tickets created during testing will be lost on redeploy
  - Mitigation: This is a demo database, resetting is expected behavior. Document in README.
  - Risk level: LOW - intentional for demo purposes
  
- **Concurrent access to tickets.json:** Multiple requests could race to write
  - Impact: TinyDB has file-locking, but Modal may run multiple containers
  - Mitigation: This is a demo, not production-grade. Could add Modal volume for shared state.
  - Risk level: MEDIUM - acceptable for demo, document limitation
  
- **Modal deployment failures:** Bad config could break production deployment
  - Impact: Users must debug Modal errors (new failure mode vs local server)
  - Mitigation: Clear error messages, health check endpoint, Modal logs
  - Risk level: MEDIUM - new complexity, offset by better deployment model

**Migration risks:**
- **Breaking change for existing users:** Users mid-tutorial with ngrok setup
  - Impact: Step 2 Part B instructions completely change
  - Mitigation: This is main branch update, users can finish on old branch first
  - Risk level: MEDIUM - document in changelog/migration guide
  
- **Example files vs workspace:** Users may have modified workspace files
  - Impact: Users must re-copy from examples or manually migrate
  - Mitigation: Clear instructions to backup workspace, diff existing files
  - Risk level: MEDIUM - standard for tutorial updates

## Observability needs

**Logs:**
- **Modal logs integration:** 
  - Modal captures stdout/stderr automatically
  - Existing Python logging will appear in Modal dashboard
  - Add: `modal app logs {app-name}` command to README for viewing logs
  - Add: Log initialization success/failure for debugging Modal deployment
  
- **Agent startup logging:**
  - Keep existing Weave init logs
  - Add: Modal-specific startup logs (app name, deployment mode, URL)
  - Add: Environment detection and logging (dev vs prod)
  - Add: Clear error messages for missing Modal secrets
  - Add: Confirmation that Weave environment attribute is set correctly

**Metrics:**
- **Weave metrics (enhanced):**
  - Request traces continue to work identically
  - Token usage tracking continues to work
  - Tool call tracking continues to work
  - **NEW:** Environment tagging - all traces tagged with `env=dev` or `env=prod` attribute
    - Enables filtering development vs production traffic
    - Helps separate testing from real usage
    - No breaking changes - just an additional attribute
  
- **Modal metrics (new):**
  - Modal dashboard shows request count, latency, cold starts
  - No code changes needed - Modal provides this automatically
  - Document: How to view Modal metrics in README

**Alerts:**
- **No automated alerts needed** (this is a demo/tutorial)
- **Manual monitoring:**
  - Users can check Modal dashboard for deployment status
  - Users can check Weave traces for agent behavior
  - Health check endpoint for smoke tests
  
- **Error visibility:**
  - Modal shows deployment errors in UI during `modal deploy`
  - Runtime errors appear in Modal logs
  - Agent errors captured in Weave traces as before

**Debugging improvements:**
- **Better than ngrok:** Modal logs persist vs ngrok tunnel logs lost on restart
- **Same as ngrok:** Weave traces provide full agent observability
- **New capability:** `modal serve` shows live logs in terminal (better DX than ngrok)

