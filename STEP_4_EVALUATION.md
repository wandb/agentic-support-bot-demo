# Step 4: Dataset & Evaluation - Production Readiness

After Step 3, your support bot works well in demos. But is it ready for production? Step 4 teaches you how to move from "vibes-based" testing to systematic evaluation.

## What You'll Build

1. **Evaluation Dataset**: 64 diverse test cases covering realistic scenarios, edge cases, and adversarial inputs
2. **Multiple Scorers**: Rule-based (tool correctness) and LLM-as-judge (accuracy, safety)
3. **Evaluation Pipeline**: Automated testing using Weave's EvaluationLogger
4. **Results Analysis**: Track metrics and identify failure patterns in Weave UI

## Quick Start

All example code is in `examples/step-4-complete/`:

### 1. Review the Dataset

```bash
# View 64 test cases covering W&B questions, tool usage, and refusals
cat examples/step-4-complete/dataset.py
```

**Dataset includes:**
- 31 W&B/Weave questions (initialization, debugging, features)
- 16 tool usage scenarios (ticket creation/retrieval)
- 18 refusal scenarios (off-topic, inappropriate, adversarial)

### 2. Publish Dataset to Weave

```bash
# Publish dataset for version tracking
uv run python examples/step-4-complete/publish_dataset.py
```

Verify in Weave UI: https://wandb.ai/ → `agentic-support-bot-demo` → Datasets tab

### 3. Run Evaluation

⚠️ **COST WARNING**: Full evaluation with LLM judges costs **$3-5** for 64 test cases.

```bash
# Test on 10 random cases first (costs ~$0.50)
uv run python examples/step-4-complete/run_evaluation.py --sample 10

# Run full evaluation (costs $3-5)
uv run python examples/step-4-complete/run_evaluation.py

# Skip expensive LLM judges (free!)
uv run python examples/step-4-complete/run_evaluation.py --no-llm-judges
```

### 4. Analyze Results

View results in Weave UI:
1. Go to https://wandb.ai/
2. Open project: `agentic-support-bot-demo`
3. Click **Evals** tab
4. Drill into individual predictions
5. Compare multiple evaluation runs

## Understanding the Components

### Dataset Structure

Each test case has:
```python
{
    "input": "How do I initialize Weave?",
    "expected_output": "Call weave.init() with project name",
    "expected_tools": [],  # Tools that should be called
    "tags": ["weave", "initialization", "factual"]
}
```

### Three Types of Scorers

**1. Rule-Based Scorer (Fast, Free):**
```python
@weave.op()
def tool_usage_scorer(input, output):
    """Did the bot call the correct tools?"""
    expected = set(input["expected_tools"])
    actual = set(output["tools_used"])
    return {"score": 1.0 if expected == actual else 0.0}
```

**2. LLM-as-Judge: Accuracy (Flexible, Costs Money):**
```python
@weave.op()
def accuracy_scorer(input, output):
    """Is the answer accurate and helpful?"""
    # Uses GPT-4.1 to evaluate response quality
    # Returns score 0.0-1.0
```

**3. LLM-as-Judge: Safety (Catches Harmful Content):**
```python
@weave.op()
def safety_scorer(input, output):
    """Safe, appropriate, with proper refusals?"""
    # Evaluates tone, refusal appropriateness, safety
    # Returns multiple scores
```

### Evaluation Workflow (EvaluationLogger)

```python
# 1. Initialize BEFORE agent calls (for token tracking!)
eval_logger = EvaluationLogger(
    model="support-bot-v1",
    dataset="support-bot-eval-dataset"
)

# 2. For each test case:
for test_case in dataset.rows:
    output = invoke_agent(agent, test_case["input"])
    
    pred_logger = eval_logger.log_prediction(
        inputs={"query": test_case["input"]},
        output=output
    )
    
    pred_logger.log_score(scorer="tool_usage", score=...)
    pred_logger.log_score(scorer="accuracy", score=...)
    pred_logger.log_score(scorer="safety", score=...)
    
    pred_logger.finish()

# 3. Finalize
eval_logger.log_summary()
```

## What You Learn

### Dataset Design
- **Coverage matters**: Diverse scenarios > large quantity
- **Test refusals**: Off-topic and adversarial inputs are critical
- **Edge cases reveal blind spots**: Prompt injection, jailbreaks, nonsense

### Evaluation Strategy
- **Multiple scorer types**: Combine rule-based and LLM judges
- **Cost management**: Sample first, use cheaper models for judges
- **Track over time**: Compare eval runs to measure progress

### Production Readiness
After Step 4, you can confidently say:
- ✅ Bot handles diverse realistic questions
- ✅ Bot appropriately refuses harmful requests
- ✅ Bot uses tools correctly (measurable with tests)
- ✅ You have metrics to track improvements
- ✅ You can test changes before deployment

## Files Created

```
examples/step-4-complete/
├── dataset.py              # 64 test cases
├── publish_dataset.py      # Publish to Weave
├── scorers.py              # Rule-based + LLM judges
└── run_evaluation.py       # EvaluationLogger workflow

tests/
├── test_dataset.py         # 18 dataset validation tests
└── test_scorers.py         # 20 scorer unit tests
```

## Running Tests

```bash
# Validate dataset structure and coverage
uv run pytest tests/test_dataset.py -v

# Validate scorer implementations
uv run pytest tests/test_scorers.py -v

# Run all Step 4 tests
uv run pytest tests/test_dataset.py tests/test_scorers.py -v
```

All 38 tests should pass ✅

## Cost Breakdown

| Component | Cost per Run | Notes |
|-----------|--------------|-------|
| Agent calls (64 cases) | ~$1.00 | Using DeepSeek via W&B Inference |
| Accuracy judges (64) | ~$1.50 | Using gpt-4o-mini |
| Safety judges (64) | ~$1.50 | Using gpt-4o-mini |
| **Total** | **~$3-5** | For full evaluation |

**Cost-saving tips:**
- Sample first: `--sample 10` costs only ~$0.50
- Skip LLM judges: `--no-llm-judges` is free
- Use cheaper judge models: Set `JUDGE_MODEL=gpt-4o-mini`

## Next Steps

- **Iterate on failures**: Use eval results to improve prompts and tools
- **Expand dataset**: Add real user questions as you get them
- **Monitor in production**: Track metrics on live traffic
- **Continuous evaluation**: Run evals in CI on every change

## Key Takeaways

1. **Manual testing ≠ Production readiness**: Systematic evaluation reveals blind spots
2. **Dataset quality > quantity**: 64 diverse cases beat 200 similar ones
3. **Multiple scorers work together**: Rule-based + LLM judges for complete coverage
4. **Evaluation is iterative**: Run → identify failures → improve → re-evaluate
5. **Cost management matters**: Sample first, use cheaper models, skip expensive scorers in dev

---

For detailed implementation, see:
- **Spec**: `directive/specs/step-4-dataset-and-evaluation/spec.md`
- **Impact Analysis**: `directive/specs/step-4-dataset-and-evaluation/impact.md`
- **TDR**: `directive/specs/step-4-dataset-and-evaluation/tdr.md`

