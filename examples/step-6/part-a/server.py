"""
Tyler agent server with guardrails deployed on Modal.

Step 6 Part A: Adds guardrail scorers to block unsafe content before it reaches users.

Changes from Step 5:
- Imports guardrail scorers (ToxicityGuardrail, OffTopicGuardrail)
- Initializes guardrails outside request handler (performance)
- Applies guardrails sequentially after agent generates response
- Returns blocked message if guardrail flags content
- Complete responses instead of streaming (needed to check content before sending)

Works in two modes:
- Development: `modal serve --env dev workspace/server.py` (ephemeral, auto-reload)
- Production: `modal deploy workspace/server.py` (persistent, stable)
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
from typing import List, Literal, Optional

import modal
import yaml
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import weave
from tyler import Agent, Thread, Message

# Add /workspace to Python path for imports
sys.path.insert(0, "/workspace")

# Import guardrails (Weave's built-in scorers)
from guardrails import InputToxicityGuardrail, OutputToxicityGuardrail

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

# Initialize guardrails (outside request handler for performance)
# These are reused across all requests
# Two-stage approach: Check input BEFORE generation, output AFTER
INPUT_TOXICITY_GUARD = InputToxicityGuardrail()
OUTPUT_TOXICITY_GUARD = OutputToxicityGuardrail()

logger.info("🛡️  Two-stage guardrails initialized (Weave built-in scorers):")
logger.info(f"  - INPUT:  {INPUT_TOXICITY_GUARD.__class__.__name__} → OpenAIModerationScorer")
logger.info(f"  - OUTPUT: {OUTPUT_TOXICITY_GUARD.__class__.__name__} → WeaveToxicityScorerV1")


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
        "message": "Tyler API with Two-Stage Guardrails (Step 6)",
        "environment": ENV or "unknown",
        "guardrails": {
            "input": [f"{INPUT_TOXICITY_GUARD.__class__.__name__} (OpenAI Moderation API)"],
            "output": [f"{OUTPUT_TOXICITY_GUARD.__class__.__name__} (WeaveToxicityScorerV1)"]
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
    OpenAI-compatible chat completions endpoint with two-stage guardrails.
    
    Two-stage guardrail approach:
    1. INPUT guardrail: Check user's prompt BEFORE generation (blocks toxic requests early)
    2. OUTPUT guardrail: Check agent's response AFTER generation (safety net)
    
    This approach is more efficient - we avoid generating responses to toxic prompts,
    saving both LLM costs and time.
    
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
            return {
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
            }
    
    logger.info("✓ INPUT guardrail passed - proceeding to generation")
    
    # Convert messages to Tyler thread
    try:
        thread = convert_to_tyler_thread(request.messages)
    except Exception as e:
        logger.error(f"Failed to convert messages: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid message format: {e}")
    
    # ========================================================================
    # GENERATE RESPONSE (only if input guardrail passed)
    # ========================================================================
    
    try:
        # Generate response with weave.attributes to tag with environment
        with weave.attributes({"env": ENV}):
            # Collect full response (not streaming for output guardrail check)
            full_response = ""
            async for chunk in AGENT.stream(thread, mode="raw"):
                # Extract content from chunk
                if hasattr(chunk, 'choices') and chunk.choices:
                    for choice in chunk.choices:
                        if hasattr(choice, 'delta') and hasattr(choice.delta, 'content'):
                            if choice.delta.content:
                                full_response += choice.delta.content
            
            logger.info("✓ Response generated - applying OUTPUT guardrail")
            
            # ================================================================
            # STAGE 2: OUTPUT GUARDRAIL - Check agent's response AFTER generation
            # ================================================================
            
            # Check if agent's response is toxic using local ML model
            output_check = await OUTPUT_TOXICITY_GUARD.score(output=full_response)
            if output_check["flagged"]:
                blocked_message = f"I cannot generate that content: {output_check['reason']}"
                logger.warning(f"🛡️  OUTPUT guardrail blocked (AFTER generation): {output_check['reason']}")
                
                # Block the response (don't send to user)
                return {
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
                }
            
            # All guardrails passed - return safe response
            logger.info("✓ OUTPUT guardrail passed - returning response to user")
            return {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": AGENT_CONFIG["model_name"],
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": full_response
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }
        
    except Exception as e:
        logger.error(f"Error during request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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

