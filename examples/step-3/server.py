"""
Tyler agent server deployed on Modal.

Works in two modes:
- Development: `modal serve workspace/server.py` (ephemeral, auto-reload)
- Production: `modal deploy workspace/server.py` (persistent, stable)

The same server file works for both - Modal handles the differences.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Literal, Optional, AsyncGenerator

import modal
import yaml
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import weave
from tyler import Agent, Thread, Message

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

# Create Modal app (Modal convention: use 'app' for the Modal App object)
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
    """
    Get the Modal environment name for Weave tagging.
    
    Returns:
        Modal environment name ("dev" or "main")
    """
    # Modal sets MODAL_ENVIRONMENT to the environment name
    # We use: "dev" for development, "main" for production
    # Just return the Modal environment name directly
    return os.getenv("MODAL_ENVIRONMENT", "main")


# ============================================================================
# Pydantic Models
# ============================================================================

class ChatMessage(BaseModel):
    """A single message in a conversation."""
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: Optional[str] = None  # For tool messages


class ChatCompletionRequest(BaseModel):
    """Request format for /v1/chat/completions endpoint."""
    model: str  # Required by OpenAI spec (not used by our server)
    messages: List[ChatMessage]
    stream: bool = False
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
    """
    Load Tyler agent from configuration file using Agent.from_config().
    
    Args:
        config_path: Path to the Tyler configuration YAML file
    
    Returns:
        Tuple of (agent instance, config dict)
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid or tools can't be loaded or secrets are missing
    """
    # Validate required secrets
    required_secrets = ["WANDB_API_KEY", "AGENTIC_SUPPORT_BOT_API_KEY"]
    missing_secrets = [s for s in required_secrets if not os.getenv(s)]
    if missing_secrets:
        error_msg = (
            f"\n{'='*70}\n"
            f"❌ Missing required Modal secrets: {', '.join(missing_secrets)}\n\n"
            f"Please create Modal secrets with:\n"
            f"  modal secret create agentic-support-bot-secrets \\\n"
            f"    WANDB_API_KEY=<your-key> \\\n"
            f"    AGENTIC_SUPPORT_BOT_API_KEY=<your-key>\n\n"
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
        # Change to workspace directory so tools.py can find db/tickets.json
        os.chdir("/workspace")
        agent = Agent.from_config(config_path)
        logger.info(f"Agent loaded from {config_path}")
        
        # Load config dict for reference
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        logger.info(f"🤖 Agent initialized: {config.get('name')} ({config.get('model_name')})")
        return agent, config
        
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        raise FileNotFoundError(
            f"Configuration file '{config_path}' not found. "
            "Please ensure tyler-chat-config.yaml is in the workspace directory."
        )
    except Exception as e:
        logger.error(f"Failed to load agent: {e}")
        raise ValueError(f"Failed to initialize agent from config: {e}")


# Global agent variables (initialized in lifespan)
AGENT = None
CONFIG = None
AGENT_CONFIG = None
ENV = None


# ============================================================================
# SSE Serialization (OpenAI-compatible streaming)
# ============================================================================

def serialize_chunk_to_sse(chunk) -> str:
    """
    Convert LiteLLM chunk to Server-Sent Events format.
    
    Args:
        chunk: LiteLLM ModelResponseStream object
        
    Returns:
        SSE-formatted string: "data: {json}\\n\\n"
    """
    chunk_dict = {
        "id": getattr(chunk, 'id', f'chatcmpl-{uuid.uuid4()}'),
        "object": getattr(chunk, 'object', 'chat.completion.chunk'),
        "created": getattr(chunk, 'created', int(time.time())),
        "model": getattr(chunk, 'model', AGENT_CONFIG["model_name"]),
        "choices": []
    }
    
    # Extract choices
    if hasattr(chunk, 'choices') and chunk.choices:
        for choice in chunk.choices:
            choice_dict = {
                "index": getattr(choice, 'index', 0),
                "delta": {},
                "finish_reason": getattr(choice, 'finish_reason', None)
            }
            
            # Extract delta (it's an object, not a dict)
            if hasattr(choice, 'delta'):
                delta = choice.delta
                
                # Handle content
                if hasattr(delta, 'content') and delta.content:
                    choice_dict["delta"]["content"] = delta.content
                
                # Handle role
                if hasattr(delta, 'role') and delta.role:
                    choice_dict["delta"]["role"] = delta.role
                
                # Handle thinking tokens (reasoning content)
                # Support both LiteLLM's 'thinking' and vLLM's 'reasoning_content' fields
                thinking_text = None
                if hasattr(delta, 'thinking') and delta.thinking:
                    thinking_text = delta.thinking
                elif hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    thinking_text = delta.reasoning_content
                
                # Output both field names for maximum compatibility
                if thinking_text:
                    choice_dict["delta"]["thinking"] = thinking_text
                    choice_dict["delta"]["reasoning_content"] = thinking_text
                
                # Handle tool calls
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    tool_calls_list = []
                    for tool_call in delta.tool_calls:
                        tool_call_dict = {
                            "index": getattr(tool_call, 'index', 0),
                            "id": getattr(tool_call, 'id', None),
                            "type": getattr(tool_call, 'type', 'function'),
                        }
                        
                        # Handle function details
                        if hasattr(tool_call, 'function'):
                            func = tool_call.function
                            tool_call_dict["function"] = {
                                "name": getattr(func, 'name', None),
                                "arguments": getattr(func, 'arguments', None)
                            }
                        
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
# Authentication
# ============================================================================

def verify_api_key(authorization: Optional[str] = None) -> None:
    """
    Verify the API key from the Authorization header.
    
    Validates the provided API key against the AGENTIC_SUPPORT_BOT_API_KEY environment variable.
    If AGENTIC_SUPPORT_BOT_API_KEY is not set, raises an error to prevent unauthorized access.
    
    Args:
        authorization: Authorization header value (e.g., "Bearer <your-secret-key>")
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header. Please provide API key."
        )
    
    # Extract bearer token
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'"
        )
    
    api_key = authorization[7:]  # Remove "Bearer " prefix
    
    # Get expected API key from environment variable
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
    """
    Convert OpenAI messages to Tyler Thread with Message objects.
    
    Args:
        messages: List of ChatMessage objects from request
        
    Returns:
        Tyler Thread instance with messages added
    """
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
    
    # Startup: Load agent and connect to MCP servers
    try:
        ENV = get_environment()
        logger.info("="*60)
        logger.info("Tyler Playground API Server (Modal)")
        logger.info("="*60)
        
        # Load agent
        AGENT, CONFIG = load_agent()
        AGENT_CONFIG = CONFIG
        
        # Connect to MCP servers if configured
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
    
    # Shutdown: Cleanup MCP connections
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
    title="Tyler Playground API",
    description="OpenAI-compatible API for Tyler support bot agent (deployed on Modal)",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
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
    """Root endpoint - redirects to health check."""
    return {
        "message": "Tyler Playground API (Modal)",
        "environment": ENV or "unknown",
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
    OpenAI-compatible chat completions endpoint.
    
    Always streams responses for optimal UX.
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
    logger.info(
        f"POST /v1/chat/completions (messages={len(request.messages)}, env={ENV})"
    )
    
    # Convert messages to Tyler thread
    try:
        thread = convert_to_tyler_thread(request.messages)
    except Exception as e:
        logger.error(f"Failed to convert messages: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid message format: {e}"
        )
    
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
            
            logger.info("Request completed")
            
        except Exception as e:
            logger.error(f"Error during streaming: {e}")
            # Send error as SSE
            error_chunk = {
                "error": {
                    "message": str(e),
                    "type": "server_error"
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
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
    # Reference shared secret from main environment (accessible from all environments)
    secrets=[modal.Secret.from_name(
        "agentic-support-bot-secrets",
        environment_name="main",
        required_keys=["WANDB_API_KEY", "AGENTIC_SUPPORT_BOT_API_KEY"]
    )],
    timeout=300,  # 5 minute timeout
)
@modal.asgi_app()
def modal_endpoint():
    """
    Modal web endpoint that serves the FastAPI app.
    
    This function is called by Modal to create the ASGI app.
    Works for both `modal serve` (dev) and `modal deploy` (prod).
    """
    return web_app

