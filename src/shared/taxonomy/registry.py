"""Category registry handling the 2-level tweet-classification taxonomy.

This module provides a light-weight, process-wide singleton `CategoryRegistry` that
parses the ``categories.json`` file at import time (or first access) and offers
helper methods to retrieve Level-1 themes and their Level-2 sub-themes.

The JSON file may contain curly quotes, which are not strictly valid JSON.  If a
first-pass ``json.loads`` fails, we automatically normalise curly quotes to
straight quotes before retrying so that documentation writers can continue using
typographic punctuation without breaking the service.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Sequence

_JSON_PATH: Path = Path(__file__).with_suffix("").parent / "categories.json"

_CURLED_QUOTES_PATTERN = re.compile(r"[“”]")


def _load_categories(path: Path) -> List[Dict]:
    """Load and return the raw taxonomy list from *path*.

    The loader attempts a strict JSON parse first.  If that fails, it will
    replace curly quotes with straight quotes and attempt to parse again before
    surfacing the original exception.
    """
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        # Attempt a tolerant parse by normalising curly quotes.
        fixed = _CURLED_QUOTES_PATTERN.sub("'", text)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            raise exc from None


class CategoryRegistry:
    """Singleton container for taxonomy lookup operations."""

    _instance: "CategoryRegistry | None" = None

    # ---------------------------------------------------------------------
    # Construction helpers
    # ---------------------------------------------------------------------
    def __new__(cls, *args, **kwargs):  # noqa: D401
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # pylint: disable=unused-argument
    def __init__(self, json_path: Path | None = None) -> None:  # noqa: D401
        if getattr(self, "_initialised", False):
            # Avoid re-initialisation in the singleton.
            return
        path = json_path or _JSON_PATH
        self._categories: List[Dict] = _load_categories(path)
        self._build_lookup_tables()
        self._initialised = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def level1_categories(self) -> List[str]:
        """Return the list of Level-1 category names."""
        return self._level1_names.copy()

    def subcategories(self, level1_name: str) -> List[str]:
        """Return Level-2 sub-category names for *level1_name*.

        Raises
        ------
        ValueError
            If *level1_name* is unknown.
        """
        try:
            return self._subs_by_level1[level1_name].copy()
        except KeyError as exc:
            raise ValueError(f"Unknown Level-1 category: {level1_name!r}") from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_lookup_tables(self) -> None:
        self._level1_names: List[str] = []
        self._subs_by_level1: Dict[str, List[str]] = {}

        for level1 in self._categories:
            name = level1["name"]
            self._level1_names.append(name)
            self._subs_by_level1[name] = [sub["name"] for sub in level1.get("subcategories", [])]


# -------------------------------------------------------------------------
# Convenience helper
# -------------------------------------------------------------------------

def get_registry() -> CategoryRegistry:
    """Return the process-wide :class:`CategoryRegistry` instance."""

    return CategoryRegistry() 