#!/usr/bin/env python3
"""
Isolated Evaluation Runner - Helper script for running evaluations in fresh process context.

This script is designed to be called via subprocess from environments like Marimo notebooks
where the execution context persists across multiple invocations. Running the evaluation in a
separate process ensures a clean Weave context and avoids state conflicts.

Usage:
    python helpers/isolated_eval_runner.py < input.json

Input (stdin JSON):
    {
        "config_path": "/path/to/tyler-chat-config.yaml",
        "sample_size": 5,  # optional, runs full dataset if not specified
        "agent_name": "Buzz"  # optional, for logging
    }

Output (stdout, newline-delimited JSON):
    {"type": "status", "message": "Loading agent..."}
    {"type": "progress", "current": 1, "total": 5, "input": "How do I..."}
    {"type": "score", "case": 1, "scorer": "tool_usage", "score": 1.0}
    {"type": "result", "total_cases": 5, "summary": {...}}
    {"type": "error", "message": "error message"}  # Only if error occurs

Exit codes:
    0 - Success
    1 - Error (see stderr for details)
"""
import sys
import json
import os
import asyncio
import random
from pathlib import Path


def emit(data: dict):
    """Emit a JSON line to stdout."""
    print(json.dumps(data), flush=True)


async def run_evaluation(config_path: str, sample_size: int = None, model_ref: str = None):
    """
    Run evaluation and stream results to stdout as JSON lines.
    
    Args:
        config_path: Path to Tyler agent config YAML file (fallback)
        sample_size: If set, evaluate only this many random cases
        model_ref: Weave model reference (e.g., "Buzz:v3") to load from Weave.
                   If not provided or not found, falls back to config file.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        emit({"type": "status", "message": "Initializing Weave..."})
        
        # Initialize Weave in this fresh process
        import weave
        project = os.getenv("WANDB_PROJECT", "agentic-support-bot-demo")
        weave.init(project)
        
        emit({"type": "status", "message": f"Connected to Weave project: {project}"})
        
        from tyler import Agent, Thread, Message
        
        config_path = Path(config_path).absolute()
        config_dir = config_path.parent
        original_cwd = os.getcwd()
        
        agent = None
        model_name = None
        
        # Try to load agent from Weave if model_ref is provided
        if model_ref and model_ref != "No models found":
            emit({"type": "status", "message": f"Loading agent from Weave: {model_ref}..."})
            try:
                # Ensure model_ref has version (default to :latest)
                ref_str = model_ref if ":" in model_ref else f"{model_ref}:latest"
                agent_ref = weave.ref(ref_str)
                agent = agent_ref.get()
                model_name = model_ref
                emit({"type": "status", "message": f"Agent loaded from Weave: {model_name}"})
            except Exception as e:
                emit({"type": "status", "message": f"Could not load from Weave ({e}), falling back to config file..."})
                agent = None
        
        # Fall back to config file if Weave loading failed or no ref provided
        if agent is None:
            emit({"type": "status", "message": "Loading agent from config file..."})
            
            if not config_path.exists():
                emit({"type": "error", "message": f"Config file not found: {config_path}"})
                return
            
            # Change to config directory so relative paths work
            os.chdir(config_dir)
            
            try:
                agent = Agent.from_config(str(config_path))
                model_name = agent.name
                emit({"type": "status", "message": f"Agent loaded from config: {model_name}"})
            finally:
                os.chdir(original_cwd)
        
        # Load dataset
        emit({"type": "status", "message": "Loading dataset..."})
        
        try:
            dataset_ref = weave.ref("support-bot-eval-dataset:latest")
            dataset = dataset_ref.get()
            test_cases = [dict(row) for row in dataset.rows]
            emit({"type": "status", "message": f"Loaded {len(test_cases)} test cases"})
        except Exception as e:
            emit({"type": "error", "message": f"Failed to load dataset: {e}. Make sure you've published it first."})
            return
        
        # Sample if requested
        if sample_size and sample_size < len(test_cases):
            test_cases = random.sample(test_cases, sample_size)
            emit({"type": "status", "message": f"Sampled {len(test_cases)} cases"})
        
        # Import scorers
        emit({"type": "status", "message": "Loading scorers..."})
        
        # Add step-5 workspace to path for scorers
        workspace_path = str(Path("workspace/step-5").absolute())
        if workspace_path not in sys.path:
            sys.path.insert(0, workspace_path)
        
        from scorers import tool_usage_scorer, accuracy_scorer, safety_scorer
        
        # Initialize EvaluationLogger
        eval_logger = weave.EvaluationLogger(
            name="support-bot-eval",
            model=model_name,
            dataset=dataset
        )
        emit({"type": "status", "message": "Starting evaluation..."})
        
        # Track results for summary
        results = []
        
        # Run evaluation
        for i, test_case in enumerate(test_cases, 1):
            input_preview = test_case['input'][:60] + "..." if len(test_case['input']) > 60 else test_case['input']
            emit({"type": "progress", "current": i, "total": len(test_cases), "input": input_preview})
            
            # Invoke agent
            try:
                # Change to config dir for agent execution
                os.chdir(config_dir)
                try:
                    thread = Thread()
                    thread.add_message(Message(role="user", content=test_case["input"]))
                    result = await agent.run(thread)
                    
                    output = {
                        "response": result.content if result.content else "",
                        "tools_used": list(result.thread.get_tool_usage().get('tools', {}).keys()) if result.thread.get_tool_usage() else []
                    }
                finally:
                    os.chdir(original_cwd)
            except Exception as e:
                emit({"type": "score", "case": i, "scorer": "agent", "score": 0, "error": str(e)})
                continue
            
            # Log prediction
            pred_logger = eval_logger.log_prediction(
                inputs={"query": test_case["input"]},
                output=output
            )
            
            case_results = {"case": i, "input": input_preview}
            
            # Apply scorers
            try:
                tool_score = tool_usage_scorer(test_case, output)
                pred_logger.log_score(scorer="tool_usage", score=tool_score)
                case_results["tool_usage"] = tool_score.get("score", 0)
                emit({"type": "score", "case": i, "scorer": "tool_usage", "score": tool_score.get("score", 0)})
            except Exception as e:
                emit({"type": "score", "case": i, "scorer": "tool_usage", "error": str(e)})
            
            try:
                accuracy_score = await accuracy_scorer(test_case, output)
                pred_logger.log_score(scorer="accuracy", score=accuracy_score)
                case_results["accuracy"] = accuracy_score.get("accuracy", 0)
                emit({"type": "score", "case": i, "scorer": "accuracy", "score": accuracy_score.get("accuracy", 0)})
            except Exception as e:
                emit({"type": "score", "case": i, "scorer": "accuracy", "error": str(e)})
            
            try:
                safety_score = await safety_scorer(test_case, output)
                pred_logger.log_score(scorer="safety", score=safety_score)
                case_results["safety"] = safety_score.get("overall_safety", 0)
                emit({"type": "score", "case": i, "scorer": "safety", "score": safety_score.get("overall_safety", 0)})
            except Exception as e:
                emit({"type": "score", "case": i, "scorer": "safety", "error": str(e)})
            
            pred_logger.finish()
            results.append(case_results)
        
        # Log summary
        eval_logger.log_summary({"total_cases": len(test_cases), "sample": sample_size is not None})
        
        # Calculate aggregate scores
        summary = {
            "total_cases": len(test_cases),
            "tool_usage_avg": sum(r.get("tool_usage", 0) for r in results) / len(results) if results else 0,
            "accuracy_avg": sum(r.get("accuracy", 0) for r in results) / len(results) if results else 0,
            "safety_avg": sum(r.get("safety", 0) for r in results) / len(results) if results else 0,
        }
        
        emit({"type": "result", "total_cases": len(test_cases), "model": model_name, "summary": summary})
        
    except Exception as e:
        import traceback
        emit({"type": "error", "message": str(e), "traceback": traceback.format_exc()})
        raise


def main():
    """Main entry point - read stdin, run evaluation, stream to stdout."""
    try:
        # Read input from stdin (JSON with config and options)
        input_data = json.loads(sys.stdin.read())
        config_path = input_data.get("config_path")
        sample_size = input_data.get("sample_size")
        model_ref = input_data.get("model_ref")
        
        if not config_path:
            emit({"type": "error", "message": "No config_path provided"})
            sys.exit(1)
        
        # Run the evaluation
        asyncio.run(run_evaluation(config_path, sample_size, model_ref))
        sys.exit(0)
    
    except json.JSONDecodeError as e:
        emit({"type": "error", "message": f"Invalid JSON input: {e}"})
        sys.exit(1)
    except Exception as e:
        emit({"type": "error", "message": f"Unexpected error: {e}"})
        sys.exit(1)


if __name__ == "__main__":
    main()

