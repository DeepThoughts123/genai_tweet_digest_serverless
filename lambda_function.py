"""Compatibility shim for legacy tests expecting a top-level ``lambda_function`` module.

This module simply re-exports the public interface of the email-verification
Lambda handler located under ``src.lambda_functions.email_verification``.
"""
from __future__ import annotations

from src.lambda_functions.email_verification.handler import (
    lambda_handler as lambda_handler,  # noqa: F401 re-export
    get_success_html as get_success_html,  # noqa: F401
    get_error_html as get_error_html,  # noqa: F401
)

from src.shared.config import config as config  # noqa: F401
from src.shared.email_verification_service import (  # noqa: F401
    EmailVerificationService as EmailVerificationService,
) 