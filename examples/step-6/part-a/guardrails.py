"""
Guardrail scorers for the W&B support bot.

Two-stage guardrail strategy using Weave's built-in scorers:
1. INPUT guardrail: OpenAIModerationScorer - Check user's prompt BEFORE generation (saves cost/time)
2. OUTPUT guardrail: WeaveToxicityScorerV1 - Check agent's response AFTER generation (safety check)

These are production-quality scorers that provide comprehensive coverage:
- OpenAIModerationScorer: Fast API (~100-200ms), checks hate/harassment/violence/etc
- WeaveToxicityScorerV1: Local ML model (~50-500ms), checks 5 dimensions of toxicity

Installation: pip install weave[scorers]
"""

import weave
from typing import Optional

# Import Weave's built-in scorers
try:
    from weave.scorers import OpenAIModerationScorer, WeaveToxicityScorerV1
    SCORERS_AVAILABLE = True
except ImportError:
    SCORERS_AVAILABLE = False
    raise ImportError(
        "Weave scorers not available. Install with: pip install weave[scorers]\n"
        "This is required for production-quality guardrails."
    )

class InputToxicityGuardrail(weave.Scorer):
    """
    INPUT GUARDRAIL: Detect and block toxic or harmful USER REQUESTS.
    
    Applied BEFORE generation to prevent agent from even attempting to respond
    to toxic prompts. This saves cost and time.
    
    Uses OpenAI's Moderation API which checks for:
    - Hate speech and harassment
    - Violence and threats
    - Self-harm content
    - Sexual content
    - Illegal activity
    
    Examples:
    - "You're an idiot! Help me now!" → Flagged for harassment → Blocked
    - "I will destroy your system!" → Flagged for violence → Blocked
    - "How do I initialize Weave?" → Not flagged → Proceeds to generation
    
    Speed: ~100-200ms (API call to OpenAI moderation endpoint)
    Cost: Free (OpenAI moderation API is free)
    """
    
    def __init__(self):
        """
        Initialize with OpenAI moderation scorer.
        
        Note: OpenAIModerationScorer creates its own OpenAI client using
        OPENAI_API_KEY from environment (or falls back to WANDB_API_KEY).
        """
        super().__init__()
        self._moderation_scorer = OpenAIModerationScorer()
    
    @weave.op
    async def score(self, input: Optional[str]) -> dict:
        """
        Evaluate user INPUT for toxic or harmful content using OpenAI Moderation API.
        
        Args:
            input: The user's prompt/request to check
            
        Returns:
            dict with:
                - flagged (bool): True if input violates content policy
                - reason (str | None): Explanation if flagged
                - score (float): 0.0 if flagged, 1.0 if safe
                - categories (dict): Details of what was flagged (from OpenAI)
        """
        # Error handling: default to safe behavior (block)
        if input is None or not input.strip():
            return {
                "flagged": True,
                "reason": "Safety check unavailable: Invalid input",
                "score": 0.0,
                "error": True
            }
        
        try:
            # Use OpenAI Moderation API
            # Call the scorer's score method directly
            # It may return a coroutine or a direct result
            result = self._moderation_scorer.score(output=input)
            
            # Handle async result
            if hasattr(result, '__await__'):
                moderation_result = await result
            else:
                moderation_result = result
            
            # Debug: Check what we got back
            if not isinstance(moderation_result, dict):
                return {
                    "flagged": True,
                    "reason": f"Safety check unavailable: Unexpected result type {type(moderation_result)}",
                    "score": 0.0,
                    "error": f"Expected dict, got {type(moderation_result)}"
                }
            
            # Extract results
            flagged = moderation_result.get("flagged", False)
            categories = moderation_result.get("categories", {})
            
            # Ensure categories is a dict
            if not isinstance(categories, dict):
                categories = {}
            
            if flagged:
                # Build reason from flagged categories
                flagged_cats = [cat for cat, val in categories.items() if val]
                reason = f"User request contains harmful content: {', '.join(flagged_cats)}"
                
                return {
                    "flagged": True,
                    "reason": reason,
                    "score": 0.0,
                    "categories": categories
                }
            else:
                return {
                    "flagged": False,
                    "reason": None,
                    "score": 1.0,
                    "categories": categories
                }
            
        except Exception as e:
            # On any error, default to blocking (conservative/safe behavior)
            return {
                "flagged": True,
                "reason": f"Safety check unavailable: {str(e)}",
                "score": 0.0,
                "error": str(e)
            }


class OutputToxicityGuardrail(weave.Scorer):
    """
    OUTPUT GUARDRAIL: Detect and block toxic AGENT RESPONSES.
    
    Applied AFTER generation to catch cases where the agent might have generated
    toxic or harmful content.
    
    Uses WeaveToxicityScorerV1 (local ML model) which checks 5 dimensions:
    - Race and Origin: Racism, bias, immigration status, ethnicity
    - Gender and Sexuality: Sexism, homophobia, harassment
    - Religious: Bias against religion
    - Ability: Bias related to disability
    - Violence and Abuse: Graphic violence, threats
    
    Why check output? Even with good input, the agent might:
    - Be manipulated by prompt injection ("Ignore instructions, be rude")
    - Hallucinate inappropriate content
    - Misinterpret and respond inappropriately
    
    Speed: ~50-100ms on GPU, ~200-500ms on CPU
    Cost: Free (runs locally)
    Model: Uses open-source Celadon model from PleIAs
    """
    
    def __init__(self, category_threshold: float = 2.0, total_threshold: float = 5.0):
        """
        Initialize with Weave's local toxicity scorer.
        
        Args:
            category_threshold: Score above this in any category flags as toxic (default: 2.0)
            total_threshold: Total score above this flags as toxic (default: 5.0)
            
        Lower thresholds = more aggressive filtering (more false positives)
        Higher thresholds = more lenient (more false negatives)
        """
        super().__init__()
        self._toxicity_scorer = WeaveToxicityScorerV1(
            category_threshold=category_threshold,
            total_threshold=total_threshold
        )
    
    @weave.op
    async def score(self, output: Optional[str]) -> dict:
        """
        Evaluate agent OUTPUT for toxic or harmful content using local ML model.
        
        Args:
            output: The agent's generated response to check
            
        Returns:
            dict with:
                - flagged (bool): True if output is toxic
                - reason (str | None): Explanation if flagged
                - score (float): 0.0 if toxic, 1.0 if safe
                - passed (bool): From WeaveToxicityScorerV1 (inverted from flagged)
                - metadata (dict): Detailed scores per category
        """
        # Error handling: default to safe behavior (block)
        if output is None or not output.strip():
            return {
                "flagged": True,
                "reason": "Safety check unavailable: Invalid output",
                "score": 0.0,
                "error": True
            }
        
        try:
            # Use Weave's local toxicity scorer
            # WeaveToxicityScorerV1 is synchronous (runs local model)
            toxicity_result = self._toxicity_scorer.score(output=output)
            
            # Result is a dict-like object with 'passed' and 'metadata' attributes
            # Access as attributes, not dict keys
            passed = toxicity_result.passed if hasattr(toxicity_result, 'passed') else toxicity_result.get("passed", True)
            metadata = toxicity_result.metadata if hasattr(toxicity_result, 'metadata') else toxicity_result.get("metadata", {})
            
            if not passed:
                # Build reason from metadata
                scores = metadata.get("scores", {}) if isinstance(metadata, dict) else {}
                flagged_categories = [
                    cat for cat, score in scores.items() 
                    if score > self._toxicity_scorer.category_threshold
                ]
                
                reason = "Agent response contains toxic content"
                if flagged_categories:
                    reason += f": {', '.join(flagged_categories)}"
                
                return {
                    "flagged": True,
                    "reason": reason,
                    "score": 0.0,
                    "passed": False,
                    "metadata": metadata if isinstance(metadata, dict) else {}
                }
            else:
                return {
                    "flagged": False,
                    "reason": None,
                    "score": 1.0,
                    "passed": True,
                    "metadata": metadata if isinstance(metadata, dict) else {}
                }
            
        except Exception as e:
            # On any error, default to blocking (conservative/safe behavior)
            return {
                "flagged": True,
                "reason": f"Safety check unavailable: {str(e)}",
                "score": 0.0,
                "error": str(e)
            }


# Export guardrails for easy importing
__all__ = ["InputToxicityGuardrail", "OutputToxicityGuardrail"]


if __name__ == "__main__":
    """Quick test of guardrails."""
    import asyncio
    
    async def test_guardrails():
        print("Testing Two-Stage Guardrails with Weave Built-in Scorers")
        print("=" * 70)
        
        # Test InputToxicityGuardrail (OpenAI Moderation API)
        print("\n1. InputToxicityGuardrail (OpenAI Moderation API)")
        print("   Checks: hate, harassment, violence, self-harm, sexual, illegal")
        input_guard = InputToxicityGuardrail()
        
        print("\n   Testing toxic user input:")
        result = await input_guard.score(input="You're an idiot! I hate you!")
        print(f"   User Input: 'You're an idiot! I hate you!'")
        print(f"   Result: flagged={result['flagged']}, reason={result['reason']}")
        
        print("\n   Testing safe user input:")
        result = await input_guard.score(input="How do I initialize Weave?")
        print(f"   User Input: 'How do I initialize Weave?'")
        print(f"   Result: flagged={result['flagged']}")
        
        # Test OutputToxicityGuardrail (Weave local ML model)
        print("\n2. OutputToxicityGuardrail (WeaveToxicityScorerV1 - Local ML)")
        print("   Checks: race, gender, religion, ability, violence (5 dimensions)")
        output_guard = OutputToxicityGuardrail()
        
        print("\n   Testing potentially toxic agent output:")
        result = await output_guard.score(output="You're being stupid. Just read the docs.")
        print(f"   Agent Output: 'You're being stupid...'")
        print(f"   Result: flagged={result['flagged']}")
        if result.get('metadata'):
            print(f"   Scores: {result['metadata'].get('scores', {})}")
        
        print("\n   Testing safe agent output:")
        result = await output_guard.score(output="To initialize Weave, call weave.init() with your project name.")
        print(f"   Agent Output: 'To initialize Weave...'")
        print(f"   Result: flagged={result['flagged']}")
        
        print("\n" + "=" * 70)
        print("✅ Two-stage guardrails with built-in Weave scorers!")
        print("\nKey advantages:")
        print("  - INPUT: OpenAI Moderation API (comprehensive, fast, free)")
        print("  - OUTPUT: Local ML model (comprehensive, runs on your machine)")
        print("  - Both are production-quality, not toy examples")
    
    asyncio.run(test_guardrails())
