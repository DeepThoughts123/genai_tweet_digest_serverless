#!/usr/bin/env python3
"""
Visual Tweet Capturer

This approach captures the complete visual representation of a tweet thread:
1. Opens the tweet URL in a browser
2. Takes screenshots while scrolling down
3. Captures the entire conversation visually
4. Saves individual screenshots and combines them

Perfect for getting the complete visual context!
"""

import sys
import os
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import requests
from typing import Dict, Any, Optional

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add lambdas to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'lambdas'))

from shared.tweet_services import TweetFetcher

class VisualTweetCapturer:
    """Visual tweet capturer using browser automation and screenshots."""
    
    def __init__(self, headless=True):
        self.api_fetcher = TweetFetcher()
        self.headless = headless
        self.driver = None
        self.screenshots = []
        
        # Create base output directory
        self.base_output_dir = "visual_captures"
        os.makedirs(self.base_output_dir, exist_ok=True)
        
        # Current conversation output directory (will be set per conversation)
        self.output_dir = self.base_output_dir
    
    def setup_browser(self, zoom_percent=100):
        """Set up Chrome browser with optimal settings for screenshot capture."""
        print("🔧 Setting up browser...")
        
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
        
        # Set user agent to avoid detection
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            # Use webdriver-manager to automatically handle chromedriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set page zoom level if different from 100%
            if zoom_percent != 100:
                zoom_level = zoom_percent / 100.0
                self.driver.execute_script(f"document.body.style.zoom='{zoom_level}'")
                print(f"✅ Chrome browser initialized with {zoom_percent}% page zoom")
            else:
                print(f"✅ Chrome browser initialized at standard size")
                
        except Exception as e:
            print(f"❌ Chrome setup failed: {e}")
            print("💡 Please ensure Chrome is installed")
            print("   brew install --cask google-chrome")
            return False
        
        return True
    
    def setup_conversation_folder(self, conversation_id: str, main_tweet_id: str) -> str:
        """
        Create a conversation-specific folder using the main tweet ID.
        
        Args:
            conversation_id: The conversation ID from Twitter API
            main_tweet_id: The ID of the first/main tweet in the conversation
            
        Returns:
            Path to the conversation folder
        """
        # Use the main tweet ID as the folder name for easy identification
        conversation_folder = os.path.join(self.base_output_dir, f"conversation_{main_tweet_id}")
        os.makedirs(conversation_folder, exist_ok=True)
        
        # Update the current output directory
        self.output_dir = conversation_folder
        
        print(f"📁 Created conversation folder: {conversation_folder}")
        return conversation_folder
    
    def capture_tweet_visually(self, tweet_url: str) -> dict:
        """
        Capture complete visual representation of a tweet thread.
        
        Returns:
            dict: Information about captured images and metadata
        """
        # Reset screenshots list for this capture to prevent accumulation from previous captures
        self.screenshots = []
        
        print(f"📸 VISUAL TWEET CAPTURER")
        print(f"🔗 URL: {tweet_url}")
        
        # Step 1: Get API data for metadata
        print(f"\n1️⃣ Fetching API metadata...")
        api_data = self.api_fetcher.fetch_tweet_by_url(tweet_url)
        
        if not api_data:
            print("⚠️ Could not fetch API metadata, proceeding with visual capture only")
            api_data = {'id': 'unknown', 'author': {'username': 'unknown'}, 'conversation_id': 'unknown'}
        
        # Step 1.5: Set up conversation-specific folder
        conversation_id = api_data.get('conversation_id', api_data['id'])
        main_tweet_id = api_data['id']
        self.setup_conversation_folder(conversation_id, main_tweet_id)
        
        # Step 2: Set up browser
        print(f"\n2️⃣ Setting up browser...")
        if not self.setup_browser():
            return None
        
        try:
            # Step 3: Navigate to tweet
            print(f"\n3️⃣ Loading tweet page...")
            self.driver.get(tweet_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )
            print("✅ Page loaded successfully")
            
            # Step 4: Capture screenshots while scrolling
            print(f"\n4️⃣ Capturing visual content...")
            self.capture_scrolling_screenshots(tweet_url)
            
            # Step 5: Process and combine screenshots
            print(f"\n5️⃣ Processing captured images...")
            result = self.process_screenshots(api_data, tweet_url)
            
            return result
            
        except TimeoutException:
            print("❌ Page load timeout")
            return None
        except Exception as e:
            print(f"❌ Capture error: {e}")
            return None
        finally:
            if self.driver:
                self.driver.quit()
                print("🔧 Browser closed")
    
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
        
        # Take initial screenshot at top of page
        screenshot_path = f"{self.output_dir}/{tweet_id}_{timestamp}_page_{screenshot_count:02d}.png"
        self.driver.save_screenshot(screenshot_path)
        self.screenshots.append(screenshot_path)
        
        # Get initial scroll position and page info
        current_scroll_position = self.driver.execute_script("return window.pageYOffset")
        viewport_height = self.driver.execute_script("return window.innerHeight")
        
        print(f"   📸 Screenshot {screenshot_count + 1}: {os.path.basename(screenshot_path)} (top of page)")
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
                self.screenshots.append(screenshot_path)
                
                print(f"   📸 Screenshot {screenshot_count + 1}: {os.path.basename(screenshot_path)}")
                screenshot_count += 1
            
            last_scroll_position = new_scroll_position
            
            # Safety check: if we're at the bottom of the page
            if new_scroll_position >= max_scroll:
                print(f"   ✅ Reached absolute bottom of page")
                break
        
        print(f"✅ Captured {len(self.screenshots)} unique screenshots")
    
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
        
        # Create result metadata
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
        
        self.setup_conversation_folder(conversation_id, first_tweet_id)
        
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
        
        # Step 4: Create comprehensive metadata
        # Sort the thread_data's thread_tweets by ID as well
        sorted_thread_data = thread_data.copy()
        sorted_thread_data['thread_tweets'] = sorted(thread_tweets, key=lambda x: int(x['id']))
        
        result = {
            'conversation_id': conversation_id,
            'capture_timestamp': datetime.now().isoformat(),
            'thread_data': sorted_thread_data,  # Now contains ID-sorted thread_tweets
            'total_tweets_in_thread': len(sorted_tweets),
            'successfully_captured': len(captured_tweets),
            'ordered_tweets': captured_tweets,  # Ordered by tweet ID (increasing)
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
        # Set up browser at 60% zoom
        if not self.setup_browser(zoom_percent=60):
            return None
        
        try:
            # Navigate to tweet
            self.driver.get(tweet_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )
            
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
                        screenshot_count += 1
                        print(f"           📸 Screenshot {screenshot_count}: scrolled {scroll_progress}px")
                    else:
                        print(f"           ⏭️ Skipped screenshot - minimal scroll progress ({scroll_progress}px)")
                
                last_scroll_position = current_scroll_position
            
            return {
                'tweet_id': tweet_id,
                'tweet_url': tweet_url,
                'screenshot_count': screenshot_count,
                'screenshots': [f"page_{i:02d}.png" for i in range(screenshot_count)],
                'capture_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"       ❌ Error capturing tweet {tweet_id}: {e}")
            return None
        finally:
            if self.driver:
                self.driver.quit()

def test_visual_capture():
    """Test the visual capture approach."""
    
    # Test with the specific tweet
    tweet_url = "https://twitter.com/AndrewYNg/status/1928105439368995193"
    
    print("📸 TESTING VISUAL TWEET CAPTURE")
    print("=" * 60)
    
    capturer = VisualTweetCapturer(headless=True)  # Headless mode - no browser window
    result = capturer.capture_tweet_visually(tweet_url)
    
    if result:
        print(f"\n" + "=" * 60)
        print(f"🎉 VISUAL CAPTURE SUCCESS!")
        print("=" * 60)
        
        print(f"\n📸 CAPTURE SUMMARY:")
        screenshots = result['screenshots']
        print(f"   📁 Output folder: {result['output_directory']}")
        print(f"   📸 Screenshots taken: {screenshots['count']}")
        print(f"   🖼️ Combined image: {screenshots['combined_file']}")
        print(f"   📐 Total size: {screenshots['total_dimensions']['width']}x{screenshots['total_dimensions']['height']}")
        
        print(f"\n📄 FILES CREATED:")
        for filename in screenshots['individual_files']:
            print(f"   • {filename}")
        if screenshots['combined_file']:
            print(f"   • {screenshots['combined_file']} (combined)")
        print(f"   • capture_metadata.json")
        
        return True
    else:
        print(f"\n❌ Visual capture failed")
        return False

if __name__ == "__main__":
    success = test_visual_capture()
    
    if success:
        print(f"\n🎯 VISUAL CAPTURE APPROACH BENEFITS:")
        print(f"   ✅ Complete visual representation")
        print(f"   ✅ Captures entire thread and replies")
        print(f"   ✅ No text truncation issues")
        print(f"   ✅ Preserves exact formatting and layout")
        print(f"   ✅ Works with any public tweet")
        print("=" * 60)
    else:
        print(f"\n❌ Please install required dependencies:")
        print(f"   pip install selenium pillow")
        print(f"   brew install --cask google-chrome")
        print(f"   brew install chromedriver") 