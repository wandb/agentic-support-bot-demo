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
- **ngrok account** (free) to expose local server ([sign up here](https://dashboard.ngrok.com/signup))
  - After signup, get your auth token from [your ngrok dashboard](https://dashboard.ngrok.com/get-started/your-authtoken)
  - Used for Step 2 (Playground)
- **Weights & Biases account** ([sign up free](https://wandb.ai/authorize))
  - Your W&B API key is used for both Weave observability AND the LLM API (we use W&B Inference with DeepSeek)
- **Modal account** (free) for production deployment ([sign up](https://modal.com))
  - Used for Step 5 (Production Deployment - optional)
  - Free tier: $30/month credits
- **Slack workspace** (optional) for Slack bot bonus feature ([create workspace](https://slack.com/get-started))
  - Optional bonus in Step 5
  - Not required for main tutorial path

---

# Let's Go! 🚀

## Step 1: Project Setup

This repo includes dependencies, configuration files, and example code so you can focus on agent-specific decisions rather than boilerplate setup.

1. **Clone the repository**

```bash
git clone https://github.com/wandb/agentic-support-bot-demo.git
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

**Edit `.env` and configure:**

**a) Add your W&B API key:**
- `WANDB_API_KEY` - Get your key from [wandb.ai/authorize](https://wandb.ai/authorize)
  - Used for both Weave observability and LLM API (we use W&B Inference with DeepSeek)

**b) Customize your project name:**
- `WANDB_PROJECT` - Add a unique suffix to avoid conflicts (e.g., `agentic-support-bot-demo-yourname`)
  - This is the Weave project where your traces, datasets, and evaluations will appear
  - **Important:** Multiple people using the same project name will overwrite each other's datasets and evaluations

**c) Add your ngrok auth token:**
- `NGROK_AUTHTOKEN` - Get your token from [ngrok dashboard](https://dashboard.ngrok.com/get-started/your-authtoken)
  - Used to expose your local playground server so Weave Playground can connect to it
  - **Note:** You need a free ngrok account to get this token

Example `.env`:
```bash
WANDB_API_KEY=your_api_key_here
WANDB_PROJECT=agentic-support-bot-demo-alice  # ← Add your name here!
NGROK_AUTHTOKEN=your_ngrok_token_here
# PLAYGROUND_API_KEY=your_secret_key_here  # Not needed until Step 2 Part B
```

**Note**: This demo uses W&B Inference with the DeepSeek model by default. You can use other LLM providers supported by [LiteLLM](https://docs.litellm.ai/docs/providers) by modifying the `model_name`, `base_url`, and `api_key` in `workspace/tyler-chat-config.yaml`.

**Note:** The `workspace/` directory is gitignored - you can experiment freely and reset anytime by copying from `examples/`.

4. **📦 Persistent Ticket Database**

In order to make testing the support tools more realistic, we have a small db to persist tickets and allow tools to actually work.

**Set up sample data:**
```bash
cp db/tickets.sample.json db/tickets.json
```

---

## Step 2: Get a Basic Agent Running

Build your agent incrementally, starting simple and adding complexity. Use **Weave at each stage** to understand what's happening.

**Note:** This demo uses the [Slide framework](https://slide.mintlify.app) to get an agent running quickly so you can focus on Weave's observability and evaluation workflow.

---

### Part A: Create Your First Agent

**Goal:** Get a minimal agent running and see your first Weave trace.

Copy the basic agent files to your workspace:

```bash
mkdir -p workspace
cp examples/step-2/part-a/*.{py,yaml} workspace/
```

This gives you:
- `main.py` - Basic agent execution script
- `tyler-chat-config.yaml` - Minimal agent configuration (generic purpose, no tools yet)

**Test it:**

```bash
uv run tyler chat --config workspace/tyler-chat-config.yaml
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

The agent should respond conversationally but won't call any tools.

**🔍 Explore Weave:**

1. Navigate to your Weave project at [wandb.ai](https://wandb.ai) (look for your `WANDB_PROJECT` name)
2. Click **Traces** → filter for `Agent.stream` operations
3. Click into a trace to see the full interaction

**Questions to explore:**
- How many traces do you see? (one per chat message?)
- What information does Weave automatically capture?
- What steps did the agent go through to respond?
- Did the agent call any tools? Why not?

**Key insight:** The agent works and Weave captured everything automatically, but the agent can't DO anything yet - it has no tools!

**Chat Commands:**
- `/quit` or `/exit` - Exit the chat
- `/help` - Show available commands

---

### Part B: Add Tools and MCP Server

**Goal:** Give your agent capabilities (local tools + documentation search).

Copy the new files with tools and MCP enabled:

```bash
cp examples/step-2/part-b/*.{py,yaml} workspace/
```

This adds:
- `tools.py` - Two support ticket tools: `create_issue` and `get_issue`
- `tyler-chat-config.yaml` - Updated config with tools and MCP enabled
- `server.py` - OpenAI-compatible API server for Weave Playground


Open `workspace/tools.py` (line 54) and look at the TOOLS list. Notice the tool definitions have NO descriptions or parameters - just function names. This is intentional! You'll add these in Step 3 to teach the agent when and how to use each tool.

Your updated `workspace/tyler-chat-config.yaml` now includes:

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

**Test in Weave Playground**

In order to use this agent in the playground we need to start a server locally and expose it. `server.py` acts as a bridge between Weave Playground (OpenAI format) and your Tyler agent.

**Set up API key authentication:**

1. **Add to `.env` file:**
   ```bash
   PLAYGROUND_API_KEY=your_secret_key_here  # Can use "dummy" for this demo
   ```

2. **Create team secret in W&B** (W&B Admins only):
   - Navigate to your W&B project → team **Settings** → **Team Secrets**
   - Click **New secret**
   - Name: `PLAYGROUND_API_KEY`
   - Value: Same as your `.env` file
   - Click **Add secret**

   **Note:** If your team already has `PLAYGROUND_API_KEY` set as a team secret, you can use any value in your `.env` file (e.g., "dummy") - the team secret takes precedence.

   See [Secrets documentation](https://docs.wandb.ai/platform/secrets#secrets) for details.

**Start the playground server:**

The server will automatically create an ngrok tunnel and display the public URL:

```bash
uv run workspace/server.py
```

You'll see output like:
```
🌐 NGROK TUNNEL ACTIVE
   Use this Base URL in Weave Playground: https://abc123.ngrok-free.app/v1
```

Copy the URL (e.g., `https://abc123.ngrok-free.app/v1`) for the next step.

**Connect Weave Playground:**

1. Go to your W&B project → navigate to Playground
2. In model dropdown: **+ Add AI provider** → **Custom provider**
3. Fill in:
   - **Provider name**: `buzz_agent`
   - **API key**: `PLAYGROUND_API_KEY`
   - **Base URL**: Your ngrok URL from the server output (already includes `/v1`)
   - **Models**: `buzz`
4. Click **Add provider**
5. Select `buzz_agent/buzz` from the model dropdown

**Test your agent:**

Select `buzz_agent/buzz`, delete the default system message, and try these prompts:

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

**🔍 Check traces in Weave:**

Navigate to Traces → filter for `Agent.stream` operations.

**What to notice:**
- Some traces show tool calls, others don't
- Agent doesn't consistently use tools when it should
- Doesn't "vibe" as a support bot
- **Why?** The agent doesn't know its purpose or when to use tools!

This is what we'll fix in Step 3.

---

## Step 3: Iterate to Make it Vibe as a Support Agent

**What You're Learning:** The core Weave workflow - **observe → diagnose → fix → verify**.

> **⏭️ Want to skip ahead?** `cp examples/step-3/*.{py,yaml} workspace/`  
> ⚠️ **But you'll miss the best part!** Iteration is where Weave shines.

**The Problem:**

Looking at your Weave traces from Step 2:
- Agent responds but doesn't consistently use tools when it should
- Feels like a generic assistant, not a support bot
- ❌ Generic purpose ("helpful AI assistant")
- ❌ Tool definitions missing descriptions and parameters

**🎯 Your Goal:** Make the agent understand its role as a W&B support bot and know when/how to use its tools.

---

#### **Iteration 1: Give Your Agent a Clear Purpose**

Open `workspace/tyler-chat-config.yaml` - the `purpose` field is currently `"You are a helpful AI assistant."` (too generic!)

**Your task:** Rewrite `purpose` to be specific to a W&B support bot. Consider:
- What's the bot's role? (support for Weights & Biases products)
- What should it do? (answer questions, create tickets, search docs)
- What tone? (professional, helpful, concise)

**Hints:**
- Be specific about the product/company
- List key capabilities
- Add a `notes` section for operational guidelines

💡 **Stuck?** See `examples/step-3/tyler-chat-config.yaml` for inspiration, but try your own first!

**Test:** Restart playground server (`uv run workspace/server.py`) and try the test prompts.

**🔍 Observe in Weave:** Does it feel more like a support bot? Check traces to see how `purpose` influences behavior.

---

#### **Iteration 2: Add Tool Descriptions**

Open `tools.py` (line 54). The `TOOLS` list currently has no descriptions or parameters - the agent doesn't know WHEN or HOW to use these tools!

**Your task:** Add complete tool definitions for both tools. For each, add:

1. **`description`** - When should the agent use this tool? What scenarios?
2. **`parameters`** - What arguments does it accept?
3. **Parameter descriptions** - What should each contain? Include examples!
4. **`required`** - Which parameters are mandatory?

**Structure to fill in:**

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

**Tips for good tool descriptions:**
- **Description**: Explain when this tool should be called - give examples of user requests
- **Parameters**: Be specific! Include examples of good values
- **Think from the agent's perspective**: What info would you need to decide when/how to use this?

**Do this for both tools:**
- `support-create_issue` - When to create tickets? What makes a good title vs description?
- `support-get_issue` - When to retrieve status? What does the user need to provide?

💡 **Stuck?** See `examples/step-3/tools.py` for fully documented definitions, but try your own first!

**Test:** Save `tools.py` → restart playground server (`uv run workspace/server.py`) → test the prompts.

**🔍 Observe in Weave:** Do you see better tool usage now?

---

#### **Iteration 3: Compare and Refine**

After making your changes:

1. **Test** with the same prompts
2. **Check Weave traces** - compare before and after:
   - Are tools being called appropriately?
   - Are parameters correct?
   - Does it feel like a support bot?
3. **Iterate more** - tool descriptions are hard to get right the first time!
   - Agent doesn't call tools? → Improve `description`
   - Wrong parameter values? → Improve parameter descriptions
   - Tone off? → Refine `purpose` statement

---

#### **Iteration 4: Verify Your Improvements**

**Test these prompts again** in Weave Playground:

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

**🔍 Use Weave to compare before and after:**

Navigate to Traces → filter for `Agent.stream` → compare new traces side-by-side with old traces from Step 2.

**Ask yourself:**
- ✅ Does the agent search docs when appropriate?
- ✅ Create tickets when users report issues?
- ✅ Retrieve ticket status correctly?
- ✅ Feel like a support bot now?
- ✅ Fill tool parameters correctly?

**Keep iterating if needed:**
- Tools not called correctly? → Refine descriptions
- Tone off? → Adjust `purpose`
- Wrong parameters? → Improve parameter descriptions

💡 **Reference:** Compare your work with `examples/step-3/` - but remember, there's no single "right" way!

---

## Step 4: Dataset & Evaluation - From Vibes to Production-Ready

After Step 3, your agent works well in demos. But can you confidently deploy it to real users?

**Goal:** Move from "it feels right" to "it's provably ready for production" by building systematic evaluation with a comprehensive test dataset and automated scoring.

---

### Part A: Create an Evaluation Dataset

Copy the dataset files to your workspace:

```bash
cp examples/step-4/part-a/*.py workspace/
```

This gives you:
- `dataset.py` - 30 synthetically generated test cases
- `publish_dataset.py` - Script to publish dataset to Weave

**Dataset Coverage:**
- **13 W&B/Weave questions**: Initialization, debugging, troubleshooting, features
- **8 Tool usage scenarios**: Support ticket creation and retrieval
- **9 Refusal scenarios**: Off-topic questions, inappropriate requests, adversarial attempts

**Dataset Structure:**

Each test case includes:
```python
{
    "input": "How do I initialize Weave in Python?",
    "expected_output_description": "Call weave.init() with your project name...",
    "expected_tools": [],  # Tools that should be called
    "tags": ["weave", "initialization", "factual"]
}
```

Note: `expected_output_description` describes what a good answer should contain (not an exact match). LLM-based scorers use this to evaluate quality.

**Publish Dataset to Weave**

Publishing provides versioning, reproducibility, and team collaboration:

```bash
uv run workspace/publish_dataset.py
```

This script:
1. Validates dataset structure (≥50 cases, required fields)
2. Connects to Weave using your `WANDB_API_KEY`
3. Publishes as `support-bot-eval-dataset`
4. Creates version history (each publish = new version)

**Verify:** Go to your project → find `support-bot-eval-dataset` → browse the rows.

---

### Part B: Build Evaluation Scorers

How do you measure if the agent's responses are good? You need scorers to evaluate:
- **Tool usage** - Are the right tools called?
- **Accuracy** - Is the answer correct and helpful?
- **Safety** - Is the tone appropriate? Does it refuse when it should?

We'll use a combination of **rule-based scorers** (fast, deterministic) and **LLM-as-judge scorers** (flexible, nuanced).

Copy the scorers and judge configurations:

```bash
cp examples/step-4/part-b/*.{py,yaml} workspace/
```

This gives you:
- `scorers.py` - Rule-based and LLM-based scorers
- `accuracy-judge-config.yaml` - Configuration for accuracy judge
- `safety-judge-config.yaml` - Configuration for safety judge

**Three types of scorers:**

| Scorer | Measures | Type | Best For |
|--------|----------|------|----------|
| `tool_usage_scorer` | Did agent call correct tools? | Rule-based (fast, deterministic) | Objective checks |
| `accuracy_scorer` | Is answer accurate and helpful? | LLM judge (flexible) | Answer quality, semantic similarity |
| `safety_scorer` | Appropriate tone and refusals? | LLM judge (flexible) | Toxic content, tone, refusals |

Open `scorers.py` to see the implementation details.

---

### Part C: Run the Evaluation

Copy the evaluation script:

```bash
cp examples/step-4/part-c/*.py workspace/
```

This gives you:
- `run_evaluation.py` - Complete evaluation runner using EvaluationLogger

**Start with a sample to test:**

```bash
# Test on 5 random cases first
uv run workspace/run_evaluation.py --sample 5
```

**The EvaluationLogger Pattern:**

```python
# 1. Load the published dataset
dataset = weave.ref("support-bot-eval-dataset:latest").get()

# 2. Initialize (before any LLM calls for token tracking)
eval_logger = EvaluationLogger(
    name="support-bot-eval",
    model=agent.name,  # References the Weave-tracked Agent object
    dataset=dataset  # Pass Dataset object to reference existing dataset
)

# 3. For each test case: invoke agent → log prediction → apply scorers
for test_case in dataset.rows:
    output = await invoke_agent(agent, test_case["input"])
    pred_logger = eval_logger.log_prediction(inputs={"query": test_case["input"]}, output=output)
    pred_logger.log_score(scorer="tool_usage", score=tool_usage_scorer(...))
    pred_logger.finish()

# 4. Log summary
eval_logger.log_summary()
```

**Why EvaluationLogger?** Incremental logging, automatic token tracking, graceful failure handling.

**Run full evaluation:**

```bash
uv run workspace/run_evaluation.py  # All 31 cases
```

---

**Analyze Results in Weave UI**

**1. Navigate to Evals:**
- Go to [wandb.ai](https://wandb.ai) → your project (set via `WANDB_PROJECT`) → **Evals** tab

**2. View aggregate metrics:**
- Tool Usage: % correct
- Accuracy: Average score
- Safety: Average score

**3. Drill into predictions:**
- Which test cases passed/failed?
- What did the agent say?
- View full agent trace

**4. Identify patterns:**
- Group failures by tag
- Are refusal cases passing?
- Are tool cases failing? (refine descriptions)
- Is accuracy low on specific topics? (improve docs search)

**5. Compare eval runs:**
- Select 2+ evaluations → **Compare**
- See side-by-side metrics
- Identify improvements/regressions

---

### What's Next: From Baseline to Better

**You now have a baseline!** With quantitative metrics, you can iterate systematically to improve your agent.

**Levers to Adjust:**

1. **Purpose and Notes** (`tyler-chat-config.yaml`) - Add examples, refine tone guidance
2. **Tool Descriptions** (`tools.py`) - Clarify when to use each tool, add examples
3. **Model Selection** (`tyler-chat-config.yaml`) - Try `gpt-4.1`, adjust `temperature`, experiment with `reasoning` levels
4. **MCP Search Strategy** - Review traces where docs search failed

**Iteration Workflow:**

1. Run baseline evaluation → Identify lowest-scoring categories
2. Pick ONE thing to improve → Make targeted changes
3. Re-run evaluation → Compare metrics with baseline
4. Analyze in Weave → Did the change help? Hurt anything else?
5. Repeat → Iterate on the next weakness

**Example:** If tool usage is low (60%), review traces where tools weren't called → improve tool `description` → add examples → re-run eval.

---

### Ready for Production?

At this point, your agent works well in the playground and you have confidence from systematic evaluation. **But the real test is production.** 

Continue to **Step 5** to deploy your agent where it matters - in front of real users. You'll learn how to:
- Deploy as a Slack bot (or other channels)
- Monitor production performance in real-time
- Collect user feedback to identify failures
- Build datasets from production data
- Create a continuous improvement loop

---

## Step 5: Production Deployment 🚀

> **📝 Note:** This step is optional! You can skip directly to Step 6 (Monitoring) using your local server from Step 2. However, deploying to Modal gives you a more realistic production experience and persistent deployment that stays up even when your laptop is closed.

**Goal:** Deploy your agent to production on Modal cloud platform.

After building confidence through systematic evaluation, it's time to deploy to the cloud! You'll deploy the same server you've been using locally to Modal, point Weave Playground at the production URL, and see that Weave traces work identically in production.

**Key Insight:** The same `server.py` that ran locally in Step 2 now runs in the cloud. Same code, same traces, same observability - just deployed to production!

**Prerequisites:**
- Completed Steps 1-4 (you have a working agent in `workspace/`)
- Free Modal account ([sign up](https://modal.com))

---

### Part A: Deploy to Modal

**Step 1: Install Modal**

```bash
uv pip install modal
```

**Step 2: Authenticate with Modal**

```bash
modal setup
```

This opens a browser to authenticate. Follow the prompts.

**Step 3: Configure Modal Secrets**

Set your W&B and Playground API keys as Modal secrets:

```bash
modal secret create wandb-secrets \
  WANDB_API_KEY=<your-wandb-api-key> \
  PLAYGROUND_API_KEY=<your-playground-api-key>
```

Replace placeholders with your actual keys:
- Get `WANDB_API_KEY` from [wandb.ai/authorize](https://wandb.ai/authorize)
- Use the same `PLAYGROUND_API_KEY` from your `.env` file

**Step 4: Deploy to Modal**

Deploy the same `server.py` you've been using locally:

```bash
modal deploy workspace/server.py
```

You'll see output like:
```
✓ Created objects.
├── 🔨 Created mount /Users/you/project/workspace
└── 🔨 Created tyler-production-server.fastapi_app
✓ App deployed! 🎉

View Deployment: https://modal.com/apps/...
```

**Step 5: Get Your Deployment URL**

```bash
modal app list
```

Look for `tyler-production-server` and note the URL. It will look like:
```
https://username--tyler-production-server-fastapi-app.modal.run
```

**Step 6: Test the Health Endpoint**

```bash
curl https://your-modal-url/health
```

You should see:
```json
{"status":"healthy","timestamp":"2025-11-03T12:00:00Z","agent_name":"agent"}
```

✅ **Your agent is now deployed to Modal!** The same server that worked locally with ngrok now runs in the cloud.

---

### Part B: Connect Weave Playground to Production

Now let's chat with your production agent! In Step 2, you used Weave Playground with your local server (via ngrok). Now you'll point it to your Modal deployment.

**Step 1: Update Weave Playground Provider**

1. Go to your W&B project → **Weave** → **Playground**
2. Find the `buzz_agent` provider you created in Step 2
3. Click the edit icon (⚙️) next to it
4. Update the **Base URL** to your Modal URL:
   ```
   https://your-modal-url/v1
   ```
   (Replace `your-modal-url` with the URL from Part A, Step 5)
5. Keep the same **API key**: `PLAYGROUND_API_KEY`
6. Click **Save**

Alternatively, create a new provider called `production-bot`:
- **Provider name**: `production-bot`
- **API key**: `PLAYGROUND_API_KEY`
- **Base URL**: `https://your-modal-url/v1`
- **Models**: `buzz`

**Step 2: Chat with Production Agent**

1. Select `buzz_agent/buzz` (or `production-bot/buzz`) from the model dropdown
2. Delete the default system message
3. Send a test message:
   ```
   How do I initialize Weave in Python?
   ```

**Step 3: Verify Response**

The bot should respond just like it did locally in Step 2!

**Step 4: Check Weave Traces**

1. Go to **Traces** tab
2. Filter for recent traces
3. Click into a trace to see:
   - Your Playground message
   - Agent reasoning
   - Tool calls (if applicable)
   - LLM requests
   - Full conversation context

**Key Observation**: The traces look identical to Step 2, but now they're from production! Same observability, just deployed to the cloud.

✅ **You're chatting with a production-deployed agent!**

---

### Part C: Verify Production Deployment

Let's confirm your deployment persists even when your laptop is off.

**Step 1: Close Your Laptop**

Seriously! Close it for a few minutes.

**Step 2: Open and Test**

1. Open laptop
2. Go to Weave Playground
3. Send another message to your production agent
4. It still works! ✅

**Why this matters**: 
- Your local server (Step 2) required your laptop running
- Modal deployment is always-on in the cloud
- Perfect for ongoing monitoring in Step 6

---

### Bonus: Slack Integration (Optional)

Want to chat with your bot via Slack @ mentions? The `server.py` already includes Slack webhook support!

**Quick Setup:**
1. Create Slack app at [api.slack.com/apps](https://api.slack.com/apps)
2. Add bot scopes: `app_mentions:read`, `chat:write`
3. Enable Event Subscriptions pointing to `https://your-modal-url/slack/events`
4. Get Bot Token and Signing Secret
5. Add to Modal:
   ```bash
   modal secret create slack-secrets \
     SLACK_BOT_TOKEN=xoxb-... \
     SLACK_SIGNING_SECRET=...
   ```
6. Redeploy: `modal deploy workspace/server.py`
7. @ mention your bot in Slack!

Both Slack and Playground conversations appear in Weave traces.

---

### Troubleshooting

**Modal Deployment Issues:**

- `Secret not found` → Run `modal secret list` to verify `wandb-secrets` is created
- `Import error: tyler` → Modal image should auto-install dependencies
- `Agent config not found` → Ensure `tyler-chat-config.yaml` is in workspace directory

**Weave Playground Can't Connect:**

- Verify Modal URL is correct (use `modal app list`)
- Ensure URL includes `/v1` at the end
- Check API key matches your `PLAYGROUND_API_KEY`
- Test health endpoint first: `curl https://your-modal-url/health`

**Agent Not Responding:**

1. Check Modal logs: `modal app logs tyler-production-server`
2. Verify deployment is running: `modal app list`
3. Check Weave traces for agent errors
4. Try local test first: `uv run workspace/server.py --no-ngrok`

**Viewing Logs:**

```bash
# View real-time logs
modal app logs tyler-production-server --follow

# View last 100 lines
modal app logs tyler-production-server -n 100
```

**Cold Start (First Request Slow):**

The first request after idle may take 5-10 seconds while Modal starts the container. This is normal. Subsequent requests will be faster (warm containers).

---

### What's Next: Production Monitoring

**You now have a production agent!** 

Continue to **Step 6** to set up:
- Real-time monitoring dashboards
- User feedback collection
- Production performance metrics
- Quality monitoring with Weave

All production conversations are already flowing to Weave traces, ready for analysis in Step 6! 🎉

---

## Step 6: Online Monitoring & Feedback Collection 📊

> **🚧 COMING SOON**  
> This step is currently under development. Check back soon for the full guide on production monitoring!

**Goal:** Monitor how your agent performs with real users and collect feedback to identify areas for improvement.

Offline evaluations tell you how the agent *should* perform. Production monitoring tells you how it *actually* performs. This step closes the loop between deployment and improvement by showing you what's happening in production and where to focus your efforts.

**What You'll Accomplish:**
- Build a monitoring dashboard to track production performance metrics (latency, costs, volume, errors)
- Collect user feedback directly in your deployment channel (thumbs up/down reactions)
- Use Weave's feedback API to associate user reactions with specific traces
- Identify patterns in failures by analyzing poorly-rated conversations
- Optionally set up automated monitors that score production traffic in the background

---

## Step 7: Continuous Improvement Loop 🔄

> **🚧 COMING SOON**  
> This step is currently under development. Check back soon for the full guide on continuous improvement!

**Goal:** Use production data to systematically improve your agent over time.

This is where everything comes together: evaluation → deployment → monitoring → improvement. You'll close the loop by turning production failures into test cases, running regression tests, and safely deploying improvements.

**What You'll Accomplish:**
- Export poorly-rated production conversations and turn them into evaluation test cases
- Add production examples to your evaluation dataset (with proper versioning in Weave)
- Run evaluations on the enriched dataset before deploying any changes
- Establish a safe deployment workflow with regression checks
- Understand how to compare metrics across iterations to ensure improvements don't break existing functionality
- Optionally explore A/B testing patterns for validating changes with real users

**Key Insight:** Your evaluation dataset should evolve with your product. By continuously adding real production failures, your offline evaluations become increasingly predictive of production performance. This creates a virtuous cycle where each production incident makes your agent more robust.

---

## Troubleshooting

**Configuration Issues:**
- `Configuration file not found` → Run from project root, ensure `workspace/tyler-chat-config.yaml` exists
- `Failed to load tool from path` → Verify `workspace/tools.py` exists and exports `TOOLS` list

**Environment Variables:**
- `Missing required environment variable: WANDB_API_KEY` → Create `.env` from `.env.example`, add your W&B API key
- `OpenAI API authentication error` → Verify `OPENAI_API_KEY` in `.env` or use different LLM provider in config

**Tool Execution:**
- Tools aren't being called → Check tool descriptions, view traces in Weave to see what agent is doing
- `Warning: Failed to initialize Weave` → Non-blocking, but check `WANDB_API_KEY` for full observability

**Python Environment Issues:**
- If you have `pyenv` or other Python version managers active, you may need to deactivate them first (`pyenv deactivate` or similar) before running `uv` commands
- **macOS**: If you see import errors related to `magic`, install: `brew install libmagic`

**Debug Mode:**
```bash
TYLER_DEBUG=1 uv run tyler chat --config workspace/tyler-chat-config.yaml
```

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
