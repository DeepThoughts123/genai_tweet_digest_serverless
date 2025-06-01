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

def test_individual_conversation_capture():
    """Test the new individual tweet conversation capture strategy."""
    
    print("🧵 TESTING INDIVIDUAL TWEET CONVERSATION CAPTURE")
    print("=" * 70)
    
    # Step 1: Get thread data using the improved thread detection
    fetcher = TweetFetcher()
    grouped_content = fetcher.detect_and_group_threads('minchoi', 7, 10)
    
    # Find the thread we're interested in
    threads = [item for item in grouped_content if item.get('is_thread', False)]
    
    if not threads:
        print("❌ No threads found for @minchoi")
        return False
    
    # Use the first thread (which should be the one we've been working with)
    thread = threads[0]
    
    print(f"🧵 Found thread with {thread['thread_tweet_count']} tweets")
    print(f"💬 Conversation ID: {thread['conversation_id']}")
    print(f"📅 Created: {thread['created_at']}")
    
    # Step 2: Test the new individual capture strategy
    print(f"\n📸 Starting individual tweet capture...")
    capturer = VisualTweetCapturer(headless=True)
    result = capturer.capture_thread_visually(thread)
    
    if result:
        print(f"\n" + "=" * 70)
        print(f"🎉 INDIVIDUAL CONVERSATION CAPTURE SUCCESS!")
        print("=" * 70)
        
        print(f"\n📊 CAPTURE SUMMARY:")
        print(f"   📁 Conversation folder: {result['output_directory']}")
        print(f"   🧵 Total tweets in thread: {result['total_tweets_in_thread']}")
        print(f"   ✅ Successfully captured: {result['successfully_captured']}")
        print(f"   📂 Subfolders created: {result['successfully_captured']}")
        print(f"   🖼️ Browser zoom: {result['browser_zoom']}")
        print(f"   📋 Capture strategy: {result['capture_strategy']}")
        print(f"   📊 Sort order: {result['sort_order']}")
        
        print(f"\n📂 FOLDER STRUCTURE:")
        base_folder = os.path.basename(result['output_directory'])
        print(f"   📁 {base_folder}/")
        print(f"       📄 metadata.json")
        
        for tweet_capture in result['ordered_tweets']:
            subfolder = tweet_capture['subfolder']
            screenshot_count = tweet_capture['screenshot_count']
            tweet_text = tweet_capture['tweet_metadata']['text'][:50]
            print(f"       📁 {subfolder}/")
            print(f"           📸 {screenshot_count} screenshots (page_00.png to page_{screenshot_count-1:02d}.png)")
            print(f"           💬 \"{tweet_text}...\"")
        
        print(f"\n📊 TWEET ID ORDER (INCREASING):")
        for i, tweet_capture in enumerate(result['ordered_tweets'], 1):
            tweet_id = tweet_capture['tweet_id']
            created_at = tweet_capture['tweet_metadata']['created_at']
            likes = tweet_capture['tweet_metadata']['metrics']['likes']
            print(f"   {i:2d}. Tweet {tweet_id} ({created_at}) - {likes} likes")
        
        return True
    else:
        print(f"\n❌ Individual conversation capture failed")
        return False

if __name__ == "__main__":
    success = test_individual_conversation_capture()
    
    if success:
        print(f"\n🎯 NEW STRATEGY BENEFITS:")
        print(f"   ✅ Each tweet captured individually at optimal size")
        print(f"   ✅ 60% page zoom for better content visibility")
        print(f"   ✅ Intelligent duplicate screenshot detection")
        print(f"   ✅ Organized subfolders for each tweet")
        print(f"   ✅ Tweets ordered by ID (increasing order)")
        print(f"   ✅ Complete scrolling capture per tweet")
        print(f"   ✅ Better file organization and navigation")
        print("=" * 70)
    else:
        print(f"\n❌ Please ensure dependencies are installed:")
        print(f"   pip install selenium pillow")
        print(f"   brew install --cask google-chrome") 