"""
Lazy import wrapper for heavy dependencies.
Only imports AI services when actually needed, improving cold start times.
"""

import importlib
from typing import Optional, Any

class LazyTweetServices:
    """Lazy loader for heavy tweet processing services."""
    
    def __init__(self):
        self._tweet_fetcher: Optional[Any] = None
        self._tweet_categorizer: Optional[Any] = None
        self._tweet_summarizer: Optional[Any] = None
        self._s3_data_manager: Optional[Any] = None
    
    @property
    def tweet_fetcher(self):
        """Lazy load TweetFetcher only when needed."""
        if self._tweet_fetcher is None:
            from .tweet_services import TweetFetcher
            self._tweet_fetcher = TweetFetcher()
        return self._tweet_fetcher
    
    @property
    def tweet_categorizer(self):
        """Lazy load TweetCategorizer only when needed."""
        if self._tweet_categorizer is None:
            from .tweet_services import TweetCategorizer
            self._tweet_categorizer = TweetCategorizer()
        return self._tweet_categorizer
    
    @property
    def tweet_summarizer(self):
        """Lazy load TweetSummarizer only when needed."""
        if self._tweet_summarizer is None:
            from .tweet_services import TweetSummarizer
            self._tweet_summarizer = TweetSummarizer()
        return self._tweet_summarizer
    
    @property 
    def s3_data_manager(self):
        """Lazy load S3DataManager only when needed."""
        if self._s3_data_manager is None:
            from .tweet_services import S3DataManager
            self._s3_data_manager = S3DataManager()
        return self._s3_data_manager

# Singleton instance for reuse across Lambda invocations
lazy_services = LazyTweetServices()

def get_tweet_services():
    """Get lazy-loaded tweet services."""
    return lazy_services 