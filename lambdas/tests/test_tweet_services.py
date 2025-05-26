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

# Add the shared directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from tweet_services import TweetFetcher, TweetCategorizer, TweetSummarizer, S3DataManager

class TestTweetFetcher(unittest.TestCase):
    """Test the TweetFetcher class."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('tweet_services.config') as mock_config:
            mock_config.twitter_bearer_token = "test_token"
            self.fetcher = TweetFetcher()
    
    @patch('tweet_services.tweepy.Client')
    def test_fetch_tweets_success(self, mock_client_class):
        """Test successful tweet fetching."""
        # Mock tweepy client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock user response
        mock_user = Mock()
        mock_user.data.id = "123456789"
        mock_client.get_user.return_value = mock_user
        
        # Mock tweet response
        mock_tweet = Mock()
        mock_tweet.id = "tweet123"
        mock_tweet.text = "Test tweet about AI"
        mock_tweet.author_id = "123456789"
        mock_tweet.created_at = datetime.now()
        mock_tweet.public_metrics = {"like_count": 10}
        
        mock_tweets_response = Mock()
        mock_tweets_response.data = [mock_tweet]
        mock_client.get_users_tweets.return_value = mock_tweets_response
        
        # Test
        with patch('tweet_services.config') as mock_config:
            mock_config.twitter_bearer_token = "test_token"
            fetcher = TweetFetcher()
            tweets = fetcher.fetch_tweets(["testuser"])
        
        # Assertions
        self.assertEqual(len(tweets), 1)
        self.assertEqual(tweets[0]['id'], "tweet123")
        self.assertEqual(tweets[0]['text'], "Test tweet about AI")
        self.assertEqual(tweets[0]['username'], "testuser")
    
    @patch('tweet_services.tweepy.Client')
    def test_fetch_tweets_user_not_found(self, mock_client_class):
        """Test handling of user not found."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock user not found
        mock_user_response = Mock()
        mock_user_response.data = None
        mock_client.get_user.return_value = mock_user_response
        
        # Test
        with patch('tweet_services.config') as mock_config:
            mock_config.twitter_bearer_token = "test_token"
            fetcher = TweetFetcher()
            tweets = fetcher.fetch_tweets(["nonexistentuser"])
        
        # Should return empty list
        self.assertEqual(len(tweets), 0)
    
    @patch('tweet_services.tweepy.Client')
    def test_fetch_tweets_api_error(self, mock_client_class):
        """Test handling of API errors."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock API error
        mock_client.get_user.side_effect = Exception("API Error")
        
        # Test
        with patch('tweet_services.config') as mock_config:
            mock_config.twitter_bearer_token = "test_token"
            fetcher = TweetFetcher()
            tweets = fetcher.fetch_tweets(["testuser"])
        
        # Should handle error gracefully
        self.assertEqual(len(tweets), 0)

class TestTweetCategorizer(unittest.TestCase):
    """Test the TweetCategorizer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('tweet_services.config') as mock_config:
            mock_config.gemini_api_key = "test_key"
            with patch('tweet_services.genai.configure'):
                with patch('tweet_services.genai.GenerativeModel'):
                    self.categorizer = TweetCategorizer()
    
    @patch('tweet_services.genai.GenerativeModel')
    @patch('tweet_services.genai.configure')
    def test_categorize_tweets_success(self, mock_configure, mock_model_class):
        """Test successful tweet categorization."""
        # Mock Gemini response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Category: New AI model releases\nConfidence: 0.95"
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        # Test data
        tweets = [
            {
                'id': 'tweet1',
                'text': 'OpenAI just released GPT-5!',
                'username': 'testuser'
            }
        ]
        
        # Test
        with patch('tweet_services.config') as mock_config:
            mock_config.gemini_api_key = "test_key"
            categorizer = TweetCategorizer()
            categorized = categorizer.categorize_tweets(tweets)
        
        # Assertions
        self.assertEqual(len(categorized), 1)
        self.assertEqual(categorized[0]['category'], 'New AI model releases')
        self.assertEqual(categorized[0]['confidence'], 0.95)
    
    @patch('tweet_services.genai.GenerativeModel')
    @patch('tweet_services.genai.configure')
    def test_categorize_tweets_invalid_response(self, mock_configure, mock_model_class):
        """Test handling of invalid Gemini response."""
        # Mock invalid Gemini response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Invalid response format"
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        # Test data
        tweets = [{'id': 'tweet1', 'text': 'Test tweet'}]
        
        # Test
        with patch('tweet_services.config') as mock_config:
            mock_config.gemini_api_key = "test_key"
            categorizer = TweetCategorizer()
            categorized = categorizer.categorize_tweets(tweets)
        
        # Should use default category
        self.assertEqual(categorized[0]['category'], 'Tools and resources')
        self.assertEqual(categorized[0]['confidence'], 0.5)
    
    @patch('tweet_services.genai.GenerativeModel')
    @patch('tweet_services.genai.configure')
    def test_categorize_tweets_api_error(self, mock_configure, mock_model_class):
        """Test handling of Gemini API errors."""
        # Mock API error
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("API Error")
        mock_model_class.return_value = mock_model
        
        # Test data
        tweets = [{'id': 'tweet1', 'text': 'Test tweet'}]
        
        # Test
        with patch('tweet_services.config') as mock_config:
            mock_config.gemini_api_key = "test_key"
            categorizer = TweetCategorizer()
            categorized = categorizer.categorize_tweets(tweets)
        
        # Should handle error gracefully with default category
        self.assertEqual(categorized[0]['category'], 'Tools and resources')
        self.assertEqual(categorized[0]['confidence'], 0.5)

class TestTweetSummarizer(unittest.TestCase):
    """Test the TweetSummarizer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('tweet_services.config') as mock_config:
            mock_config.gemini_api_key = "test_key"
            with patch('tweet_services.genai.configure'):
                with patch('tweet_services.genai.GenerativeModel'):
                    self.summarizer = TweetSummarizer()
    
    @patch('tweet_services.genai.GenerativeModel')
    @patch('tweet_services.genai.configure')
    def test_summarize_tweets_success(self, mock_configure, mock_model_class):
        """Test successful tweet summarization."""
        # Mock Gemini response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "OpenAI has released a groundbreaking new model that shows significant improvements in reasoning capabilities."
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        # Test data
        categorized_tweets = [
            {
                'id': 'tweet1',
                'text': 'OpenAI just released GPT-5!',
                'category': 'New AI model releases',
                'confidence': 0.95
            },
            {
                'id': 'tweet2', 
                'text': 'GPT-5 shows amazing reasoning!',
                'category': 'New AI model releases',
                'confidence': 0.90
            }
        ]
        
        # Test
        with patch('tweet_services.config') as mock_config:
            mock_config.gemini_api_key = "test_key"
            summarizer = TweetSummarizer()
            result = summarizer.summarize_tweets(categorized_tweets)
        
        # Assertions
        self.assertIn('summaries', result)
        self.assertIn('total_tweets', result)
        self.assertIn('generated_at', result)
        self.assertEqual(result['total_tweets'], 2)
        self.assertIn('New AI model releases', result['summaries'])
        self.assertEqual(result['summaries']['New AI model releases']['tweet_count'], 2)
    
    @patch('tweet_services.genai.GenerativeModel')
    @patch('tweet_services.genai.configure')
    def test_summarize_tweets_empty_input(self, mock_configure, mock_model_class):
        """Test handling of empty tweet list."""
        # Test
        with patch('tweet_services.config') as mock_config:
            mock_config.gemini_api_key = "test_key"
            summarizer = TweetSummarizer()
            result = summarizer.summarize_tweets([])
        
        # Assertions
        self.assertEqual(result['total_tweets'], 0)
        self.assertEqual(len(result['summaries']), 0)
    
    @patch('tweet_services.genai.GenerativeModel')
    @patch('tweet_services.genai.configure')
    def test_summarize_tweets_api_error(self, mock_configure, mock_model_class):
        """Test handling of Gemini API errors."""
        # Mock API error
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("API Error")
        mock_model_class.return_value = mock_model
        
        # Test data
        categorized_tweets = [
            {
                'id': 'tweet1',
                'text': 'Test tweet',
                'category': 'New AI model releases',
                'confidence': 0.95
            }
        ]
        
        # Test
        with patch('tweet_services.config') as mock_config:
            mock_config.gemini_api_key = "test_key"
            summarizer = TweetSummarizer()
            result = summarizer.summarize_tweets(categorized_tweets)
        
        # Should handle error gracefully with fallback summary
        self.assertIn('New AI model releases', result['summaries'])
        summary_text = result['summaries']['New AI model releases']['summary']
        self.assertIn('recent developments in new ai model releases.', summary_text.lower())

class TestS3DataManager(unittest.TestCase):
    """Test the S3DataManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('tweet_services.config') as mock_config:
            mock_config.s3_client = Mock()
            mock_config.s3_bucket = "test-bucket"
            mock_config.tweets_prefix = "tweets/"
            self.manager = S3DataManager()
    
    @patch('tweet_services.config')
    def test_save_tweets_success(self, mock_config):
        """Test successful tweet saving to S3."""
        # Mock S3 client
        mock_s3_client = Mock()
        mock_config.s3_client = mock_s3_client
        mock_config.s3_bucket = "test-bucket"
        mock_config.tweets_prefix = "tweets/"
        
        # Test data
        tweets = [{'id': 'tweet1', 'text': 'Test tweet'}]
        digest_data = {'summaries': {}, 'total_tweets': 1}
        
        # Test
        manager = S3DataManager()
        result_key = manager.save_tweets(tweets, digest_data)
        
        # Assertions
        self.assertIn('tweets/digests/', result_key)
        self.assertIn('_digest.json', result_key)
        self.assertEqual(mock_s3_client.put_object.call_count, 2)  # tweets + digest
    
    @patch('tweet_services.config')
    def test_save_tweets_s3_error(self, mock_config):
        """Test handling of S3 errors."""
        # Mock S3 client with error
        mock_s3_client = Mock()
        mock_s3_client.put_object.side_effect = Exception("S3 Error")
        mock_config.s3_client = mock_s3_client
        mock_config.s3_bucket = "test-bucket"
        mock_config.tweets_prefix = "tweets/"
        
        # Test data
        tweets = [{'id': 'tweet1', 'text': 'Test tweet'}]
        digest_data = {'summaries': {}, 'total_tweets': 1}
        
        # Test - should raise exception
        manager = S3DataManager()
        with self.assertRaises(Exception):
            manager.save_tweets(tweets, digest_data)

if __name__ == '__main__':
    unittest.main() 