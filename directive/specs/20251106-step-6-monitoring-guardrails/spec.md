# Spec (per PR)

**Spec ID**: 20251106  
**Created**: 2025-11-06  

**Feature name**: Step 6 - Online Monitoring & Guardrails  
**One-line summary**: Add real-time safety guardrails and production monitoring to the support bot using Weave Scorers  

---

## Problem

After Step 5, users have deployed their agent to production via Modal, but they have no visibility into production performance or safety mechanisms. They lack:

1. **Safety controls**: No guardrails to prevent toxic, off-topic, or inappropriate responses from reaching users
2. **Production metrics**: No way to track performance (latency, costs, volume, errors) in real-time
3. **Quality monitoring**: No automated scoring of production traffic to identify degrading performance
4. **Failure identification**: No systematic way to find and diagnose production failures

This creates risk for production deployments and missed opportunities for continuous improvement.

## Goal

Enable users to:
1. Implement **guardrails** using custom Python scorers that actively prevent unsafe content before it reaches users
2. Configure **LLM-as-a-judge monitors** through Weave UI, reusing Step 4 evaluation prompts and models for consistency
3. View production metrics and trends in Weave UI
4. Understand the tradeoffs between guardrails (fast, custom code) and monitors (flexible, LLM-based)
5. Compare production monitoring scores to offline eval baseline (same model + same prompts ensure consistency)
6. Identify **failure patterns** by analyzing low-scoring conversations

## Success Criteria

- [ ] Users can add at least 2 guardrails (e.g., toxicity, off-topic detection) that block unsafe responses in real-time
- [ ] Users can create LLM-as-a-judge monitors by reusing Step 4 scorer prompts and models in Weave UI
- [ ] Users can set sampling rates for monitors (e.g., score 10% of production traffic)
- [ ] Monitors run automatically in background after activation (no manual scoring calls)
- [ ] Users can view production monitor trends in Weave UI
- [ ] Users can compare production scores to Step 4 eval baseline (same model + same prompts = apples-to-apples comparison)
- [ ] Users can query low-scoring traces to identify improvement opportunities
- [ ] Step 6 code examples run successfully on first try (no manual fixes required)
- [ ] Documentation clearly explains when to use guardrails (fast, deterministic) vs monitors (flexible, LLM-based)

## User Story

**As a developer deploying an AI agent to production**,  
I want real-time safety controls and automated quality monitoring,  
so that I can prevent unsafe responses, track performance degradation, and systematically identify areas for improvement.

## Flow / States

### Happy Path: Adding Guardrails

1. User copies `examples/step-6/part-a/` files to workspace (includes updated `server.py` with guardrails integrated)
2. User reviews `guardrails.py` which includes:
   - `ToxicityGuardrail` - blocks toxic content
   - `OffTopicGuardrail` - blocks non-support questions
3. User reviews `server.py` to see how guardrails are applied before returning responses
4. User deploys to dev (`modal serve --env dev workspace/server.py`)
5. User tests in Weave Playground with adversarial prompts
6. Guardrails block unsafe content and user sees blocked message
7. User views guardrail results in Weave traces (flagged=true with reason)

### Happy Path: Setting Up Monitors

1. User navigates to Weave project → Monitors tab → "New Monitor"
2. User configures first monitor (e.g., Accuracy Monitor):
   - Name: `accuracy-monitor`
   - Operation: `Agent.stream`
   - Sampling rate: 10%
   - LLM Judge: `openai/meta-llama/Llama-3.1-8B-Instruct` (same as Step 4's `accuracy-judge-config.yaml`)
   - System prompt: Copy from `accuracy-judge-config.yaml`
   - Scoring prompt: **Reuses prompt from Step 4's `accuracy_scorer`** (copy from `scorers.py` lines 86-110)
3. User creates second monitor (e.g., Safety Monitor):
   - Name: `safety-monitor`
   - LLM Judge: `openai/meta-llama/Llama-3.1-8B-Instruct` (same as Step 4's `safety-judge-config.yaml`)
   - Scoring prompt: **Reuses prompt from Step 4's `safety_scorer`** (copy from `scorers.py` lines 172-208)
   - Same sampling rate
4. Monitors activate and begin scoring sampled production traffic automatically
5. User generates traffic and views monitor scores in Weave UI (Monitors tab)
6. User filters by low scores to identify failing conversations
7. User compares monitor scores to Step 4 eval baseline (same model + same prompts = consistent evaluation)

### Edge Case: Guardrail Failure

1. User's toxicity guardrail encounters an error (API timeout)
2. Guardrail defaults to conservative behavior (block with explanation)
3. Error is logged to Weave with flagged=true and reason="Safety check unavailable"
4. User reviews error traces and improves error handling

## UX Links

- Weave Guardrails Documentation: https://docs.wandb.ai/weave/guides/evaluation/guardrails_and_monitors
- Weave Saved Views: https://docs.wandb.ai/weave/guides/tools/saved-views

## Requirements

### Must Have

- **Guardrails must**:
  - Block unsafe content before it reaches users
  - Use Weave's `Scorer` class with `.call()` pattern
  - Return structured results with `flagged` boolean and `reason` text
  - Handle errors gracefully (default to safe behavior)
  - Be fast enough for synchronous execution (<500ms)
  - Log all guardrail checks to Weave for analysis

- **Monitors must**:
  - Be created through Weave UI as LLM-as-a-judge scorers (not custom Python code)
  - Use scoring prompts to evaluate production traffic
  - Score production traffic asynchronously in Weave's backend (not blocking responses)
  - Support configurable sampling rates via UI (e.g., 10%, 100%)
  - Run automatically once activated (no manual `.apply_scorer()` calls needed)
  - Store results in Weave for historical analysis
  - Support filtering and querying low-scoring traces

- **Examples must**:
  - Include at least 2 working guardrails (toxicity, off-topic) integrated in server.py
  - Reference Step 4's `accuracy_scorer` and `safety_scorer` prompts and judge configs for reuse in monitors
  - Provide clear instructions on extracting prompts and model configs from Step 4 and pasting into Weave UI
  - Show proper guardrail initialization (outside main functions for efficiency)
  - Include error handling for guardrail failures
  - Work with existing Modal deployment from Step 5
  - Include screenshots/instructions for creating monitors in Weave UI with same models as Step 4

- **Documentation must**:
  - Explain difference between guardrails vs monitors with clear table (code-based vs UI-based, fast vs flexible)
  - Show when to use each approach (guardrails for speed/determinism, monitors for flexibility/analysis)
  - Explain `.call()` method and why it's needed for guardrails
  - Provide step-by-step instructions for creating monitors in Weave UI
  - Show how to copy Step 4 scorer prompts and model configs into monitor configuration
  - Explain the value of reusing same model + prompts (consistent evaluation between offline and production)
  - Demonstrate analyzing monitor results in Weave UI (Monitors tab)
  - Show how to compare production monitor scores to Step 4 eval baseline (apples-to-apples with same judges)
  - Include troubleshooting for common guardrail and monitor issues

### Must Not

- Must not require additional infrastructure beyond Weave (use existing Modal deployment)
- Must not make guardrails optional (they are critical for safety)
- Must not require custom Python code for monitors (use Weave's LLM-as-a-judge UI)
- Must not require manual instrumentation for monitors (automatic scoring after activation)
- Must not slow down response times with monitors (they run asynchronously on Weave's backend)
- Must not slow down response times significantly with guardrails (<10% latency increase)

## Acceptance Criteria

### Guardrails

- **Given** an adversarial prompt with toxic language, **when** user invokes agent, **then** guardrail blocks response and returns safe message
- **Given** an off-topic question unrelated to support, **when** user invokes agent, **then** guardrail blocks response and explains scope limitation
- **Given** a guardrail encounters an error, **when** checking content, **then** defaults to blocking with error explanation
- **Given** a safe, on-topic prompt, **when** user invokes agent, **then** guardrails pass and normal response is returned
- **Given** guardrail execution, **when** checking trace in Weave, **then** user sees scorer results with flagged status and reason

### Monitors

- **Given** monitor with 10% sampling rate, **when** 100 requests processed, **then** approximately 10 are scored
- **Given** monitor configured for quality scoring, **when** request processed, **then** score is logged to Weave asynchronously
- **Given** multiple monitors enabled, **when** request sampled, **then** all monitors run in parallel
- **Given** monitor encounters error, **when** scoring request, **then** error is logged but response is not blocked
- **Given** production traffic over 24 hours, **when** viewing Weave UI, **then** user sees score trends over time

### Integration

- **Given** all Step 6 components enabled, **when** agent processes request, **then** guardrails check synchronously, monitors sample asynchronously
- **Given** Step 5 deployment exists, **when** adding Step 6 code, **then** no breaking changes to existing functionality
- **Given** Step 6 running in production, **when** viewing Weave, **then** user sees separate metrics for dev (env=dev) and prod (env=main)

### Negative Cases

- **Given** guardrail API times out, **when** checking content, **then** response is blocked with "Safety check unavailable" message
- **Given** monitor scoring fails, **when** processing request, **then** response proceeds normally (monitor failure doesn't block)
- **Given** sampling rate set to 0%, **when** processing requests, **then** no monitors execute but guardrails still run

## Non-Goals

- Custom monitor UIs outside Weave (use Weave's built-in visualization)
- Real-time alerting on low scores (future enhancement, mention in "Next Steps")
- A/B testing frameworks (covered in Step 7)
- User feedback collection (deferred to future step)
- Integration with external monitoring tools (Datadog, etc.)
- Automated remediation based on scores (human-in-the-loop required)
- Guardrail customization UI (users edit Python code directly)
- Performance benchmarking suite (focus on monitoring capabilities)

