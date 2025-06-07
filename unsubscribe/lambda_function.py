"""Compatibility shim for Unsubscribe Lambda handler in legacy tests."""
from __future__ import annotations

from src.lambda_functions.unsubscribe.handler import lambda_handler as lambda_handler  # noqa: F401

from src.shared.config import config as config  # noqa: F401 