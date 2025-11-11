# Impact Analysis — Step 6: Online Monitoring & Guardrails

**Spec ID**: 20251106  
**Created**: 2025-11-06  

## Modules/packages likely touched

### New Files (Part A: Guardrails)
- `examples/step-6/part-a/guardrails.py` - Custom Python scorer classes for guardrails
  - `ToxicityGuardrail(Scorer)` - Detects toxic/harmful content
  - `OffTopicGuardrail(Scorer)` - Blocks non-support questions
- `examples/step-6/part-a/server.py` - Updated Modal server with guardrails integrated
  - Imports guardrail scorers
  - Applies guardrails using `.call()` and `apply_scorer()` before returning responses
  - Handles guardrail failures gracefully

### No New Files (Part B: Monitors)
- Part B has no code files - monitors are configured through Weave UI
- Documentation will reference existing `workspace/scorers.py` from Step 4
- Documentation will reference existing judge configs:
  - `workspace/accuracy-judge-config.yaml`
  - `workspace/safety-judge-config.yaml`

### Documentation Updates
- `README.md` - Step 6 section (~150-200 lines)
  - Part A: Adding Guardrails subsection
  - Part B: Setting Up Monitors subsection
  - Comparison table: Guardrails vs Monitors
  - Screenshots for Weave UI monitor configuration
  - Troubleshooting section

### Test Files
- `tests/test_guardrails.py` - Unit tests for guardrail scorers
  - Test toxic content detection
  - Test off-topic detection
  - Test error handling (graceful degradation)
  - Test scorer initialization efficiency

## Contracts to update (APIs, events, schemas, migrations)

### API Behavior Changes
- **Modal server endpoint behavior** (`/v1/chat/completions`):
  - **Before**: Returns agent response directly
  - **After**: May return guardrail-blocked message if content flagged
  - **Breaking?** No - still returns valid OpenAI-compatible response format
  - **Example blocked response**:
    ```json
    {
      "choices": [{
        "message": {
          "role": "assistant",
          "content": "I cannot generate that content: [reason from guardrail]"
        }
      }]
    }
    ```

### Weave Trace Schema
- **No changes** - Guardrail scorer results automatically stored in existing Weave trace structure
- Guardrail results appear in trace's scorer/feedback fields (existing Weave functionality)

### No Migrations Required
- No database schema changes
- No data migrations needed
- All guardrail/monitor data stored in Weave's existing infrastructure

## Risks

### Security
- ✅ **Positive impact**: Guardrails are a security feature that prevents unsafe content
- ⚠️ **Risk**: Guardrails can be bypassed if users skip Part A or deploy without guardrails
  - **Mitigation**: Documentation emphasizes guardrails are not optional; include warnings
- ⚠️ **Risk**: Guardrail logic bugs could allow harmful content through
  - **Mitigation**: Comprehensive test coverage; start with well-tested patterns (toxicity, off-topic)
- ⚠️ **Risk**: Over-blocking (false positives) could frustrate legitimate users
  - **Mitigation**: Conservative guardrail prompts; monitor false positive rates; provide override mechanisms in production

### Performance/Availability
- ⚠️ **Risk**: Guardrails add latency to every request
  - **Spec requirement**: <10% latency increase (<500ms for guardrails)
  - **Mitigation**: 
    - Use lightweight scorers (rule-based or small models)
    - Initialize scorers outside request handlers (pattern shown in examples)
    - Provide performance testing guidance
- ⚠️ **Risk**: Guardrail failures could block all requests
  - **Mitigation**: Error handling defaults to safe behavior (block with explanation)
  - **Mitigation**: Log errors to Weave for debugging
- ✅ **Monitors have no performance impact**: Run asynchronously on Weave's backend
- ⚠️ **Risk**: High monitor sampling rates could incur LLM costs
  - **Mitigation**: Document cost implications; recommend 10% sampling for production

### Data integrity
- ✅ **No data integrity risks**: 
  - Guardrails don't modify data, only block/allow responses
  - Monitors are read-only observations
  - All scoring results stored in Weave (no custom storage)

### User Experience
- ⚠️ **Risk**: Users may not understand why content was blocked
  - **Mitigation**: Guardrails return clear explanations (e.g., "I cannot generate that content: Contains off-topic request about cooking")
- ⚠️ **Risk**: Inconsistent scoring between Step 4 evals and monitors
  - **Mitigation**: Documentation emphasizes using same models + prompts for consistency

### Educational/Tutorial Risks
- ⚠️ **Risk**: Users may confuse guardrails (code) with monitors (UI)
  - **Mitigation**: Clear comparison table; separate Parts A and B; emphasize differences
- ⚠️ **Risk**: Manual prompt copying from Step 4 to monitors is error-prone
  - **Mitigation**: Provide exact line numbers; include validation tips (test monitor on sample trace)
- ⚠️ **Risk**: Weave UI may change, making screenshots outdated
  - **Mitigation**: Include text instructions alongside screenshots; version documentation

## Observability needs

### Logs
- **Guardrail blocking events** (automatic via Weave):
  - Every guardrail check logged as scorer result in trace
  - Filter traces by `scorer.result.flagged = true` to find blocked requests
  - Includes blocking reason for debugging

- **Guardrail errors** (needs explicit logging):
  - Log exceptions in guardrail scorers to Weave
  - Include context: which guardrail failed, why, input hash
  - Example: `print(f"ToxicityGuardrail failed: {str(e)}")` (Weave captures stdout)

- **Monitor configuration changes** (automatic via Weave):
  - Weave audit log tracks monitor creation/updates
  - No custom logging needed

### Metrics
- **Automatically tracked by Weave**:
  - Guardrail execution latency (per scorer, per trace)
  - Guardrail block rate (% of requests flagged)
  - Monitor scoring frequency (based on sampling rate)
  - Monitor score distributions over time

- **Custom metrics** (optional, not required for tutorial):
  - False positive rate (requires user feedback mechanism - out of scope for Step 6)
  - Guardrail vs monitor score correlation (can query via Weave API)

### Alerts
- ⚠️ **Not in scope for Step 6** (mentioned in Non-Goals)
- **Future enhancement**: Alert on:
  - High guardrail block rates (>20% of traffic)
  - Guardrail failures (error rate > 1%)
  - Monitor scores dropping below baseline
- **Mitigation for Step 6**: Document where users would set up alerts (Weave UI, future feature)

### Dashboard/Visualization Needs
- **Weave UI (built-in)**:
  - Traces tab: View individual guardrail results
  - Monitors tab: View monitor score trends over time
  - Saved Views: Create filtered views (e.g., "Blocked Requests")

- **Tutorial should create Saved View**:
  - Name: "Guardrail Blocked Requests"
  - Filter: `scorer.name contains "Guardrail" AND scorer.result.flagged = true`
  - Purpose: Quick access to blocked content for analysis

## Dependencies

### External Dependencies
- **No new package dependencies**:
  - Guardrails use existing `weave` package
  - Monitors configured through Weave UI (no client-side dependencies)

### Weave Feature Dependencies
- **Required Weave features**:
  - Scorer class support (stable, documented)
  - `.call()` method on ops (stable, documented)
  - `apply_scorer()` method (stable, documented)
  - Monitors UI (available in Multi-Tenant SaaS - confirmed in docs)

- **W&B Inference availability**:
  - Model: `openai/meta-llama/Llama-3.1-8B-Instruct`
  - Must be available in both:
    1. API (for Step 4 scorers) - ✅ Already working in Step 4
    2. Weave monitor UI (for monitor configuration) - ⚠️ Need to verify in implementation

### Integration Dependencies
- **Step 5 deployment** (prerequisite):
  - Guardrails integrate into existing `server.py` from Step 5
  - Monitors watch `Agent.stream` operation (must have Step 5 traces)
  
- **Step 4 scorers** (soft dependency):
  - Monitors reuse prompts/configs from Step 4
  - Users can still complete Step 6 without Step 4, but lose consistency benefit

## Rollback Plan

### If Guardrails Cause Issues
- **Rollback**: Revert to Step 5's `server.py` (no guardrails)
  - `cp examples/step-5/server.py workspace/server.py`
  - Redeploy: `modal deploy workspace/server.py`
- **Partial rollback**: Comment out specific guardrails in `server.py`
- **Zero downtime**: Modal deployment updates without downtime

### If Monitors Cause Issues
- **Disable in UI**: Toggle monitor off in Weave UI (no code changes)
- **Delete monitor**: Remove monitor entirely from Weave UI
- **No rollback needed**: Monitors don't affect server code

## Success Metrics

### Technical Metrics
- ✅ Guardrails execute in <500ms (p99)
- ✅ Guardrail error rate < 1%
- ✅ Monitor sampling rate configurable (10%, 25%, 50%, 100%)
- ✅ Zero production incidents caused by Step 6 changes

### Educational Metrics
- ✅ Users successfully add guardrails without manual debugging
- ✅ Users successfully configure monitors on first try
- ✅ Users understand guardrails vs monitors tradeoffs (survey/feedback)
- ✅ Users can interpret guardrail/monitor results in Weave UI

### Adoption Metrics (Internal W&B Use)
- Track how many users complete Step 6
- Track guardrail patterns users implement (toxicity? custom?)
- Track monitor configurations (which prompts? sampling rates?)
- Feedback on which pattern (guardrails vs monitors) users prefer

## Open Questions

1. **Monitor model availability**: Can users select `openai/meta-llama/Llama-3.1-8B-Instruct` in Weave monitor UI?
   - **Resolution needed before**: Implementation
   - **Fallback**: Use different model, document the difference

2. **Monitor prompt length limits**: Are there character limits on scoring prompts in Weave UI?
   - **Impact**: Step 4 prompts are ~400-500 chars each
   - **Resolution needed before**: Implementation
   - **Fallback**: Provide abbreviated prompts

3. **Guardrail best practices**: What guardrails are most useful for support bot use case?
   - **Proposed**: Toxicity (harmful content) + OffTopic (non-support questions)
   - **Alternative**: Add PII detection guardrail?
   - **Resolution needed before**: Implementation

4. **Monitor response format**: Do monitors need `json_object` response format like Step 4 scorers?
   - **Impact**: Affects UI configuration instructions
   - **Resolution needed before**: Documentation
   - **Test during**: Implementation

## Notes

- **Manual prompt copying is intentional**: While not ideal from DRY perspective, it's realistic for production workflows and teaches users how to bridge offline eval → online monitoring
- **No feedback collection in Step 6**: Deferred to future step to keep scope manageable
- **Guardrails ≠ Perfect safety**: Documentation should set realistic expectations about limitations
- **Monitoring is passive**: Emphasize that monitors don't prevent issues, only observe them

