"""
OpenAI-compatible API server for Tyler agent.

Exposes the Tyler support bot through a /v1/chat/completions endpoint
that works with Weave Playground and other OpenAI-compatible clients.
"""

import asyncio
import json
import logging
import os
import time
import uuid
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

def load_agent() -> tuple[Agent, dict]:
    """
    Load Tyler agent from configuration file.
    
    Returns:
        Tuple of (agent instance, config dict)
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid or tools can't be loaded
    """
    config_path = "tyler-chat-config.yaml"
    
    # Load config file
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded configuration from {config_path}")
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        raise FileNotFoundError(
            f"Configuration file '{config_path}' not found. "
            "Please run the server from the project root directory."
        )
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in config file: {e}")
        raise ValueError(f"Failed to parse config file: {e}")
    
    # Extract agent config (handle nested structure)
    agent_config = config.get("agent", config)  # Support both nested and flat
    
    # Validate required fields
    required_fields = ["name", "model_name", "purpose"]
    missing_fields = [f for f in required_fields if f not in agent_config]
    if missing_fields:
        raise ValueError(f"Missing required config fields: {', '.join(missing_fields)}")
    
    # Load tools dynamically
    tools = []
    if "tools" in config and config["tools"]:
        tool_path = config["tools"][0]  # Get first tool path
        logger.info(f"Loading tools from {tool_path}")
        
        try:
            # Import tools module
            import importlib.util
            spec = importlib.util.spec_from_file_location("custom_tools", tool_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Failed to load module from {tool_path}")
            
            tools_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(tools_module)
            
            # Get TOOLS list
            if hasattr(tools_module, 'TOOLS'):
                tools = tools_module.TOOLS
                # Validate dict-based tool specs only
                if not isinstance(tools, list):
                    raise TypeError("TOOLS must be a list of dict-based tool definitions")
                validated_tools = []
                tool_names = []
                for idx, t in enumerate(tools):
                    if not isinstance(t, dict):
                        raise TypeError(
                            f"TOOLS[{idx}] must be a dict with 'definition' and 'implementation'"
                        )
                    definition = t.get('definition')
                    implementation = t.get('implementation')
                    if not isinstance(definition, dict):
                        raise ValueError(
                            f"TOOLS[{idx}].definition must be a dict"
                        )
                    if implementation is None:
                        raise ValueError(
                            f"TOOLS[{idx}] missing 'implementation'"
                        )
                    # Extract function name for logging
                    name = (
                        definition.get('function', {})
                                  .get('name')
                    )
                    if not name:
                        raise ValueError(
                            f"TOOLS[{idx}].definition.function.name is required"
                        )
                    validated_tools.append(t)
                    tool_names.append(name)
                tools = validated_tools
                logger.info(f"Loaded {len(tools)} tools: {tool_names}")
            else:
                logger.warning(f"No TOOLS list found in {tool_path}")
        except Exception as e:
            logger.error(f"Failed to load tools from {tool_path}: {e}")
            raise ValueError(f"Failed to load tools: {e}")
    
    # Initialize Weave
    try:
        project = os.getenv("WANDB_PROJECT", "agentic-support-bot-demo")
        weave.init(project)
        logger.info(f"Weave initialized: project={project}")
    except Exception as e:
        logger.warning(f"Weave initialization failed: {e} (observability degraded)")
    
    # Create agent with all config fields
    agent_kwargs = {
        "name": agent_config["name"],
        "model_name": agent_config["model_name"],
        "purpose": agent_config["purpose"],
        "tools": tools,
        "temperature": config.get("temperature", 0.7),
        "max_tool_iterations": config.get("max_tool_iterations", 10)
    }
    
    # Add optional fields if present
    if "base_url" in config:
        agent_kwargs["base_url"] = config["base_url"]
        logger.info(f"Using base_url: {config['base_url']}")
    
    if "api_key" in config:
        # Support environment variable expansion (e.g., ${WANDB_API_KEY})
        api_key = config["api_key"]
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            api_key = os.getenv(env_var)
            if not api_key:
                logger.warning(f"Environment variable {env_var} not set")
        agent_kwargs["api_key"] = api_key
    
    if "reasoning" in config:
        agent_kwargs["reasoning"] = config["reasoning"]
        logger.info(f"Reasoning enabled: {config['reasoning']}")
    
    if "notes" in agent_config:
        agent_kwargs["notes"] = agent_config["notes"]
    
    agent = Agent(**agent_kwargs)
    
    logger.info(f"Agent initialized: {agent_config['name']} ({agent_config['model_name']})")
    return agent, config


# Initialize agent at startup
try:
    AGENT, CONFIG = load_agent()
    # Extract agent config for easy access throughout the module
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
    
    This is a simple demonstration of API key validation.
    In production, you would validate against a secure secret store.
    
    Args:
        authorization: Authorization header value (e.g., "Bearer dummy")
        
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
    
    # For demo purposes, we accept "dummy" as the API key
    # In production, you would validate against W&B secrets or a secure key store
    if api_key != "dummy":
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
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Tyler Playground API",
    description="OpenAI-compatible API for Tyler support bot agent",
    version="1.0.0"
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
            async for chunk in AGENT.go(thread, stream="raw"):
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
    
    host = os.getenv("PLAYGROUND_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("PLAYGROUND_SERVER_PORT", "8000"))
    
    logger.info("="*60)
    logger.info("Tyler Playground API Server")
    logger.info("="*60)
    logger.info(f"Agent: {AGENT_CONFIG['name']} ({AGENT_CONFIG['model_name']})")
    logger.info(f"Server: http://{host}:{port}")
    logger.info(f"Health check: http://{host}:{port}/health")
    logger.info("="*60)
    
    uvicorn.run(
        "playground_server:app",
        host=host,
        port=port,
        log_level="info",
        reload=False  # Disable reload to prevent double initialization
    )

