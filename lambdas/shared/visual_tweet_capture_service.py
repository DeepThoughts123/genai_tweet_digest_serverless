#!/usr/bin/env python3
"""
Production Visual Tweet Capture Service

Professional screenshot capture for tweets with S3 storage integration.
Date-based folder organization for production use.

Features:
- Account-based organization with content type prefixes
- S3 integration with automatic folder creation
- Configurable browser zoom and capture parameters
- Comprehensive error handling and logging
- Support for threads, individual tweets, and retweets
- Clean metadata with no duplication
"""

import os
import json
import time
import boto3
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import logging

from .tweet_services import TweetFetcher
from .config import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VisualTweetCaptureService:
    """
    Production service for visual tweet capture with S3 storage.
    """
    
    def __init__(self, s3_bucket: str, zoom_percent: int = 60, crop_enabled: bool = False, 
                 crop_x1: int = 0, crop_y1: int = 0, crop_x2: int = 100, crop_y2: int = 100):
        """
        Initialize the visual tweet capture service.
        
        Args:
            s3_bucket: S3 bucket name for storing captured images
            zoom_percent: Browser zoom percentage for captures (default: 60%)
            crop_enabled: Enable image cropping (default: False)
            crop_x1: Left boundary as percentage (0-100)
            crop_y1: Top boundary as percentage (0-100)
            crop_x2: Right boundary as percentage (0-100)
            crop_y2: Bottom boundary as percentage (0-100)
        """
        self.s3_bucket = s3_bucket
        self.zoom_percent = zoom_percent
        self.tweet_fetcher = TweetFetcher()
        
        # Cropping parameters
        self.crop_enabled = crop_enabled
        self.crop_x1 = crop_x1
        self.crop_y1 = crop_y1
        self.crop_x2 = crop_x2
        self.crop_y2 = crop_y2
        
        # Validate crop parameters
        if self.crop_enabled:
            self._validate_crop_parameters()
        
        # Create date-based folder prefix for today's captures
        self.date_folder = datetime.now().strftime("%Y-%m-%d")
        
        # Initialize S3 client
        self.s3_client = boto3.client('s3')
        
        # Browser setup
        self.driver = None
        self.temp_dir = None
        
        logger.info(f"VisualTweetCaptureService initialized with bucket: {s3_bucket}, date folder: {self.date_folder}, zoom: {zoom_percent}%")
        if self.crop_enabled:
            logger.info(f"Cropping enabled: ({self.crop_x1}%, {self.crop_y1}%) to ({self.crop_x2}%, {self.crop_y2}%)")
    
    def _validate_crop_parameters(self):
        """Validate crop parameters are within valid ranges."""
        if not (0 <= self.crop_x1 < self.crop_x2 <= 100):
            raise ValueError(f"Invalid crop X coordinates: x1={self.crop_x1}, x2={self.crop_x2}. Must be 0 <= x1 < x2 <= 100")
        if not (0 <= self.crop_y1 < self.crop_y2 <= 100):
            raise ValueError(f"Invalid crop Y coordinates: y1={self.crop_y1}, y2={self.crop_y2}. Must be 0 <= y1 < y2 <= 100")
    
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
                
                logger.debug(f"Cropped image {image_path} to ({left},{top},{right},{bottom})")
                return crop_output_path
                
        except Exception as e:
            logger.warning(f"Error cropping image {image_path}: {e}")
            return image_path  # Return original path if cropping fails
    
    def capture_account_content(
        self, 
        account_name: str, 
        days_back: int = 7, 
        max_tweets: int = 25
    ) -> Dict[str, Any]:
        """
        Capture all visual content for a Twitter account and store in S3.
        
        Args:
            account_name: Twitter account name (without @)
            days_back: Number of days to look back
            max_tweets: Maximum number of tweets to retrieve
            
        Returns:
            Dictionary with capture results and S3 locations
        """
        logger.info(f"Starting capture for @{account_name} - {days_back} days, {max_tweets} max tweets")
        
        try:
            # Step 1: Get all content for the account
            grouped_content = self.tweet_fetcher.detect_and_group_threads(
                account_name, days_back, max_tweets
            )
            
            if not grouped_content:
                logger.warning(f"No content found for @{account_name}")
                return {
                    'success': False,
                    'message': f'No content found for @{account_name}',
                    'account': account_name,
                    'captured_items': []
                }
            
            # Step 2: Separate threads and individual tweets
            threads = [item for item in grouped_content if item.get('is_thread', False)]
            individual_tweets = [item for item in grouped_content if not item.get('is_thread', False)]
            
            logger.info(f"Found {len(threads)} threads and {len(individual_tweets)} individual tweets")
            
            # Step 3: Set up temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix=f"tweet_capture_{account_name}_")
            logger.info(f"Created temporary directory: {self.temp_dir}")
            
            captured_results = []
            
            # Step 4: Capture all threads
            for i, thread in enumerate(threads, 1):
                logger.info(f"Capturing thread {i}/{len(threads)}: {thread['conversation_id']}")
                try:
                    result = self._capture_thread(thread, account_name)
                    if result:
                        captured_results.append(result)
                        logger.info(f"✅ Thread {i} captured successfully")
                    else:
                        logger.error(f"❌ Thread {i} capture failed")
                except Exception as e:
                    logger.error(f"❌ Thread {i} capture error: {e}")
            
            # Step 5: Capture all individual tweets
            for i, tweet in enumerate(individual_tweets, 1):
                logger.info(f"Capturing individual tweet {i}/{len(individual_tweets)}: {tweet['id']}")
                try:
                    result = self._capture_individual_tweet(tweet, account_name)
                    if result:
                        captured_results.append(result)
                        logger.info(f"✅ Individual tweet {i} captured successfully")
                    else:
                        logger.error(f"❌ Individual tweet {i} capture failed")
                except Exception as e:
                    logger.error(f"❌ Individual tweet {i} capture error: {e}")
            
            # Step 6: Create summary report
            summary = self._create_capture_summary(account_name, captured_results, threads, individual_tweets)
            
            # Step 7: Upload summary to S3
            summary_s3_key = f"visual_captures/{self.date_folder}/{account_name.lower()}/capture_summary.json"
            self._upload_json_to_s3(summary, summary_s3_key)
            
            logger.info(f"✅ Capture complete for @{account_name}: {len(captured_results)} items captured")
            
            return {
                'success': True,
                'account': account_name,
                'total_items_captured': len(captured_results),
                'threads_captured': len([r for r in captured_results if r['type'] == 'thread']),
                'individual_tweets_captured': len([r for r in captured_results if r['type'] == 'individual_tweet']),
                'summary_s3_location': f"s3://{self.s3_bucket}/{summary_s3_key}",
                'captured_items': captured_results
            }
            
        except Exception as e:
            logger.error(f"❌ Error capturing content for @{account_name}: {e}")
            return {
                'success': False,
                'account': account_name,
                'error': str(e),
                'captured_items': []
            }
        finally:
            # Clean up temporary directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
    
    def _capture_thread(self, thread_data: Dict[str, Any], account_name: str) -> Optional[Dict[str, Any]]:
        """
        Capture a complete thread and upload to S3.
        
        Args:
            thread_data: Thread data from Twitter API
            account_name: Twitter account name
            
        Returns:
            Dictionary with capture results or None if failed
        """
        try:
            conversation_id = thread_data.get('conversation_id', thread_data['id'])
            thread_tweets = thread_data.get('thread_tweets', [])
            
            # Find the first tweet ID (chronologically earliest) - same as exploration
            if thread_tweets:
                # Sort by created_at to find the actual first tweet
                sorted_by_time = sorted(thread_tweets, key=lambda x: x['created_at'])
                first_tweet_id = sorted_by_time[0]['id']
            else:
                # Fallback to main thread ID
                first_tweet_id = thread_data['id']
            
            # Create S3 folder structure using first tweet ID (same as exploration)
            s3_folder_prefix = f"visual_captures/{self.date_folder}/{account_name.lower()}/convo_{first_tweet_id}/"
            
            # Get tweets ordered by ID (increasing order) for capture - same as exploration
            sorted_tweets = sorted(thread_tweets, key=lambda x: int(x['id']))
            
            captured_tweets = []
            
            # Capture each tweet in the thread
            for i, tweet in enumerate(sorted_tweets, 1):
                tweet_id = tweet['id']
                tweet_url = f"https://twitter.com/{account_name}/status/{tweet_id}"
                
                logger.info(f"  Capturing tweet {i}/{len(sorted_tweets)}: {tweet_id}")
                
                # Capture individual tweet
                tweet_capture_result = self._capture_tweet_screenshots(tweet_url, tweet_id)
                
                if tweet_capture_result:
                    # Upload screenshots to S3
                    s3_tweet_folder = f"{s3_folder_prefix}tweet_{tweet_id}/"
                    uploaded_files = self._upload_screenshots_to_s3(
                        tweet_capture_result['screenshots'], 
                        s3_tweet_folder
                    )
                    
                    # Add to captured tweets (same structure as exploration)
                    captured_tweets.append({
                        'tweet_id': tweet_id,
                        'tweet_url': tweet_url,
                        'tweet_metadata': tweet,
                        'id_order': i,  # Order by ID instead of chronological
                        'screenshot_count': len(uploaded_files),
                        's3_screenshots': uploaded_files,
                        's3_folder': f"s3://{self.s3_bucket}/{s3_tweet_folder}",
                        'capture_timestamp': tweet_capture_result['capture_timestamp']
                    })
            
            # Create thread metadata (same clean structure as exploration)
            clean_thread_data = thread_data.copy()
            clean_thread_data.pop('thread_tweets', None)
            
            thread_metadata = {
                'conversation_id': conversation_id,
                'capture_timestamp': datetime.now().isoformat(),
                'thread_summary': clean_thread_data,
                'total_tweets_in_thread': len(sorted_tweets),
                'successfully_captured': len(captured_tweets),
                'ordered_tweets': captured_tweets,
                's3_bucket': self.s3_bucket,
                's3_folder_prefix': s3_folder_prefix,
                'browser_zoom': f'{self.zoom_percent}_percent',
                'cropping': {
                    'enabled': self.crop_enabled,
                    'coordinates': {
                        'x1_percent': self.crop_x1,
                        'y1_percent': self.crop_y1,
                        'x2_percent': self.crop_x2,
                        'y2_percent': self.crop_y2
                    } if self.crop_enabled else None
                },
                'capture_strategy': 'individual_tweet_capture',
                'sort_order': 'by_tweet_id_increasing'
            }
            
            # Upload metadata to S3
            metadata_s3_key = f"{s3_folder_prefix}metadata.json"
            self._upload_json_to_s3(thread_metadata, metadata_s3_key)
            
            return {
                'type': 'thread',
                'conversation_id': conversation_id,
                'total_tweets': len(sorted_tweets),
                'captured_tweets': len(captured_tweets),
                's3_location': f"s3://{self.s3_bucket}/{s3_folder_prefix}",
                'metadata_s3_location': f"s3://{self.s3_bucket}/{metadata_s3_key}",
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error capturing thread {conversation_id}: {e}")
            return None
    
    def _capture_individual_tweet(self, tweet_data: Dict[str, Any], account_name: str) -> Optional[Dict[str, Any]]:
        """
        Capture an individual tweet and upload to S3.
        
        Args:
            tweet_data: Tweet data from Twitter API
            account_name: Twitter account name
            
        Returns:
            Dictionary with capture results or None if failed
        """
        try:
            tweet_id = tweet_data['id']
            tweet_url = tweet_data['url']
            
            # Detect content type
            content_type = self._detect_content_type(tweet_data)
            
            # Create S3 folder structure
            s3_folder_prefix = f"visual_captures/{self.date_folder}/{account_name.lower()}/{content_type}_{tweet_id}/"
            
            # Capture tweet screenshots
            capture_result = self._capture_tweet_screenshots(tweet_url, tweet_id)
            
            if not capture_result:
                return None
            
            # Upload screenshots to S3
            uploaded_files = self._upload_screenshots_to_s3(
                capture_result['screenshots'], 
                s3_folder_prefix
            )
            
            # Create metadata
            metadata = {
                'tweet_id': tweet_id,
                'tweet_url': tweet_url,
                'content_type': content_type,
                'capture_timestamp': capture_result['capture_timestamp'],
                'screenshot_count': len(uploaded_files),
                's3_screenshots': uploaded_files,
                's3_bucket': self.s3_bucket,
                's3_folder_prefix': s3_folder_prefix,
                'browser_zoom': f'{self.zoom_percent}_percent',
                'cropping': {
                    'enabled': self.crop_enabled,
                    'coordinates': {
                        'x1_percent': self.crop_x1,
                        'y1_percent': self.crop_y1,
                        'x2_percent': self.crop_x2,
                        'y2_percent': self.crop_y2
                    } if self.crop_enabled else None
                },
                'tweet_metadata': tweet_data
            }
            
            # Upload metadata to S3
            metadata_s3_key = f"{s3_folder_prefix}capture_metadata.json"
            self._upload_json_to_s3(metadata, metadata_s3_key)
            
            return {
                'type': 'individual_tweet',
                'content_type': content_type,
                'tweet_id': tweet_id,
                'screenshot_count': len(uploaded_files),
                's3_location': f"s3://{self.s3_bucket}/{s3_folder_prefix}",
                'metadata_s3_location': f"s3://{self.s3_bucket}/{metadata_s3_key}",
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error capturing individual tweet {tweet_data.get('id', 'unknown')}: {e}")
            return None
    
    def _capture_tweet_screenshots(self, tweet_url: str, tweet_id: str) -> Optional[Dict[str, Any]]:
        """
        Capture screenshots of a tweet using browser automation.
        
        Args:
            tweet_url: URL of the tweet to capture
            tweet_id: Tweet ID for file naming
            
        Returns:
            Dictionary with screenshot file paths or None if failed
        """
        try:
            # Set up browser
            if not self._setup_browser():
                return None
            
            # Navigate to tweet
            self.driver.get(tweet_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )
            
            # Wait for dynamic content
            time.sleep(3.0)
            
            # Capture screenshots with scrolling
            screenshots = self._capture_scrolling_screenshots(tweet_id)
            
            return {
                'tweet_id': tweet_id,
                'tweet_url': tweet_url,
                'screenshots': screenshots,
                'capture_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error capturing screenshots for {tweet_id}: {e}")
            return None
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def _capture_scrolling_screenshots(self, tweet_id: str) -> List[str]:
        """
        Capture multiple screenshots while scrolling through content.
        
        Args:
            tweet_id: Tweet ID for file naming
            
        Returns:
            List of screenshot file paths
        """
        screenshots = []
        screenshot_count = 0
        max_screenshots = 10  # Same as exploration for thread tweets
        consecutive_same_positions = 0
        
        # Get initial page info (same as exploration)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        viewport_height = self.driver.execute_script("return window.innerHeight")
        
        # Take initial screenshot at top of page (same filename format as exploration)
        screenshot_path = os.path.join(self.temp_dir, f"{tweet_id}_{timestamp}_page_{screenshot_count:02d}.png")
        self.driver.save_screenshot(screenshot_path)
        
        # Apply cropping if enabled
        cropped_path = self.crop_image(screenshot_path)
        screenshots.append(cropped_path)
        screenshot_count += 1
        
        last_scroll_position = self.driver.execute_script("return window.pageYOffset")
        
        # Scroll and capture remaining screenshots (same as exploration)
        while screenshot_count < max_screenshots:
            # Scroll down
            scroll_amount = int(viewport_height * 0.8)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount})")
            
            # Wait for content to load
            time.sleep(2.0)
            
            # Get current scroll position
            new_scroll_position = self.driver.execute_script("return window.pageYOffset")
            current_scroll_position = new_scroll_position
            
            # Check if we actually scrolled (same logic as exploration)
            if new_scroll_position <= last_scroll_position:
                consecutive_same_positions += 1
                if consecutive_same_positions >= 2:
                    logger.debug(f"Cannot scroll further for {tweet_id}")
                    break
            else:
                consecutive_same_positions = 0
                
                # Take screenshot if we made significant progress (same logic as exploration)
                scroll_progress = new_scroll_position - current_scroll_position
                if scroll_progress > (viewport_height * 0.3):  # Only if scrolled more than 30% of viewport
                    screenshot_path = os.path.join(self.temp_dir, f"{tweet_id}_{timestamp}_page_{screenshot_count:02d}.png")
                    self.driver.save_screenshot(screenshot_path)
                    
                    # Apply cropping if enabled
                    cropped_path = self.crop_image(screenshot_path)
                    screenshots.append(cropped_path)
                    screenshot_count += 1
                else:
                    logger.debug(f"Skipped screenshot for {tweet_id} - minimal scroll progress ({scroll_progress}px)")
            
            last_scroll_position = new_scroll_position
        
        logger.debug(f"Captured {len(screenshots)} screenshots for {tweet_id}")
        if self.crop_enabled:
            logger.debug(f"Applied cropping to all screenshots: ({self.crop_x1}%, {self.crop_y1}%) → ({self.crop_x2}%, {self.crop_y2}%)")
        return screenshots
    
    def _setup_browser(self) -> bool:
        """
        Set up Chrome browser with optimal settings.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")  # Standard size
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            
            # Set user agent to avoid detection (same as exploration)
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set page zoom level if different from 100%
            if self.zoom_percent != 100:
                zoom_level = self.zoom_percent / 100.0
                self.driver.execute_script(f"document.body.style.zoom='{zoom_level}'")
            
            return True
            
        except Exception as e:
            logger.error(f"Browser setup failed: {e}")
            return False
    
    def _upload_screenshots_to_s3(self, screenshot_paths: List[str], s3_folder: str) -> List[str]:
        """
        Upload screenshot files to S3.
        
        Args:
            screenshot_paths: List of local screenshot file paths
            s3_folder: S3 folder prefix to upload to
            
        Returns:
            List of S3 keys for uploaded files
        """
        uploaded_files = []
        
        for screenshot_path in screenshot_paths:
            try:
                filename = os.path.basename(screenshot_path)
                s3_key = f"{s3_folder}{filename}"
                
                # Upload to S3
                self.s3_client.upload_file(screenshot_path, self.s3_bucket, s3_key)
                uploaded_files.append(s3_key)
                logger.debug(f"Uploaded {filename} to s3://{self.s3_bucket}/{s3_key}")
                
            except Exception as e:
                logger.error(f"Failed to upload {screenshot_path}: {e}")
        
        return uploaded_files
    
    def _upload_json_to_s3(self, data: Dict[str, Any], s3_key: str) -> bool:
        """
        Upload JSON data to S3.
        
        Args:
            data: Dictionary to upload as JSON
            s3_key: S3 key for the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            json_data = json.dumps(data, indent=2, default=str)
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=json_data,
                ContentType='application/json'
            )
            logger.debug(f"Uploaded JSON to s3://{self.s3_bucket}/{s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload JSON to {s3_key}: {e}")
            return False
    
    def _detect_content_type(self, tweet_data: Dict[str, Any]) -> str:
        """
        Detect the type of tweet content.
        
        Args:
            tweet_data: Tweet data from API
            
        Returns:
            Content type string ("retweet", "tweet", or "convo")
        """
        text = tweet_data.get('text', '')
        if text.startswith('RT @'):
            return "retweet"
        
        is_thread = tweet_data.get('is_thread', False)
        if is_thread:
            return "convo"
        
        return "tweet"
    
    def _create_capture_summary(
        self, 
        account_name: str, 
        captured_results: List[Dict[str, Any]], 
        threads: List[Dict[str, Any]], 
        individual_tweets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create a comprehensive summary of the capture session.
        
        Args:
            account_name: Twitter account name
            captured_results: List of capture results
            threads: List of thread data
            individual_tweets: List of individual tweet data
            
        Returns:
            Summary dictionary
        """
        thread_results = [r for r in captured_results if r['type'] == 'thread']
        tweet_results = [r for r in captured_results if r['type'] == 'individual_tweet']
        
        return {
            'account': account_name,
            'capture_timestamp': datetime.now().isoformat(),
            'service_config': {
                'zoom_percent': self.zoom_percent,
                's3_bucket': self.s3_bucket
            },
            'summary': {
                'total_items_found': len(threads) + len(individual_tweets),
                'total_items_captured': len(captured_results),
                'threads_found': len(threads),
                'threads_captured': len(thread_results),
                'individual_tweets_found': len(individual_tweets),
                'individual_tweets_captured': len(tweet_results),
                'success_rate': len(captured_results) / (len(threads) + len(individual_tweets)) if (len(threads) + len(individual_tweets)) > 0 else 0
            },
            'captured_content': captured_results
        }

# Convenience function for easy usage
def capture_twitter_account_visuals(
    account_name: str,
    s3_bucket: str,
    days_back: int = 7,
    max_tweets: int = 25,
    zoom_percent: int = 60
) -> Dict[str, Any]:
    """
    Convenience function to capture visual content for a Twitter account.
    
    Args:
        account_name: Twitter account name (without @)
        s3_bucket: S3 bucket for storing captured images
        days_back: Number of days to look back (default: 7)
        max_tweets: Maximum number of tweets to retrieve (default: 25)
        zoom_percent: Browser zoom percentage (default: 60%)
        
    Returns:
        Dictionary with capture results
    """
    service = VisualTweetCaptureService(s3_bucket, zoom_percent)
    return service.capture_account_content(account_name, days_back, max_tweets) 