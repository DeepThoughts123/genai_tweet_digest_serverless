#!/usr/bin/env python3
"""
Comprehensive tweet fetching experiments for the GenAI Tweets Digest project.
This script uses the same configuration and services as the Lambda functions.

Place this in the exploration/ folder to keep experimental code organized.
"""

import sys
import os
import json
from datetime import datetime

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add the lambdas directory to the path (from exploration folder, go up one level then into lambdas)
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambdas'))

from shared.tweet_services import TweetFetcher, TweetCategorizer, TweetSummarizer

def test_single_account_tweets():
    """Test fetching tweets from a single account."""
    print("🐦 Testing single account tweet fetching...")
    
    fetcher = TweetFetcher()
    
    # Example: Fetch tweets from a specific account
    username = "AndrewYNg"  # Change this to the account you want to test
    tweets = fetcher.fetch_tweets([username], days_back=3, max_tweets_per_user=5)
    
    print(f"✅ Fetched {len(tweets)} tweets from @{username}")
    
    for i, tweet in enumerate(tweets, 1):
        print(f"\n--- Tweet {i} ---")
        print(f"ID: {tweet['id']}")
        print(f"Text: {tweet['text'][:100]}{'...' if len(tweet['text']) > 100 else ''}")
        print(f"Created: {tweet['created_at']}")
        print(f"Metrics: {tweet['public_metrics']}")

def test_multiple_accounts():
    """Test fetching tweets from multiple accounts."""
    print("\n🐦 Testing multiple accounts tweet fetching...")
    
    fetcher = TweetFetcher()
    
    # Test with multiple accounts
    usernames = ["AndrewYNg", "OpenAI", "karpathy"]  # Customize this list
    tweets = fetcher.fetch_tweets(usernames, days_back=2, max_tweets_per_user=3)
    
    print(f"✅ Fetched {len(tweets)} total tweets from {len(usernames)} accounts")
    
    # Group by username
    tweets_by_user = {}
    for tweet in tweets:
        username = tweet['username']
        if username not in tweets_by_user:
            tweets_by_user[username] = []
        tweets_by_user[username].append(tweet)
    
    for username, user_tweets in tweets_by_user.items():
        print(f"\n@{username}: {len(user_tweets)} tweets")
        for tweet in user_tweets[:2]:  # Show first 2 tweets
            print(f"  - {tweet['text'][:80]}{'...' if len(tweet['text']) > 80 else ''}")

def test_tweet_categorization():
    """Test AI categorization on fetched tweets."""
    print("\n🤖 Testing tweet categorization...")
    
    # First fetch some tweets
    fetcher = TweetFetcher()
    tweets = fetcher.fetch_tweets(["OpenAI"], days_back=1, max_tweets_per_user=3)
    
    if not tweets:
        print("❌ No tweets fetched for categorization test")
        return
    
    # Then categorize them
    categorizer = TweetCategorizer()
    categorized_tweets = categorizer.categorize_tweets(tweets)
    
    print(f"✅ Categorized {len(categorized_tweets)} tweets")
    
    for tweet in categorized_tweets:
        print(f"\n--- Categorized Tweet ---")
        print(f"Text: {tweet['text'][:100]}{'...' if len(tweet['text']) > 100 else ''}")
        print(f"Category: {tweet['category']}")
        print(f"Confidence: {tweet['confidence']}")

def test_full_pipeline():
    """Test the complete tweet processing pipeline."""
    print("\n🔄 Testing full pipeline (fetch → categorize → summarize)...")
    
    # Step 1: Fetch tweets
    fetcher = TweetFetcher()
    usernames = ["OpenAI", "AndrewYNg"]
    tweets = fetcher.fetch_tweets(usernames, days_back=2, max_tweets_per_user=2)
    
    if not tweets:
        print("❌ No tweets fetched for pipeline test")
        return
    
    print(f"📥 Step 1: Fetched {len(tweets)} tweets")
    
    # Step 2: Categorize tweets
    categorizer = TweetCategorizer()
    categorized_tweets = categorizer.categorize_tweets(tweets)
    print(f"🏷️  Step 2: Categorized {len(categorized_tweets)} tweets")
    
    # Step 3: Summarize by category
    summarizer = TweetSummarizer()
    summary_result = summarizer.summarize_tweets(categorized_tweets)
    
    print(f"📝 Step 3: Generated summaries for {len(summary_result['summaries'])} categories")
    
    # Display results
    print("\n--- PIPELINE RESULTS ---")
    for category, data in summary_result['summaries'].items():
        print(f"\n📊 {category} ({data['tweet_count']} tweets):")
        print(f"   Summary: {data['summary']}")

def test_time_range_analysis():
    """Test different time ranges to see tweet volume patterns."""
    print("\n📅 Testing time range analysis...")
    
    fetcher = TweetFetcher()
    username = "OpenAI"  # Change to test different accounts
    
    time_ranges = [1, 3, 7, 14]  # days
    
    for days in time_ranges:
        tweets = fetcher.fetch_tweets([username], days_back=days, max_tweets_per_user=50)
        print(f"📊 Last {days} day(s): {len(tweets)} tweets from @{username}")
        
        if tweets:
            # Calculate engagement stats
            total_likes = sum(t['public_metrics'].get('like_count', 0) for t in tweets)
            total_retweets = sum(t['public_metrics'].get('retweet_count', 0) for t in tweets)
            avg_likes = total_likes / len(tweets) if tweets else 0
            
            print(f"   💖 Total likes: {total_likes:,} (avg: {avg_likes:.1f})")
            print(f"   🔄 Total retweets: {total_retweets:,}")

def test_custom_account():
    """Test fetching from a custom account of your choice."""
    print("\n🎯 Testing custom account...")
    
    # Customize this section for your specific testing needs
    custom_username = input("Enter a Twitter username to test (without @): ").strip()
    
    if not custom_username:
        print("No username provided, skipping custom test")
        return
    
    fetcher = TweetFetcher()
    
    try:
        tweets = fetcher.fetch_tweets([custom_username], days_back=7, max_tweets_per_user=10)
        
        if tweets:
            print(f"✅ Successfully fetched {len(tweets)} tweets from @{custom_username}")
            
            # Show some stats
            total_likes = sum(tweet['public_metrics'].get('like_count', 0) for tweet in tweets)
            print(f"📊 Total likes across all tweets: {total_likes:,}")
            
            # Show most popular tweet
            most_liked = max(tweets, key=lambda t: t['public_metrics'].get('like_count', 0))
            print(f"\n🔥 Most liked tweet ({most_liked['public_metrics'].get('like_count', 0):,} likes):")
            print(f"   {most_liked['text'][:150]}{'...' if len(most_liked['text']) > 150 else ''}")
            
            # Show recent tweets
            print(f"\n🕒 Most recent tweets:")
            sorted_tweets = sorted(tweets, key=lambda t: t['created_at'], reverse=True)
            for tweet in sorted_tweets[:3]:
                print(f"   • {tweet['text'][:100]}{'...' if len(tweet['text']) > 100 else ''}")
            
        else:
            print(f"❌ No tweets found for @{custom_username}")
            
    except Exception as e:
        print(f"❌ Error fetching tweets from @{custom_username}: {e}")

def save_exploration_results(data, filename):
    """Save exploration results to a JSON file."""
    exploration_dir = os.path.dirname(__file__)
    filepath = os.path.join(exploration_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, indent=2, default=str, fp=f)
    
    print(f"💾 Results saved to: {filepath}")

def main():
    """Main function to run various tweet fetching experiments."""
    print("=" * 70)
    print("🚀 GenAI Tweets Digest - Tweet Fetching Exploration Lab")
    print("=" * 70)
    
    # Check if environment is properly configured
    if not os.getenv('TWITTER_BEARER_TOKEN'):
        print("❌ Please set your TWITTER_BEARER_TOKEN environment variable")
        print("   Create a .env file in this directory with your API credentials")
        print("   Copy from env_template.txt and fill in your actual tokens")
        print("   Or export TWITTER_BEARER_TOKEN='your_actual_token'")
        return
    
    try:
        # Run different test scenarios
        test_single_account_tweets()
        test_multiple_accounts()
        
        # Only test AI features if Gemini API key is available
        if os.getenv('GEMINI_API_KEY'):
            test_tweet_categorization()
            test_full_pipeline()
        else:
            print("\n🤖 Skipping AI tests (no Gemini API key)")
            print("   Add GEMINI_API_KEY to your .env file to test categorization and summarization")
        
        test_time_range_analysis()
        test_custom_account()
        
        print("\n" + "=" * 70)
        print("🎉 Exploration completed!")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error during exploration: {e}")
        print("Make sure your API credentials are properly configured in .env file")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 