# Spec (per PR)

**Feature name**: Step 4: Dataset & Evaluation  
**One-line summary**: Add comprehensive evaluation capabilities to move the support bot from "vibes-based" testing to production-ready systematic evaluation

---

## Problem
After Step 3, developers have a support bot that "feels right" based on manual testing with a handful of prompts in the Weave Playground. However, this ad-hoc testing approach doesn't provide confidence for production deployment. Developers face critical questions:

- Is the bot reliable enough for real users?
- Will it handle edge cases and adversarial inputs appropriately?
- How do we measure improvement objectively?
- What types of questions might break the bot?
- Are we missing important test scenarios?

Without systematic evaluation, developers risk deploying agents that work well in demos but fail in production with real user traffic.

## Goal
Provide a complete evaluation framework that enables developers to systematically test their support bot against a comprehensive dataset and measure performance with both simple and sophisticated scoring metrics. This includes creating a realistic test dataset of 50+ cases and implementing multiple scorer types (simple rule-based and LLM-judge scorers).

## Success Criteria
- [ ] Dataset contains at least 50 diverse test cases covering realistic scenarios
- [ ] Dataset includes both questions the bot should answer AND questions it should refuse
- [ ] At least 3 different scorer types implemented (tool correctness, LLM accuracy judge, LLM safety judge)
- [ ] Evaluation can be run programmatically and results tracked in Weave
- [ ] Tutorial follows the "challenge first, solution in examples/" pattern used in previous steps
- [ ] Developers gain confidence in their bot's production-readiness

## User Story
As a developer who has built a support bot that works in demos, I want a systematic way to evaluate its behavior across diverse scenarios, so that I can confidently deploy it to production knowing it handles both common cases and edge cases appropriately.

## Flow / States
**Happy Path**:
1. Developer completes Step 3 with a working support bot
2. Developer is presented with the "challenge" - think about what test cases matter
3. Developer attempts to create a dataset and scorers themselves (optional, can skip)
4. Developer examines the complete example in `examples/step-4-complete/`
5. Developer runs `publish_dataset.py` to publish dataset to Weave
6. Developer verifies dataset appears in Weave UI Datasets section
7. Developer runs `run_evaluation.py` to execute evaluation using EvaluationLogger
8. Developer reviews results in Weave UI Evals tab to understand strengths/weaknesses
9. Developer examines individual predictions and scores to identify failure patterns
10. Developer iterates on bot configuration based on eval results

**Edge Cases**:
- Developer's dataset is too small or biased - documentation explains coverage principles
- Dataset publishing fails - check Weave connection and API key
- Scorer implementation has bugs - tests validate scorer logic
- LLM judge is expensive - documentation warns about costs and suggests sampling strategies
- EvaluationLogger not initialized before LLM calls - token tracking won't work, documentation warns
- Evaluation reveals poor performance - this is actually success! Now they know what to fix.

## UX Links
- Example evaluation scripts: TBD in examples/step-4-complete/
- Weave EvaluationLogger docs: https://docs.wandb.ai/weave/guides/evaluation/evaluation_logger
- Weave Scorers docs: https://docs.wandb.ai/weave/guides/evaluation/scorers
- Weave Builtin Scorers: https://docs.wandb.ai/weave/guides/evaluation/builtin_scorers
- Weave Datasets docs: https://docs.wandb.ai/weave/guides/core-types/datasets
- Tutorial narrative in README Step 4 section

## Requirements

### Dataset Requirements
- Must create a dataset with at least 50 test cases
- Each row must include:
  - `input`: The user's question/request (string)
  - `expected_output`: A description or key points the answer should contain (string or dict)
  - `expected_tools`: List of tool names that should be called, or empty list (list)
- Must include realistic Weights & Biases questions covering:
  - Weave initialization and setup
  - Common debugging scenarios (timeouts, authentication, etc.)
  - W&B features (experiments, artifacts, sweeps)
  - Support ticket creation and retrieval
- Must include questions the bot should NOT answer:
  - Off-topic requests (non-W&B questions)
  - Inappropriate requests (explicit content, harmful instructions)
  - Requests outside the bot's capabilities
  - Attempts to manipulate the bot's behavior or extract system prompts
- Must cover diverse scenarios:
  - Simple factual questions
  - Multi-step problems requiring tool usage
  - Ambiguous questions requiring clarification
  - Edge cases and error scenarios
- Dataset must be stored as Python data structure (list of dicts) for easy version control
- Must use `weave.Dataset` to publish dataset to Weave for tracking and versioning
- Must provide a separate script (`publish_dataset.py`) that publishes the dataset to Weave
- Dataset should follow Weave's dataset schema as documented at https://docs.wandb.ai/weave/guides/core-types/datasets

### Scorer Requirements
- Must implement at least 3 different scorer types:
  1. **Simple rule-based scorer**: Check if correct tools were used (custom scorer)
  2. **LLM-as-judge accuracy scorer**: Evaluate if the answer is accurate and helpful (custom scorer)
  3. **Builtin scorer**: Use at least one Weave builtin scorer from https://docs.wandb.ai/weave/guides/evaluation/builtin_scorers
- All custom scorers must follow Weave's Scorer patterns as documented at https://docs.wandb.ai/weave/guides/evaluation/scorers:
  - Use `@weave.op()` decorator for function-based scorers, OR
  - Use class-based scorers inheriting from `weave.Scorer`
- Scorers must return dict with clear metric names and values
- LLM judges must use structured prompts with clear evaluation criteria
- LLM judges should use gpt-4.1 by default (per user rule)
- Scorers must handle missing fields gracefully (not crash on unexpected input)
- Must document trade-offs (cost, speed, reliability) for each scorer type
- Scorers should accept standard parameters: `output`, and optionally `input` for reference-based evaluation

### Tutorial/Documentation Requirements
- Must follow Step 3's pattern: "challenge first, then solution"
- Must explain WHY evaluation matters (production readiness, not just vibes)
- Must include a "Questions a Real User Would Face" section discussing:
  - How many test cases are enough?
  - How to choose what to test?
  - How to measure subjective qualities?
  - When to use LLM-as-judge vs simple rules?
  - What are the trade-offs of different evaluation approaches?
- Must provide complete working example in `examples/step-4-complete/`
- Must explain the two-step workflow:
  1. First run `publish_dataset.py` to publish dataset to Weave
  2. Then run `run_evaluation.py` to execute evaluation using EvaluationLogger
- Must explain the EvaluationLogger incremental workflow:
  - Initialize logger before making LLM calls (for token tracking)
  - Log predictions incrementally with `log_prediction()`
  - Log scores for each prediction with `log_score()`
  - Finish each prediction with `finish()`
  - Summarize with `log_summary()`
- Must explain how to interpret evaluation results
- Must show how evaluation results appear in Weave UI (Evals tab)
- Must document costs and provide guidance on using sampling for expensive scorers

### Code Structure Requirements
- Create `examples/step-4-complete/dataset.py` - dataset definition (list of dicts)
- Create `examples/step-4-complete/publish_dataset.py` - script to publish dataset to Weave using `weave.Dataset`
- Create `examples/step-4-complete/scorers.py` - custom scorer implementations using `@weave.op()` or `weave.Scorer`
- Create `examples/step-4-complete/run_evaluation.py` - evaluation script using `weave.EvaluationLogger`
- Evaluation script must use `EvaluationLogger` pattern as documented at https://docs.wandb.ai/weave/guides/evaluation/evaluation_logger
- Update README with Step 4 section following existing tutorial style
- Add tests validating dataset structure and scorer logic
- Must not duplicate tools or config - reference existing files where appropriate

## Acceptance Criteria

**Dataset Quality**:
- Given the dataset, when reviewed, then at least 50 unique test cases exist
- Given the dataset, when analyzed, then at least 5 cases test refusal scenarios (off-topic/inappropriate)
- Given the dataset, when analyzed, then at least 10 cases require tool usage
- Given the dataset, when analyzed, then at least 10 realistic W&B questions are included
- Given the dataset, when analyzed, then diverse question types are represented (factual, procedural, troubleshooting, multi-turn)

**Scorer Functionality**:
- Given a test case where correct tools were used, when the tool_usage_scorer runs, then it returns `{"correct_tools": true}`
- Given a test case where wrong tools were used, when the tool_usage_scorer runs, then it returns `{"correct_tools": false}`
- Given a test case with a good answer, when the accuracy_scorer runs, then it returns a high score (>0.7)
- Given a test case with a poor answer, when the accuracy_scorer runs, then it returns a low score (<0.3)
- Given a test case where the bot should refuse, when the safety_scorer runs, then it correctly identifies whether refusal occurred
- Given a test case with inappropriate content in the response, when the safety_scorer runs, then it flags the issue

**Dataset Publishing**:
- Given the dataset definition exists, when `publish_dataset.py` is run, then dataset is published to Weave successfully
- Given the dataset is published, when viewing Weave UI, then the dataset appears in the Datasets section with all 50+ rows
- Given the dataset is published, when accessed programmatically, then it can be retrieved using Weave's dataset API

**Evaluation Execution**:
- Given the evaluation script uses `EvaluationLogger`, when run with proper environment variables, then all test cases execute without errors
- Given the evaluation uses `EvaluationLogger.log_prediction()`, when predictions are made, then each prediction is logged incrementally
- Given scorers are implemented, when `log_score()` is called for each prediction, then scores are recorded correctly
- Given the evaluation completes with `log_summary()`, when checking Weave, then results are logged with clear metrics
- Given the evaluation completes, when reviewing results, then per-case scores and aggregate metrics are both available
- Given the evaluation completes, when checking costs, then token usage is tracked and visible (due to EvaluationLogger initialization before LLM calls)

**Tutorial Experience**:
- Given a developer reads Step 4 README, when they reach the challenge section, then clear guiding questions help them think about evaluation
- Given a developer examines the example solution, when they read the code, then comments explain key decisions
- Given a developer runs the example evaluation, when it completes, then they understand how to interpret results

## Non-Goals
- Building a UI for dataset creation (code-based dataset is fine)
- Implementing human-in-the-loop evaluation (automated only)
- Creating a CI/CD pipeline for continuous evaluation (manual execution is fine)
- Fine-tuning models based on evaluation results (out of scope)
- Implementing advanced techniques like prompt optimization or DSPy (keep it simple)
- Production monitoring or alerting (this is development-time evaluation)
- Multi-turn conversation evaluation (single-turn test cases only)
- Comparative evaluation across multiple agent versions (single version at a time)

