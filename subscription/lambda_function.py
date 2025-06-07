"""Compatibility shim exposing Subscription Lambda handler for legacy tests."""
from __future__ import annotations

from src.lambda_functions.subscription.handler import (
    lambda_handler as lambda_handler,  # noqa: F401
    get_subscriber_count_handler as get_subscriber_count_handler,  # noqa: F401
)

from src.shared.config import config as config  # noqa: F401
from src.shared.dynamodb_service import SubscriberService as SubscriberService  # noqa: F401 