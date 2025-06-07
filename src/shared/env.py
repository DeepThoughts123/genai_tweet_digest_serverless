"""Environment variable accessor with cached values."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional


@lru_cache(maxsize=None)
def get(key: str, default: Optional[str] = None) -> str:  # noqa: D401
    """Return the environment variable *key* or *default*.

    Uses an LRU cache so lookups are cheap.
    """
    return os.getenv(key, default) or "" 