#!/usr/bin/env python3
"""
Quick test to verify Weave-loaded agents have working tools.

Run with:
    cd examples/step-6
    uv run python test_weave_agent.py

This will:
1. Load Buzz:v10 from Weave
2. Ask about a ticket status
3. Print the response and tool usage

Check your Weave traces to see if tools were called successfully!
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def main():
    print("="*60)
    print("Weave Agent Tool Serialization Test")
    print("="*60)
    print()
    
    # Check for WANDB_API_KEY
    if not os.getenv("WANDB_API_KEY"):
        print("❌ WANDB_API_KEY not set")
        sys.exit(1)
    
    # Initialize Weave
    import weave
    project = os.getenv("WANDB_PROJECT", "agentic-support-bot-demo")
    print(f"Initializing Weave: {project}")
    weave.init(project)
    print("✓ Weave initialized")
    print()
    
    # Load agent DIRECTLY from Weave (testing the serialization fix)
    agent_ref = "Frank:latest"  # Published with Tyler 5.2.2
    print(f"Loading agent directly from Weave: {agent_ref}")
    try:
        # Direct load - no reconstruction!
        agent = weave.ref(agent_ref).get()
        print(f"✓ Agent loaded directly: {agent.name}")
        print(f"  Model: {agent.model_name}")
        print(f"  Purpose: {agent.purpose[:100]}..." if len(agent.purpose) > 100 else f"  Purpose: {agent.purpose}")
        
        # Check if logger is properly initialized
        print()
        print("Checking logger serialization fix:")
        if hasattr(agent, 'logger'):
            import logging
            if isinstance(agent.logger, logging.Logger):
                print(f"  ✓ Logger is a proper Logger object: {agent.logger.name}")
            else:
                print(f"  ❌ Logger is NOT a Logger object: {type(agent.logger)} = {agent.logger}")
        else:
            print("  ⚠️ Agent has no logger attribute")
        
    except Exception as e:
        print(f"❌ Failed to load agent: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Check what tools the agent has
    print()
    print("Checking agent tools:")
    if hasattr(agent, 'tools') and agent.tools:
        print(f"  ✓ Agent has {len(agent.tools)} tools")
    
    # Test a query that should trigger get_issue tool
    print()
    print("="*60)
    print("Testing tool call: asking about ticket #10234")
    print("="*60)
    print()
    
    from tyler import Thread, Message
    
    thread = Thread()
    thread.add_message(Message(role="user", content="What's the status of ticket #10234?"))
    
    print("Running agent...")
    try:
        result = await agent.run(thread)
        
        print()
        print("Response:")
        print("-"*40)
        print(result.content if result.content else "(no content)")
        print("-"*40)
        
        # Check for tool usage
        print()
        print("Tool usage:")
        tool_usage = result.thread.get_tool_usage()
        if tool_usage and tool_usage.get('tools'):
            for tool_name, usage in tool_usage['tools'].items():
                print(f"  ✓ {tool_name}: called {usage.get('call_count', 0)} time(s)")
        else:
            print("  ⚠️ No tools were called")
        
        print()
        print("="*60)
        print("Test complete! Check Weave traces for details:")
        print(f"https://wandb.ai/{project}/weave")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Agent run failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

