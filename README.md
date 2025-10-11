# Agentic Support Bot Demo

A demonstration of an agentic support bot powered by [Tyler](https://slide.mintlify.app), the agent framework from Slide, with integrated observability via [Weights & Biases Weave](https://wandb.ai/site/weave).

## Features

- 🤖 **Tyler Agent**: Powered by OpenAI's gpt-4.1 model
- 🔧 **Custom Tools**: Issue management tools (`create_issue`, `get_issue`)
- 📊 **Observability**: Full tracing and monitoring with W&B Weave
- 🎯 **Type-Safe**: Built with modern Python and type hints

## Prerequisites

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv)
- Weights & Biases API key ([get one here](https://wandb.ai/authorize)) - **Required**
- LLM Provider API key (e.g., [OpenAI](https://platform.openai.com/api-keys)) - **Optional**, configure based on your chosen provider

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd agentic-support-bot-demo
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
- `WANDB_API_KEY` - Required for Weave observability
- `OPENAI_API_KEY` - Optional, only if using OpenAI models

**Note**: The agent uses OpenAI's gpt-4.1 model by default. Configure your LLM provider API key accordingly, or modify the `model_name` in `create_agent()` to use a different provider supported by [LiteLLM](https://docs.litellm.ai/docs/providers).

## Usage

### Interactive CLI (Recommended)

Start an interactive chat session with the support bot using the Tyler CLI:

```bash
uv run tyler chat --config tyler-chat-config.yaml
```

This launches an interactive terminal session where you can:
- 💬 Chat naturally with the support bot
- 🔧 Create and retrieve support issues using natural language
- 📊 See real-time streaming responses
- 🔄 Maintain conversation context across multiple messages
- 📈 Automatically log all interactions to Weave

**Example conversation:**
```
You: I need to create a new issue for API timeouts

support-bot: I'll help you create a support issue for API timeouts...
[🔧 Using tool: create_issue]
I've created a new issue (ID: abc-123) ...

You: Can you get me the details for issue #123?

support-bot: Let me retrieve that issue for you...
[🔧 Using tool: get_issue]
Here are the details for issue #123...
```

**Chat Commands:**
- `/help` - Show available commands
- `/new` - Start a new conversation thread
- `/quit` or `/exit` - Exit the chat
- `/clear` - Clear the screen

### Programmatic Usage (Alternative)

For testing or automation, you can also run the agent programmatically:

```bash
uv run main.py
```

This will execute a pre-defined demo interaction showing tool usage with streaming.

## Project Structure

```
.
├── tyler-chat-config.yaml  # Tyler CLI configuration for interactive chat
├── main.py                 # Alternative: Programmatic agent execution
├── tools.py                # Custom tool implementations (create_issue, get_issue)
├── tests/                  # Test suite
│   ├── test_main.py       # Tests for tools and configuration
│   └── conftest.py        # Test fixtures
├── directive/              # Directive workflow docs
│   ├── specs/             # Feature specifications
│   └── reference/         # Templates and guidelines
├── pyproject.toml         # Project dependencies
└── README.md              # This file
```

## Observability

All agent interactions are automatically traced in Weights & Biases Weave:

- 📈 View token usage and costs
- 🔍 Inspect tool calls and responses
- ⏱️ Monitor latency and performance
- 🐛 Debug agent behavior with full traces

Access your traces at: https://wandb.ai/

## Troubleshooting

### Configuration Issues

**Problem**: `Configuration file not found`  
**Solution**: Make sure you're running the command from the project root directory where `tyler-chat-config.yaml` is located.

**Problem**: `Failed to load tool from path`  
**Solution**: Verify that `tools.py` exists and exports a `TOOLS` list. Run tests with `uv run pytest` to validate.

### Environment Variable Issues

**Problem**: `Missing required environment variable: WANDB_API_KEY`  
**Solution**: 
1. Create a `.env` file from `.env.example`
2. Add your Weights & Biases API key
3. The key will be loaded automatically when you run tyler chat

**Problem**: `OpenAI API authentication error`  
**Solution**:
1. Verify your `OPENAI_API_KEY` is set in `.env`
2. Or modify `model_name` in `tyler-chat-config.yaml` to use a different LLM provider
3. Ensure the API key has sufficient credits/permissions

### Tool Execution Issues

**Problem**: Tools aren't being called by the agent  
**Solution**: 
1. Make sure your request clearly describes needing to create or retrieve an issue
2. Check that `tools.py` is properly referenced in `tyler-chat-config.yaml`
3. Verify Weave traces at wandb.ai to see what the agent is doing

**Problem**: `Warning: Failed to initialize Weave`  
**Solution**: This is non-blocking. The agent will continue to work, but observability will be limited. Check your `WANDB_API_KEY`.

### Debug Mode

Enable debug output for troubleshooting:

```bash
TYLER_DEBUG=1 uv run tyler chat --config tyler-chat-config.yaml
```

## Testing

Run the test suite to verify everything is working correctly:

```bash
# Run all tests
uv run pytest tests/ -v

# Run only configuration tests
uv run pytest tests/test_main.py::TestConfigurationFile -v

# Run only tool tests
uv run pytest tests/test_main.py::TestCreateIssueTool -v
uv run pytest tests/test_main.py::TestGetIssueTool -v
```

## License

See [LICENSE](./LICENSE) file for details.

## Resources

- [Slide Framework Documentation](https://slide.mintlify.app)
- [Tyler CLI Documentation](https://slide.mintlify.app/apps/tyler-cli)
- [Tyler Agent API Reference](https://slide.mintlify.app/api-reference/tyler-agent)
- [Weave Documentation](https://wandb.github.io/weave/)
- [Creating Custom Tools Guide](https://slide.mintlify.app/guides/adding-tools)

