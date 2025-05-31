#!/usr/bin/env python3
"""
Quick and minimal tweet fetching test script.
Use this for rapid experimentation with tweet_services.py
"""

import sys
import os

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add lambdas to path (from exploration folder)
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambdas'))

from shared.tweet_services import TweetFetcher

def quick_test():
    """Quick test to fetch a few tweets."""
    # Initialize fetcher
    fetcher = TweetFetcher()
    
    # Fetch tweets from a single account
    username = "AndrewYNg"  # Change this to test different accounts
    tweets = fetcher.fetch_tweets([username], days_back=7, max_tweets_per_user=5)
    
    print(f"Found {len(tweets)} tweets from @{username}:")
    
    for i, tweet in enumerate(tweets, 1):
        print(f"\n{'='*80}")
        print(f"Tweet #{i}")
        
        # Show thread info if applicable
        if tweet.get('is_thread', False):
            print(f"🧵 THREAD ({tweet.get('thread_tweet_count', 1)} tweets)")
        
        print(f"📅 {tweet['created_at']}")
        print(f"👍 {tweet['public_metrics'].get('like_count', 0)} likes | "
              f"🔄 {tweet['public_metrics'].get('retweet_count', 0)} retweets | "
              f"💬 {tweet['public_metrics'].get('reply_count', 0)} replies")
        
        print(f"\n📝 Content:")
        print(f"{tweet['text']}")
        
        if 'conversation_id' in tweet and tweet['conversation_id']:
            print(f"\n🔗 Conversation ID: {tweet['conversation_id']}")
    
    print(f"\n{'='*80}")

if __name__ == "__main__":
    if not os.getenv('TWITTER_BEARER_TOKEN'):
        print("❌ Please set your TWITTER_BEARER_TOKEN environment variable")
        print("   Create a .env file in this directory with your API credentials")
        print("   Copy from env_template.txt and fill in your actual tokens")
        print("   Example content:")
        print("   TWITTER_BEARER_TOKEN=your_actual_token_here")
    else:
        quick_test() 