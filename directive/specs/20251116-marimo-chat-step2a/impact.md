# Impact Analysis — Marimo In-Browser Chat for Step 2A

**Spec ID**: 20251116  
**Created**: 2025-11-16  

## Modules/packages likely touched

### Modified Files

**`marimo-guide.py`** (1619 lines currently)
- **Lines ~250-540**: Step 2A section
- **Changes needed**:
  - Add agent loading cell (load from config with MCP support)
  - Add chat adapter function cell (converts marimo messages to Tyler format)
  - Add chat widget UI cell with `mo.ui.chat()`
  - Update file copy button logic to trigger agent loading
  - Add error handling cells for agent failures
  - Add dynamic Weave trace links
  - Remove or make optional terminal instructions
- **Estimated impact**: +100-150 lines of new code
- **Risk level**: Low (isolated to Step 2A, other steps unchanged)

### New Dependencies

**None required** - All packages already in `pyproject.toml`:
- ✅ `marimo>=0.17.7` (already present, has `mo.ui.chat()`)
- ✅ `slide-agents` (already present, includes Tyler Agent)
- ✅ `weave` (already present for observability)
- ✅ `pyyaml` (already present for config loading)
- ✅ `python-dotenv` (already present for env vars)

### Unchanged Files

**No changes needed to**:
- `examples/step-2/part-a/tyler-chat-config.yaml` - works as-is
- `examples/step-2/part-a/tools.py` - works as-is
- `examples/step-2/part-a/main.py` - remains for reference
- `examples/step-2/part-b/*` - Step 2B unchanged
- `examples/step-3/` through `step-6/` - All later steps unchanged
- `README.md` - Optional minor update (can defer)

### Files That Work With No Changes

Because we're using the **same** `Agent.from_config()` approach as the server:
- All agent configs are compatible
- All tools work identically
- MCP server connections use same code path
- Weave tracing works automatically

## Contracts to update (APIs, events, schemas, migrations)

### No External Contracts Changed

This feature is entirely internal to the marimo guide. No external APIs, events, or schemas are affected.

### Internal Interfaces (New)

**Agent Loading Function** (new in marimo-guide.py):
```python
def load_agent_from_config(
    config_path: Path
) -> tuple[Agent | None, dict | None, str]:
    """
    Load Tyler Agent using same approach as server.
    
    Returns:
        (agent, config_dict, status_message)
        - agent: Agent instance or None if failed
        - config_dict: Parsed config or None if failed
        - status_message: User-friendly status/error message
    """
```

**Chat Adapter Function** (new in marimo-guide.py):
```python
def tyler_chat_function(
    messages: list[dict], 
    config: dict
) -> str:
    """
    Adapter for mo.ui.chat() that uses Tyler Agent.
    
    Args:
        messages: Chat history from marimo [{"role": "user", "content": "..."}]
        config: Model configuration from marimo (unused, for compatibility)
        
    Returns:
        Assistant response text (complete, not streaming)
    """
```

These are internal helper functions in `marimo-guide.py`, not exposed as public APIs.

### Compatibility Guarantees

**Backward Compatibility:**
- ✅ Terminal workflow (`tyler chat`) still works
- ✅ All existing files/configs unchanged
- ✅ Users can skip browser chat, use terminal if preferred
- ✅ No breaking changes to any step

**Forward Compatibility:**
- ✅ Config tested in Step 2A works in Step 2B deployment
- ✅ Agent behavior identical between local and deployed
- ✅ MCP servers work same way (or fail gracefully locally)

## Risks

### Security

**Risk Level: Very Low**

**Local Execution Only:**
- Agent runs in user's marimo Python process (localhost)
- No network exposure beyond what agent/MCP servers need
- Same security posture as running `tyler chat` in terminal
- No new secrets or credentials introduced

**Environment Variables:**
- Uses existing `WANDB_API_KEY` from `.env`
- Uses existing `OPENAI_API_KEY` (if configured)
- No changes to secret management approach

**Code Execution:**
- Agent loads tools from `workspace/tools.py` (user's own code)
- MCP servers connect to user-configured endpoints
- No remote code execution risk
- Same trust model as terminal-based testing

**Mitigation:**
- Agent confined to user's local environment
- Weave API key already required for existing steps
- No new attack surface introduced

### Performance/Availability

**Risk Level: Low**

**Agent Loading Time:**
- `Agent.from_config()` takes ~1-3 seconds
- MCP connection (if configured) adds ~1-2 seconds
- One-time cost when files copied or config changes
- **Impact**: Acceptable for local testing
- **Mitigation**: Load agent only when needed (reactive cell)

**Chat Response Time:**
- `agent.run()` blocks until complete (~3-10 seconds typical)
- No streaming means user waits for full response
- **Impact**: Slightly slower UX than streaming, but acceptable for testing
- **Mitigation**: Show loading indicator in marimo

**Memory Usage:**
- Agent instance kept in memory (~50-100MB)
- Conversation history in memory (minimal)
- **Impact**: Negligible for local development
- **Mitigation**: Agent garbage collected when marimo restarts

**Marimo Reactivity:**
- Chat widget should not re-load agent on every message
- Reactive cell structure must prevent unnecessary reloads
- **Impact**: Could cause slowness if designed poorly
- **Mitigation**: Careful cell dependency management (addressed in TDR)

### Data Integrity

**Risk Level: Very Low**

**No Persistent Data:**
- Chat conversations ephemeral (not saved to disk)
- No database writes
- No file modifications during chat operation
- Only Weave traces are persistent (as intended)

**Configuration Consistency:**
- Risk: User edits config while agent loaded
- Impact: Agent uses stale config until reload
- **Mitigation**: Marimo reactive execution will reload agent when config file changes (or manual refresh)

**Trace Data:**
- All agent calls traced to Weave (same as terminal)
- No risk of losing observability
- Traces tagged with operation name and attributes
- **Mitigation**: `weave.init()` called before agent loading

## Observability needs

### Logs

**Not Applicable** - Local development tool, not a production service.

**User-Visible Feedback** (via marimo UI elements):
- ✅ Agent loading status (success/failure with details)
- ✅ MCP connection status (connected/failed/not configured)
- ⚠️ Error messages with actionable troubleshooting
- 🔗 Direct links to Weave traces

### Metrics

**Not Applicable** - No automated telemetry collection from marimo guide.

**Manual Validation** (for success criteria):
- Time to first chat interaction (internal testing)
- Error rate during agent loading (internal testing)
- Completion rate of Step 2A (qualitative feedback)
- User satisfaction (team dogfooding survey)

### Alerts

**Not Applicable** - Local tool, no operational monitoring needed.

**User-Facing Alerts** (via marimo callouts):
- `mo.callout(..., kind="warn")` for config issues
- `mo.callout(..., kind="danger")` for agent load failures
- `mo.callout(..., kind="info")` for MCP connection info
- `mo.callout(..., kind="success")` for successful setup

---

## Dependencies & Integration Points

### Upstream Dependencies

**Tyler Agent** (`slide-agents` package):
- **API Used**: `Agent.from_config()`, `agent.run()`, `agent.connect_mcp()`
- **Stability**: These are stable public APIs
- **Version**: No version change needed (already compatible)
- **Risk**: Very low - well-tested APIs

**Marimo** (`marimo>=0.17.7`):
- **API Used**: `mo.ui.chat()` with custom function
- **Stability**: Feature introduced in 0.6.0, stable since
- **Version**: Current version sufficient
- **Risk**: Very low - documented feature

**Weave** (`weave` package):
- **API Used**: `weave.init()`, automatic tracing
- **Stability**: Core Weave APIs, very stable
- **Version**: No change needed
- **Risk**: Very low - already in use

### Downstream Impact

**Step 2B (Modal Deployment):**
- ✅ **No changes needed** to Step 2B
- ✅ **Benefit**: Config pre-validated in Step 2A
- ✅ Users have confidence before deploying
- ✅ Faster debugging if deployment fails

**Step 3 (Iterate/Vibe):**
- ✅ **No changes needed** to Step 3
- ✅ **Benefit**: Users can test config edits locally
- ✅ Faster iteration cycle (local test → deploy)

**Step 4+ (Evaluation, Production, Guardrails):**
- ✅ **No impact** on later steps
- ✅ These use deployed agent, not local
- ✅ **Benefit**: Users more confident in agent behavior

### Integration Testing Needed

**Agent Loading:**
- [ ] Load agent from valid config → succeeds
- [ ] Load agent from invalid config → shows clear error
- [ ] Load agent with MCP configured → connects or warns
- [ ] Load agent without MCP → works normally

**Chat Functionality:**
- [ ] Send message → get response
- [ ] Multi-turn conversation → context maintained
- [ ] Tool calls → visible in Weave traces
- [ ] Agent errors → surfaced to user

**Consistency Check:**
- [ ] Same prompt in Step 2A and Step 2B → identical tool calls
- [ ] Same prompt in Step 2A and terminal → identical behavior
- [ ] Config edits reflected in both local and deployed

---

## Migration & Rollout Considerations

### No Migration Needed

**Feature is additive:**
- Enhances existing Step 2A
- No breaking changes
- Terminal workflow continues to work
- Users on older branches unaffected

**No data migration:**
- No persistent state
- No database changes
- No config format changes

### Rollout Plan

**Phase 1: Internal Testing** (1-2 days)
- W&B team tests enhanced Step 2A
- Validate agent loading works correctly
- Test error handling paths
- Collect UX feedback

**Phase 2: Merge to Main**
- Merge feature branch after PR approval
- Available immediately to all users
- No deployment infrastructure needed
- Users get update on next `git pull`

**Phase 3: Documentation** (optional)
- Update README.md Step 2A section
- Mention browser-based testing option
- Keep terminal instructions as alternative
- No urgency (marimo guide is self-documenting)

### Rollback Plan

**If Critical Issues Discovered:**

**Option 1: Quick Revert** (< 5 minutes)
```bash
git revert <commit-hash>
git push origin main
```
- Users fall back to terminal-based Step 2A
- No data loss (no persistent state)
- Weave traces remain intact

**Option 2: Feature Flag** (if partial issues)
```python
ENABLE_CHAT = os.getenv("MARIMO_CHAT_ENABLED", "true") == "true"
if ENABLE_CHAT:
    # Show chat widget
else:
    # Show terminal instructions only
```
- Can disable quickly if needed
- Minimal code change
- Gradual rollout possible

**Blast Radius: Very Low**
- Only affects Step 2A user experience
- Terminal workflow always available
- No production systems impacted
- No data loss possible

---

## Open Questions & Resolutions

### Resolved

✅ **Q: Use streaming or non-streaming?**
- **Resolution**: Use `agent.run()` (non-streaming) for simplicity
- Rationale: marimo custom functions don't support streaming, acceptable UX for local testing

✅ **Q: Same agent as server?**
- **Resolution**: Yes, use `Agent.from_config()` - exact same code path
- Rationale: Validates config will work when deployed

✅ **Q: Handle MCP connection failures?**
- **Resolution**: Show warning but allow agent to work without MCP
- Rationale: MCP may not be accessible locally, works when deployed

### Remaining for TDR

❓ **Should we show tool calls in chat UI?**
- Option A: Show "[Using tool: create_issue]" inline
- Option B: Tool calls only visible in Weave traces
- **Decision needed**: TDR will specify

❓ **How to handle config reloading?**
- Option A: Manual (user refreshes marimo)
- Option B: Automatic file watching
- **Decision needed**: TDR will specify (lean toward manual for simplicity)

❓ **Error message detail level?**
- Option A: Show full stack traces
- Option B: User-friendly messages only
- **Decision needed**: TDR will specify (lean toward friendly with "Show details" expander)

---

## Testing Strategy

### Unit Testing

**Not Applicable** - Marimo cells are UI/integration, not unit-testable functions.

**Manual Validation Required:**
- Agent loading from valid config
- Chat interaction flow
- Error handling display
- Weave link generation

### Integration Testing (Manual)

**Test Scenarios:**

1. **Happy Path**:
   - [ ] Copy files → agent loads → chat works → traces visible

2. **Error Handling**:
   - [ ] Invalid config → clear error message
   - [ ] Missing config → setup instructions
   - [ ] MCP failure → warning but functional

3. **Consistency**:
   - [ ] Same prompt in chat and terminal → same behavior
   - [ ] Config from Step 2A → works in Step 2B deployment

### Acceptance Testing

**Success Criteria from Spec:**
- [ ] Users complete Step 2A without terminal
- [ ] Agent responds correctly to test prompts
- [ ] Traces appear in Weave
- [ ] Error messages are actionable
- [ ] Transition to Step 2B is smooth

**Will be validated in TDR implementation milestones.**

---

## Success Metrics (Post-Implementation)

### Immediate Validation (Day 1)

- [ ] Agent loads in < 5 seconds
- [ ] First chat response in < 15 seconds
- [ ] Zero crashes with valid config
- [ ] All test prompts work

### Team Feedback (Week 1)

- [ ] "Easier than terminal" - majority preference
- [ ] "Clear what to do" - no confusion
- [ ] "Smooth to Step 2B" - good transition
- [ ] No showstopper bugs reported

### Long-term (Month 1)

- [ ] Step 2A completion rate maintained or improved
- [ ] Fewer "stuck at Step 2A" support requests
- [ ] Positive feedback in team retros
- [ ] Feature considered stable

---

## Risk Summary

| Risk Category | Level | Mitigation | Status |
|--------------|-------|------------|--------|
| Security | Very Low | Local execution, same as terminal | ✅ Acceptable |
| Performance | Low | Acceptable for local testing | ✅ Acceptable |
| Data Integrity | Very Low | No persistent state | ✅ Acceptable |
| Compatibility | Very Low | Additive feature, no breaking changes | ✅ Acceptable |
| Rollback | Very Low | Simple revert, no data loss | ✅ Acceptable |

**Overall Risk Assessment: LOW** ✅

---

## Approval Checklist

- [x] All modified files identified
- [x] Dependencies verified (no new ones needed)
- [x] Security risks assessed and mitigated
- [x] Performance impact acceptable
- [x] Rollback plan documented
- [x] Success metrics defined
- [x] Integration points identified
- [ ] TDR ready to be created (pending approval)

**Ready for TDR Phase** ✅

