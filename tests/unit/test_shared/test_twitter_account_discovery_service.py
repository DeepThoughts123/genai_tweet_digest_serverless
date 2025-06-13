"""
Test cases for Twitter Account Discovery Service.

Tests the iterative discovery of influential Twitter accounts in the generative AI field.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import tempfile
import os
import json
from datetime import datetime
from dataclasses import asdict

# Add path for imports
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from selenium.common.exceptions import TimeoutException, WebDriverException

# Import the service and data classes
import src.shared.twitter_account_discovery_service as tads_module
from src.shared.twitter_account_discovery_service import (
    TwitterAccountDiscoveryService, 
    ProfileInfo, 
    DiscoveryResult,
    discover_twitter_accounts
)


class TestTwitterAccountDiscoveryService(unittest.TestCase):
    """Base test class for Twitter Account Discovery Service."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.output_dir = "/tmp/test_discovery_output"
        
        # Mock config.gemini_api_key to be None for consistent testing
        self.config_patcher = patch('src.shared.twitter_account_discovery_service.config')
        self.mock_config = self.config_patcher.start()
        self.mock_config.gemini_api_key = None  # Default to None
        
        self.service = TwitterAccountDiscoveryService(
            output_dir=self.output_dir,
            max_browser_retries=3,
            retry_delay=0.1  # Short delay for testing
        )
        
        # Mock external dependencies
        self.visual_capture_patcher = patch('src.shared.twitter_account_discovery_service.VisualTweetCaptureService')
        self.mock_visual_capture_class = self.visual_capture_patcher.start()
        self.mock_visual_capture = self.mock_visual_capture_class.return_value
        
        # Mock Gemini AI
        self.genai_patcher = patch('src.shared.twitter_account_discovery_service.genai')
        self.mock_genai = self.genai_patcher.start()
        
        # Mock webdriver
        self.webdriver_patcher = patch('src.shared.twitter_account_discovery_service.webdriver')
        self.mock_webdriver = self.webdriver_patcher.start()
        self.mock_driver = Mock()
        self.mock_webdriver.Chrome.return_value = self.mock_driver
        
        # Mock file operations
        self.os_makedirs_patcher = patch('os.makedirs')
        self.mock_makedirs = self.os_makedirs_patcher.start()
        
        # Mock datetime for consistent timestamps
        self.datetime_patcher = patch('src.shared.twitter_account_discovery_service.datetime')
        self.mock_datetime = self.datetime_patcher.start()
        self.mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"
        
    def tearDown(self):
        """Clean up test fixtures."""
        self.config_patcher.stop()
        self.visual_capture_patcher.stop()
        self.genai_patcher.stop()
        self.webdriver_patcher.stop()
        self.os_makedirs_patcher.stop()
        self.datetime_patcher.stop()


class TestServiceInitialization(TestTwitterAccountDiscoveryService):
    """Test service initialization and configuration."""
    
    def test_initialization_with_defaults(self):
        """Test service initialization with default parameters."""
        # Ensure no API key for this test
        with patch('src.shared.twitter_account_discovery_service.config') as mock_config:
            mock_config.gemini_api_key = None
            service = TwitterAccountDiscoveryService()
            
            self.assertEqual(service.output_dir, "./twitter_discovery_output")
            self.assertEqual(service.max_browser_retries, 3)
            self.assertEqual(service.retry_delay, 2.0)
            self.assertIsNone(service.driver)
            self.assertIsNone(service.genai_model)
    
    def test_initialization_with_custom_params(self):
        """Test service initialization with custom parameters."""
        custom_dir = "/custom/output"
        service = TwitterAccountDiscoveryService(
            output_dir=custom_dir,
            max_browser_retries=5,
            retry_delay=1.5
        )
        
        self.assertEqual(service.output_dir, custom_dir)
        self.assertEqual(service.max_browser_retries, 5)
        self.assertEqual(service.retry_delay, 1.5)


class TestURLValidation(TestTwitterAccountDiscoveryService):
    """Test URL validation and processing methods."""
    
    def test_validate_twitter_url_valid_urls(self):
        """Test validation of valid Twitter URLs."""
        valid_urls = [
            "https://twitter.com/username",
            "https://x.com/username", 
            "https://www.twitter.com/username",
            "https://www.x.com/username",
            "https://twitter.com/username123",
            "https://x.com/user_name"
        ]
        
        for url in valid_urls:
            with self.subTest(url=url):
                result = self.service._validate_twitter_url(url)
                self.assertTrue(result, f"URL should be valid: {url}")
    
    def test_validate_twitter_url_invalid_urls(self):
        """Test validation rejects invalid URLs."""
        invalid_urls = [
            "https://facebook.com/username",
            "https://instagram.com/username",
            "https://linkedin.com/in/username",
            "not-a-url",
            "",
            "https://twitter.com/",  # Missing username
            "ftp://twitter.com/username"  # Wrong protocol
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                result = self.service._validate_twitter_url(url)
                self.assertFalse(result, f"URL should be invalid: {url}")
    
    def test_extract_username_from_url_success(self):
        """Test extracting username from valid Twitter URLs."""
        test_cases = [
            ("https://twitter.com/username", "username"),
            ("https://x.com/test_user", "test_user"),
            ("https://www.twitter.com/user123", "user123"),
            ("https://twitter.com/username/", "username"),  # Trailing slash
        ]
        
        for url, expected_username in test_cases:
            with self.subTest(url=url):
                result = self.service._extract_username_from_url(url)
                self.assertEqual(result, expected_username)
    
    def test_extract_username_from_url_invalid(self):
        """Test extracting username fails for invalid URLs."""
        invalid_urls = [
            "https://twitter.com/",
            "https://facebook.com/username",
            "not-a-url"
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    self.service._extract_username_from_url(url)


class TestBrowserSetup(TestTwitterAccountDiscoveryService):
    """Test browser setup and management."""
    
    @patch('src.shared.twitter_account_discovery_service.ChromeDriverManager')
    @patch('src.shared.twitter_account_discovery_service.Service')
    @patch('src.shared.twitter_account_discovery_service.Options')
    def test_setup_browser_success(self, mock_options, mock_service, mock_driver_manager):
        """Test successful browser setup."""
        mock_driver_manager.return_value.install.return_value = "/path/to/chromedriver"
        
        result = self.service.setup_browser()
        
        self.assertTrue(result)
        self.assertEqual(self.service.driver, self.mock_driver)
        self.mock_webdriver.Chrome.assert_called_once()
    
    @patch('src.shared.twitter_account_discovery_service.ChromeDriverManager')
    @patch('src.shared.twitter_account_discovery_service.Service')
    @patch('src.shared.twitter_account_discovery_service.Options')
    @patch('src.shared.twitter_account_discovery_service.time.sleep')
    def test_setup_browser_retry_on_failure(self, mock_sleep, mock_options, mock_service, mock_driver_manager):
        """Test browser setup retry mechanism."""
        mock_driver_manager.return_value.install.return_value = "/path/to/chromedriver"
        
        # First two attempts fail, third succeeds
        self.mock_webdriver.Chrome.side_effect = [
            WebDriverException("connection timeout"),
            WebDriverException("session not created"),
            self.mock_driver
        ]
        
        result = self.service.setup_browser()
        
        self.assertTrue(result)
        self.assertEqual(self.mock_webdriver.Chrome.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)  # Two delays between attempts
    
    @patch('src.shared.twitter_account_discovery_service.ChromeDriverManager')
    @patch('src.shared.twitter_account_discovery_service.Service')
    @patch('src.shared.twitter_account_discovery_service.Options')
    def test_setup_browser_max_retries_exceeded(self, mock_options, mock_service, mock_driver_manager):
        """Test browser setup fails after max retries."""
        mock_driver_manager.return_value.install.return_value = "/path/to/chromedriver"
        self.mock_webdriver.Chrome.side_effect = WebDriverException("persistent error")
        
        result = self.service.setup_browser()
        
        self.assertFalse(result)
        self.assertEqual(self.mock_webdriver.Chrome.call_count, 3)  # max_browser_retries
    
    def test_cleanup_browser_success(self):
        """Test successful browser cleanup."""
        self.service.driver = self.mock_driver
        
        self.service.cleanup_browser()
        
        self.mock_driver.quit.assert_called_once()
        self.assertIsNone(self.service.driver)
    
    def test_cleanup_browser_with_exception(self):
        """Test browser cleanup handles exceptions gracefully."""
        self.service.driver = self.mock_driver
        self.mock_driver.quit.side_effect = Exception("Cleanup error")
        
        # Should not raise exception
        self.service.cleanup_browser()
        
        self.mock_driver.quit.assert_called_once()
        self.assertIsNone(self.service.driver)
    
    def test_cleanup_browser_no_driver(self):
        """Test cleanup when no driver exists."""
        self.service.driver = None
        
        # Should not raise exception
        self.service.cleanup_browser()
        
        # No assertion needed, just ensure no exception is raised


class TestProfileExtraction(TestTwitterAccountDiscoveryService):
    """Test profile information extraction from Twitter pages."""
    
    def setUp(self):
        super().setUp()
        self.service.driver = self.mock_driver
        
        # Mock WebDriverWait
        self.wait_patcher = patch('src.shared.twitter_account_discovery_service.WebDriverWait')
        self.mock_wait_class = self.wait_patcher.start()
        self.mock_wait = self.mock_wait_class.return_value
        
    def tearDown(self):
        super().tearDown()
        self.wait_patcher.stop()
    
    def test_extract_profile_info_success(self):
        """Test successful extraction of profile information."""
        profile_url = "https://twitter.com/test_user"
        
        # Mock page elements with proper text values
        def mock_find_element(by, value):
            if '[data-testid="UserDescription"]' in value:
                element = Mock()
                element.text = "AI researcher and machine learning enthusiast"
                return element
            elif 'followers' in value.lower():
                element = Mock()
                element.text = "1,234 Followers"
                return element
            elif 'following' in value.lower():
                element = Mock()
                element.text = "567 Following"
                return element
            return Mock()
        
        self.mock_driver.find_element.side_effect = mock_find_element
        
        result = self.service.extract_profile_info(profile_url)
        
        self.assertEqual(len(result), 5)  # username, handle, description, followers, following
        username, handle, description, followers_count, following_count = result
        
        self.assertEqual(username, "test_user")
        self.assertEqual(handle, "@test_user")
        self.assertEqual(description, "AI researcher and machine learning enthusiast")
        self.assertEqual(followers_count, 1234)
        self.assertEqual(following_count, 567)
    
    def test_extract_profile_info_missing_elements(self):
        """Test profile extraction when some elements are missing."""
        profile_url = "https://twitter.com/test_user"
        
        # Mock missing elements (WebDriverException)
        self.mock_driver.find_element.side_effect = WebDriverException("Element not found")
        
        result = self.service.extract_profile_info(profile_url)
        
        username, handle, description, followers_count, following_count = result
        self.assertEqual(username, "test_user")
        self.assertEqual(handle, "@test_user")
        self.assertEqual(description, "")  # Default when missing
        self.assertIsNone(followers_count)  # None when missing
        self.assertIsNone(following_count)  # None when missing
    
    def test_extract_profile_info_number_parsing(self):
        """Test parsing of follower/following numbers in various formats."""
        test_cases = [
            ("1,234 Followers", 1234),
            ("10.5K Followers", 10500),
            ("2.3M Followers", 2300000),
            ("15 Followers", 15),
            ("Invalid Format", None)
        ]
        
        for input_text, expected_count in test_cases:
            with self.subTest(input_text=input_text):
                def mock_find_element(by, value):
                    element = Mock()
                    element.text = input_text
                    return element
                
                self.mock_driver.find_element.side_effect = mock_find_element
                
                result = self.service.extract_profile_info("https://twitter.com/test")
                _, _, _, followers_count, _ = result
                
                self.assertEqual(followers_count, expected_count)


class TestGeminiClassification(TestTwitterAccountDiscoveryService):
    """Test Gemini AI classification of profile relevance."""
    
    def setUp(self):
        super().setUp()
        
        # Mock service to have Gemini model for these tests
        self.service.genai_model = Mock()
    
    def test_classify_profile_relevance_positive(self):
        """Test classification of GenAI-relevant profile."""
        profile_info = ("openai", "@openai", "Building safe AGI", 1000000, 500)
        
        # Mock Gemini response indicating relevance
        mock_response = Mock()
        mock_response.text = "YES - This profile is highly relevant to generative AI as OpenAI is a leading AI research company."
        self.service.genai_model.generate_content.return_value = mock_response
        
        is_relevant, reasoning = self.service.classify_profile_relevance(profile_info)
        
        self.assertTrue(is_relevant)
        self.assertIn("YES", reasoning)
        self.assertIn("AI", reasoning)
    
    def test_classify_profile_relevance_negative(self):
        """Test classification of non-GenAI-relevant profile."""
        profile_info = ("chef_joe", "@chef_joe", "Professional chef sharing recipes", 5000, 1200)
        
        # Mock Gemini response indicating non-relevance
        mock_response = Mock()
        mock_response.text = "NO - This profile focuses on cooking and recipes, not generative AI."
        self.service.genai_model.generate_content.return_value = mock_response
        
        is_relevant, reasoning = self.service.classify_profile_relevance(profile_info)
        
        self.assertFalse(is_relevant)
        self.assertIn("NO", reasoning)
        self.assertIn("cooking", reasoning)
    
    def test_classify_profile_relevance_api_error(self):
        """Test handling of Gemini API errors during classification."""
        profile_info = ("test_user", "@test_user", "Test description", 1000, 500)
        
        # Mock API error
        self.service.genai_model.generate_content.side_effect = Exception("API rate limit exceeded")
        
        with self.assertRaises(Exception):
            self.service.classify_profile_relevance(profile_info)
    
    def test_classify_profile_relevance_fallback_mode(self):
        """Test fallback keyword-based classification when no Gemini model."""
        # Remove Gemini model to test fallback
        self.service.genai_model = None
        
        # Test AI-relevant profile
        ai_profile = ("openai", "@openai", "Building artificial intelligence", 1000000, 500)
        is_relevant, reasoning = self.service.classify_profile_relevance(ai_profile)
        
        self.assertTrue(is_relevant)
        self.assertIn("Keyword-based", reasoning)
        
        # Test non-AI profile
        non_ai_profile = ("chef", "@chef", "Professional cooking", 5000, 1200)
        is_relevant, reasoning = self.service.classify_profile_relevance(non_ai_profile)
        
        self.assertFalse(is_relevant)
        self.assertIn("Keyword-based", reasoning)
    
    def test_build_classification_prompt(self):
        """Test building of classification prompt for Gemini."""
        prompt = self.service._build_classification_prompt(
            username="test_user",
            handle="@test_user", 
            description="AI researcher working on LLMs",
            followers_count=5000,
            following_count=1200
        )
        
        self.assertIn("test_user", prompt)
        self.assertIn("@test_user", prompt)
        self.assertIn("AI researcher", prompt)
        self.assertIn("5000", prompt)
        self.assertIn("1200", prompt)
        self.assertIn("generative ai", prompt.lower())  # Case insensitive check


class TestFollowingExtraction(TestTwitterAccountDiscoveryService):
    """Test extraction of following accounts from Twitter pages."""
    
    def setUp(self):
        super().setUp()
        self.service.driver = self.mock_driver
        
        # Mock WebDriverWait and scrolling
        self.wait_patcher = patch('src.shared.twitter_account_discovery_service.WebDriverWait')
        self.mock_wait_class = self.wait_patcher.start()
        self.mock_wait = self.mock_wait_class.return_value
        
        self.time_patcher = patch('src.shared.twitter_account_discovery_service.time.sleep')
        self.mock_sleep = self.time_patcher.start()
        
    def tearDown(self):
        super().tearDown()
        self.wait_patcher.stop()
        self.time_patcher.stop()
    
    def test_extract_following_accounts_success(self):
        """Test successful extraction of following accounts."""
        profile_url = "https://twitter.com/test_user"
        
        # Mock following page elements
        mock_elements = []
        for handle in ["openai", "anthropic", "googleai", "test_user"]:
            element = Mock()
            element.get_attribute.return_value = f"https://twitter.com/{handle}"
            element.text = f"@{handle}"
            mock_elements.append(element)
        
        self.mock_driver.find_elements.return_value = mock_elements
        
        # Mock execute_script calls - need values for both scroll and position checks
        # Pattern: scroll, position, scroll, position, etc.
        # Simulate 3 scrolls that change position, then 3 that don't change (to trigger end)
        scroll_positions = [
            # First scroll iteration
            None, 0,    # scroll() call returns None, position check returns 0
            # Second scroll iteration 
            None, 1000, # scroll() call returns None, position check returns 1000
            # Third scroll iteration
            None, 2000, # scroll() call returns None, position check returns 2000
            # Fourth scroll iteration (same position - triggers no_change_count)
            None, 2000, # scroll() call returns None, position check returns 2000 (same)
            # Fifth scroll iteration (same position - triggers no_change_count)
            None, 2000, # scroll() call returns None, position check returns 2000 (same)
            # Sixth scroll iteration (same position - triggers break)
            None, 2000, # scroll() call returns None, position check returns 2000 (same)
            # Extra values in case of more calls
            None, 2000, None, 2000, None, 2000, None, 2000
        ]
        
        self.mock_driver.execute_script.side_effect = scroll_positions
        
        result = self.service.extract_following_accounts(profile_url)
        
        # Should extract 3 accounts (excluding self)
        expected_accounts = ["openai", "anthropic", "googleai"]
        self.assertEqual(sorted(result), sorted(expected_accounts))
    
    def test_extract_following_accounts_navigation_error(self):
        """Test handling of navigation errors to following page."""
        profile_url = "https://twitter.com/test_user"
        
        # Mock navigation error
        self.mock_driver.get.side_effect = WebDriverException("Page not found")
        
        with self.assertRaises(WebDriverException):
            self.service.extract_following_accounts(profile_url)
    
    def test_extract_following_accounts_empty_page(self):
        """Test extraction when following page is empty."""
        profile_url = "https://twitter.com/test_user"
        
        # Mock empty following page
        self.mock_driver.find_elements.return_value = []
        
        # Mock execute_script calls - need values for both scroll and position checks
        # Pattern: scroll returns None, position returns same value to trigger early break
        scroll_positions = [
            None, 0,    # First: scroll() returns None, position returns 0
            None, 0,    # Second: scroll() returns None, position returns 0 (same)
            None, 0,    # Third: scroll() returns None, position returns 0 (same)
            None, 0,    # Fourth: scroll() returns None, position returns 0 (same) - triggers break
            # Extra values in case
            None, 0, None, 0, None, 0
        ]
        
        self.mock_driver.execute_script.side_effect = scroll_positions
        
        result = self.service.extract_following_accounts(profile_url)
        
        self.assertEqual(result, [])
    
    def test_extract_following_accounts_scroll_limit_reached(self):
        """Test extraction stops at scroll limit to prevent infinite loop."""
        profile_url = "https://twitter.com/test_user"
        
        # Mock some account elements
        mock_element = Mock()
        mock_element.get_attribute.return_value = "https://twitter.com/test_account"
        mock_element.text = "@test_account"
        self.mock_driver.find_elements.return_value = [mock_element]
        
        # Mock execute_script to always return increasing scroll positions (never stabilizes)
        # This should hit the max_scrolls limit (20)
        scroll_positions = []
        for i in range(50):  # Generate enough values for max_scrolls iterations
            scroll_positions.extend([None, i * 100])  # scroll() returns None, position increases
        
        self.mock_driver.execute_script.side_effect = scroll_positions
        
        result = self.service.extract_following_accounts(profile_url)
        
        # Should still return results despite hitting scroll limit
        self.assertIsInstance(result, list)
        # Should not scroll more than reasonable limit (max_scrolls = 20)
        self.assertLess(self.mock_sleep.call_count, 25)


class TestProfileProcessing(TestTwitterAccountDiscoveryService):
    """Test complete profile processing workflow."""
    
    def setUp(self):
        super().setUp()
        
        # Mock all dependencies for profile processing
        self.service.setup_browser = Mock(return_value=True)
        self.service.extract_profile_info = Mock(return_value=(
            "test_user", "@test_user", "AI researcher", 5000, 1200
        ))
        self.service.classify_profile_relevance = Mock(return_value=(
            True, "YES - Relevant to generative AI"
        ))
        self.service.extract_following_accounts = Mock(return_value=[
            "openai", "anthropic", "googleai"
        ])
    
    def test_process_profile_genai_relevant(self):
        """Test processing of GenAI-relevant profile."""
        profile_url = "https://twitter.com/test_user"
        iteration = 0
        
        result = self.service.process_profile(profile_url, iteration)
        
        self.assertIsInstance(result, ProfileInfo)
        self.assertEqual(result.username, "test_user")
        self.assertEqual(result.handle, "@test_user")
        self.assertTrue(result.is_genai_relevant)
        self.assertEqual(len(result.discovered_following), 3)
        self.assertEqual(result.iteration_discovered, 0)
    
    def test_process_profile_not_genai_relevant(self):
        """Test processing of non-GenAI-relevant profile."""
        profile_url = "https://twitter.com/chef_joe"
        
        # Mock non-relevant classification
        self.service.extract_profile_info.return_value = (
            "chef_joe", "@chef_joe", "Professional chef", 2000, 800
        )
        self.service.classify_profile_relevance.return_value = (
            False, "NO - Focuses on cooking, not AI"
        )
        
        result = self.service.process_profile(profile_url, 1)
        
        self.assertFalse(result.is_genai_relevant)
        self.assertIsNone(result.discovered_following)  # Should not extract following for non-relevant
    
    def test_process_profile_browser_setup_failure(self):
        """Test profile processing when browser setup fails."""
        profile_url = "https://twitter.com/test_user"
        
        # Mock browser setup failure
        self.service.setup_browser.return_value = False
        
        with self.assertRaises(RuntimeError):
            self.service.process_profile(profile_url, 0)
    
    def test_process_profile_invalid_url(self):
        """Test profile processing with invalid URL."""
        invalid_url = "https://facebook.com/user"
        
        with self.assertRaises(ValueError):
            self.service.process_profile(invalid_url, 0)


class TestDiscoveryWorkflow(TestTwitterAccountDiscoveryService):
    """Test the complete discovery workflow."""
    
    def setUp(self):
        super().setUp()
        
        # Mock profile processing for controlled testing
        self.service.process_profile = Mock()
        self.service.save_results = Mock(return_value="/tmp/results.json")
        
        # Create mock profiles for different scenarios
        self.genai_profile = ProfileInfo(
            username="openai_test",
            handle="@openai_test", 
            profile_url="https://twitter.com/openai_test",
            description="AI research company",
            followers_count=100000,
            following_count=500,
            is_genai_relevant=True,
            genai_classification_reason="YES - Leading AI company",
            discovered_following=["anthropic", "googleai", "huggingface"],
            iteration_discovered=0,
            discovery_timestamp="2024-01-01T12:00:00"
        )
        
        self.non_genai_profile = ProfileInfo(
            username="chef_test",
            handle="@chef_test",
            profile_url="https://twitter.com/chef_test", 
            description="Professional chef",
            followers_count=5000,
            following_count=1000,
            is_genai_relevant=False,
            genai_classification_reason="NO - Cooking focused",
            discovered_following=None,
            iteration_discovered=0,
            discovery_timestamp="2024-01-01T12:00:00"
        )
    
    def test_discover_accounts_single_iteration(self):
        """Test discovery with single iteration (seed only)."""
        seed_urls = ["https://twitter.com/openai_test", "https://twitter.com/chef_test"]
        
        # Mock process_profile to return our test profiles
        self.service.process_profile.side_effect = [self.genai_profile, self.non_genai_profile]
        
        result = self.service.discover_accounts(seed_urls, max_iterations=0)
        
        self.assertIsInstance(result, DiscoveryResult)
        self.assertEqual(result.total_iterations, 1)  # 0 iterations = 1 processing round
        self.assertEqual(result.total_profiles_processed, 2)
        self.assertEqual(len(result.genai_relevant_profiles), 1)
        self.assertEqual(len(result.non_relevant_profiles), 1)
        self.assertEqual(len(result.failed_profiles), 0)
    
    def test_discover_accounts_multiple_iterations(self):
        """Test discovery with multiple iterations."""
        seed_urls = ["https://twitter.com/openai_test"]
        
        # First iteration: process seed
        # Second iteration: process discovered accounts
        iteration_profiles = [
            self.genai_profile,  # Seed profile
            # Mock profiles for discovered accounts
            ProfileInfo("anthropic", "@anthropic", "https://twitter.com/anthropic", 
                       "AI safety", 50000, 300, True, "YES - AI safety", 
                       ["openai_test"], 1, "2024-01-01T12:00:00"),
        ]
        
        self.service.process_profile.side_effect = iteration_profiles
        
        result = self.service.discover_accounts(seed_urls, max_iterations=1)
        
        self.assertEqual(result.total_iterations, 2)
        self.assertGreaterEqual(result.total_profiles_processed, 2)
        self.assertGreater(len(result.genai_relevant_profiles), 1)
    
    def test_discover_accounts_empty_seed_urls(self):
        """Test discovery fails with empty seed URLs."""
        with self.assertRaises(ValueError):
            self.service.discover_accounts([])
    
    def test_discover_accounts_invalid_seed_urls(self):
        """Test discovery fails with invalid seed URLs."""
        invalid_urls = ["https://facebook.com/user", "not-a-url"]
        
        with self.assertRaises(ValueError):
            self.service.discover_accounts(invalid_urls)
    
    def test_discover_accounts_profile_processing_failure(self):
        """Test discovery handles profile processing failures gracefully."""
        seed_urls = ["https://twitter.com/test_user"]
        
        # Mock processing failure
        self.service.process_profile.side_effect = RuntimeError("Browser setup failed")
        
        result = self.service.discover_accounts(seed_urls, max_iterations=0)
        
        # Should complete but with failed profiles
        self.assertEqual(len(result.failed_profiles), 1)
        self.assertEqual(len(result.genai_relevant_profiles), 0)
        self.assertEqual(len(result.non_relevant_profiles), 0)


class TestResultsSaving(TestTwitterAccountDiscoveryService):
    """Test saving of discovery results."""
    
    def test_save_results_with_default_filename(self):
        """Test saving results with default filename."""
        result = DiscoveryResult(
            total_iterations=1,
            total_profiles_processed=2,
            genai_relevant_profiles=[],
            non_relevant_profiles=[],
            failed_profiles=[],
            discovery_summary={"status": "completed"}
        )
        
        with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
            with patch('json.dump') as mock_json_dump:
                output_path = self.service.save_results(result)
                
                self.assertIsInstance(output_path, str)
                self.assertTrue(output_path.endswith('.json'))
                mock_file.assert_called_once()
                mock_json_dump.assert_called_once()
    
    def test_save_results_with_custom_filename(self):
        """Test saving results with custom filename."""
        result = DiscoveryResult(
            total_iterations=1,
            total_profiles_processed=1,
            genai_relevant_profiles=[],
            non_relevant_profiles=[],
            failed_profiles=[],
            discovery_summary={}
        )
        
        custom_file = "/tmp/custom_results.json"
        
        with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
            with patch('json.dump') as mock_json_dump:
                output_path = self.service.save_results(result, custom_file)
                
                self.assertEqual(output_path, custom_file)
                # Check that file was opened with proper encoding
                mock_file.assert_called_with(custom_file, 'w', encoding='utf-8')


class TestConvenienceFunction(TestTwitterAccountDiscoveryService):
    """Test the convenience function."""
    
    @patch('src.shared.twitter_account_discovery_service.TwitterAccountDiscoveryService')
    def test_discover_twitter_accounts_function(self, mock_service_class):
        """Test the convenience function creates service and calls discover_accounts."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        mock_result = DiscoveryResult(
            total_iterations=1,
            total_profiles_processed=1,
            genai_relevant_profiles=[],
            non_relevant_profiles=[],
            failed_profiles=[],
            discovery_summary={}
        )
        mock_service.discover_accounts.return_value = mock_result
        
        seed_urls = ["https://twitter.com/test"]
        result = discover_twitter_accounts(seed_urls, max_iterations=2, output_dir="/tmp/test")
        
        # Verify service was created with correct parameters
        mock_service_class.assert_called_once_with(output_dir="/tmp/test")
        
        # Verify discover_accounts was called
        mock_service.discover_accounts.assert_called_once_with(seed_urls, 2)
        
        # Verify cleanup was called
        mock_service.cleanup_browser.assert_called_once()
        
        self.assertEqual(result, mock_result)


class TestDataClasses(unittest.TestCase):
    """Test the data classes used in the service."""
    
    def test_profile_info_initialization(self):
        """Test ProfileInfo data class initialization."""
        profile = ProfileInfo(
            username="test_user",
            handle="@test_user",
            profile_url="https://twitter.com/test_user",
            description="Test description"
        )
        
        self.assertEqual(profile.username, "test_user")
        self.assertEqual(profile.handle, "@test_user")
        self.assertEqual(profile.profile_url, "https://twitter.com/test_user")
        self.assertEqual(profile.description, "Test description")
        self.assertIsNone(profile.followers_count)  # Default None
        self.assertEqual(profile.iteration_discovered, 0)  # Default 0
    
    def test_discovery_result_initialization(self):
        """Test DiscoveryResult data class initialization."""
        result = DiscoveryResult(
            total_iterations=2,
            total_profiles_processed=10,
            genai_relevant_profiles=[],
            non_relevant_profiles=[],
            failed_profiles=[],
            discovery_summary={"key": "value"}
        )
        
        self.assertEqual(result.total_iterations, 2)
        self.assertEqual(result.total_profiles_processed, 10)
        self.assertEqual(len(result.genai_relevant_profiles), 0)
        self.assertIsNone(result.output_file_path)  # Default None


if __name__ == '__main__':
    unittest.main() 