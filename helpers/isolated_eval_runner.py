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
        config_path: Path to Tyler agent config YAML file (fallback if Weave load fails)
        sample_size: If set, evaluate only this many random cases
        model_ref: Weave model reference (e.g., "Buzz:v4") to load and evaluate
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
        model_ref_str = None  # String reference for EvaluationLogger (must be str, not WeaveObject)
        
        # Try to load agent from Weave if model_ref is provided
        if model_ref and model_ref != "No models found":
            emit({"type": "status", "message": f"Loading agent from Weave: {model_ref}..."})
            try:
                # Ensure model_ref has version (default to :latest)
                ref_str = model_ref if ":" in model_ref else f"{model_ref}:latest"
                agent_ref = weave.ref(ref_str)
                weave_model = agent_ref.get()
                
                # Extract properties from Weave model
                model_name = getattr(weave_model, 'name', model_ref.split(":")[0])
                
                # EvaluationLogger model parameter is just a label/name, not a reference
                # Using just the model name (without version) as the identifier
                # The version info will be tracked in evaluation metadata
                model_ref_str = model_name  # Just "Buzz", not "Buzz:v4" or URI
                
                # Reconstruct Tyler Agent from Weave properties (includes tools with implementations)
                emit({"type": "status", "message": f"Reconstructing Tyler Agent from Weave properties..."})
                
                # Get all properties from WeaveObject
                purpose = getattr(weave_model, 'purpose', '')
                notes = getattr(weave_model, 'notes', '')
                agent_model_name = getattr(weave_model, 'model_name', 'gpt-4.1')
                temperature = getattr(weave_model, 'temperature', 0.7)
                max_tool_iterations = getattr(weave_model, 'max_tool_iterations', 10)
                
                # Get tools and MCP config (convert from WeaveList/WeaveDict to Python types)
                tools_weave = getattr(weave_model, 'tools', [])
                mcp_weave = getattr(weave_model, 'mcp', None)
                
                tools_list = [dict(t) for t in tools_weave] if tools_weave else None
                mcp_dict = dict(mcp_weave) if mcp_weave else None
                
                # Create Tyler Agent with all stored properties
                agent = Agent(
                    name=model_name,
                    model_name=agent_model_name,
                    purpose=purpose,
                    notes=notes or "",
                    temperature=temperature,
                    max_tool_iterations=max_tool_iterations,
                    tools=tools_list,
                    mcp=mcp_dict,
                )
                
                # CRITICAL: Copy the ref from the original WeaveObject to prevent creating a new version
                # This tells Weave this is the SAME model, not a new one
                if hasattr(weave_model, 'ref') and weave_model.ref is not None:
                    agent.ref = weave_model.ref
                    emit({"type": "status", "message": f"Attached original ref: {weave_model.ref.name}:{weave_model.ref._digest[:8]}"})
                
                emit({"type": "status", "message": f"Tyler Agent reconstructed: {model_name} (tools: {len(agent.tools) if hasattr(agent, 'tools') else 0})"})
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
                model_ref_str = model_name  # Just use name string for config-loaded agents
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
        
        # Initialize EvaluationLogger with the reconstructed Tyler Agent (which IS a weave.Model subclass)
        # This properly links the evaluation to the model version
        emit({"type": "status", "message": f"Creating evaluation with model: {model_name}"})
        eval_logger = weave.EvaluationLogger(
            name="support-bot-eval",
            model=agent,  # Pass the weave.Model instance directly for proper linking
            dataset=dataset
        )
        emit({"type": "status", "message": "Starting evaluation..."})
        
        # Track results for summary
        results = []
        eval_error = None
        
        try:
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
                
                # Log prediction using context manager for proper cleanup
                with eval_logger.log_prediction(
                    inputs={"query": test_case["input"]},
                    output=output
                ) as pred_logger:
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
        
        # Re-raise any error that occurred during evaluation after cleanup
        if eval_error:
            raise eval_error
        
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

