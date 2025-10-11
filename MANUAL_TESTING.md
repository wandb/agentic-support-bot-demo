# Manual Testing Checklist for Tyler Chat CLI

This checklist covers manual validation steps that should be performed to verify the tyler chat CLI integration works correctly.

## Pre-requisites

- [ ] Environment variables set in `.env`:
  - `WANDB_API_KEY` (required)
  - `OPENAI_API_KEY` (required for gpt-4.1 model)
- [ ] All automated tests pass: `uv run pytest tests/ -v`
- [ ] Dependencies installed: `uv sync`

## Test 1: Basic CLI Startup

**Steps:**
1. Run `uv run tyler chat --config support-bot.yaml`
2. Verify the CLI starts successfully
3. Check that no error messages appear
4. Verify agent introduction/greeting (if any)

**Expected Results:**
- ✅ CLI launches without errors
- ✅ Interactive prompt appears
- ✅ Agent is ready to receive input

**Status:** ⬜ Not tested | ✅ Pass | ❌ Fail

---

## Test 2: Create Issue Tool Usage

**Steps:**
1. Start tyler chat CLI
2. Type: "I need to create a new issue for API timeout errors"
3. Observe agent behavior

**Expected Results:**
- ✅ Agent acknowledges the request
- ✅ Tool indicator appears: `[🔧 Using tool: create_issue]` (or similar)
- ✅ Agent reports successful issue creation with a mock issue ID
- ✅ Response includes issue details (title, status, priority)

**Example Prompt Variations:**
- "Create an issue titled 'Login Bug' with description 'Users can't login' and high priority"
- "Please make a new support ticket for slow page loading"

**Status:** ⬜ Not tested | ✅ Pass | ❌ Fail

---

## Test 3: Get Issue Tool Usage

**Steps:**
1. In the same chat session (or new session)
2. Type: "Can you get me the details for issue #123?"
3. Observe agent behavior

**Expected Results:**
- ✅ Agent acknowledges the request
- ✅ Tool indicator appears: `[🔧 Using tool: get_issue]` (or similar)
- ✅ Agent returns mock issue data for issue #123
- ✅ Response includes all issue fields (id, title, description, status, priority, timestamps)

**Example Prompt Variations:**
- "Show me issue ABC-456"
- "What's the status of issue number 789?"

**Status:** ⬜ Not tested | ✅ Pass | ❌ Fail

---

## Test 4: Multi-Turn Conversation Context

**Steps:**
1. Start tyler chat CLI
2. First message: "Create an issue for API timeouts"
3. Second message: "What was the ID of that issue?" (without specifying which issue)
4. Observe if agent remembers context

**Expected Results:**
- ✅ Agent uses create_issue tool for first message
- ✅ Agent responds to second message using context from first message
- ✅ No errors about missing context or unclear requests

**Status:** ⬜ Not tested | ✅ Pass | ❌ Fail

---

## Test 5: Chat Commands

**Steps:**
1. Start tyler chat CLI
2. Test each command:
   - `/help` - should show available commands
   - `/new` - should create new conversation thread
   - `/clear` - should clear the screen
   - `/quit` or `/exit` - should exit gracefully

**Expected Results:**
- ✅ All commands work as documented
- ✅ No errors or crashes

**Status:** ⬜ Not tested | ✅ Pass | ❌ Fail

---

## Test 6: Weave Observability

**Steps:**
1. Run a few interactions with tyler chat CLI
2. Exit the CLI
3. Visit https://wandb.ai/
4. Navigate to project "agentic-support-bot-demo"
5. Check for traces

**Expected Results:**
- ✅ Project exists in W&B Weave
- ✅ Traces appear for each interaction
- ✅ Tool calls are logged
- ✅ Token usage and latency data are captured

**Status:** ⬜ Not tested | ✅ Pass | ❌ Fail

---

## Test 7: Error Handling - Missing Env Var

**Steps:**
1. Temporarily remove `OPENAI_API_KEY` from `.env`
2. Run `uv run tyler chat --config support-bot.yaml`
3. Observe error message

**Expected Results:**
- ✅ Clear error message about missing API key
- ✅ Agent doesn't start with partial configuration
- ✅ Error message is actionable (tells user what to do)

**Restore:** Re-add `OPENAI_API_KEY` after test

**Status:** ⬜ Not tested | ✅ Pass | ❌ Fail

---

## Test 8: Streaming Responses

**Steps:**
1. Start tyler chat CLI
2. Ask a question that generates a longer response
3. Observe how response appears

**Expected Results:**
- ✅ Response streams in real-time (words appear gradually)
- ✅ No "waiting" periods with blank output
- ✅ Tool usage indicators appear at appropriate times

**Status:** ⬜ Not tested | ✅ Pass | ❌ Fail

---

## Test 9: Configuration File Validation

**Steps:**
1. Temporarily break `support-bot.yaml` (e.g., invalid YAML syntax or missing required field)
2. Try to run `uv run tyler chat --config support-bot.yaml`
3. Observe error message

**Expected Results:**
- ✅ Tyler chat detects invalid configuration
- ✅ Error message indicates what's wrong
- ✅ Agent doesn't start with broken config

**Restore:** Fix `support-bot.yaml` after test

**Status:** ⬜ Not tested | ✅ Pass | ❌ Fail

---

## Test 10: Alternative - Programmatic Execution

**Steps:**
1. Run `uv run main.py`
2. Observe demo execution

**Expected Results:**
- ✅ Script runs successfully
- ✅ Agent creates and retrieves issues
- ✅ Streaming output appears
- ✅ No errors or crashes
- ✅ Weave initialization message appears

**Status:** ⬜ Not tested | ✅ Pass | ❌ Fail

---

## Summary

**Total Tests:** 10  
**Passed:** ___  
**Failed:** ___  
**Not Tested:** ___  

**Notes:**
_Add any observations, issues, or suggestions here_

---

## Known Limitations

These are expected behaviors based on the spec (not bugs):

- ✓ Tools return mock data (no real issue system integration)
- ✓ Conversation context is in-session only (no persistence across sessions)
- ✓ Only two tools available (create_issue, get_issue)
- ✓ Weave warning if WANDB_API_KEY missing (but agent continues)

---

**Testing Date:** _______________  
**Tested By:** _______________  
**Version/Commit:** _______________

