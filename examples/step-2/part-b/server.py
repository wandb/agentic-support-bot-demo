"""
Universal server for Tyler agent.

Works in multiple contexts:
- Step 2: Local development with ngrok (OpenAI endpoint for Weave Playground)
- Step 5: Production deployment on Modal with Slack integration

The same server file works for both - it detects the environment and adapts.
"""

import argparse
import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import List, Literal, Optional, AsyncGenerator

import yaml
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import weave
from tyler import Agent, Thread, Message

# Optional dependencies
try:
    import modal
    MODAL_AVAILABLE = True
except ImportError:
    MODAL_AVAILABLE = False
    modal = None

try:
    from slack_bolt.async_app import AsyncApp
    from slack_sdk.errors import SlackApiError
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False
    AsyncApp = None
    SlackApiError = None

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

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
    timestamp: Optional[str] = None
    agent_name: Optional[str] = None
    model: Optional[str] = None


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
    
    # Use Agent.from_config() helper from Slide
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
            "Please ensure tyler-chat-config.yaml is in the workspace directory."
        )
    except Exception as e:
        logger.error(f"Failed to load agent: {e}")
        raise ValueError(f"Failed to initialize agent from config: {e}")


# Global agent variables
AGENT = None
CONFIG = None
AGENT_CONFIG = None

# Slack app (initialized if SLACK_BOT_TOKEN is available in Step 5)
SLACK_APP = None

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
            
            # Extract delta
            if hasattr(choice, 'delta'):
                delta = choice.delta
                
                if hasattr(delta, 'content') and delta.content:
                    choice_dict["delta"]["content"] = delta.content
                
                if hasattr(delta, 'role') and delta.role:
                    choice_dict["delta"]["role"] = delta.role
                
                # Handle thinking/reasoning tokens
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
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'"
        )
    
    api_key = authorization[7:]  # Remove "Bearer " prefix
    
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


def verify_slack_signature(
    body: bytes,
    timestamp: str,
    signature: str
) -> bool:
    """
    Verify Slack request signature (Step 5 only).
    
    Args:
        body: Raw request body bytes
        timestamp: X-Slack-Request-Timestamp header
        signature: X-Slack-Signature header
        
    Returns:
        True if signature is valid, False otherwise
    """
    signing_secret = os.getenv("SLACK_SIGNING_SECRET")
    if not signing_secret:
        logger.error("SLACK_SIGNING_SECRET not configured")
        return False
    
    # Check timestamp to prevent replay attacks
    current_timestamp = int(time.time())
    if abs(current_timestamp - int(timestamp)) > 60 * 5:  # 5 minutes
        logger.warning("Slack request timestamp too old")
        return False
    
    # Compute expected signature
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    expected_signature = 'v0=' + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison
    return hmac.compare_digest(expected_signature, signature)


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
# Slack Event Processing (Step 5 only)
# ============================================================================

async def process_slack_event(event: dict) -> None:
    """
    Process Slack app_mention event asynchronously.
    
    Called from background task to avoid Slack's 3-second timeout.
    
    Args:
        event: Slack event dictionary
    """
    try:
        # Extract message details
        channel = event.get("channel")
        text = event.get("text", "")
        thread_ts = event.get("thread_ts") or event.get("ts")
        
        # Remove bot mention from text
        # Slack sends: "@BotName help me" -> we want: "help me"
        text_clean = " ".join(
            word for word in text.split() 
            if not word.startswith("<@")
        ).strip()
        
        if not text_clean:
            text_clean = "Hello! How can I help you?"
        
        logger.info(f"Processing Slack message: channel={channel}, text='{text_clean[:50]}...'")
        
        # Create Tyler thread with user message
        thread = Thread()
        thread.add_message(Message(role="user", content=text_clean))
        
        # Invoke agent (this will be traced by Weave)
        logger.info("Invoking Tyler agent...")
        response_text = ""
        async for chunk in AGENT.stream(thread, mode="text"):
            response_text += chunk
        
        logger.info(f"Agent response length: {len(response_text)} chars")
        
        # Post response to Slack
        if SLACK_APP:
            try:
                await SLACK_APP.client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=response_text
                )
                logger.info("Response posted to Slack successfully")
            except SlackApiError as e:
                logger.error(f"Slack API error: {e.response['error']}")
        else:
            logger.error("Slack app not initialized")
        
    except Exception as e:
        logger.error(f"Error processing Slack event: {e}", exc_info=True)
        
        # Try to post error message to Slack
        if SLACK_APP and channel:
            try:
                await SLACK_APP.client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=f"Sorry, I encountered an error: {str(e)}\nCheck the Weave traces for details."
                )
            except Exception as post_error:
                logger.error(f"Failed to post error message to Slack: {post_error}")


# ============================================================================
# Lifecycle Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage agent and MCP connections during app lifespan."""
    global AGENT, CONFIG, AGENT_CONFIG, SLACK_APP
    
    # Startup: Load agent
    logger.info("Starting up server...")
    
    try:
        # Load agent configuration
        config_path = os.getenv("TYLER_CONFIG", "tyler-chat-config.yaml")
        AGENT, CONFIG = load_agent(config_path)
        AGENT_CONFIG = CONFIG.get("agent", CONFIG)
        
        # Connect to MCP servers
        if CONFIG.get("mcp"):
            try:
                logger.info("Connecting to MCP servers...")
                await AGENT.connect_mcp()
                logger.info("✓ MCP servers connected successfully")
            except Exception as e:
                logger.error(f"Failed to connect to MCP servers: {e}")
                logger.warning("Continuing without MCP integration")
        
        # Initialize Slack app if credentials available (Step 5)
        if SLACK_AVAILABLE and os.getenv("SLACK_BOT_TOKEN"):
            logger.info("Initializing Slack integration...")
            SLACK_APP = AsyncApp(token=os.getenv("SLACK_BOT_TOKEN"))
            logger.info("✓ Slack app initialized")
        else:
            logger.info("Slack integration not configured (SLACK_BOT_TOKEN not set)")
        
        logger.info("✓ Server startup complete")
        
    except Exception as e:
        logger.error(f"Fatal error during startup: {e}")
        raise
    
    yield
    
    # Shutdown: Cleanup
    logger.info("Shutting down server...")
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
    title="Tyler API Server",
    description="Universal server for Tyler support bot (Local/Modal, Playground/Slack)",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    response = HealthResponse(
        status="healthy",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    )
    
    # Include agent info if available
    if AGENT_CONFIG:
        response.agent_name = AGENT_CONFIG.get("name")
        response.model = AGENT_CONFIG.get("model_name")
    
    return response


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "message": "Tyler API Server",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "chat_completions": "/v1/chat/completions",
            "slack_events": "/slack/events"
        }
    }


@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    authorization: Optional[str] = Header(None)
):
    """
    OpenAI-compatible chat completions endpoint.
    
    Used by Weave Playground in Step 2 and Step 5.
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
    
    logger.info(f"POST /v1/chat/completions (messages={len(request.messages)})")
    
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
            
            yield "data: [DONE]\n\n"
            logger.info("Request completed")
            
        except Exception as e:
            logger.error(f"Error during streaming: {e}")
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
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/slack/events")
async def slack_events(request: Request):
    """
    Slack event webhook endpoint (Step 5 only).
    
    Handles app_mention events from Slack workspace.
    Verifies request signature and processes events asynchronously.
    """
    # Get raw body for signature verification
    body = await request.body()
    
    # Verify Slack signature
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    
    if not verify_slack_signature(body, timestamp, signature):
        logger.warning("Invalid Slack signature")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse JSON body
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Handle URL verification challenge
    if payload.get("type") == "url_verification":
        logger.info("Slack URL verification challenge received")
        return JSONResponse({"challenge": payload.get("challenge")})
    
    # Handle event callback
    if payload.get("type") == "event_callback":
        event = payload.get("event", {})
        event_type = event.get("type")
        
        logger.info(f"Slack event received: type={event_type}")
        
        # Only handle app_mention events
        if event_type == "app_mention":
            # Acknowledge immediately (within 3 seconds)
            # Process event in background to avoid timeout
            asyncio.create_task(process_slack_event(event))
            return JSONResponse({"ok": True})
        else:
            logger.info(f"Ignoring event type: {event_type}")
            return JSONResponse({"ok": True})
    
    # Unknown event type
    logger.warning(f"Unknown Slack event type: {payload.get('type')}")
    return JSONResponse({"ok": True})


# ============================================================================
# Modal Deployment Configuration (Step 5 only)
# ============================================================================

if MODAL_AVAILABLE:
    # Create Modal image with all dependencies
    image = modal.Image.debian_slim(python_version="3.12").pip_install(
        "fastapi",
        "uvicorn",
        "pydantic",
        "python-dotenv",
        "pyyaml",
        "weave",
        "tyler",
        "slack-bolt",
        "slack-sdk",
    )
    
    # Create Modal app
    modal_app = modal.App("tyler-production-server", image=image)
    
    # Deploy FastAPI app to Modal
    @modal_app.function(
        secrets=[
            modal.Secret.from_name("wandb-secrets"),  # WANDB_API_KEY, PLAYGROUND_API_KEY
            modal.Secret.from_name("slack-secrets", required=False),  # SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET (optional)
        ],
        timeout=300,  # 5 minute timeout for long agent calls
        allow_concurrent_inputs=10,  # Handle multiple requests
    )
    @modal.asgi_app()
    def fastapi_app():
        """Modal ASGI wrapper for FastAPI app."""
        return app


# ============================================================================
# Local Development with ngrok (Step 2)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    import pathlib
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # Try to import ngrok (Step 2)
    try:
        import ngrok as ngrok_lib
        NGROK_AVAILABLE = True
    except ImportError:
        NGROK_AVAILABLE = False
        ngrok_lib = None
    
    # Default config path is in the workspace directory
    workspace_dir = pathlib.Path(__file__).parent
    default_config_path = str(workspace_dir / "tyler-chat-config.yaml")
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Tyler API Server - Works locally (Step 2) or on Modal (Step 5)"
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
        default=os.getenv("SERVER_HOST", "0.0.0.0"),
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("SERVER_PORT", "8000")),
        help="Port to bind the server to (default: 8000)"
    )
    parser.add_argument(
        "--no-ngrok",
        action="store_true",
        help="Disable ngrok tunnel (useful for Modal deployment testing)"
    )
    args = parser.parse_args()
    
    # Validate required environment variables
    if not os.getenv("PLAYGROUND_API_KEY"):
        logger.error("PLAYGROUND_API_KEY environment variable is required")
        logger.error("Please set it in your .env file or environment")
        raise ValueError("Missing required environment variable: PLAYGROUND_API_KEY")
    
    # Load the agent with the specified config
    try:
        AGENT, CONFIG = load_agent(args.config)
        AGENT_CONFIG = CONFIG.get("agent", CONFIG)
    except Exception as e:
        logger.error(f"Failed to load agent with config {args.config}: {e}")
        raise
    
    # Set up ngrok tunnel if available and not disabled
    tunnel_url = None
    if NGROK_AVAILABLE and not args.no_ngrok:
        if not os.getenv("NGROK_AUTHTOKEN"):
            logger.warning("NGROK_AUTHTOKEN not set - skipping ngrok tunnel")
            logger.warning("Server will only be accessible locally")
        else:
            logger.info("Setting up ngrok tunnel...")
            try:
                listener = ngrok_lib.forward(args.port, authtoken_from_env=True)
                tunnel_url = listener.url()
                logger.info(f"✓ Ngrok tunnel established: {tunnel_url}")
            except Exception as e:
                logger.error(f"Failed to create ngrok tunnel: {e}")
                logger.warning("Continuing without ngrok - server only accessible locally")
    
    logger.info("="*60)
    logger.info("Tyler API Server")
    logger.info("="*60)
    logger.info(f"Config: {args.config}")
    logger.info(f"Agent: {AGENT_CONFIG['name']} ({AGENT_CONFIG['model_name']})")
    logger.info(f"Local server: http://{args.host}:{args.port}")
    logger.info(f"Health check: http://{args.host}:{args.port}/health")
    logger.info(f"Authentication: Required (Bearer token)")
    if tunnel_url:
        logger.info(f"Ngrok tunnel: {tunnel_url}")
    logger.info("="*60)
    
    if tunnel_url:
        print("\n" + "="*60)
        print("🌐 NGROK TUNNEL ACTIVE")
        print(f"   Use this Base URL in Weave Playground: {tunnel_url}/v1")
        print("="*60 + "\n")
    
    uvicorn.run(
        "server:app",
        host=args.host,
        port=args.port,
        log_level="info",
        reload=False  # Disable reload to prevent double initialization
    )

