"""Sequential LLM-based hierarchical tweet classifier."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import List

from shared.taxonomy import get_registry

from .llm_client import LLMClient
from .prompt_builder import PromptBuilder


@dataclass(slots=True)
class ClassificationResult:
    tweet_id: str
    text: str
    level1: str
    level2: List[str]
    conf_l1: float
    conf_l2: float
    version: str = "v1-seq-llm"


class HierarchicalClassifier:  # noqa: D101
    _LOW_CONFIDENCE_THRESHOLD = 0.3

    def __init__(
        self,
        llm_client: LLMClient,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self._llm = llm_client
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._registry = get_registry()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def classify(self, tweet_id: str, tweet_text: str) -> ClassificationResult:  # noqa: D401
        """Classify *tweet_text* into Level-1 and Level-2 categories."""
        # --- Level-1 -----------------------------------------------
        l1_msgs = self._prompt_builder.build_level1_prompt(tweet_text)
        l1_raw = self._llm.chat_completion(l1_msgs)
        l1_result = self._safe_json_load(l1_raw, stage="L1")
        level1: str = l1_result.get("level1")
        conf_l1: float = float(l1_result.get("confidence", 1.0))

        if conf_l1 < self._LOW_CONFIDENCE_THRESHOLD:
            logging.warning("Low L1 confidence %.2f for tweet %s", conf_l1, tweet_id)
            return ClassificationResult(tweet_id, tweet_text, "Uncertain", [], conf_l1, 0.0)

        if level1 not in self._registry.level1_categories():
            logging.warning("Invalid L1 category '%s' from model", level1)
            level1 = "Other"

        # --- Level-2 -----------------------------------------------
        l2_msgs = self._prompt_builder.build_level2_prompt(tweet_text, level1)
        l2_raw = self._llm.chat_completion(l2_msgs)
        l2_result = self._safe_json_load(l2_raw, stage="L2")
        level2 = l2_result.get("level2", [])
        if isinstance(level2, str):
            level2 = [level2]
        level2 = [sub for sub in level2 if sub in self._registry.subcategories(level1)]
        conf_l2: float = float(l2_result.get("confidence", 1.0)) if level2 else 0.0

        return ClassificationResult(tweet_id, tweet_text, level1, level2, conf_l1, conf_l2)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _safe_json_load(raw: str, stage: str) -> dict:  # noqa: D401
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            logging.error("%s JSON parse error: %s", stage, exc)
            # Attempt quick fix by trimming leading/trailing text
            brace_start = raw.find("{")
            brace_end = raw.rfind("}")
            if brace_start >= 0 and brace_end > brace_start:
                try:
                    return json.loads(raw[brace_start : brace_end + 1])
                except json.JSONDecodeError:
                    pass
            raise 