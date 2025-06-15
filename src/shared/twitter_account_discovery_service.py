#!/usr/bin/env python3
"""
Twitter Account Discovery Service

Discovers influential Twitter accounts in the generative AI field through iterative crawling.

Features:
- Starts with seed Twitter profile URLs
- Captures profile pages and extracts metadata using Gemini AI with image analysis
- Uses Gemini AI to classify if users are active in generative AI space
- Crawls "following" pages to discover new accounts with login support
- Supports N iterations of discovery
- Outputs comprehensive list of GenAI-relevant accounts

Process Flow:
1. Login to Twitter using provided credentials
2. Start with seed URLs (iteration 0)
3. For each URL, capture profile page screenshot and use Gemini AI for extraction
4. Use Gemini AI to classify if user is GenAI-relevant
5. For relevant users, navigate to their "following" page
6. Scroll and capture following pages to extract account handles using image analysis
7. Generate new URLs for discovered accounts (iteration 1, 2, ... N)
8. Repeat process for specified number of iterations
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
import re
import tempfile
import base64

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import google.generativeai as genai

from .visual_tweet_capture_service import VisualTweetCaptureService
from .config import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Twitter login credentials
TWITTER_USERNAME = "dan_lin47482"
TWITTER_PASSWORD = "Tweettweet9"

@dataclass
class ProfileInfo:
    """Data class for Twitter profile information."""
    username: str
    handle: str  # @username format
    profile_url: str
    description: str
    followers_count: Optional[int] = None
    following_count: Optional[int] = None
    is_genai_relevant: Optional[bool] = None
    genai_classification_reason: Optional[str] = None
    profile_screenshot_path: Optional[str] = None
    following_page_screenshots: Optional[List[str]] = None
    discovered_following: Optional[List[str]] = None
    iteration_discovered: int = 0
    discovery_timestamp: Optional[str] = None

@dataclass
class DiscoveryResult:
    """Data class for discovery process results."""
    total_iterations: int
    total_profiles_processed: int
    genai_relevant_profiles: List[ProfileInfo]
    non_relevant_profiles: List[ProfileInfo]
    failed_profiles: List[Dict[str, Any]]
    discovery_summary: Dict[str, Any]
    output_file_path: Optional[str] = None

class TwitterAccountDiscoveryService:
    """
    Service for discovering influential Twitter accounts in the generative AI field.
    """
    
    def __init__(self, output_dir: str = "./twitter_discovery_output", 
                 max_browser_retries: int = 3, retry_delay: float = 2.0):
        """
        Initialize the Twitter account discovery service.
        
        Args:
            output_dir: Directory to store discovery results and screenshots
            max_browser_retries: Number of browser setup attempts
            retry_delay: Delay between retries in seconds
        """
        self.output_dir = output_dir
        self.max_browser_retries = max_browser_retries
        self.retry_delay = retry_delay
        self.driver = None
        self.genai_model = None
        self.is_logged_in = False
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create screenshots directory
        self.screenshots_dir = os.path.join(self.output_dir, "screenshots")
        os.makedirs(self.screenshots_dir, exist_ok=True)
        
        # Initialize Gemini AI
        if config.gemini_api_key:
            genai.configure(api_key=config.gemini_api_key)
            self.genai_model = genai.GenerativeModel("gemini-2.0-flash")
            logger.info("Gemini AI model initialized successfully")
        else:
            logger.warning("Gemini API key not found. AI classification will not work.")
    
    def discover_accounts(self, seed_urls: List[str], max_iterations: int = 1,
                         max_profiles_per_iteration: int = 10) -> DiscoveryResult:
        """
        Main method to discover Twitter accounts through iterative crawling.
        
        Args:
            seed_urls: List of initial Twitter profile URLs to start discovery
            max_iterations: Maximum number of discovery iterations (0 = seed only)
            max_profiles_per_iteration: Maximum profiles to process per iteration
            
        Returns:
            DiscoveryResult with comprehensive discovery results
            
        Raises:
            ValueError: If seed_urls is empty or invalid
            RuntimeError: If browser setup fails after all retries
        """
        if not seed_urls:
            raise ValueError("Seed URLs cannot be empty")
        
        # Validate all seed URLs
        for url in seed_urls:
            if not self._validate_twitter_url(url):
                raise ValueError(f"Invalid Twitter URL: {url}")
        
        logger.info(f"Starting discovery with {len(seed_urls)} seed URLs, max_iterations={max_iterations}")
        
        # Set up browser and login at the beginning
        if not self.setup_browser():
            logger.warning("Main browser setup failed, trying fallback configurations...")
            if not self._setup_browser_fallback():
                raise RuntimeError("Failed to set up browser after all retries and fallbacks")
        
        # Login to Twitter for accessing following pages
        login_success = self._login_to_twitter()
        if not login_success:
            logger.warning("Failed to login to Twitter - following pages may not be accessible")
            logger.info("Will attempt to process profiles without login (limited functionality)")
        else:
            logger.info("Successfully logged in - full functionality available")
        
        # Initialize tracking variables
        all_genai_relevant = []
        all_non_relevant = []
        all_failed = []
        processed_urls = set()
        total_processed = 0
        
        # Current iteration URLs to process
        current_urls = seed_urls.copy()
        
        try:
            # Process iterations
            for iteration in range(max_iterations + 1):  # +1 because 0 iterations = 1 processing round
                logger.info(f"Starting iteration {iteration} with {len(current_urls)} URLs")
                
                if not current_urls:
                    logger.info(f"No URLs to process in iteration {iteration}, stopping")
                    break
                
                # Limit profiles per iteration
                urls_to_process = current_urls[:max_profiles_per_iteration]
                next_iteration_urls = []
                
                for url in urls_to_process:
                    if url in processed_urls:
                        logger.info(f"Skipping already processed URL: {url}")
                        continue
                        
                    try:
                        logger.info(f"Processing profile {total_processed + 1}: {url}")
                        profile = self.process_profile(url, iteration)
                        
                        processed_urls.add(url)
                        total_processed += 1
                        
                        if profile.is_genai_relevant:
                            all_genai_relevant.append(profile)
                            # Add discovered following to next iteration
                            if profile.discovered_following and iteration < max_iterations:
                                for handle in profile.discovered_following:
                                    following_url = f"https://x.com/{handle}"
                                    if following_url not in processed_urls:
                                        next_iteration_urls.append(following_url)
                        else:
                            all_non_relevant.append(profile)
                            
                    except Exception as e:
                        logger.error(f"Failed to process profile {url}: {e}")
                        all_failed.append({
                            'url': url,
                            'error': str(e),
                            'iteration': iteration,
                            'timestamp': datetime.now().isoformat()
                        })
                
                # Prepare for next iteration
                current_urls = next_iteration_urls
                logger.info(f"Iteration {iteration} complete. Found {len(next_iteration_urls)} new URLs for next iteration")
        
        finally:
            # Clean up browser resources
            self.cleanup_browser()
        
        # Create discovery summary
        discovery_summary = {
            'total_iterations_completed': iteration + 1,
            'total_profiles_processed': total_processed,
            'genai_relevant_count': len(all_genai_relevant),
            'non_relevant_count': len(all_non_relevant),
            'failed_count': len(all_failed),
            'discovery_timestamp': datetime.now().isoformat(),
            'seed_urls': seed_urls,
            'max_iterations_requested': max_iterations
        }
        
        # Create result object
        result = DiscoveryResult(
            total_iterations=iteration + 1,
            total_profiles_processed=total_processed,
            genai_relevant_profiles=all_genai_relevant,
            non_relevant_profiles=all_non_relevant,
            failed_profiles=all_failed,
            discovery_summary=discovery_summary
        )
        
        # Save results
        output_file = self.save_results(result)
        result.output_file_path = output_file
        
        logger.info(f"Discovery complete! Found {len(all_genai_relevant)} GenAI-relevant profiles")
        return result
    
    def process_profile(self, profile_url: str, iteration: int) -> ProfileInfo:
        """
        Process a single Twitter profile to extract information and classify relevance.
        
        Args:
            profile_url: Twitter profile URL to process
            iteration: Current iteration number (0 for seed profiles)
            
        Returns:
            ProfileInfo with extracted data and classification
            
        Raises:
            ValueError: If profile_url is invalid
            WebDriverException: If page loading fails
        """
        if not self._validate_twitter_url(profile_url):
            raise ValueError(f"Invalid Twitter URL: {profile_url}")
        
        # Extract username from URL
        username = self._extract_username_from_url(profile_url)
        handle = f"@{username}"
        
        logger.info(f"Processing profile: {handle}")
        
        # Browser should already be set up from discover_accounts method
        if not self.driver:
            logger.warning("Browser not initialized - attempting to set up")
            if not self.setup_browser():
                raise RuntimeError("Failed to set up browser")
        
        try:
            # Extract profile information
            profile_info = self.extract_profile_info(profile_url)
            username, handle, description, followers_count, following_count = profile_info
            
            # Classify relevance using Gemini AI
            is_relevant, reasoning = self.classify_profile_relevance(profile_info)
            
            # Create profile object
            profile = ProfileInfo(
                username=username,
                handle=handle,
                profile_url=profile_url,
                description=description,
                followers_count=followers_count,
                following_count=following_count,
                is_genai_relevant=is_relevant,
                genai_classification_reason=reasoning,
                iteration_discovered=iteration,
                discovery_timestamp=datetime.now().isoformat()
            )
            
            # If relevant, extract following accounts
            if is_relevant:
                try:
                    discovered_following = self.extract_following_accounts(profile_url)
                    profile.discovered_following = discovered_following
                    logger.info(f"Discovered {len(discovered_following)} following accounts for {handle}")
                except Exception as e:
                    logger.warning(f"Failed to extract following for {handle}: {e}")
                    profile.discovered_following = []
            
            return profile
            
        except Exception as e:
            logger.error(f"Error processing profile {profile_url}: {e}")
            raise
    
    def extract_profile_info(self, profile_url: str) -> Tuple[str, str, str, Optional[int], Optional[int]]:
        """
        Extract basic profile information from a Twitter profile page using Gemini AI image analysis.
        
        Args:
            profile_url: Twitter profile URL
            
        Returns:
            Tuple of (username, handle, description, followers_count, following_count)
            
        Raises:
            WebDriverException: If page elements cannot be found
        """
        # Navigate to profile page
        self.driver.get(profile_url)
        
        # Wait for page to load
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "main"))
            )
        except TimeoutException:
            logger.warning(f"Page load timeout for {profile_url}")
        
        # Wait a bit for dynamic content
        time.sleep(3)
        
        # Extract username from URL
        username = self._extract_username_from_url(profile_url)
        handle = f"@{username}"
        
        # Capture screenshot of the profile page
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(self.screenshots_dir, f"profile_{username}_{timestamp}.png")
        
        try:
            self.driver.save_screenshot(screenshot_path)
            screenshot_saved = True
        except Exception as e:
            logger.debug(f"Could not take profile screenshot: {e}")
            screenshot_saved = False
        
        # Use Gemini AI to extract profile information from the screenshot
        if screenshot_saved:
            try:
                description, followers_count, following_count = self._extract_profile_info_with_gemini(screenshot_path, username)
            except Exception as e:
                logger.warning(f"Gemini extraction failed for {username}, falling back to HTML parsing: {e}")
                # Fallback to original HTML parsing method
                description, followers_count, following_count = self._extract_profile_info_html_fallback()
        else:
            # No screenshot available, use HTML parsing
            logger.debug("No screenshot available, using HTML parsing")
            description, followers_count, following_count = self._extract_profile_info_html_fallback()
        
        return username, handle, description, followers_count, following_count
    
    def _extract_profile_info_with_gemini(self, screenshot_path: str, username: str) -> Tuple[str, Optional[int], Optional[int]]:
        """
        Extract profile information using Gemini AI with image analysis.
        
        Args:
            screenshot_path: Path to the profile screenshot
            username: Twitter username
            
        Returns:
            Tuple of (description, followers_count, following_count)
        """
        if not self.genai_model:
            raise Exception("Gemini model not initialized")
        
        # Load and encode the image
        with open(screenshot_path, "rb") as image_file:
            image_data = image_file.read()
            
        # Convert to PIL Image for Gemini
        from PIL import Image as PILImage
        import io
        pil_image = PILImage.open(io.BytesIO(image_data))
        
        # Build prompt for profile information extraction
        prompt = f"""
Please analyze this Twitter profile screenshot for user @{username} and extract the following information:

1. Profile description/bio (the text under the user's name and handle)
2. Number of followers (look for "X Followers" or similar)
3. Number of following (look for "X Following" or similar)

Please format your response as JSON:
{{
    "description": "profile bio text here",
    "followers_count": number or null,
    "following_count": number or null
}}

Notes:
- For numbers, convert K to thousands and M to millions (e.g., "1.2K" → 1200, "2.5M" → 2500000)
- If any information is not visible or unclear, use null
- Keep the description exactly as shown in the profile
"""
        
        # Generate content with image
        response = self.genai_model.generate_content([prompt, pil_image])
        
        if not response or not response.text:
            raise Exception("Empty response from Gemini API")
        
        response_text = response.text.strip()
        
        # Parse JSON response
        try:
            # Extract JSON from response (handle cases where there might be extra text)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                data = json.loads(json_text)
                
                description = data.get('description', '')
                followers_count = data.get('followers_count')
                following_count = data.get('following_count')
                
                return description, followers_count, following_count
            else:
                raise ValueError("No valid JSON found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse Gemini response as JSON: {e}")
            logger.debug(f"Raw response: {response_text}")
            # Try to extract information using regex as fallback
            return self._extract_info_from_text_fallback(response_text)
    
    def _extract_info_from_text_fallback(self, response_text: str) -> Tuple[str, Optional[int], Optional[int]]:
        """
        Fallback method to extract information from Gemini text response using regex.
        
        Args:
            response_text: Raw text response from Gemini
            
        Returns:
            Tuple of (description, followers_count, following_count)
        """
        description = ""
        followers_count = None
        following_count = None
        
        # Try to extract description
        desc_patterns = [
            r'description["\s:]+([^"]+)',
            r'bio["\s:]+([^"]+)',
            r'Profile[^:]*:\s*([^\n]+)',
        ]
        
        for pattern in desc_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                description = match.group(1).strip().strip('"').strip("'")
                break
        
        # Try to extract follower count
        follower_patterns = [
            r'followers?["\s:]*(\d+(?:\.\d+)?[KMkm]?)',
            r'(\d+(?:\.\d+)?[KMkm]?)\s+followers?',
        ]
        
        for pattern in follower_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                followers_count = self._parse_number_with_suffix(match.group(1))
                break
        
        # Try to extract following count
        following_patterns = [
            r'following["\s:]*(\d+(?:\.\d+)?[KMkm]?)',
            r'(\d+(?:\.\d+)?[KMkm]?)\s+following',
        ]
        
        for pattern in following_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                following_count = self._parse_number_with_suffix(match.group(1))
                break
        
        return description, followers_count, following_count
    
    def _extract_profile_info_html_fallback(self) -> Tuple[str, Optional[int], Optional[int]]:
        """
        Fallback method to extract profile info using HTML parsing (original method).
        
        Returns:
            Tuple of (description, followers_count, following_count)
        """
        # Extract description
        description = ""
        try:
            desc_element = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="UserDescription"]')
            description = desc_element.text.strip()
        except (NoSuchElementException, WebDriverException):
            logger.debug("Description not found using HTML parsing")
        
        # Extract followers count
        followers_count = None
        try:
            followers_element = self.driver.find_element(By.CSS_SELECTOR, 'a[href$="/verified_followers"], a[href$="/followers"]')
            followers_text = followers_element.text
            followers_count = self._parse_number_with_suffix(followers_text)
        except (NoSuchElementException, WebDriverException):
            logger.debug("Followers count not found using HTML parsing")
        
        # Extract following count
        following_count = None
        try:
            following_element = self.driver.find_element(By.CSS_SELECTOR, 'a[href$="/following"]')
            following_text = following_element.text
            following_count = self._parse_number_with_suffix(following_text)
        except (NoSuchElementException, WebDriverException):
            logger.debug("Following count not found using HTML parsing")
        
        return description, followers_count, following_count
    
    def classify_profile_relevance(self, profile_info: Tuple[str, str, str, Optional[int], Optional[int]]) -> Tuple[bool, str]:
        """
        Use Gemini AI to classify if a profile is relevant to generative AI.
        
        Args:
            profile_info: Tuple of (username, handle, description, followers_count, following_count)
            
        Returns:
            Tuple of (is_relevant: bool, reasoning: str)
            
        Raises:
            Exception: If Gemini API call fails
        """
        if not self.genai_model:
            # Fallback: simple keyword-based classification
            username, handle, description, followers_count, following_count = profile_info
            ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'deep learning', 
                          'neural network', 'generative', 'llm', 'gpt', 'transformer']
            
            text_to_check = f"{username} {description}".lower()
            has_ai_keywords = any(keyword in text_to_check for keyword in ai_keywords)
            
            return has_ai_keywords, f"Keyword-based classification: {'YES' if has_ai_keywords else 'NO'}"
        
        username, handle, description, followers_count, following_count = profile_info
        
        # Build prompt for Gemini
        prompt = self._build_classification_prompt(username, handle, description, followers_count, following_count)
        
        try:
            response = self.genai_model.generate_content(prompt)
            
            if not response or not response.text:
                raise Exception("Empty response from Gemini API")
            
            response_text = response.text.strip()
            
            # Parse response for YES/NO decision
            is_relevant = response_text.upper().startswith('YES')
            
            return is_relevant, response_text
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    def extract_following_accounts(self, profile_url: str) -> List[str]:
        """
        Navigate to a profile's "following" page and extract account handles using image analysis.
        
        Args:
            profile_url: Base Twitter profile URL
            
        Returns:
            List of discovered Twitter handles (without @ prefix)
            
        Raises:
            WebDriverException: If following page cannot be accessed
        """
        # Ensure we're logged in before accessing following page
        if not self.is_logged_in:
            logger.warning("Not logged in - following page access may be limited")
            logger.info("Attempting to access following page anyway (may have limited results)")
            # Don't fail completely, just warn and continue
        
        # Construct following page URL with proper format
        username = self._extract_username_from_url(profile_url)
        # Fix URL construction: use the exact username case from the profile URL
        following_url = f"https://x.com/{username}/following"
        
        logger.info(f"Extracting following accounts from: {following_url}")
        
        try:
            # Navigate to following page
            self.driver.get(following_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "main"))
            )
            
            time.sleep(3)  # Wait for initial content load
            
            # Check if we got blocked or need to login
            try:
                current_url = str(self.driver.current_url) if hasattr(self.driver, 'current_url') else ""
                page_source = str(self.driver.page_source) if hasattr(self.driver, 'page_source') else ""
                
                if "login" in current_url.lower() or "This browser is no longer supported" in page_source:
                    logger.warning("Following page requires login or browser is blocked")
                    return []  # Return empty list instead of failing
            except (AttributeError, TypeError):
                # Handle cases where driver attributes are Mock objects or unavailable
                logger.debug("Could not check page state - continuing with extraction")
            
            discovered_handles = set()
            screenshots_taken = []
            max_scrolls = 10  # Limit scrolling for efficiency
            scroll_count = 0
            last_scroll_position = 0
            no_change_count = 0
            
            while scroll_count < max_scrolls:
                # Take screenshot of current view
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = os.path.join(self.screenshots_dir, f"following_{username}_{timestamp}_{scroll_count:02d}.png")
                
                try:
                    self.driver.save_screenshot(screenshot_path)
                    screenshots_taken.append(screenshot_path)
                except Exception as e:
                    logger.debug(f"Could not take screenshot: {e}")
                    # Continue without screenshot - rely on HTML parsing
                
                # Extract handles from current screenshot using Gemini
                try:
                    handles_from_image = self._extract_handles_from_following_screenshot(screenshot_path)
                    for handle in handles_from_image:
                        if handle and handle != username:  # Don't include self
                            discovered_handles.add(handle)
                except Exception as e:
                    logger.warning(f"Failed to extract handles from screenshot {screenshot_path}: {e}")
                
                # Also try HTML parsing as backup
                try:
                    handles_from_html = self._extract_handles_from_html()
                    for handle in handles_from_html:
                        if handle and handle != username:
                            discovered_handles.add(handle)
                except Exception as e:
                    logger.debug(f"HTML parsing backup failed: {e}")
                
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for content to load
                
                # Check if scroll position changed
                current_scroll_position = self.driver.execute_script("return window.pageYOffset;")
                if current_scroll_position == last_scroll_position:
                    no_change_count += 1
                    if no_change_count >= 3:  # No change for 3 consecutive scrolls
                        logger.info("Reached end of following list")
                        break
                else:
                    no_change_count = 0
                    last_scroll_position = current_scroll_position
                
                scroll_count += 1
            
            discovered_list = list(discovered_handles)
            logger.info(f"Discovered {len(discovered_list)} following accounts using image analysis")
            return discovered_list
            
        except Exception as e:
            logger.error(f"Error extracting following accounts: {e}")
            raise WebDriverException(f"Failed to extract following accounts: {e}")
    
    def _extract_handles_from_following_screenshot(self, screenshot_path: str) -> List[str]:
        """
        Extract Twitter handles from a following page screenshot using Gemini AI.
        
        Args:
            screenshot_path: Path to the following page screenshot
            
        Returns:
            List of Twitter handles (without @ prefix)
        """
        if not self.genai_model:
            return []
        
        # Check if screenshot file exists
        if not os.path.exists(screenshot_path):
            logger.debug(f"Screenshot file not found: {screenshot_path}")
            return []
        
        try:
            # Load and process the image
            with open(screenshot_path, "rb") as image_file:
                image_data = image_file.read()
                
            from PIL import Image as PILImage
            import io
            pil_image = PILImage.open(io.BytesIO(image_data))
            
            # Build prompt for following accounts extraction
            prompt = """
Please analyze this Twitter "following" page screenshot and extract all visible Twitter usernames/handles.

Look for:
- Profile names and @handles in the following list
- User profiles being followed
- Any visible usernames in the format @username or just username

Please respond with a JSON array of usernames (without @ prefix):
["username1", "username2", "username3"]

Notes:
- Only include actual Twitter usernames, not display names
- Remove the @ symbol if present
- Skip any verified badges, follower counts, or other UI elements
- If no usernames are visible, return an empty array []
"""
            
            # Generate content with image
            response = self.genai_model.generate_content([prompt, pil_image])
            
            if not response or not response.text:
                return []
            
            response_text = response.text.strip()
            
            # Parse JSON response
            try:
                # Extract JSON from response
                json_start = response_text.find('[')
                json_end = response_text.rfind(']') + 1
                if json_start >= 0 and json_end > json_start:
                    json_text = response_text[json_start:json_end]
                    handles = json.loads(json_text)
                    
                    # Clean and validate handles
                    clean_handles = []
                    for handle in handles:
                        if isinstance(handle, str):
                            clean_handle = handle.strip().lstrip('@').lower()
                            if re.match(r'^[a-zA-Z0-9_]+$', clean_handle):
                                clean_handles.append(clean_handle)
                    
                    return clean_handles
                else:
                    # Try to extract handles using regex as fallback
                    return self._extract_handles_from_text_regex(response_text)
                    
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"Failed to parse Gemini response as JSON: {e}")
                return self._extract_handles_from_text_regex(response_text)
                
        except Exception as e:
            logger.warning(f"Error extracting handles from screenshot with Gemini: {e}")
            return []
    
    def _extract_handles_from_text_regex(self, text: str) -> List[str]:
        """
        Extract handles from text using regex patterns.
        
        Args:
            text: Text to extract handles from
            
        Returns:
            List of handles
        """
        handles = set()
        
        # Various patterns to match Twitter handles
        patterns = [
            r'@([a-zA-Z0-9_]+)',  # @username
            r'"([a-zA-Z0-9_]+)"',  # "username" 
            r"'([a-zA-Z0-9_]+)'",  # 'username'
            r'\b([a-zA-Z0-9_]{3,15})\b',  # standalone usernames (3-15 chars)
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, str) and len(match) >= 3:
                    handles.add(match.lower())
        
        return list(handles)
    
    def _extract_handles_from_html(self) -> List[str]:
        """
        Backup method to extract handles using HTML parsing.
        
        Returns:
            List of handles extracted from HTML
        """
        handles = set()
        
        try:
            # Look for various selectors that might contain usernames
            account_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                '[data-testid="UserCell"] a[href*="/"], [role="link"][href*="/"]')
            
            for element in account_elements:
                try:
                    href = element.get_attribute('href')
                    if href and '/status/' not in href and '/i/' not in href:
                        # Extract username from href
                        if 'twitter.com/' in href or 'x.com/' in href:
                            handle = href.split('/')[-1]
                            if handle and re.match(r'^[a-zA-Z0-9_]+$', handle):
                                handles.add(handle.lower())
                except:
                    continue
            
            # Also try to find handles in text content
            text_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                '[data-testid="UserCell"]')
            
            for element in text_elements:
                try:
                    text = element.text
                    # Look for @username patterns
                    at_handles = re.findall(r'@(\w+)', text)
                    for handle in at_handles:
                        if re.match(r'^[a-zA-Z0-9_]+$', handle):
                            handles.add(handle.lower())
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Error in HTML parsing backup: {e}")
        
        return list(handles)
    
    def _login_to_twitter(self) -> bool:
        """
        Login to Twitter using provided credentials with enhanced anti-detection measures.
        
        Returns:
            True if login successful, False otherwise
        """
        try:
            logger.info("Attempting to login to Twitter...")
            
            # Navigate to Twitter login page
            self.driver.get("https://x.com/login")
            
            # Add random delay to appear more human-like
            time.sleep(3 + (time.time() % 2))  # 3-5 second delay
            
            # Check if we got the "browser not supported" page
            try:
                unsupported_element = self.driver.find_element(By.XPATH, "//*[contains(text(), 'This browser is no longer supported')]")
                if unsupported_element:
                    logger.error("Twitter detected unsupported browser - trying alternative approach")
                    # Try direct navigation to a profile instead
                    return self._try_direct_access()
            except:
                pass  # Element not found, continue with login
            
            # Wait for login form to load with extended timeout
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.NAME, "text"))
                )
            except TimeoutException:
                logger.error("Login form did not load - trying alternative selectors")
                # Try alternative selectors
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.any_of(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="text"]')),
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[autocomplete="username"]')),
                            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-testid="ocfEnterTextTextInput"]'))
                        )
                    )
                except TimeoutException:
                    logger.error("Could not find username input field")
                    return False
            
            # Find and fill username field
            username_field = None
            for selector in ['input[name="text"]', 'input[autocomplete="username"]', 'input[data-testid="ocfEnterTextTextInput"]']:
                try:
                    username_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not username_field:
                logger.error("Could not locate username field")
                return False
            
            # Type username slowly to mimic human behavior
            username_field.clear()
            for char in TWITTER_USERNAME:
                username_field.send_keys(char)
                time.sleep(0.05 + (time.time() % 0.1))  # Random delay between keystrokes
            
            time.sleep(1)
            
            # Find and click Next button
            next_button = None
            for selector in ['//span[text()="Next"]/..', '//div[@role="button"]//span[text()="Next"]/..', '[data-testid="LoginForm_Login_Button"]']:
                try:
                    if selector.startswith('//'):
                        next_button = self.driver.find_element(By.XPATH, selector)
                    else:
                        next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not next_button:
                logger.error("Could not find Next button")
                return False
            
            next_button.click()
            time.sleep(3)
            
            # Wait for password field
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.NAME, "password")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]')),
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[autocomplete="current-password"]'))
                    )
                )
            except TimeoutException:
                logger.error("Password field did not appear")
                return False
            
            # Find password field
            password_field = None
            for selector in ['input[name="password"]', 'input[type="password"]', 'input[autocomplete="current-password"]']:
                try:
                    password_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not password_field:
                logger.error("Could not locate password field")
                return False
            
            # Type password slowly
            password_field.clear()
            for char in TWITTER_PASSWORD:
                password_field.send_keys(char)
                time.sleep(0.05 + (time.time() % 0.1))
            
            time.sleep(1)
            
            # Find and click Log In button
            login_button = None
            for selector in ['//span[text()="Log in"]/..', '//div[@role="button"]//span[text()="Log in"]/..', '[data-testid="LoginForm_Login_Button"]']:
                try:
                    if selector.startswith('//'):
                        login_button = self.driver.find_element(By.XPATH, selector)
                    else:
                        login_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not login_button:
                logger.error("Could not find Log In button")
                return False
            
            login_button.click()
            
            # Wait for login to complete with extended timeout
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="SideNav_AccountSwitcher_Button"]')),
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="primaryColumn"]')),
                        EC.url_contains("home"),
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="Home timeline"]'))
                    )
                )
                
                self.is_logged_in = True
                logger.info("Successfully logged in to Twitter")
                return True
                
            except TimeoutException:
                logger.error("Login timeout - could not verify successful login")
                # Check if we're actually logged in by looking at the current URL
                current_url = self.driver.current_url
                if "home" in current_url or "x.com" in current_url:
                    logger.info("Login appears successful based on URL")
                    self.is_logged_in = True
                    return True
                return False
            
        except Exception as e:
            logger.error(f"Error during Twitter login: {e}")
            return False
    
    def _try_direct_access(self) -> bool:
        """
        Try to access Twitter directly without explicit login if browser is detected.
        
        Returns:
            True if we can access content, False otherwise
        """
        try:
            logger.info("Attempting direct access to Twitter content...")
            
            # Try to access a public Twitter page
            test_url = "https://x.com/elonmusk"  # Public account
            self.driver.get(test_url)
            
            time.sleep(5)
            
            # Check if we can see profile content
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.TAG_NAME, "article")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="UserName"]')),
                        EC.presence_of_element_located((By.TAG_NAME, "main"))
                    )
                )
                
                # Check if we still get the "browser not supported" message
                if "This browser is no longer supported" in self.driver.page_source:
                    logger.error("Still getting browser not supported message")
                    return False
                
                logger.info("Direct access appears to work")
                return True
                
            except TimeoutException:
                logger.error("Could not access Twitter content directly")
                return False
                
        except Exception as e:
            logger.error(f"Error during direct access attempt: {e}")
            return False
    
    def setup_browser(self) -> bool:
        """
        Set up Selenium browser with enhanced anti-detection settings.
        
        Returns:
            True if browser setup successful, False otherwise
        """
        if self.driver:
            return True  # Already set up
        
        for attempt in range(self.max_browser_retries):
            try:
                logger.info(f"Setting up browser (attempt {attempt + 1}/{self.max_browser_retries})")
                
                # Chrome options with enhanced anti-detection
                chrome_options = Options()
                
                # Basic headless setup
                chrome_options.add_argument("--headless=new")  # Use new headless mode
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                
                # Window and display settings
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument("--start-maximized")
                
                # Enhanced user agent (more recent Chrome version)
                chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                
                # Anti-detection settings
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                chrome_options.add_argument("--disable-extensions")
                chrome_options.add_argument("--disable-plugins")
                chrome_options.add_argument("--disable-web-security")
                chrome_options.add_argument("--allow-running-insecure-content")
                chrome_options.add_argument("--ignore-certificate-errors")
                chrome_options.add_argument("--ignore-ssl-errors")
                chrome_options.add_argument("--ignore-certificate-errors-spki-list")
                
                # Memory and performance
                chrome_options.add_argument("--memory-pressure-off")
                chrome_options.add_argument("--max_old_space_size=4096")
                
                # Additional anti-fingerprinting
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                
                # Preferences to avoid detection
                prefs = {
                    "profile.default_content_setting_values": {
                        "notifications": 2,
                        "media_stream": 2,
                    },
                    "profile.default_content_settings.popups": 0,
                }
                chrome_options.add_experimental_option("prefs", prefs)
                
                # Set up ChromeDriver
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
                # Additional anti-detection measures
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                # Test basic functionality
                logger.info("Testing browser functionality...")
                self.driver.get("data:text/html,<html><body><h1>Browser Test</h1></body></html>")
                
                logger.info("Browser setup successful")
                return True
                
            except Exception as e:
                logger.warning(f"Browser setup attempt {attempt + 1} failed: {e}")
                
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                
                if attempt < self.max_browser_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Waiting {delay}s before retry...")
                    time.sleep(delay)
        
        logger.error("Failed to set up browser after all retries")
        return False
    
    def _setup_browser_fallback(self) -> bool:
        """
        Fallback browser setup with alternative configurations to avoid detection.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("Trying fallback browser configurations...")
        
        fallback_configs = [
            {
                "name": "Minimal headless",
                "options": ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--window-size=1920,1080"]
            },
            {
                "name": "Non-headless (visible)",
                "options": ["--no-sandbox", "--disable-dev-shm-usage", "--window-size=1920,1080", "--start-maximized"]
            },
            {
                "name": "Stealth mode",
                "options": [
                    "--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ]
            }
        ]
        
        for config in fallback_configs:
            try:
                logger.info(f"Trying {config['name']} configuration...")
                
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                
                chrome_options = Options()
                for option in config['options']:
                    chrome_options.add_argument(option)
                
                # Basic anti-detection
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
                # Test with a simple page first
                self.driver.get("https://httpbin.org/user-agent")
                time.sleep(2)
                
                # Test Twitter access
                self.driver.get("https://x.com")
                time.sleep(5)
                
                # Check if we get the "browser not supported" message
                if "This browser is no longer supported" not in self.driver.page_source:
                    logger.info(f"{config['name']} configuration successful")
                    return True
                else:
                    logger.warning(f"{config['name']} still detected as unsupported")
                    
            except Exception as e:
                logger.warning(f"{config['name']} failed: {e}")
                continue
        
        return False
    
    def cleanup_browser(self) -> None:
        """Clean up browser resources."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser cleanup successful")
            except Exception as e:
                logger.warning(f"Error during browser cleanup: {e}")
            finally:
                self.driver = None
    
    def save_results(self, result: DiscoveryResult, output_file: str = None) -> str:
        """
        Save discovery results to JSON file.
        
        Args:
            result: DiscoveryResult to save
            output_file: Optional output file path
            
        Returns:
            Path to saved results file
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.output_dir, f"twitter_discovery_results_{timestamp}.json")
        
        # Convert dataclasses to dict for JSON serialization
        result_dict = {
            'total_iterations': result.total_iterations,
            'total_profiles_processed': result.total_profiles_processed,
            'genai_relevant_profiles': [asdict(profile) for profile in result.genai_relevant_profiles],
            'non_relevant_profiles': [asdict(profile) for profile in result.non_relevant_profiles],
            'failed_profiles': result.failed_profiles,
            'discovery_summary': result.discovery_summary
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Results saved to: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            raise
    
    def _validate_twitter_url(self, url: str) -> bool:
        """
        Validate if URL is a valid Twitter profile URL.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid Twitter profile URL, False otherwise
        """
        if not url:
            return False
        
        try:
            parsed = urlparse(url)
            
            # Check protocol
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Check domain
            domain = parsed.netloc.lower()
            valid_domains = ['twitter.com', 'www.twitter.com', 'x.com', 'www.x.com']
            if domain not in valid_domains:
                return False
            
            # Check path (should have username)
            path = parsed.path.strip('/')
            if not path or '/' in path:  # Should be just username, no sub-paths
                return False
            
            # Username should be alphanumeric/underscore only
            if not re.match(r'^[a-zA-Z0-9_]+$', path):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _extract_username_from_url(self, url: str) -> str:
        """
        Extract username from Twitter profile URL.
        
        Args:
            url: Twitter profile URL
            
        Returns:
            Username (without @ prefix)
            
        Raises:
            ValueError: If URL format is invalid
        """
        if not self._validate_twitter_url(url):
            raise ValueError(f"Invalid Twitter URL format: {url}")
        
        try:
            parsed = urlparse(url)
            username = parsed.path.strip('/')
            return username
        except Exception as e:
            raise ValueError(f"Could not extract username from URL: {url}") from e
    
    def _build_classification_prompt(self, username: str, handle: str, description: str, 
                                   followers_count: Optional[int], following_count: Optional[int]) -> str:
        """
        Build prompt for Gemini AI to classify profile relevance.
        
        Args:
            username: Twitter username
            handle: Twitter handle (@username)
            description: Profile description/bio
            followers_count: Number of followers
            following_count: Number of following
            
        Returns:
            Formatted prompt for Gemini AI
        """
        prompt = f"""
Please analyze this Twitter profile and determine if the user is active in the generative AI field.

Profile Information:
- Username: {username}
- Handle: {handle}
- Bio/Description: "{description}"
- Followers: {followers_count if followers_count else 'Unknown'}
- Following: {following_count if following_count else 'Unknown'}

Criteria for being "active in generative AI":
- Works at AI companies (OpenAI, Anthropic, Google DeepMind, etc.)
- Conducts AI research (universities, research labs)
- Develops AI tools or applications
- Regularly discusses AI topics, papers, or developments
- Is an AI influencer, educator, or thought leader
- Creates AI-related content (tutorials, courses, etc.)

Please respond with:
- Start with "YES" if they are active in generative AI, or "NO" if they are not
- Follow with a brief explanation of your reasoning

Examples:
- YES - This person works at OpenAI and regularly posts about AI research
- NO - This person is a chef who posts about cooking recipes
- YES - AI researcher at Stanford working on large language models

Response:"""
        
        return prompt.strip()
    
    def _parse_number_with_suffix(self, text: str) -> Optional[int]:
        """
        Parse follower/following count text with K/M suffixes.
        
        Args:
            text: Text like "1,234 Followers" or "10.5K Following"
            
        Returns:
            Parsed number or None if parsing fails
        """
        if not text:
            return None
        
        try:
            # Extract number part (remove "Followers", "Following", etc.)
            number_text = re.search(r'([0-9,]+\.?[0-9]*[KMkm]?)', text)
            if not number_text:
                return None
            
            number_str = number_text.group(1).replace(',', '')
            
            # Handle K and M suffixes
            if number_str.lower().endswith('k'):
                base = float(number_str[:-1])
                return int(base * 1000)
            elif number_str.lower().endswith('m'):
                base = float(number_str[:-1])
                return int(base * 1000000)
            else:
                return int(float(number_str))
                
        except (ValueError, AttributeError):
            return None

def discover_twitter_accounts(seed_urls: List[str], max_iterations: int = 1,
                            output_dir: str = "./twitter_discovery_output") -> DiscoveryResult:
    """
    Convenience function for discovering Twitter accounts.
    
    Args:
        seed_urls: List of initial Twitter profile URLs
        max_iterations: Maximum number of discovery iterations
        output_dir: Directory to store results
        
    Returns:
        DiscoveryResult with comprehensive discovery results
    """
    service = TwitterAccountDiscoveryService(output_dir=output_dir)
    try:
        return service.discover_accounts(seed_urls, max_iterations)
    finally:
        service.cleanup_browser() 