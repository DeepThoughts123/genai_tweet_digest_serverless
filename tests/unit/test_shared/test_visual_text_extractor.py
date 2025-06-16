#!/usr/bin/env python3
"""
Unit tests for VisualTextExtractor service.

Tests the integrated visual capture and text extraction functionality
following TDD principles.
"""

import pytest
import os
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from shared.visual_text_extractor import VisualTextExtractor, ExtractionResult
from PIL import Image


class TestVisualTextExtractor:
    """Test suite for VisualTextExtractor service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_api_key = "test_gemini_api_key_12345"
        
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initialization_with_valid_api_key(self):
        """Test VisualTextExtractor initializes correctly with valid API key."""
        with patch('shared.visual_text_extractor.genai') as mock_genai:
            extractor = VisualTextExtractor(api_key=self.mock_api_key)
            
            assert extractor.api_key == self.mock_api_key
            mock_genai.configure.assert_called_once_with(api_key=self.mock_api_key)
    
    def test_initialization_without_api_key_raises_error(self):
        """Test VisualTextExtractor raises error when no API key provided."""
        with pytest.raises(ValueError, match="Missing Gemini API key"):
            VisualTextExtractor(api_key=None)
    
    @patch('shared.visual_text_extractor.genai')
    def test_extract_from_tweet_url_success(self, mock_genai):
        """Test successful text extraction from tweet URL."""
        # Setup
        extractor = VisualTextExtractor(api_key=self.mock_api_key)
        
        # Mock the core methods directly
        with patch.object(extractor, '_capture_tweet_screenshots') as mock_capture, \
             patch.object(extractor, '_extract_text_and_summary_from_screenshots') as mock_extract:
            
            # Mock screenshot capture
            mock_capture.return_value = ['/fake/screenshot1.png', '/fake/screenshot2.png']
            
            # Mock text extraction
            mock_extract.return_value = ExtractionResult(
                success=True,
                full_text="Sample tweet text",
                summary="Tweet summary",
                engagement_metrics={
                    'reply_count': "10",
                    'retweet_count': "5", 
                    'like_count': "100",
                    'bookmark_count': "20"
                }
            )
            
            # Test
            result = extractor.extract_from_tweet_url(
                tweet_url="https://twitter.com/user/status/123", 
                tweet_id="123"
            )
        
        # Assertions
        assert isinstance(result, ExtractionResult)
        assert result.success is True
        assert result.full_text == "Sample tweet text"
        assert result.summary == "Tweet summary"
        assert result.engagement_metrics['reply_count'] == "10"
        assert result.engagement_metrics['like_count'] == "100"
        assert result.screenshots_captured == 2
    
    @patch('shared.visual_text_extractor.genai')
    def test_extract_from_tweet_url_failure(self, mock_genai):
        """Test handling of extraction failure."""
        # Setup
        extractor = VisualTextExtractor(api_key=self.mock_api_key)
        
        # Mock the screenshot capture to fail
        with patch.object(extractor, '_capture_tweet_screenshots') as mock_capture:
            mock_capture.side_effect = Exception("Browser error")
            
            result = extractor.extract_from_tweet_url(
                tweet_url="https://twitter.com/user/status/123", 
                tweet_id="123"
            )
        
        # Assertions
        assert isinstance(result, ExtractionResult)
        assert result.success is False
        assert result.error is not None
        assert "Browser error" in result.error
    
    @patch('shared.visual_text_extractor.genai')
    def test_parse_extraction_response_valid_json(self, mock_genai):
        """Test parsing valid JSON response from LLM."""
        extractor = VisualTextExtractor(api_key=self.mock_api_key)
        
        response_text = '''```json
        {
            "full_text": "Complete tweet text here",
            "summary": "Brief summary",
            "reply_count": "5",
            "retweet_count": "2",
            "like_count": "50",
            "bookmark_count": "10"
        }
        ```'''
        
        result = extractor._parse_extraction_response(response_text)
        
        assert result.success is True
        assert result.full_text == "Complete tweet text here"
        assert result.summary == "Brief summary"
        assert result.engagement_metrics['reply_count'] == "5"
        assert result.engagement_metrics['like_count'] == "50"
    
    @patch('shared.visual_text_extractor.genai')
    def test_parse_extraction_response_invalid_json(self, mock_genai):
        """Test handling of invalid JSON response."""
        extractor = VisualTextExtractor(api_key=self.mock_api_key)
        
        response_text = "This is not valid JSON"
        
        result = extractor._parse_extraction_response(response_text)
        
        assert result.success is False
        assert result.error is not None
        assert "JSON" in result.error
    
    @patch('shared.visual_text_extractor.genai')
    def test_capture_screenshots_creates_files(self, mock_genai):
        """Test that screenshot capture creates files."""
        with patch('shared.visual_text_extractor.webdriver') as mock_webdriver:
            mock_driver = Mock()
            mock_webdriver.Chrome.return_value = mock_driver
            mock_driver.save_screenshot = Mock()
            
            extractor = VisualTextExtractor(api_key=self.mock_api_key)
            screenshots = extractor._capture_tweet_screenshots(
                tweet_url="https://twitter.com/user/status/123",
                tweet_id="123",
                output_dir=self.temp_dir
            )
            
            # Should attempt to take screenshots
            assert mock_driver.save_screenshot.called
    
    @patch('shared.visual_text_extractor.genai')
    def test_extract_batch_processing(self, mock_genai):
        """Test batch processing of multiple tweets."""
        with patch('shared.visual_text_extractor.webdriver'):
            extractor = VisualTextExtractor(api_key=self.mock_api_key)
            
            tweets = [
                {"id": "123", "url": "https://twitter.com/user/status/123"},
                {"id": "456", "url": "https://twitter.com/user/status/456"}
            ]
            
            with patch.object(extractor, 'extract_from_tweet_url') as mock_extract:
                mock_extract.return_value = ExtractionResult(
                    success=True,
                    full_text="Sample text",
                    summary="Sample summary",
                    engagement_metrics={"like_count": "10"}
                )
                
                results = extractor.extract_batch(tweets)
                
                assert len(results) == 2
                assert mock_extract.call_count == 2
    
    def test_extraction_result_dataclass(self):
        """Test ExtractionResult dataclass functionality."""
        result = ExtractionResult(
            success=True,
            full_text="Test text",
            summary="Test summary",
            engagement_metrics={"likes": "10"},
            processing_time=1.5
        )
        
        assert result.success is True
        assert result.full_text == "Test text"
        assert result.summary == "Test summary"
        assert result.engagement_metrics == {"likes": "10"}
        assert result.processing_time == 1.5
        assert result.error is None
    
    def test_extraction_result_failure_case(self):
        """Test ExtractionResult for failure scenarios."""
        result = ExtractionResult(
            success=False,
            error="Test error message"
        )
        
        assert result.success is False
        assert result.error == "Test error message"
        assert result.full_text is None
        assert result.summary is None
        assert result.engagement_metrics == {}


class TestExtractionResult:
    """Test suite for ExtractionResult dataclass."""
    
    def test_successful_result_creation(self):
        """Test creating successful extraction result."""
        result = ExtractionResult(
            success=True,
            full_text="Sample tweet content",
            summary="Brief summary",
            engagement_metrics={"likes": "100", "retweets": "50"},
            processing_time=2.3,
            screenshots_captured=3
        )
        
        assert result.success is True
        assert result.full_text == "Sample tweet content"
        assert result.summary == "Brief summary"
        assert result.engagement_metrics["likes"] == "100"
        assert result.processing_time == 2.3
        assert result.screenshots_captured == 3
        assert result.error is None
    
    def test_failed_result_creation(self):
        """Test creating failed extraction result."""
        result = ExtractionResult(
            success=False,
            error="Network timeout error"
        )
        
        assert result.success is False
        assert result.error == "Network timeout error"
        assert result.full_text is None
        assert result.summary is None
        assert result.engagement_metrics == {}
        assert result.processing_time is None
        assert result.screenshots_captured is None


if __name__ == "__main__":
    pytest.main([__file__]) 