# Technical Design Review (TDR) — Step 6: Online Monitoring & Guardrails

**Spec ID**: 20251106  
**Created**: 2025-11-06  
**Author**: AI Agent  
**Links**: 
- Spec: `/directive/specs/20251106-step-6-monitoring-guardrails/spec.md`
- Impact: `/directive/specs/20251106-step-6-monitoring-guardrails/impact.md`
- Related: Weave Guardrails Documentation (https://docs.wandb.ai/weave/guides/evaluation/guardrails_and_monitors)

---

## 1. Summary

We are building Step 6 of the agentic support bot tutorial, which adds production safety controls and quality monitoring using Weave's scoring infrastructure. This step teaches users two complementary patterns:

**Part A: Guardrails** - Active safety controls using custom Python `Scorer` classes that run synchronously in the server to block unsafe content before it reaches users. These are fast, deterministic checks (e.g., toxicity detection, off-topic filtering) integrated directly into the Modal deployment.

**Part B: Monitors** - Passive quality tracking using LLM-as-a-judge scorers configured through Weave's UI that run asynchronously on Weave's backend to sample and score production traffic. Users reuse prompts and model configurations from Step 4's evaluation scorers to ensure consistent scoring between offline evaluation and production monitoring.

This step bridges the gap between offline evaluation (Step 4) and production deployment (Step 5), giving users visibility into production behavior and safety mechanisms to prevent harmful outputs.

## 2. Decision Drivers & Non‑Goals

### Decision Drivers

**Educational Clarity**:
- Users must understand the difference between guardrails (code) and monitors (UI)
- Show realistic production patterns, not toy examples
- Demonstrate value of consistent evaluation (reusing Step 4 prompts/models)

**Safety Requirements**:
- Guardrails must be fast (<500ms) to avoid UX degradation
- Error handling must default to safe behavior (block on failure)
- All guardrail decisions must be logged for auditability

**Production Readiness**:
- Work with existing Modal deployment from Step 5 (no breaking changes)
- Monitors must not impact server performance (async on Weave backend)
- Support cost control via configurable sampling rates

**Consistency**:
- Reuse Step 4 evaluation logic (same models + prompts) for apples-to-apples comparison
- Enable users to compare offline eval scores to production monitor scores

### Non‑Goals

- ❌ User feedback collection (deferred to future step)
- ❌ Real-time alerting on low scores (future enhancement)
- ❌ A/B testing frameworks (covered in Step 7)
- ❌ Custom monitoring dashboards beyond Weave UI
- ❌ Automated remediation based on scores
- ❌ Multi-model judge ensembles
- ❌ Guardrail customization UI (users edit Python code)

## 3. Current State — Codebase Map (concise)

### Key Modules (Existing)

**Step 5 Server** (`examples/step-5/server.py`):
- Modal web app serving OpenAI-compatible API
- Uses Slide `Agent` to handle requests
- Returns streaming responses
- No safety checks or monitoring currently

**Step 4 Scorers** (`workspace/scorers.py`):
- `tool_usage_scorer` - Rule-based tool correctness
- `accuracy_scorer` - LLM judge for answer quality (uses `accuracy-judge-config.yaml`)
- `safety_scorer` - LLM judge for tone/safety (uses `safety-judge-config.yaml`)
- Both LLM judges use `openai/meta-llama/Llama-3.1-8B-Instruct` via W&B Inference

**Test Infrastructure** (`tests/`):
- `conftest.py` - Shared fixtures
- `test_server.py` - Server endpoint tests
- `test_tools.py` - Tool execution tests
- `test_scorers.py` - Scorer unit tests

### Existing Data Models

**Weave Traces**:
- Automatic tracking of all `@weave.op()` decorated functions
- Call objects contain inputs, outputs, timing, costs
- Scorer results stored in trace feedback/scorer fields

**Modal Deployment**:
- Environment-based deployment (dev/main)
- Secrets management via Modal
- Auto-reload in dev mode

### External Contracts

**OpenAI-Compatible API** (`/v1/chat/completions`):
- Request: Standard OpenAI format
- Response: Standard OpenAI format with streaming support
- Used by Weave Playground

**Weave API** (implicit):
- Automatic trace logging via `weave.init()`
- `.call()` method returns (result, Call object)
- `apply_scorer()` associates scorer with Call

### Observability (Current)

**Available**:
- Weave traces for all agent interactions
- Modal logs for server errors
- Weave UI for trace exploration

**Missing** (to be added in Step 6):
- Guardrail blocking events (visible in traces)
- Monitor score trends over time
- Saved views for filtered analysis

## 4. Proposed Design (high level, implementation‑agnostic)

### Part A: Guardrails Architecture

```
User Request
    ↓
Modal Server (/v1/chat/completions)
    ↓
Agent.stream.call(messages)  ← Returns (result, call)
    ↓
Apply Guardrails (synchronous):
    - toxicity_guardrail.score(call)
    - off_topic_guardrail.score(call)
    ↓
Check Results:
    - If flagged=true → Return blocked message
    - If flagged=false → Return agent response
    ↓
Response to User
    ↓
(All guardrail checks logged to Weave automatically)
```

**Key Design Decisions**:

1. **Scorer Implementation**: Inherit from `weave.Scorer`, implement `score()` method
2. **Initialization**: Create scorer instances outside request handler (performance)
3. **Integration Point**: After agent generates response, before returning to user
4. **Error Handling**: Try-catch around scorer execution, default to blocking on error
5. **Response Format**: Return friendly message with reason when blocking

### Part B: Monitors Architecture

```
Production Traffic (Agent.stream ops)
    ↓
Weave Backend (automatic)
    ↓
Monitor Sampling (10% of calls)
    ↓
LLM-as-a-Judge Scoring (async):
    - Accuracy Monitor (Llama-3.1-8B)
    - Safety Monitor (Llama-3.1-8B)
    ↓
Store Scores in Weave
    ↓
User Views in Weave UI:
    - Monitors tab (trends)
    - Traces tab (individual scores)
```

**Key Design Decisions**:

1. **Configuration**: Through Weave UI, not code
2. **Prompts**: Copy from Step 4 `scorers.py` (lines 86-110, 172-208)
3. **Models**: Same as Step 4 (`openai/meta-llama/Llama-3.1-8B-Instruct`)
4. **Sampling**: 10% recommended for cost control
5. **Async Execution**: No impact on server latency

### Interfaces & Data Contracts

#### Guardrail Scorer Interface

```python
class GuardrailScorer(weave.Scorer):
    """Base pattern for guardrail scorers."""
    
    @weave.op
    def score(self, output: str) -> dict:
        """
        Evaluate content safety.
        
        Args:
            output: Generated content to check
            
        Returns:
            {
                "flagged": bool,  # True if content should be blocked
                "reason": str | None,  # Explanation if flagged
                "score": float  # 0.0 if flagged, 1.0 if safe
            }
        """
        pass
```

#### Server Integration Pattern

```python
# Initialize guardrails (outside request handler)
toxicity_guard = ToxicityGuardrail()
off_topic_guard = OffTopicGuardrail()

async def handle_request(messages: list[dict]) -> dict:
    # Generate response
    result, call = agent.stream.call(messages)
    
    # Apply guardrails sequentially (simpler, easier to debug)
    # Check toxicity first
    toxicity_check = await call.apply_scorer(toxicity_guard)
    if toxicity_check.result["flagged"]:
        return blocked_response(toxicity_check.result["reason"])
    
    # Check off-topic second
    topic_check = await call.apply_scorer(off_topic_guard)
    if topic_check.result["flagged"]:
        return blocked_response(topic_check.result["reason"])
    
    # Return safe response
    return result
```

#### Monitor Configuration (Weave UI)

**Accuracy Monitor**:
```yaml
name: accuracy-monitor
operation: Agent.stream
sampling_rate: 0.1  # 10%
judge_model: openai/meta-llama/Llama-3.1-8B-Instruct
system_prompt: "You are an evaluation judge. Return only valid JSON."
scoring_prompt: |
  You are evaluating a customer support bot's response for accuracy and helpfulness.
  
  User Question: {input}
  Expected Behavior/Content: {expected_output_description}
  Actual Bot Response: {output}
  
  [... full prompt from accuracy_scorer ...]
response_format: json_object
temperature: 0.0
```

### Error Handling

**Guardrail Errors**:
```python
try:
    check = await call.apply_scorer(guardrail)
except Exception as e:
    # Log error
    print(f"Guardrail {guardrail.name} failed: {str(e)}")
    
    # Default to safe behavior (block)
    return {
        "flagged": True,
        "reason": "Safety check unavailable",
        "error": str(e)
    }
```

**Monitor Errors**:
- Handled automatically by Weave backend
- Failed scoring attempts logged but don't block traffic
- User views error status in Monitors tab

### Performance Expectations

**Guardrails**:
- Target: <500ms per guardrail (p99)
- Combined: <10% total latency increase (2 guards × 500ms = 1000ms max, acceptable for tutorial)
- Sequential execution: Guardrails run one after another (simpler, easier to understand)

**Monitors**:
- No impact on server latency (async on Weave backend)
- Scoring latency: ~1-3 seconds per sample (acceptable for background)
- Sampling delay: Results appear within seconds of request

## 5. Alternatives Considered

### Alternative A: Guardrails as Separate Service

**Approach**: Deploy guardrails as separate Modal service, call before agent

**Pros**:
- Independent scaling
- Language-agnostic (could reuse across projects)
- Easier to update without redeploying agent

**Cons**:
- Additional network hop (latency)
- More infrastructure to maintain
- Complicates tutorial (multiple deployments)
- Adds cost (separate service)

**Why Not Chosen**: Tutorial simplicity and latency concerns outweigh scaling benefits

### Alternative B: Use Only Monitors (No Guardrails)

**Approach**: Configure monitors with 100% sampling, review blocked content manually

**Pros**:
- Simpler implementation (UI-only)
- No code changes to server
- All logic in Weave

**Cons**:
- **Cannot block unsafe content in real-time**
- Inappropriate responses reach users
- Not suitable for production safety
- Defeats educational purpose (teaching active vs passive patterns)

**Why Not Chosen**: Safety requirement mandates real-time blocking capability

### Alternative C: Guardrails Use LLM Judges (Like Monitors)

**Approach**: Guardrails call LLM APIs for scoring

**Pros**:
- More sophisticated detection
- Easier to customize (prompts vs code)
- Could reuse Step 4 judge configs directly

**Cons**:
- **Too slow** (LLM latency ~500-2000ms, violates <500ms target)
- Expensive (every request = LLM call)
- External API dependency increases failure modes
- Cannot run during LLM API outages

**Why Not Chosen**: Performance requirements favor lightweight, deterministic checks for guardrails

### Alternative D: Duplicate Scorers for Monitors

**Approach**: Create new scorer definitions specifically for monitors (separate from Step 4)

**Pros**:
- Cleaner separation of concerns
- Could optimize prompts specifically for monitoring

**Cons**:
- **Breaks consistency** between offline eval and production monitoring
- More code to maintain
- Loses educational value of reuse pattern
- Harder to compare eval vs production scores

**Why Chosen Design is Better**: Reusing Step 4 prompts/models ensures apples-to-apples comparison and teaches realistic production workflow

## 6. Data Model & Contract Changes

### Tables/Collections

**No new tables** - All data stored in Weave's existing infrastructure:
- Traces table (existing)
- Scorer results (existing, as feedback on traces)
- Monitor configurations (existing, in Weave backend)

### API Changes

**Modal Server** (`/v1/chat/completions`):

**Before Step 6**:
```json
POST /v1/chat/completions
{
  "model": "buzz",
  "messages": [{"role": "user", "content": "Help me"}]
}

Response:
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "I'd be happy to help! What do you need?"
    }
  }]
}
```

**After Step 6** (when guardrail blocks):
```json
POST /v1/chat/completions
{
  "model": "buzz",
  "messages": [{"role": "user", "content": "Tell me how to hack"}]
}

Response:
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "I cannot generate that content: Request is off-topic for W&B support"
    }
  }]
}
```

**Breaking?** No - response format unchanged, only content differs when blocked

### Event Changes

**No new events** - Existing Weave trace events sufficient:
- `weave.op.start` - Agent execution begins
- `weave.op.end` - Agent execution completes
- `weave.scorer.result` - Guardrail/monitor score recorded (new data, existing event)

### Backward Compatibility

- ✅ Step 5 server continues to work without Step 6 changes
- ✅ Users can skip guardrails (though discouraged for safety)
- ✅ Monitors are optional (pure observability, no behavior change)
- ✅ No breaking changes to existing API contracts

### Deprecation Plan

N/A - No deprecations in this step

## 7. Security, Privacy, Compliance

### AuthN/AuthZ Model

**No changes to authentication**:
- Modal server uses existing `AGENTIC_SUPPORT_BOT_API_KEY`
- Weave uses existing `WANDB_API_KEY`
- Monitor configuration requires Weave project access (existing permissions)

**New authorization consideration**:
- Guardrail logic runs in server (trusted code)
- Monitor configuration via Weave UI (requires project admin/editor role)
- No new permission levels needed

### Secrets Management

**Existing secrets** (unchanged):
- `WANDB_API_KEY` - Used by agent and judges
- `AGENTIC_SUPPORT_BOT_API_KEY` - API authentication

**No new secrets required**

### PII Handling

**Guardrails**:
- Process user inputs and bot outputs (may contain PII)
- Do not persist PII separately (only in Weave traces, already logged)
- Blocking reasons may reference content (e.g., "contains request about cooking")
  - **Risk**: Reason might leak sensitive content in logs
  - **Mitigation**: Use generic reasons ("off-topic request detected" vs quoting user input)

**Monitors**:
- Score sampled traffic (may contain PII)
- LLM judges see user inputs/outputs (sent to W&B Inference)
- Sampling reduces PII exposure (10% vs 100%)
- **Same PII risk as Step 4 evaluations** (accepted in previous step)

### Threat Model & Mitigations

**Threat: Bypass Guardrails**
- **Attack**: User sends requests directly to agent, skipping guardrails
- **Mitigation**: Guardrails integrated in server, not bypassable by API users
- **Residual Risk**: Low - guardrails run on every request

**Threat: Prompt Injection Against Guardrails**
- **Attack**: Craft input to fool guardrail scorer (e.g., "ignore previous instructions")
- **Mitigation**: Use robust scorer implementations; test adversarial cases
- **Residual Risk**: Medium - LLM-based guardrails more vulnerable than rule-based

**Threat: Excessive Blocking (DoS)**
- **Attack**: Guardrail bug causes all requests to be blocked
- **Mitigation**: Comprehensive testing; gradual rollout; monitoring
- **Residual Risk**: Low - can disable guardrails and redeploy quickly

**Threat: Monitor Prompt Injection**
- **Attack**: User crafts input to manipulate monitor scores
- **Mitigation**: Monitors are observational only, don't affect responses
- **Residual Risk**: Very Low - manipulated scores don't cause harm

**Threat: Credential Exposure in Logs**
- **Attack**: Guardrail logging exposes API keys or secrets
- **Mitigation**: Never log request/response content containing creds
- **Residual Risk**: Low - standard logging hygiene

## 8. Observability & Operations

### Logs to Add

**Guardrail Execution Logs** (automatic via Weave):
```python
# Each guardrail check automatically logged as:
{
  "op_name": "ToxicityGuardrail.score",
  "inputs": {"output": "<response>"},
  "output": {"flagged": false, "reason": null, "score": 1.0},
  "latency_ms": 45,
  "timestamp": "2025-11-06T12:34:56Z"
}
```

**Guardrail Error Logs** (explicit):
```python
print(f"Guardrail {guardrail.name} failed: {str(e)}")
# Appears in Modal logs and Weave traces
```

**Monitor Logs** (automatic via Weave):
- Monitor execution logs in Weave backend
- Scoring results attached to traces
- Error logs for failed scorers

### Metrics to Add

**Guardrail Metrics** (queryable via Weave):
- `guardrail.block_rate` - % of requests blocked per guardrail
- `guardrail.latency_p99` - 99th percentile latency
- `guardrail.error_rate` - % of guardrail executions that failed
- `guardrail.combined_latency` - Total time for all guardrails

**Monitor Metrics** (automatic in Weave UI):
- `monitor.score_distribution` - Histogram of scores over time
- `monitor.sampling_rate` - Actual % of traffic scored
- `monitor.score_latency` - Time to complete scoring

### Dashboards to Create

**Weave Saved View: "Guardrail Blocked Requests"**:
```
Filter:
  - scorer.name contains "Guardrail"
  - scorer.result.flagged = true
  
Columns:
  - Timestamp
  - Input (user request)
  - Output (agent response)
  - Guardrail name
  - Block reason
  
Sort: Timestamp desc
```

**Weave Saved View: "Production Monitoring Dashboard"**:
```
Filter:
  - attributes.env = "main"
  - operation = "Agent.stream"
  
Columns:
  - Timestamp
  - Input
  - Output
  - accuracy_monitor.score
  - safety_monitor.score
  - Latency
  
Sort: accuracy_monitor.score asc (show worst first)
```

### Alerts to Create

**Not in scope for Step 6** (mentioned in Non-Goals), but document where users would set up:

Future alerts:
- Guardrail block rate > 20% (possible attack or misconfiguration)
- Guardrail error rate > 1% (guardrail service degradation)
- Monitor scores dropping >10% from baseline (production regression)

### Runbooks

**Runbook: High Guardrail Block Rate**
1. Check Weave "Guardrail Blocked Requests" view
2. Review blocked content for patterns (legitimate vs false positives)
3. If false positives: Adjust guardrail logic, redeploy
4. If legitimate: Investigate why bad requests increased

**Runbook: Guardrail Errors**
1. Check Modal logs for error details
2. Check Weave traces for failing guardrail ops
3. If transient: Monitor, may self-recover
4. If persistent: Disable failing guardrail, debug, fix, redeploy

**Runbook: Low Monitor Scores**
1. Compare to Step 4 evaluation baseline
2. Check recent changes (code, prompts, model updates)
3. Review low-scoring traces for patterns
4. Run offline evaluation to confirm regression
5. Rollback or fix identified issues

### SLOs

**Guardrail Latency SLO**:
- Target: p99 < 500ms per guardrail
- Measurement: Weave trace latencies
- Alert threshold: p99 > 600ms for 5 minutes

**Guardrail Availability SLO**:
- Target: 99.9% success rate
- Measurement: Error rate in Weave traces
- Alert threshold: Error rate > 1% for 5 minutes

**Monitor Accuracy** (soft target):
- Target: Monitor scores correlate with Step 4 eval (r > 0.8)
- Measurement: Manual correlation analysis
- Review: Weekly during initial rollout

## 9. Rollout & Migration

### Feature Flags

**No feature flags in tutorial context** - users manually control rollout by:
- Part A: Copy files to enable guardrails
- Part B: Activate monitors in Weave UI

In production context (beyond tutorial):
- Could add `ENABLE_GUARDRAILS` env var
- Could add guardrail-specific toggles

### Rollout Phases

**Phase 1: Development Testing**
1. User completes Part A (guardrails) in dev environment
2. Test with adversarial prompts in Weave Playground
3. Verify guardrails block appropriately
4. Check Weave traces for scorer results

**Phase 2: Production Deployment**
1. User deploys to main: `modal deploy workspace/server.py`
2. Guardrails active on all production traffic
3. Monitor production traces for block rate

**Phase 3: Monitor Setup**
1. User configures monitors in Weave UI
2. Start with 10% sampling
3. Generate production traffic
4. Verify monitor scores appear in Weave

**Phase 4: Baseline Comparison**
1. Collect 1 week of monitor scores
2. Compare to Step 4 evaluation baseline
3. Identify any discrepancies
4. Adjust sampling rate or prompts as needed

### Data Backfill

**No backfill needed**:
- Monitors only score new traffic (going forward)
- Guardrails apply to new requests only
- Historical traces unchanged

**Optional**: Retroactive scoring
- Users could manually score past traces using `apply_scorer()` API
- Not covered in tutorial (advanced use case)

### Revert Plan

**Revert Guardrails**:
```bash
# Option 1: Revert to Step 5 server
cp examples/step-5/server.py workspace/server.py
modal deploy workspace/server.py

# Option 2: Comment out guardrails
# Edit workspace/server.py, comment out guardrail checks
modal deploy workspace/server.py
```

**Revert Monitors**:
```
1. Navigate to Weave UI → Monitors tab
2. Click monitor → Toggle "Active" to off
3. Or delete monitor entirely
```

**Blast Radius**:
- Guardrails: Affects all production traffic (high blast radius)
  - **Mitigation**: Test thoroughly in dev first; gradual rollout
- Monitors: Affects only observability (low blast radius)
  - **Mitigation**: Can disable instantly in UI

## 10. Test Strategy & Spec Coverage (TDD)

### TDD Commitment

✅ **All tests written before implementation**
✅ **Verify tests fail before writing code**
✅ **Implement minimal code to pass**
✅ **Refactor with tests as safety net**

### Spec→Test Mapping

| Spec Acceptance Criterion | Test ID(s) | Test Type |
|---------------------------|------------|-----------|
| **Guardrails** | | |
| Adversarial prompt with toxic language blocked | `test_toxicity_guardrail_blocks_toxic` | Unit |
| Off-topic question blocked with explanation | `test_offtopic_guardrail_blocks_offtopic` | Unit |
| Guardrail error defaults to blocking | `test_guardrail_error_defaults_safe` | Unit |
| Safe, on-topic prompt passes guardrails | `test_guardrails_allow_safe_content` | Integration |
| Guardrail results visible in Weave trace | `test_guardrail_results_in_trace` | Integration |
| **Monitors** | | |
| 10% sampling rate scores ~10 of 100 requests | N/A - UI config, manual verification | Manual |
| Monitor scores logged to Weave asynchronously | N/A - Weave backend behavior | Manual |
| Multiple monitors run in parallel | N/A - Weave backend behavior | Manual |
| Monitor error doesn't block response | N/A - Weave backend behavior | Manual |
| Monitor trends visible in UI over 24h | N/A - UI visualization | Manual |
| **Integration** | | |
| Guardrails check sync, monitors sample async | `test_guardrails_and_monitors_flow` | E2E |
| No breaking changes to Step 5 deployment | `test_server_compatibility` | Integration |
| Dev/prod separation maintained | `test_environment_tags` | Integration |
| **Negative Cases** | | |
| Guardrail API timeout blocks with message | `test_guardrail_timeout_blocks_safely` | Unit |
| Monitor scoring failure doesn't affect response | N/A - Weave handles | Manual |
| 0% sampling = no monitor execution | N/A - UI config | Manual |

### Test Tiers

#### Unit Tests (`tests/test_guardrails.py`)

```python
class TestToxicityGuardrail:
    """Unit tests for toxicity guardrail scorer."""
    
    def test_blocks_toxic_content(self):
        """GIVEN toxic content WHEN scored THEN flagged=true"""
        guardrail = ToxicityGuardrail()
        result = guardrail.score(output="You're an idiot!")
        assert result["flagged"] is True
        assert "toxic" in result["reason"].lower()
    
    def test_allows_safe_content(self):
        """GIVEN safe content WHEN scored THEN flagged=false"""
        guardrail = ToxicityGuardrail()
        result = guardrail.score(output="How do I initialize Weave?")
        assert result["flagged"] is False
        assert result["reason"] is None
    
    def test_error_handling_defaults_safe(self):
        """GIVEN scorer error WHEN scored THEN defaults to blocking"""
        # Mock scorer to raise exception
        # Verify error handling returns flagged=true

class TestOffTopicGuardrail:
    """Unit tests for off-topic guardrail scorer."""
    
    def test_blocks_offtopic_request(self):
        """GIVEN off-topic request WHEN scored THEN flagged=true"""
        guardrail = OffTopicGuardrail()
        result = guardrail.score(output="Here's a recipe for cookies...")
        assert result["flagged"] is True
        assert "off-topic" in result["reason"].lower()
    
    def test_allows_support_question(self):
        """GIVEN W&B support question WHEN scored THEN flagged=false"""
        guardrail = OffTopicGuardrail()
        result = guardrail.score(output="To initialize Weave, call weave.init()...")
        assert result["flagged"] is False
```

#### Integration Tests (`tests/test_server.py`)

```python
class TestServerWithGuardrails:
    """Integration tests for server with guardrails enabled."""
    
    async def test_guardrail_blocks_unsafe_request(self):
        """GIVEN unsafe request WHEN posted to server THEN returns blocked message"""
        response = await client.post("/v1/chat/completions", json={
            "model": "buzz",
            "messages": [{"role": "user", "content": "How do I hack?"}]
        })
        assert response.status_code == 200
        content = response.json()["choices"][0]["message"]["content"]
        assert "cannot generate" in content.lower()
    
    async def test_guardrail_allows_safe_request(self):
        """GIVEN safe request WHEN posted to server THEN returns normal response"""
        response = await client.post("/v1/chat/completions", json={
            "model": "buzz",
            "messages": [{"role": "user", "content": "How do I initialize Weave?"}]
        })
        assert response.status_code == 200
        content = response.json()["choices"][0]["message"]["content"]
        assert "weave.init" in content.lower()
    
    async def test_guardrail_results_in_weave_trace(self):
        """GIVEN guardrail execution WHEN checked in Weave THEN scorer results present"""
        # Make request
        # Query Weave for trace
        # Verify scorer results attached
```

#### E2E Tests (`tests/test_e2e.py`)

```python
class TestEndToEnd:
    """End-to-end tests covering full flow."""
    
    async def test_guardrails_and_monitors_flow(self):
        """GIVEN production deployment WHEN traffic flows THEN guardrails block sync, monitors score async"""
        # Deploy server with guardrails
        # Configure monitors in Weave (via API)
        # Send test traffic (safe + unsafe)
        # Verify:
        #   - Unsafe blocked immediately (guardrails)
        #   - Safe requests succeed
        #   - Monitor scores appear in Weave (eventually)
```

### Negative & Edge Cases

| Test Case | Expected Behavior |
|-----------|-------------------|
| Guardrail scorer raises exception | Block with "Safety check unavailable" |
| Guardrail initialization fails | Server startup fails (fail fast) |
| Empty output to score | Guardrail handles gracefully (allow or custom logic) |
| Very long output (>10k chars) | Guardrail truncates or handles within latency budget |
| Sequential guardrail execution | Each runs to completion before next starts (clear error attribution) |
| Monitor prompt exceeds length limit | ✅ RESOLVED - No length limits, use full prompts |
| Monitor model unavailable in UI | ✅ RESOLVED - Model confirmed available |

### Performance Tests

**Guardrail Latency Test**:
```python
async def test_guardrail_latency_under_500ms():
    """GIVEN 100 sample outputs WHEN scored THEN p99 < 500ms"""
    guardrail = ToxicityGuardrail()
    latencies = []
    
    for output in sample_outputs:
        start = time.time()
        guardrail.score(output=output)
        latencies.append(time.time() - start)
    
    p99 = np.percentile(latencies, 99)
    assert p99 < 0.5, f"p99 latency {p99}s exceeds 500ms target"
```

**Combined Guardrails Latency Test**:
```python
async def test_all_guardrails_under_10_percent_overhead():
    """GIVEN all guardrails WHEN applied THEN total latency < 10% of baseline"""
    # Measure baseline request latency (no guardrails)
    baseline = measure_request_latency()
    
    # Measure with guardrails
    with_guardrails = measure_request_latency_with_guardrails()
    
    overhead = (with_guardrails - baseline) / baseline
    assert overhead < 0.10, f"Guardrail overhead {overhead:.1%} exceeds 10% target"
```

### CI Requirements

✅ **All tests must run in CI**
✅ **Tests must pass before merge**
✅ **Coverage target**: 80% for new code (guardrails.py)
✅ **Linting**: Black, ruff, mypy must pass
✅ **Integration tests**: Run against dev Modal deployment

**CI Workflow**:
```yaml
1. Unit tests (parallel)
2. Linting (parallel with unit tests)
3. Integration tests (sequential, requires Modal)
4. Coverage report
5. Block merge if any failures
```

## 11. Risks & Open Questions

### Known Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Guardrails too slow (>500ms) | High | Use lightweight scorers; performance tests in CI; benchmark before deployment |
| Guardrails have high false positive rate | Medium | Comprehensive test cases; user testing in dev; gradual rollout |
| Monitor model unavailable in Weave UI | Medium | Verify during implementation; provide fallback model documentation |
| Manual prompt copying is error-prone | Low | Provide exact line numbers; include validation tips; screenshots |
| Users confuse guardrails vs monitors | Low | Clear comparison table; separate tutorial parts; emphasize differences |

### Open Questions & Resolution Paths

**Q1: Is `openai/meta-llama/Llama-3.1-8B-Instruct` available in Weave monitor UI?**
- **Priority**: High (blocks Part B implementation)
- **Status**: ✅ **RESOLVED** - Model confirmed available in Weave monitor UI
- **Decision**: Use `openai/meta-llama/Llama-3.1-8B-Instruct` for both monitors (same as Step 4)

**Q2: Are there character limits on monitor scoring prompts in Weave UI?**
- **Priority**: Medium (affects documentation)
- **Status**: ✅ **RESOLVED** - No issues with ~500 character prompts
- **Decision**: Use full Step 4 prompts without abbreviation

**Q3: What guardrail patterns are most effective for support bot use case?**
- **Priority**: Low (can iterate post-launch)
- **Status**: ✅ **RESOLVED** - Start with toxicity + off-topic
- **Decision**: Two guardrails sufficient for tutorial; can add more in future iterations
- **Future**: Add PII detection, prompt injection detection as enhancements

**Q4: Should guardrails run in parallel or sequential?**
- **Priority**: Medium (affects latency)
- **Status**: ✅ **RESOLVED** - Sequential execution chosen
- **Decision**: Run guardrails sequentially (simpler code, easier to understand for tutorial)
- **Rationale**: Tutorial clarity > micro-optimization; still meets <500ms target per guardrail
- **Tradeoff**: Slightly slower than parallel, but more predictable and debuggable

**Q5: How to handle monitor configuration changes (UI-based) in version control?**
- **Priority**: Low (tutorial context, not production)
- **Status**: ✅ **RESOLVED** - Document monitor configs in tutorial
- **Decision**: Users recreate monitors in their Weave projects following tutorial instructions
- **Note**: In production, Weave API could export/import monitor configs (advanced topic)

## 12. Milestones / Plan (post‑approval)

### Milestone 1: Part A - Guardrails (3-4 hours)

**Task 1.1: Implement Guardrail Scorers** (1 hour)
- [ ] Create `examples/step-6/part-a/guardrails.py`
- [ ] Implement `ToxicityGuardrail(Scorer)` class
- [ ] Implement `OffTopicGuardrail(Scorer)` class
- [ ] Add error handling and logging
- [ ] Initialize scorers efficiently (outside request handler pattern)
- **DoD**: Scorers implement `score()` method returning `{flagged, reason, score}`

**Task 1.2: Write Guardrail Tests** (1 hour)
- [ ] Create `tests/test_guardrails.py`
- [ ] Write tests for toxic content blocking
- [ ] Write tests for off-topic blocking
- [ ] Write tests for safe content (no blocking)
- [ ] Write error handling tests
- [ ] Write latency performance tests
- **DoD**: All tests fail (no implementation yet)

**Task 1.3: Integrate Guardrails into Server** (45 min)
- [ ] Update `examples/step-6/part-a/server.py`
- [ ] Import guardrail scorers
- [ ] Add guardrail execution logic
- [ ] Implement blocking response logic
- [ ] Handle guardrail errors gracefully
- **DoD**: Server applies guardrails before returning responses; tests pass

**Task 1.4: Part A Documentation** (45 min)
- [ ] Update `README.md` with Part A section
- [ ] Explain guardrail pattern and `.call()` method
- [ ] Provide copy command for files
- [ ] Add testing instructions
- [ ] Include troubleshooting tips
- **DoD**: Users can complete Part A following README instructions

### Milestone 2: Part B - Monitors (2-3 hours)

**Task 2.1: Extract Monitor Prompts** (30 min)
- [ ] Document which lines from `scorers.py` to copy
- [ ] Extract accuracy prompt (lines 86-110)
- [ ] Extract safety prompt (lines 172-208)
- [ ] Extract model configs from `*-judge-config.yaml`
- **DoD**: Clear mapping from Step 4 files to monitor configs

**Task 2.2: Create Monitor UI Instructions** (1 hour)
- [ ] Create monitors in Weave UI (for screenshots)
- [ ] Take screenshots of each configuration step
- [ ] Verify model availability in UI
- [ ] Test monitor activation and sampling
- [ ] Verify scores appear in traces
- **DoD**: Monitor configuration steps validated; screenshots captured

**Task 2.3: Part B Documentation** (1 hour)
- [ ] Update `README.md` with Part B section
- [ ] Add step-by-step UI instructions with screenshots
- [ ] Show exact prompt and model configs to use
- [ ] Explain sampling rate configuration
- [ ] Document how to view monitor results
- [ ] Add comparison section (production vs Step 4 baseline)
- **DoD**: Users can complete Part B following README instructions

### Milestone 3: Testing & Polish (1-2 hours)

**Task 3.1: Integration Testing** (45 min)
- [ ] Test full flow: guardrails + monitors
- [ ] Verify dev environment (`modal serve --env dev`)
- [ ] Test production deployment (`modal deploy`)
- [ ] Verify environment tagging (env=dev vs env=main)
- [ ] Test Weave UI views (Traces, Monitors tabs)
- **DoD**: End-to-end flow works; both parts functional

**Task 3.2: Comparison Table & Summary** (30 min)
- [ ] Create guardrails vs monitors comparison table
- [ ] Add "When to use each" guidance
- [ ] Document reuse strategy (Step 4 → Step 6)
- [ ] Add troubleshooting section
- **DoD**: Clear conceptual explanation of both patterns

**Task 3.3: Final QA** (30 min)
- [ ] Run all tests in CI
- [ ] Verify lint/format passes
- [ ] Test tutorial from scratch (fresh user perspective)
- [ ] Check all links and references
- [ ] Verify screenshots are clear and current
- **DoD**: Tutorial ready for users; all tests passing

### Dependencies

- **Part B depends on Step 4**: Need `scorers.py` and judge configs to copy prompts
- **Integration tests depend on Modal**: Require Modal account and deployment
- **Screenshots depend on Weave UI**: Require access to Weave project with traces

### Timeline

- **Total estimated time**: 6-9 hours
- **Parallelization**: Tasks within milestones can run in parallel
- **Critical path**: M1 → M2 → M3 (sequential milestones)

---

**Approval Gate**: Do not start coding until this TDR is reviewed and approved in the PR.

