# Impact Analysis — Tyler Agent Foundation

## Modules/packages likely touched
- `main.py` — Will be completely refactored from hello world to Tyler agent initialization and execution
- `.env` — New file for API key management (not committed to git)
- `pyproject.toml` — New dependencies:
  - `slide-tyler` (Tyler agent core - includes LiteLLM for model access)
  - `slide-lye` (tool utilities for custom tool implementations)
  - `weave` (Weights & Biases Weave for observability)
  - `python-dotenv` (for loading environment variables from .env file)
  - Tyler includes LiteLLM which supports 100+ LLM providers including OpenAI

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
  - For OpenAI's gpt-4.1: Requires `OPENAI_API_KEY` environment variable
  - Rate limits apply based on provider and organization tier

- **Weights & Biases Weave API**: New dependency for observability
  - Requires `WANDB_API_KEY` environment variable
  - Project will be created/accessed: "agentic-support-bot-demo"

## Risks

### Security
- **API Key Exposure**: Two new secrets must be managed (`OPENAI_API_KEY`, `WANDB_API_KEY`)
  - Using `.env` file for local development (must be in `.gitignore`)
  - Mitigation: Fail fast with clear error if keys are missing; document in README
  - Create `.env.example` template for developers (without actual keys)
- **Prompt Injection**: Agent will execute based on LLM output with tool access
  - Mitigation: Tools are stubbed with no real system access (for now)
  - Future: Need input validation when tools are implemented

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
- **Future Consideration**: Add alerts for production deployment (error rates, latency, costs)

