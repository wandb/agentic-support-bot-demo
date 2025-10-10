"""Agentic support bot powered by Tyler agent."""

import os
from dotenv import load_dotenv
import weave
from tyler import Agent, Thread, Message
from tools import get_tools


def validate_environment() -> None:
    """
    Validate that all required environment variables are present.
    
    Raises:
        ValueError: If any required environment variable is missing.
    """
    required_vars = ["WANDB_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(
            f"Missing required environment variable(s): {', '.join(missing_vars)}. "
            f"Please set them in your .env file or environment."
        )

def main():
    """Main entry point for the support bot agent."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Validate environment
    validate_environment()
    print("✓ Environment validated")
    
    # Initialize Weave for observability
    weave.init("agentic-support-bot-demo")
    
    # Create Tyler agent with custom tools
    # Get custom tools
    tools = get_tools()
    
    # Create Weave Prompt for agent purpose
    purpose_prompt = weave.StringPrompt(
        "You are a helpful support bot assistant that helps users manage support issues. "
        "You can create new issues and retrieve existing ones. "
        "Always be friendly, clear, and helpful in your responses."
    )
    
    agent = Agent(
        name="support-bot",
        model_name="gpt-4.1",
        purpose=purpose_prompt,
        tools=tools
    )

    # Create thread and message
    thread = Thread()
    message = Message(
        role="user",
        content=(
            "Please help me with the following: "
            "1. Create a new issue titled 'API Response Timeout' with description "
            "'Users are experiencing timeouts when calling the /api/data endpoint' "
            "and priority 'high'. "
            "2. Then retrieve issue #123 to show me its details."
        )
    )
    thread.add_message(message)
    
    print("\n" + "="*60)
    print("DEMO: Agent Execution with Tool Usage (Streaming)")
    print("="*60)
    print(f"\nUser: {message.content}\n")
    
    # Execute agent with streaming
    import asyncio
    from tyler.models.execution import EventType
    
    async def run_with_streaming():
        print("Assistant: ", end="", flush=True)
        
        async for event in agent.go(thread, stream=True):
            if event.type == EventType.LLM_STREAM_CHUNK:
                # Stream LLM response chunks
                chunk = event.data.get("content_chunk", "")
                print(chunk, end="", flush=True)
            
            elif event.type == EventType.TOOL_SELECTED:
                # Show when tools are being used
                tool_name = event.data.get("tool_name", "")
                print(f"\n\n[🔧 Using tool: {tool_name}]", flush=True)
            
            elif event.type == EventType.TOOL_RESULT:
                # Show tool completion
                tool_name = event.data.get("tool_name", "")
                print(f"\n[✓ Tool completed: {tool_name}]\n", flush=True)
        
        print("\n")
    
    asyncio.run(run_with_streaming())
    
    print("="*60)
    print("\n✓ Demo completed successfully!")


if __name__ == "__main__":
    main()
