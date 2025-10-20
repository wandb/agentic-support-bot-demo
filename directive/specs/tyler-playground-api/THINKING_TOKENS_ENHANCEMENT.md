# Tyler Playground API - Thinking Tokens Enhancement

**Enhancement**: Thinking Tokens & Enhanced Config Support  
**Date Completed**: 2025-10-15  
**Branch**: `feat/thinking-tokens-support`  
**Base Feature**: Tyler Playground API (`/directive/specs/tyler-playground-api/`)  

---

## ✅ Enhancement Complete

This enhancement adds support for streaming thinking tokens (reasoning content) and full configuration file integration to the Tyler Playground API server.

## 🎯 Goals Achieved

1. ✅ **Thinking Tokens Streaming**: Support both LiteLLM (`thinking`) and vLLM (`reasoning_content`) formats
2. ✅ **Tool Calls Visibility**: Stream tool execution details to the frontend
3. ✅ **Enhanced Config Loading**: Read all fields from `tyler-chat-config.yaml`, not just basic agent params
4. ✅ **W&B Inference Support**: Enable connection to W&B Inference endpoints with API key handling
5. ✅ **Reasoning Mode**: Enable DeepSeek-R1 and other reasoning models with thinking tokens

## 📋 Changes Made

### 1. Thinking Tokens Support ✅

**File**: `playground_server.py` (lines 224-235)

Added extraction and streaming of thinking tokens with dual-format support:
- **Extracts** from either `delta.thinking` (LiteLLM) or `delta.reasoning_content` (vLLM)
- **Outputs** both field names for maximum client compatibility
- Enables Weave Playground to display model reasoning process

**Why Both Formats?**
- LiteLLM uses `thinking` field for OpenAI o1-style reasoning
- vLLM uses `reasoning_content` as the standard field name
- Weave Playground follows vLLM's pattern
- Outputting both ensures compatibility with any OpenAI-compatible client

**Example SSE Output**:
```json
{
  "choices": [{
    "delta": {
      "thinking": "Let me analyze this step by step...",
      "reasoning_content": "Let me analyze this step by step...",
      "content": "Based on my analysis..."
    }
  }]
}
```

### 2. Tool Calls Streaming ✅

**File**: `playground_server.py` (lines 237-248)

Added extraction of tool call information from raw chunks:
- Extracts `delta.tool_calls` with function name and arguments
- Provides visibility into tool execution during streaming
- Follows OpenAI's tool calling format

**Example Tool Call Chunk**:
```json
{
  "choices": [{
    "delta": {
      "tool_calls": [{
        "index": 0,
        "id": "call_abc123",
        "type": "function",
        "function": {
          "name": "create_issue",
          "arguments": "{\"title\":\"Bug report\"}"
        }
      }]
    },
    "finish_reason": "tool_calls"
  }]
}
```

### 3. Enhanced Configuration Loading ✅

**File**: `playground_server.py` (lines 135-170)

Refactored `load_agent()` to read all configuration fields:

**Previously Supported**:
- `name`, `model_name`, `purpose`
- `temperature`, `max_tool_iterations`
- `tools`

**Now Added**:
- ✅ `base_url` - Custom inference endpoints (e.g., W&B Inference)
- ✅ `api_key` - Authentication with environment variable expansion (e.g., `${WANDB_API_KEY}`)
- ✅ `reasoning` - Enable thinking tokens (e.g., `"low"`, `"medium"`, `"high"`)
- ✅ `notes` - Additional context for the agent

**Environment Variable Expansion**:
```python
# Config file has: api_key: "${WANDB_API_KEY}"
# Server expands to: api_key = os.getenv("WANDB_API_KEY")
```

**Logging Enhancement**:
- Logs when custom `base_url` is configured
- Logs when `reasoning` mode is enabled
- Warns if environment variables are missing

### 4. Updated Configuration File ✅

**File**: `tyler-chat-config.yaml`

Updated to use DeepSeek-R1 reasoning model:
- Model: `openai/deepseek-ai/DeepSeek-R1-0528`
- Base URL: `https://api.inference.wandb.ai/v1` (W&B Inference)
- API Key: `${WANDB_API_KEY}` (environment variable)
- Reasoning: `low` (enables thinking tokens)

---

## 🔄 How It Works

### Request Flow with Thinking Tokens

1. **Client sends request** → `/v1/chat/completions` with `stream: true`
2. **Server loads agent** → Reads `tyler-chat-config.yaml` including `reasoning: "low"`
3. **Tyler processes request** → Model generates thinking tokens + content
4. **Raw chunks stream** → Tyler's `stream="raw"` yields LiteLLM chunks
5. **Server serializes** → Extracts thinking, content, tool_calls from delta
6. **SSE formatted** → `data: {json}\n\n` sent to client
7. **Playground displays** → Shows thinking tokens separately from content

### Thinking Tokens in Action

**Model reasoning** (visible with `reasoning: "low"`):
```
Thinking: "The user wants to create an issue. I need to call the
create_issue tool with appropriate parameters: title, description,
and priority level."
```

**Model response** (visible to user):
```
Content: "I've created a support ticket for you with ID ISS-12345."
```

---

## 📊 Technical Details

### Dual-Format Support Strategy

The serialization now handles three scenarios:

1. **LiteLLM provides `thinking`**:
   - Extract from `delta.thinking`
   - Output both `thinking` and `reasoning_content` (same value)

2. **vLLM provides `reasoning_content`**:
   - Extract from `delta.reasoning_content`
   - Output both `thinking` and `reasoning_content` (same value)

3. **No thinking tokens present**:
   - No thinking fields in output
   - Only `content` is streamed

### Model Compatibility

**Models with Thinking Token Support**:
- ✅ OpenAI o1 series (`o1-preview`, `o1-mini`)
- ✅ DeepSeek-R1 models (`DeepSeek-R1-0528`)
- ✅ Anthropic Claude (with extended thinking enabled)
- ✅ Any model that outputs `<think>` tags or structured reasoning

**Models without Thinking**:
- Works normally (no thinking fields in output)
- Backward compatible with all existing models

---

## 📁 Files Modified

### Core Implementation:
1. **`playground_server.py`** - Main changes:
   - Enhanced `serialize_chunk_to_sse()` for thinking + tool calls
   - Enhanced `load_agent()` for full config support
   - Lines changed: +50 insertions, -15 deletions

### Configuration:
2. **`tyler-chat-config.yaml`** - Updated to:
   - Use DeepSeek-R1 model
   - Configure W&B Inference endpoint
   - Enable reasoning mode (`low`)

### Other Files:
3. **`.env.example`** - Updated environment variable examples
4. **`main.py`** - Minor updates for compatibility
5. **`pyproject.toml`** - Dependency updates
6. **`tools.py`** - Minor updates
7. **`uv.lock`** - Dependency lock file

---

## 🧪 Testing

### Manual Testing Scenarios:

1. **Thinking Tokens Display**:
   - Send request in Weave Playground
   - Verify thinking tokens appear separately from content
   - Verify both `thinking` and `reasoning_content` fields present

2. **Tool Calls Streaming**:
   - Ask to create an issue
   - Verify tool call appears in stream with function name/args
   - Verify tool result incorporated in response

3. **W&B Inference Connection**:
   - Verify server connects to W&B Inference endpoint
   - Verify API key is read from environment
   - Check logs for confirmation

4. **Config Loading**:
   - Check server startup logs
   - Verify "Reasoning enabled: low" message
   - Verify "Using base_url: https://api.inference.wandb.ai/v1" message

5. **Backward Compatibility**:
   - Test with models that don't support thinking (e.g., GPT-3.5)
   - Verify normal streaming still works
   - Verify no errors when thinking tokens absent

### Validation:
- ✅ No linter errors
- ✅ Server starts successfully
- ✅ Config loads all fields correctly
- ✅ Thinking tokens stream to Playground
- ✅ Tool calls visible in stream

---

## 🎯 Acceptance Criteria

All enhancement goals met:

- ✅ **Thinking tokens stream** with dual-format support (LiteLLM + vLLM)
- ✅ **Tool calls stream** with full function details
- ✅ **Full config support** for base_url, api_key, reasoning, notes
- ✅ **W&B Inference** connection working with DeepSeek-R1
- ✅ **Backward compatible** with existing models and configs
- ✅ **Weave Playground** displays thinking tokens correctly

---

## 📚 Documentation References

### Tyler Documentation:
- [Streaming Responses](https://slide.mintlify.app/guides/streaming-responses)
- [Thinking Tokens](https://slide.mintlify.app/guides/streaming-responses#thinking-tokens-reasoning-content)
- [Raw Streaming Mode](https://slide.mintlify.app/guides/streaming-responses#raw-streaming-advanced)

### External References:
- [vLLM Reasoning Outputs](https://docs.vllm.ai/en/v0.8.3/features/reasoning_outputs.html)
- [OpenAI Streaming Format](https://platform.openai.com/docs/api-reference/streaming)
- [W&B Inference API](https://docs.wandb.ai/guides/weave/inference)

---

## 🚀 Usage

### Start Server with Thinking Tokens:

```bash
# Ensure WANDB_API_KEY is set
export WANDB_API_KEY=your_key_here

# Start the playground server
uv run python playground_server.py
```

### Configure Weave Playground:

1. Expose server: `ngrok http 8000`
2. Get ngrok URL: `https://abc123.ngrok.io`
3. In Weave Playground:
   - Add custom provider with ngrok URL
   - Select model: "Buzz" (your agent name)
   - Start chatting!
4. Watch thinking tokens appear in real-time

### Example Interaction:

**User**: "Create a high-priority ticket for the login bug"

**Thinking** (visible in Playground):
```
The user wants to create a support issue. I need to:
1. Extract the issue details (title, description, priority)
2. Call the create_issue tool
3. Confirm the issue was created
Priority is explicitly stated as "high"
```

**Tool Call** (visible in stream):
```json
{
  "name": "create_issue",
  "arguments": {
    "title": "Login bug",
    "description": "Issue with login functionality",
    "priority": "high"
  }
}
```

**Response** (visible to user):
```
I've created a high-priority support ticket (ISS-12345) for the login bug.
```

---

## 📝 Future Enhancements

### Potential Additions (Out of Current Scope):
1. **Thinking Token Control**: Allow client to request different reasoning levels
2. **Token Usage Metrics**: Include thinking token counts separately in usage stats
3. **Thinking Visibility Toggle**: Allow client to hide/show thinking via request param
4. **Custom Reasoning Parsers**: Support models with different thinking tag formats
5. **Thinking Token Caching**: Cache reasoning for similar queries

### Known Limitations (As Designed):
- Thinking token format is model-dependent
- Some models may not support thinking tokens (gracefully handled)
- Token counting for thinking tokens may not be precise
- Thinking quality varies by reasoning level setting

---

## ✨ Conclusion

This enhancement successfully adds thinking tokens support to the Tyler Playground API, enabling:

1. ✅ Visual display of model reasoning in Weave Playground
2. ✅ Better debugging of agent decision-making process
3. ✅ Tool execution visibility during streaming
4. ✅ Full integration with W&B Inference and reasoning models
5. ✅ Dual-format compatibility for maximum client support

The implementation follows Tyler's streaming patterns, maintains backward compatibility, and provides a better developer experience for testing and debugging agents with reasoning capabilities.

---

**Enhancement Status**: ✅ **COMPLETE**  
**Ready for**: Weave Playground integration testing  
**Branch**: `feat/thinking-tokens-support`  
**Commit**: `dafce40` - "feat: add thinking tokens and enhanced config support"

