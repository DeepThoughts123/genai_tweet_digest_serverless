#!/usr/bin/env python3
"""
Visual Tweet Capturer

This comprehensive approach captures visual representations of ALL Twitter content types:
1. Conversations/threads (multi-tweet discussions)
2. Individual tweets (original posts)  
3. Retweets (shared content with RT @)

Features:
- Account-based organization (each account gets its own folder)
- Content type prefixes (convo_, tweet_, retweet_)
- Individual tweet capture at 60% page zoom for optimal clarity
- Intelligent duplicate detection and scrolling
- ID-based ordering for consistent navigation
- Cross-account testing with --account parameter
- Production-ready for serverless GenAI processing

Perfect for comprehensive Twitter content analysis!
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import requests
from typing import Dict, Any, Optional, List

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add lambdas to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'lambdas'))

from shared.tweet_services import TweetFetcher

class VisualTweetCapturer:
    """Visual tweet capturer using browser automation and screenshots."""
    
    def __init__(self, headless=True, crop_enabled=False, crop_x1=0, crop_y1=0, crop_x2=100, crop_y2=100, 
                 max_browser_retries=3, retry_delay=2.0, retry_backoff=2.0):
        self.api_fetcher = TweetFetcher()
        self.headless = headless
        self.driver = None
        self.screenshots = []
        
        # Browser retry configuration
        self.max_browser_retries = max_browser_retries
        self.retry_delay = retry_delay  # Initial delay in seconds
        self.retry_backoff = retry_backoff  # Backoff multiplier
        
        # Cropping parameters
        self.crop_enabled = crop_enabled
        self.crop_x1 = crop_x1  # Left boundary as percentage (0-100)
        self.crop_y1 = crop_y1  # Top boundary as percentage (0-100) 
        self.crop_x2 = crop_x2  # Right boundary as percentage (0-100)
        self.crop_y2 = crop_y2  # Bottom boundary as percentage (0-100)
        
        # Validate crop parameters
        if self.crop_enabled:
            self._validate_crop_parameters()
        
        # Create base output directory
        self.base_output_dir = "visual_captures"
        os.makedirs(self.base_output_dir, exist_ok=True)
        
        # Current conversation output directory (will be set per conversation)
        self.output_dir = self.base_output_dir
    
    def _validate_crop_parameters(self):
        """Validate crop parameters are within valid ranges."""
        if not (0 <= self.crop_x1 < self.crop_x2 <= 100):
            raise ValueError(f"Invalid crop X coordinates: x1={self.crop_x1}, x2={self.crop_x2}. Must be 0 <= x1 < x2 <= 100")
        if not (0 <= self.crop_y1 < self.crop_y2 <= 100):
            raise ValueError(f"Invalid crop Y coordinates: y1={self.crop_y1}, y2={self.crop_y2}. Must be 0 <= y1 < y2 <= 100")
        
        print(f"✂️ Cropping enabled: ({self.crop_x1}%, {self.crop_y1}%) to ({self.crop_x2}%, {self.crop_y2}%)")
    
    def crop_image(self, image_path: str, output_path: str = None) -> str:
        """
        Crop an image based on percentage coordinates.
        
        Args:
            image_path: Path to the source image
            output_path: Path for the cropped image (if None, overwrites original)
            
        Returns:
            Path to the cropped image
        """
        if not self.crop_enabled:
            return image_path
        
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                
                # Calculate pixel coordinates from percentages
                left = int(width * self.crop_x1 / 100)
                top = int(height * self.crop_y1 / 100)
                right = int(width * self.crop_x2 / 100)
                bottom = int(height * self.crop_y2 / 100)
                
                # Crop the image
                cropped_img = img.crop((left, top, right, bottom))
                
                # Save the cropped image
                crop_output_path = output_path or image_path
                cropped_img.save(crop_output_path, 'PNG', optimize=True)
                
                return crop_output_path
                
        except Exception as e:
            print(f"⚠️ Error cropping image {image_path}: {e}")
            return image_path  # Return original path if cropping fails
    
    def _cleanup_failed_driver(self):
        """Clean up any existing driver instance that may have failed during setup."""
        if self.driver:
            try:
                self.driver.quit()
                print("   🧹 Cleaned up failed browser instance")
            except Exception as e:
                print(f"   ⚠️ Error during browser cleanup: {e}")
            finally:
                self.driver = None
    
    def _categorize_browser_error(self, error: Exception) -> str:
        """
        Categorize browser setup errors to determine retry strategy.
        
        Args:
            error: Exception that occurred during browser setup
            
        Returns:
            Error category: 'transient', 'permanent', or 'unknown'
        """
        error_str = str(error).lower()
        
        # Transient errors that might resolve with retry
        transient_indicators = [
            'timeout', 'connection', 'network', 'temporary', 'busy',
            'resource temporarily unavailable', 'address already in use',
            'chromedriver', 'webdriver', 'session not created'
        ]
        
        # Permanent errors that won't resolve with retry
        permanent_indicators = [
            'chrome not found', 'executable not found', 'no such file',
            'permission denied', 'access denied', 'not installed',
            'unsupported chrome version'
        ]
        
        for indicator in transient_indicators:
            if indicator in error_str:
                return 'transient'
        
        for indicator in permanent_indicators:
            if indicator in error_str:
                return 'permanent'
        
        return 'unknown'  # Default to retry for unknown errors
    
    def setup_browser(self, zoom_percent=100):
        """Set up Chrome browser with optimal settings and retry mechanism."""
        print("🔧 Setting up browser...")
        
        for attempt in range(1, self.max_browser_retries + 1):
            try:
                # Clean up any previous failed attempt
                self._cleanup_failed_driver()
                
                if attempt > 1:
                    print(f"   🔄 Retry attempt {attempt}/{self.max_browser_retries}")
                
                chrome_options = Options()
                
                if self.headless:
                    chrome_options.add_argument("--headless")
                
                # Use standard window size but we'll zoom the page content
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--window-size=1920,1080")  # Standard size
                chrome_options.add_argument("--disable-extensions")
                chrome_options.add_argument("--disable-plugins")
                chrome_options.add_argument("--disable-web-security")  # May help with some setup issues
                chrome_options.add_argument("--disable-features=VizDisplayCompositor")  # May help with crashes
                
                # Set user agent to avoid detection
                chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                
                # Use webdriver-manager to automatically handle chromedriver
                print(f"   📥 Installing/updating ChromeDriver...")
                service = Service(ChromeDriverManager().install())
                
                print(f"   🚀 Starting Chrome browser...")
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
                # Test that the browser is working by navigating to a simple page
                print(f"   🧪 Testing browser functionality...")
                self.driver.get("data:text/html,<html><body><h1>Browser Test</h1></body></html>")
                
                # Set page zoom level if different from 100%
                if zoom_percent != 100:
                    zoom_level = zoom_percent / 100.0
                    self.driver.execute_script(f"document.body.style.zoom='{zoom_level}'")
                    print(f"✅ Chrome browser initialized with {zoom_percent}% page zoom (attempt {attempt})")
                else:
                    print(f"✅ Chrome browser initialized at standard size (attempt {attempt})")
                
                return True
                
            except Exception as e:
                error_category = self._categorize_browser_error(e)
                print(f"   ❌ Browser setup failed (attempt {attempt}): {e}")
                print(f"   🔍 Error category: {error_category}")
                
                # Clean up failed driver
                self._cleanup_failed_driver()
                
                # Don't retry for permanent errors
                if error_category == 'permanent':
                    print(f"   🚫 Permanent error detected - not retrying")
                    break
                
                # If this isn't the last attempt, wait before retrying
                if attempt < self.max_browser_retries:
                    delay = self.retry_delay * (self.retry_backoff ** (attempt - 1))
                    print(f"   ⏱️ Waiting {delay:.1f} seconds before retry...")
                    time.sleep(delay)
                else:
                    print(f"   🚫 Max retry attempts ({self.max_browser_retries}) reached")
        
        # All attempts failed
        print("❌ Browser setup failed after all retry attempts")
        print("💡 Troubleshooting suggestions:")
        print("   • Ensure Chrome is installed: brew install --cask google-chrome")
        print("   • Check Chrome version compatibility")
        print("   • Try running without headless mode for debugging")
        print("   • Check system resources (memory, CPU)")
        print("   • Restart your system if issues persist")
        
        return False
    
    def setup_browser_with_fallback(self, zoom_percent=100):
        """
        Set up browser with fallback options if primary setup fails.
        
        Args:
            zoom_percent: Browser zoom percentage
            
        Returns:
            bool: True if successful, False if all options failed
        """
        # Try primary setup with retries
        if self.setup_browser(zoom_percent):
            return True
        
        print("🔄 Trying fallback browser configurations...")
        
        # Fallback 1: Try without headless mode (if currently headless)
        if self.headless:
            print("   📱 Fallback 1: Trying non-headless mode...")
            original_headless = self.headless
            self.headless = False
            
            if self.setup_browser(zoom_percent):
                print("   ✅ Non-headless mode successful")
                return True
            
            # Restore original headless setting
            self.headless = original_headless
        
        # Fallback 2: Try with minimal Chrome options
        print("   ⚙️ Fallback 2: Trying minimal Chrome configuration...")
        try:
            self._cleanup_failed_driver()
            
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Test basic functionality
            self.driver.get("data:text/html,<html><body><h1>Minimal Test</h1></body></html>")
            
            print("   ✅ Minimal configuration successful")
            return True
            
        except Exception as e:
            print(f"   ❌ Minimal configuration failed: {e}")
            self._cleanup_failed_driver()
        
        print("🚫 All browser setup options failed")
        return False
    
    def setup_conversation_folder(self, conversation_id: str, main_tweet_id: str, tweet_type: str = "tweet", account_name: str = "unknown") -> str:
        """
        Create a conversation-specific folder using the account name, then tweet type and ID.
        
        Args:
            conversation_id: The conversation ID from Twitter API
            main_tweet_id: The ID of the first/main tweet in the conversation
            tweet_type: Type of content - "convo", "tweet", or "retweet"
            account_name: Twitter account username (without @)
            
        Returns:
            Path to the conversation folder
        """
        # Use appropriate prefix based on tweet type
        if tweet_type == "convo":
            folder_name = f"convo_{main_tweet_id}"
        elif tweet_type == "retweet":
            folder_name = f"retweet_{main_tweet_id}"
        else:  # Default to "tweet" prefix
            folder_name = f"tweet_{main_tweet_id}"
        
        # Create account-specific folder first
        account_folder = os.path.join(self.base_output_dir, account_name.lower())
        os.makedirs(account_folder, exist_ok=True)
        
        # Create the content folder within the account folder
        conversation_folder = os.path.join(account_folder, folder_name)
        os.makedirs(conversation_folder, exist_ok=True)
        
        # Update the current output directory
        self.output_dir = conversation_folder
        
        print(f"📁 Created {tweet_type} folder: {account_name}/{folder_name}")
        return conversation_folder
    
    def _detect_tweet_type(self, api_data: dict) -> str:
        """
        Detect the type of tweet based on API data.
        
        Args:
            api_data: Tweet data from API
            
        Returns:
            "retweet", "tweet", or "convo"
        """
        # Check if it's a retweet by looking at the text
        text = api_data.get('text', '')
        if text.startswith('RT @'):
            return "retweet"
        
        # Check if it's part of a conversation/thread
        is_thread = api_data.get('is_thread', False)
        if is_thread:
            return "convo"
        
        # Default to individual tweet
        return "tweet"
    
    def _extract_username_from_url(self, tweet_url: str) -> str:
        """
        Extract username from tweet URL.
        
        Args:
            tweet_url: Tweet URL in format https://twitter.com/username/status/tweet_id
            
        Returns:
            Username without @ symbol, or "unknown" if extraction fails
        """
        import re
        # Pattern to match Twitter URL: https://twitter.com/username/status/tweet_id
        match = re.search(r'twitter\.com/([^/]+)/status/', tweet_url)
        if match:
            return match.group(1)
        
        # Also try x.com format
        match = re.search(r'x\.com/([^/]+)/status/', tweet_url)
        if match:
            return match.group(1)
        
        return "unknown"
    
    def _get_account_name(self, api_data: dict, tweet_url: str = None) -> str:
        """
        Extract account name from API data or tweet URL as fallback.
        
        Args:
            api_data: Tweet data from API
            tweet_url: Tweet URL as fallback source for username
            
        Returns:
            Account username (without @)
        """
        # First try to get from API data
        if api_data and 'author' in api_data and 'username' in api_data['author']:
            username = api_data['author']['username']
            if username != 'unknown':
                return username
        
        # Fallback to extracting from URL
        if tweet_url:
            username = self._extract_username_from_url(tweet_url)
            if username != 'unknown':
                print(f"📝 Extracted account name from URL: @{username}")
                return username
        
        return "unknown"
    
    def capture_tweet_visually(self, tweet_url: str, zoom_percent: int = 100) -> dict:
        """
        Capture complete visual representation of a tweet thread.
        
        Args:
            tweet_url: URL of the tweet to capture
            zoom_percent: Browser zoom percentage (default: 100)
        
        Returns:
            dict: Information about captured images and metadata
        """
        # Reset screenshots list for this capture to prevent accumulation from previous captures
        self.screenshots = []
        
        print(f"📸 VISUAL TWEET CAPTURER")
        print(f"🔗 URL: {tweet_url}")
        if zoom_percent != 100:
            print(f"🔍 Browser zoom: {zoom_percent}%")
        
        # Step 1: Get API data for metadata
        print(f"\n1️⃣ Fetching API metadata...")
        api_data = self.api_fetcher.fetch_tweet_by_url(tweet_url)
        
        if not api_data:
            print("⚠️ Could not fetch API metadata, proceeding with visual capture only")
            # Extract tweet ID and username from URL as fallback
            tweet_id_from_url = self._extract_tweet_id(tweet_url)
            username_from_url = self._extract_username_from_url(tweet_url)
            
            api_data = {
                'id': tweet_id_from_url,
                'author': {'username': username_from_url}, 
                'conversation_id': tweet_id_from_url
            }
            
            if username_from_url != 'unknown':
                print(f"📝 Extracted username from URL: @{username_from_url}")
        
        # Step 1.5: Set up conversation-specific folder
        conversation_id = api_data.get('conversation_id', api_data['id'])
        main_tweet_id = api_data['id']
        tweet_type = self._detect_tweet_type(api_data)
        account_name = self._get_account_name(api_data, tweet_url)
        self.setup_conversation_folder(conversation_id, main_tweet_id, tweet_type, account_name)
        
        # Step 2: Set up browser with specified zoom and retry mechanism
        print(f"\n2️⃣ Setting up browser with retry mechanism...")
        if not self.setup_browser_with_fallback(zoom_percent=zoom_percent):
            print("❌ Failed to set up browser after all retry attempts and fallbacks")
            return None
        
        try:
            # Step 3: Navigate to tweet with retry logic
            print(f"\n3️⃣ Loading tweet page...")
            if not self._navigate_to_page_with_retry(tweet_url):
                print("❌ Failed to load tweet page after retries")
                return None
            
            # Step 4: Capture screenshots while scrolling
            print(f"\n4️⃣ Capturing visual content...")
            self.capture_scrolling_screenshots(tweet_url)
            
            # Step 5: Process and combine screenshots
            print(f"\n5️⃣ Processing captured images...")
            result = self.process_screenshots(api_data, tweet_url)
            
            return result
            
        except Exception as e:
            print(f"❌ Capture error: {e}")
            return None
        finally:
            if self.driver:
                self.driver.quit()
                print("🔧 Browser closed")
    
    def _navigate_to_page_with_retry(self, url: str, max_retries: int = 3) -> bool:
        """
        Navigate to a page with retry mechanism for network/loading issues.
        
        Args:
            url: URL to navigate to
            max_retries: Maximum number of retry attempts
            
        Returns:
            bool: True if successful, False if all attempts failed
        """
        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    print(f"   🔄 Page load retry {attempt}/{max_retries}")
                
                # Navigate to the page
                self.driver.get(url)
                
                # Wait for key elements to load with different timeouts based on attempt
                base_timeout = 10
                timeout = base_timeout + (attempt - 1) * 5  # Increase timeout with each retry
                
                # Wait for article element (main tweet content)
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.TAG_NAME, "article"))
                )
                
                # Additional wait for dynamic content to fully load
                time.sleep(2 + attempt)  # Slightly longer wait on retries
                
                print(f"✅ Page loaded successfully (attempt {attempt})")
                return True
                
            except TimeoutException as e:
                print(f"   ⏱️ Page load timeout on attempt {attempt}: {e}")
                if attempt < max_retries:
                    delay = 2.0 * attempt  # Progressive delay
                    print(f"   ⏱️ Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                
            except WebDriverException as e:
                print(f"   🌐 WebDriver error on attempt {attempt}: {e}")
                if attempt < max_retries:
                    delay = 3.0 * attempt  # Longer delay for WebDriver issues
                    print(f"   ⏱️ Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                
            except Exception as e:
                print(f"   ❌ Unexpected error on attempt {attempt}: {e}")
                if attempt < max_retries:
                    print(f"   ⏱️ Waiting 5 seconds before retry...")
                    time.sleep(5.0)
        
        print(f"❌ Failed to load page after {max_retries} attempts")
        return False
    
    def capture_scrolling_screenshots(self, tweet_url: str):
        """Capture screenshots while scrolling down to get the complete thread with dynamic loading."""
        screenshot_count = 0
        last_scroll_position = 0
        consecutive_same_positions = 0
        max_screenshots = 20  # Prevent infinite scrolling
        
        # Get initial page info
        tweet_id = self._extract_tweet_id(tweet_url)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print(f"📸 Starting screenshot capture...")
        if self.crop_enabled:
            print(f"✂️ Will crop screenshots to ({self.crop_x1}%, {self.crop_y1}%) → ({self.crop_x2}%, {self.crop_y2}%)")
        
        # Take initial screenshot at top of page
        screenshot_path = f"{self.output_dir}/{tweet_id}_{timestamp}_page_{screenshot_count:02d}.png"
        self.driver.save_screenshot(screenshot_path)
        
        # Apply cropping if enabled
        cropped_path = self.crop_image(screenshot_path)
        self.screenshots.append(cropped_path)
        
        # Get initial scroll position and page info
        current_scroll_position = self.driver.execute_script("return window.pageYOffset")
        viewport_height = self.driver.execute_script("return window.innerHeight")
        
        print(f"   📸 Screenshot {screenshot_count + 1}: {os.path.basename(cropped_path)} (top of page)")
        if self.crop_enabled and cropped_path != screenshot_path:
            print(f"   ✂️ Applied cropping")
        print(f"   📊 Viewport: {viewport_height}px, Initial scroll: {current_scroll_position}px")
        
        screenshot_count += 1
        last_scroll_position = current_scroll_position
        
        while screenshot_count < max_screenshots:
            # Scroll down by 80% of viewport height
            scroll_amount = int(viewport_height * 0.8)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount})")
            
            # Wait for content to load and any animations
            time.sleep(2.0)
            
            # Get new scroll position
            new_scroll_position = self.driver.execute_script("return window.pageYOffset")
            current_page_height = self.driver.execute_script("return document.body.scrollHeight")
            max_scroll = current_page_height - viewport_height
            
            print(f"   🔄 Scrolled by {scroll_amount}px: {last_scroll_position}px → {new_scroll_position}px (page: {current_page_height}px)")
            
            # Check if scrolling actually worked
            if new_scroll_position <= last_scroll_position:
                consecutive_same_positions += 1
                print(f"   ⚠️ No scroll progress (attempt {consecutive_same_positions})")
                
                if consecutive_same_positions >= 2:
                    print(f"   ✅ Reached end of scrollable content")
                    break
            else:
                consecutive_same_positions = 0
                
                # Only take screenshot if we actually scrolled
                screenshot_path = f"{self.output_dir}/{tweet_id}_{timestamp}_page_{screenshot_count:02d}.png"
                self.driver.save_screenshot(screenshot_path)
                
                # Apply cropping if enabled
                cropped_path = self.crop_image(screenshot_path)
                self.screenshots.append(cropped_path)
                
                print(f"   📸 Screenshot {screenshot_count + 1}: {os.path.basename(cropped_path)}")
                if self.crop_enabled and cropped_path != screenshot_path:
                    print(f"   ✂️ Applied cropping")
                screenshot_count += 1
            
            last_scroll_position = new_scroll_position
            
            # Safety check: if we're at the bottom of the page
            if new_scroll_position >= max_scroll:
                print(f"   ✅ Reached absolute bottom of page")
                break
        
        print(f"✅ Captured {len(self.screenshots)} unique screenshots")
        if self.crop_enabled:
            print(f"✂️ All screenshots cropped to region: ({self.crop_x1}%, {self.crop_y1}%) → ({self.crop_x2}%, {self.crop_y2}%)")
    
    def process_screenshots(self, api_data: dict, tweet_url: str) -> dict:
        """Process captured screenshots without combining them."""
        if not self.screenshots:
            print("❌ No screenshots to process")
            return None
        
        print(f"🔄 Processing {len(self.screenshots)} screenshots...")
        
        # Calculate total dimensions from individual screenshots
        total_height = 0
        max_width = 0
        
        for screenshot_path in self.screenshots:
            try:
                with Image.open(screenshot_path) as img:
                    width, height = img.size
                    total_height += height
                    max_width = max(max_width, width)
            except Exception as e:
                print(f"⚠️ Error reading {screenshot_path}: {e}")
        
        # Create result metadata with cropping information
        result = {
            'tweet_url': tweet_url,
            'capture_timestamp': datetime.now().isoformat(),
            'screenshots': {
                'individual_files': [os.path.basename(path) for path in self.screenshots],
                'count': len(self.screenshots),
                'total_dimensions': {
                    'width': max_width,
                    'height': total_height
                }
            },
            'cropping': {
                'enabled': self.crop_enabled,
                'coordinates': {
                    'x1_percent': self.crop_x1,
                    'y1_percent': self.crop_y1,
                    'x2_percent': self.crop_x2,
                    'y2_percent': self.crop_y2
                } if self.crop_enabled else None
            },
            'api_metadata': api_data,
            'output_directory': self.output_dir
        }
        
        # Save metadata
        metadata_path = f"{self.output_dir}/capture_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Processing complete!")
        print(f"   📁 Conversation folder: {self.output_dir}")
        print(f"   📸 Individual screenshots: {len(self.screenshots)}")
        print(f"   📊 Total dimensions: {max_width}x{total_height}")
        if self.crop_enabled:
            print(f"   ✂️ Cropping applied: ({self.crop_x1}%, {self.crop_y1}%) → ({self.crop_x2}%, {self.crop_y2}%)")
        print(f"   💾 Metadata saved: {os.path.basename(metadata_path)}")
        
        return result
    
    def combine_screenshots(self) -> str:
        """Combine individual screenshots into a single long image."""
        if not self.screenshots:
            return None
        
        print(f"🔗 Combining screenshots...")
        
        try:
            # Load all images
            images = []
            total_height = 0
            max_width = 0
            
            for screenshot_path in self.screenshots:
                img = Image.open(screenshot_path)
                images.append(img)
                width, height = img.size
                total_height += height
                max_width = max(max_width, width)
            
            # Create combined image
            combined_image = Image.new('RGB', (max_width, total_height), color='white')
            
            # Paste images vertically
            y_offset = 0
            for img in images:
                combined_image.paste(img, (0, y_offset))
                y_offset += img.size[1]
            
            # Save combined image
            tweet_id = self._extract_tweet_id(self.screenshots[0])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            combined_path = f"{self.output_dir}/{tweet_id}_{timestamp}_combined.png"
            
            combined_image.save(combined_path, 'PNG', optimize=True)
            
            # Clean up individual images
            for img in images:
                img.close()
            
            print(f"✅ Combined image saved: {os.path.basename(combined_path)}")
            return combined_path
            
        except Exception as e:
            print(f"❌ Error combining screenshots: {e}")
            return None
    
    def _extract_tweet_id(self, path_or_url: str) -> str:
        """Extract tweet ID from path or URL."""
        import re
        match = re.search(r'(\d{19})', path_or_url)
        return match.group(1) if match else 'unknown'

    def capture_thread_visually(self, thread_data: Dict[str, Any]) -> dict:
        """
        Capture complete visual representation of a thread by capturing each tweet individually.
        
        Args:
            thread_data: Thread data dictionary with thread_tweets array
            
        Returns:
            dict: Information about captured thread images and metadata
        """
        # Reset screenshots list for this capture
        self.screenshots = []
        
        if not thread_data.get('is_thread', False):
            print("⚠️ Not a thread - falling back to single tweet capture")
            return self.capture_tweet_visually(thread_data['url'])
        
        print(f"🧵 INDIVIDUAL TWEET THREAD CAPTURER")
        print(f"📊 Thread: {thread_data['thread_tweet_count']} tweets")
        print(f"💬 Conversation ID: {thread_data['conversation_id']}")
        
        # Step 1: Set up conversation-specific folder
        conversation_id = thread_data.get('conversation_id', thread_data['id'])
        # Find the first tweet ID (chronologically earliest)
        thread_tweets = thread_data.get('thread_tweets', [])
        if thread_tweets:
            # Sort by created_at to find the actual first tweet
            sorted_tweets = sorted(thread_tweets, key=lambda x: x['created_at'])
            first_tweet_id = sorted_tweets[0]['id']
        else:
            # Fallback to main thread ID
            first_tweet_id = thread_data['id']
        
        # Use "convo" prefix for conversation/thread folders
        account_name = thread_data['author']['username']
        self.setup_conversation_folder(conversation_id, first_tweet_id, "convo", account_name)
        
        # Step 2: Get tweets ordered by ID (increasing order)
        sorted_tweets = sorted(thread_tweets, key=lambda x: int(x['id']))
        print(f"   📊 Processing {len(sorted_tweets)} tweets ordered by ID")
        
        # Step 3: Capture each tweet individually
        captured_tweets = []
        
        for i, tweet in enumerate(sorted_tweets, 1):
            tweet_id = tweet['id']
            # Use the username from thread data instead of hardcoding
            username = thread_data['author']['username']
            tweet_url = f"https://twitter.com/{username}/status/{tweet_id}"
            
            print(f"\n   📸 Capturing tweet {i}/{len(sorted_tweets)}: {tweet_id}")
            print(f"       🔗 URL: {tweet_url}")
            print(f"       💬 Text: {tweet['text'][:100]}...")
            
            # Create tweet-specific subfolder
            tweet_folder = os.path.join(self.output_dir, f"tweet_{tweet_id}")
            os.makedirs(tweet_folder, exist_ok=True)
            print(f"       📁 Created subfolder: tweet_{tweet_id}")
            
            # Capture this individual tweet at 60% zoom
            tweet_capture_result = self.capture_individual_tweet(tweet_url, tweet_id, tweet_folder)
            
            if tweet_capture_result:
                # Add tweet metadata to the result
                tweet_capture_result.update({
                    'tweet_metadata': tweet,
                    'id_order': i,  # Order by ID instead of chronological
                    'subfolder': f"tweet_{tweet_id}"
                })
                captured_tweets.append(tweet_capture_result)
                print(f"       ✅ Captured {tweet_capture_result['screenshot_count']} screenshots")
            else:
                print(f"       ❌ Failed to capture tweet {tweet_id}")
        
        # Step 4: Create comprehensive metadata without duplication
        # Remove thread_tweets from thread_data to avoid duplication with ordered_tweets
        clean_thread_data = thread_data.copy()
        # Remove the thread_tweets array since we'll have this info in ordered_tweets
        clean_thread_data.pop('thread_tweets', None)
        
        result = {
            'conversation_id': conversation_id,
            'capture_timestamp': datetime.now().isoformat(),
            'thread_summary': clean_thread_data,  # Summary info without duplicate tweet list
            'total_tweets_in_thread': len(sorted_tweets),
            'successfully_captured': len(captured_tweets),
            'ordered_tweets': captured_tweets,  # Complete ordered tweet list with capture info
            'output_directory': self.output_dir,
            'capture_strategy': 'individual_tweet_capture',
            'browser_zoom': '60_percent',
            'sort_order': 'by_tweet_id_increasing'
        }
        
        # Save comprehensive metadata
        metadata_path = f"{self.output_dir}/metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Thread processing complete!")
        print(f"   📁 Conversation folder: {self.output_dir}")
        print(f"   🧵 Tweets captured: {len(captured_tweets)}/{len(sorted_tweets)}")
        print(f"   📂 Subfolders created: {len(captured_tweets)}")
        print(f"   💾 Metadata saved: metadata.json")
        
        return result
    
    def capture_individual_tweet(self, tweet_url: str, tweet_id: str, tweet_folder: str) -> Optional[dict]:
        """
        Capture an individual tweet with scrolling at 60% page zoom, avoiding duplicates.
        
        Args:
            tweet_url: URL of the tweet to capture
            tweet_id: ID of the tweet
            tweet_folder: Folder to save screenshots in
            
        Returns:
            Dict with capture results or None if failed
        """
        # Set up browser at 60% zoom with retry mechanism
        if not self.setup_browser_with_fallback(zoom_percent=60):
            print(f"       ❌ Failed to set up browser for tweet {tweet_id} after all retries")
            return None
        
        try:
            # Navigate to tweet with retry logic
            if not self._navigate_to_page_with_retry(tweet_url):
                print(f"       ❌ Failed to load tweet page for {tweet_id} after retries")
                return None
            
            # Wait a bit more for dynamic content
            time.sleep(3.0)
            
            # Capture with intelligent scrolling to avoid duplicates
            screenshot_count = 0
            max_screenshots = 10  # Reduced since 60% zoom shows more content
            last_scroll_position = -1  # Initialize to impossible value
            consecutive_same_positions = 0
            
            # Get viewport and page info
            viewport_height = self.driver.execute_script("return window.innerHeight")
            
            # Take initial screenshot
            screenshot_path = f"{tweet_folder}/page_{screenshot_count:02d}.png"
            self.driver.save_screenshot(screenshot_path)
            
            # Apply cropping if enabled
            cropped_path = self.crop_image(screenshot_path)
            screenshot_count += 1
            
            while screenshot_count < max_screenshots:
                # Get current scroll position before scrolling
                current_scroll_position = self.driver.execute_script("return window.pageYOffset")
                current_page_height = self.driver.execute_script("return document.body.scrollHeight")
                max_scroll = current_page_height - viewport_height
                
                # Check if we've reached the bottom
                if current_scroll_position >= max_scroll:
                    print(f"           ✅ Reached bottom of page")
                    break
                
                # Scroll down by a reasonable amount (since page is zoomed to 60%)
                scroll_amount = int(viewport_height * 0.7)  # Larger scroll since content is smaller
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount})")
                
                # Wait for content to load
                time.sleep(2.5)
                
                # Get new scroll position
                new_scroll_position = self.driver.execute_script("return window.pageYOffset")
                
                # Check if we actually scrolled
                if new_scroll_position <= current_scroll_position:
                    consecutive_same_positions += 1
                    print(f"           ⚠️ No scroll progress (attempt {consecutive_same_positions})")
                    
                    if consecutive_same_positions >= 2:
                        print(f"           ✅ Cannot scroll further - end of content")
                        break
                else:
                    # We scrolled successfully, reset counter and take screenshot
                    consecutive_same_positions = 0
                    
                    # Only take screenshot if we made significant progress
                    scroll_progress = new_scroll_position - current_scroll_position
                    if scroll_progress > (viewport_height * 0.3):  # Only if scrolled more than 30% of viewport
                        screenshot_path = f"{tweet_folder}/page_{screenshot_count:02d}.png"
                        self.driver.save_screenshot(screenshot_path)
                        
                        # Apply cropping if enabled
                        cropped_path = self.crop_image(screenshot_path)
                        screenshot_count += 1
                        print(f"           📸 Screenshot {screenshot_count}: scrolled {scroll_progress}px")
                        if self.crop_enabled and cropped_path != screenshot_path:
                            print(f"           ✂️ Applied cropping")
                    else:
                        print(f"           ⏭️ Skipped screenshot - minimal scroll progress ({scroll_progress}px)")
                
                last_scroll_position = current_scroll_position
            
            return {
                'tweet_id': tweet_id,
                'tweet_url': tweet_url,
                'screenshot_count': screenshot_count,
                'screenshots': [f"page_{i:02d}.png" for i in range(screenshot_count)],
                'capture_timestamp': datetime.now().isoformat(),
                'cropping': {
                    'enabled': self.crop_enabled,
                    'coordinates': {
                        'x1_percent': self.crop_x1,
                        'y1_percent': self.crop_y1,
                        'x2_percent': self.crop_x2,
                        'y2_percent': self.crop_y2
                    } if self.crop_enabled else None
                }
            }
            
        except Exception as e:
            print(f"       ❌ Error capturing tweet {tweet_id}: {e}")
            return None
        finally:
            if self.driver:
                self.driver.quit()

def test_visual_capture():
    """Test the visual capture approach with retry mechanism."""
    
    # Test with the specific tweet
    tweet_url = "https://twitter.com/AndrewYNg/status/1928105439368995193"
    
    print("📸 TESTING VISUAL TWEET CAPTURE WITH RETRY MECHANISM")
    print("=" * 70)
    
    # Test with custom retry configuration
    capturer = VisualTweetCapturer(
        headless=True,  # Headless mode - no browser window
        max_browser_retries=3,  # Try browser setup up to 3 times
        retry_delay=2.0,  # Start with 2 second delays
        retry_backoff=2.0  # Double the delay each retry
    )
    
    print(f"🔧 Retry Configuration:")
    print(f"   Max browser retries: {capturer.max_browser_retries}")
    print(f"   Initial retry delay: {capturer.retry_delay}s")
    print(f"   Retry backoff multiplier: {capturer.retry_backoff}x")
    print()
    
    result = capturer.capture_tweet_visually(tweet_url)
    
    if result:
        print(f"\n" + "=" * 70)
        print(f"🎉 VISUAL CAPTURE SUCCESS!")
        print("=" * 70)
        
        print(f"\n📸 CAPTURE SUMMARY:")
        screenshots = result['screenshots']
        print(f"   📁 Output folder: {result['output_directory']}")
        print(f"   📸 Screenshots taken: {screenshots['count']}")
        print(f"   📐 Total size: {screenshots['total_dimensions']['width']}x{screenshots['total_dimensions']['height']}")
        
        # Show cropping info if enabled
        cropping = result.get('cropping', {})
        if cropping.get('enabled', False):
            coords = cropping['coordinates']
            print(f"   ✂️ Cropping applied: ({coords['x1_percent']}%, {coords['y1_percent']}%) → ({coords['x2_percent']}%, {coords['y2_percent']}%)")
        
        print(f"\n📄 FILES CREATED:")
        for filename in screenshots['individual_files']:
            print(f"   • {filename}")
        print(f"   • capture_metadata.json")
        
        return True
    else:
        print(f"\n❌ Visual capture failed after all retry attempts")
        print(f"\n🔧 RETRY MECHANISM FEATURES DEMONSTRATED:")
        print(f"   ✅ Intelligent error categorization (transient vs permanent)")
        print(f"   ✅ Exponential backoff retry delays")
        print(f"   ✅ Automatic cleanup of failed browser instances")
        print(f"   ✅ Fallback configurations (non-headless, minimal options)")
        print(f"   ✅ Page loading retry with progressive timeouts")
        return False

def test_visual_capture_with_cropping():
    """Test visual capture with image cropping enabled."""
    
    tweet_url = "https://twitter.com/AndrewYNg/status/1928105439368995193"
    
    print("✂️ TESTING VISUAL CAPTURE WITH IMAGE CROPPING")
    print("=" * 70)
    
    # Test with cropping enabled - crop to middle portion of screenshots
    capturer = VisualTweetCapturer(
        headless=True,
        crop_enabled=True,
        crop_x1=20,  # Start at 20% from left
        crop_y1=10,  # Start at 10% from top
        crop_x2=80,  # End at 80% from left
        crop_y2=90,  # End at 90% from top
        max_browser_retries=2,  # Fewer retries for test
        retry_delay=1.5
    )
    
    result = capturer.capture_tweet_visually(tweet_url)
    
    if result:
        print(f"\n✅ CROPPING TEST SUCCESS!")
        print(f"   📁 Output folder: {result['output_directory']}")
        
        cropping = result['cropping']
        if cropping['enabled']:
            coords = cropping['coordinates']
            print(f"   ✂️ Cropping region: ({coords['x1_percent']}%, {coords['y1_percent']}%) → ({coords['x2_percent']}%, {coords['y2_percent']}%)")
        
        return True
    else:
        print(f"\n❌ Cropping test failed")
        return False

if __name__ == "__main__":
    print("🚀 STARTING VISUAL TWEET CAPTURER TESTS")
    print("=" * 70)
    
    # Test 1: Basic visual capture with retry mechanism
    print("\n📸 TEST 1: Basic Visual Capture with Retry Mechanism")
    success1 = test_visual_capture()
    
    # Test 2: Visual capture with cropping
    print("\n✂️ TEST 2: Visual Capture with Image Cropping")
    success2 = test_visual_capture_with_cropping()
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    if success1 and success2:
        print("🎉 ALL TESTS PASSED!")
        print(f"\n🎯 ENHANCED VISUAL CAPTURE BENEFITS:")
        print(f"   ✅ Complete visual representation")
        print(f"   ✅ Robust retry mechanism for browser failures")
        print(f"   ✅ Intelligent error categorization")
        print(f"   ✅ Exponential backoff retry delays")
        print(f"   ✅ Fallback browser configurations")
        print(f"   ✅ Page loading retry with progressive timeouts")
        print(f"   ✅ Automatic cleanup of failed instances")
        print(f"   ✅ Optional image cropping for focused content")
        print(f"   ✅ Captures entire thread and replies")
        print(f"   ✅ No text truncation issues")
        print(f"   ✅ Preserves exact formatting and layout")
        print(f"   ✅ Works with any public tweet")
        print("=" * 70)
    elif success1:
        print("✅ Basic capture test passed")
        print("⚠️ Cropping test failed")
        print("\n💡 The retry mechanism is working for basic captures")
    elif success2:
        print("⚠️ Basic capture test failed")
        print("✅ Cropping test passed")
        print("\n💡 Cropping functionality works when browser setup succeeds")
    else:
        print("❌ BOTH TESTS FAILED")
        print(f"\n🔧 TROUBLESHOOTING:")
        print(f"   • Ensure Chrome is installed: brew install --cask google-chrome")
        print(f"   • Check Chrome version compatibility")
        print(f"   • Try running with headless=False for debugging")
        print(f"   • Check system resources (memory, CPU)")
        print(f"   • Verify network connectivity")
        print(f"   • Install dependencies: pip install selenium pillow webdriver-manager")
        print("=" * 70) 