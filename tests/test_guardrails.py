"""
Tests for guardrail scorers using Weave's built-in scorers.

Input-only guardrail approach:
- INPUT: OpenAIModerationScorer (checks user input BEFORE generation)
- No OUTPUT guardrail (would break streaming UX)

Why only INPUT guardrails?
- INPUT guardrails block bad requests before generation (fast, doesn't break streaming)
- OUTPUT guardrails require full response to check (breaks streaming, worse UX)
- Modern LLMs rarely generate toxic content on their own
- This is the most common production pattern for streaming applications

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

# Add examples/step-6 to path so we can import guardrails
step_6_path = Path(__file__).parent.parent / "examples" / "step-6"
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
        THEN flagged=false (or flagged=true with error if API unavailable)
        
        Maps to Spec: "Safe, on-topic prompt passes guardrails"
        
        Note: If OpenAI Moderation API has errors (timeout, rate limit), 
        guardrail defaults to blocking for safety. Test handles both cases.
        """
        from guardrails import InputToxicityGuardrail
        
        guardrail = InputToxicityGuardrail()
        result = await guardrail.score(input="How do I initialize Weave in Python?")
        
        # Check if error occurred (either explicit error key or error message in reason)
        has_error = "error" in result or (
            result.get("reason") and "unavailable" in result.get("reason", "").lower()
        )
        
        if has_error:
            # Error case: guardrail defaults to blocking (safe behavior)
            assert result["flagged"] is True, "Error case should default to blocking"
            error_msg = result.get("error") or result.get("reason") or "Unknown error"
            pytest.skip(f"OpenAI Moderation API error: {error_msg}")
        else:
            # Normal case: safe input should pass
            assert result["flagged"] is False, f"Safe input should not be flagged. Result: {result}"
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
    
    def test_scorer_has_score_method(self):
        """
        GIVEN guardrail scorer
        WHEN checked for score method
        THEN should have @weave.op decorated score method
        """
        from guardrails import InputToxicityGuardrail
        
        input_guard = InputToxicityGuardrail()
        
        assert hasattr(input_guard, 'score'), "InputToxicityGuardrail must have score method"
        assert callable(input_guard.score), "score must be callable"
    
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
        GIVEN guardrail scorer
        WHEN initialized outside request handler
        THEN should be reusable across multiple score calls
        
        Maps to TDR: "Initialize scorers outside request handler (performance)"
        """
        from guardrails import InputToxicityGuardrail
        
        # Initialize once (simulating module-level initialization)
        input_guard = InputToxicityGuardrail()
        
        # Use multiple times
        result1 = await input_guard.score(input="test 1")
        result2 = await input_guard.score(input="test 2")
        
        assert isinstance(result1, dict)
        assert isinstance(result2, dict)


class TestInputGuardrailFlow:
    """Tests for input guardrail workflow (only input checking, no output)."""
    
    @requires_openai
    @pytest.mark.asyncio
    async def test_input_guardrail_blocks_before_generation(self):
        """
        GIVEN toxic user input
        WHEN input guardrail applied
        THEN should block BEFORE any generation happens
        
        Key insight: Saves cost and time by not generating for toxic prompts.
        This is the only guardrail stage - no output guardrail to maintain streaming.
        """
        from guardrails import InputToxicityGuardrail
        
        input_guard = InputToxicityGuardrail()
        user_prompt = "I hate you! You're terrible!"
        
        # Check input FIRST
        input_check = await input_guard.score(input=user_prompt)
        
        # Should be blocked (don't proceed to generation)
        assert input_check["flagged"] is True
        # In real flow, we would return here and NOT call the agent
    
    @requires_openai
    @pytest.mark.asyncio
    async def test_input_guardrail_allows_safe_input(self):
        """
        GIVEN safe user input
        WHEN input guardrail applied
        THEN should allow and proceed to generation (or skip if API error)
        
        Note: No output guardrail needed - modern LLMs rarely generate toxic content,
        and output checking would break streaming UX.
        
        If OpenAI Moderation API has errors, guardrail defaults to blocking for safety.
        """
        from guardrails import InputToxicityGuardrail
        
        input_guard = InputToxicityGuardrail()
        safe_prompt = "How do I initialize Weave in Python?"
        
        # Check input
        input_check = await input_guard.score(input=safe_prompt)
        
        # Check if error occurred (either explicit error key or error message in reason)
        has_error = "error" in input_check or (
            input_check.get("reason") and "unavailable" in input_check.get("reason", "").lower()
        )
        
        if has_error:
            # Error case: skip test (API unavailable in CI)
            error_msg = input_check.get("error") or input_check.get("reason") or "Unknown error"
            pytest.skip(f"OpenAI Moderation API error: {error_msg}")
        
        # Should NOT be blocked (proceed to generation)
        assert input_check["flagged"] is False, f"Safe input should not be flagged. Result: {input_check}"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
