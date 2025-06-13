#!/usr/bin/env python3
"""
Twitter Account Discovery Service

Discovers influential Twitter accounts in the generative AI field through iterative crawling.

Features:
- Starts with seed Twitter profile URLs
- Captures profile pages and extracts metadata (description, followers, following count)
- Uses Gemini AI to classify if users are active in generative AI space
- Crawls "following" pages to discover new accounts
- Supports N iterations of discovery
- Outputs comprehensive list of GenAI-relevant accounts

Process Flow:
1. Start with seed URLs (iteration 0)
2. For each URL, capture profile page and extract user info
3. Use Gemini AI to classify if user is GenAI-relevant
4. For relevant users, navigate to their "following" page
5. Scroll and capture following pages to extract account handles
6. Generate new URLs for discovered accounts (iteration 1, 2, ... N)
7. Repeat process for specified number of iterations
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
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
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
        
        # Initialize tracking variables
        all_genai_relevant = []
        all_non_relevant = []
        all_failed = []
        processed_urls = set()
        total_processed = 0
        
        # Current iteration URLs to process
        current_urls = seed_urls.copy()
        
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
                                following_url = f"https://twitter.com/{handle}"
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
        
        # Set up browser if not already done
        if not self.setup_browser():
            raise RuntimeError("Failed to set up browser after all retries")
        
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
        Extract basic profile information from a Twitter profile page.
        
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
        
        # Extract description
        description = ""
        try:
            desc_element = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="UserDescription"]')
            description = desc_element.text.strip()
        except (NoSuchElementException, WebDriverException):
            logger.debug(f"Description not found for {username}")
        
        # Extract followers count
        followers_count = None
        try:
            followers_element = self.driver.find_element(By.CSS_SELECTOR, 'a[href$="/verified_followers"], a[href$="/followers"]')
            followers_text = followers_element.text
            followers_count = self._parse_number_with_suffix(followers_text)
        except (NoSuchElementException, WebDriverException):
            logger.debug(f"Followers count not found for {username}")
        
        # Extract following count
        following_count = None
        try:
            following_element = self.driver.find_element(By.CSS_SELECTOR, 'a[href$="/following"]')
            following_text = following_element.text
            following_count = self._parse_number_with_suffix(following_text)
        except (NoSuchElementException, WebDriverException):
            logger.debug(f"Following count not found for {username}")
        
        return username, handle, description, followers_count, following_count
    
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
        Navigate to a profile's "following" page and extract account handles.
        
        Args:
            profile_url: Base Twitter profile URL
            
        Returns:
            List of discovered Twitter handles (without @ prefix)
            
        Raises:
            WebDriverException: If following page cannot be accessed
        """
        # Construct following page URL
        username = self._extract_username_from_url(profile_url)
        following_url = f"{profile_url.rstrip('/')}/following"
        
        logger.info(f"Extracting following accounts from: {following_url}")
        
        try:
            # Navigate to following page
            self.driver.get(following_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "main"))
            )
            
            time.sleep(3)  # Wait for initial content load
            
            discovered_handles = set()
            last_scroll_position = 0
            max_scrolls = 20  # Prevent infinite scrolling
            scroll_count = 0
            no_change_count = 0
            
            while scroll_count < max_scrolls:
                # Find account elements
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
                                    if handle and handle != username:  # Don't include self
                                        discovered_handles.add(handle)
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
                                if handle != username:  # Don't include self
                                    discovered_handles.add(handle)
                        except:
                            continue
                            
                except Exception as e:
                    logger.debug(f"Error finding account elements: {e}")
                
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
            logger.info(f"Discovered {len(discovered_list)} following accounts")
            return discovered_list
            
        except Exception as e:
            logger.error(f"Error extracting following accounts: {e}")
            raise WebDriverException(f"Failed to extract following accounts: {e}")
    
    def setup_browser(self) -> bool:
        """
        Set up Selenium browser with retry mechanism.
        
        Returns:
            True if browser setup successful, False otherwise
        """
        if self.driver:
            return True  # Already set up
        
        for attempt in range(self.max_browser_retries):
            try:
                logger.info(f"Setting up browser (attempt {attempt + 1}/{self.max_browser_retries})")
                
                # Chrome options
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
                
                # Set up ChromeDriver
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
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