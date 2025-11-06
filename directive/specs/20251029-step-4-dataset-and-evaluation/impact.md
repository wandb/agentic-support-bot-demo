# Impact Analysis — Step 4: Dataset & Evaluation

## Modules/packages likely touched

### New files:
- **`examples/step-4-complete/dataset.py`** - Dataset definition with 50+ test cases
- **`examples/step-4-complete/publish_dataset.py`** - Script to publish dataset to Weave
- **`examples/step-4-complete/scorers.py`** - Custom scorer implementations (tool correctness, LLM judges)
- **`examples/step-4-complete/run_evaluation.py`** - Evaluation execution script using EvaluationLogger

### Modified files:
- **`README.md`** - Add comprehensive Step 4 section with:
  - Challenge narrative ("Questions a Real User Would Face")
  - Two-script workflow explanation (publish → evaluate)
  - EvaluationLogger pattern explanation
  - How to interpret results in Weave UI
  - Cost warnings and sampling guidance
  
- **`tests/`** - Add new test files:
  - `tests/test_dataset.py` - Validate dataset structure, coverage requirements
  - `tests/test_scorers.py` - Validate scorer implementations don't crash on various inputs
  - Unit tests for scorer logic (e.g., tool matching, score calculation)

### Potentially modified:
- **`pyproject.toml`** - May need to add dependencies if scorers require additional packages
  - Likely no changes needed - Weave already included
  - OpenAI client already present for LLM judges

### Unchanged (referenced):
- **`examples/step-3-complete/tyler-chat-config.yaml`** - Agent config used by evaluation
- **`examples/step-3-complete/tools.py`** - Tools called by agent during evaluation
- **`playground_server.py`** - Not used in evaluation, but agent uses same logic

## Contracts to update (APIs, events, schemas, migrations)

### Dataset Schema Contract:
- **Format**: List of dicts with specific keys
  ```python
  {
    "input": str,              # User's question/request
    "expected_output": str | dict,  # Expected answer content
    "expected_tools": list[str]     # Tool names that should be called
  }
  ```
- **Weave Dataset contract**: Must publish using `weave.Dataset(name="...", rows=[...])`
- **Version tracking**: Each dataset publish creates a new version in Weave
- **No breaking changes**: Dataset is new, no existing contract to break

### Scorer Interface Contract:
- **Custom scorers** must follow Weave patterns:
  - Function-based: `@weave.op()` decorated function
  - Class-based: Inherit from `weave.Scorer` and implement `score()`
  - Return type: `dict` with metric names and values
  - Parameters: Must accept `output`, optionally `input` for reference-based scoring
  
- **Builtin scorers**: Use as documented in https://docs.wandb.ai/weave/guides/evaluation/builtin_scorers
  - No custom contract needed, follow Weave's API

### EvaluationLogger Workflow Contract:
- **Initialization**: `EvaluationLogger(model=..., dataset=...)` before LLM calls
- **Per-prediction workflow**:
  1. `pred_logger = eval_logger.log_prediction(inputs=..., output=...)`
  2. `pred_logger.log_score(scorer=..., score=...)`
  3. `pred_logger.finish()`
- **Summary**: `eval_logger.log_summary(...)` to finalize
- **Critical ordering**: Initialize logger BEFORE any LLM calls to capture token usage

### Agent Invocation Contract:
- Evaluation needs to invoke the agent for each test case
- Must use same config/tools as Step 3 (`tyler-chat-config.yaml`, `tools.py`)
- Need to call agent programmatically, not via CLI
- May need to extract agent creation logic into reusable function

## Risks

### Security:
- **Medium risk**: Dataset may contain sensitive examples
  - **Impact**: Dataset is published to Weave, visible to team members
  - **Mitigation**: 
    - Use only public W&B documentation questions (no proprietary info)
    - No real user data or PII in test cases
    - Review dataset before publishing
  
- **Low risk**: LLM-as-judge API keys
  - **Impact**: Scorers make LLM calls using W&B API key
  - **Mitigation**: Already using env vars for API keys, same pattern as existing code
  
- **Low risk**: Adversarial test cases
  - **Impact**: Dataset includes prompt injection attempts and adversarial inputs
  - **Mitigation**: These are intended test cases, not real attacks. Agent is already sandboxed with mock tools.

### Performance/Availability:
- **High risk**: Evaluation runtime and costs
  - **Impact**: 
    - 50+ test cases × LLM inference = significant latency
    - LLM-as-judge scorers double the API calls (prediction + judge)
    - Could take 5-10+ minutes to run full evaluation
    - Costs could be $1-5 per full evaluation run (depends on model choices)
  - **Mitigation**:
    - Document expected runtime and costs prominently
    - Provide sampling guidance (test on 10 cases first)
    - Suggest using cheaper models for judges (gpt-4o-mini vs gpt-4.1)
    - Show how to run evaluation on subset of dataset
    - EvaluationLogger supports incremental logging (can resume if interrupted)
  
- **Medium risk**: Rate limiting
  - **Impact**: Rapid sequential LLM calls may hit API rate limits
  - **Mitigation**: 
    - Document potential for rate limits
    - EvaluationLogger handles this gracefully (will show errors per prediction)
    - Suggest using W&B Inference which has generous limits

### Data integrity:
- **High risk**: Dataset quality directly impacts usefulness
  - **Impact**: 
    - Poor test coverage = false confidence
    - Biased dataset = misleading metrics
    - Incorrect expected_output values = invalid scoring
  - **Mitigation**:
    - Spec requires minimum coverage (50+ cases, diverse types)
    - Tests validate dataset structure
    - Manual review of dataset before inclusion
    - Documentation explains what makes a good test case
    - Examples include comments explaining rationale for expected values
  
- **Medium risk**: Scorer correctness
  - **Impact**: Buggy scorers = misleading evaluation results
  - **Mitigation**:
    - Unit tests for scorer logic
    - Test scorers on known good/bad outputs
    - Document scorer limitations (LLM judges are probabilistic)
    - Show example scorer outputs in README

### Cost Management:
- **High risk**: Unexpected evaluation costs
  - **Impact**: Running full eval with LLM judges can cost $1-5+ per run
  - **Mitigation**:
    - **Prominent cost warnings** in README
    - Show token counts and estimated costs after eval runs
    - EvaluationLogger automatically tracks token usage
    - Provide sampling scripts (evaluate on 10 random cases)
    - Suggest using cheaper models for development iterations

### User Experience:
- **Medium risk**: Evaluation complexity intimidates users
  - **Impact**: Users skip evaluation step, miss learning opportunity
  - **Mitigation**:
    - "Challenge first" narrative builds intuition before showing code
    - Clear step-by-step workflow (publish → evaluate)
    - Complete working example to copy/modify
    - Screenshots of Weave UI showing results
  
- **Low risk**: Evaluation results are hard to interpret
  - **Impact**: Users don't know what to do with scores
  - **Mitigation**:
    - README explains what good scores look like
    - Show how to drill into failures in Weave UI
    - Provide interpretation guidance (e.g., "70% tool accuracy is good for v1")

### Dependency Management:
- **Low risk**: Weave API changes
  - **Impact**: EvaluationLogger API or Dataset API could change
  - **Mitigation**:
    - Pin Weave version in pyproject.toml
    - Link to official docs for each API used
    - Monitor Weave releases for breaking changes

## Observability needs

### Logs:
- **Automatic via Weave**:
  - All evaluation runs logged to Weave Evals tab
  - Per-prediction inputs, outputs, and scores tracked
  - Dataset references preserved (link to dataset version used)
  - Model and config metadata captured
  
- **Token usage tracking**:
  - EvaluationLogger captures token counts if initialized before LLM calls
  - Critical for cost monitoring
  - Displayed in Weave UI per evaluation run
  
- **Error logging**:
  - Failed predictions logged with error details
  - Scorer failures tracked per prediction
  - `log_summary()` aggregates success/failure rates

### Metrics:
- **Automatic aggregation by Weave**:
  - Mean/median/stddev for numeric scores
  - Distribution of boolean scores (% correct)
  - Per-scorer metrics tracked separately
  
- **Custom metrics in log_summary()**:
  - Overall evaluation time
  - Total cost estimate
  - Pass/fail rates by question type (if tagged)
  - Any domain-specific aggregations

- **Comparison metrics**:
  - Weave Evals tab supports side-by-side comparison
  - Track metrics across multiple evaluation runs
  - Identify regressions when config changes

### Alerts:
- **None required**: Development-time evaluation only
- No production deployment in this step
- Users review results manually in Weave UI

### Weave UI Integration:
- **Datasets tab**: Published dataset visible with all rows
- **Evals tab**: All evaluation runs with aggregate metrics
- **Individual predictions**: Click into eval to see per-case results
- **Comparisons**: Select multiple evals to compare side-by-side
- **Traces**: Link from eval predictions to full agent traces

## Testing considerations

### What to test (automated):
- **Dataset structure validation**:
  - All rows have required keys (input, expected_output, expected_tools)
  - At least 50 rows exist
  - Diversity requirements met (X% tool usage, Y% refusals, etc.)
  - expected_tools values are valid tool names
  
- **Scorer logic**:
  - Tool matching scorer correctly identifies matching/non-matching tools
  - Scorers don't crash on missing fields
  - Scorers return properly formatted dicts
  - Score values are in valid ranges (0-1 for normalized scores)
  
- **Scripts run without errors**:
  - `publish_dataset.py` can be imported without errors
  - `run_evaluation.py` can be imported without errors
  - Dataset can be loaded and validated

### What NOT to test (manual only):
- **Full evaluation runs**: Too expensive and slow for CI
  - Manual testing only
  - Document how to run locally
  
- **LLM judge quality**: Can't unit test LLM behavior
  - Test that judges run without errors
  - Can't validate judge correctness in CI
  
- **Weave UI workflows**: Manual verification
  - Published dataset appears correctly
  - Eval results display properly
  - Comparison views work

### CI implications:
- **Fast validation tests only**:
  - Dataset structure validation (<1 second)
  - Scorer unit tests (<5 seconds)
  - No actual LLM calls in CI
  
- **Mock LLM responses for scorer tests**:
  - Test scorer logic with synthetic outputs
  - Validate error handling
  
- **No Weave publishing in CI**:
  - Would pollute Weave project with test data
  - Validate code structure only

## Dependencies added/updated

### Likely no new dependencies:
- `weave` - Already in pyproject.toml (core dependency)
- `openai` - Already present for LLM calls
- `pydantic` - Already present (Tyler dependency)

### Potential additions:
- If using specific builtin scorers that require extra packages
- Check Weave docs for scorer-specific dependencies

## Migration path

### For existing tutorial users:
- **No migration needed**: Step 4 is a new additive step
- Users who completed Steps 1-3 can proceed directly
- No changes to existing steps required

### For the tutorial itself:
- README gets new Step 4 section (no changes to Steps 1-3)
- New files in examples/step-4-complete/ directory
- No impact on existing example directories

## Rollback plan

### If Step 4 needs to be removed:
1. Delete `examples/step-4-complete/` directory
2. Remove Step 4 section from README
3. Remove Step 4 tests from test suite
4. No impact on Steps 1-3 (fully independent)

### If evaluation approach needs to change:
- EvaluationLogger is flexible - can swap scorers easily
- Dataset can be republished with corrections
- No breaking changes to other steps

