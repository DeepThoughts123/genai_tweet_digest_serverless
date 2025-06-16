"""
Shared libraries for GenAI Tweet Digest application.

This module provides common functionality used across both Lambda and Fargate components.
"""

# Version information
__version__ = "2.0.0"

# Make core services easily importable
from .config.settings import config
from .tweet_services import TweetFetcher, TweetCategorizer, TweetSummarizer, S3DataManager
# TODO: Complete service reorganization - temporarily commented out
# from ..infrastructure.persistence.dynamodb.subscription_store import SubscriberService
# from ..infrastructure.email.ses_client import SESEmailService
# from ..infrastructure.external.selenium_client import VisualTweetCaptureService
from .processing_orchestrator import ProcessingOrchestrator

__all__ = [
    'config',
    'TweetFetcher',
    'TweetCategorizer', 
    'TweetSummarizer',
    'S3DataManager',
    # 'SubscriberService',
    # 'SESEmailService',
    # 'VisualTweetCaptureService',
    'ProcessingOrchestrator'
] 