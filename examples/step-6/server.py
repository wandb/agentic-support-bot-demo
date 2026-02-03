"""
Tyler agent server with optional input guardrails deployed on Modal.

Works in two modes:
- Development: `modal serve examples/step-6/server.py` (ephemeral, auto-reload)
- Production: `modal deploy examples/step-6/server.py` (persistent, stable)

The agent is loaded from Weave based on the config reference in config.json.
The config YAML is fetched from Weave and used to create the Tyler Agent.
Update config.json to deploy a different config version, then redeploy.

Guardrails:
- If OPENAI_API_KEY is set, input guardrails are enabled (blocks toxic requests)
- If OPENAI_API_KEY is not set, guardrails are disabled (agent runs without safety checks)
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
from typing import List, Literal, Optional, AsyncGenerator

import modal
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import weave
from tyler import Agent, Thread, Message

# Add /workspace to Python path for imports (guardrails, tools)
sys.path.insert(0, "/workspace")

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ============================================================================
# Conditional Guardrail Initialization
# ============================================================================

# Initialize input guardrail only if OPENAI_API_KEY is available
INPUT_TOXICITY_GUARD = None
GUARDRAILS_ENABLED = False

if os.getenv("OPENAI_API_KEY"):
    try:
        from guardrails import InputToxicityGuardrail
        INPUT_TOXICITY_GUARD = InputToxicityGuardrail()
        GUARDRAILS_ENABLED = True
        logger.info("🛡️  Guardrails ENABLED (OPENAI_API_KEY found)")
        logger.info(f"   Input guardrail: {INPUT_TOXICITY_GUARD.__class__.__name__}")
    except ImportError as e:
        logger.warning(f"⚠️  Guardrails import failed: {e}")
        logger.warning("   Guardrails disabled - continuing without safety checks")
    except Exception as e:
        logger.warning(f"⚠️  Guardrails initialization failed: {e}")
        logger.warning("   Guardrails disabled - continuing without safety checks")
else:
    logger.warning("⚠️  Guardrails DISABLED (no OPENAI_API_KEY)")
    logger.warning("   To enable guardrails, add OPENAI_API_KEY to Modal secrets")

# ============================================================================
# Modal Configuration
# ============================================================================

# Create Modal app
app = modal.App("agentic-support-bot")

# Create Modal image with dependencies and workspace files
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_pyproject(Path(__file__).parent.parent.parent / "pyproject.toml")
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
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class HealthResponse(BaseModel):
    """Response format for health check endpoint."""
    status: str
    environment: str
    agent_name: Optional[str] = None
    config_ref: Optional[str] = None
    model: Optional[str] = None
    guardrails_enabled: bool = False


# ============================================================================
# Agent Loading from Weave Config
# ============================================================================

def load_config_ref(config_path: str = "/workspace/config.json") -> str:
    """
    Load config reference from JSON file.
    
    Args:
        config_path: Path to the config JSON file
    
    Returns:
        Config ref string (e.g., "Buzz:v3")
    
    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"\n{'='*70}\n"
            f"❌ Config file not found at: {config_path}\n\n"
            f"Please create config.json with your config reference:\n"
            f'{{"config_ref": "YourAgentName:latest"}}\n\n'
            f"Or use the marimo notebook to select and save your config.\n"
            f"{'='*70}\n"
        )
    
    with open(config_path) as f:
        config = json.load(f)
    
    if "config_ref" not in config:
        raise ValueError("config.json must contain 'config_ref' field")
    
    return config["config_ref"]


def load_agent(config_json_path: str = "/workspace/config.json") -> tuple[Agent, str]:
    """
    Load Tyler agent by fetching config YAML from Weave.
    
    The config YAML is stored in Weave as an AgentConfig object.
    This function fetches the YAML, writes it to disk, and creates
    the Tyler Agent using Agent.from_config().
    
    Args:
        config_json_path: Path to the config.json file with config_ref
    
    Returns:
        Tuple of (agent instance, config_ref string)
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config can't be loaded from Weave
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
    
    # Load config ref from JSON
    config_ref = load_config_ref(config_json_path)
    
    # Ensure ref has version (append :latest if not)
    if ':' not in config_ref:
        config_ref = f"{config_ref}:latest"
    
    # Load config YAML from Weave
    try:
        logger.info(f"Loading config from Weave: {config_ref}")
        config_obj = weave.ref(config_ref).get()
        
        # Extract YAML content from AgentConfig object
        yaml_content = config_obj.yaml
        config_name = config_obj.name
        
        logger.info(f"📄 Config loaded: {config_name} ({config_ref})")
        
        # Write YAML to workspace where tools.py exists
        config_path = Path("/workspace/tyler-chat-config.yaml")
        config_path.write_text(yaml_content)
        logger.info(f"📝 Config written to {config_path}")
        
        # Change to workspace directory so relative paths (./tools.py) work
        os.chdir("/workspace")
        
        # Create Tyler Agent from config
        agent = Agent.from_config(str(config_path))
        logger.info(f"🤖 Agent created: {agent.name} (tools: {len(agent.tools) if hasattr(agent, 'tools') and agent.tools else 0})")
        
        return agent, config_ref
        
    except Exception as e:
        logger.error(f"Failed to load config from Weave: {e}")
        raise ValueError(
            f"Could not load config '{config_ref}' from Weave. "
            f"Make sure the config exists and you have access. Error: {e}"
        )


# Global agent variables (initialized in lifespan)
AGENT = None
CONFIG_REF = None
ENV = None


# ============================================================================
# SSE Serialization (OpenAI-compatible streaming)
# ============================================================================

def serialize_chunk_to_sse(chunk) -> str:
    """Convert LiteLLM chunk to Server-Sent Events format."""
    chunk_dict = {
        "id": getattr(chunk, 'id', f'chatcmpl-{uuid.uuid4()}'),
        "object": getattr(chunk, 'object', 'chat.completion.chunk'),
        "created": getattr(chunk, 'created', int(time.time())),
        "model": getattr(chunk, 'model', AGENT.model_name if AGENT else "unknown"),
        "choices": []
    }
    
    if hasattr(chunk, 'choices') and chunk.choices:
        for choice in chunk.choices:
            choice_dict = {
                "index": getattr(choice, 'index', 0),
                "delta": {},
                "finish_reason": getattr(choice, 'finish_reason', None)
            }
            
            if hasattr(choice, 'delta'):
                delta = choice.delta
                
                if hasattr(delta, 'content') and delta.content:
                    choice_dict["delta"]["content"] = delta.content
                
                if hasattr(delta, 'role') and delta.role:
                    choice_dict["delta"]["role"] = delta.role
                
                # Handle thinking tokens
                thinking_text = None
                if hasattr(delta, 'thinking') and delta.thinking:
                    thinking_text = delta.thinking
                elif hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    thinking_text = delta.reasoning_content
                
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
                        
                        if hasattr(tool_call, 'function'):
                            func = tool_call.function
                            tool_call_dict["function"] = {
                                "name": getattr(func, 'name', None),
                                "arguments": getattr(func, 'arguments', None)
                            }
                        
                        tool_calls_list.append(tool_call_dict)
                    
                    choice_dict["delta"]["tool_calls"] = tool_calls_list
            
            chunk_dict["choices"].append(choice_dict)
    
    if hasattr(chunk, 'usage') and chunk.usage:
        chunk_dict["usage"] = {
            "prompt_tokens": getattr(chunk.usage, 'prompt_tokens', 0),
            "completion_tokens": getattr(chunk.usage, 'completion_tokens', 0),
            "total_tokens": getattr(chunk.usage, 'total_tokens', 0)
        }
    
    return f"data: {json.dumps(chunk_dict)}\n\n"


def create_blocked_message_stream(message: str, model: str, finish_reason: str = "content_filter") -> str:
    """
    Create a streaming SSE response for blocked/filtered messages.
    
    Used when guardrails block a request - maintains streaming consistency.
    Returns a complete chunk with the blocked message in SSE format.
    """
    chunk_dict = {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {
                "role": "assistant",
                "content": message
            },
            "finish_reason": finish_reason
        }]
    }
    return f"data: {json.dumps(chunk_dict)}\n\n"


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
        raise HTTPException(status_code=401, detail="Invalid API key")


# ============================================================================
# Message Conversion
# ============================================================================

def convert_to_tyler_thread(messages: List[ChatMessage]) -> Thread:
    """Convert OpenAI messages to Tyler Thread."""
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
    global AGENT, CONFIG_REF, ENV
    
    try:
        ENV = get_environment()
        logger.info("="*60)
        logger.info("Tyler Playground API Server (Modal)")
        if GUARDRAILS_ENABLED:
            logger.info("🛡️  Guardrails: ENABLED")
        else:
            logger.info("⚠️  Guardrails: DISABLED")
        logger.info("="*60)
        
        # Load agent from Weave config
        AGENT, CONFIG_REF = load_agent()
        
        # Connect to MCP servers if the agent has them configured
        if hasattr(AGENT, 'mcp_config') and AGENT.mcp_config:
            try:
                logger.info("Connecting to MCP servers...")
                await AGENT.connect_mcp()
                logger.info("✓ MCP servers connected successfully")
            except Exception as e:
                logger.error(f"Failed to connect to MCP servers: {e}")
                logger.warning("Continuing without MCP integration")
        
        logger.info("="*60)
        logger.info(f"✅ All systems ready (env={ENV})")
        logger.info(f"   Agent: {AGENT.name} (config: {CONFIG_REF})")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Failed to initialize server: {e}")
        raise
    
    yield
    
    # Shutdown: Cleanup MCP connections
    if AGENT and hasattr(AGENT, 'mcp_config') and AGENT.mcp_config:
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
    description="OpenAI-compatible API for Tyler support bot agent with optional guardrails (deployed on Modal)",
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
        agent_name=AGENT.name if AGENT else None,
        config_ref=CONFIG_REF,
        model=AGENT.model_name if AGENT else None,
        guardrails_enabled=GUARDRAILS_ENABLED
    )


@web_app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Tyler Playground API (Modal)",
        "environment": ENV or "unknown",
        "guardrails": {
            "enabled": GUARDRAILS_ENABLED,
            "input": INPUT_TOXICITY_GUARD.__class__.__name__ if INPUT_TOXICITY_GUARD else None
        },
        "agent": {
            "name": AGENT.name if AGENT else None,
            "config_ref": CONFIG_REF,
            "model": AGENT.model_name if AGENT else None
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
    OpenAI-compatible chat completions endpoint with optional input guardrail.
    
    If OPENAI_API_KEY is set, input guardrails check user prompts BEFORE generation.
    Toxic requests are blocked immediately without calling the LLM.
    """
    verify_api_key(authorization)
    
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages array cannot be empty")
    
    logger.info(f"POST /v1/chat/completions (messages={len(request.messages)}, config={CONFIG_REF})")
    
    # ========================================================================
    # INPUT GUARDRAIL (if enabled) - Check user's prompt BEFORE generation
    # ========================================================================
    
    if INPUT_TOXICITY_GUARD:
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
                blocked_message = f"I apologize, but I cannot process your request as it was flagged for: {input_check['reason']}"
                logger.warning(f"🛡️  INPUT guardrail blocked: {input_check['reason']}")
                
                # Stream blocked message (maintains streaming consistency)
                async def generate_blocked() -> AsyncGenerator[str, None]:
                    """Stream the blocked message in SSE format."""
                    yield create_blocked_message_stream(
                        message=blocked_message,
                        model=AGENT.model_name if AGENT else "unknown",
                        finish_reason="content_filter"
                    )
                    yield "data: [DONE]\n\n"
                
                return StreamingResponse(
                    generate_blocked(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no"
                    }
                )
        
        logger.info("✓ INPUT guardrail passed")
    
    # ========================================================================
    # STREAM RESPONSE
    # ========================================================================
    
    try:
        thread = convert_to_tyler_thread(request.messages)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid message format: {e}")
    
    async def generate() -> AsyncGenerator[str, None]:
        """Generate SSE stream from Tyler agent."""
        try:
            with weave.attributes({"env": ENV, "config_ref": CONFIG_REF}):
                async for chunk in AGENT.stream(thread, mode="openai"):
                    yield serialize_chunk_to_sse(chunk)
            
            yield "data: [DONE]\n\n"
            logger.info("Request completed")
            
        except Exception as e:
            logger.error(f"Error during streaming: {e}")
            error_chunk = {"error": {"message": str(e), "type": "server_error"}}
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
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
        required_keys=["WANDB_API_KEY", "AGENTIC_SUPPORT_BOT_API_KEY"]
    )],
    timeout=300,
)
@modal.asgi_app()
def modal_endpoint():
    """Modal web endpoint that serves the FastAPI app."""
    return web_app
