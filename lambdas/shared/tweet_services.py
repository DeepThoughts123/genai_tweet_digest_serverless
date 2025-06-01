"""
Simplified tweet processing services for Lambda functions.
Minimal version focused on supporting visual tweet capture.
"""

import tweepy
import google.generativeai as genai
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from tweepy.errors import TweepyException
import logging
from .config import config

class TweetFetcher:
    """Basic tweet fetcher for visual capture support."""
    
    def __init__(self):
        # v2 API client for basic functionality
        self.client_v2 = tweepy.Client(bearer_token=config.twitter_bearer_token)
    
    def fetch_tweet_by_url(self, tweet_url: str) -> Optional[Dict[str, Any]]:
        """
        Extract tweet ID and fetch basic tweet data for visual capture.
        
        Args:
            tweet_url: Twitter/X URL (e.g., https://twitter.com/user/status/123)
            
        Returns:
            Dictionary with basic tweet data for visual capture metadata
        """
        # Extract tweet ID from URL
        tweet_id = self._extract_tweet_id_from_url(tweet_url)
        if not tweet_id:
            print(f"❌ Could not extract tweet ID from URL: {tweet_url}")
            return None
        
        print(f"🔍 Fetching basic tweet data for ID: {tweet_id}")
        return self.fetch_tweet_by_id(tweet_id)
    
    def fetch_tweet_by_id(self, tweet_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch basic tweet data by ID.
        
        Args:
            tweet_id: Twitter tweet ID
            
        Returns:
            Dictionary with basic tweet data
        """
        try:
            tweet_response = self.client_v2.get_tweet(
                id=tweet_id,
                tweet_fields=['created_at', 'public_metrics', 'author_id', 'text', 'conversation_id'],
                expansions=['author_id'],
                user_fields=['username', 'name']
            )
            
            if tweet_response.data:
                tweet = tweet_response.data
                
                # Get author information
                author_username = "unknown"
                author_name = "Unknown"
                if hasattr(tweet_response, 'includes') and tweet_response.includes:
                    if hasattr(tweet_response.includes, 'users') and tweet_response.includes.users:
                        users = tweet_response.includes.users
                        if users and len(users) > 0:
                            author_username = users[0].username
                            author_name = users[0].name
                
                return {
                    'id': tweet_id,
                    'url': f"https://twitter.com/{author_username}/status/{tweet_id}",
                    'text': tweet.text,
                    'author': {
                        'id': str(tweet.author_id),
                        'username': author_username,
                        'name': author_name
                    },
                    'created_at': tweet.created_at.isoformat() if tweet.created_at else None,
                    'conversation_id': str(tweet.conversation_id) if hasattr(tweet, 'conversation_id') else tweet_id,
                    'metrics': {
                        'likes': tweet.public_metrics.get('like_count', 0),
                        'retweets': tweet.public_metrics.get('retweet_count', 0),
                        'replies': tweet.public_metrics.get('reply_count', 0),
                        'quotes': tweet.public_metrics.get('quote_count', 0),
                        'bookmarks': tweet.public_metrics.get('bookmark_count', 0),
                        'impressions': tweet.public_metrics.get('impression_count', 0),
                    }
                }
            else:
                print(f"❌ Tweet {tweet_id} not found")
                return None
                
        except Exception as e:
            print(f"❌ Error fetching tweet {tweet_id}: {e}")
            return None
    
    def _extract_tweet_id_from_url(self, url: str) -> Optional[str]:
        """Extract tweet ID from various Twitter URL formats."""
        # Common Twitter URL patterns
        patterns = [
            r'twitter\.com/\w+/status/(\d+)',  # https://twitter.com/user/status/123
            r'x\.com/\w+/status/(\d+)',       # https://x.com/user/status/123
            r'/status/(\d+)',                 # /status/123
            r'(\d{19})',                      # Raw tweet ID (19 digits)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None

    def fetch_recent_tweets(self, username: str, days_back: int = 7, max_tweets: int = 10) -> List[str]:
        """
        Fetch recent tweet URLs from a user account for visual capture.
        
        Args:
            username: Twitter username (without @)
            days_back: How many days back to search
            max_tweets: Maximum number of tweets to return
            
        Returns:
            List of tweet URLs for visual capture
        """
        tweet_urls = []
        
        try:
            # Get user ID
            user = self.client_v2.get_user(username=username)
            if not user.data:
                print(f"❌ User not found: {username}")
                return []
            
            user_id = user.data.id
            print(f"✅ Found user @{username} (ID: {user_id})")
            
            # Calculate date range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days_back)
            
            # Format for Twitter API (RFC3339)
            formatted_start_time = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            formatted_end_time = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            print(f"🔍 Searching for tweets from {formatted_start_time} to {formatted_end_time}")
            
            # Fetch recent tweets
            tweets = self.client_v2.get_users_tweets(
                id=user_id,
                max_results=max_tweets,
                start_time=formatted_start_time,
                end_time=formatted_end_time,
                tweet_fields=['created_at', 'public_metrics'],
                exclude=['replies']  # Include retweets but exclude replies
            )
            
            if tweets.data:
                print(f"📝 Found {len(tweets.data)} tweets")
                for tweet in tweets.data:
                    tweet_url = f"https://twitter.com/{username}/status/{tweet.id}"
                    tweet_urls.append(tweet_url)
                    print(f"   • {tweet_url} ({tweet.created_at.strftime('%Y-%m-%d')})")
            else:
                print(f"📭 No tweets found for @{username} in the last {days_back} days")
                
        except Exception as e:
            print(f"❌ Error fetching tweets for @{username}: {e}")
        
        return tweet_urls

    def fetch_thread_by_tweet_id(self, tweet_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch complete thread for a given tweet ID.
        
        Args:
            tweet_id: Twitter tweet ID (can be any tweet in the thread)
            
        Returns:
            Dictionary with complete thread data or None if failed
        """
        # First get the base tweet to get conversation_id and author
        base_tweet = self.fetch_tweet_by_id(tweet_id)
        if not base_tweet:
            print(f"❌ Could not fetch base tweet {tweet_id}")
            return None
        
        conversation_id = base_tweet['conversation_id']
        author_username = base_tweet['author']['username']
        author_id = base_tweet['author']['id']
        
        print(f"🧵 Fetching complete thread for conversation {conversation_id}")
        
        try:
            # Search for all tweets in this conversation by this author
            search_query = f"conversation_id:{conversation_id} from:{author_username}"
            
            thread_response = self.client_v2.search_recent_tweets(
                query=search_query,
                max_results=100,  # Max tweets in a thread
                tweet_fields=['created_at', 'public_metrics', 'author_id', 'text', 'conversation_id'],
                expansions=['author_id'],
                user_fields=['username', 'name']
            )
            
            if not thread_response.data:
                print(f"📝 Single tweet thread (no additional tweets found)")
                return base_tweet
            
            # Process all tweets in thread
            thread_tweets = []
            
            for tweet in thread_response.data:
                if str(tweet.author_id) == author_id:  # Only tweets by same author
                    tweet_data = {
                        'id': str(tweet.id),
                        'text': tweet.text,
                        'created_at': tweet.created_at.isoformat() if tweet.created_at else None,
                        'metrics': {
                            'likes': tweet.public_metrics.get('like_count', 0),
                            'retweets': tweet.public_metrics.get('retweet_count', 0),
                            'replies': tweet.public_metrics.get('reply_count', 0),
                            'quotes': tweet.public_metrics.get('quote_count', 0),
                            'bookmarks': tweet.public_metrics.get('bookmark_count', 0),
                            'impressions': tweet.public_metrics.get('impression_count', 0),
                        }
                    }
                    thread_tweets.append(tweet_data)
            
            # Sort tweets by creation time (chronological order)
            thread_tweets.sort(key=lambda x: x['created_at'])
            
            # Create thread summary
            total_likes = sum(t['metrics']['likes'] for t in thread_tweets)
            total_retweets = sum(t['metrics']['retweets'] for t in thread_tweets)
            total_replies = sum(t['metrics']['replies'] for t in thread_tweets)
            total_quotes = sum(t['metrics']['quotes'] for t in thread_tweets)
            total_bookmarks = sum(t['metrics']['bookmarks'] for t in thread_tweets)
            total_impressions = sum(t['metrics']['impressions'] for t in thread_tweets)
            
            # Combine thread text with numbering
            combined_text_parts = []
            for i, tweet in enumerate(thread_tweets, 1):
                combined_text_parts.append(f"[{i}/{len(thread_tweets)}] {tweet['text']}")
            
            combined_text = "\n\n".join(combined_text_parts)
            
            # Find the main tweet (earliest or most engaged)
            main_tweet = thread_tweets[0]  # Use first chronologically
            
            print(f"✅ Found complete thread: {len(thread_tweets)} tweets")
            
            return {
                'id': main_tweet['id'],
                'url': f"https://twitter.com/{author_username}/status/{main_tweet['id']}",
                'text': combined_text,
                'author': base_tweet['author'],
                'created_at': main_tweet['created_at'],
                'conversation_id': conversation_id,
                'is_thread': True,
                'thread_tweet_count': len(thread_tweets),
                'thread_tweets': thread_tweets,
                'metrics': {
                    'likes': total_likes,
                    'retweets': total_retweets,
                    'replies': total_replies,
                    'quotes': total_quotes,
                    'bookmarks': total_bookmarks,
                    'impressions': total_impressions,
                }
            }
            
        except Exception as e:
            print(f"❌ Error fetching thread: {e}")
            return base_tweet  # Fall back to single tweet

    def detect_and_group_threads(self, username: str, days_back: int = 7, max_tweets: int = 25) -> List[Dict[str, Any]]:
        """
        Fetch recent tweets and group them by threads.
        
        Args:
            username: Twitter username (without @)
            days_back: How many days back to search
            max_tweets: Maximum number of tweets to return (should be high enough for complete threads)
            
        Returns:
            List of tweet data (individual tweets or complete threads)
            
        Note: max_tweets limits total tweets from user's timeline. If a user has a 12-tweet 
        thread but max_tweets=5, you'll only get 5 tweets total, truncating the thread.
        """
        print(f"🧵 DETECTING THREADS for @{username}")
        
        # First get all recent tweets with conversation_id
        try:
            # Get user ID
            user = self.client_v2.get_user(username=username)
            if not user.data:
                print(f"❌ User not found: {username}")
                return []
            
            user_id = user.data.id
            print(f"✅ Found user @{username} (ID: {user_id})")
            
            # Calculate date range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days_back)
            
            # Format for Twitter API (RFC3339)
            formatted_start_time = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            formatted_end_time = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            print(f"🔍 Searching for tweets from {formatted_start_time} to {formatted_end_time}")
            
            # Fetch recent tweets with conversation_id
            tweets = self.client_v2.get_users_tweets(
                id=user_id,
                max_results=max_tweets,
                start_time=formatted_start_time,
                end_time=formatted_end_time,
                tweet_fields=['created_at', 'public_metrics', 'conversation_id', 'text'],
                exclude=['replies']  # Include retweets but exclude replies
            )
            
            if not tweets.data:
                print(f"📭 No tweets found for @{username} in the last {days_back} days")
                return []
            
            # Group tweets by conversation_id
            conversation_groups = {}
            for tweet in tweets.data:
                conv_id = str(tweet.conversation_id) if hasattr(tweet, 'conversation_id') else str(tweet.id)
                if conv_id not in conversation_groups:
                    conversation_groups[conv_id] = []
                conversation_groups[conv_id].append(tweet)
            
            # Process each conversation group
            grouped_results = []
            
            for conv_id, conv_tweets in conversation_groups.items():
                if len(conv_tweets) == 1:
                    # Single tweet - not a thread
                    tweet = conv_tweets[0]
                    tweet_data = {
                        'id': str(tweet.id),
                        'url': f"https://twitter.com/{username}/status/{tweet.id}",
                        'text': tweet.text,
                        'author': {
                            'id': str(user_id),
                            'username': username,
                            'name': username
                        },
                        'created_at': tweet.created_at.isoformat() if tweet.created_at else None,
                        'conversation_id': conv_id,
                        'is_thread': False,
                        'metrics': {
                            'likes': tweet.public_metrics.get('like_count', 0),
                            'retweets': tweet.public_metrics.get('retweet_count', 0),
                            'replies': tweet.public_metrics.get('reply_count', 0),
                            'quotes': tweet.public_metrics.get('quote_count', 0),
                            'bookmarks': tweet.public_metrics.get('bookmark_count', 0),
                            'impressions': tweet.public_metrics.get('impression_count', 0),
                        }
                    }
                    grouped_results.append(tweet_data)
                else:
                    # Multi-tweet conversation - likely a thread
                    print(f"🧵 Found thread with {len(conv_tweets)} tweets in conversation {conv_id}")
                    
                    # Sort tweets chronologically
                    conv_tweets.sort(key=lambda x: x.created_at)
                    
                    # Process tweets (convert API objects to dicts)
                    thread_tweets = []
                    total_likes = total_retweets = total_replies = 0
                    total_quotes = total_bookmarks = total_impressions = 0
                    
                    for tweet in conv_tweets:
                        # Convert API object to dict
                        tweet_data = {
                            'id': str(tweet.id),
                            'text': tweet.text,
                            'created_at': tweet.created_at.isoformat() if tweet.created_at else None,
                            'metrics': {
                                'likes': tweet.public_metrics.get('like_count', 0),
                                'retweets': tweet.public_metrics.get('retweet_count', 0),
                                'replies': tweet.public_metrics.get('reply_count', 0),
                                'quotes': tweet.public_metrics.get('quote_count', 0),
                                'bookmarks': tweet.public_metrics.get('bookmark_count', 0),
                                'impressions': tweet.public_metrics.get('impression_count', 0),
                            }
                        }
                        thread_tweets.append(tweet_data)
                        
                        # Sum metrics
                        total_likes += tweet_data['metrics']['likes']
                        total_retweets += tweet_data['metrics']['retweets']
                        total_replies += tweet_data['metrics']['replies']
                        total_quotes += tweet_data['metrics']['quotes']
                        total_bookmarks += tweet_data['metrics']['bookmarks']
                        total_impressions += tweet_data['metrics']['impressions']
                    
                    # Combine thread text with numbering
                    combined_text_parts = []
                    for i, tweet_data in enumerate(thread_tweets, 1):
                        combined_text_parts.append(f"[{i}/{len(thread_tweets)}] {tweet_data['text']}")
                    
                    combined_text = "\n\n".join(combined_text_parts)
                    
                    # Use first tweet as main reference
                    main_tweet = thread_tweets[0]
                    
                    thread_result = {
                        'id': main_tweet['id'],
                        'url': f"https://twitter.com/{username}/status/{main_tweet['id']}",
                        'text': combined_text,
                        'author': {
                            'id': str(user_id),
                            'username': username,
                            'name': username
                        },
                        'created_at': main_tweet['created_at'],
                        'conversation_id': conv_id,
                        'is_thread': True,
                        'thread_tweet_count': len(thread_tweets),
                        'thread_tweets': thread_tweets,
                        'metrics': {
                            'likes': total_likes,
                            'retweets': total_retweets,
                            'replies': total_replies,
                            'quotes': total_quotes,
                            'bookmarks': total_bookmarks,
                            'impressions': total_impressions,
                        }
                    }
                    grouped_results.append(thread_result)
            
            # Sort by creation time (newest first)
            grouped_results.sort(key=lambda x: x['created_at'], reverse=True)
            
            print(f"📊 Grouped into {len(grouped_results)} items:")
            for item in grouped_results:
                if item['is_thread']:
                    print(f"   🧵 Thread: {item['thread_tweet_count']} tweets, {item['metrics']['likes']} total likes")
                else:
                    print(f"   📝 Single tweet: {item['metrics']['likes']} likes")
            
            return grouped_results
            
        except Exception as e:
            print(f"❌ Error detecting threads for @{username}: {e}")
            return []

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