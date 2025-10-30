"""
OpenAI-compatible API server for Tyler agent.

Exposes the Tyler support bot through a /v1/chat/completions endpoint
that works with Weave Playground and other OpenAI-compatible clients.
"""

import argparse
import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import List, Literal, Optional, AsyncGenerator

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import weave
from tyler import Agent, Thread, Message

# Configure logging
logging.basicConfig(
    level=os.getenv("PLAYGROUND_LOG_LEVEL", "INFO"),
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

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
    agent_name: str
    model: str


# ============================================================================
# Agent Initialization
# ============================================================================

def load_agent(config_path: str = "tyler-chat-config.yaml") -> tuple[Agent, dict]:
    """
    Load Tyler agent from configuration file using Agent.from_config().
    
    Args:
        config_path: Path to the Tyler configuration YAML file
    
    Returns:
        Tuple of (agent instance, config dict)
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid or tools can't be loaded
    """
    # Initialize Weave before loading agent
    try:
        project = os.getenv("WANDB_PROJECT", "agentic-support-bot-demo")
        weave.init(project)
        logger.info(f"Weave initialized: project={project}")
    except Exception as e:
        logger.warning(f"Weave initialization failed: {e} (observability degraded)")
    
    # Use new Agent.from_config() helper from Slide 4.2.0
    try:
        agent = Agent.from_config(config_path)
        logger.info(f"Agent loaded from {config_path}")
        
        # Load config dict for reference
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        logger.info(f"Agent initialized: {config.get('name')} ({config.get('model_name')})")
        return agent, config
        
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        raise FileNotFoundError(
            f"Configuration file '{config_path}' not found. "
            "Please run the server from the project root directory."
        )
    except Exception as e:
        logger.error(f"Failed to load agent: {e}")
        raise ValueError(f"Failed to initialize agent from config: {e}")


# Global agent variables (initialized conditionally below)
AGENT = None
CONFIG = None
AGENT_CONFIG = None

# Initialize agent at module load time only if not running as main script
# When running as main, command-line args will handle initialization
if __name__ != "__main__":
    try:
        # Check for config path in environment variable
        # Default to workspace directory
        import pathlib
        workspace_dir = pathlib.Path(__file__).parent
        default_config = workspace_dir / "tyler-chat-config.yaml"
        config_path = os.getenv("TYLER_CONFIG", str(default_config))
        AGENT, CONFIG = load_agent(config_path)
        AGENT_CONFIG = CONFIG.get("agent", CONFIG)
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise


# ============================================================================
# SSE Serialization
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
    
    Validates the provided API key against the PLAYGROUND_API_KEY environment variable.
    If PLAYGROUND_API_KEY is not set, raises an error to prevent unauthorized access.
    
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
    expected_key = os.getenv("PLAYGROUND_API_KEY")
    if not expected_key:
        logger.error("PLAYGROUND_API_KEY environment variable not set")
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
    """Manage MCP connections during app lifespan."""
    # Startup: Connect to MCP servers
    if AGENT and CONFIG and CONFIG.get("mcp"):
        try:
            logger.info("Connecting to MCP servers...")
            await AGENT.connect_mcp()
            logger.info("✓ MCP servers connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MCP servers: {e}")
            # Don't fail startup - MCP is optional
            logger.warning("Continuing without MCP integration")
    
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

app = FastAPI(
    title="Tyler Playground API",
    description="OpenAI-compatible API for Tyler support bot agent",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        agent_name=AGENT_CONFIG["name"],
        model=AGENT_CONFIG["model_name"]
    )


@app.get("/")
async def root():
    """Root endpoint - redirects to health check."""
    return {
        "message": "Tyler Playground API",
        "endpoints": {
            "health": "/health",
            "chat_completions": "/v1/chat/completions"
        }
    }


@app.post("/v1/chat/completions")
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
        f"POST /v1/chat/completions (messages={len(request.messages)})"
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
# Server Startup
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    import pathlib
    import ngrok
    
    # Default config path is in the workspace directory
    workspace_dir = pathlib.Path(__file__).parent
    default_config_path = str(workspace_dir / "tyler-chat-config.yaml")
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Tyler Playground API Server - OpenAI-compatible chat completions endpoint"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=default_config_path,
        help=f"Path to Tyler configuration YAML file (default: {default_config_path})"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("PLAYGROUND_SERVER_HOST", "0.0.0.0"),
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PLAYGROUND_SERVER_PORT", "8000")),
        help="Port to bind the server to (default: 8000)"
    )
    args = parser.parse_args()
    
    # Validate required environment variables
    if not os.getenv("PLAYGROUND_API_KEY"):
        logger.error("PLAYGROUND_API_KEY environment variable is required")
        logger.error("Please set it in your .env file or environment")
        logger.error("Example: export PLAYGROUND_API_KEY=your_secret_key")
        raise ValueError("Missing required environment variable: PLAYGROUND_API_KEY")
    
    if not os.getenv("NGROK_AUTHTOKEN"):
        logger.error("NGROK_AUTHTOKEN environment variable is required")
        logger.error("Please set it in your .env file")
        logger.error("Get your authtoken at: https://dashboard.ngrok.com/get-started/your-authtoken")
        raise ValueError("Missing required environment variable: NGROK_AUTHTOKEN")
    
    # Load the agent with the specified config
    try:
        AGENT, CONFIG = load_agent(args.config)
        AGENT_CONFIG = CONFIG.get("agent", CONFIG)
    except Exception as e:
        logger.error(f"Failed to load agent with config {args.config}: {e}")
        raise
    
    # Set up ngrok tunnel
    logger.info("Setting up ngrok tunnel...")
    try:
        listener = ngrok.forward(args.port, authtoken_from_env=True)
        tunnel_url = listener.url()
        logger.info(f"✓ Ngrok tunnel established: {tunnel_url}")
    except Exception as e:
        logger.error(f"Failed to create ngrok tunnel: {e}")
        logger.error("Make sure NGROK_AUTHTOKEN is set correctly")
        raise
    
    logger.info("="*60)
    logger.info("Tyler Playground API Server")
    logger.info("="*60)
    logger.info(f"Config: {args.config}")
    logger.info(f"Agent: {AGENT_CONFIG['name']} ({AGENT_CONFIG['model_name']})")
    logger.info(f"Local server: http://{args.host}:{args.port}")
    logger.info(f"Health check: http://{args.host}:{args.port}/health")
    logger.info(f"Authentication: Required (Bearer token)")
    logger.info("="*60)
    logger.info("")
    logger.info("🌐 NGROK TUNNEL ACTIVE")
    logger.info(f"   Use this Base URL in Weave Playground: {tunnel_url}/v1")
    logger.info("")
    logger.info("="*60)
    
    uvicorn.run(
        "playground_server:app",
        host=args.host,
        port=args.port,
        log_level="info",
        reload=False  # Disable reload to prevent double initialization
    )

