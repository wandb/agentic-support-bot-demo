#!/usr/bin/env python3
"""
Run evaluation of the W&B support bot using Weave's EvaluationLogger.

This script:
1. Loads the published dataset from Weave
2. Invokes the agent for each test case
3. Applies scorers (tool usage, accuracy, safety)
4. Logs all results to Weave for analysis

Usage:
    uv run python examples/step-4-complete/run_evaluation.py
    
    # Run on a sample for testing:
    uv run python examples/step-4-complete/run_evaluation.py --sample 10

Cost Warning:
    Using W&B Inference with Llama is often free or very low cost.
    Use --sample to test on a smaller subset first.
"""

import os
import sys
import argparse
import asyncio
import random
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

import weave
from weave import EvaluationLogger
from tyler import Agent, Thread, Message

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from scorers import tool_usage_scorer, accuracy_scorer, safety_scorer


# ====================
# Agent Invocation Utility
# ====================

def create_agent_from_config(config_path: str) -> Agent:
    """
    Create an agent from a tyler-chat-config.yaml file.
    
    Uses the new Agent.from_config() helper from Slide 4.2.0.
    
    Args:
        config_path: Path to the YAML config file
        
    Returns:
        Tyler Agent instance
    """
    # Use new Agent.from_config() helper - much simpler!
    agent = Agent.from_config(config_path)
    return agent


async def invoke_agent(agent: Agent, query: str) -> dict[str, Any]:
    """
    Invoke the agent with a single query and return structured output.
    
    Args:
        agent: Tyler Agent instance
        query: User's question/request
        
    Returns:
        dict with:
            - response: Agent's text response
            - tools_used: List of tool names that were called
            - metadata: Additional execution metadata
    """
    # Create thread with user message
    thread = Thread()
    message = Message(role="user", content=query)
    thread.add_message(message)
    
    # Run agent (non-streaming for evaluation)
    try:
        result = await agent.run(thread)
        
        # Extract response text from AgentResult
        response_text = result.content if result.content else ""
        
        # Extract tools used from thread
        tools_used = []
        tool_usage = result.thread.get_tool_usage()
        if tool_usage and tool_usage.get('tools'):
            tools_used = list(tool_usage['tools'].keys())
        
        return {
            "response": response_text,
            "tools_used": tools_used,
            "metadata": {
                "success": True,
                "error": None
            }
        }
        
    except Exception as e:
        # If agent fails, return error
        return {
            "response": f"[Error: Agent failed - {str(e)}]",
            "tools_used": [],
            "metadata": {
                "success": False,
                "error": str(e)
            }
        }


# ====================
# Evaluation Execution
# ====================

async def run_evaluation(
    dataset_name: str = "support-bot-eval-dataset",
    agent_name: str = None,
    agent_config_path: str = "workspace/step-4/tyler-chat-config.yaml",
    sample_size: int = None,
    use_llm_judges: bool = True
):
    """
    Run the full evaluation using EvaluationLogger.
    
    Args:
        dataset_name: Name of the dataset in Weave
        agent_name: Name of agent in Weave to evaluate (e.g. "Buzz"). 
                   Will try to load "{agent_name}:latest" from Weave.
                   Can include version tag (e.g. "Buzz:v2").
                   If not provided, loads from config file instead.
        agent_config_path: Path to config file (fallback if agent_name not in Weave)
        sample_size: If set, evaluate only this many random cases (for testing)
        use_llm_judges: Whether to use LLM judge scorers (costs money)
    """
    print("=" * 70)
    print("W&B Support Bot Evaluation")
    print("=" * 70)
    print()
    
    # Load environment variables
    load_dotenv()
    
    # Check API key
    if not os.getenv("WANDB_API_KEY"):
        print("❌ Error: WANDB_API_KEY not set")
        print("Please set your W&B API key in .env or environment")
        sys.exit(1)
    
    # Initialize Weave (must be before EvaluationLogger for token tracking!)
    weave_project = os.getenv("WANDB_PROJECT", "agentic-support-bot-demo")
    print("Initializing Weave...")
    weave.init(weave_project)
    print(f"✓ Connected to Weave project: {weave_project}")
    print()
    
    # Load agent - try Weave first if agent_name provided, fall back to config
    if agent_name:
        print(f"Attempting to load agent '{agent_name}' from Weave...")
        # If agent_name doesn't include version, append :latest
        agent_ref_name = agent_name if ':' in agent_name else f"{agent_name}:latest"
        try:
            agent_ref = weave.ref(agent_ref_name)
            agent = agent_ref.get()
            print(f"✓ Loaded agent from Weave: {agent.name}")
            print(f"✓ Agent version: {agent_ref.uri()}")
        except Exception as e:
            print(f"⚠️  Could not load '{agent_ref_name}' from Weave: {e}")
            print(f"   Falling back to config file: {agent_config_path}")
            agent = create_agent_from_config(agent_config_path)
            print(f"✓ Agent created from config: {agent.name}")
    else:
        print(f"Loading agent from config: {agent_config_path}")
        agent = create_agent_from_config(agent_config_path)
        print(f"✓ Agent created from config: {agent.name}")
        print(f"💡 Tip: Use --agent-name '{agent.name}' to evaluate the Weave-tracked version")
    
    print()
    
    # Load dataset from Weave
    print(f"Loading dataset: {dataset_name}")
    try:
        dataset_ref = weave.ref(f"{dataset_name}:latest")
        dataset = dataset_ref.get()
        # Convert rows to dictionaries for easier access
        test_cases = [dict(row) for row in dataset.rows]
        print(f"✓ Loaded {len(test_cases)} test cases")
        print(f"✓ Dataset version: {dataset_ref.uri()}")
    except Exception as e:
        print(f"❌ Failed to load dataset: {e}")
        print()
        print("Make sure you've published the dataset first:")
        print("  uv run python examples/step-4-complete/publish_dataset.py")
        sys.exit(1)
    
    # Sample if requested
    if sample_size and sample_size < len(test_cases):
        print(f"\n⚠️  Sampling {sample_size} random cases for testing")
        test_cases = random.sample(test_cases, sample_size)
        print(f"✓ Sample selected: {len(test_cases)} cases")
    
    print()
    
    # Cost info
    if use_llm_judges:
        print("📊 Evaluation Info")
        print(f"Running evaluation with LLM judges on {len(test_cases)} cases")
        print(f"Using Llama-3.1-8B via W&B Inference (often free or low cost)")
        print()
    
    # Initialize EvaluationLogger BEFORE making LLM calls (for token tracking)
    print("Initializing EvaluationLogger...")
    eval_logger = EvaluationLogger(
        name="support-bot-eval",
        model=agent.name,  # References the Weave-tracked Agent object
        dataset=dataset  # Pass the loaded Dataset object to reference existing dataset
    )
    print("✓ EvaluationLogger initialized")
    print()
    
    # Run evaluation
    print("=" * 70)
    print(f"Running Evaluation ({len(test_cases)} cases)")
    print("=" * 70)
    print()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"[{i}/{len(test_cases)}] Evaluating: {test_case['input'][:60]}...")
        
        # Invoke agent
        try:
            output = await invoke_agent(agent, test_case["input"])
        except Exception as e:
            print(f"  ❌ Agent invocation failed: {e}")
            continue
        
        # Log prediction
        pred_logger = eval_logger.log_prediction(
            inputs={"query": test_case["input"]},
            output=output
        )
        
        # Apply scorers
        # 1. Tool usage scorer (always run - it's free and fast)
        try:
            tool_score = tool_usage_scorer(test_case, output)
            pred_logger.log_score(scorer="tool_usage", score=tool_score)
            print(f"  ✓ Tool usage: {tool_score.get('score', 0):.2f}")
        except Exception as e:
            print(f"  ⚠️  Tool scorer failed: {e}")
        
        # 2. Accuracy scorer (LLM judge - costs money)
        if use_llm_judges:
            try:
                accuracy_score = await accuracy_scorer(test_case, output)
                pred_logger.log_score(scorer="accuracy", score=accuracy_score)
                acc = accuracy_score.get('accuracy', 0)
                print(f"  ✓ Accuracy: {acc:.2f}")
            except Exception as e:
                print(f"  ⚠️  Accuracy scorer failed: {e}")
        
        # 3. Safety scorer (LLM judge - costs money)
        if use_llm_judges:
            try:
                safety_score = await safety_scorer(test_case, output)
                pred_logger.log_score(scorer="safety", score=safety_score)
                safety = safety_score.get('overall_safety', 0)
                print(f"  ✓ Safety: {safety:.2f}")
            except Exception as e:
                print(f"  ⚠️  Safety scorer failed: {e}")
        
        # Finish this prediction
        pred_logger.finish()
        print()
    
    # Log summary
    print("=" * 70)
    print("Finalizing Evaluation")
    print("=" * 70)
    
    eval_logger.log_summary({
        "total_cases": len(test_cases),
        "use_llm_judges": use_llm_judges
    })
    
    print("✓ Evaluation complete!")
    print()
    print("=" * 70)
    print("View Results in Weave UI:")
    print("=" * 70)
    print("1. Navigate to: https://wandb.ai/")
    print(f"2. Open project: {weave_project}")
    print("3. Click 'Evals' tab to see this evaluation")
    print("4. Click into the eval to see per-prediction scores")
    print("5. Compare multiple eval runs side-by-side")
    print()


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Run W&B support bot evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate the latest version of agent "Buzz" from Weave (recommended)
  python run_evaluation.py --agent-name Buzz
  
  # Evaluate a specific version from Weave
  python run_evaluation.py --agent-name Buzz:v3
  
  # Evaluate from config file (creates new agent instance)
  python run_evaluation.py --config workspace/step-4/tyler-chat-config.yaml
  
  # Test on 10 random cases first
  python run_evaluation.py --agent-name Buzz --sample 10
  
  # Run without LLM judges (only tool correctness)
  python run_evaluation.py --agent-name Buzz --no-llm-judges
        """
    )
    
    parser.add_argument(
        "--agent-name",
        help="Name of agent in Weave to evaluate (e.g. 'Buzz' loads 'Buzz:latest'). "
             "Can include version tag (e.g. 'Buzz:v2'). "
             "If not provided, loads from --config instead."
    )
    
    parser.add_argument(
        "--config",
        default="workspace/step-4/tyler-chat-config.yaml",
        help="Path to agent config file (default: workspace/step-4/tyler-chat-config.yaml). "
             "Used when --agent-name is not provided."
    )
    
    parser.add_argument(
        "--sample",
        type=int,
        help="Number of random cases to evaluate (for testing)"
    )
    
    parser.add_argument(
        "--no-llm-judges",
        action="store_true",
        help="Skip LLM judge scorers (saves money, only runs tool scorer)"
    )
    
    parser.add_argument(
        "--dataset",
        default="support-bot-eval-dataset",
        help="Name of dataset in Weave (default: support-bot-eval-dataset)"
    )
    
    args = parser.parse_args()
    
    # Run the async evaluation
    asyncio.run(run_evaluation(
        dataset_name=args.dataset,
        agent_name=args.agent_name,
        agent_config_path=args.config,
        sample_size=args.sample,
        use_llm_judges=not args.no_llm_judges
    ))


if __name__ == "__main__":
    main()

