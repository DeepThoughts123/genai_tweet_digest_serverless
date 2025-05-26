"""
Simplified tweet processing services for Lambda functions.
Adapted from the original backend services with Lambda-specific optimizations.
"""

import tweepy
import google.generativeai as genai
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from tweepy.auth import OAuthHandler
from tweepy.errors import TweepyException
import logging
from .config import config

class TweetFetcher:
    """Simplified tweet fetcher for Lambda."""
    
    def __init__(self):
        self.client = tweepy.Client(bearer_token=config.twitter_bearer_token)
    
    def fetch_tweets(self, usernames: List[str], days_back: int = 7, max_tweets_per_user: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent tweets from specified usernames."""
        all_tweets = []
        
        # Calculate date range
        end_time = datetime.utcnow() # Ensure UTC
        start_time = end_time - timedelta(days=days_back)
        
        # Format for Twitter API (RFC3339)
        # YYYY-MM-DDTHH:MM:SSZ
        formatted_start_time = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        formatted_end_time = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

        for username in usernames:
            try:
                # Get user ID
                user = self.client.get_user(username=username)
                if not user.data:
                    print(f"User not found: {username}")
                    continue
                
                user_id = user.data.id
                
                # Fetch tweets
                tweets = self.client.get_users_tweets(
                    id=user_id,
                    max_results=max_tweets_per_user,
                    start_time=formatted_start_time,
                    end_time=formatted_end_time,
                    tweet_fields=['created_at', 'public_metrics', 'author_id']
                )
                
                if tweets.data:
                    for tweet in tweets.data:
                        tweet_data = {
                            'id': tweet.id,
                            'text': tweet.text,
                            'author_id': tweet.author_id,
                            'username': username,
                            'created_at': tweet.created_at.isoformat(),
                            'public_metrics': tweet.public_metrics
                        }
                        all_tweets.append(tweet_data)
                        
            except Exception as e:
                print(f"Error fetching tweets for {username}: {e}")
                continue
        
        return all_tweets

class TweetCategorizer:
    """Simplified tweet categorizer for Lambda."""
    
    def __init__(self):
        genai.configure(api_key=config.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        self.categories = [
            "New AI model releases",
            "Breakthrough research findings", 
            "Applications and case studies",
            "Ethical discussions and regulations",
            "Tools and resources"
        ]
    
    def categorize_tweets(self, tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Categorize tweets using Gemini."""
        categorized_tweets = []
        
        for tweet in tweets:
            try:
                category, confidence = self._categorize_single_tweet(tweet['text'])
                
                tweet_with_category = tweet.copy()
                tweet_with_category.update({
                    'category': category,
                    'confidence': confidence
                })
                categorized_tweets.append(tweet_with_category)
                
            except Exception as e:
                print(f"Error categorizing tweet {tweet['id']}: {e}")
                # Add with default category
                tweet_with_category = tweet.copy()
                tweet_with_category.update({
                    'category': 'Tools and resources',
                    'confidence': 0.5
                })
                categorized_tweets.append(tweet_with_category)
        
        return categorized_tweets
    
    def _categorize_single_tweet(self, text: str) -> tuple[str, float]:
        """Categorize a single tweet."""
        prompt = f"""
        Categorize this tweet about Generative AI into one of these categories:
        1. New AI model releases
        2. Breakthrough research findings
        3. Applications and case studies
        4. Ethical discussions and regulations
        5. Tools and resources

        Tweet: "{text}"

        Respond with only the category name and confidence (0-1) in this format:
        Category: [category name]
        Confidence: [0.XX]
        """
        
        response = self.model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Parse response
        category_match = re.search(r'Category:\s*(.+)', response_text)
        confidence_match = re.search(r'Confidence:\s*([\d.]+)', response_text)
        
        category = category_match.group(1).strip() if category_match else "Tools and resources"
        confidence = float(confidence_match.group(1)) if confidence_match else 0.5
        
        # Validate category
        if category not in self.categories:
            category = "Tools and resources"
            confidence = 0.5
        
        return category, confidence

class TweetSummarizer:
    """Simplified tweet summarizer for Lambda."""
    
    def __init__(self):
        genai.configure(api_key=config.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    def summarize_tweets(self, categorized_tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summaries by category."""
        from collections import defaultdict
        
        # Group tweets by category
        tweets_by_category = defaultdict(list)
        for tweet in categorized_tweets:
            tweets_by_category[tweet['category']].append(tweet)
        
        summaries = {}
        
        for category, tweets in tweets_by_category.items():
            if not tweets:
                continue
                
            try:
                summary = self._generate_category_summary(category, tweets)
                summaries[category] = {
                    'summary': summary,
                    'tweet_count': len(tweets),
                    'tweets': tweets
                }
            except Exception as e:
                print(f"Error summarizing category {category}: {e}")
                summaries[category] = {
                    'summary': f"Recent developments in {category.lower()}.",
                    'tweet_count': len(tweets),
                    'tweets': tweets
                }
        
        return {
            'summaries': summaries,
            'total_tweets': len(categorized_tweets),
            'generated_at': datetime.now().isoformat()
        }
    
    def _generate_category_summary(self, category: str, tweets: List[Dict[str, Any]]) -> str:
        """Generate summary for a specific category."""
        tweet_texts = [tweet['text'] for tweet in tweets]
        
        prompt = f"""
        Create a professional 2-4 sentence summary for the "{category}" category based on these tweets:

        {chr(10).join([f"- {text}" for text in tweet_texts[:10]])}

        The summary should:
        - Be informative and engaging
        - Highlight key developments or trends
        - Be suitable for a professional newsletter
        - Avoid repetition and focus on the most important points
        """
        
        response = self.model.generate_content(prompt)
        return response.text.strip()

class S3DataManager:
    """Manage tweet data storage in S3."""
    
    def __init__(self):
        self.s3_client = config.s3_client
        self.bucket = config.s3_bucket
    
    def save_tweets(self, tweets: List[Dict[str, Any]], digest_data: Dict[str, Any]) -> str:
        """Save tweets and digest data to S3."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Save raw tweets
        tweets_key = f"{config.tweets_prefix}raw/{timestamp}_tweets.json"
        self._save_json_to_s3(tweets_key, tweets)
        
        # Save digest data
        digest_key = f"{config.tweets_prefix}digests/{timestamp}_digest.json"
        self._save_json_to_s3(digest_key, digest_data)
        
        return digest_key
    
    def _save_json_to_s3(self, key: str, data: Any) -> None:
        """Save JSON data to S3."""
        json_data = json.dumps(data, indent=2, default=str)
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json_data,
            ContentType='application/json'
        ) 