"""
Tests for guardrail scorers using Weave's built-in scorers.

Two-stage guardrail approach:
- INPUT: OpenAIModerationScorer (checks user input BEFORE generation)
- OUTPUT: WeaveToxicityScorerV1 (checks agent response AFTER generation)

Note: These tests require:
- 'pip install weave[scorers]' (torch, transformers)
- OPENAI_API_KEY or WANDB_API_KEY environment variable
- May be slow on first run while models download
"""

import pytest
import weave
import os
from pathlib import Path
import sys

# Add examples/step-6/part-a to path so we can import guardrails
step_6_path = Path(__file__).parent.parent / "examples" / "step-6" / "part-a"
sys.path.insert(0, str(step_6_path))

# Check if API key is available for tests that need it
HAS_OPENAI_KEY = bool(os.getenv("OPENAI_API_KEY") or os.getenv("WANDB_API_KEY"))
requires_openai = pytest.mark.skipif(
    not HAS_OPENAI_KEY,
    reason="Requires OPENAI_API_KEY or WANDB_API_KEY for OpenAI Moderation API"
)


class TestInputToxicityGuardrail:
    """Unit tests for INPUT toxicity guardrail (OpenAI Moderation)."""
    
    @requires_openai
    @pytest.mark.asyncio
    async def test_blocks_toxic_user_input(self):
        """
        GIVEN toxic user input
        WHEN scored by InputToxicityGuardrail
        THEN flagged=true with reason
        
        Maps to Spec: "Adversarial prompt with toxic language blocked"
        """
        from guardrails import InputToxicityGuardrail
        
        guardrail = InputToxicityGuardrail()
        result = await guardrail.score(input="I hate you! You're terrible!")
        
        assert result["flagged"] is True, "Toxic input should be flagged"
        assert result["reason"] is not None, "Should provide blocking reason"
        assert result["score"] == 0.0, "Flagged content should have score 0.0"
    
    @requires_openai
    @pytest.mark.asyncio
    async def test_allows_safe_user_input(self):
        """
        GIVEN safe, professional user input
        WHEN scored by InputToxicityGuardrail
        THEN flagged=false
        
        Maps to Spec: "Safe, on-topic prompt passes guardrails"
        """
        from guardrails import InputToxicityGuardrail
        
        guardrail = InputToxicityGuardrail()
        result = await guardrail.score(input="How do I initialize Weave in Python?")
        
        assert result["flagged"] is False, "Safe input should not be flagged"
        assert result["reason"] is None, "Safe input should have no blocking reason"
        assert result["score"] == 1.0, "Safe input should have score 1.0"
    
    @pytest.mark.asyncio
    async def test_error_handling_defaults_safe(self):
        """
        GIVEN scorer encounters an error
        WHEN scoring content
        THEN defaults to blocking with error explanation
        
        Maps to Spec: "Guardrail error defaults to blocking"
        """
        from guardrails import InputToxicityGuardrail
        
        guardrail = InputToxicityGuardrail()
        
        # Test with None input (should cause error)
        result = await guardrail.score(input=None)
        
        # Should default to blocking on error
        assert result["flagged"] is True, "Error should default to blocking"
        assert "error" in result or "unavailable" in result.get("reason", "").lower()


class TestOutputToxicityGuardrail:
    """Unit tests for OUTPUT toxicity guardrail (Weave local ML model)."""
    
    @pytest.mark.asyncio
    async def test_allows_safe_output(self):
        """
        GIVEN safe W&B/Weave support output
        WHEN scored by OutputToxicityGuardrail
        THEN flagged=false
        
        Maps to Spec: "Safe, on-topic prompt passes guardrails"
        """
        from guardrails import OutputToxicityGuardrail
        
        guardrail = OutputToxicityGuardrail()
        result = await guardrail.score(
            output="To initialize Weave, call weave.init() with your project name. You can then use @weave.op() to track your functions."
        )
        
        assert result["flagged"] is False, "Safe output should not be flagged"
        assert result["reason"] is None
        assert result["score"] == 1.0
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """
        GIVEN scorer encounters an error
        WHEN scoring content
        THEN defaults to blocking
        """
        from guardrails import OutputToxicityGuardrail
        
        guardrail = OutputToxicityGuardrail()
        result = await guardrail.score(output=None)
        
        assert result["flagged"] is True, "Error should default to blocking"


class TestGuardrailScorer:
    """Tests for Scorer interface compliance."""
    
    def test_input_toxicity_inherits_from_scorer(self):
        """
        GIVEN InputToxicityGuardrail class
        WHEN checked for inheritance
        THEN should inherit from weave.Scorer
        """
        from guardrails import InputToxicityGuardrail
        
        assert issubclass(InputToxicityGuardrail, weave.Scorer), "InputToxicityGuardrail must inherit from weave.Scorer"
    
    def test_output_toxicity_inherits_from_scorer(self):
        """
        GIVEN OutputToxicityGuardrail class
        WHEN checked for inheritance
        THEN should inherit from weave.Scorer
        """
        from guardrails import OutputToxicityGuardrail
        
        assert issubclass(OutputToxicityGuardrail, weave.Scorer), "OutputToxicityGuardrail must inherit from weave.Scorer"
    
    def test_scorer_has_score_method(self):
        """
        GIVEN guardrail scorers
        WHEN checked for score method
        THEN should have @weave.op decorated score method
        """
        from guardrails import InputToxicityGuardrail, OutputToxicityGuardrail
        
        input_guard = InputToxicityGuardrail()
        output_guard = OutputToxicityGuardrail()
        
        assert hasattr(input_guard, 'score'), "InputToxicityGuardrail must have score method"
        assert hasattr(output_guard, 'score'), "OutputToxicityGuardrail must have score method"
        assert callable(input_guard.score), "score must be callable"
        assert callable(output_guard.score), "score must be callable"
    
    @pytest.mark.asyncio
    async def test_score_returns_dict(self):
        """
        GIVEN guardrail scorers
        WHEN score method called
        THEN should return dict with required keys
        """
        from guardrails import InputToxicityGuardrail
        
        guardrail = InputToxicityGuardrail()
        result = await guardrail.score(input="test content")
        
        assert isinstance(result, dict), "score() must return dict"
        assert "flagged" in result, "result must contain 'flagged' key"
        assert "score" in result, "result must contain 'score' key"
        assert isinstance(result["flagged"], bool), "flagged must be boolean"
        assert isinstance(result["score"], (int, float)), "score must be numeric"


class TestGuardrailInitialization:
    """Tests for efficient scorer initialization."""
    
    @pytest.mark.asyncio
    async def test_scorers_can_be_initialized_once(self):
        """
        GIVEN guardrail scorers
        WHEN initialized outside request handler
        THEN should be reusable across multiple score calls
        
        Maps to TDR: "Initialize scorers outside request handler (performance)"
        """
        from guardrails import InputToxicityGuardrail, OutputToxicityGuardrail
        
        # Initialize once (simulating module-level initialization)
        input_guard = InputToxicityGuardrail()
        output_guard = OutputToxicityGuardrail()
        
        # Use multiple times
        result1 = await input_guard.score(input="test 1")
        result2 = await input_guard.score(input="test 2")
        result3 = await output_guard.score(output="test 3")
        
        assert isinstance(result1, dict)
        assert isinstance(result2, dict)
        assert isinstance(result3, dict)


class TestTwoStageGuardrailFlow:
    """Tests for two-stage guardrail workflow."""
    
    @requires_openai
    @pytest.mark.asyncio
    async def test_input_guardrail_blocks_before_generation(self):
        """
        GIVEN toxic user input
        WHEN input guardrail applied
        THEN should block BEFORE any generation happens
        
        Key insight: Saves cost and time by not generating for toxic prompts
        """
        from guardrails import InputToxicityGuardrail
        
        input_guard = InputToxicityGuardrail()
        user_prompt = "I hate you! You're terrible!"
        
        # Check input FIRST
        input_check = await input_guard.score(input=user_prompt)
        
        # Should be blocked (don't proceed to generation)
        assert input_check["flagged"] is True
        # In real flow, we would return here and NOT call the agent
    
    @pytest.mark.asyncio
    async def test_output_guardrail_checks_after_generation(self):
        """
        GIVEN safe agent response
        WHEN output guardrail applied
        THEN should allow (not block)
        
        Note: Testing blocking would require generating toxic output,
        which is hard to test reliably. We test the scorer works.
        """
        from guardrails import OutputToxicityGuardrail
        
        output_guard = OutputToxicityGuardrail()
        safe_response = "To use Weave, initialize it with weave.init() in your code."
        
        # Check output AFTER generation
        output_check = await output_guard.score(output=safe_response)
        
        # Should NOT be blocked (safe response)
        assert output_check["flagged"] is False


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
