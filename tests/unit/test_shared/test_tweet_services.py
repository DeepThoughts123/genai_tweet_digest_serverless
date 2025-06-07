"""
Unit tests for tweet processing services.
Tests the core business logic without external dependencies.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime, timedelta
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.shared.tweet_services import TweetFetcher, TweetCategorizer, TweetSummarizer, S3DataManager

class TestTweetFetcher(unittest.TestCase):
    """Test the TweetFetcher class."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('src.shared.tweet_services.config') as mock_config:
            mock_config.twitter_bearer_token = "test_token"
            self.fetcher = TweetFetcher()
    
    @patch('src.shared.tweet_services.tweepy.Client')
    def test_fetch_tweets_success(self, mock_client_class):
        """Test successful tweet fetching."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_user = Mock()
        mock_user.data.id = "123456789"
        mock_client.get_user.return_value = mock_user
        
        # Create a more complete mock tweet with all required attributes
        mock_tweet = Mock()
        mock_tweet.id = "tweet123"
        mock_tweet.text = "Test tweet about AI"
        mock_tweet.author_id = "123456789"
        mock_tweet.created_at = datetime.now()
        mock_tweet.public_metrics = {"like_count": 10, "retweet_count": 5, "reply_count": 2, "quote_count": 1, "bookmark_count": 3, "impression_count": 100}
        
        # Add attributes expected by our enhanced fetching logic
        mock_tweet.conversation_id = "conv123"
        
        mock_tweets_response = Mock()
        mock_tweets_response.data = [mock_tweet]
        mock_client.get_users_tweets.return_value = mock_tweets_response
        
        with patch('src.shared.tweet_services.config') as mock_config:
            mock_config.twitter_bearer_token = "test_token"
            fetcher = TweetFetcher()
            tweets = fetcher.fetch_tweets(["testuser"])
        
        self.assertEqual(len(tweets), 1)
        self.assertEqual(tweets[0]['id'], "tweet123")
        self.assertEqual(tweets[0]['text'], "Test tweet about AI")
        self.assertEqual(tweets[0]['author']['username'], "testuser")
        self.assertEqual(tweets[0]['conversation_id'], "conv123")
    
    @patch('src.shared.tweet_services.tweepy.Client')
    def test_fetch_tweets_user_not_found(self, mock_client_class):
        """Test handling of user not found."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_user_response = Mock()
        mock_user_response.data = None
        mock_client.get_user.return_value = mock_user_response
        
        with patch('src.shared.tweet_services.config') as mock_config:
            mock_config.twitter_bearer_token = "test_token"
            fetcher = TweetFetcher()
            tweets = fetcher.fetch_tweets(["nonexistentuser"])
        self.assertEqual(len(tweets), 0)
    
    @patch('src.shared.tweet_services.tweepy.Client')
    def test_fetch_tweets_api_error(self, mock_client_class):
        """Test handling of API errors."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_user.side_effect = Exception("API Error")
        
        with patch('src.shared.tweet_services.config') as mock_config:
            mock_config.twitter_bearer_token = "test_token"
            fetcher = TweetFetcher()
            tweets = fetcher.fetch_tweets(["testuser"])
        self.assertEqual(len(tweets), 0)
    
    @patch('src.shared.tweet_services.tweepy.Client')
    def test_fetch_tweets_thread_detection(self, mock_client_class):
        """Test thread detection and reconstruction."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_user = Mock()
        mock_user.data.id = "123456789"
        mock_client.get_user.return_value = mock_user
        
        # Create first tweet in thread
        mock_tweet1 = Mock()
        mock_tweet1.id = "tweet1"
        mock_tweet1.text = "This is the first tweet in a thread"
        mock_tweet1.author_id = "123456789"
        mock_tweet1.created_at = datetime.now()
        mock_tweet1.public_metrics = {"like_count": 5, "retweet_count": 2, "reply_count": 1, "quote_count": 0, "bookmark_count": 1, "impression_count": 50}
        mock_tweet1.conversation_id = "conv123"
        
        # Create second tweet in thread
        mock_tweet2 = Mock()
        mock_tweet2.id = "tweet2"
        mock_tweet2.text = "This is the second tweet in the same thread"
        mock_tweet2.author_id = "123456789"
        mock_tweet2.created_at = datetime.now() + timedelta(minutes=1)
        mock_tweet2.public_metrics = {"like_count": 3, "retweet_count": 1, "reply_count": 0, "quote_count": 0, "bookmark_count": 0, "impression_count": 30}
        mock_tweet2.conversation_id = "conv123"
        
        mock_tweets_response = Mock()
        mock_tweets_response.data = [mock_tweet1, mock_tweet2]  # Return both tweets as a thread
        mock_client.get_users_tweets.return_value = mock_tweets_response
        
        with patch('src.shared.tweet_services.config') as mock_config:
            mock_config.twitter_bearer_token = "test_token"
            fetcher = TweetFetcher()
            tweets = fetcher.fetch_tweets(["testuser"])
        
        # Should get one result representing the thread
        self.assertEqual(len(tweets), 1)
        thread_tweet = tweets[0]
        
        # Check that it's marked as a thread
        self.assertTrue(thread_tweet.get('is_thread', False))
        self.assertEqual(thread_tweet.get('thread_tweet_count', 1), 2)
        
        # Check that the text contains both tweets
        self.assertIn("first tweet", thread_tweet['text'])
        self.assertIn("second tweet", thread_tweet['text'])
        self.assertIn("[1/2]", thread_tweet['text'])
        self.assertIn("[2/2]", thread_tweet['text'])
    
    @patch('src.shared.tweet_services.tweepy.Client')
    def test_fetch_tweet_by_id_success(self, mock_client_class):
        """Test successful tweet fetching by ID."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Create mock tweet
        mock_tweet = Mock()
        mock_tweet.id = "tweet123"
        mock_tweet.text = "Test tweet content"
        mock_tweet.author_id = "123456789"
        mock_tweet.created_at = datetime.now()
        mock_tweet.public_metrics = {"like_count": 10, "retweet_count": 5, "reply_count": 2, "quote_count": 1, "bookmark_count": 3, "impression_count": 100}
        mock_tweet.conversation_id = "conv123"
        
        # Create mock user  
        mock_user = Mock()
        mock_user.username = "testuser"
        mock_user.name = "Test User"
        
        # Create mock response
        mock_response = Mock()
        mock_response.data = mock_tweet
        mock_response.includes = Mock()
        mock_response.includes.users = [mock_user]
        
        mock_client.get_tweet.return_value = mock_response
        
        with patch('src.shared.tweet_services.config') as mock_config:
            mock_config.twitter_bearer_token = "test_token"
            fetcher = TweetFetcher()
            result = fetcher.fetch_tweet_by_id("tweet123")
        
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], "tweet123")
        self.assertEqual(result['text'], "Test tweet content")
        self.assertEqual(result['author']['username'], "testuser")
        self.assertEqual(result['author']['name'], "Test User")
        self.assertEqual(result['metrics']['likes'], 10)

    @patch('src.shared.tweet_services.tweepy.Client')
    def test_fetch_tweets_multiple_users(self, mock_client_class):
        """Test fetching tweets from multiple users."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock responses for two different users
        def mock_get_user_side_effect(username):
            if username == "user1":
                mock_user = Mock()
                mock_user.data.id = "111111111"
                return mock_user
            elif username == "user2":
                mock_user = Mock()
                mock_user.data.id = "222222222"
                return mock_user
            else:
                mock_user = Mock()
                mock_user.data = None
                return mock_user
        
        mock_client.get_user.side_effect = mock_get_user_side_effect
        
        def mock_get_users_tweets_side_effect(id, **kwargs):
            if id == "111111111":
                # User1 tweet
                mock_tweet1 = Mock()
                mock_tweet1.id = "tweet1"
                mock_tweet1.text = "Tweet from user1"
                mock_tweet1.created_at = datetime.now()
                mock_tweet1.public_metrics = {"like_count": 15, "retweet_count": 3, "reply_count": 1, "quote_count": 0, "bookmark_count": 2, "impression_count": 75}
                mock_tweet1.conversation_id = "conv1"
                
                mock_response = Mock()
                mock_response.data = [mock_tweet1]
                return mock_response
            elif id == "222222222":
                # User2 tweet
                mock_tweet2 = Mock()
                mock_tweet2.id = "tweet2"
                mock_tweet2.text = "Tweet from user2"
                mock_tweet2.created_at = datetime.now()
                mock_tweet2.public_metrics = {"like_count": 25, "retweet_count": 8, "reply_count": 3, "quote_count": 1, "bookmark_count": 5, "impression_count": 120}
                mock_tweet2.conversation_id = "conv2"
                
                mock_response = Mock()
                mock_response.data = [mock_tweet2]
                return mock_response
            else:
                mock_response = Mock()
                mock_response.data = None
                return mock_response
        
        mock_client.get_users_tweets.side_effect = mock_get_users_tweets_side_effect
        
        with patch('src.shared.tweet_services.config') as mock_config:
            mock_config.twitter_bearer_token = "test_token"
            fetcher = TweetFetcher()
            tweets = fetcher.fetch_tweets(["user1", "user2"])
        
        # Should get 2 tweets total, sorted by engagement
        self.assertEqual(len(tweets), 2)
        
        # Check tweets are sorted by engagement (user2 should be first due to higher engagement)
        self.assertEqual(tweets[0]['author']['username'], "user2")
        self.assertEqual(tweets[1]['author']['username'], "user1")
        
        # Check content
        self.assertEqual(tweets[0]['text'], "Tweet from user2")
        self.assertEqual(tweets[1]['text'], "Tweet from user1")

class TestTweetCategorizer(unittest.TestCase):
    """Test the TweetCategorizer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('src.shared.tweet_services.config') as mock_config:
            mock_config.gemini_api_key = "test_key"
            with patch('src.shared.tweet_services.genai.configure'):
                with patch('src.shared.tweet_services.genai.GenerativeModel'):
                    self.categorizer = TweetCategorizer()
    
    @patch('src.shared.tweet_services.genai.GenerativeModel')
    @patch('src.shared.tweet_services.genai.configure')
    def test_categorize_tweets_success(self, mock_configure, mock_model_class):
        """Test successful tweet categorization."""
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Category: New AI model releases\nConfidence: 0.95"
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        tweets = [{'id': 'tweet1', 'text': 'OpenAI just released GPT-5!', 'username': 'testuser'}]
        with patch('src.shared.tweet_services.config') as mock_config:
            mock_config.gemini_api_key = "test_key"
            categorizer = TweetCategorizer()
            categorized = categorizer.categorize_tweets(tweets)
        self.assertEqual(len(categorized), 1)
        self.assertEqual(categorized[0]['category'], 'New AI model releases')
        self.assertEqual(categorized[0]['confidence'], 0.95)
    
    @patch('src.shared.tweet_services.genai.GenerativeModel')
    @patch('src.shared.tweet_services.genai.configure')
    def test_categorize_tweets_invalid_response(self, mock_configure, mock_model_class):
        """Test handling of invalid Gemini response."""
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Invalid response format"
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        tweets = [{'id': 'tweet1', 'text': 'Test tweet'}]
        with patch('src.shared.tweet_services.config') as mock_config:
            mock_config.gemini_api_key = "test_key"
            categorizer = TweetCategorizer()
            categorized = categorizer.categorize_tweets(tweets)
        self.assertEqual(categorized[0]['category'], 'Tools and resources')
        self.assertEqual(categorized[0]['confidence'], 0.5)
    
    @patch('src.shared.tweet_services.genai.GenerativeModel')
    @patch('src.shared.tweet_services.genai.configure')
    def test_categorize_tweets_api_error(self, mock_configure, mock_model_class):
        """Test handling of Gemini API errors."""
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("API Error")
        mock_model_class.return_value = mock_model
        tweets = [{'id': 'tweet1', 'text': 'Test tweet'}]
        with patch('src.shared.tweet_services.config') as mock_config:
            mock_config.gemini_api_key = "test_key"
            categorizer = TweetCategorizer()
            categorized = categorizer.categorize_tweets(tweets)
        self.assertEqual(categorized[0]['category'], 'Tools and resources')
        self.assertEqual(categorized[0]['confidence'], 0.5)

class TestTweetSummarizer(unittest.TestCase):
    """Test the TweetSummarizer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('src.shared.tweet_services.config') as mock_config:
            mock_config.gemini_api_key = "test_key"
            with patch('src.shared.tweet_services.genai.configure'):
                with patch('src.shared.tweet_services.genai.GenerativeModel'):
                    self.summarizer = TweetSummarizer()
    
    @patch('src.shared.tweet_services.genai.GenerativeModel')
    @patch('src.shared.tweet_services.genai.configure')
    def test_summarize_tweets_success(self, mock_configure, mock_model_class):
        """Test successful tweet summarization."""
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "OpenAI has released a groundbreaking new model that shows significant improvements in reasoning capabilities."
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        categorized_tweets = [
            {'id': 'tweet1', 'text': 'OpenAI just released GPT-5!', 'category': 'New AI model releases', 'confidence': 0.95},
            {'id': 'tweet2', 'text': 'GPT-5 shows amazing reasoning!', 'category': 'New AI model releases', 'confidence': 0.90}
        ]
        with patch('src.shared.tweet_services.config') as mock_config:
            mock_config.gemini_api_key = "test_key"
            summarizer = TweetSummarizer()
            result = summarizer.summarize_tweets(categorized_tweets)
        self.assertIn('summaries', result)
        self.assertIn('total_tweets', result)
        self.assertIn('generated_at', result)
        self.assertEqual(result['total_tweets'], 2)
        self.assertIn('New AI model releases', result['summaries'])
        self.assertEqual(result['summaries']['New AI model releases']['tweet_count'], 2)
    
    @patch('src.shared.tweet_services.genai.GenerativeModel')
    @patch('src.shared.tweet_services.genai.configure')
    def test_summarize_tweets_empty_input(self, mock_configure, mock_model_class):
        """Test handling of empty tweet list."""
        with patch('src.shared.tweet_services.config') as mock_config:
            mock_config.gemini_api_key = "test_key"
            summarizer = TweetSummarizer()
            result = summarizer.summarize_tweets([])
        self.assertEqual(result['total_tweets'], 0)
        self.assertEqual(len(result['summaries']), 0)
    
    @patch('src.shared.tweet_services.genai.GenerativeModel')
    @patch('src.shared.tweet_services.genai.configure')
    def test_summarize_tweets_api_error(self, mock_configure, mock_model_class):
        """Test handling of Gemini API errors."""
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("API Error")
        mock_model_class.return_value = mock_model
        categorized_tweets = [{'id': 'tweet1', 'text': 'Test tweet', 'category': 'New AI model releases', 'confidence': 0.95}]
        with patch('src.shared.tweet_services.config') as mock_config:
            mock_config.gemini_api_key = "test_key"
            summarizer = TweetSummarizer()
            result = summarizer.summarize_tweets(categorized_tweets)
        self.assertIn('New AI model releases', result['summaries'])
        summary_text = result['summaries']['New AI model releases']['summary']
        self.assertIn('recent developments in new ai model releases.', summary_text.lower())

class TestS3DataManager(unittest.TestCase):
    """Test the S3DataManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.s3_config_patcher = patch('src.shared.tweet_services.config') 
        self.mock_s3_config = self.s3_config_patcher.start()
        
        self.mock_s3_client_for_manager = Mock() # Specific mock for S3 client
        self.mock_s3_config.s3_client = self.mock_s3_client_for_manager
        self.mock_s3_config.s3_bucket = "test-bucket"
        self.mock_s3_config.tweets_prefix = "tweets/"
        
        self.manager = S3DataManager() # Instantiated with patched config

    def tearDown(self):
        self.s3_config_patcher.stop()
    
    def test_save_tweets_success(self):
        """Test successful tweet saving to S3."""
        tweets = [{'id': 'tweet1', 'text': 'Test tweet'}]
        digest_data = {'summaries': {}, 'total_tweets': 1}
        
        result_key = self.manager.save_tweets(tweets, digest_data)
        
        self.assertIn('tweets/digests/', result_key)
        self.assertIn('_digest.json', result_key)
        self.mock_s3_client_for_manager.put_object.assert_any_call(
            Bucket="test-bucket",
            Key=result_key.replace("digests", "raw").replace("_digest.json", "_tweets.json"), # Approximate raw key
            Body=json.dumps(tweets, indent=2, default=str),
            ContentType='application/json'
        )
        self.mock_s3_client_for_manager.put_object.assert_any_call(
            Bucket="test-bucket",
            Key=result_key,
            Body=json.dumps(digest_data, indent=2, default=str),
            ContentType='application/json'
        )
        self.assertEqual(self.mock_s3_client_for_manager.put_object.call_count, 2)
    
    def test_save_tweets_s3_error(self):
        """Test handling of S3 errors."""
        self.mock_s3_client_for_manager.put_object.side_effect = Exception("S3 Error")
        
        tweets = [{'id': 'tweet1', 'text': 'Test tweet'}]
        digest_data = {'summaries': {}, 'total_tweets': 1}
        
        with self.assertRaisesRegex(Exception, "S3 Error"):
            self.manager.save_tweets(tweets, digest_data)

if __name__ == '__main__':
    unittest.main() 