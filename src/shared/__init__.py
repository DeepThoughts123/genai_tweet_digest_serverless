"""
Shared libraries for GenAI Tweet Digest application.

This module provides common functionality used across both Lambda and Fargate components.
"""

# Version information
__version__ = "2.0.0"

# Make core services easily importable
from .config import config
from .tweet_services import TweetFetcher, TweetCategorizer, TweetSummarizer, S3DataManager
from .dynamodb_service import SubscriberService
from .ses_service import SESEmailService
from .visual_tweet_capture_service import VisualTweetCaptureService
from .processing_orchestrator import ProcessingOrchestrator

__all__ = [
    'config',
    'TweetFetcher',
    'TweetCategorizer', 
    'TweetSummarizer',
    'S3DataManager',
    'SubscriberService',
    'SESEmailService',
    'VisualTweetCaptureService',
    'ProcessingOrchestrator'
] 