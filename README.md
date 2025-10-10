# Agentic Support Bot Demo

A demonstration of an agentic support bot powered by [Tyler](https://slide.mintlify.app), the agent framework from Slide, with integrated observability via [Weights & Biases Weave](https://wandb.ai/site/weave).

## Features

- 🤖 **Tyler Agent**: Powered by OpenAI's gpt-4.1 model
- 🔧 **Custom Tools**: Issue management tools (`create_issue`, `get_issue`)
- 📊 **Observability**: Full tracing and monitoring with W&B Weave
- 🎯 **Type-Safe**: Built with modern Python and type hints

## Prerequisites

- Python 3.12 or higher
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

Run the agent:

```bash
uv run main.py
```

The agent will:
1. Initialize with Weave observability
2. Register custom issue management tools
3. Execute a demo interaction showing tool usage (with streaming!)
4. Log all traces to your Weave project: `agentic-support-bot-demo`

## Project Structure

```
.
├── main.py                 # Main agent script and execution
├── tools.py                # Custom tool implementations
├── test_main.py            # Test suite
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

## License

See [LICENSE](./LICENSE) file for details.

## Resources

- [Tyler Documentation](https://slide.mintlify.app)
- [Weave Documentation](https://wandb.github.io/weave/)

