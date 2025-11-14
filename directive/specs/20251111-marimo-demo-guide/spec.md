# Spec (per PR)

**Spec ID**: 20251111  
**Created**: 2025-11-11  

**Feature name**: Marimo Interactive Demo Guide  
**One-line summary**: Add an interactive Marimo notebook that guides users through the agentic support bot tutorial with one-click actions and seamless Weave UI integration  

---

## Problem

The current README-based tutorial is comprehensive but creates friction for users:

1. **Cognitive Load**: 1000+ line README requires extensive scrolling to find the current step
2. **Manual Execution**: Users must copy/paste terminal commands, risking typos and path errors
3. **Context Switching**: Users jump between README (instructions) → terminal (commands) → IDE (file editing) → browser (Weave UI) → back to README
4. **Progress Tracking**: No visual indication of completion or what's remaining
5. **Configuration Editing**: Editing YAML/Python files requires understanding file locations and syntax
6. **Navigation**: Hard to jump between steps or review previous instructions

This friction reduces engagement and increases time-to-value for learning Weave's observability and evaluation workflow.

## Goal

Create an interactive Marimo notebook (`marimo-guide.py`) that serves as a **complete alternative** to the README tutorial, providing:

1. **Full coverage of Steps 1-6** - Users can complete the entire tutorial using only the Marimo guide
2. **Tab-based navigation** with progress tracking and clear step transitions
3. **One-click actions** for file copying, server deployment, evaluation runs, and all setup tasks
4. **Seamless Weave UI integration** with context-specific deep links (Playground, Traces, Evals, Monitors)
5. **Inline editing** for configs and prompts without leaving the notebook
6. **Weave-first learning** by keeping all analysis, exploration, and validation in Weave UI (not the notebook)
7. **Error prevention** with validation checks, status feedback, and helpful error messages

**Key Insight**: The notebook is a **full tutorial alternative** that handles mechanical work (setup, commands, deployments) while directing users to Weave UI for actual learning (testing, analysis, iteration). Users can choose Marimo OR README based on their preference.

## Success Criteria

- [ ] Users can complete Steps 1-6 faster using Marimo guide vs README alone (measured by internal testing)
- [ ] Users spend more time in Weave UI (good!) and less time debugging terminal commands (bad!)
- [ ] All one-click actions (deploy, evaluate, copy files) work correctly on first try
- [ ] Notebook opens Weave UI at contextually appropriate moments (e.g., "View Traces" after testing in Playground)
- [ ] Users can edit agent configs inline and see results immediately
- [ ] Progress indicators show completion status for each step
- [ ] The guide is a complete alternative - users can complete entire tutorial using only Marimo OR only README
- [ ] Notebook works on macOS, Linux, and Windows with Python 3.12+

## User Story

**As a developer learning Weave's observability and evaluation workflow**,  
I want an interactive guide that handles the mechanical work (commands, file copying, deployments),  
so that I can focus on understanding Weave concepts and analyzing agent behavior in the Weave UI.

## Flow / States

**Coverage**: The Marimo guide includes ALL Steps 1-6. Below are detailed flows for the most interactive steps (2B, 4). Other steps follow similar patterns with context-appropriate actions.

### All Steps Overview

**Note**: Users reach Marimo after completing minimal bootstrap in README (clone, uv sync, start marimo). The notebook assumes these are already done.

**Step 1: Project Setup**
- Welcome message confirming successful Marimo launch
- Environment validation (Python version, dependencies installed)
- `.env` file configuration helper with field-by-field guidance
- Workspace directory setup button (`mkdir -p workspace/db`, copy sample data)
- Validation checks confirming all prerequisites met
- "Ready!" confirmation before proceeding to Step 2

**Step 2A: Create First Agent**
- Copy basic agent files button
- Instructions for running tyler chat CLI
- Test prompt suggestions
- Links to view first traces in Weave

**Step 2B: Add Tools & MCP** (detailed flow below)

**Step 3: Iterate**
- Current config viewer with syntax highlighting
- Inline editor for agent purpose and tool descriptions
- Save and auto-restart server
- Quick links to Playground and Traces
- Before/after comparison guidance

**Step 4: Dataset & Evaluation** (detailed flow below)

**Step 5: Production Deployment**
- One-click production deploy button
- Production URL capture and display
- Instructions for adding production provider to Playground
- Link to create production Saved View in Weave

**Step 6: Monitoring & Guardrails**
- Copy guardrails files button
- Guardrails code explanation
- Deploy with guardrails button
- Test prompts for adversarial testing
- Step-by-step monitor creation guide (links to Weave UI)
- Instructions for copying Step 4 scorer prompts to monitors

---

### Happy Path: Step 2B (Add Tools & Deploy)

1. User opens `marimo-guide.py` in browser (`marimo edit marimo-guide.py`)
2. User navigates to "Step 2: Basic Agent" tab → "Part B: Add Tools" section
3. User clicks **[📁 Copy Step 2B Files]** button
   - Notebook runs: `cp examples/step-2/part-b/*.{py,yaml} workspace/`
   - Shows ✅ success message: "Files copied! Check workspace/tools.py"
4. User completes Modal setup checklist (3 checkboxes):
   - ☑ Modal authenticated (`modal setup`)
   - ☑ Created dev environment
   - ☑ Created Modal secrets
5. Deploy button becomes enabled when checklist complete
6. User clicks **[🚀 Start Dev Server]** button
   - Notebook runs: `modal serve --env dev workspace/server.py`
   - Shows live output stream with URL highlighted
7. When server URL detected, notebook shows:
   - **[🎮 Open Weave Playground]** button
   - Instructions for adding custom provider in Playground
   - Test prompt suggestions with copy buttons
8. User clicks **[🎮 Open Weave Playground]** → Opens in new tab
9. User tests prompts in Playground (works in Weave UI, not notebook)
10. User returns to notebook, clicks **[🔍 View Traces]** button → Opens Weave Traces filtered to recent calls
11. User analyzes traces in Weave UI
12. User returns to notebook, clicks "Continue to Step 3" → Advances to next tab

### Happy Path: Step 4 (Evaluation)

1. User navigates to "Step 4: Evaluation" tab
2. User clicks **[📁 Copy All Step 4 Files]** button
3. User clicks **[📤 Publish Dataset]** button
   - Notebook runs `publish_dataset.py` with progress indicator
   - Extracts dataset URL from output
   - Shows **[📊 View Dataset in Weave]** button
4. User clicks button → Opens dataset in Weave UI
5. User explores dataset in Weave (sees 31 test cases, tags, expected outputs)
6. User returns to notebook
7. User adjusts sample size slider (set to 5 for quick test)
8. User clicks **[▶️ Run Evaluation]** button
   - Notebook runs evaluation with live progress
   - Shows completion status
   - Displays **[📈 View Results in Weave]** button
9. User clicks button → Opens Weave Evals tab
10. User analyzes results in Weave (scores, failures, patterns)
11. User returns to notebook to iterate
12. User edits config in inline YAML editor
13. User clicks **[💾 Save Config]** → Updates `workspace/tyler-chat-config.yaml`
14. User clicks **[▶️ Run Evaluation]** again to test improvement
15. Cycle repeats: analyze in Weave → edit in notebook → re-evaluate

### Edge Case: Server Deploy Failure

1. User clicks **[🚀 Start Dev Server]** but Modal secrets not configured
2. Notebook detects error in output
3. Shows error callout with troubleshooting steps:
   - "❌ Missing Modal secrets. Run: `modal secret create...`"
   - Link to troubleshooting section
4. User fixes issue, clicks button again
5. Server starts successfully

### Edge Case: Environment Variable Missing

1. User opens notebook but `WANDB_API_KEY` not set
2. Notebook detects missing env var on startup
3. Shows prominent warning banner at top:
   - "⚠️ Required: Set WANDB_API_KEY in .env file"
   - Instructions with expandable details
4. Action buttons disabled until env configured
5. User sets env var and refreshes notebook
6. Warning clears, buttons become enabled

## UX Links

- Marimo Documentation: https://docs.marimo.io/
- Marimo UI Elements: https://docs.marimo.io/guides/interactivity/
- Weave Playground: https://docs.wandb.ai/weave/guides/tools/playground
- Weave Traces: https://docs.wandb.ai/weave/guides/tracking/tracing

## Requirements

### Must Have

- **README Updates**:
  - Minimal "Getting Started" section at the top with universal bootstrap steps (clone, uv sync)
  - Immediate choice point: "Choose Your Path: Option A (Marimo) or Option B (README)"
  - Option A instructions: "Run `marimo edit marimo-guide.py`" with clear indication this is preferred
  - Option B indication: "Continue reading below"
  - Rest of README remains unchanged (full Step 1-6 content for traditional users)

- **Navigation Structure**:
  - Tab-based navigation for ALL Steps 1-6 (using `mo.ui.tabs()`)
  - Each step is fully self-contained with all necessary instructions and actions
  - Progress indicators showing completion status per step
  - Clear section headers matching README structure
  - "Continue to Step X" buttons for forward navigation
  - "Jump to Step X" quick navigation for experienced users

- **One-Click Actions** (covering all steps):
  - **Step 1**: Dependency installer (`uv sync`), workspace setup
  - **Step 2A**: Copy basic agent files
  - **Step 2B**: Copy tools/server files, Modal setup, dev server deployment
  - **Step 3**: Copy improved tools, config save/reload
  - **Step 4**: Copy eval files, publish dataset, run evaluations with sample control
  - **Step 5**: Production deployment button
  - **Step 6**: Copy guardrails files, deploy with guardrails
  - All file operations include confirmation and status feedback

- **Weave UI Integration**:
  - Deep links to Playground with pre-filled provider info
  - Deep links to Traces with relevant filters (operation, env tag)
  - Deep links to Evals showing specific evaluation runs
  - Deep links to Monitors tab for configuration
  - Deep links to Datasets for exploration
  - All links open in new browser tabs

- **Inline Editors**:
  - YAML editor for `tyler-chat-config.yaml` with syntax highlighting
  - Text area for editing agent `purpose` with character count
  - Code editor for tool descriptions (optional)
  - Save buttons persist changes to workspace files

- **Status & Feedback**:
  - Success callouts (green) for completed actions
  - Error callouts (red) with troubleshooting steps
  - Warning callouts (yellow) for missing prerequisites
  - Live output streaming for long-running commands
  - Loading indicators for async operations
  - Checkboxes for prerequisite validation

- **Environment Detection**:
  - Check for `WANDB_API_KEY`, `OPENAI_API_KEY` on startup
  - Detect if Modal is authenticated
  - Warn if required files missing
  - Show Python version and dependency status

- **Documentation**:
  - Each step includes learning objectives
  - Inline hints and tips (expandable accordions)
  - Links to relevant Weave docs for deep dives
  - Quick reference for commands (for users who prefer terminal)
  - Clear statement at top: "This guide assumes you've completed the Getting Started section in README"

### Must Not

- Must not replace Weave UI for analysis (all exploration happens in Weave)
- Must not create custom visualizations that duplicate Weave features
- Must not auto-execute commands without user confirmation
- Must not hide complexity that users need to understand
- Must not make the notebook required (both Marimo and README are complete alternatives)
- Must not run multiple modal serve instances simultaneously
- Must not modify files outside `workspace/` directory
- Must not expose sensitive credentials in notebook UI

### Nice to Have (Optional)

- Live trace preview (fetch recent trace from Weave API and show summary)
- Config diff viewer (compare current vs example configs)
- Estimated time indicators for each step
- Keyboard shortcuts for navigation
- Export step completion report
- Integration with README (show relevant sections inline)

## Acceptance Criteria

### Environment Setup

- **Given** user opens notebook without `.env` file, **when** notebook loads, **then** shows warning banner with setup instructions
- **Given** user has `.env` configured, **when** notebook loads, **then** detects and validates environment variables
- **Given** Python version < 3.12, **when** notebook loads, **then** shows error message explaining version requirement

### File Operations

- **Given** user on Step 2B, **when** clicks [Copy Files] button, **then** files copied to workspace/ and success message shown
- **Given** files already exist, **when** clicks [Copy Files] button, **then** prompts for confirmation before overwriting
- **Given** copy fails (permissions), **when** operation errors, **then** shows error with specific reason

### Server Deployment

- **Given** Modal prerequisites incomplete, **when** user tries to deploy, **then** button disabled with tooltip explaining requirements
- **Given** prerequisites complete, **when** clicks [Start Dev Server] button, **then** `modal serve` runs with live output
- **Given** server starting, **when** Modal URL appears in output, **then** notebook extracts and highlights URL
- **Given** server running, **when** clicks [Start Dev Server] again, **then** warns that server already running

### Weave UI Integration

- **Given** server deployed, **when** clicks [Open Playground] button, **then** opens Weave Playground in new tab with correct project
- **Given** traces exist, **when** clicks [View Traces] button, **then** opens Weave Traces with filter for Agent.stream operations
- **Given** evaluation complete, **when** clicks [View Results] button, **then** opens Weave Evals showing most recent run
- **Given** no project configured, **when** clicks Weave link, **then** opens Weave home (graceful degradation)

### Evaluation Workflow

- **Given** dataset not published, **when** clicks [Run Evaluation] button, **then** shows error prompting to publish first
- **Given** sample size = 5, **when** clicks [Run Evaluation] button, **then** runs with `--sample 5` flag
- **Given** evaluation running, **when** monitoring progress, **then** shows live progress indicator
- **Given** evaluation complete, **when** showing results, **then** extracts and displays summary metrics

### Config Editing

- **Given** Step 3, **when** user edits `purpose` in text area, **then** character count updates live
- **Given** user modifies config, **when** clicks [Save] button, **then** writes to workspace/tyler-chat-config.yaml
- **Given** save successful, **when** confirming, **then** shows success message and prompts to re-deploy
- **Given** YAML syntax error, **when** clicking [Save] button, **then** shows validation error with line number

### Progress Tracking

- **Given** user completes Step 2, **when** viewing progress, **then** Step 2 tab shows ✓ indicator
- **Given** user on Step 4, **when** checking prerequisites, **then** shows which prior steps must be complete
- **Given** user navigates between tabs, **when** returning to completed step, **then** preserves completion state

### Negative Cases

- **Given** network error during Modal deploy, **when** operation fails, **then** shows error with retry button
- **Given** Weave API unavailable, **when** clicking [View Traces] button, **then** falls back to opening project home
- **Given** malformed YAML in editor, **when** clicking [Save] button, **then** shows validation error without saving
- **Given** workspace/ directory missing, **when** trying file operations, **then** offers to create directory

## Non-Goals

- Building a complete IDE within Marimo (users still edit in their preferred editor)
- Creating custom trace visualization (use Weave UI for analysis)
- Real-time collaboration features (single-user experience)
- Mobile responsiveness (desktop-focused workflow)
- Integration with other notebook formats (Jupyter, etc.)
- Automated testing within notebook (tests run via pytest)
- Production deployment from notebook (users deploy via terminal)
- Custom themes or branding
- Offline mode (requires Weave API access)
- Multi-language support (English only initially)
- Video tutorials or interactive tours
- Integration with LMS or learning platforms
- Gamification or achievement system

---

## Additional Context

### Why Marimo vs Jupyter?

- **Reactive execution**: Changes propagate automatically (no manual cell re-running)
- **Pure Python**: Notebook is a `.py` file, works with git and code review
- **Modern UI**: Better widgets and interactivity out of the box
- **No hidden state**: Cell execution order doesn't matter
- **Built-in deployment**: Can serve as web app with `marimo run`

### Integration with Existing Tutorial

**Bootstrap Flow:**
1. README contains minimal setup that EVERYONE must do:
   - Clone repository
   - Install uv
   - Run `uv sync` (installs all dependencies including Marimo)
2. README immediately presents the choice:
   - **Option A: Interactive Guide (Marimo)** 🎮 - Run `marimo edit marimo-guide.py` (preferred)
   - **Option B: Traditional Guide (README)** 📖 - Continue reading below
3. User picks their path and completes Steps 1-6

**Content Parity:**
- Marimo covers ALL steps 1-6 with full instructions and one-click actions
- README covers ALL steps 1-6 with traditional markdown instructions
- Both contain identical learning objectives and outcomes
- Both should stay in sync for content/instructions
- Users can switch between them at any time

### Target Audience

- Developers new to Weave (primary)
- Experienced ML engineers exploring observability (secondary)
- Engineering teams evaluating Weave for production use
- W&B employees dogfooding products

