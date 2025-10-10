# Impact Analysis — Tyler Agent Foundation

## Modules/packages likely touched
- `main.py` — Completely refactored from hello world to Tyler agent with streaming execution
- `tools.py` — New file containing custom tool implementations and definitions
- `tests/` — New directory with comprehensive test suite
  - `tests/test_main.py` — 8 test cases covering all acceptance criteria
  - `tests/conftest.py` — Pytest fixtures to prevent real API calls
- `.env.example` — New template file for environment variables
- `.github/workflows/test.yml` — New CI workflow for automated testing
- `pyproject.toml` — New dependencies:
  - `slide-tyler` (Tyler agent core - includes LiteLLM for model access)
  - `slide-lye` (tool utilities for custom tool implementations)
  - `weave` (Weights & Biases Weave for observability)
  - `python-dotenv` (for loading environment variables from .env file)
  - `pytest` + `pytest-mock` (dev dependencies for testing)
- `.python-version` — Updated to Python 3.12+
- `README.md` — Comprehensive documentation with setup and usage instructions

## Contracts to update (APIs, events, schemas, migrations)

### New Tool Schemas (Internal Contracts)
Two new tool definitions that will be registered with the Tyler agent:

1. **`create_issue` tool schema**:
   - Input: `title` (string), `description` (string), optional `priority` (string)
   - Output: Mock issue object with `id`, `title`, `status`, `created_at`

2. **`get_issue` tool schema**:
   - Input: `issue_id` (string/int)
   - Output: Mock issue object with `id`, `title`, `description`, `status`, `created_at`

### External API Dependencies
- **LLM Provider (via Tyler/LiteLLM)**: Tyler uses LiteLLM for model access
  - Supporting 100+ providers (OpenAI, Anthropic, etc.)
  - For OpenAI's gpt-4.1: Requires `OPENAI_API_KEY` environment variable (optional - can be configured per provider)
  - Rate limits apply based on provider and organization tier

- **Weights & Biases Weave API**: New dependency for observability
  - Requires `WANDB_API_KEY` environment variable (REQUIRED)
  - Project will be created/accessed: "agentic-support-bot-demo"
  - Can be disabled in CI/tests with `WANDB_MODE=disabled`

## Risks

### Security
- **API Key Exposure**: API keys must be managed securely
  - `WANDB_API_KEY` (required), `OPENAI_API_KEY` (optional)
  - Using `.env` file for local development (already in `.gitignore`)
  - `.env.example` template provided (without actual keys)
  - CI uses environment variables with test values
  - Mitigation: Fail fast with clear error if WANDB_API_KEY missing
- **Prompt Injection**: Agent will execute based on LLM output with tool access
  - Mitigation: Tools are stubbed with no real system access (for now)
  - Future: Need input validation when tools are implemented
- **Test Isolation**: Tests must not make real API calls
  - Mitigation: `conftest.py` auto-mocks all API calls
  - CI sets `WANDB_MODE=disabled` as additional safeguard

### Performance/Availability
- **OpenAI API Dependency**: Script depends on OpenAI API availability
  - Network failures or API outages will cause script failure
  - Mitigation: Consider adding retry logic in future iterations
- **Rate Limits**: OpenAI API has rate limits that could cause failures
  - Mitigation: Not critical for demo/development use
- **Cost**: Each agent execution incurs OpenAI API costs
  - Mitigation: Using efficient model (gpt-4.1), costs manageable for development

### Data integrity
- **Low Risk**: No persistent data storage in this iteration
- **Weave Data**: Agent interactions logged to W&B cloud
  - Consider: What data is being sent to Weave (prompts, responses, tool calls)
  - Mitigation: Document what Weave captures; ensure no sensitive data in demo prompts

## Observability needs

### Logs
- **Script Execution Logs**:
  - Agent initialization success/failure
  - Tool registration confirmation
  - Weave initialization status
  - Any errors during execution

### Metrics (via Weave)
- **Automatic Weave Tracking**:
  - LLM call latency and token usage
  - Tool invocation counts (`create_issue`, `get_issue`)
  - Agent conversation turns
  - Model used (should be gpt-4.1)

### Traces (via Weave)
- **Full Agent Execution Traces**:
  - Complete conversation flow
  - Tool call sequences
  - Input/output for each step
  - Model responses and reasoning

### Alerts
- **Not Required for Initial Implementation**: This is a development script, not production
- **CI/CD**: GitHub Actions workflow will alert on test failures via PR checks
- **Future Consideration**: Add alerts for production deployment (error rates, latency, costs)

