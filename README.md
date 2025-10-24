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
  - Your W&B API key will be used for both Weave observability AND as the LLM API (we use W&B Inference with DeepSeek)

For each step we have attempted to include both **code-first** and **UI-first** instructions so you can feel what it is like for both technical and non-technical users.

---

# Let's Go! 🚀

## Step 1: Project Setup

### What You're Really Accomplishing

To save you time on boilerplate setup, we've created this repository with dependencies, configuration files, and example code already in place. This lets you focus on the agent-specific decisions (coming in Step 2) rather than wrestling with environment setup.

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

Edit `.env` and add your API key and project:
- `WANDB_API_KEY` - **Required** for both Weave observability and LLM API (we use W&B Inference with DeepSeek)
- `WANDB_PROJECT` - (Optional) Defaults to `agentic-support-bot-demo` - this is the Weave project where your traces will appear

**Note**: This demo uses W&B Inference with the DeepSeek model by default. You can use other LLM providers supported by [LiteLLM](https://docs.litellm.ai/docs/providers) by modifying the `model_name`, `base_url`, and `api_key` in `tyler-chat-config.yaml`.

---

## Step 2: Get a Basic Agent Running

We'll build your agent incrementally, starting simple and adding complexity. You'll use **Weave at each stage** to understand what's happening.

**Note:** This demo is specifically about **using Weave**, not building an agent from scratch. We're using the [Slide framework](https://slide.mintlify.app) to get an agent up and running quickly so you can focus on experiencing Weave's observability and evaluation workflow.

### Part A: Create Your First Agent

**What You're Accomplishing:** Get a minimal agent running and see your first Weave trace.

**Instructions:**

Your `tyler-chat-config.yaml` is already set up with a minimal configuration:

```yaml
name: "agent"
model_name: "openai/deepseek-ai/DeepSeek-R1-0528"
purpose: "You are a helpful AI assistant."

# W&B Inference endpoint configuration
base_url: "https://api.inference.wandb.ai/v1"
api_key: "${WANDB_API_KEY}"

temperature: 0.7
reasoning: "low"
```

**Notice:** The agent is generic - not specific to a support bot. You'll make it specific in Step 3!

**Test it:**

Now let's test it using Slide's CLI:

```bash
uv run tyler chat
```

Try these prompts:

```
How do I initialize Weave in my Python code?
```

```
I'm getting API timeout errors when logging predictions. Can you help?
```

```
What's the status of ticket #123?
```

```
Can you explain how to track model performance in wandb?
```

```
I need to create a support ticket for authentication issues
```

The agent should respond conversationally to all prompts. Now **check Weave**:

1. Navigate to your Weave project at [agentic-support-bot-demo](https://wandb.ai) (look for `agentic-support-bot-demo` in your projects)
2. Click **Traces** - you should see your conversation!
3. Click into the trace to see the full interaction captured

**What to notice:**
- ✅ Agent works and can converse
- ✅ Weave automatically captured everything
- ❌ Agent can't DO anything (no tools yet)

**Chat Commands:**
- `/quit` or `/exit` - Exit the chat
- `/help` - Show available commands

---

### Part B: Add Tools and MCP Server

**What You're Accomplishing:** Give your agent capabilities (local tools + documentation search) and test in Weave Playground.

> **⏭️ Want to skip ahead?** 
> ```bash
> cp examples/step-2b-with-tools/* .
> ```

**Step 1: Add Tools to Your Config**

Update your `tyler-chat-config.yaml` to include tools and MCP:

```yaml
name: "agent"
model_name: "openai/deepseek-ai/DeepSeek-R1-0528"
purpose: "You are a helpful AI assistant."

# W&B Inference endpoint configuration
base_url: "https://api.inference.wandb.ai/v1"
api_key: "${WANDB_API_KEY}"

temperature: 0.7
max_tool_iterations: 10
reasoning: "low"

# Tool Configuration
tools:
  - "./tools.py"

# MCP Server Configuration for W&B documentation search
mcp:
  servers:
    - name: "wandb"
      transport: "streamablehttp"
      url: "https://docs.wandb.ai/mcp"
```

**Step 2: Check Your Tools**

Your `tools.py` should have two functions and a `TOOLS` export:
- `create_issue(*, title, description, priority)` - Creates a support ticket  
- `get_issue(*, issue_id)` - Retrieves a ticket
- `TOOLS` - A list of tool definitions in JSON format

**Notice:** The tool definitions in `TOOLS` have NO descriptions or parameter details - just the function names! This is intentional - you'll add descriptions and parameters in Step 3 to teach the agent when and how to use each tool!

**Step 3: Test in Weave Playground**

Start the playground server:

```bash
uv run playground_server.py
```

**Tip**: You can specify a different config file with the `--config` flag:
```bash
uv run playground_server.py --config examples/step-3-complete/tyler-chat-config.yaml
```

Run `uv run playground_server.py --help` to see all available options.

In a **new terminal**, expose via ngrok:

```bash
ngrok http 8000
```

Copy the `https://` URL (e.g., `https://abc123.ngrok-free.app`)

**Set up a dummy team secret:**

Before connecting to the Weave Playground, you need to create a team secret in W&B:

**Note:** Only W&B Admins can create, edit, or delete secrets.

1. Navigate to your team's **Settings** page
2. In the **Team Secrets** section, click **New secret**
3. Enter the secret name: `BUZZ_API_KEY`
4. In the **Secret** field, enter: `dummy`
5. Click **Add secret**

This demonstrates how API authentication works with W&B secrets. The playground server validates this API key when you connect (it expects "dummy" for this demo). For more details on W&B secrets, see the [Secrets documentation](https://docs.wandb.ai/platform/secrets#secrets).

**Connect Weave Playground:**

1. Go to [Weave Playground](https://wandb.ai/playground)
2. Click **Select a model** → **+ Add AI provider** -> **Custom provider**
3. Fill in:
   - **Provider name**: `buzz_agent`
   - **Base URL**: `https://abc123.ngrok-free.app/v1` (your ngrok URL + `/v1`)
   - **API key**: `BUZZ_API_KEY`
   - **Models**: Click "Add model" and enter `buzz`
4. Click **Add provider**
5. Select `buzz_agent/buzz` from the model dropdown

**Try these prompts to test your agent:**

```
How do I initialize Weave in my Python code?
```

```
I'm getting API timeout errors when logging predictions. Can you help?
```

```
What's the status of ticket #123?
```

```
Can you explain how to track model performance in wandb?
```

```
I need to create a support ticket for authentication issues
```

**Check your traces in Weave:**

1. Navigate to [wandb.ai/agentic-support-bot-demo](https://wandb.ai) (`agentic-support-bot-demo` project)
2. Click **Traces** to see your Playground interactions

**What to notice in Weave dashboard:**
- Some traces show tool calls, others don't
- Agent doesn't consistently use tools
- Agent doesn't really "vibe" as a support bot
- Why? **The agent doesn't know its purpose or when to use tools!**

This is what we'll fix in Step 3.

---

## Step 3: Iterate to Make it Vibe as a Support Agent

**What You're Learning:** The core Weave workflow - **observe → diagnose → fix → verify**. This is how you improve agents!

> **⏭️ Want to skip to the finished support bot?** 
> ```bash
> cp examples/step-3-complete/* .
> ```
> 
> ⚠️ **But you'll miss the best part!** Iteration is where Weave shines.

### Part A: Identify the Problem

**Test your agent** with these same prompts in Weave Playground:

```
How do I initialize Weave in my Python code?
```

```
I'm getting API timeout errors when logging predictions. Can you help?
```

```
What's the status of ticket #123?
```

```
Can you explain how to track model performance in wandb?
```

```
I need to create a support ticket for authentication issues
```

**What you'll likely see:**
- Agent responds but doesn't search docs effectively
- Agent might not create tickets properly
- Agent doesn't properly retrieve ticket status
- Agent doesn't feel like a "support bot" - just a generic assistant

**Now use Weave to diagnose WHY:**

1. Navigate to [wandb.ai/agentic-support-bot-demo](https://wandb.ai) (`agentic-support-bot-demo` project)
2. Click **Traces** and find your recent interactions
3. Click into a trace and examine:
   - **Messages**: What did the agent say?
   - **Tool Calls**: Were tools called? Which ones? With what arguments?
   - **Agent Config**: Look at the config sent to the model

**What you should notice:**
- ❌ Agent has a **generic purpose** ("helpful AI assistant" - it doesn't know it's a support bot!)
- ❌ Tool definitions are **missing descriptions and parameters** - agent doesn't know WHEN to use them or HOW!

This is the problem. Weave helped you see it!

---

### Part B: Improve Purpose & Tool Descriptions

**Fix #1: Give your agent a clear purpose**

Update `tyler-chat-config.yaml`:

```yaml
name: "Buzz"
model_name: "openai/deepseek-ai/DeepSeek-R1-0528"
purpose: |
  You are a support bot for Weave, W&B's LLM observability platform.
  
  Your role is to:
  1. Help users with questions about Weave features and functionality
  2. Search the Weave documentation when users ask how-to questions
  3. Create and manage support tickets for issues users report
  
  Always be friendly, clear, and helpful in your responses.

notes: |
  - Use the search_docs tool for questions about Weave features and usage
  - Use create_issue for when users report problems or need help
  - Use get_issue to check on existing support tickets
  - Ask clarifying questions if the user's request is unclear
  - Be proactive in suggesting next steps

# W&B Inference endpoint configuration
base_url: "https://api.inference.wandb.ai/v1"
api_key: "${WANDB_API_KEY}"

temperature: 0.7
max_tool_iterations: 10
reasoning: "low"

# Tool Configuration
tools:
  - "./tools.py"

# MCP Server Configuration for W&B documentation search
mcp:
  servers:
    - name: "wandb"
      transport: "streamablehttp"
      url: "https://docs.wandb.ai/mcp"
```

**Fix #2: Improve tool descriptions**

Update `tools.py` with better descriptions in the tool definitions. Here's an example for `create_issue`:

```python
TOOLS = [
    {
        "definition": {
            "type": "function",
            "function": {
                "name": "support-create_issue",
                "description": "Create a support ticket for a user's problem or request. Use when user reports a bug, error, or problem with Weave, requests help or assistance, or asks to create a support ticket.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Brief, clear summary of the issue (e.g., 'API timeout errors in production')"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description including error messages, steps to reproduce, or context"
                        },
                        "priority": {
                            "type": "string",
                            "description": "Urgency: 'high' for critical production issues, 'medium' for standard issues, 'low' for minor questions",
                            "enum": ["low", "medium", "high"],
                            "default": "medium"
                        }
                    },
                    "required": ["title", "description"]
                }
            }
        },
        "implementation": create_issue
    },
    # ... do the same for get_issue
]
```

**Key improvements to make:**
1. Add a clear **description** explaining when to use the tool
2. Add **parameters** section with all function arguments
3. Add detailed **parameter descriptions** with examples
4. Specify **required** parameters

The agent needs both the description (when to use) AND the parameters (how to use) to call tools effectively.

See `examples/step-3-complete/tools.py` for the complete implementation.

**Restart your agent:**

```bash
# Stop the current playground server (Ctrl+C)
uv run playground_server.py
```

---

### Part C: Verify Improvements with Weave

**Test the same prompts again** in Weave Playground:

```
How do I initialize Weave in my Python code?
```

```
I'm getting API timeout errors when logging predictions. Can you help?
```

```
What's the status of ticket #123?
```

```
Can you explain how to track model performance in wandb?
```

```
I need to create a support ticket for authentication issues
```

**Now check Weave traces:**

1. Navigate to [wandb.ai/agentic-support-bot-demo](https://wandb.ai) (`agentic-support-bot-demo` project)
2. Find your new traces in the **Traces** tab
3. Compare to your old traces from Part A (side-by-side if possible)
4. **Notice the difference:**
   - ✅ Agent now searches docs appropriately
   - ✅ Agent creates tickets properly
   - ✅ Agent retrieves ticket status
   - ✅ Agent "vibes" as a support bot!

**This is the Weave workflow:**
1. 🔍 **Observe** behavior in traces
2. 🩺 **Diagnose** what's wrong
3. ✏️ **Fix** the issue (purpose + descriptions)
4. ✅ **Verify** improvement in new traces

**You just learned how to iterate on agents with observability!**

---

### Not Perfect? Iterate Again!

If your agent still doesn't work perfectly, **use Weave traces to understand why** and keep iterating:

- Check which tool calls are wrong
- Read the agent's reasoning
- Improve tool descriptions further
- Refine the purpose statement

This is real agent development!

---

---

Coming soon:

## Step 4: Create a Dataset

<!-- ### What You're Really Accomplishing

Transitioning from ad-hoc testing to systematic evaluation by building a curated set of test cases that represent your agent's expected usage.

### Questions a Real User Would Face

- **What scenarios should I cover?** Which are most important? Most common? Most risky?
- **How do I structure test data?** What format? What fields are needed?
- **How many test cases do I need?** 10? 100? 1000?
- **Should I include edge cases or focus on common paths?** Balance between coverage and effort?
- **Where do test cases come from?** Manual creation? Real user data? Synthetic generation?
- **How do I version and maintain this dataset?** Git? Database? Manual files?
- **What's the "expected output"?** Exact matches? Semantic similarity? Action taken?

Creating good test datasets is harder than it looks - it requires domain knowledge, creativity, and careful thought about what "correct" means.

### What This Demo Decided For You

✅ **Dataset format**: Weave Dataset structure with rows and columns  
✅ **Test coverage**: Example test cases covering main agent capabilities  
✅ **Expected outputs**: Simple action-based expectations (create_ticket, provide_info, etc.)  
✅ **Storage**: Versioned in Weave (or code) for reproducibility  
✅ **Size**: Small but representative set (~10-20 cases) to start

### Your Focus

As you create or review test cases, think about whether they truly represent real-world usage. Are you testing the right things? Would failures on these cases matter in production?

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

### What You're Really Accomplishing

Defining objective, automated metrics to measure agent quality - translating human judgment into code.

### Questions a Real User Would Face

- **What should I measure?** Accuracy? Helpfulness? Tone? Safety? All of the above?
- **How do I measure subjective qualities?** Like "helpfulness" or "brand voice"?
- **Should I use LLM-as-judge?** Which model? What prompt? How reliable is it?
- **Exact match or semantic similarity?** When is each appropriate?
- **How do I handle multiple valid responses?** Not all questions have one right answer
- **What about edge cases?** Refusals, clarifications, multi-turn conversations?
- **How do I validate my scorers are correct?** Who judges the judges?

Building good evaluation metrics is one of the hardest parts of AI engineering - it requires domain expertise and careful thinking about what success means.

### What This Demo Decided For You

✅ **Scorer framework**: Weave's `@weave.op()` decorator for automatic tracking  
✅ **Initial metrics**: Simple action accuracy and tool usage scoring  
✅ **Evaluation patterns**: Example code showing scorer structure  
✅ **Output format**: Dictionary-based results for flexibility

### Your Focus

Think critically about the scorers: Do they measure what matters? Would high scores actually mean a good agent? What important qualities are missing? This is where product sense meets engineering.

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

### What You're Really Accomplishing

Creating your first quantitative measurement of agent performance - establishing a benchmark to compare all future improvements against.

### Questions a Real User Would Face

- **How do I run evaluations at scale?** Sequentially? In parallel? Rate limits?
- **What's a "good" score?** Is 80% accuracy good enough? 90%? Depends on the task?
- **How long will this take?** Runtime and cost for N test cases?
- **How do I handle flakiness?** LLM outputs are non-deterministic
- **Should I use sampling/temperature 0?** Trade-offs between consistency and creativity?
- **Where do I store results?** For comparison over time?
- **How do I surface results to stakeholders?** Dashboards? Reports? Alerts?

Running your first eval is exciting but raises questions about reliability, cost, and what the numbers actually mean.

### What This Demo Decided For You

✅ **Evaluation harness**: Weave's `Evaluation` class handles execution and tracking  
✅ **Parallelization**: Automatically handles concurrent execution  
✅ **Result storage**: Results automatically logged to Weave for comparison  
✅ **Cost tracking**: Token usage tracked per evaluation run  
✅ **Model config**: Sensible defaults (temperature, etc.) pre-set

### Your Focus

Look at the results critically. What does a 75% accuracy score actually tell you? Which failures matter most? This baseline is your north star for improvement - make sure you trust it.

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

### What You're Really Accomplishing

Systematically comparing LLM providers and models to find the best balance of quality, cost, and latency for your specific use case.

### Questions a Real User Would Face

- **Which models should I test?** GPT-4? Claude? Gemini? Open source?
- **How do I switch between providers?** Different APIs, auth patterns, response formats?
- **What about cost differences?** Some models are 10-100x more expensive than others
- **What about latency?** Faster models might sacrifice quality
- **How do I handle provider-specific features?** Function calling implementation varies
- **Should I test different model sizes?** GPT-4 vs GPT-3.5? Claude Opus vs Sonnet?
- **How do I make comparisons fair?** Same prompts? Same temperature? Same test set?
- **What if a model fails mid-eval?** Rate limits, timeouts, API errors?

Model selection is crucial - it impacts your quality, cost, and reliability. But testing is time-consuming and expensive.

### What This Demo Decided For You

✅ **Provider abstraction**: LiteLLM handles different APIs uniformly  
✅ **Easy switching**: Change one line in config file to test new models  
✅ **Comparison framework**: Weave automatically tracks results for side-by-side comparison  
✅ **Suggested models**: Pre-configured with sensible options to try  
✅ **Cost visibility**: Token usage and estimated costs in traces

### Your Focus

As you compare models, think about the trade-offs. Is a 5% accuracy improvement worth 10x the cost? How much does latency matter for your users? This is where engineering meets business decisions.

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

### What You're Really Accomplishing

The iterative improvement cycle - the core of AI engineering where you experiment, measure, and refine to boost performance.

### Questions a Real User Would Face

- **Where do I start?** Prompts? Tools? Examples? RAG? Fine-tuning?
- **How do I know what to fix?** Which errors are most important?
- **Should I use few-shot examples?** How many? Which ones? Where to put them?
- **How do I improve tool calling?** Better descriptions? Better names? More/fewer tools?
- **What about prompt engineering?** What techniques actually work?
- **Should I add guardrails?** How to validate outputs without breaking creativity?
- **How much testing between changes?** Full eval every time? Spot checks?
- **How do I avoid overfitting to my test set?** Am I gaming my own metrics?
- **When is "good enough" good enough?** Diminishing returns vs. perfectionism?

This is the messy, creative phase where art meets science. Every change needs testing, and improvements aren't always obvious.

### What This Demo Decided For You

✅ **Iteration tools**: Easy config changes with immediate testing  
✅ **Fast feedback loop**: CLI for quick spot checks, evals for validation  
✅ **Common techniques**: Examples of prompt improvements, tool refinements  
✅ **Measurement framework**: Automatic comparison of runs in Weave  
✅ **Version control**: Git + Weave for tracking what changed and impact

### Your Focus

This is where you live for weeks in real projects. Notice what makes iteration fast vs. slow. Can you quickly test a hypothesis? Is it clear what improved and what regressed? This workflow quality determines your development velocity.

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

### What You're Really Accomplishing

Moving from "works" to "delightful" - the final polish that makes users love (or hate) your agent.

### Questions a Real User Would Face

- **What's the right personality?** Formal? Casual? Funny? It depends on brand and context
- **How much context should the agent maintain?** Full conversation? Last N messages? Summarization?
- **When should the agent ask clarifying questions?** Too many is annoying, too few causes errors
- **How do I handle ambiguity gracefully?** Not every user request is clear
- **What about error messages?** Technical details vs. user-friendly language?
- **Should the agent apologize?** Set boundaries? How human-like should it feel?
- **How do I measure "quality"?** NPS? User feedback? Custom scorers?

These details are what separate good agents from great ones, but they're highly subjective and hard to measure objectively.

### What This Demo Decided For You

✅ **Base personality**: Friendly support bot tone pre-configured  
✅ **Context handling**: Multi-turn conversation support built-in  
✅ **Error patterns**: Basic error handling implemented  
✅ **Evaluation framework**: Infrastructure to test subjective qualities with custom scorers

### Your Focus

This is where product intuition matters most. These details can't always be A/B tested or measured - you need to develop taste for what makes a good interaction. Pay attention to how the agent "feels" to use.

### Details to Polish

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
├── examples/               # Complete reference files for skip-ahead
│   ├── step-2b-with-tools/
│   └── step-3-complete/
├── tyler-chat-config.yaml  # Agent configuration (starter)
├── tools.py                # Custom tool implementations (starter)
├── playground_server.py    # API server for Weave Playground
├── main.py                 # Programmatic agent execution
├── tests/                  # Test suite
├── directive/              # Spec and implementation docs
├── pyproject.toml         # Project dependencies
└── README.md              # This file
```

**Weave Project**: All traces go to `agentic-support-bot-demo` project at [wandb.ai](https://wandb.ai)

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
3. View Weave traces at [wandb.ai/agentic-support-bot-demo](https://wandb.ai) to see what the agent is doing
4. Check tool docstrings - agent needs clear descriptions to know when to use tools!

**Problem**: `Warning: Failed to initialize Weave`  
**Solution**: Non-blocking, but check your `WANDB_API_KEY` for full observability. Your traces should appear at [wandb.ai/agentic-support-bot-demo](https://wandb.ai).

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
