"""
Tests for evaluation scorers.

These tests validate that scorers:
- Return properly formatted results
- Handle correct/incorrect cases appropriately
- Don't crash on unexpected input
- Work with edge cases
"""

import sys
from pathlib import Path

# Add examples directory to path to import scorers
examples_dir = Path(__file__).parent.parent / "examples" / "step-4-complete"
sys.path.insert(0, str(examples_dir))

from scorers import tool_usage_scorer, get_all_scorers


class TestToolUsageScorer:
    """Test the rule-based tool usage scorer."""
    
    def test_correct_tools(self):
        """Scorer returns success when tools match exactly."""
        input_data = {
            "input": "Create a ticket",
            "expected_tools": ["support-create_issue"]
        }
        output_data = {
            "response": "I've created the ticket",
            "tools_used": ["support-create_issue"]
        }
        
        result = tool_usage_scorer(input_data, output_data)
        
        assert result["correct_tools"] == True
        assert result["score"] == 1.0
        assert len(result["missing_tools"]) == 0
        assert len(result["extra_tools"]) == 0
    
    def test_missing_tools(self):
        """Scorer identifies when expected tools weren't called."""
        input_data = {
            "expected_tools": ["support-create_issue"]
        }
        output_data = {
            "tools_used": []  # Forgot to call tool!
        }
        
        result = tool_usage_scorer(input_data, output_data)
        
        assert result["correct_tools"] == False
        assert result["score"] == 0.0
        assert "support-create_issue" in result["missing_tools"]
        assert len(result["extra_tools"]) == 0
    
    def test_extra_tools(self):
        """Scorer identifies when unexpected tools were called."""
        input_data = {
            "expected_tools": []  # Should not call any tools
        }
        output_data = {
            "tools_used": ["support-create_issue"]  # But it did!
        }
        
        result = tool_usage_scorer(input_data, output_data)
        
        assert result["correct_tools"] == False
        assert result["score"] == 0.0
        assert len(result["missing_tools"]) == 0
        assert "support-create_issue" in result["extra_tools"]
    
    def test_multiple_tools_correct(self):
        """Scorer handles multiple tools correctly."""
        input_data = {
            "expected_tools": ["support-create_issue", "support-get_issue"]
        }
        output_data = {
            "tools_used": ["support-create_issue", "support-get_issue"]
        }
        
        result = tool_usage_scorer(input_data, output_data)
        
        assert result["correct_tools"] == True
        assert result["score"] == 1.0
    
    def test_wrong_tool_called(self):
        """Scorer detects when wrong tool was called."""
        input_data = {
            "expected_tools": ["support-create_issue"]
        }
        output_data = {
            "tools_used": ["support-get_issue"]  # Wrong tool!
        }
        
        result = tool_usage_scorer(input_data, output_data)
        
        assert result["correct_tools"] == False
        assert result["score"] == 0.0
        assert "support-create_issue" in result["missing_tools"]
        assert "support-get_issue" in result["extra_tools"]
    
    def test_handles_missing_fields(self):
        """Scorer doesn't crash when fields are missing."""
        # Missing expected_tools
        result = tool_usage_scorer({}, {"tools_used": []})
        assert "correct_tools" in result
        assert "score" in result
        
        # Missing tools_used
        result = tool_usage_scorer({"expected_tools": []}, {})
        assert "correct_tools" in result
        assert "score" in result
        
        # Both missing
        result = tool_usage_scorer({}, {})
        assert "correct_tools" in result
        assert "score" in result
        assert result["correct_tools"] == True  # Empty == Empty
    
    def test_order_doesnt_matter(self):
        """Tool order shouldn't matter for correctness."""
        input_data = {
            "expected_tools": ["support-create_issue", "support-get_issue"]
        }
        output_data = {
            "tools_used": ["support-get_issue", "support-create_issue"]  # Reversed
        }
        
        result = tool_usage_scorer(input_data, output_data)
        
        assert result["correct_tools"] == True
        assert result["score"] == 1.0


class TestScorerReturnFormats:
    """Test that all scorers return properly formatted results."""
    
    def test_tool_scorer_returns_dict(self):
        """Tool scorer returns a dictionary."""
        result = tool_usage_scorer(
            {"expected_tools": []},
            {"tools_used": []}
        )
        
        assert isinstance(result, dict)
        assert "score" in result
        assert isinstance(result["score"], (int, float))
    
    def test_tool_scorer_has_required_fields(self):
        """Tool scorer returns all expected fields."""
        result = tool_usage_scorer(
            {"expected_tools": []},
            {"tools_used": []}
        )
        
        required_fields = ["correct_tools", "missing_tools", "extra_tools", "score"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
    
    def test_score_in_valid_range(self):
        """Tool scorer returns scores in [0, 1] range."""
        # Test correct case (should be 1.0)
        result = tool_usage_scorer(
            {"expected_tools": ["support-create_issue"]},
            {"tools_used": ["support-create_issue"]}
        )
        assert 0.0 <= result["score"] <= 1.0
        
        # Test incorrect case (should be 0.0)
        result = tool_usage_scorer(
            {"expected_tools": ["support-create_issue"]},
            {"tools_used": []}
        )
        assert 0.0 <= result["score"] <= 1.0


class TestLLMJudgeScorers:
    """Test LLM judge scorers (without making actual API calls)."""
    
    def test_accuracy_scorer_exists(self):
        """Accuracy scorer is available."""
        from scorers import accuracy_scorer
        assert callable(accuracy_scorer)
    
    def test_safety_scorer_exists(self):
        """Safety scorer is available."""
        from scorers import safety_scorer
        assert callable(safety_scorer)
    
    def test_llm_scorers_handle_errors_gracefully(self):
        """LLM scorers should return error scores if API fails."""
        from scorers import accuracy_scorer, safety_scorer
        
        # These will fail without valid API keys, but should return error dict
        input_data = {"input": "test", "expected_output": "test"}
        output_data = {"response": "test"}
        
        # Accuracy scorer
        result = accuracy_scorer(input_data, output_data)
        assert isinstance(result, dict)
        assert "accuracy" in result or "error" in result
        
        # Safety scorer
        result = safety_scorer(input_data, output_data)
        assert isinstance(result, dict)
        # Should have tone, refusal, safety fields or error
        assert any(key in result for key in ["tone", "error"])


class TestScorerRegistry:
    """Test scorer registration and retrieval."""
    
    def test_get_all_scorers_returns_dict(self):
        """get_all_scorers returns a dictionary."""
        scorers = get_all_scorers()
        assert isinstance(scorers, dict)
    
    def test_get_all_scorers_includes_required_scorers(self):
        """get_all_scorers includes all required scorers."""
        scorers = get_all_scorers()
        
        required = ["tool_usage", "accuracy", "safety"]
        for scorer_name in required:
            assert scorer_name in scorers, f"Missing scorer: {scorer_name}"
    
    def test_all_scorers_are_callable(self):
        """All returned scorers should be callable."""
        scorers = get_all_scorers()
        
        for name, scorer in scorers.items():
            assert callable(scorer), f"Scorer '{name}' is not callable"


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_strings_in_tools(self):
        """Handle empty strings in tool lists."""
        input_data = {"expected_tools": [""]}
        output_data = {"tools_used": [""]}
        
        result = tool_usage_scorer(input_data, output_data)
        assert "score" in result
        # Empty string tools should match
        assert result["correct_tools"] == True
    
    def test_duplicate_tools(self):
        """Handle duplicate tools in lists."""
        input_data = {"expected_tools": ["support-create_issue", "support-create_issue"]}
        output_data = {"tools_used": ["support-create_issue"]}
        
        result = tool_usage_scorer(input_data, output_data)
        # Sets remove duplicates, so this should match
        assert result["correct_tools"] == True
    
    def test_none_values(self):
        """Handle None values gracefully."""
        # None in input
        result = tool_usage_scorer(None, {"tools_used": []})
        assert "score" in result
        
        # None in output
        result = tool_usage_scorer({"expected_tools": []}, None)
        assert "score" in result
    
    def test_very_large_tool_lists(self):
        """Handle large tool lists."""
        many_tools = [f"tool-{i}" for i in range(100)]
        
        input_data = {"expected_tools": many_tools}
        output_data = {"tools_used": many_tools}
        
        result = tool_usage_scorer(input_data, output_data)
        assert result["correct_tools"] == True
        assert result["score"] == 1.0

