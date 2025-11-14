# Technical Design Review (TDR) — Marimo Interactive Demo Guide

**Spec ID**: 20251111  
**Created**: 2025-11-11  
**Author**: AI Agent  
**Links**: 
- Spec: `/directive/specs/20251111-marimo-demo-guide/spec.md`
- Impact: `/directive/specs/20251111-marimo-demo-guide/impact.md`
- Marimo Documentation: https://docs.marimo.io/
- Marimo GitHub: https://github.com/marimo-team/marimo

---

## 1. Summary

We are building an interactive Marimo notebook (`marimo-guide.py`) that serves as a complete alternative to the README-based tutorial for the agentic support bot demo. The guide provides a structured, tab-based interface that orchestrates the user's journey through Steps 1-6 with progress tracking, automated file operations, inline config editing, and contextual deep links to Weave UI.

**Key Value Proposition**: While users still need a terminal open for interactive commands (tyler chat, modal serve), the Marimo guide significantly reduces cognitive load by providing structure, validation, automation where possible, and eliminating errors from typos/incorrect commands. Users choose between Marimo (interactive, structured) or README (traditional, markdown) after completing minimal bootstrap setup.

**Why This Matters**: The current 1000-line README creates friction through extensive scrolling, manual command execution, and lack of progress feedback. The Marimo guide keeps users focused on Weave learning objectives while handling mechanical tasks, resulting in faster completion and better learning outcomes.

## 2. Decision Drivers & Non‑Goals

### Decision Drivers

**Educational Experience**:
- Users must spend time learning Weave, not fighting with setup
- Clear progress indicators reduce drop-off
- Validation prevents wasted time debugging environment issues
- Weave-first approach: all analysis happens in Weave UI (not notebook)

**Error Reduction**:
- Automated file operations eliminate copy/paste typos
- Prerequisite checks catch issues early
- Copy-to-clipboard buttons reduce command typos
- YAML validation prevents config syntax errors

**Accessibility**:
- Both paths (Marimo + README) must be equally complete
- Marimo optional, not required (accommodate all user preferences)
- Works across platforms (macOS, Linux, Windows)
- Degrades gracefully (if Marimo fails, README still works)

**Maintenance Burden**:
- Keep notebook implementation simple (resist over-engineering)
- Accept manual sync between README and Marimo
- Focus on high-value automation, skip marginal gains
- Pure Python (no DSLs or templating complexity)

### Non‑Goals

- ❌ Zero terminal usage (users will need terminal for interactive commands)
- ❌ Custom trace visualization (use Weave UI for analysis)
- ❌ Automated code generation or AI assistance
- ❌ Real-time collaboration or multi-user features
- ❌ Mobile responsiveness (desktop workflow)
- ❌ Production deployment orchestration (user deploys via terminal)
- ❌ Integration with other notebook formats (Jupyter, etc.)
- ❌ Telemetry or usage analytics (privacy-first approach)
- ❌ Perfect content sync between README and Marimo (accept some drift)

## 3. Current State — Codebase Map (concise)

### Key Modules (Existing)

**Tutorial Structure**:
- `README.md` (1025 lines) - Current tutorial, Steps 1-6
- `examples/step-*/` - Reference implementations for each step
- `workspace/` - User's working directory for tutorial completion
- `db/tickets.sample.json` - Sample data for support tools

**Dependencies** (`pyproject.toml`):
- `slide-agents` - Agent framework
- `weave` - Observability and evaluation
- `modal` - Serverless deployment
- `uv` - Package manager (system requirement)
- **Missing**: `marimo` (to be added)

**Test Infrastructure** (`tests/`):
- Unit tests for tools, scorers, guardrails
- Integration tests for server endpoints
- No tests for tutorial flow (validated manually)

### Existing Data Models

**Project Structure**:
```
repo/
├── README.md (tutorial)
├── examples/ (step reference code)
├── workspace/ (user workspace)
├── db/ (sample data)
├── tests/ (validation)
└── pyproject.toml (dependencies)
```

**User Workspace** (created during tutorial):
```
workspace/
├── tyler-chat-config.yaml
├── server.py
├── tools.py
├── guardrails.py
├── dataset.py
├── scorers.py
├── run_evaluation.py
└── db/tickets.json
```

### External Contracts

**README Format** (markdown):
- Steps 1-6 with headings, code blocks, commands
- No interactive elements
- Linear navigation (scrolling)

**Weave UI URLs**:
- Playground: `https://wandb.ai/{entity}/{project}/playground`
- Traces: `https://wandb.ai/{entity}/{project}/traces`
- Evals: `https://wandb.ai/{entity}/{project}/weave/evaluations`
- Monitors: `https://wandb.ai/{entity}/{project}/weave/monitors`

### Observability (Current)

**Available**:
- None (tutorial is local, no observability)

**Not Needed**:
- Tutorial tool runs locally, no production concerns

## 4. Proposed Design (high level, implementation‑agnostic)

### Overall Architecture

```
User Journey:
1. Clone repo, run uv sync (minimal bootstrap - everyone does this)
2. Choose path: Marimo OR README
3. Complete Steps 1-6 in chosen format

Marimo Path:
Browser (marimo edit marimo-guide.py)
    ├─ Tab: Step 1 (Project Setup)
    ├─ Tab: Step 2A (Basic Agent)
    ├─ Tab: Step 2B (Tools & MCP)
    ├─ Tab: Step 3 (Iterate)
    ├─ Tab: Step 4 (Evaluation)
    ├─ Tab: Step 5 (Production Deploy)
    └─ Tab: Step 6 (Guardrails & Monitors)

Terminal (user's system terminal - runs alongside)
    ├─ tyler chat (interactive CLI)
    ├─ modal serve (long-running dev server)
    └─ Any debugging/exploration commands
```

### Component Responsibilities

**Marimo Notebook**:
- ✅ Provide navigation structure (tabs, progress tracking)
- ✅ Validate prerequisites (env vars, files, dependencies)
- ✅ Automate file operations (cp, mkdir, config saves)
- ✅ Offer copy-to-clipboard for terminal commands
- ✅ Display contextual instructions and hints
- ✅ Generate Weave UI deep links
- ✅ Parse command output (extract URLs, statuses)
- ✅ Provide inline editors for configs
- ❌ NOT responsible for running interactive commands
- ❌ NOT responsible for trace visualization

**User's Terminal**:
- Run interactive commands (tyler chat)
- Run long-running commands (modal serve)
- View live logs and output
- Debug issues as needed

**Weave UI** (browser tabs):
- Playground for testing agent
- Traces for analysis
- Evals for result exploration
- Monitors for production tracking

### Interfaces & Data Contracts

#### Marimo Cell Structure

```python
# Each step is a function returning UI elements
def step_1_project_setup():
    """Step 1: Project Setup tab content."""
    
    # Environment validation
    env_status = check_environment()
    display_env_status(env_status)
    
    # .env configuration helper
    env_editor = create_env_editor()
    save_button = create_save_button()
    
    # Workspace setup
    setup_workspace_button = create_button(
        label="🏗️ Set Up Workspace",
        action=lambda: setup_workspace_directory()
    )
    
    # Progress indicator
    if all_checks_pass():
        show_success("✅ Ready for Step 2!")
        show_continue_button(target_step=2)
    
    return mo.vstack([
        env_status,
        env_editor,
        save_button,
        setup_workspace_button,
        # ... more UI elements
    ])
```

#### File Operations API

```python
def copy_files(source: str, dest: str, confirm: bool = True) -> dict:
    """
    Copy files with validation and user feedback.
    
    Args:
        source: Source path pattern (e.g., "examples/step-2/*.py")
        dest: Destination directory (e.g., "workspace/")
        confirm: Prompt if files will be overwritten
        
    Returns:
        {
            "success": bool,
            "files_copied": list[str],
            "error": str | None
        }
    """
    pass

def save_config(content: str, path: str) -> dict:
    """
    Save config file with YAML validation.
    
    Args:
        content: YAML content to save
        path: File path relative to workspace
        
    Returns:
        {
            "success": bool,
            "error": str | None,
            "validation_errors": list[str]
        }
    """
    pass
```

#### Weave URL Generation API

```python
def generate_weave_url(
    entity: str,
    project: str,
    view: Literal["playground", "traces", "evals", "monitors"],
    filters: dict[str, str] | None = None
) -> str:
    """
    Generate deep link to Weave UI.
    
    Args:
        entity: W&B entity (from WANDB_PROJECT)
        project: W&B project name
        view: Which Weave view to open
        filters: Optional filters (e.g., {"operation": "Agent.stream"})
        
    Returns:
        Full URL to Weave view
        
    Example:
        >>> generate_weave_url("myteam", "demo", "traces", {"operation": "Agent.stream"})
        "https://wandb.ai/myteam/demo/traces?filter=operation%3DAgent.stream"
    """
    pass
```

### Error Handling

**Environment Validation Errors**:
```python
# Missing WANDB_API_KEY
if not os.getenv("WANDB_API_KEY"):
    show_warning("""
    ⚠️ Missing WANDB_API_KEY
    
    1. Get your key: https://wandb.ai/authorize
    2. Add to .env file:
       WANDB_API_KEY=your_key_here
    3. Restart Marimo: Ctrl+C, then `marimo edit marimo-guide.py`
    """)
    disable_action_buttons()
```

**File Operation Errors**:
```python
# File copy fails
try:
    result = copy_files(source, dest)
except PermissionError:
    show_error("""
    ❌ Permission denied
    
    Check file permissions:
    ```bash
    ls -la workspace/
    chmod +w workspace/
    ```
    """)
    show_retry_button()
```

**Command Execution Errors**:
```python
# User reports command failed in terminal
show_troubleshooting("""
If `modal serve` fails:
1. Check Modal authentication: `modal token list`
2. Verify secrets: `modal secret list`
3. Check logs: `modal app logs`
4. See README troubleshooting section
""")
```

### Performance Expectations

**Notebook Loading**:
- Initial load: <2 seconds
- Tab switching: <100ms
- File operations: <500ms

**Button Actions**:
- File copy: <1 second
- Config save: <200ms
- URL generation: <100ms

**No Performance Impact On**:
- Modal deployments (user's terminal)
- Evaluation runs (user's terminal)
- Weave API calls (separate browser tabs)

## 5. Alternatives Considered

### Alternative A: Enhanced README with Collapsible Sections

**Approach**: Keep markdown README, add HTML details/summary tags for collapsibility

**Pros**:
- No new dependencies
- Works in all markdown renderers
- Simpler to maintain

**Cons**:
- No interactivity (buttons, validation)
- No progress tracking
- Still requires manual command execution
- Can't do inline editing

**Why Not Chosen**: Doesn't solve core problems (manual execution, error-prone commands, no validation)

### Alternative B: Web Application (React/Next.js)

**Approach**: Build full web app with backend API for command execution

**Pros**:
- Full control over UI/UX
- Could run commands server-side
- Professional polish
- Mobile-friendly

**Cons**:
- Massive scope (weeks vs days)
- Requires hosting infrastructure
- Security concerns (executing user commands)
- Overkill for tutorial use case
- Harder to maintain

**Why Not Chosen**: Scope too large, infrastructure burden too high for tutorial tool

### Alternative C: Jupyter Notebook

**Approach**: Use Jupyter instead of Marimo

**Pros**:
- More familiar to ML audience
- Mature ecosystem
- Rich widget library

**Cons**:
- Cell execution order matters (hidden state)
- .ipynb JSON format (bad for git)
- Requires notebook server setup
- Manual cell re-running needed
- No reactive updates

**Why Marimo is Better**:
- Pure Python (.py file, git-friendly)
- Reactive (changes propagate automatically)
- No hidden state (cell order doesn't matter)
- Modern UI out of the box
- Simpler deployment (`marimo edit file.py`)

### Alternative D: VS Code Extension

**Approach**: Build VS Code extension with guided tutorial

**Pros**:
- Integrated with IDE
- Can control terminal directly
- Rich UI capabilities

**Cons**:
- Only works in VS Code (not universal)
- Extension development complexity
- Publishing/distribution overhead
- Users might not use VS Code

**Why Not Chosen**: Too specific to one IDE, Marimo works universally

### Alternative E: CLI Wizard (questionary/typer)

**Approach**: Interactive CLI wizard in terminal

**Pros**:
- Terminal-native
- No browser needed
- Simple implementation

**Cons**:
- Limited UI (text-only)
- Hard to show visual progress
- Can't open browser links automatically
- Difficult to provide rich instructions

**Why Not Chosen**: Terminal-only UX is limiting, browser-based is richer

## Why Marimo (Chosen Option)

✅ **Pure Python** - Git-friendly, code review works
✅ **Reactive** - Changes propagate automatically
✅ **Modern UI** - Professional widgets out of the box
✅ **Simple** - Just `marimo edit file.py`
✅ **No hidden state** - Cell order doesn't matter
✅ **Browser-based** - Can open Weave UI links
✅ **Lightweight** - 5MB package, no infrastructure needed

**Tradeoff Accepted**: Users still need terminal for interactive commands (tyler chat, modal serve), but Marimo provides significant value through structure, validation, and automation of non-interactive tasks.

## 6. Data Model & Contract Changes

### Tables/Collections

**No database changes** - Tutorial tool doesn't use databases

### README Structure Changes

**Before**:
```markdown
# Building an Agentic Chatbot with Weave

## Goal
...

## Prerequisites
...

## Step 1: Project Setup
...
[1000 lines continue]
```

**After**:
```markdown
# Building an Agentic Chatbot with Weave

## Goal
...

## Getting Started

### Prerequisites
- Python 3.12+
- Git
- Terminal access

### Installation

1. Clone the repository
```bash
git clone https://github.com/wandb/agentic-support-bot-demo.git
cd agentic-support-bot-demo
```

2. Install dependencies
```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies (includes Marimo)
uv sync
```

### Choose Your Path

**Option A: Interactive Guide (Marimo)** 🎮 ← Recommended

Guided experience with one-click actions and progress tracking.

```bash
marimo edit marimo-guide.py
```

The guide will open in your browser and walk you through everything!

**Option B: Traditional Guide (README)** 📖

Classic markdown tutorial, continue reading below.

---

## Step 1: Project Setup
...
[existing content continues]
```

**Impact**:
- ~80 lines added at top (Getting Started + choice point)
- No changes to existing Step 1-6 content
- Both paths remain complete and functional

### API/Event Changes

**No API changes** - Local tool, no external APIs

### Backward Compatibility

✅ **Fully backward compatible**:
- Existing README still works as-is
- Users who don't want Marimo can ignore it
- No breaking changes to tutorial content
- Git history preserved

### Deprecation Plan

**No deprecations** - Both formats coexist indefinitely

## 7. Security, Privacy, Compliance

### AuthN/AuthZ Model

**No authentication required**:
- Marimo runs locally on user's machine
- No server component
- No user accounts or sessions

**Access control**:
- User controls their own machine
- File operations limited to repo directory
- No network access except opening browser URLs

### Secrets Management

**Environment variables** (.env file):
- `WANDB_API_KEY` - User enters in .env file
- `OPENAI_API_KEY` - User enters in .env file
- `AGENTIC_SUPPORT_BOT_API_KEY` - User enters in .env file

**Marimo behavior**:
- Reads env vars via `os.getenv()`
- Validates presence (not values)
- Never displays secret values in UI
- Never transmits secrets anywhere

**Security measures**:
- `.env` already in `.gitignore`
- Add `.marimo/` to `.gitignore` (stores notebook state)
- Warn users not to commit notebooks with secrets in cells
- Don't log secret values to console

### PII Handling

**No PII collected**:
- Marimo runs locally, no telemetry
- No usage tracking
- No data sent to external services
- All operations local to user's machine

**User data** (local only):
- Config files (YAML)
- Dataset (tutorial examples)
- Workspace files (generated during tutorial)
- All stored locally, never transmitted

### Threat Model & Mitigations

**Threat: Malicious Code Execution**
- **Attack**: User downloads modified marimo-guide.py with malicious code
- **Mitigation**: File in version-controlled repo, code review applies
- **Residual Risk**: Low - user must explicitly run file

**Threat: Secrets in Version Control**
- **Attack**: User commits notebook with secrets visible in cells
- **Mitigation**: Document warning, add `.marimo/` to `.gitignore`
- **Residual Risk**: Medium - user education required

**Threat: Subprocess Command Injection**
- **Attack**: User modifies notebook to execute arbitrary commands
- **Mitigation**: Use parameterized subprocess calls, not shell=True
- **Residual Risk**: Low - user has full control anyway (their machine)

**Threat: Browser URL Injection**
- **Attack**: Manipulate Weave URL generation to open malicious site
- **Mitigation**: URL validation, whitelist wandb.ai domain
- **Residual Risk**: Very Low - URLs are generated, not user-input

## 8. Observability & Operations

### Logs

**Not applicable** - Local tool, no production logs needed

**Optional debugging**:
- Users can add `print()` statements for troubleshooting
- Marimo shows cell outputs for debugging
- Terminal shows command outputs

### Metrics

**No automated metrics collection**

**Manual feedback collection** (optional):
- Add feedback link in notebook final step
- GitHub Discussions for questions
- Survey link for completion feedback

**Metrics of interest** (collect manually):
- % users choosing Marimo vs README
- Completion rates (Marimo vs README)
- Time to complete (self-reported)
- Error rates per step (GitHub issues)

### Alerts

**Not applicable** - Local tool, no operational alerts

### Dashboards

**Not applicable** - Local tool, no dashboards

### User Feedback Collection

**Recommended additions**:
```python
# At end of notebook
mo.md("""
## 🎉 Congratulations!

You've completed the tutorial! 

**Share your feedback:**
- How was your experience? [Quick Survey](https://forms.gle/...)
- Questions? [GitHub Discussions](https://github.com/wandb/agentic-support-bot-demo/discussions)
- Found a bug? [Open an Issue](https://github.com/wandb/agentic-support-bot-demo/issues/new)
""")
```

## 9. Rollout & Migration

### Feature Flags

**No feature flags** - Simple presence/absence of Marimo guide

**Rollout strategy**:
1. Add `marimo` to pyproject.toml
2. Add `marimo-guide.py` to repo
3. Update README with Getting Started + choice point
4. Deploy to main branch
5. Users get both options on next `git pull`

### Rollout Phases

**Phase 1: Internal Testing** (1 week)
- W&B team members test Marimo guide
- Collect feedback on flow, bugs, unclear instructions
- Iterate on content and UX

**Phase 2: Soft Launch** (1 week)
- Deploy to repo without major announcement
- Let organic users discover it
- Monitor GitHub issues for problems
- A/B test: track which option users choose (if telemetry added)

**Phase 3: Public Launch**
- Announce in W&B Slack, social media
- Update wandb.ai/weave docs to mention Marimo option
- Collect feedback at scale
- Iterate based on usage patterns

**Phase 4: Continuous Improvement**
- Monitor GitHub Discussions for common questions
- Update both README and Marimo based on feedback
- Add more automation as patterns emerge
- Consider video walkthrough using Marimo

### Migration

**For existing users** (mid-tutorial):
- Already following README? → No migration needed, continue as-is
- Want to try Marimo? → Run `uv sync`, then `marimo edit marimo-guide.py`
- Marimo detects existing workspace files, skips completed steps

**For new users**:
- See choice immediately after minimal setup
- Clear recommendation (Marimo preferred)
- Can switch between paths at any time

### Revert Plan

**If Marimo causes problems**:

**Option 1: Remove mention from README** (< 5 minutes)
```bash
git revert <commit-with-marimo-reference>
git push
# Users see only README, marimo-guide.py stays but undiscovered
```

**Option 2: Remove Marimo entirely** (< 10 minutes)
```bash
rm marimo-guide.py
# Edit pyproject.toml, remove marimo dependency
# Revert README changes
git commit -m "Remove Marimo guide"
git push
```

**Option 3: Mark as experimental**
```markdown
### Option A: Interactive Guide (Marimo) 🧪 Experimental

⚠️ This is an experimental feature. If you encounter issues, use Option B (README) below.
```

**Blast Radius**:
- Very Low - Marimo is additive, removing doesn't break anything
- README remains functional throughout
- Users mid-tutorial unaffected (continue with README)

## 10. Test Strategy & Spec Coverage (TDD)

### TDD Approach

**Challenge**: Marimo notebook is interactive UI, not API
**Solution**: Manual validation against spec acceptance criteria

**Testing philosophy**:
- Unit test helper functions (file operations, URL generation)
- Manual test UI flows (button clicks, tab navigation)
- Regression test: fresh user completes full tutorial

### Spec→Test Mapping

| Spec Acceptance Criterion | Validation Method | Tester |
|---------------------------|-------------------|--------|
| **Environment Setup** | | |
| Notebook detects missing .env | Manual test: remove .env, launch notebook | Dev |
| Warning shown with setup instructions | Visual inspection of warning callout | Dev |
| Python < 3.12 shows error | Manual test on Python 3.11 env | Dev |
| **File Operations** | | |
| Copy files button works | Unit test + manual verification | Dev + User |
| Overwrite confirmation shown | Manual test: click twice | Dev |
| Permission error handled gracefully | Manual test: chmod 444 workspace/ | Dev |
| **Server Deployment** | | |
| Button disabled without prerequisites | Manual test: uncheck prereq boxes | Dev |
| Modal URL extracted correctly | Unit test on sample output | Dev |
| Running server warning shown | Manual test: click deploy twice | Dev |
| **Weave UI Integration** | | |
| Playground link opens correct URL | Manual test: click button | Dev + User |
| Traces filtered to Agent.stream | Manual test: verify filter applied | Dev |
| Eval results link works | Manual test after running eval | User |
| **Evaluation Workflow** | | |
| Sample slider works (5 cases) | Manual test: run eval | Dev |
| Progress shown during eval | Manual test: watch UI | Dev |
| Results link after completion | Manual test: verify appears | Dev |
| **Config Editing** | | |
| YAML editor has syntax highlighting | Visual inspection | Dev |
| Save button writes to file | Unit test + file check | Dev |
| YAML validation catches errors | Unit test with malformed YAML | Dev |
| **Progress Tracking** | | |
| Step completion marked with ✓ | Manual test: complete step | Dev + User |
| Prerequisites check before step | Manual test: skip to Step 4 | Dev |
| State preserved across tabs | Manual test: switch tabs | Dev |
| **Negative Cases** | | |
| Network error during deploy | Mock test: simulate failure | Dev |
| Malformed YAML doesn't save | Unit test | Dev |
| Missing workspace directory handled | Manual test: rm -rf workspace/ | Dev |

### Test Tiers

#### Unit Tests (`tests/test_marimo_helpers.py`)

```python
"""Unit tests for Marimo notebook helper functions."""

import pytest
from pathlib import Path
from marimo_guide_helpers import (
    copy_files,
    save_config,
    generate_weave_url,
    parse_modal_output,
    validate_yaml,
)

class TestFileOperations:
    """Test file operation helpers."""
    
    def test_copy_files_success(self, tmp_path):
        """GIVEN source files exist WHEN copy_files called THEN files copied"""
        source = tmp_path / "source"
        source.mkdir()
        (source / "test.py").write_text("# test")
        
        dest = tmp_path / "dest"
        dest.mkdir()
        
        result = copy_files(str(source / "*.py"), str(dest))
        
        assert result["success"] is True
        assert len(result["files_copied"]) == 1
        assert (dest / "test.py").exists()
    
    def test_copy_files_permission_error(self, tmp_path):
        """GIVEN dest not writable WHEN copy_files called THEN error returned"""
        source = tmp_path / "source"
        source.mkdir()
        (source / "test.py").write_text("# test")
        
        dest = tmp_path / "dest"
        dest.mkdir()
        dest.chmod(0o444)  # Read-only
        
        result = copy_files(str(source / "*.py"), str(dest))
        
        assert result["success"] is False
        assert "permission" in result["error"].lower()

class TestConfigOperations:
    """Test config save/load helpers."""
    
    def test_save_valid_yaml(self, tmp_path):
        """GIVEN valid YAML WHEN save_config called THEN file written"""
        content = "name: test\nvalue: 123"
        path = tmp_path / "config.yaml"
        
        result = save_config(content, str(path))
        
        assert result["success"] is True
        assert path.exists()
        assert yaml.safe_load(path.read_text())["name"] == "test"
    
    def test_save_invalid_yaml(self, tmp_path):
        """GIVEN malformed YAML WHEN save_config called THEN validation error"""
        content = "name: test\n  invalid: : indent"
        path = tmp_path / "config.yaml"
        
        result = save_config(content, str(path))
        
        assert result["success"] is False
        assert len(result["validation_errors"]) > 0

class TestURLGeneration:
    """Test Weave URL generation."""
    
    def test_generate_playground_url(self):
        """GIVEN entity/project WHEN generate_weave_url THEN correct URL"""
        url = generate_weave_url("myteam", "demo", "playground")
        
        assert url == "https://wandb.ai/myteam/demo/playground"
    
    def test_generate_traces_url_with_filter(self):
        """GIVEN filters WHEN generate_weave_url THEN URL with query params"""
        url = generate_weave_url(
            "myteam", "demo", "traces",
            filters={"operation": "Agent.stream"}
        )
        
        assert "wandb.ai/myteam/demo/traces" in url
        assert "operation=Agent.stream" in url

class TestModalOutputParsing:
    """Test parsing Modal command output."""
    
    def test_extract_modal_url(self):
        """GIVEN modal serve output WHEN parse THEN URL extracted"""
        output = """
        ✓ Created objects.
        └── 🔨 Created web function => https://user--app-dev.modal.run
        ✓ App deployed in 3.14s
        """
        
        url = parse_modal_output(output)
        
        assert url == "https://user--app-dev.modal.run"
    
    def test_extract_modal_url_not_found(self):
        """GIVEN output without URL WHEN parse THEN None returned"""
        output = "Some random output without URL"
        
        url = parse_modal_output(output)
        
        assert url is None
```

#### Integration Tests (Manual)

**Test Plan**: Fresh User Walkthrough
1. Clone repo
2. Run `uv sync`
3. Run `marimo edit marimo-guide.py`
4. Complete Steps 1-6 following only Marimo guide
5. Verify all outcomes match README expectations
6. Document any confusion or errors

**Success criteria**:
- ✅ User completes without consulting README
- ✅ All files created correctly
- ✅ Agent works in Playground
- ✅ Evaluations run successfully
- ✅ Production deployment works

#### E2E Tests (User Acceptance)

**Beta Tester Checklist**:
- [ ] Can choose between Marimo and README easily
- [ ] Marimo launches successfully
- [ ] All tabs load without errors
- [ ] File copy buttons work
- [ ] Config editing and saving works
- [ ] Weave links open correct pages
- [ ] Progress indicators accurate
- [ ] Completion time < README time
- [ ] Would recommend Marimo over README

### Negative & Edge Cases

| Test Case | Expected Behavior | Priority |
|-----------|-------------------|----------|
| Marimo not installed | Error with install instructions | High |
| Browser doesn't support Marimo UI | Fallback message to use README | Medium |
| User closes browser mid-step | Can reopen and continue | High |
| Network down during Weave link click | Link opens but page loads error (graceful) | Low |
| Multiple Marimo instances | Each works independently | Medium |
| WANDB_PROJECT env var wrong format | Validation error with fix guidance | High |
| Modal authentication expired | Command fails, user sees clear error | Medium |
| File already exists (overwrite) | Confirmation dialog shown | High |
| Disk full during file copy | Error message with disk space check | Low |

### Performance Tests

**Notebook Loading Performance**:
```python
def test_notebook_loads_quickly():
    """GIVEN marimo-guide.py WHEN user runs marimo edit THEN loads < 3 seconds"""
    import time
    start = time.time()
    
    # Simulate notebook load (import all dependencies)
    import marimo_guide
    
    load_time = time.time() - start
    assert load_time < 3.0, f"Notebook loaded in {load_time}s, target <3s"
```

**File Operation Performance**:
```python
def test_file_copy_performance(tmp_path):
    """GIVEN typical file set WHEN copy_files called THEN completes < 1 second"""
    # Create 10 files (~5KB each, typical for step files)
    source = tmp_path / "source"
    source.mkdir()
    for i in range(10):
        (source / f"file{i}.py").write_text("# " + "x" * 5000)
    
    dest = tmp_path / "dest"
    dest.mkdir()
    
    start = time.time()
    copy_files(str(source / "*.py"), str(dest))
    duration = time.time() - start
    
    assert duration < 1.0, f"Copy took {duration}s, target <1s"
```

### CI Requirements

**What's testable in CI**:
✅ Unit tests for helper functions
✅ YAML validation logic
✅ URL generation logic
✅ File operation logic
✅ Linting (black, ruff)

**What's NOT testable in CI** (manual validation):
❌ UI interactions (button clicks)
❌ Browser behavior (links opening)
❌ Full user flow (requires human)
❌ Marimo UI rendering

**CI Configuration**:
```yaml
name: Test Marimo Guide Helpers

on: [pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv sync
      - name: Run helper tests
        run: uv run pytest tests/test_marimo_helpers.py -v
      - name: Lint marimo-guide.py
        run: |
          uv run ruff check marimo-guide.py
          uv run black --check marimo-guide.py
```

## 11. Risks & Open Questions

### Known Risks & Mitigations

| Risk | Severity | Mitigation | Status |
|------|----------|------------|--------|
| Users still need terminal (not "one window") | Medium | Set expectations clearly in spec; Marimo still valuable for structure/validation | Accepted |
| Marimo and README get out of sync | Medium | Maintenance checklist; prioritize learning objectives over verbatim match | Accepted |
| Marimo unfamiliar to users | Low | Minimal Marimo knowledge needed; README always available | Mitigated |
| Browser requirement excludes SSH users | Low | README works for headless environments | Mitigated |
| File operations could fail (permissions) | Low | Comprehensive error handling with troubleshooting tips | Mitigated |
| Secrets accidentally committed in .marimo/ | Medium | Add to .gitignore; document warning | Mitigated |

### Open Questions & Resolution Paths

All open questions from Impact Analysis have been resolved through discussion:

**Q1: Pin marimo version or allow latest?**
- ✅ **RESOLVED** - Pin to `marimo>=0.6.0,<0.7.0`
- **Rationale**: Marimo actively developed, pin to known-good version for stability

**Q2: How to manage background processes (modal serve)?**
- ✅ **RESOLVED** - User runs in terminal, Marimo provides command + instructions
- **Rationale**: Simpler, more transparent, users see logs directly

**Q3: Persist notebook state across sessions?**
- ✅ **RESOLVED** - Don't persist execution state, but show progress indicators
- **Rationale**: Fresh start each time avoids confusion, progress indicators sufficient

**Q4: How to keep README ↔ Marimo in sync?**
- ✅ **RESOLVED** - Manual sync with checklist
- **Rationale**: Automated sync too complex; manual sync with discipline is practical

**Q5: Modal serve in notebook or terminal?**
- ✅ **RESOLVED** - Terminal (user runs, Marimo provides copy button)
- **Rationale**: Terminal gives better logs, easier to stop, more transparent

## 12. Milestones / Plan (post‑approval)

### Milestone 1: Project Structure & Dependencies (2-3 hours)

**Task 1.1: Add Marimo Dependency** (30 min)
- [ ] Update `pyproject.toml` with `marimo = ">=0.6.0,<0.7.0"`
- [ ] Run `uv sync` to test installation
- [ ] Verify Marimo launches: `marimo --version`
- **DoD**: Marimo installed and working

**Task 1.2: Create Basic Notebook Structure** (1 hour)
- [ ] Create `marimo-guide.py` with imports
- [ ] Set up tab structure for Steps 1-6
- [ ] Add placeholder content for each tab
- [ ] Test launches: `marimo edit marimo-guide.py`
- **DoD**: Empty notebook with 6 tabs loads successfully

**Task 1.3: Create Helper Functions Module** (1 hour)
- [ ] Create `marimo_guide_helpers.py` (or inline in notebook)
- [ ] Implement `copy_files()` function
- [ ] Implement `save_config()` function
- [ ] Implement `generate_weave_url()` function
- [ ] Implement `parse_modal_output()` function
- **DoD**: Helper functions defined (not tested yet)

**Task 1.4: Set Up Tests** (30 min)
- [ ] Create `tests/test_marimo_helpers.py`
- [ ] Write test stubs for all helper functions
- [ ] Verify tests run: `pytest tests/test_marimo_helpers.py`
- **DoD**: Test file created, tests fail (no implementation)

### Milestone 2: Implement Steps 1-3 (5-6 hours)

**Task 2.1: Step 1 - Project Setup** (1.5 hours)
- [ ] Environment variable detection
- [ ] .env file configuration helper
- [ ] Workspace directory setup button
- [ ] Prerequisite validation UI
- [ ] Progress indicator
- **DoD**: Step 1 fully functional, manual test passes

**Task 2.2: Step 2A - Basic Agent** (1 hour)
- [ ] File copy button (examples/step-2/part-a)
- [ ] Tyler chat command with copy button
- [ ] Test prompt suggestions
- [ ] Link to view traces in Weave
- **DoD**: Step 2A functional, user can reach first traces

**Task 2.3: Step 2B - Tools & MCP** (1.5 hours)
- [ ] File copy button (examples/step-2/part-b)
- [ ] Modal setup checklist (3 checkboxes)
- [ ] Deploy button (copies command for terminal)
- [ ] Modal URL input field
- [ ] Playground link generator
- [ ] Provider setup instructions
- **DoD**: Step 2B functional, user can deploy and test in Playground

**Task 2.4: Step 3 - Iterate** (1.5 hours)
- [ ] Current config display
- [ ] Inline YAML editor for tyler-chat-config.yaml
- [ ] Purpose field editor with character count
- [ ] Save config button
- [ ] Link to Playground for testing
- [ ] Link to Traces for verification
- [ ] Before/after comparison guidance
- **DoD**: Step 3 functional, user can edit config and see results

### Milestone 3: Implement Steps 4-6 (5-6 hours)

**Task 3.1: Step 4 - Evaluation** (2 hours)
- [ ] Copy all Step 4 files button
- [ ] Publish dataset button
- [ ] Dataset link after publish
- [ ] Sample size slider (1-31)
- [ ] Run evaluation button
- [ ] Progress indicator during eval
- [ ] Results link to Weave Evals
- [ ] Config editor for iteration
- **DoD**: Step 4 functional, user can run evals and iterate

**Task 3.2: Step 5 - Production Deploy** (1 hour)
- [ ] Production deploy button (copies command)
- [ ] Production URL input field
- [ ] Playground provider setup (production)
- [ ] Saved View creation instructions
- [ ] Link to production traces
- **DoD**: Step 5 functional, user can deploy to production

**Task 3.3: Step 6 - Guardrails & Monitors** (2 hours)
- [ ] Copy guardrails files button
- [ ] Guardrails explanation
- [ ] Deploy with guardrails button
- [ ] Test prompts for adversarial testing
- [ ] Monitor creation step-by-step guide
- [ ] Links to Weave Monitors tab
- [ ] Comparison table (guardrails vs monitors)
- **DoD**: Step 6 functional, user can add guardrails and monitors

### Milestone 4: README Integration & Documentation (3-4 hours)

**Task 4.1: Update README** (1.5 hours)
- [ ] Add "Getting Started" section
- [ ] Add minimal bootstrap (clone, uv sync)
- [ ] Add "Choose Your Path" decision point
- [ ] Mark Marimo as recommended
- [ ] Add Marimo launch instructions
- [ ] Add `.marimo/` to `.gitignore`
- **DoD**: README has clear choice point, both paths documented

**Task 4.2: Add Inline Documentation** (1 hour)
- [ ] Learning objectives for each step
- [ ] Expandable hints/tips (mo.accordion)
- [ ] Links to Weave docs
- [ ] Troubleshooting sections
- [ ] Quick command reference
- **DoD**: Notebook is self-documenting

**Task 4.3: Add Completion Feedback** (30 min)
- [ ] Congratulations message
- [ ] Feedback survey link
- [ ] GitHub Discussions link
- [ ] Issue reporting link
- **DoD**: Users can provide feedback easily

**Task 4.4: Create Maintenance Checklist** (30 min)
- [ ] Document sync process (README ↔ Marimo)
- [ ] List items to check when updating
- [ ] Add to PR template
- **DoD**: Maintainers know how to keep both in sync

### Milestone 5: Testing & Polish (4-5 hours)

**Task 5.1: Write & Run Unit Tests** (2 hours)
- [ ] Implement all test cases in `test_marimo_helpers.py`
- [ ] Verify all tests pass
- [ ] Add edge case tests
- [ ] Run coverage: `pytest --cov`
- [ ] Target: 80%+ coverage for helpers
- **DoD**: All unit tests passing, coverage target met

**Task 5.2: Manual Testing - Fresh User Flow** (1.5 hours)
- [ ] Reset workspace (rm -rf workspace/)
- [ ] Unset all env vars
- [ ] Launch Marimo guide
- [ ] Complete Steps 1-6 following only Marimo
- [ ] Document any issues or confusion
- **DoD**: Fresh user flow validated, issues documented

**Task 5.3: Cross-Platform Testing** (1 hour)
- [ ] Test on macOS (primary development)
- [ ] Test on Linux (common in Docker)
- [ ] Test on Windows (WSL or native)
- [ ] Fix any platform-specific path issues
- **DoD**: Works on all three platforms

**Task 5.4: Polish & Refinement** (30 min)
- [ ] Fix any UX issues from testing
- [ ] Improve button labels/icons
- [ ] Enhance error messages
- [ ] Check all links work
- [ ] Proofread all instructions
- **DoD**: Polished, professional experience

### Milestone 6: Launch Preparation (2-3 hours)

**Task 6.1: Internal Review** (1 hour)
- [ ] W&B team members test Marimo guide
- [ ] Collect feedback
- [ ] Prioritize issues
- [ ] Fix critical issues
- **DoD**: Internal team approves for launch

**Task 6.2: Beta Testing** (1 hour)
- [ ] Recruit 2-3 external testers
- [ ] Provide beta access (feature branch)
- [ ] Collect detailed feedback
- [ ] Iterate based on feedback
- **DoD**: Beta testers complete tutorial successfully

**Task 6.3: Final QA** (30 min)
- [ ] Run all tests one final time
- [ ] Verify linting passes
- [ ] Check git status (no untracked secrets)
- [ ] Verify `.gitignore` up to date
- **DoD**: Ready for merge to main

**Task 6.4: Launch** (30 min)
- [ ] Merge PR to main
- [ ] Update wandb.ai/weave docs (if applicable)
- [ ] Announce in Slack/social media
- [ ] Monitor GitHub issues for feedback
- **DoD**: Marimo guide live and announced

### Dependencies

**Cross-Milestone Dependencies**:
- M2 depends on M1 (need notebook structure before implementing steps)
- M3 depends on M2 (Steps 4-6 reference Steps 1-3)
- M4 depends on M3 (README integration needs full notebook)
- M5 depends on M4 (testing needs complete implementation)
- M6 depends on M5 (launch needs passing tests)

**External Dependencies**:
- Marimo package availability (stable, no risk)
- Weave UI URLs (stable, documented)
- Modal CLI (already dependency)
- Existing tutorial structure (no changes expected)

### Timeline

**Total estimated time**: 21-27 hours
**Recommended schedule**: 1 week (3-4 days of focused work)

**Day 1**: M1 + M2 (project setup + Steps 1-3)
**Day 2**: M3 (Steps 4-6)
**Day 3**: M4 + M5 (README integration + testing)
**Day 4**: M6 (internal review + beta + launch)

**Critical path**: M1 → M2 → M3 → M4 → M5 → M6 (fully sequential)

### Success Metrics (Post-Launch)

**Immediate (Week 1)**:
- [ ] 50+ users try Marimo guide
- [ ] < 5 critical bugs reported
- [ ] Positive feedback in GitHub Discussions

**Short-term (Month 1)**:
- [ ] 50% of new users choose Marimo over README
- [ ] < 10% user drop-off rate
- [ ] Median completion time < README baseline

**Long-term (Quarter 1)**:
- [ ] 70%+ users prefer Marimo (survey data)
- [ ] Marimo completion rate > README completion rate
- [ ] Maintained with < 1 hour/week effort

---

**Approval Gate**: Do not start coding until this TDR is reviewed and approved in the PR.

