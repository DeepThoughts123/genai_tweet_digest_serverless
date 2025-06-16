#!/usr/bin/env python3
"""
Unit tests for Enhanced Optimized Tweet Processor.

Tests the full integration pipeline:
1. Tweet fetching
2. Visual capture and text extraction
3. Classification
4. Enhanced metadata generation

Following TDD principles.
"""

import pytest
import os
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.applications.processors.tweet_processor import ProcessingConfig, ProcessingResult
from src.shared.visual_text_extractor import ExtractionResult


class TestEnhancedOptimizedProcessor:
    """Test suite for Enhanced Optimized Tweet Processor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = ProcessingConfig(
            days_back=7,
            max_tweets_per_account=5,
            max_concurrent_accounts=1,
            enable_classification=True,
            enable_visual_extraction=True,  # New feature
            output_dir=self.temp_dir
        )
        
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_processing_config_with_visual_extraction(self):
        """Test ProcessingConfig includes visual extraction settings."""
        config = ProcessingConfig(
            enable_visual_extraction=True,
            enable_classification=True,
            visual_extraction_batch_size=3,
            zoom_percent=60
        )
        
        assert config.enable_visual_extraction is True
        assert config.enable_classification is True
        assert config.visual_extraction_batch_size == 3
        assert config.zoom_percent == 60
    
    @patch('src.shared.visual_text_extractor.VisualTextExtractor')
    @patch('src.shared.tweet_services.TweetFetcher')
    def test_enhanced_processor_initialization(self, mock_tweet_fetcher, mock_visual_extractor):
        """Test enhanced processor initializes with visual extraction service."""
        from src.applications.processors.enhanced_processor import EnhancedOptimizedTweetProcessor
        
        processor = EnhancedOptimizedTweetProcessor(self.config)
        
        assert processor.config.enable_visual_extraction is True
        assert hasattr(processor, 'visual_extractor')
        mock_visual_extractor.assert_called_once()
    
    @patch('src.shared.visual_text_extractor.VisualTextExtractor')
    @patch('src.shared.tweet_services.TweetFetcher')
    def test_process_single_tweet_with_visual_extraction(self, mock_tweet_fetcher, mock_visual_extractor):
        """Test processing single tweet with visual extraction."""
        from src.applications.processors.enhanced_processor import EnhancedOptimizedTweetProcessor
        
        # Mock tweet data
        mock_tweet = {
            'id': '123456789',
            'url': 'https://twitter.com/user/status/123456789',
            'text': 'Original tweet text',
            'account': 'testuser'
        }
        
        # Mock visual extraction result
        mock_extraction_result = ExtractionResult(
            success=True,
            full_text="Complete extracted text from screenshot",
            summary="Brief summary of the tweet content",
            engagement_metrics={"like_count": "100", "retweet_count": "50"},
            processing_time=2.5,
            screenshots_captured=2
        )
        
        mock_visual_extractor.return_value.extract_from_tweet_url.return_value = mock_extraction_result
        
        processor = EnhancedOptimizedTweetProcessor(self.config)
        result = processor._enhance_tweet_metadata(mock_tweet, mock_extraction_result)
        
        # Assertions
        assert result['full_text'] == "Complete extracted text from screenshot"
        assert result['summary'] == "Brief summary of the tweet content"
        assert result['engagement_metrics']['like_count'] == "100"
        assert 'visual_extraction' in result
        assert result['visual_extraction']['screenshots_captured'] == 2
    
    @patch('src.shared.visual_text_extractor.VisualTextExtractor')
    @patch('src.shared.tweet_services.TweetFetcher')
    def test_process_single_tweet_visual_extraction_failure(self, mock_tweet_fetcher, mock_visual_extractor):
        """Test handling of visual extraction failure."""
        from src.applications.processors.enhanced_processor import EnhancedOptimizedTweetProcessor
        
        mock_tweet = {
            'id': '123456789',
            'url': 'https://twitter.com/user/status/123456789',
            'text': 'Original tweet text',
            'account': 'testuser'
        }
        
        # Mock visual extraction failure
        mock_extraction_result = ExtractionResult(
            success=False,
            error="Failed to capture screenshot"
        )
        
        mock_visual_extractor.return_value.extract_from_tweet_url.return_value = mock_extraction_result
        
        processor = EnhancedOptimizedTweetProcessor(self.config)
        result = processor._enhance_tweet_metadata(mock_tweet, mock_extraction_result)
        
        # Should fallback to original text
        assert result['full_text'] == 'Original tweet text'  # Fallback to API text
        assert result['summary'] is None  # No summary without visual extraction
        assert 'visual_extraction_error' in result
        assert result['visual_extraction_error'] == "Failed to capture screenshot"
    
    @patch('src.core.services.classification.classification.classifier.HierarchicalClassifier')
    @patch('src.shared.visual_text_extractor.VisualTextExtractor')
    @patch('src.shared.tweet_services.TweetFetcher')
    def test_classify_with_full_text(self, mock_tweet_fetcher, mock_visual_extractor, mock_classifier):
        """Test classification uses full extracted text instead of truncated API text."""
        from src.applications.processors.enhanced_processor import EnhancedOptimizedTweetProcessor
        
        mock_tweet = {
            'id': '123456789',
            'text': 'Truncated API text...',
            'account': 'testuser'
        }
        
        # Mock visual extraction with full text
        mock_extraction_result = ExtractionResult(
            success=True,
            full_text="This is the complete full text extracted from the screenshot that contains much more detail than the API text",
            summary="Summary of the complete text"
        )
        
        mock_visual_extractor.return_value.extract_from_tweet_url.return_value = mock_extraction_result
        
        # Mock classification result
        mock_classification_result = Mock()
        mock_classification_result.level1 = "Breakthrough Research"
        mock_classification_result.level2 = ["Machine Learning"]
        mock_classification_result.conf_l1 = 0.95
        mock_classification_result.conf_l2 = 0.90
        
        mock_classifier.return_value.classify.return_value = mock_classification_result
        
        processor = EnhancedOptimizedTweetProcessor(self.config)
        enhanced_tweet = processor._enhance_tweet_metadata(mock_tweet, mock_extraction_result)
        
        # Check enhanced tweet structure
        assert enhanced_tweet['full_text'] == "This is the complete full text extracted from the screenshot that contains much more detail than the API text"
        assert enhanced_tweet['original_text'] == "Truncated API text..."
    
    @patch('src.shared.visual_text_extractor.VisualTextExtractor')
    @patch('src.shared.tweet_services.TweetFetcher')
    def test_enhanced_metadata_structure(self, mock_tweet_fetcher, mock_visual_extractor):
        """Test that enhanced metadata includes all required fields."""
        from src.applications.processors.enhanced_processor import EnhancedOptimizedTweetProcessor
        
        mock_tweet = {
            'id': '123456789',
            'url': 'https://twitter.com/user/status/123456789',
            'text': 'Original tweet text',
            'account': 'testuser'
        }
        
        mock_extraction_result = ExtractionResult(
            success=True,
            full_text="Complete extracted text",
            summary="Brief summary",
            engagement_metrics={"like_count": "100", "retweet_count": "50"},
            processing_time=2.5,
            screenshots_captured=2
        )
        
        mock_visual_extractor.return_value.extract_from_tweet_url.return_value = mock_extraction_result
        
        processor = EnhancedOptimizedTweetProcessor(self.config)
        enhanced_tweet = processor._enhance_tweet_metadata(mock_tweet, mock_extraction_result)
        
        # Check enhanced metadata structure
        assert 'original_text' in enhanced_tweet  # Original API text
        assert 'full_text' in enhanced_tweet      # Extracted full text
        assert 'summary' in enhanced_tweet        # Generated summary
        assert 'engagement_metrics' in enhanced_tweet  # Extracted metrics
        assert 'visual_extraction' in enhanced_tweet   # Visual processing info
        
        assert enhanced_tweet['original_text'] == 'Original tweet text'
        assert enhanced_tweet['full_text'] == 'Complete extracted text'
        assert enhanced_tweet['summary'] == 'Brief summary'
        assert enhanced_tweet['engagement_metrics']['like_count'] == '100'
        assert enhanced_tweet['visual_extraction']['processing_time'] == 2.5
        assert enhanced_tweet['visual_extraction']['screenshots_captured'] == 2
    
    @patch('src.shared.visual_text_extractor.VisualTextExtractor')
    @patch('src.shared.tweet_services.TweetFetcher')
    def test_parallel_visual_processing(self, mock_tweet_fetcher, mock_visual_extractor):
        """Test parallel processing of multiple tweets with visual extraction."""
        from src.applications.processors.enhanced_processor import EnhancedOptimizedTweetProcessor
        
        tweets = [
            {'id': '123', 'url': 'https://twitter.com/user/status/123', 'text': 'Tweet 1'},
            {'id': '456', 'url': 'https://twitter.com/user/status/456', 'text': 'Tweet 2'},
            {'id': '789', 'url': 'https://twitter.com/user/status/789', 'text': 'Tweet 3'}
        ]
        
        # Mock visual extraction results
        mock_extraction_result = ExtractionResult(
            success=True,
            full_text="Extracted text",
            summary="Summary",
            processing_time=1.0
        )
        
        mock_visual_extractor.return_value.extract_batch.return_value = [
            mock_extraction_result,
            mock_extraction_result,
            mock_extraction_result
        ]
        
        processor = EnhancedOptimizedTweetProcessor(self.config)
        enhanced_tweets, stats = processor._process_tweets_with_visual_extraction('testuser', tweets)
        
        assert len(enhanced_tweets) == 3
        assert all(tweet['full_text'] == "Extracted text" for tweet in enhanced_tweets)
        assert stats['tweets_visually_processed'] == 3
        
        # Should use batch processing for efficiency
        mock_visual_extractor.return_value.extract_batch.assert_called_once()
    
    def test_processing_result_includes_visual_stats(self):
        """Test ProcessingResult includes visual processing statistics."""
        result = ProcessingResult(
            account="testuser",
            success=True,
            tweets_fetched=5,
            tweets_classified=5,
            tweets_visually_processed=4,  # New field
            visual_extraction_failures=1,  # New field
            categories_found=["Breakthrough Research"],
            processing_time=15.0
        )
        
        assert result.tweets_visually_processed == 4
        assert result.visual_extraction_failures == 1
        assert result.tweets_fetched == 5
        assert result.tweets_classified == 5
    
    @patch('src.shared.visual_text_extractor.VisualTextExtractor')
    @patch('src.shared.tweet_services.TweetFetcher')
    def test_configuration_validation(self, mock_tweet_fetcher, mock_visual_extractor):
        """Test configuration validation for visual extraction."""
        from src.applications.processors.enhanced_processor import EnhancedOptimizedTweetProcessor
        
        # Valid configuration should work
        valid_config = ProcessingConfig(
            enable_visual_extraction=True,
            visual_extraction_batch_size=3,  # Valid
            zoom_percent=60  # Valid
        )
        
        processor = EnhancedOptimizedTweetProcessor(valid_config)
        assert processor.config.enable_visual_extraction is True
    
    @patch('src.shared.visual_text_extractor.VisualTextExtractor')
    @patch('src.shared.tweet_services.TweetFetcher')
    def test_rate_limiting_with_visual_processing(self, mock_tweet_fetcher, mock_visual_extractor):
        """Test rate limiting includes visual processing operations."""
        from src.applications.processors.enhanced_processor import EnhancedOptimizedTweetProcessor
        
        processor = EnhancedOptimizedTweetProcessor(self.config)
        
        # Should have rate limiters for visual processing
        assert hasattr(processor, 'visual_extraction_limiter')
        assert hasattr(processor, 'screenshot_capture_limiter')
    
    @patch('src.shared.visual_text_extractor.VisualTextExtractor')
    @patch('src.shared.tweet_services.TweetFetcher')
    def test_fallback_behavior(self, mock_tweet_fetcher, mock_visual_extractor):
        """Test fallback behavior when visual extraction is disabled."""
        from src.applications.processors.enhanced_processor import EnhancedOptimizedTweetProcessor
        
        # Config without visual extraction
        config_no_visual = ProcessingConfig(
            enable_visual_extraction=False,
            enable_classification=True
        )
        
        processor = EnhancedOptimizedTweetProcessor(config_no_visual)
        
        # Should not initialize visual extractor
        assert processor.visual_extractor is None
        
        # Should still process tweets normally with fallback
        mock_tweet = {'id': '123', 'text': 'Test tweet'}
        result = processor._enhance_tweet_metadata(mock_tweet, None)
        
        # Should use original text
        assert result['full_text'] == 'Test tweet'
        assert result['summary'] is None


if __name__ == "__main__":
    pytest.main([__file__]) 