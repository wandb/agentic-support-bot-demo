"""
Tests for helpers/isolated_agent_runner.py
"""
import json
import subprocess
import sys
from pathlib import Path


def test_isolated_agent_runner_basic():
    """Test that the isolated agent runner can be invoked and handle basic input."""
    runner_script = Path(__file__).parent.parent / "helpers" / "isolated_agent_runner.py"
    
    # Test with invalid input (should handle gracefully)
    result = subprocess.run(
        [sys.executable, str(runner_script)],
        input=json.dumps({"messages": []}),  # Empty messages
        capture_output=True,
        text=True
    )
    
    # Should exit with error code
    assert result.returncode == 1
    
    # Should output error as JSON
    try:
        error_output = json.loads(result.stdout.strip())
        assert "error" in error_output
    except json.JSONDecodeError:
        # Output might be multi-line, just check it contains error info
        assert "error" in result.stdout.lower() or result.returncode != 0


def test_isolated_agent_runner_missing_config():
    """Test handling of missing config path."""
    runner_script = Path(__file__).parent.parent / "helpers" / "isolated_agent_runner.py"
    
    result = subprocess.run(
        [sys.executable, str(runner_script)],
        input=json.dumps({"messages": [{"role": "user", "content": "test"}]}),  # No config_path
        capture_output=True,
        text=True
    )
    
    # Should exit with error code
    assert result.returncode == 1
    
    # Should mention missing config in output
    output = result.stdout.lower()
    assert "error" in output or "config" in output


if __name__ == "__main__":
    print("Testing isolated_agent_runner...")
    try:
        test_isolated_agent_runner_basic()
        print("✓ Basic error handling test passed")
    except AssertionError as e:
        print(f"✗ Basic error handling test failed: {e}")
    
    try:
        test_isolated_agent_runner_missing_config()
        print("✓ Missing config test passed")
    except AssertionError as e:
        print(f"✗ Missing config test failed: {e}")
    
    print("\nNote: Full integration tests require a valid Tyler config and environment setup.")


