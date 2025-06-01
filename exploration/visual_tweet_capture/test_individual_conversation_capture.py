#!/usr/bin/env python3
"""
Test Individual Tweet Conversation Capture

Tests the new strategy where each tweet in a conversation is captured individually
at 60% browser size, with each tweet saved in its own subfolder.
"""

import sys
import os
from dotenv import load_dotenv
load_dotenv()

# Add lambdas to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'lambdas'))

from shared.tweet_services import TweetFetcher
from visual_tweet_capturer import VisualTweetCapturer

def test_individual_conversation_capture(account_name: str = 'minchoi', days_back: int = 7, max_tweets: int = 25):
    """Test capturing ALL content (threads + individual tweets) for an account.
    
    Note: max_tweets should be high enough to capture complete threads.
    If an account has a 12-tweet thread but max_tweets=5, you'll only get 5 tweets total.
    """
    
    print("🧵 TESTING COMPREHENSIVE TWEET CAPTURE")
    print("=" * 70)
    print(f"📅 Lookback period: {days_back} days")
    print(f"📊 Max tweets to retrieve: {max_tweets}")
    
    # Step 1: Get all content for the account
    fetcher = TweetFetcher()
    grouped_content = fetcher.detect_and_group_threads(account_name, days_back, max_tweets)
    
    if not grouped_content:
        print(f"❌ No content found for @{account_name}")
        return False
    
    # Separate threads and individual tweets
    threads = [item for item in grouped_content if item.get('is_thread', False)]
    individual_tweets = [item for item in grouped_content if not item.get('is_thread', False)]
    
    print(f"📊 Found content for @{account_name}:")
    print(f"   🧵 Threads: {len(threads)}")
    print(f"   📝 Individual tweets: {len(individual_tweets)}")
    
    if not threads and not individual_tweets:
        print(f"❌ No suitable content found for @{account_name}")
        return False
    
    # Initialize capture results
    capturer = VisualTweetCapturer(headless=True)
    captured_results = []
    
    # Step 2: Capture ALL threads
    if threads:
        print(f"\n🧵 CAPTURING {len(threads)} THREAD(S):")
        for i, thread in enumerate(threads, 1):
            print(f"\n   Thread {i}/{len(threads)}:")
            print(f"   📊 {thread['thread_tweet_count']} tweets")
            print(f"   💬 Conversation ID: {thread['conversation_id']}")
            print(f"   👍 Total likes: {thread.get('metrics', {}).get('likes', 0)}")
            print(f"   📄 Text: \"{thread.get('text', '')[:100]}...\"")
            
            try:
                result = capturer.capture_thread_visually(thread)
                if result:
                    captured_results.append({
                        'type': 'thread',
                        'result': result,
                        'content': thread
                    })
                    print(f"   ✅ Thread captured: {result['successfully_captured']}/{result['total_tweets_in_thread']} tweets")
                else:
                    print(f"   ❌ Thread capture failed")
            except Exception as e:
                print(f"   ❌ Thread capture error: {e}")
    
    # Step 3: Capture ALL individual tweets
    if individual_tweets:
        print(f"\n📝 CAPTURING {len(individual_tweets)} INDIVIDUAL TWEET(S):")
        for i, tweet in enumerate(individual_tweets, 1):
            print(f"\n   Tweet {i}/{len(individual_tweets)}:")
            print(f"   💬 Tweet ID: {tweet['id']}")
            print(f"   👍 Likes: {tweet.get('metrics', {}).get('likes', 0)}")
            print(f"   📄 Text: \"{tweet.get('text', '')[:100]}...\"")
            
            try:
                # Create a custom capturer for individual tweets to pass account name
                result = capture_individual_tweet_with_account(capturer, tweet['url'], account_name)
                if result:
                    captured_results.append({
                        'type': 'individual_tweet',
                        'result': result,
                        'content': tweet
                    })
                    print(f"   ✅ Tweet captured: {result['screenshots']['count']} screenshots")
                else:
                    print(f"   ❌ Tweet capture failed")
            except Exception as e:
                print(f"   ❌ Tweet capture error: {e}")
    
    # Step 4: Summary of all captures
    if captured_results:
        print(f"\n" + "=" * 70)
        print(f"🎉 COMPREHENSIVE CAPTURE SUCCESS FOR @{account_name.upper()}!")
        print("=" * 70)
        
        thread_results = [r for r in captured_results if r['type'] == 'thread']
        tweet_results = [r for r in captured_results if r['type'] == 'individual_tweet']
        
        print(f"\n📊 COMPLETE CAPTURE SUMMARY:")
        print(f"   🧵 Threads captured: {len(thread_results)}")
        print(f"   📝 Individual tweets captured: {len(tweet_results)}")
        print(f"   📁 Total output folders: {len(captured_results)}")
        
        # Detail thread captures
        if thread_results:
            print(f"\n🧵 THREAD CAPTURE DETAILS:")
            total_thread_tweets = 0
            for i, item in enumerate(thread_results, 1):
                result = item['result']
                thread = item['content']
                tweets_captured = result['successfully_captured']
                total_tweets = result['total_tweets_in_thread']
                total_thread_tweets += tweets_captured
                
                print(f"   {i}. Conversation {thread['conversation_id']}")
                print(f"      📊 {tweets_captured}/{total_tweets} tweets captured")
                print(f"      📁 Folder: {result['output_directory'].replace('visual_captures/', '')}")
                print(f"      👍 Thread likes: {thread.get('metrics', {}).get('likes', 0)}")
            
            print(f"   📊 Total individual tweet screenshots: {total_thread_tweets}")
        
        # Detail individual tweet captures
        if tweet_results:
            print(f"\n📝 INDIVIDUAL TWEET CAPTURE DETAILS:")
            total_screenshots = 0
            for i, item in enumerate(tweet_results, 1):
                result = item['result']
                tweet = item['content']
                screenshot_count = result['screenshots']['count']
                total_screenshots += screenshot_count
                
                print(f"   {i}. Tweet {tweet['id']}")
                print(f"      📸 {screenshot_count} screenshots")
                print(f"      📁 Folder: {result['output_directory'].replace('visual_captures/', '')}")
                print(f"      👍 Likes: {tweet.get('metrics', {}).get('likes', 0)}")
            
            print(f"   📸 Total individual screenshots: {total_screenshots}")
        
        # Show all output folders
        print(f"\n📁 ALL OUTPUT FOLDERS:")
        for item in captured_results:
            folder_name = item['result']['output_directory'].replace('visual_captures/', '')
            content_type = "🧵 Thread" if item['type'] == 'thread' else "📝 Tweet"
            print(f"   {content_type}: {folder_name}")
        
        return True
    else:
        print(f"\n❌ No content was successfully captured for @{account_name}")
        return False

def capture_individual_tweet_with_account(capturer, tweet_url, account_name):
    """
    Capture individual tweet with known account name.
    """
    # Reset screenshots list for this capture to prevent accumulation from previous captures
    capturer.screenshots = []
    
    print(f"📸 VISUAL TWEET CAPTURER")
    print(f"🔗 URL: {tweet_url}")
    
    # Step 1: Get API data for metadata
    print(f"\n1️⃣ Fetching API metadata...")
    api_data = capturer.api_fetcher.fetch_tweet_by_url(tweet_url)
    
    if not api_data:
        print("⚠️ Could not fetch API metadata, proceeding with visual capture only")
        api_data = {'id': 'unknown', 'author': {'username': account_name}, 'conversation_id': 'unknown'}
    else:
        # Ensure we have the correct account name
        if 'author' not in api_data:
            api_data['author'] = {}
        api_data['author']['username'] = account_name
    
    # Step 1.5: Set up conversation-specific folder
    conversation_id = api_data.get('conversation_id', api_data['id'])
    main_tweet_id = api_data['id']
    tweet_type = capturer._detect_tweet_type(api_data)
    capturer.setup_conversation_folder(conversation_id, main_tweet_id, tweet_type, account_name)
    
    # Step 2: Set up browser
    print(f"\n2️⃣ Setting up browser...")
    if not capturer.setup_browser():
        return None
    
    try:
        # Step 3: Navigate to tweet
        print(f"\n3️⃣ Loading tweet page...")
        capturer.driver.get(tweet_url)
        
        # Wait for page to load
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import TimeoutException
        
        WebDriverWait(capturer.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "article"))
        )
        print("✅ Page loaded successfully")
        
        # Step 4: Capture screenshots while scrolling
        print(f"\n4️⃣ Capturing visual content...")
        capturer.capture_scrolling_screenshots(tweet_url)
        
        # Step 5: Process and combine screenshots
        print(f"\n5️⃣ Processing captured images...")
        result = capturer.process_screenshots(api_data, tweet_url)
        
        return result
        
    except TimeoutException:
        print("❌ Page load timeout")
        return None
    except Exception as e:
        print(f"❌ Capture error: {e}")
        return None
    finally:
        if capturer.driver:
            capturer.driver.quit()
            print("🔧 Browser closed")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test individual tweet conversation capture')
    parser.add_argument('--account', '-a', default='minchoi', 
                       help='Twitter account name to test (without @)')
    parser.add_argument('--days', '-d', type=int, default=7,
                       help='Number of days to look back (default: 7)')
    parser.add_argument('--max-tweets', '-m', type=int, default=25,
                       help='Maximum number of tweets to retrieve (default: 25)')
    args = parser.parse_args()
    
    print(f"🎯 Testing with account: @{args.account}")
    print(f"📅 Lookback: {args.days} days, Max tweets: {args.max_tweets}")
    success = test_individual_conversation_capture(
        account_name=args.account, 
        days_back=args.days, 
        max_tweets=args.max_tweets
    )
    
    if success:
        print(f"\n🎯 COMPREHENSIVE CAPTURE STRATEGY BENEFITS:")
        print(f"   ✅ Captures ALL threads and individual tweets for account")
        print(f"   ✅ Each tweet captured individually at 60% page zoom")
        print(f"   ✅ Intelligent duplicate screenshot detection")
        print(f"   ✅ Organized subfolders for each tweet/conversation")
        print(f"   ✅ Tweets ordered by ID (increasing order)")
        print(f"   ✅ Complete scrolling capture per tweet")
        print(f"   ✅ Comprehensive content coverage within lookback window")
        print(f"   ✅ Better file organization and navigation")
        print("=" * 70)
    else:
        print(f"\n❌ Please ensure dependencies are installed:")
        print(f"   pip install selenium pillow")
        print(f"   brew install --cask google-chrome") 