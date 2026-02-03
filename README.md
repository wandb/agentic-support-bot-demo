# Building an Agentic Chatbot with Weave

## Goal

Using our own products regularly helps us better empathize with and understand our users' needs. This repo provides a streamlined guide to experience how Weave works in a typical AI development workflow.

**Go from zero to a production-deployed support bot with systematic evaluation, real-time monitoring, and continuous improvement.**

## Project

Build a support bot for Weights & Biases that can:
- Answer questions about our product (from our docs)
- Create and give updates on support tickets

### Your Task

**Get this bot ready for production.** Going from 0 to demo is easy, but can you build an agent ready to face real customer questions? Discover:

- Where Weave shines in the development process
- What features are intuitive vs. confusing
- What's missing or could be improved

## Prerequisites

- **Python 3.12+** environment
- **GitHub** to clone the repo
- **Terminal access** to run commands
- **Modal account** (free) for serverless deployment ([sign up here](https://modal.com))
  - Used to deploy your agent server (both development and production)
  - Free tier includes generous compute credits
- **Weights & Biases account** ([sign up free](https://wandb.ai/authorize))
  - Your W&B API key is used for both Weave observability AND the LLM API (we use W&B Inference with DeepSeek)

---

# Getting Started 🚀

## 1. Clone the repository

```bash
git clone https://github.com/wandb/agentic-support-bot-demo.git
cd agentic-support-bot-demo
```

## 2. Install dependencies

We use [uv](https://github.com/astral-sh/uv) for fast, reliable Python package management.

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies (includes Marimo)
uv sync
```

## 3. Launch the Interactive Guide

```bash
uv run marimo run marimo-guide.py
```

The guide will open in your browser and walk you through the entire tutorial.

---

## What You'll Learn

The interactive guide covers:

1. **Project Setup** - Configure environment variables and workspace
2. **Basic Agent** - Get a minimal agent running with Weave tracing
3. **Tools & MCP** - Add capabilities and connect to documentation search
4. **Iteration** - The core Weave workflow: observe → diagnose → fix → verify
5. **Evaluation** - Build systematic evaluation with datasets and scorers
6. **Deployment** - Deploy to Modal for production
7. **Monitoring & Guardrails** - Add safety controls and quality tracking

---

## Resources

- [Slide Framework Documentation](https://slide.mintlify.app)
- [Tyler CLI Documentation](https://slide.mintlify.app/apps/tyler-cli)
- [Weave Documentation](https://wandb.github.io/weave/)
- [Creating Custom Tools Guide](https://slide.mintlify.app/guides/adding-tools)
- [Get W&B API Key](https://wandb.ai/authorize)

---

## License

See [LICENSE](./LICENSE) file for details.
