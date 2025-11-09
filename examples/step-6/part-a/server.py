"""
Tyler agent server with input guardrails deployed on Modal.

Step 6 Part A: Adds input guardrail to block toxic requests before generation.

Changes from Step 5:

- Imports input guardrail scorer (InputToxicityGuardrail)
- Initializes guardrail outside request handler (performance)
- Applies INPUT guardrail before generation to block toxic requests
- Returns blocked message if guardrail flags content
- Maintains streaming for great UX (output guardrails would break streaming)

Why only INPUT guardrail?
- Blocks toxic requests BEFORE generation (fast, maintains streaming)
- Most common production pattern for streaming apps
- Modern LLMs rarely generate toxic content on their own

Works in two modes:
- Development: `modal serve --env dev workspace/server.py` (ephemeral, auto-reload)
- Production: `modal deploy workspace/server.py` (persistent, stable)

Version: 1.6 - Input guardrail only, streaming restored
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, List, Literal, Optional

import modal
import yaml
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import weave
from tyler import Agent, Thread, Message

# Add /workspace to Python path for imports
sys.path.insert(0, "/workspace")

# Import guardrail (input only - maintains streaming UX)
from guardrails import InputToxicityGuardrail

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ============================================================================
# Modal Configuration
# ============================================================================

# Create Modal app
app = modal.App("agentic-support-bot")

# Create Modal image with dependencies and workspace files
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_pyproject(Path(__file__).parent.parent / "pyproject.toml")
    .add_local_dir(Path(__file__).parent, remote_path="/workspace")
)

# ============================================================================
# Environment Detection
# ============================================================================

def get_environment() -> str:
    """Get the Modal environment name for Weave tagging."""
    return os.getenv("MODAL_ENVIRONMENT", "main")


# ============================================================================
# Pydantic Models
# ============================================================================

class ChatMessage(BaseModel):
    """A single message in a conversation."""
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    """Request format for /v1/chat/completions endpoint."""
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class HealthResponse(BaseModel):
    """Response format for health check endpoint."""
    status: str
    environment: str
    agent_name: Optional[str] = None
    model: Optional[str] = None


# ============================================================================
# Agent Initialization
# ============================================================================

def load_agent(config_path: str = "/workspace/tyler-chat-config.yaml") -> tuple[Agent, dict]:
    """Load Tyler agent from configuration file using Agent.from_config()."""
    # Validate required secrets
    required_secrets = ["WANDB_API_KEY", "AGENTIC_SUPPORT_BOT_API_KEY", "OPENAI_API_KEY"]
    missing_secrets = [s for s in required_secrets if not os.getenv(s)]
    if missing_secrets:
        error_msg = (
            f"\n{'='*70}\n"
            f"❌ Missing required Modal secrets: {', '.join(missing_secrets)}\n\n"
            f"Please create Modal secrets with:\n"
            f"  modal secret create agentic-support-bot-secrets \\\n"
            f"    WANDB_API_KEY=<your-key> \\\n"
            f"    AGENTIC_SUPPORT_BOT_API_KEY=<your-key> \\\n"
            f"    OPENAI_API_KEY=<your-key>\n\n"
            f"Then restart the server.\n"
            f"{'='*70}\n"
        )
        logger.error(error_msg)
        raise ValueError(f"Missing required secrets: {', '.join(missing_secrets)}")
    
    # Detect environment
    env = get_environment()
    logger.info(f"🚀 Environment: {env}")
    
    # Initialize Weave
    try:
        project = os.getenv("WANDB_PROJECT", "agentic-support-bot-demo")
        weave.init(project)
        logger.info(f"📊 Weave initialized: project={project}, env={env}")
    except Exception as e:
        logger.warning(f"Weave initialization failed: {e} (observability degraded)")
    
    # Load agent from config
    try:
        os.chdir("/workspace")
        agent = Agent.from_config(config_path)
        logger.info(f"Agent loaded from {config_path}")
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        logger.info(f"🤖 Agent initialized: {config.get('name')} ({config.get('model_name')})")
        return agent, config
        
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        raise
    except Exception as e:
        logger.error(f"Failed to load agent: {e}")
        raise ValueError(f"Failed to initialize agent from config: {e}")


# Global variables (initialized in lifespan)
AGENT = None
CONFIG = None
AGENT_CONFIG = None
ENV = None

# Initialize input guardrail (outside request handler for performance)
# Reused across all requests to check user input BEFORE generation
INPUT_TOXICITY_GUARD = InputToxicityGuardrail()

logger.info("🛡️  Input guardrail initialized (maintains streaming):")
logger.info(f"  - INPUT: {INPUT_TOXICITY_GUARD.__class__.__name__} → FixedOpenAIModerationScorer")



# ============================================================================
# Authentication
# ============================================================================

def verify_api_key(authorization: Optional[str] = None) -> None:
    """Verify the API key from the Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header. Please provide API key."
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'"
        )
    
    api_key = authorization[7:]
    expected_key = os.getenv("AGENTIC_SUPPORT_BOT_API_KEY")
    
    if not expected_key:
        logger.error("AGENTIC_SUPPORT_BOT_API_KEY environment variable not set")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: API key not configured"
        )
    
    if api_key != expected_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )


# ============================================================================
# Message Conversion
# ============================================================================

def convert_to_tyler_thread(messages: List[ChatMessage]) -> Thread:
    """Convert OpenAI messages to Tyler Thread with Message objects."""
    thread = Thread()
    for msg in messages:
        thread.add_message(Message(role=msg.role, content=msg.content))
    return thread


def serialize_chunk_to_sse(chunk) -> str:
    """
    Serialize a streaming chunk to Server-Sent Events format.
    
    Converts Tyler/LiteLLM chunk objects to OpenAI-compatible SSE format.
    Returns formatted string: "data: {json}\n\n"
    """
    chunk_dict = {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": getattr(chunk, 'model', 'unknown'),
        "choices": []
    }
    
    # Process choices if present
    if hasattr(chunk, 'choices') and chunk.choices:
        for choice in chunk.choices:
            choice_dict = {
                "index": getattr(choice, 'index', 0),
                "delta": {},
                "finish_reason": getattr(choice, 'finish_reason', None)
            }
            
            # Handle delta
            if hasattr(choice, 'delta'):
                delta = choice.delta
                if hasattr(delta, 'role') and delta.role:
                    choice_dict["delta"]["role"] = delta.role
                if hasattr(delta, 'content') and delta.content is not None:
                    choice_dict["delta"]["content"] = delta.content
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    # Convert tool calls to dict format
                    tool_calls_list = []
                    for tool_call in delta.tool_calls:
                        tool_call_dict = {
                            "index": getattr(tool_call, 'index', 0),
                            "id": getattr(tool_call, 'id', None),
                            "type": getattr(tool_call, 'type', 'function'),
                            "function": {}
                        }
                        if hasattr(tool_call, 'function'):
                            func = tool_call.function
                            tool_call_dict["function"]["name"] = getattr(func, 'name', None)
                            tool_call_dict["function"]["arguments"] = getattr(func, 'arguments', None)
                        tool_calls_list.append(tool_call_dict)
                    
                    choice_dict["delta"]["tool_calls"] = tool_calls_list
            
            chunk_dict["choices"].append(choice_dict)
    
    # Include usage in final chunk
    if hasattr(chunk, 'usage') and chunk.usage:
        chunk_dict["usage"] = {
            "prompt_tokens": getattr(chunk.usage, 'prompt_tokens', 0),
            "completion_tokens": getattr(chunk.usage, 'completion_tokens', 0),
            "total_tokens": getattr(chunk.usage, 'total_tokens', 0)
        }
    
    return f"data: {json.dumps(chunk_dict)}\n\n"


# ============================================================================
# Lifecycle Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage agent and MCP connections during app lifespan."""
    global AGENT, CONFIG, AGENT_CONFIG, ENV
    
    # Startup
    try:
        ENV = get_environment()
        logger.info("="*60)
        logger.info("Tyler Server with Guardrails (Modal - Step 6)")
        logger.info("="*60)
        
        AGENT, CONFIG = load_agent()
        AGENT_CONFIG = CONFIG
        
        if CONFIG.get("mcp"):
            try:
                logger.info("Connecting to MCP servers...")
                await AGENT.connect_mcp()
                logger.info("✓ MCP servers connected successfully")
            except Exception as e:
                logger.error(f"Failed to connect to MCP servers: {e}")
                logger.warning("Continuing without MCP integration")
        
        logger.info("="*60)
        logger.info(f"✅ All systems ready (env={ENV})")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Failed to initialize server: {e}")
        raise
    
    yield
    
    # Shutdown
    if AGENT and CONFIG and CONFIG.get("mcp"):
        try:
            logger.info("Cleaning up MCP connections...")
            await AGENT.cleanup()
            logger.info("✓ MCP cleanup completed")
        except Exception as e:
            logger.warning(f"Error during MCP cleanup: {e}")


# ============================================================================
# FastAPI Application
# ============================================================================

web_app = FastAPI(
    title="Tyler API with Guardrails",
    description="OpenAI-compatible API with safety guardrails (Step 6)",
    version="1.0.0",
    lifespan=lifespan
)

web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Endpoints
# ============================================================================

@web_app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        environment=ENV or "unknown",
        agent_name=AGENT_CONFIG.get("name") if AGENT_CONFIG else None,
        model=AGENT_CONFIG.get("model_name") if AGENT_CONFIG else None
    )


@web_app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Tyler API with Input Guardrail (Step 6)",
        "environment": ENV or "unknown",
        "guardrails": {
            "input": f"{INPUT_TOXICITY_GUARD.__class__.__name__} (OpenAI Moderation API - maintains streaming)"
        },
        "endpoints": {
            "health": "/health",
            "chat_completions": "/v1/chat/completions"
        }
    }


@web_app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    authorization: Optional[str] = Header(None)
):
    """
    OpenAI-compatible chat completions endpoint with input guardrail.
    
    INPUT guardrail approach:
    1. Check user's prompt BEFORE generation (blocks toxic requests early)
    2. If safe, stream response normally (great UX)
    
    Why not output guardrail?
    - Would require buffering full response (no streaming)
    - Kills UX for minimal gain
    - Modern LLMs rarely generate toxic content
    - This is the most common production pattern
    
    Requires API key authentication via Authorization header.
    """
    # Verify API key
    verify_api_key(authorization)
    
    # Validate request
    if not request.messages:
        raise HTTPException(
            status_code=400,
            detail="messages array cannot be empty"
        )
    
    # Log request
    logger.info(f"POST /v1/chat/completions (messages={len(request.messages)}, env={ENV})")
    
    # ========================================================================
    # STAGE 1: INPUT GUARDRAIL - Check user's prompt BEFORE generation
    # ========================================================================
    
    # Extract user's input (last user message)
    user_input = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_input = msg.content
            break
    
    if user_input:
        # Check for toxic user input using OpenAI Moderation API
        input_check = await INPUT_TOXICITY_GUARD.score(input=user_input)
        if input_check["flagged"]:
            blocked_message = f"I cannot process that request: {input_check['reason']}"
            logger.warning(f"🛡️  INPUT guardrail blocked (BEFORE generation): {input_check['reason']}")
            
            # Return blocked message immediately (DON'T generate!)
            return JSONResponse(content={
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": AGENT_CONFIG["model_name"],
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": blocked_message
                    },
                    "finish_reason": "content_filter"
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }, status_code=200)
    
    logger.info("✓ INPUT guardrail passed - proceeding to streaming generation")
    
    # Convert messages to Tyler thread
    try:
        thread = convert_to_tyler_thread(request.messages)
    except Exception as e:
        logger.error(f"Failed to convert messages: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid message format: {e}")
    
    # ========================================================================
    # STREAM RESPONSE (input guardrail passed - safe to stream)
    # ========================================================================
    
    # Stream response from Tyler agent
    async def generate() -> AsyncGenerator[str, None]:
        """Generate SSE stream from Tyler agent."""
        try:
            # Wrap agent call with weave.attributes to tag with environment
            with weave.attributes({"env": ENV}):
                async for chunk in AGENT.stream(thread, mode="raw"):
                    yield serialize_chunk_to_sse(chunk)
            
            # Send [DONE] message
            yield "data: [DONE]\n\n"
            
            logger.info("Request completed successfully")
            
        except Exception as e:
            logger.error(f"Error during streaming: {e}")
            # Send error as SSE
            error_chunk = {
                "error": {
                    "message": str(e),
                    "type": "internal_error"
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    # Return streaming response
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


# ============================================================================
# Modal Web Endpoint
# ============================================================================

@app.function(
    image=image,
    secrets=[modal.Secret.from_name(
        "agentic-support-bot-secrets",
        environment_name="main",
        required_keys=["WANDB_API_KEY", "AGENTIC_SUPPORT_BOT_API_KEY", "OPENAI_API_KEY"]
    )],
    timeout=300,
)
@modal.asgi_app()
def modal_endpoint():
    """
    Modal web endpoint that serves the FastAPI app.
    
    Works for both `modal serve` (dev) and `modal deploy` (prod).
    """
    return web_app

