# Building an Agentic Chatbot with Weave

## Goal

Using our own products regularly helps us better empathize with and understand our users' needs. Testing alone doesn't reveal real-world issues. To truly evaluate our product, we need to apply it to actual AI application development scenarios. Since creating projects from scratch takes too much time, this document provides a streamlined approach. 

**In under 30 minutes, you'll experience how Weave works in a typical use case.**

## Project

Build a real-world agentic chatbot to interact with customers. We will build a support bot that has the capabilities to:

- Answer questions about our product (from our docs)
- Create and give updates on support tickets

### Your Task

**Get this bot ready to put in production.**

Going from 0 to demo is fairly easy, but can you build an agent ready to face real questions and represent your company? This project will help you discover:

- Where Weave shines in the development process
- What features are intuitive vs. confusing
- What's missing or could be improved
- How our tools perform under real development conditions

## Prerequisites

Currently there is a need to write and run code, so to get started you will need:

- **Python environment** (3.13+ recommended; if you don't have one, we'll walk you through it)
- **GitHub** to clone the repo
- **Terminal access** to run commands
- **Weights & Biases account** ([sign up free](https://wandb.ai/authorize))
- **LLM API key** (e.g., [OpenAI](https://platform.openai.com/api-keys))

For each step we have attempted to include both **code-first** and **UI-first** instructions so you can feel what it is like for both technical and non-technical users.

---

# Let's Go! 🚀

## Step 1: Project Setup

### Code Approach

1. **Clone the repository**

```bash
git clone https://github.com/your-org/agentic-support-bot-demo.git
cd agentic-support-bot-demo
```

2. **Install dependencies**

We use [uv](https://github.com/astral-sh/uv) for fast, reliable Python package management.

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

3. **Configure environment variables**

```bash
# Create your .env file
cp .env.example .env
```

Edit `.env` and add your API keys:
- `WANDB_API_KEY` - **Required** for Weave observability
- `OPENAI_API_KEY` - Required if using OpenAI models

**Note**: You can use other LLM providers supported by [LiteLLM](https://docs.litellm.ai/docs/providers) by modifying the `model_name` in `tyler-chat-config.yaml`.

### UI Approach

❌ **Can't be done currently.** 

**Question for discussion**: Could we adopt an Agent Class that can be configured entirely through the Weave UI? This would make onboarding non-technical users much smoother.

---

## Step 2: Get a Basic Agent Running

### Code Approach

Start the interactive chat CLI:

```bash
uv run tyler chat
```

This launches an interactive terminal session where you can:
- 💬 Chat naturally with the support bot
- 🔧 Create and retrieve support issues using natural language
- 📊 See real-time streaming responses
- 🔄 Maintain conversation context across multiple messages
- 📈 Automatically log all interactions to Weave

**Try these example prompts:**
```
You: I need to create a new issue for API timeouts

You: Can you get me the details for issue #123?
```

**Chat Commands:**
- `/help` - Show available commands
- `/new` - Start a new conversation thread
- `/quit` or `/exit` - Exit the chat
- `/clear` - Clear the screen

**View your traces**

1. Navigate to your Weave project at [wandb.ai](https://wandb.ai)
2. After running the agent locally (code approach above), you'll see traces appear automatically
3. Click into a trace to explore the agent's behavior

---

## Step 3: Vibe Check - Experiment in the Playground

### Code Approach

Continue chatting with the agent in the CLI and try various prompts:

- Ask it questions about your product
- Request it to create support tickets
- Test edge cases and unusual requests
- See how it handles multi-turn conversations

**What to look for:**
- Is the agent helpful and on-brand?
- Does it call tools at the right time?
- Are responses clear and accurate?

### UI Approach

Now you can test the agent visually in Weave Playground!

**1. Start the Playground Server**

```bash
uv run playground_server.py
```

The server will start on `http://0.0.0.0:8000`. You should see:
```
============================================================
Tyler Playground API Server
============================================================
Agent: Buzz (gpt-4o)
Server: http://0.0.0.0:8000
Health check: http://0.0.0.0:8000/health
============================================================
```

**2. Expose via ngrok (for Weave Playground access)**

In a new terminal:
```bash
ngrok http 8000
```

Copy the `https://` URL (e.g., `https://abc123.ngrok-free.app`)

**3. Configure Weave Playground**

1. Go to [Weave Playground](https://wandb.ai/playground)
2. Click **Select a model** dropdown → **+ Add AI provider**
3. Fill in provider information:
   - **Provider name**: `tyler-support-bot`
   - **Base URL**: `https://abc123.ngrok-free.app/v1/` (your ngrok URL + `/v1/`)
   - **API key**: `dummy` (not validated for local dev, but required field)
   - **Models**: Click "Add model" and enter `support-bot`
4. Click **Add provider**
5. Select `tyler-support-bot/support-bot` from the model dropdown

**4. Start Chatting!**

Try these prompts in the Playground:
- "Create a new support issue for API timeout problems with high priority"
- "Show me issue #123"
- "I need help with authentication errors"

**What to look for:**
- 📊 **Streaming responses**: Watch tokens appear in real-time
- 🔧 **Tool usage**: See when create_issue/get_issue are called
- 📈 **Weave traces**: Check your project dashboard for automatic trace logging
- 💬 **Conversation flow**: Test multi-turn conversations
- ⚡ **Response quality**: Is the agent helpful and accurate?

**Troubleshooting:**

- **Server won't start**: Make sure you're running from the project root where `tyler-chat-config.yaml` exists
- **ngrok connection fails**: Check that ngrok is running and the URL is correct
- **Playground shows errors**: Verify the Base URL ends with `/v1/` (trailing slash matters)
- **No traces in Weave**: Check that `WANDB_API_KEY` is set in your `.env` file

**Alternative: Test with curl**

If you don't want to set up ngrok, test locally:
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"Create a support ticket for API timeouts"}],"stream":true}'
```

---

<!-- ## Step 4: Create a Dataset

Build a test dataset to systematically evaluate your agent.

### Code Approach

```python
import weave

# Initialize Weave
weave.init('your-project-name')

# Create a dataset of test cases
dataset = weave.Dataset(
    name='support-bot-eval',
    rows=[
        {'user_message': 'I need help with API rate limits', 'expected_action': 'provide_info'},
        {'user_message': 'Create a ticket for billing issue', 'expected_action': 'create_ticket'},
        {'user_message': 'What is the status of ticket #456?', 'expected_action': 'get_ticket'},
        # Add more test cases...
    ]
)
```

### UI Approach

1. In Weave, navigate to **Datasets**
2. Click **New Dataset**
3. Add rows manually or import from CSV
4. Include columns for:
   - Input (user message)
   - Expected behavior
   - Any other metadata

**Question**: How intuitive is the dataset creation flow?

---

## Step 5: Create Evaluation Scorers

Define how you'll measure agent performance.

### Code Approach

```python
import weave

@weave.op()
def accuracy_scorer(output: dict, expected: dict) -> dict:
    """Check if the agent took the expected action"""
    return {
        'correct': output.get('action') == expected.get('expected_action')
    }

@weave.op()
def tool_usage_scorer(output: dict) -> dict:
    """Check if tools were used appropriately"""
    return {
        'used_tools': len(output.get('tool_calls', [])) > 0,
        'tool_names': [t['name'] for t in output.get('tool_calls', [])]
    }
```

### UI Approach

**Question**: Can scorers be created or configured in the UI? If not, would this be valuable?

---

## Step 6: Establish Baseline Performance

Run evaluations to understand your starting point.

### Code Approach

```python
import weave
from tyler import create_agent

# Initialize Weave
weave.init('your-project-name')

# Create evaluation
evaluation = weave.Evaluation(
    dataset=dataset,
    scorers=[accuracy_scorer, tool_usage_scorer]
)

# Run with default model (gpt-4.1)
agent = create_agent()
results = evaluation.evaluate(agent)

print(f"Baseline accuracy: {results['accuracy']}")
```

### UI Approach

1. Navigate to **Evaluations** in Weave
2. Select your dataset
3. Select your agent
4. Run the evaluation
5. View results in the dashboard

**What to note:**
- How easy was it to run your first eval?
- Are the results clear and actionable?
- Can you easily compare different runs?

---

## Step 7: Test Different Models

Compare performance across different LLM providers and models.

### Code Approach

Edit `tyler-chat-config.yaml` to test different models:

```yaml
# Try different models
model_name: "gpt-4.1"        # Current default
# model_name: "gpt-3.5-turbo"  # Faster, cheaper
# model_name: "claude-3-opus"  # Anthropic
```

Run evaluations for each model and compare in Weave.

### UI Approach

1. In Weave, navigate to your evaluations
2. Compare runs side-by-side
3. Filter and sort by metrics
4. **Question**: Can you easily see which model performs best for your use case?

---

## Step 8: Iterate to Improve Accuracy

Now that you have a baseline, start improving:

### Code Approach

**Try these improvements:**

1. **Better prompts** - Edit the system prompt in `tyler-chat-config.yaml`
2. **Add examples** - Include few-shot examples in your prompt
3. **Refine tools** - Improve tool descriptions in `tools.py`
4. **Add guardrails** - Implement validation logic

After each change:
```bash
# Test interactively
uv run tyler chat

# Run full evaluation
python run_evaluation.py
```

### UI Approach

1. Make changes to your agent (code or config)
2. Run new evaluation in Weave
3. Compare to previous runs
4. **Key question**: Can you quickly identify what changed and whether it helped?

---

## Step 9 (Bonus): Iterate on the Details

Polish the agent's personality and behavior:

- **Tone of voice**: Make it friendly, professional, or quirky
- **Follow-up questions**: Have the agent proactively ask clarifying questions
- **Error handling**: Gracefully handle ambiguous requests
- **Multi-turn context**: Ensure the agent remembers previous messages

**Test these in the playground and measure with custom scorers:**

```python
@weave.op()
def tone_scorer(output: dict) -> dict:
    """Evaluate if the tone matches brand guidelines"""
    # Your custom logic here
    pass
```

---

## Project Structure

```
.
├── tyler-chat-config.yaml  # Agent configuration
├── main.py                 # Programmatic agent execution
├── tools.py                # Custom tool implementations
├── tests/                  # Test suite
├── directive/              # Spec and implementation docs
├── pyproject.toml         # Project dependencies
└── README.md              # This file
```

---

## Troubleshooting

### Configuration Issues

**Problem**: `Configuration file not found`  
**Solution**: Run commands from the project root directory where `tyler-chat-config.yaml` is located.

**Problem**: `Failed to load tool from path`  
**Solution**: Verify `tools.py` exists and exports a `TOOLS` list. Run `uv run pytest` to validate.

### Environment Variable Issues

**Problem**: `Missing required environment variable: WANDB_API_KEY`  
**Solution**: 
1. Create `.env` from `.env.example`
2. Add your Weights & Biases API key
3. The key loads automatically when you run the agent

**Problem**: `OpenAI API authentication error`  
**Solution**:
1. Verify `OPENAI_API_KEY` is set in `.env`
2. Or use a different LLM provider in `tyler-chat-config.yaml`
3. Ensure the API key has sufficient credits

### Tool Execution Issues

**Problem**: Tools aren't being called  
**Solution**: 
1. Make requests that clearly need tool usage
2. Check `tools.py` is referenced in `tyler-chat-config.yaml`
3. View Weave traces to see what the agent is doing

**Problem**: `Warning: Failed to initialize Weave`  
**Solution**: Non-blocking, but check your `WANDB_API_KEY` for full observability.

### Debug Mode

```bash
TYLER_DEBUG=1 uv run tyler chat --config tyler-chat-config.yaml
```

---

## Testing Your Changes

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test categories
uv run pytest tests/test_main.py::TestConfigurationFile -v
uv run pytest tests/test_main.py::TestCreateIssueTool -v
```

---

## Share Your Feedback! 💬

As you go through this project, please note:

✅ **What worked well** - Where did Weave make your life easier?  
⚠️ **What was confusing** - Where did you get stuck?  
❌ **What was frustrating** - What slowed you down?  
💡 **What's missing** - What features would have helped?

Your feedback helps us build better products for AI developers.

---

## Resources

- [Slide Framework Documentation](https://slide.mintlify.app)
- [Tyler CLI Documentation](https://slide.mintlify.app/apps/tyler-cli)
- [Weave Documentation](https://wandb.github.io/weave/)
- [Creating Custom Tools Guide](https://slide.mintlify.app/guides/adding-tools)
- [Get W&B API Key](https://wandb.ai/authorize)

---

## License

See [LICENSE](./LICENSE) file for details. -->
