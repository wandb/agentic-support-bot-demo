"""
Input guardrail for the W&B support bot.

Uses OpenAI's Moderation API to check user prompts BEFORE generation.
This blocks toxic requests early, saving cost and time while maintaining streaming UX.

Why only INPUT guardrail?
- INPUT guardrails block bad requests before generation (fast, doesn't break streaming)
- OUTPUT guardrails require full response to check (breaks streaming, worse UX)
- Modern LLMs rarely generate toxic content on their own
- This is the most common production pattern for streaming applications

Installation: pip install weave[scorers]
"""

import weave
from typing import Optional

# Import our fixed version of OpenAIModerationScorer
# (Weave's version has a bug on line 48 where it tries to iterate over a Pydantic model)
from fixed_moderation_scorer import FixedOpenAIModerationScorer

class InputToxicityGuardrail(weave.Scorer):
    """
    INPUT GUARDRAIL: Detect and block toxic or harmful USER REQUESTS.
    
    Applied BEFORE generation to prevent agent from even attempting to respond
    to toxic prompts. This saves cost and time.
    
    Uses OpenAI's Moderation API (via our fixed version of OpenAIModerationScorer)
    which checks for:
    - Hate speech and harassment
    - Violence and threats
    - Self-harm content
    - Sexual content
    - Illegal activity
    
    Note: We use a local fixed version of OpenAIModerationScorer because Weave's
    built-in version has a bug (line 48 tries to iterate over Pydantic model).
    
    Examples:
    - "You're an idiot! Help me now!" → Flagged for harassment → Blocked
    - "I will destroy your system!" → Flagged for violence → Blocked
    - "How do I initialize Weave?" → Not flagged → Proceeds to generation
    
    Speed: ~100-200ms (API call to OpenAI moderation endpoint)
    Cost: Free (OpenAI moderation API is free)
    """
    
    def __init__(self):
        """
        Initialize with our fixed OpenAI moderation scorer.
        
        Note: Uses OPENAI_API_KEY from environment.
        """
        super().__init__()
        self._moderation_scorer = FixedOpenAIModerationScorer()
    
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
            # Use OpenAI Moderation API via Weave's scorer
            # OpenAIModerationScorer.score() is async and returns dict with 'passed' and 'categories'
            moderation_result = await self._moderation_scorer.score(output=input)
            
            # Extract results - it's a plain dict
            passed = moderation_result.get("passed", True)
            categories = moderation_result.get("categories", {})
            
            # OpenAI returns passed=True if safe, passed=False if flagged
            flagged = not passed
            
            if flagged:
                # Build reason from flagged categories
                flagged_cats = list(categories.keys()) if categories else []
                reason = f"User request contains harmful content: {', '.join(flagged_cats)}" if flagged_cats else "User request flagged by moderation"
                
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


# Export guardrail for easy importing
__all__ = ["InputToxicityGuardrail"]


if __name__ == "__main__":
    """Quick test of input guardrail."""
    import asyncio
    
    async def test_guardrail():
        print("Testing Input Guardrail with OpenAI Moderation API")
        print("=" * 70)
        
        # Test InputToxicityGuardrail
        print("\nInputToxicityGuardrail (OpenAI Moderation API)")
        print("Checks: hate, harassment, violence, self-harm, sexual, illegal")
        input_guard = InputToxicityGuardrail()
        
        print("\n   Testing toxic user input:")
        result = await input_guard.score(input="You're an idiot! I hate you!")
        print(f"   User Input: 'You're an idiot! I hate you!'")
        print(f"   Result: flagged={result['flagged']}, reason={result['reason']}")
        
        print("\n   Testing safe user input:")
        result = await input_guard.score(input="How do I initialize Weave?")
        print(f"   User Input: 'How do I initialize Weave?'")
        print(f"   Result: flagged={result['flagged']}")
        
        print("\n" + "=" * 70)
        print("✅ Input guardrail working!")
        print("\nKey advantages:")
        print("  - Blocks toxic requests BEFORE generation")
        print("  - Fast (~100-200ms)")
        print("  - Maintains streaming UX")
        print("  - Most common production pattern")
    
    asyncio.run(test_guardrail())
