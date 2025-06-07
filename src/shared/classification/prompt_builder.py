"""Prompt builder utilities for the hierarchical tweet classifier."""
from __future__ import annotations

from textwrap import dedent
from typing import List

from shared.taxonomy import get_registry

_SYSTEM_MESSAGE = (
    "You are an expert taxonomy classifier for GenAI tweets. "
    "Return answers as valid JSON matching the requested schema. "
    "No extra keys, no commentary."
)


class PromptBuilder:
    """Factory for classification prompts based on the global taxonomy."""

    def __init__(self, registry=None):
        self._registry = registry or get_registry()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def build_level1_prompt(self, tweet_text: str) -> List[dict]:  # noqa: D401
        """Return OpenAI-style messages for the Level-1 classification call."""
        level1_lines = [
            f"{idx + 1}. {name}" for idx, name in enumerate(self._registry.level1_categories())
        ]
        user_content = dedent(
            f"""
            TWEET: "{tweet_text}"

            Below is the complete set of Level-1 themes. Choose the single best theme.
            Respond with: {{"level1": "<Theme>", "confidence": <0-1 float>}}

            LEVEL-1 THEMES
            {chr(10).join(level1_lines)}
            """
        ).strip()
        return [{"role": "system", "content": _SYSTEM_MESSAGE}, {"role": "user", "content": user_content}]

    def build_level2_prompt(self, tweet_text: str, level1: str) -> List[dict]:  # noqa: D401
        """Return messages for the Level-2 classification call."""
        subs = self._registry.subcategories(level1)
        sub_lines = [f"{idx + 1}. {name}" for idx, name in enumerate(subs)]
        user_content = dedent(
            f"""
            TWEET: "{tweet_text}"
            The tweet was classified as Level-1 = "{level1}".
            Below are its Level-2 sub-themes. You may pick zero or more.
            Respond with: {{"level2": ["<Sub1>", …], "confidence": <0-1 float>}}

            SUB-THEMES FOR {level1}
            {chr(10).join(sub_lines)}
            """
        ).strip()
        return [{"role": "system", "content": _SYSTEM_MESSAGE}, {"role": "user", "content": user_content}] 