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
        """Fetch recent tweets from specified usernames with complete text including threads."""
        all_tweets = []
        
        # Calculate date range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days_back)
        
        # Format for Twitter API (RFC3339)
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
                
                # Fetch tweets with expanded fields for thread detection
                tweets = self.client.get_users_tweets(
                    id=user_id,
                    max_results=max_tweets_per_user,
                    start_time=formatted_start_time,
                    end_time=formatted_end_time,
                    tweet_fields=['created_at', 'public_metrics', 'author_id', 'context_annotations', 
                                'entities', 'referenced_tweets', 'conversation_id', 'in_reply_to_user_id'],
                    expansions=['referenced_tweets.id', 'in_reply_to_user_id']
                )
                
                if tweets.data:
                    # Create lookup for referenced tweets (for retweets)
                    referenced_tweets_lookup = {}
                    if hasattr(tweets, 'includes') and tweets.includes and hasattr(tweets.includes, 'get') and tweets.includes.get('tweets'):
                        for ref_tweet in tweets.includes['tweets']:
                            referenced_tweets_lookup[ref_tweet.id] = ref_tweet.text
                    
                    # Group tweets by conversation to handle threads
                    conversations = {}
                    standalone_tweets = []
                    
                    for tweet in tweets.data:
                        if hasattr(tweet, 'conversation_id') and tweet.conversation_id:
                            conv_id = tweet.conversation_id
                            if conv_id not in conversations:
                                conversations[conv_id] = []
                            conversations[conv_id].append(tweet)
                        else:
                            standalone_tweets.append(tweet)
                    
                    # Process standalone tweets
                    for tweet in standalone_tweets:
                        full_text = self._get_full_tweet_text(tweet, referenced_tweets_lookup)
                        tweet_data = self._create_tweet_data(tweet, full_text, username)
                        all_tweets.append(tweet_data)
                    
                    # Process conversations (threads)
                    for conv_id, conv_tweets in conversations.items():
                        thread_text = self._get_complete_thread_text(conv_tweets, conv_id, user_id, referenced_tweets_lookup)
                        
                        # Use the first tweet in the thread as the main tweet
                        main_tweet = min(conv_tweets, key=lambda t: t.created_at)
                        tweet_data = self._create_tweet_data(main_tweet, thread_text, username)
                        
                        # Only mark as thread if we actually found multiple tweets from this user
                        is_actual_thread = "\n\n[2/" in thread_text  # Check if we have multiple parts
                        if is_actual_thread:
                            tweet_data['is_thread'] = True
                            # Count the number of thread parts
                            thread_count = thread_text.count('[') if '[' in thread_text else 1
                            tweet_data['thread_tweet_count'] = thread_count
                        
                        all_tweets.append(tweet_data)
                        
            except Exception as e:
                print(f"Error fetching tweets for {username}: {e}")
                continue
        
        return all_tweets
    
    def _get_full_tweet_text(self, tweet, referenced_tweets_lookup):
        """Get the full text of a tweet, handling retweets."""
        full_text = tweet.text
        
        # If this is a retweet, try to get the full original text
        if hasattr(tweet, 'referenced_tweets') and tweet.referenced_tweets:
            for ref_tweet in tweet.referenced_tweets:
                if ref_tweet.type == 'retweeted' and ref_tweet.id in referenced_tweets_lookup:
                    original_text = referenced_tweets_lookup[ref_tweet.id]
                    rt_match = re.match(r'RT @(\w+):', tweet.text)
                    if rt_match:
                        retweeted_user = rt_match.group(1)
                        full_text = f"RT @{retweeted_user}: {original_text}"
        
        return full_text
    
    def _get_complete_thread_text(self, conv_tweets, conv_id, user_id, referenced_tweets_lookup):
        """Get complete thread text by fetching all tweets in the conversation."""
        try:
            # Get the main tweet to check for potential follow-ups
            main_tweet = min(conv_tweets, key=lambda t: t.created_at)
            main_tweet_id = main_tweet.id
            
            # First, try to get the complete conversation using conversation_id
            try:
                # Search for all tweets in this conversation from this specific user only
                search_query = f"conversation_id:{conv_id} from:{user_id}"
                additional_tweets = self.client.search_recent_tweets(
                    query=search_query,
                    max_results=100,
                    tweet_fields=['created_at', 'public_metrics', 'author_id', 'conversation_id', 'in_reply_to_user_id'],
                    expansions=['author_id']
                )
                
                # Combine with existing tweets, remove duplicates
                all_conv_tweets = list(conv_tweets)
                existing_ids = {tweet.id for tweet in conv_tweets}
                
                if additional_tweets.data:
                    for add_tweet in additional_tweets.data:
                        if add_tweet.id not in existing_ids and str(add_tweet.author_id) == str(user_id):
                            all_conv_tweets.append(add_tweet)
                
                conv_tweets = all_conv_tweets
                print(f"Found {len(conv_tweets)} tweets from user {user_id} in conversation {conv_id}")
                
            except Exception as e:
                print(f"Search failed for conversation {conv_id}: {e}")
                # If search fails, just use the original tweets
                pass
            
            # Sort tweets by creation time to get proper thread order
            sorted_tweets = sorted(conv_tweets, key=lambda t: t.created_at)
            
            # Only include tweets from our target user
            user_tweets_in_thread = [t for t in sorted_tweets if str(t.author_id) == str(user_id)]
            
            if len(user_tweets_in_thread) > 1:
                # This is a multi-tweet thread from our user
                thread_parts = []
                for i, tweet in enumerate(user_tweets_in_thread):
                    tweet_text = self._get_full_tweet_text(tweet, referenced_tweets_lookup)
                    
                    # Skip if this is a retweet and we already have original content
                    if i > 0 and tweet_text.startswith('RT @') and any(not t.startswith('RT @') for t in thread_parts):
                        continue
                        
                    thread_parts.append(f"[{i+1}/{len(user_tweets_in_thread)}] {tweet_text}")
                
                if len(thread_parts) > 1:
                    print(f"Reconstructed thread with {len(thread_parts)} parts for user {user_id}")
                    return "\n\n".join(thread_parts)
                else:
                    # Only one meaningful tweet after filtering
                    return self._get_full_tweet_text(user_tweets_in_thread[0], referenced_tweets_lookup)
            else:
                # Single tweet, just return its full text
                tweet = user_tweets_in_thread[0] if user_tweets_in_thread else sorted_tweets[0]
                return self._get_full_tweet_text(tweet, referenced_tweets_lookup)
            
        except Exception as e:
            print(f"Error getting complete thread for conversation {conv_id}: {e}")
            # Fallback: just return the text of the first tweet
            if conv_tweets:
                first_tweet = min(conv_tweets, key=lambda t: t.created_at)
                return self._get_full_tweet_text(first_tweet, referenced_tweets_lookup)
            return "Error retrieving thread content"
    
    def _create_tweet_data(self, tweet, full_text, username):
        """Create standardized tweet data dictionary."""
        return {
            'id': tweet.id,
            'text': full_text,
            'author_id': tweet.author_id,
            'username': username,
            'created_at': tweet.created_at.isoformat(),
            'public_metrics': tweet.public_metrics,
            'conversation_id': getattr(tweet, 'conversation_id', None)
        }

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