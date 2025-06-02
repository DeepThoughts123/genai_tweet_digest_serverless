"""
Test cases for visual tweet capture service with retry mechanism.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import tempfile
import os
import time
import json
from datetime import datetime

# Add path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from selenium.common.exceptions import TimeoutException, WebDriverException
# Import with proper module path to handle relative imports
import shared.visual_tweet_capture_service as vtcs_module
from shared.visual_tweet_capture_service import VisualTweetCaptureService, capture_twitter_account_visuals


class TestVisualTweetCaptureService(unittest.TestCase):
    """Test the visual tweet capture service."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.s3_bucket = "test-bucket"
        self.service = VisualTweetCaptureService(
            s3_bucket=self.s3_bucket,
            zoom_percent=60,
            max_browser_retries=3,
            retry_delay=0.1,  # Short delay for testing
            retry_backoff=2.0
        )
        
        # Mock external dependencies
        self.tweet_fetcher_patcher = patch('shared.visual_tweet_capture_service.TweetFetcher')
        self.mock_tweet_fetcher_class = self.tweet_fetcher_patcher.start()
        self.mock_tweet_fetcher = self.mock_tweet_fetcher_class.return_value
        
        self.s3_client_patcher = patch('shared.visual_tweet_capture_service.boto3.client')
        self.mock_s3_client_class = self.s3_client_patcher.start()
        self.mock_s3_client = self.mock_s3_client_class.return_value
        
        # Set the mock s3 client on the service
        self.service.s3_client = self.mock_s3_client
        
        # Mock tempfile
        self.tempfile_patcher = patch('shared.visual_tweet_capture_service.tempfile.mkdtemp')
        self.mock_tempfile = self.tempfile_patcher.start()
        self.mock_tempfile.return_value = "/tmp/test_capture"
        
        # Mock shutil for cleanup
        self.shutil_patcher = patch('shared.visual_tweet_capture_service.shutil.rmtree')
        self.mock_shutil = self.shutil_patcher.start()
        
    def tearDown(self):
        """Clean up test fixtures."""
        self.tweet_fetcher_patcher.stop()
        self.s3_client_patcher.stop()
        self.tempfile_patcher.stop()
        self.shutil_patcher.stop()


class TestRetryMechanism(TestVisualTweetCaptureService):
    """Test the retry mechanism functionality."""
    
    @patch('shared.visual_tweet_capture_service.webdriver.Chrome')
    @patch('shared.visual_tweet_capture_service.ChromeDriverManager')
    @patch('shared.visual_tweet_capture_service.Service')
    def test_browser_setup_success_first_attempt(self, mock_service, mock_driver_manager, mock_chrome):
        """Test successful browser setup on first attempt."""
        # Mock successful setup
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_driver_manager.return_value.install.return_value = "/path/to/chromedriver"
        
        result = self.service._setup_browser()
        
        self.assertTrue(result)
        self.assertEqual(mock_chrome.call_count, 1)
        self.assertEqual(self.service.driver, mock_driver)
    
    @patch('shared.visual_tweet_capture_service.webdriver.Chrome')
    @patch('shared.visual_tweet_capture_service.ChromeDriverManager')
    @patch('shared.visual_tweet_capture_service.Service')
    @patch('shared.visual_tweet_capture_service.time.sleep')  # Speed up tests
    def test_browser_setup_retry_transient_error(self, mock_sleep, mock_service, mock_driver_manager, mock_chrome):
        """Test browser setup retry with transient error."""
        # First two attempts fail with transient error, third succeeds
        mock_chrome.side_effect = [
            WebDriverException("connection timeout"),  # Transient
            WebDriverException("chromedriver session not created"),  # Transient
            Mock()  # Success
        ]
        mock_driver_manager.return_value.install.return_value = "/path/to/chromedriver"
        
        result = self.service._setup_browser()
        
        self.assertTrue(result)
        self.assertEqual(mock_chrome.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)  # Two delays between attempts
    
    @patch('shared.visual_tweet_capture_service.webdriver.Chrome')
    @patch('shared.visual_tweet_capture_service.ChromeDriverManager')
    @patch('shared.visual_tweet_capture_service.Service')
    def test_browser_setup_permanent_error_no_retry(self, mock_service, mock_driver_manager, mock_chrome):
        """Test browser setup fails fast for permanent errors."""
        # Permanent error should not retry
        mock_chrome.side_effect = Exception("chrome not found")
        mock_driver_manager.return_value.install.return_value = "/path/to/chromedriver"
        
        result = self.service._setup_browser()
        
        self.assertFalse(result)
        self.assertEqual(mock_chrome.call_count, 1)  # Only one attempt
    
    @patch('shared.visual_tweet_capture_service.webdriver.Chrome')
    @patch('shared.visual_tweet_capture_service.ChromeDriverManager')
    @patch('shared.visual_tweet_capture_service.Service')
    @patch('shared.visual_tweet_capture_service.time.sleep')
    def test_browser_setup_max_retries_exceeded(self, mock_sleep, mock_service, mock_driver_manager, mock_chrome):
        """Test browser setup fails after max retries."""
        # All attempts fail with transient error
        mock_chrome.side_effect = WebDriverException("connection timeout")
        mock_driver_manager.return_value.install.return_value = "/path/to/chromedriver"
        
        result = self.service._setup_browser()
        
        self.assertFalse(result)
        self.assertEqual(mock_chrome.call_count, 3)  # max_browser_retries attempts
        self.assertEqual(mock_sleep.call_count, 2)  # Two delays between attempts
    
    def test_error_categorization_transient(self):
        """Test categorization of transient errors."""
        transient_errors = [
            Exception("connection timeout"),
            Exception("chromedriver session not created"),
            Exception("webdriver temporarily unavailable"),
            Exception("network connection busy")
        ]
        
        for error in transient_errors:
            category = self.service._categorize_browser_error(error)
            self.assertEqual(category, 'transient', f"Error '{error}' should be transient")
    
    def test_error_categorization_permanent(self):
        """Test categorization of permanent errors."""
        permanent_errors = [
            Exception("chrome not found"),
            Exception("executable not found"),
            Exception("permission denied"),
            Exception("chrome browser not installed")
        ]
        
        for error in permanent_errors:
            category = self.service._categorize_browser_error(error)
            self.assertEqual(category, 'permanent', f"Error '{error}' should be permanent")
    
    def test_error_categorization_unknown(self):
        """Test categorization of unknown errors."""
        unknown_error = Exception("some unknown error message")
        category = self.service._categorize_browser_error(unknown_error)
        self.assertEqual(category, 'unknown')
    
    @patch('shared.visual_tweet_capture_service.webdriver.Chrome')
    @patch('shared.visual_tweet_capture_service.ChromeDriverManager')
    @patch('shared.visual_tweet_capture_service.Service')
    def test_cleanup_failed_driver(self, mock_service, mock_driver_manager, mock_chrome):
        """Test cleanup of failed driver instance."""
        mock_driver = Mock()
        self.service.driver = mock_driver
        
        self.service._cleanup_failed_driver()
        
        mock_driver.quit.assert_called_once()
        self.assertIsNone(self.service.driver)
    
    @patch('shared.visual_tweet_capture_service.webdriver.Chrome')
    @patch('shared.visual_tweet_capture_service.ChromeDriverManager')
    @patch('shared.visual_tweet_capture_service.Service')
    def test_cleanup_failed_driver_with_exception(self, mock_service, mock_driver_manager, mock_chrome):
        """Test cleanup handles exceptions gracefully."""
        mock_driver = Mock()
        mock_driver.quit.side_effect = Exception("Cleanup error")
        self.service.driver = mock_driver
        
        # Should not raise exception
        self.service._cleanup_failed_driver()
        
        mock_driver.quit.assert_called_once()
        self.assertIsNone(self.service.driver)


class TestFallbackBrowserSetup(TestVisualTweetCaptureService):
    """Test the fallback browser setup functionality."""
    
    @patch.object(VisualTweetCaptureService, '_setup_browser')
    def test_fallback_primary_success(self, mock_setup_browser):
        """Test fallback when primary setup succeeds."""
        mock_setup_browser.return_value = True
        
        result = self.service._setup_browser_with_fallback()
        
        self.assertTrue(result)
        mock_setup_browser.assert_called_once()
    
    @patch.object(VisualTweetCaptureService, '_setup_browser')
    @patch('shared.visual_tweet_capture_service.webdriver.Chrome')
    @patch('shared.visual_tweet_capture_service.ChromeDriverManager')
    @patch('shared.visual_tweet_capture_service.Service')
    def test_fallback_minimal_config_success(self, mock_service, mock_driver_manager, mock_chrome, mock_setup_browser):
        """Test fallback to minimal configuration succeeds."""
        # Primary setup fails, fallback succeeds
        mock_setup_browser.return_value = False
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_driver_manager.return_value.install.return_value = "/path/to/chromedriver"
        
        result = self.service._setup_browser_with_fallback()
        
        self.assertTrue(result)
        mock_setup_browser.assert_called_once()
        self.assertEqual(self.service.driver, mock_driver)
    
    @patch.object(VisualTweetCaptureService, '_setup_browser')
    @patch('shared.visual_tweet_capture_service.webdriver.Chrome')
    @patch('shared.visual_tweet_capture_service.ChromeDriverManager')
    @patch('shared.visual_tweet_capture_service.Service')
    def test_fallback_all_options_fail(self, mock_service, mock_driver_manager, mock_chrome, mock_setup_browser):
        """Test fallback when all options fail."""
        # Both primary and fallback fail
        mock_setup_browser.return_value = False
        mock_chrome.side_effect = Exception("All setups fail")
        mock_driver_manager.return_value.install.return_value = "/path/to/chromedriver"
        
        result = self.service._setup_browser_with_fallback()
        
        self.assertFalse(result)
        mock_setup_browser.assert_called_once()


class TestPageNavigationRetry(TestVisualTweetCaptureService):
    """Test the page navigation retry functionality."""
    
    def setUp(self):
        super().setUp()
        self.mock_driver = Mock()
        self.service.driver = self.mock_driver
        
        # Mock WebDriverWait
        self.wait_patcher = patch('shared.visual_tweet_capture_service.WebDriverWait')
        self.mock_wait_class = self.wait_patcher.start()
        self.mock_wait = self.mock_wait_class.return_value
        
        # Mock time.sleep for faster tests
        self.sleep_patcher = patch('shared.visual_tweet_capture_service.time.sleep')
        self.mock_sleep = self.sleep_patcher.start()
        
    def tearDown(self):
        super().tearDown()
        self.wait_patcher.stop()
        self.sleep_patcher.stop()
    
    def test_page_navigation_success_first_attempt(self):
        """Test successful page navigation on first attempt."""
        url = "https://twitter.com/test/status/123"
        
        result = self.service._navigate_to_page_with_retry(url)
        
        self.assertTrue(result)
        self.mock_driver.get.assert_called_once_with(url)
        self.mock_wait.until.assert_called_once()
    
    def test_page_navigation_retry_timeout_success(self):
        """Test page navigation retry after timeout, then success."""
        url = "https://twitter.com/test/status/123"
        
        # First attempt times out, second succeeds
        self.mock_wait.until.side_effect = [TimeoutException("timeout"), None]
        
        result = self.service._navigate_to_page_with_retry(url, max_retries=3)
        
        self.assertTrue(result)
        self.assertEqual(self.mock_driver.get.call_count, 2)
        self.assertEqual(self.mock_wait.until.call_count, 2)
        # The method calls sleep for retry delay AND for content loading wait
        # First retry: delay * attempt = 2.0 * 1 = 2.0
        # Content loading wait: 2 + attempt = 2 + 2 = 4
        expected_calls = [call(2.0), call(4)]
        self.mock_sleep.assert_has_calls(expected_calls)
    
    def test_page_navigation_retry_webdriver_error(self):
        """Test page navigation retry after WebDriver error."""
        url = "https://twitter.com/test/status/123"
        
        # First attempt has WebDriver error, second succeeds
        self.mock_wait.until.side_effect = [WebDriverException("webdriver error"), None]
        
        result = self.service._navigate_to_page_with_retry(url, max_retries=3)
        
        self.assertTrue(result)
        self.assertEqual(self.mock_driver.get.call_count, 2)
        self.assertEqual(self.mock_wait.until.call_count, 2)
        # The method calls sleep for retry delay AND for content loading wait
        # First retry: delay * attempt = 3.0 * 1 = 3.0 (WebDriver errors get longer delay)
        # Content loading wait: 2 + attempt = 2 + 2 = 4
        expected_calls = [call(3.0), call(4)]
        self.mock_sleep.assert_has_calls(expected_calls)
    
    def test_page_navigation_max_retries_exceeded(self):
        """Test page navigation fails after max retries."""
        url = "https://twitter.com/test/status/123"
        max_retries = 2
        
        # All attempts fail
        self.mock_wait.until.side_effect = TimeoutException("persistent timeout")
        
        result = self.service._navigate_to_page_with_retry(url, max_retries=max_retries)
        
        self.assertFalse(result)
        self.assertEqual(self.mock_driver.get.call_count, max_retries)
        self.assertEqual(self.mock_wait.until.call_count, max_retries)
        self.assertEqual(self.mock_sleep.call_count, max_retries - 1)


class TestTweetScreenshotCapture(TestVisualTweetCaptureService):
    """Test tweet screenshot capture with retry mechanism."""
    
    @patch.object(VisualTweetCaptureService, '_setup_browser_with_fallback')
    @patch.object(VisualTweetCaptureService, '_navigate_to_page_with_retry')
    @patch.object(VisualTweetCaptureService, '_capture_scrolling_screenshots')
    @patch('shared.visual_tweet_capture_service.time.sleep')
    def test_capture_tweet_screenshots_success(self, mock_sleep, mock_capture_scrolling, mock_navigate, mock_setup_browser):
        """Test successful tweet screenshot capture."""
        # Mock successful setup and navigation
        mock_setup_browser.return_value = True
        mock_navigate.return_value = True
        mock_capture_scrolling.return_value = ["/tmp/screenshot1.png", "/tmp/screenshot2.png"]
        
        tweet_url = "https://twitter.com/test/status/123"
        tweet_id = "123"
        
        result = self.service._capture_tweet_screenshots(tweet_url, tweet_id)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['tweet_id'], tweet_id)
        self.assertEqual(result['tweet_url'], tweet_url)
        self.assertEqual(len(result['screenshots']), 2)
        
        mock_setup_browser.assert_called_once()
        mock_navigate.assert_called_once_with(tweet_url)
        mock_capture_scrolling.assert_called_once_with(tweet_id)
    
    @patch.object(VisualTweetCaptureService, '_setup_browser_with_fallback')
    def test_capture_tweet_screenshots_browser_setup_fails(self, mock_setup_browser):
        """Test tweet screenshot capture when browser setup fails."""
        mock_setup_browser.return_value = False
        
        tweet_url = "https://twitter.com/test/status/123"
        tweet_id = "123"
        
        result = self.service._capture_tweet_screenshots(tweet_url, tweet_id)
        
        self.assertIsNone(result)
        mock_setup_browser.assert_called_once()
    
    @patch.object(VisualTweetCaptureService, '_setup_browser_with_fallback')
    @patch.object(VisualTweetCaptureService, '_navigate_to_page_with_retry')
    def test_capture_tweet_screenshots_navigation_fails(self, mock_navigate, mock_setup_browser):
        """Test tweet screenshot capture when page navigation fails."""
        mock_setup_browser.return_value = True
        mock_navigate.return_value = False
        
        tweet_url = "https://twitter.com/test/status/123"
        tweet_id = "123"
        
        result = self.service._capture_tweet_screenshots(tweet_url, tweet_id)
        
        self.assertIsNone(result)
        mock_setup_browser.assert_called_once()
        mock_navigate.assert_called_once_with(tweet_url)
    
    @patch.object(VisualTweetCaptureService, '_setup_browser_with_fallback')
    @patch.object(VisualTweetCaptureService, '_navigate_to_page_with_retry')
    @patch.object(VisualTweetCaptureService, '_capture_scrolling_screenshots')
    @patch('shared.visual_tweet_capture_service.time.sleep')
    def test_capture_tweet_screenshots_cleanup_on_exception(self, mock_sleep, mock_capture_scrolling, mock_navigate, mock_setup_browser):
        """Test that driver is cleaned up even when exception occurs."""
        mock_setup_browser.return_value = True
        mock_navigate.return_value = True
        mock_capture_scrolling.side_effect = Exception("Capture error")
        
        # Mock driver
        mock_driver = Mock()
        self.service.driver = mock_driver
        
        tweet_url = "https://twitter.com/test/status/123"
        tweet_id = "123"
        
        result = self.service._capture_tweet_screenshots(tweet_url, tweet_id)
        
        self.assertIsNone(result)  # Should return None due to exception
        mock_driver.quit.assert_called_once()  # Driver should be cleaned up
        self.assertIsNone(self.service.driver)  # Driver should be set to None


class TestConvenienceFunction(TestVisualTweetCaptureService):
    """Test the convenience function with retry parameters."""
    
    @patch('shared.visual_tweet_capture_service.VisualTweetCaptureService')
    def test_convenience_function_with_retry_params(self, mock_service_class):
        """Test that convenience function passes retry parameters correctly."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.capture_account_content.return_value = {'success': True}
        
        result = capture_twitter_account_visuals(
            account_name="testuser",
            s3_bucket="test-bucket",
            days_back=7,
            max_tweets=25,
            zoom_percent=60,
            max_browser_retries=5,
            retry_delay=1.5,
            retry_backoff=3.0
        )
        
        # Verify service was created with correct retry parameters
        mock_service_class.assert_called_once_with(
            s3_bucket="test-bucket",
            zoom_percent=60,
            max_browser_retries=5,
            retry_delay=1.5,
            retry_backoff=3.0
        )
        
        # Verify capture was called
        mock_service.capture_account_content.assert_called_once_with("testuser", 7, 25)
        
        self.assertEqual(result, {'success': True})


class TestRetryConfiguration(TestVisualTweetCaptureService):
    """Test retry configuration and parameter validation."""
    
    def test_retry_configuration_initialization(self):
        """Test that retry configuration is properly initialized."""
        service = VisualTweetCaptureService(
            s3_bucket="test-bucket",
            max_browser_retries=5,
            retry_delay=1.5,
            retry_backoff=3.0
        )
        
        self.assertEqual(service.max_browser_retries, 5)
        self.assertEqual(service.retry_delay, 1.5)
        self.assertEqual(service.retry_backoff, 3.0)
    
    def test_retry_configuration_defaults(self):
        """Test that retry configuration uses correct defaults."""
        service = VisualTweetCaptureService(s3_bucket="test-bucket")
        
        self.assertEqual(service.max_browser_retries, 3)
        self.assertEqual(service.retry_delay, 2.0)
        self.assertEqual(service.retry_backoff, 2.0)
    
    @patch('shared.visual_tweet_capture_service.time.sleep')
    def test_exponential_backoff_calculation(self, mock_sleep):
        """Test that exponential backoff is calculated correctly."""
        # Create service with specific backoff settings
        service = VisualTweetCaptureService(
            s3_bucket="test-bucket",
            retry_delay=1.0,
            retry_backoff=2.0
        )
        
        # Mock webdriver to always fail
        with patch('shared.visual_tweet_capture_service.webdriver.Chrome') as mock_chrome:
            mock_chrome.side_effect = WebDriverException("connection timeout")
            with patch('shared.visual_tweet_capture_service.ChromeDriverManager'):
                with patch('shared.visual_tweet_capture_service.Service'):
                    service._setup_browser()
        
        # Verify sleep was called with exponentially increasing delays
        expected_calls = [
            call(1.0),  # First retry: delay * (backoff ** 0) = 1.0 * 1 = 1.0
            call(2.0),  # Second retry: delay * (backoff ** 1) = 1.0 * 2 = 2.0
        ]
        
        mock_sleep.assert_has_calls(expected_calls)


if __name__ == '__main__':
    unittest.main() 