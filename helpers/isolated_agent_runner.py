#!/usr/bin/env python3
"""
Isolated Agent Runner - Helper script for running Tyler Agent in fresh process context.

This script is designed to be called via subprocess from environments like Marimo notebooks
where the execution context persists across multiple invocations. Running the agent in a
separate process ensures that each agent call creates a new root Weave trace instead of
nesting under a parent context.

Usage:
    python helpers/isolated_agent_runner.py < input.json

Input (stdin JSON):
    {
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ],
        "config_path": "/path/to/tyler-chat-config.yaml",
        "object_name": "BasicAgentConfig"  # Optional, defaults to "AgentConfig"
    }

Output (stdout, newline-delimited JSON):
    {"content": "Hello"}
    {"content": " there"}
    {"content": "!"}
    {"error": "error message"}  # Only if error occurs

Exit codes:
    0 - Success
    1 - Error (see stderr for details)
"""
import sys
import json
import os
import asyncio
from pathlib import Path


async def run_agent_stream(messages: list[dict], config_path: str, object_name: str = "AgentConfig"):
    """
    Load agent and stream response to stdout as JSON lines.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        config_path: Path to Tyler agent config YAML file
        object_name: Weave object name for config versioning (e.g., "BasicAgentConfig")
        
    Yields:
        Content chunks as they're generated
    """
    try:
        # Initialize Weave in this fresh process (creates new root trace context)
        import weave
        import yaml
        project = os.getenv("WANDB_PROJECT", "agentic-support-bot-demo")
        weave.init(project)
        
        # Change to config directory so relative paths work
        config_path = Path(config_path).absolute()
        config_dir = config_path.parent
        original_cwd = os.getcwd()
        os.chdir(config_dir)
        
        try:
            # Load and publish config to Weave before running agent
            # This creates a version only when config is actually used
            config_ref = None
            config_ref_uri = None
            try:
                # Ensure helpers directory is in path for import
                # The subprocess might run from a different directory
                import sys
                helpers_path = Path(__file__).parent.absolute()
                if str(helpers_path.parent) not in sys.path:
                    sys.path.insert(0, str(helpers_path.parent))
                
                from helpers.marimo_helpers import publish_agent_config
                
                # Read config file
                with open(config_path) as f:
                    yaml_content = f.read()
                    config_data = yaml.safe_load(yaml_content)
                
                # Publish to Weave with specified object name
                agent_name = config_data.get("name", "agent")
                config_ref = publish_agent_config(agent_name, yaml_content, object_name)
                
                # Extract URI from ref for use in weave.attributes()
                # This creates a clickable link in Weave UI
                if config_ref and hasattr(config_ref, 'uri'):
                    config_ref_uri = config_ref.uri()
            except Exception as e:
                # Don't fail the whole request if publish fails
                print(json.dumps({"warning": f"Failed to publish config: {e}"}), flush=True)
            
            # Load Tyler agent from config
            from tyler import Agent, Thread, Message
            agent = Agent.from_config(str(config_path))
            
            # Convert messages to Tyler Thread
            thread = Thread()
            for msg in messages:
                thread.add_message(Message(role=msg["role"], content=msg["content"]))
            
            # Stream response with config_ref as trace attribute
            # This links the trace to the specific config version used
            if config_ref_uri:
                with weave.attributes({'config_ref': config_ref_uri}):
                    async for chunk in agent.stream(thread, mode="openai"):
                        if hasattr(chunk, 'choices') and chunk.choices:
                            for choice in chunk.choices:
                                if hasattr(choice, 'delta'):
                                    delta = choice.delta
                                    if hasattr(delta, 'content') and delta.content is not None:
                                        # Output as JSON line for parsing by parent process
                                        print(json.dumps({"content": delta.content}), flush=True)
            else:
                # Fallback without config_ref if publish failed
                async for chunk in agent.stream(thread, mode="openai"):
                    if hasattr(chunk, 'choices') and chunk.choices:
                        for choice in chunk.choices:
                            if hasattr(choice, 'delta'):
                                delta = choice.delta
                                if hasattr(delta, 'content') and delta.content is not None:
                                    print(json.dumps({"content": delta.content}), flush=True)
        
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
    
    except Exception as e:
        # Output error as JSON line (don't re-raise - main() would print it again)
        print(json.dumps({"error": str(e)}), flush=True)


def main():
    """Main entry point - read stdin, run agent, stream to stdout."""
    try:
        # Read input from stdin (JSON with messages and config path)
        input_data = json.loads(sys.stdin.read())
        messages = input_data.get("messages", [])
        config_path = input_data.get("config_path")
        object_name = input_data.get("object_name", "AgentConfig")
        
        if not messages:
            print(json.dumps({"error": "No messages provided"}), flush=True)
            sys.exit(1)
        
        if not config_path:
            print(json.dumps({"error": "No config_path provided"}), flush=True)
            sys.exit(1)
        
        # Run the agent streaming
        asyncio.run(run_agent_stream(messages, config_path, object_name))
        sys.exit(0)
    
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON input: {e}"}), flush=True)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Unexpected error: {e}"}), flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()


