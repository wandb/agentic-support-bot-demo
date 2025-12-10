"""
Local server runner for Step 6 - bypasses Modal for local testing.

Run with:
    cd examples/step-6
    uv run python run_local.py

Then test with:
    curl http://localhost:8000/health
    curl -X POST http://localhost:8000/v1/chat/completions \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer test-key" \
      -d '{"model": "test", "messages": [{"role": "user", "content": "Hello!"}]}'
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

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
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


# ============================================================================
# Agent Loading from Weave Config
# ============================================================================

def load_config_ref(config_path: str = "config.json") -> str:
    """Load config reference from JSON file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"\n{'='*70}\n"
            f"❌ Config file not found at: {config_path}\n\n"
            f"Please create config.json with your config reference:\n"
            f'{{"config_ref": "YourAgentName:latest"}}\n\n'
            f"{'='*70}\n"
        )
    
    with open(config_path) as f:
        config = json.load(f)
    
    if "config_ref" not in config:
        raise ValueError("config.json must contain 'config_ref' field")
    
    return config["config_ref"]


def load_agent(config_json_path: str = "config.json") -> tuple[Agent, str]:
    """
    Load Tyler agent by fetching config YAML from Weave.
    
    The config YAML is stored in Weave as an AgentConfig object.
    This function fetches the YAML, writes it to disk, and creates
    the Tyler Agent using Agent.from_config().
    """
    # Check for WANDB_API_KEY
    if not os.getenv("WANDB_API_KEY"):
        raise ValueError(
            "WANDB_API_KEY not set. Required to load config from Weave.\n"
            "Set it in your environment or .env file."
        )
    
    # Initialize Weave
    try:
        project = os.getenv("WANDB_PROJECT", "agentic-support-bot-demo")
        weave.init(project)
        logger.info(f"📊 Weave initialized: project={project}")
    except Exception as e:
        logger.warning(f"Weave initialization failed: {e}")
        raise
    
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
        
        # Write YAML to current directory where tools.py exists
        config_path = Path("tyler-chat-config.yaml")
        config_path.write_text(yaml_content)
        logger.info(f"📝 Config written to {config_path}")
        
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


# Global variables
AGENT = None
CONFIG_REF = None
ENV = "local"


# ============================================================================
# SSE Serialization
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
                
                thinking_text = None
                if hasattr(delta, 'thinking') and delta.thinking:
                    thinking_text = delta.thinking
                elif hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    thinking_text = delta.reasoning_content
                
                if thinking_text:
                    choice_dict["delta"]["thinking"] = thinking_text
                    choice_dict["delta"]["reasoning_content"] = thinking_text
                
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


# ============================================================================
# Authentication (simplified for local testing)
# ============================================================================

def verify_api_key(authorization: Optional[str] = None) -> None:
    """Verify API key - simplified for local testing."""
    # Skip auth for local testing if no key is configured
    expected_key = os.getenv("AGENTIC_SUPPORT_BOT_API_KEY")
    if not expected_key:
        logger.info("No AGENTIC_SUPPORT_BOT_API_KEY set - skipping auth for local testing")
        return
    
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    
    api_key = authorization[7:]
    
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
    """Manage agent lifecycle."""
    global AGENT, CONFIG_REF, ENV
    
    try:
        logger.info("="*60)
        logger.info("Tyler Playground API Server (LOCAL)")
        logger.info("="*60)
        
        AGENT, CONFIG_REF = load_agent()
        
        # Connect to MCP servers if the agent has them configured
        if hasattr(AGENT, 'mcp_config') and AGENT.mcp_config:
            try:
                logger.info("Connecting to MCP servers...")
                await AGENT.connect_mcp()
                logger.info("✓ MCP servers connected")
            except Exception as e:
                logger.warning(f"MCP connection failed: {e}")
        
        logger.info("="*60)
        logger.info(f"✅ Server ready at http://localhost:8000")
        logger.info(f"   Agent: {AGENT.name} (config: {CONFIG_REF})")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        raise
    
    yield
    
    if AGENT and hasattr(AGENT, 'mcp_config') and AGENT.mcp_config:
        try:
            await AGENT.cleanup()
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")


# ============================================================================
# FastAPI Application
# ============================================================================

web_app = FastAPI(
    title="Tyler Playground API (Local)",
    description="Local testing server for Step 6",
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
        environment=ENV,
        agent_name=AGENT.name if AGENT else None,
        config_ref=CONFIG_REF,
        model=AGENT.model_name if AGENT else None
    )


@web_app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Tyler Playground API (Local)",
        "environment": ENV,
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
    """OpenAI-compatible chat completions endpoint."""
    verify_api_key(authorization)
    
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages array cannot be empty")
    
    logger.info(f"POST /v1/chat/completions (messages={len(request.messages)}, config={CONFIG_REF})")
    
    try:
        thread = convert_to_tyler_thread(request.messages)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid message format: {e}")
    
    async def generate() -> AsyncGenerator[str, None]:
        """Generate SSE stream from Tyler agent."""
        try:
            async for chunk in AGENT.stream(thread, mode="raw"):
                yield serialize_chunk_to_sse(chunk)
            
            yield "data: [DONE]\n\n"
            logger.info("Request completed")
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            error_chunk = {"error": {"message": str(e), "type": "server_error"}}
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "run_local:web_app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
