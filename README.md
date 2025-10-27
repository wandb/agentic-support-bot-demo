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

**Set up API key authentication:**

The playground server requires an API key for authentication. You need to:

1. **Set the API key locally** (in your `.env` file):
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and set your API key (for the purpose of this demo, you can just use "dummy" as your secret)
   PLAYGROUND_API_KEY=your_secret_key_here
   ```

2. **Create a team secret in W&B** (for Weave Playground to authenticate):
   
   **Note:** Only W&B Admins can create, edit, or delete secrets.
   
   - Navigate to your team's **Settings** page
   - In the **Team Secrets** section, click **New secret**
   - Enter the secret name: `PLAYGROUND_API_KEY`
   - In the **Secret** field, enter the **same secret value** you used in your `.env` file
   - Click **Add secret**

For more details on W&B secrets, see the [Secrets documentation](https://docs.wandb.ai/platform/secrets#secrets).

**Start the playground server:**

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

**Connect Weave Playground:**

1. Go to [Weave Playground](https://wandb.ai/playground)
2. Click **Select a model** → **+ Add AI provider** -> **Custom provider**
3. Fill in:
   - **Provider name**: `buzz_agent`
   - **Base URL**: `https://abc123.ngrok-free.app/v1` (your ngrok URL + `/v1`, no trailing slash)
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

Now it's time to iterate! Instead of just giving you the answer, let's walk through what you should experiment with.

**🎯 Your Goal:** Make the agent understand its role as a Weights & Biases support bot and know when/how to use its tools.

---

#### **Iteration 1: Give Your Agent a Clear Purpose**

Open `tyler-chat-config.yaml` and look at the `purpose` field:

```yaml
purpose: "You are a helpful AI assistant."
```

**What's wrong with this?**
- It's generic - could be any chatbot
- Doesn't tell the agent it's a support bot
- Doesn't explain what the agent should help with
- No guidance on behavior or tone

**Your task:** Rewrite the `purpose` to make it clear this is a **support bot for Weights & Biases**. Think about:
- What is this bot's role?
- What types of requests should it handle?
- What should its personality/tone be?

**Hints:**
- Be specific about what product/company you're supporting (Weights & Biases)
- List the key things the agent should do
- Set expectations for how it should interact with users
- Consider adding a `notes` section with operational guidelines

**💡 Need help?** Look at `examples/step-3-complete/tyler-chat-config.yaml` to see a well-crafted purpose statement.

**Test your changes:**
```bash
# Restart the playground server
uv run playground_server.py
```

Try your test prompts again in Weave Playground. Does it feel more like a support bot? Check the traces to see if the purpose is helping.

---

#### **Iteration 2: Add Tool Descriptions**

Open `tools.py` and look at the `TOOLS` export (around line 54):

```python
TOOLS = [
    {
        "definition": {
            "type": "function",
            "function": {
                "name": "support-create_issue",
                # Missing: description, parameters!
            }
        },
        "implementation": create_issue
    },
    # ... same for get_issue
]
```

**What's wrong with this?**
- ❌ No `description` - agent doesn't know WHEN to use this tool
- ❌ No `parameters` - agent doesn't know HOW to use this tool
- ❌ No parameter descriptions - agent doesn't know what values to pass

**Your task:** Add complete tool definitions. For each tool, you need to add:

1. **`description`** - When should the agent use this tool? What scenarios?
2. **`parameters`** - What arguments does the tool accept?
3. **Parameter descriptions** - What should each parameter contain? Include examples!
4. **`required`** - Which parameters are mandatory?

**Example structure to fill in:**

```python
{
    "definition": {
        "type": "function",
        "function": {
            "name": "support-create_issue",
            "description": "YOUR DESCRIPTION HERE - explain when to use this tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "YOUR DESCRIPTION - what should title contain?"
                    },
                    "description": {
                        "type": "string",
                        "description": "YOUR DESCRIPTION - what should description contain?"
                    },
                    "priority": {
                        "type": "string",
                        "description": "YOUR DESCRIPTION - how should agent choose priority?",
                        "enum": ["low", "medium", "high"],
                        "default": "medium"
                    }
                },
                "required": ["title", "description"]
            }
        }
    },
    "implementation": create_issue
}
```

**Tips for writing good tool descriptions:**
- **Description field**: Explain the scenarios when this tool should be called. Give examples of user requests.
- **Parameter descriptions**: Be specific! Include examples of good values. The agent uses these to decide what to pass.
- **Think from the agent's perspective**: What information would YOU need to decide when and how to use this tool?

**Do this for both tools:**
- `support-create_issue` - When should tickets be created for W&B issues? What makes a good title vs description?
- `support-get_issue` - When should the agent retrieve ticket status? What does the user need to provide?

**💡 Stuck?** Look at `examples/step-3-complete/tools.py` (lines 108-159) to see fully documented tool definitions. But try writing your own first!

**Test your changes:**

1. Save `tools.py`
2. Restart the playground server (the tools are loaded at startup):
   ```bash
   # Stop with Ctrl+C, then restart
   uv run playground_server.py
   ```
3. Test the same prompts in Weave Playground
4. **Check Weave traces** - do you see better tool usage now?

---

#### **Iteration 3: Compare and Refine**

After making your changes:

1. **Test thoroughly** with the same prompts from Part A
2. **Check Weave traces** - compare before and after:
   - Are tools being called appropriately?
   - Are the parameters correct?
   - Does the agent feel like a support bot?
3. **Iterate more** - tool descriptions are hard to get right the first time!
   - If the agent doesn't call tools when it should, improve the `description`
   - If the agent passes wrong values, improve parameter descriptions
   - If the tone is off, refine the `purpose` statement

**This is real agent development** - observe, diagnose, fix, verify, repeat!

---

### Part C: Verify Your Improvements with Weave

After making your changes to `purpose` and tool descriptions, it's time to see if they worked!

**1. Test the same prompts again** in Weave Playground:

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

**2. Use Weave to compare before and after:**

1. Navigate to [wandb.ai/agentic-support-bot-demo](https://wandb.ai) (`agentic-support-bot-demo` project)
2. Click the **Traces** tab
3. Find your new traces (after your changes)
4. **Compare them side-by-side** with your old traces from Part A

**3. Ask yourself:**
- ✅ Does the agent search docs when appropriate?
- ✅ Does it create tickets when users report issues?
- ✅ Does it retrieve ticket status correctly?
- ✅ Does it "feel" like a support bot now?
- ✅ Are the tool parameters being filled correctly?

**4. Look at the differences in the traces:**
- How has the agent's behavior changed?
- Which tool descriptions are working well?
- Which ones might need more iteration?

**5. Keep iterating if needed:**
- If the agent still doesn't use tools correctly, refine your descriptions
- If the tone is off, adjust the `purpose` statement
- If parameters are wrong, improve parameter descriptions

**💡 Want to see a polished example?** Compare your work with `examples/step-3-complete/` - but remember, your version might be different, and that's okay! There's no single "right" way to write these descriptions.

---

**🎉 You just learned a core Weave workflow:**

1. 🔍 **Observe** - Run your agent and examine traces
2. 🩺 **Diagnose** - Identify what's wrong by looking at tool calls, responses, and config
3. ✏️ **Fix** - Improve purpose, tool descriptions, or other config
4. ✅ **Verify** - Test again and compare traces to see if it improved

---

## Step 4: Dataset & Evaluation - From Vibes to Production-Ready

**What You're Really Accomplishing:**

Moving from "it feels right" to "it's provably ready for production" by building systematic evaluation. You'll create a comprehensive test dataset and implement automated scoring to validate your agent's behavior across diverse scenarios - including edge cases and adversarial inputs you haven't tested yet.

> **⏭️ Want to skip ahead?** 
> ```bash
> cp examples/step-4-complete/* .
> ```
> 
> ⚠️ **But you'll miss the learning!** This step teaches evaluation thinking - a critical skill for production agents.

---

### The Challenge: What Makes a Bot "Production-Ready"?

After Step 3, you have a support bot that works well in demos. But can you confidently deploy it to real users? Consider these questions:

**Dataset Design Questions:**
- **What scenarios should you test?** Happy paths? Edge cases? Adversarial inputs?
- **How many test cases are enough?** 10? 50? 100? What coverage do you need?
- **What about failure modes?** Off-topic questions? Inappropriate requests? Prompt injection?
- **How do you define "correct"?** Exact matches? Semantic similarity? Correct actions taken?

**Evaluation Questions:**
- **How do you measure quality?** Tool usage? Answer accuracy? Tone and safety?
- **Should you use LLM-as-judge?** What are the trade-offs vs. simple rules?
- **What about costs?** Running 50+ test cases with LLM judges isn't free!
- **How do you track improvements?** Compare runs? Identify regressions?

**Think about this for a moment before seeing the solution.**

What test cases would YOU create? What would you measure?

---

**What You're Really Accomplishing:**

Moving from "it feels right" to "it's provably ready for production" by building systematic evaluation. You'll create a comprehensive test dataset with 64 diverse cases and implement automated scoring to validate your agent's behavior across realistic scenarios, edge cases, and adversarial inputs.

> **⏭️ Want to skip ahead?** 
> ```bash
> cp examples/step-4-complete/* .
> ```

---

### Part A: Review the Evaluation Dataset

The example dataset in `examples/step-4-complete/dataset.py` contains **64 carefully crafted test cases**:

```bash
# View the complete dataset
cat examples/step-4-complete/dataset.py
```

**Dataset Coverage:**
- **31 W&B/Weave questions**: Initialization, debugging, troubleshooting, features
- **16 Tool usage scenarios**: Support ticket creation and retrieval
- **18 Refusal scenarios**: Off-topic questions, inappropriate requests, adversarial attempts

**Dataset Structure:**

Each test case includes:
```python
{
    "input": "How do I initialize Weave in Python?",
    "expected_output": "Call weave.init() with your project name",
    "expected_tools": [],  # Tools that should be called
    "tags": ["weave", "initialization", "factual"]
}
```

**Key Insights:**
- **Coverage matters**: 64 diverse cases reveal more issues than 200 similar ones
- **Test refusals**: Critical to verify the bot says "no" appropriately  
- **Edge cases included**: Prompt injection, jailbreaks, nonsense requests test robustness

---

### Part B: Publish Dataset to Weave

Publishing provides versioning, reproducibility, and team collaboration:

```bash
uv run python examples/step-4-complete/publish_dataset.py
```

This script:
1. Validates dataset structure (≥50 cases, required fields)
2. Connects to Weave using your `WANDB_API_KEY`
3. Publishes as `support-bot-eval-dataset`
4. Creates version history (each publish = new version)

**Verify in Weave UI:**
1. Go to https://wandb.ai/
2. Open project: `agentic-support-bot-demo`
3. Click **Datasets** tab
4. Browse all 64 test cases

---

### Part C: Understanding the Scorers

The evaluation uses **three types of scorers** to measure different aspects:

**1. Rule-Based Scorer: Tool Correctness** (Fast, Free, Deterministic)

```python
@weave.op()
def tool_usage_scorer(input: dict, output: dict) -> dict:
    """Did the bot call the correct tools?"""
    expected_tools = set(input.get("expected_tools", []))
    actual_tools = set(output.get("tools_used", []))
    
    return {
        "correct_tools": expected_tools == actual_tools,
        "score": 1.0 if expected_tools == actual_tools else 0.0
    }
```

✅ **Use for**: Objective checks (tools called, format correct)  
❌ **Don't use for**: Subjective quality (helpfulness, tone)

**2. LLM-as-Judge: Accuracy Scorer** (Flexible, Often Free)

```python
@weave.op()
def accuracy_scorer(input: dict, output: dict) -> dict:
    """Is the answer accurate and helpful?"""
    # Uses Llama-3.1-8B via W&B Inference to evaluate quality
    # Returns score 0.0-1.0 based on semantic similarity
```

✅ **Use for**: Answer quality, semantic similarity, helpfulness  
⚠️ **Note**: LLM judges aren't 100% consistent (they're probabilistic)

**3. LLM-as-Judge: Safety Scorer** (Catches Harmful Content)

```python
@weave.op()
def safety_scorer(input: dict, output: dict) -> dict:
    """Safe, appropriate, with proper refusals?"""
    # Evaluates tone (0-1), refusal appropriateness (0-1), safety (0-1)
    # Returns multiple scores for comprehensive safety assessment
```

✅ **Use for**: Detecting toxic content, measuring tone, validating refusals

**View the complete scorers:**

```bash
cat examples/step-4-complete/scorers.py
```

---

### Part D: Run the Evaluation

⚠️ **COST WARNING**: Full evaluation with LLM judges may incur costs depending on your W&B Inference tier (often free for reasonable usage).

**Start with a sample to test:**

```bash
# Test on 10 random cases first
uv run python examples/step-4-complete/run_evaluation.py --sample 10
```

**Understanding the EvaluationLogger Pattern:**

```python
# 1. Initialize BEFORE agent calls (for token tracking!)
eval_logger = EvaluationLogger(
    model="support-bot-v1",
    dataset="support-bot-eval-dataset"
)

# 2. For each test case:
for test_case in dataset.rows:
    output = invoke_agent(agent, test_case["input"])
    
    # Log prediction
    pred_logger = eval_logger.log_prediction(
        inputs={"query": test_case["input"]},
        output=output
    )
    
    # Apply scorers
    pred_logger.log_score(scorer="tool_usage", score=tool_usage_scorer(...))
    pred_logger.log_score(scorer="accuracy", score=accuracy_scorer(...))
    pred_logger.log_score(scorer="safety", score=safety_scorer(...))
    
    # Finish this prediction
    pred_logger.finish()

# 3. Log summary
eval_logger.log_summary()
```

**Why EvaluationLogger?**
- ✅ Incremental logging (log as you go)
- ✅ Automatic token tracking
- ✅ Handles failures gracefully
- ✅ Flexible for custom scorers

**Run full evaluation:**

```bash
# Full evaluation on all 64 cases
uv run python examples/step-4-complete/run_evaluation.py
```

**Or skip LLM judges to save money:**

```bash
# Only run tool correctness scorer (free!)
uv run python examples/step-4-complete/run_evaluation.py --no-llm-judges
```

---

### Part E: Analyze Results in Weave UI

After running the evaluation:

**1. Navigate to Weave Evals Tab:**
- Go to https://wandb.ai/
- Open project: `agentic-support-bot-demo`
- Click **Evals** tab

**2. View Aggregate Metrics:**

You'll see summary statistics:
- **Tool Usage**: 87.5% correct (14/16 tool cases passed)
- **Accuracy**: 0.78 average
- **Safety**: 0.92 average (strong refusals)

**3. Drill into Individual Predictions:**

Click into the eval to see:
- Which test cases passed/failed?
- What did the agent say?
- What were the scores?
- Link to full agent trace

**4. Identify Failure Patterns:**

Group failures by tag to find:
- Are refusal cases passing? (Good!)
- Are tool cases failing? (Check tool descriptions)
- Is accuracy low on debugging questions? (Improve docs search)

**5. Compare Multiple Eval Runs:**
- Select 2+ evaluations
- Click **Compare**
- See side-by-side metrics
- Identify what improved/regressed

---

### What You Learned

**Key Takeaways:**

1. **Manual testing ≠ Production readiness**
   - Ad-hoc testing misses edge cases
   - Systematic evaluation reveals blind spots

2. **Dataset quality > Dataset size**
   - 64 diverse cases beat 200 similar ones
   - Refusal scenarios are critical
   - Adversarial inputs test robustness

3. **Multiple scorer types work together**
   - Rule-based: Fast, cheap, objective
   - LLM judges: Flexible, semantic, subjective

4. **Evaluation is iterative**
   - Run eval → identify failures → improve → re-eval
   - Track metrics over time

5. **Cost management matters**
   - Sample first (--sample 10)
   - Skip expensive scorers in dev
   - Use cheaper judge models

**Production Readiness Checklist:**

After Step 4, you can confidently say:
- ✅ Bot handles diverse realistic questions
- ✅ Bot appropriately refuses off-topic/harmful requests
- ✅ Bot uses tools correctly (measurable)
- ✅ You have quantitative metrics
- ✅ You can test changes systematically

---

**Files Created:**

```
examples/step-4-complete/
├── dataset.py                    # 64 test cases
├── publish_dataset.py            # Publish to Weave
├── scorers.py                    # Rule-based + LLM judges
├── accuracy-judge-config.yaml    # Accuracy judge configuration
├── safety-judge-config.yaml      # Safety judge configuration
└── run_evaluation.py             # EvaluationLogger workflow

tests/
├── test_dataset.py         # 18 dataset validation tests
└── test_scorers.py         # 20 scorer unit tests
```

**Run Tests:**

```bash
uv run pytest tests/test_dataset.py tests/test_scorers.py -v
# All 38 tests should pass ✅
```

---

**Cost Breakdown:**

| Component | Cost per Run | Notes |
|-----------|--------------|-------|
| Agent calls (64 cases) | Free-$1.00 | DeepSeek via W&B Inference |
| Accuracy judges (64) | Free-$0.50 | Llama-3.1-8B via W&B Inference |
| Safety judges (64) | Free-$0.50 | Llama-3.1-8B via W&B Inference |
| **Total** | **Free-$2** | Full evaluation (W&B Inference may be free) |

**Cost-saving tips:**
- Sample first: `--sample 10` to test quickly
- Skip LLM judges: `--no-llm-judges` if you only want tool correctness
- W&B Inference: Using Llama via W&B Inference is often free or very cheap

**Customize Judge Models:**

The judges use **Llama-3.1-8B-Instruct via W&B Inference** by default (fast and cost-effective).

Edit the judge config files to use different models:

```yaml
# examples/step-4-complete/accuracy-judge-config.yaml
model_name: "meta-llama/Llama-3.1-8B-Instruct"  # Default
base_url: "https://api.inference.wandb.ai/v1"
api_key: "${WANDB_API_KEY}"

# Or use gpt-4.1 for higher accuracy:
# model_name: "gpt-4.1"
# base_url: "https://api.openai.com/v1"
# api_key: "${OPENAI_API_KEY}"

# Or use DeepSeek (same as main agent):
# model_name: "openai/deepseek-ai/DeepSeek-R1-0528"
```

Both `accuracy-judge-config.yaml` and `safety-judge-config.yaml` use the same Llama model by default.

---

## Project Structure

```
.
├── examples/               # Complete reference files for skip-ahead
│   ├── step-2b-with-tools/
│   ├── step-3-complete/
│   └── step-4-complete/
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
