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
        "config_path": "/path/to/tyler-chat-config.yaml",  # Used to find tools.py directory
        "sample_size": 5,  # optional, runs full dataset if not specified
        "config_ref": "Buzz:v3"  # Weave config reference (REQUIRED)
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
import tempfile
from pathlib import Path


def emit(data: dict):
    """Emit a JSON line to stdout."""
    print(json.dumps(data), flush=True)


async def run_evaluation(config_path: str, sample_size: int = None, config_ref: str = None):
    """
    Run evaluation and stream results to stdout as JSON lines.
    
    Args:
        config_path: Path to workspace directory (used to find tools.py)
        sample_size: If set, evaluate only this many random cases
        config_ref: Weave config reference (e.g., "Buzz:v3") - REQUIRED
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        # Validate config_ref is provided
        if not config_ref or config_ref == "No configs found":
            emit({"type": "error", "message": "No config_ref provided. Select a config version to evaluate."})
            return
        
        emit({"type": "status", "message": "Initializing Weave..."})
        
        # Initialize Weave in this fresh process
        import weave
        project = os.getenv("WANDB_PROJECT", "agentic-support-bot-demo")
        weave.init(project)
        
        emit({"type": "status", "message": f"Connected to Weave project: {project}"})
        
        from tyler import Agent, Thread, Message
        
        # Determine workspace directory for tools.py
        config_path = Path(config_path).absolute()
        workspace_dir = config_path.parent  # e.g., workspace/step-4/
        original_cwd = os.getcwd()
        
        # Calculate scorers path BEFORE changing directories
        # Go up from workspace/step-4 to project root, then to workspace/step-5
        project_root = workspace_dir.parent.parent  # From workspace/step-4/ -> workspace/ -> project root
        scorers_path = project_root / "workspace" / "step-5"
        
        # Load config from Weave (the source of truth)
        emit({"type": "status", "message": f"Loading config from Weave: {config_ref}..."})
        
        # Ensure config_ref has version (default to :latest)
        ref_str = config_ref if ":" in config_ref else f"{config_ref}:latest"
        
        try:
        config_obj = weave.ref(ref_str).get()
        
            # Extract YAML content from AgentConfig object
            # AgentConfig is a custom Weave Object with a 'yaml' attribute
            if hasattr(config_obj, 'yaml'):
        yaml_content = config_obj.yaml
        config_name = config_obj.name
            else:
                # Fallback: if it's a dict or other structure
                emit({"type": "error", "message": f"Unexpected config object type: {type(config_obj)}. Expected AgentConfig with 'yaml' attribute."})
                return
        
        emit({"type": "status", "message": f"Loaded config '{config_name}' from Weave ({ref_str})"})
            
        except Exception as e:
            emit({"type": "error", "message": f"Failed to load config from Weave: {e}. Make sure the config exists."})
            return
        
        # Write YAML to workspace directory where tools.py lives
        # This ensures ./tools.py relative path resolves correctly
        temp_config_path = workspace_dir / "tyler-chat-config.yaml"
        
        try:
            temp_config_path.write_text(yaml_content)
        emit({"type": "status", "message": f"Config written to {temp_config_path}"})
        except Exception as e:
            emit({"type": "error", "message": f"Failed to write config file: {e}"})
            return
        
        # Change to workspace directory and load agent
        os.chdir(workspace_dir)
        
        try:
            agent = Agent.from_config(str(temp_config_path))
            model_name = agent.name
            emit({"type": "status", "message": f"Agent created: {model_name} (tools: {len(agent.tools) if hasattr(agent, 'tools') and agent.tools else 0})"})
        except Exception as e:
            import traceback
            emit({"type": "error", "message": f"Failed to create agent from config: {e}\n\nTraceback:\n{traceback.format_exc()}"})
            os.chdir(original_cwd)
            return
        
        # Load dataset
        emit({"type": "status", "message": "Loading dataset..."})
        
        try:
            dataset_ref = weave.ref("support-bot-eval-dataset:latest")
            dataset = dataset_ref.get()
            
            # If sampling, create a subset dataset
            if sample_size and len(dataset.rows) > sample_size:
                # Sample row indices
                import random
                all_indices = list(range(len(dataset.rows)))
                sampled_indices = random.sample(all_indices, sample_size)
                # Create a subset dataset for evaluation
                eval_dataset = dataset.select(sampled_indices)
                emit({"type": "status", "message": f"Sampled {sample_size} cases from {len(dataset.rows)} total"})
            else:
                eval_dataset = dataset
            
            emit({"type": "status", "message": f"Loaded {len(eval_dataset.rows)} test cases"})
        except Exception as e:
            emit({"type": "error", "message": f"Failed to load dataset: {e}. Make sure you've published it first."})
            os.chdir(original_cwd)
            return
        
        # Import scorers
        emit({"type": "status", "message": "Loading scorers..."})
        
        # Add step-5 workspace to path for scorers (calculated earlier, before chdir)
        if str(scorers_path) not in sys.path:
            sys.path.insert(0, str(scorers_path))
        
        from scorers import tool_usage_scorer, accuracy_scorer, safety_scorer
        
        # Initialize EvaluationLogger
        # Pass agent.name (string) not the agent object itself
        emit({"type": "status", "message": f"Creating evaluation with model: {model_name}"})
        eval_logger = weave.EvaluationLogger(
            name="support-bot-eval",
            model=model_name,  # Pass string name, not agent object
            dataset=eval_dataset  # Use the (possibly sampled) Weave Dataset
        )
        emit({"type": "status", "message": "Starting evaluation..."})
        
        # Track results for summary
        results = []
        eval_error = None
        
        try:
            # Run evaluation - iterate over dataset rows directly
            for i, test_case in enumerate(eval_dataset.rows, 1):
                # Convert row to dict for easier access
                test_case_dict = dict(test_case)
                input_preview = test_case_dict['input'][:60] + "..." if len(test_case_dict['input']) > 60 else test_case_dict['input']
                emit({"type": "progress", "current": i, "total": len(eval_dataset.rows), "input": input_preview})
                
                # Invoke agent
                try:
                    # Ensure we're in workspace dir for tool resolution
                    os.chdir(workspace_dir)
                    try:
                        thread = Thread()
                        thread.add_message(Message(role="user", content=test_case_dict["input"]))
                        result = await agent.run(thread)
                        
                        output = {
                            "response": result.content if result.content else "",
                            "tools_used": list(result.thread.get_tool_usage().get('tools', {}).keys()) if result.thread.get_tool_usage() else []
                        }
                    finally:
                        pass  # Stay in workspace dir
                except Exception as e:
                    emit({"type": "score", "case": i, "scorer": "agent", "score": 0, "error": str(e)})
                    continue
                
                # Log prediction using context manager for proper cleanup
                with eval_logger.log_prediction(
                    inputs={"query": test_case_dict["input"]},
                    output=output
                ) as pred_logger:
                    case_results = {"case": i, "input": input_preview}
                    
                    # Apply scorers
                    try:
                        tool_score = tool_usage_scorer(test_case_dict, output)
                        pred_logger.log_score(scorer="tool_usage", score=tool_score)
                        case_results["tool_usage"] = tool_score.get("score", 0)
                        emit({"type": "score", "case": i, "scorer": "tool_usage", "score": tool_score.get("score", 0)})
                    except Exception as e:
                        emit({"type": "score", "case": i, "scorer": "tool_usage", "error": str(e)})
                    
                    try:
                        accuracy_score = await accuracy_scorer(test_case_dict, output)
                        pred_logger.log_score(scorer="accuracy", score=accuracy_score)
                        case_results["accuracy"] = accuracy_score.get("accuracy", 0)
                        emit({"type": "score", "case": i, "scorer": "accuracy", "score": accuracy_score.get("accuracy", 0)})
                    except Exception as e:
                        emit({"type": "score", "case": i, "scorer": "accuracy", "error": str(e)})
                    
                    try:
                        safety_score = await safety_scorer(test_case_dict, output)
                        pred_logger.log_score(scorer="safety", score=safety_score)
                        case_results["safety"] = safety_score.get("overall_safety", 0)
                        emit({"type": "score", "case": i, "scorer": "safety", "score": safety_score.get("overall_safety", 0)})
                    except Exception as e:
                        emit({"type": "score", "case": i, "scorer": "safety", "error": str(e)})
                    
                    results.append(case_results)
                    # pred_logger.finish() is called automatically by context manager
        except Exception as e:
            eval_error = e
        finally:
            # Always finalize the evaluation logger to prevent cleanup errors
            try:
                # Log summary (this also finalizes the evaluation)
                eval_logger.log_summary({"total_cases": len(test_cases), "sample": sample_size is not None})
            except Exception as summary_error:
                # If log_summary fails, try explicit finish
                emit({"type": "status", "message": f"Warning: log_summary failed ({summary_error}), calling finish()"})
                try:
                    eval_logger.finish()
                except Exception:
                    pass  # Ignore cleanup errors
            
            # Restore original working directory
            os.chdir(original_cwd)
        
        # Re-raise any error that occurred during evaluation after cleanup
        if eval_error:
            raise eval_error
        
        # Calculate aggregate scores
        summary = {
            "total_cases": len(eval_dataset.rows),
            "tool_usage_avg": sum(r.get("tool_usage", 0) for r in results) / len(results) if results else 0,
            "accuracy_avg": sum(r.get("accuracy", 0) for r in results) / len(results) if results else 0,
            "safety_avg": sum(r.get("safety", 0) for r in results) / len(results) if results else 0,
        }
        
        emit({"type": "result", "total_cases": len(eval_dataset.rows), "model": model_name, "config_ref": config_ref, "summary": summary})
        
    except Exception as e:
        import traceback
        emit({"type": "error", "message": str(e), "traceback": traceback.format_exc()})
        # Don't raise - just emit error and exit cleanly so marimo can display it


def main():
    """Main entry point - read stdin, run evaluation, stream to stdout."""
    try:
        # Read input from stdin (JSON with config and options)
        input_data = json.loads(sys.stdin.read())
        config_path = input_data.get("config_path")
        sample_size = input_data.get("sample_size")
        config_ref = input_data.get("config_ref")
        
        # Support legacy "model_ref" parameter for backward compatibility
        if not config_ref:
            config_ref = input_data.get("model_ref")
        
        if not config_path:
            emit({"type": "error", "message": "No config_path provided"})
            sys.exit(1)
        
        # Run the evaluation
        asyncio.run(run_evaluation(config_path, sample_size, config_ref))
        sys.exit(0)
    
    except json.JSONDecodeError as e:
        emit({"type": "error", "message": f"Invalid JSON input: {e}"})
        sys.exit(1)
    except Exception as e:
        emit({"type": "error", "message": f"Unexpected error: {e}"})
        sys.exit(1)


if __name__ == "__main__":
    main()
