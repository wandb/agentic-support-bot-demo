#!/usr/bin/env python3
"""
Publish a new agent version to Weave using the updated Tyler package.

This creates a new agent and saves it to Weave, allowing us to test
the serialization fix.

Run with:
    cd examples/step-6
    uv run python publish_agent.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def main():
    print("="*60)
    print("Publishing New Agent to Weave")
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
    
    # Create a fresh agent with the updated Tyler
    from tyler import Agent
    
    print("Creating new agent with updated Tyler (5.2.2)...")
    
    # Use config from workspace/step-4 as base
    config_path = Path(__file__).parent.parent.parent / "workspace/step-4/tyler-chat-config.yaml"
    
    if config_path.exists():
        print(f"Loading config from: {config_path}")
        # Change to config dir for relative paths
        original_cwd = os.getcwd()
        os.chdir(config_path.parent)
        try:
            agent = Agent.from_config(str(config_path))
        finally:
            os.chdir(original_cwd)
    else:
        # Create minimal agent if no config
        print("Creating minimal test agent...")
        agent = Agent(
            name="TestAgent",
            model_name="gpt-4.1",
            purpose="A test agent to verify Weave serialization.",
            notes="",
            temperature=0.7,
        )
    
    print(f"✓ Agent created: {agent.name}")
    print(f"  Model: {agent.model_name}")
    print(f"  Tools: {len(agent.tools) if hasattr(agent, 'tools') and agent.tools else 0}")
    print()
    
    # Publish to Weave (this happens automatically when agent is used with Weave)
    # But we can explicitly save it by using weave.publish
    print("Publishing agent to Weave...")
    ref = weave.publish(agent, name=agent.name)
    print(f"✓ Agent published!")
    print(f"  Ref: {ref.uri()}")
    print()
    
    print("="*60)
    print(f"Now test with: python test_weave_agent.py")
    print(f"Update test_weave_agent.py to use: {agent.name}:latest")
    print("="*60)

if __name__ == "__main__":
    main()

