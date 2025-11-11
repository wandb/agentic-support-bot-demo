"""
Fixed version of Weave's OpenAIModerationScorer.

This is a local copy with the bug fix applied to line 48.

Original bug:
    for k, v in response.categories  # ❌ response.categories is a Pydantic model, not iterable of tuples

Fixed version:
    for k, v in response.categories.model_dump().items()  # ✅ Properly iterate over dict items

Once Weave fixes this in their library, we can remove this file and use their version.
"""

from typing import Any
from pydantic import Field
import weave
from weave.scorers.scorer_types import LLMScorer
from weave.scorers.default_models import OPENAI_DEFAULT_MODERATION_MODEL


class FixedOpenAIModerationScorer(LLMScorer):
    """Fixed version of OpenAI Moderation API scorer.

    Uses the OpenAI moderation API to check if the model output is safe.
    This scorer sends the provided output to the OpenAI moderation API and returns a structured response
    indicating whether the output contains unsafe content.

    Note: Pass the text to be scored to this Scorer's `output` parameter in the `score` method.

    Attributes:
        model_id (str): The OpenAI moderation model identifier to be used. Defaults to `OPENAI_DEFAULT_MODERATION_MODEL`.
    """

    model_id: str = Field(
        description="The OpenAI moderation model identifier to be used.",
        default=OPENAI_DEFAULT_MODERATION_MODEL,
    )

    @weave.op
    async def score(self, *, output: str, **kwargs: Any) -> dict:
        """Score the given text against the OpenAI moderation API.

        Args:
            output: text to check for moderation, must be a string

        Returns:
            dict with:
                - passed (bool): True if content is safe, False if flagged
                - categories (dict): Dictionary of flagged categories
        """
        response = await self._amoderation(
            model=self.model_id,
            input=output,
        )

        response = response.results[0]
        passed = not response.flagged
        
        # ✅ FIX: Convert Pydantic model to dict before iterating
        categories_dict = response.categories.model_dump() if hasattr(response.categories, 'model_dump') else dict(response.categories)
        
        categories = {
            k: v
            for k, v in categories_dict.items()  # ✅ Now properly iterating over dict items
            if v and ("/" not in k and "-" not in k)
        }

        return {"passed": passed, "categories": categories}

