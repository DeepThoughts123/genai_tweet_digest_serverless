"""
Unit tests for Lambda function handlers.
Tests the Lambda entry points and event handling.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os

# Add the Lambda function directories to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'subscription'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'weekly-digest'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

class TestSubscriptionLambda(unittest.TestCase):
    """Test the subscription Lambda function."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the config module before importing lambda_function
        self.config_patcher = patch('lambda_function.config')
        self.mock_config = self.config_patcher.start()
        self.mock_config.validate_required_env_vars.return_value = True
        
        # Import after patching
        global lambda_function
        import lambda_function
        self.lambda_function = lambda_function
    
    def tearDown(self):
        """Clean up patches."""
        self.config_patcher.stop()
    
    @patch('lambda_function.SubscriberService')
    def test_subscription_success(self, mock_subscriber_service_class):
        """Test successful email subscription."""
        # Mock SubscriberService
        mock_service = Mock()
        mock_service.add_subscriber.return_value = {
            'success': True,
            'subscriber_id': 'test-id-123'
        }
        mock_subscriber_service_class.return_value = mock_service
        
        # Test event
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({'email': 'test@example.com'})
        }
        context = {}
        
        # Test
        response = self.lambda_function.lambda_handler(event, context)
        
        # Assertions
        self.assertEqual(response['statusCode'], 201)
        body = json.loads(response['body'])
        self.assertTrue(body['success'])
        self.assertIn('subscriber_id', body)
    
    @patch('lambda_function.SubscriberService')
    def test_subscription_duplicate_email(self, mock_subscriber_service_class):
        """Test subscription with duplicate email."""
        # Mock SubscriberService
        mock_service = Mock()
        mock_service.add_subscriber.return_value = {
            'success': False,
            'message': 'Email already subscribed'
        }
        mock_subscriber_service_class.return_value = mock_service
        
        # Test event
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({'email': 'existing@example.com'})
        }
        context = {}
        
        # Test
        response = self.lambda_function.lambda_handler(event, context)
        
        # Assertions
        self.assertEqual(response['statusCode'], 409)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
    
    def test_subscription_invalid_email(self):
        """Test subscription with invalid email."""
        # Test event
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({'email': 'invalid-email'})
        }
        context = {}
        
        # Test
        response = self.lambda_function.lambda_handler(event, context)
        
        # Assertions
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertIn('Invalid email format', body['message'])
    
    def test_subscription_missing_body(self):
        """Test subscription with missing request body."""
        # Test event
        event = {
            'httpMethod': 'POST'
        }
        context = {}
        
        # Test
        response = self.lambda_function.lambda_handler(event, context)
        
        # Assertions
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertIn('Request body is required', body['message'])
    
    def test_subscription_invalid_json(self):
        """Test subscription with invalid JSON."""
        # Test event
        event = {
            'httpMethod': 'POST',
            'body': 'invalid json'
        }
        context = {}
        
        # Test
        response = self.lambda_function.lambda_handler(event, context)
        
        # Assertions
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertIn('Invalid JSON', body['message'])
    
    def test_options_request(self):
        """Test CORS preflight OPTIONS request."""
        # Test event
        event = {
            'httpMethod': 'OPTIONS'
        }
        context = {}
        
        # Test
        response = self.lambda_function.lambda_handler(event, context)
        
        # Assertions
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('Access-Control-Allow-Origin', response['headers'])
    
    def test_config_validation_failure(self):
        """Test handling of configuration validation failure."""
        # Mock config validation failure
        self.mock_config.validate_required_env_vars.return_value = False
        
        # Test event
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({'email': 'test@example.com'})
        }
        context = {}
        
        # Test
        response = self.lambda_function.lambda_handler(event, context)
        
        # Assertions
        self.assertEqual(response['statusCode'], 500)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertIn('Server configuration error', body['message'])
    
    @patch('lambda_function.SubscriberService')
    def test_get_subscriber_count(self, mock_subscriber_service_class):
        """Test get subscriber count handler."""
        # Mock SubscriberService
        mock_service = Mock()
        mock_service.get_subscriber_count.return_value = 42
        mock_subscriber_service_class.return_value = mock_service
        
        # Test event
        event = {
            'httpMethod': 'GET'
        }
        context = {}
        
        # Test
        response = self.lambda_function.get_subscriber_count_handler(event, context)
        
        # Assertions
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['success'])
        self.assertEqual(body['subscriber_count'], 42)

class TestWeeklyDigestLambda(unittest.TestCase):
    """Test the weekly digest Lambda function."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Clear any existing lambda_function imports
        import importlib
        modules_to_clear = [
            'lambda_function',
            'weekly_digest_lambda_function'
        ]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        
        # Import weekly digest lambda function directly from its path
        import importlib.util
        weekly_digest_path = os.path.join(os.path.dirname(__file__), '..', 'weekly-digest', 'lambda_function.py')
        spec = importlib.util.spec_from_file_location("weekly_digest_lambda_function", weekly_digest_path)
        weekly_lambda_function = importlib.util.module_from_spec(spec)
        sys.modules["weekly_digest_lambda_function"] = weekly_lambda_function
        spec.loader.exec_module(weekly_lambda_function)
        
        self.lambda_function = weekly_lambda_function
        
        # Mock the config module after importing lambda_function
        self.config_patcher = patch.object(weekly_lambda_function, 'config')
        self.mock_config = self.config_patcher.start()
        self.mock_config.validate_required_env_vars.return_value = True
        self.mock_config.get_influential_accounts.return_value = ['testuser1', 'testuser2']
    
    def tearDown(self):
        """Clean up patches."""
        self.config_patcher.stop()
    
    @patch('weekly_digest_lambda_function.TweetFetcher')
    @patch('weekly_digest_lambda_function.TweetCategorizer')
    @patch('weekly_digest_lambda_function.TweetSummarizer')
    @patch('weekly_digest_lambda_function.SubscriberService')
    @patch('weekly_digest_lambda_function.SESEmailService')
    @patch('weekly_digest_lambda_function.S3DataManager')
    def test_weekly_digest_success(self, mock_s3, mock_email, mock_subscriber, 
                                   mock_summarizer, mock_categorizer, mock_fetcher):
        """Test successful weekly digest generation."""
        # Mock services
        mock_fetcher_instance = Mock()
        mock_fetcher_instance.fetch_tweets.return_value = [
            {'id': 'tweet1', 'text': 'Test tweet 1'},
            {'id': 'tweet2', 'text': 'Test tweet 2'}
        ]
        mock_fetcher.return_value = mock_fetcher_instance
        
        mock_categorizer_instance = Mock()
        mock_categorizer_instance.categorize_tweets.return_value = [
            {'id': 'tweet1', 'text': 'Test tweet 1', 'category': 'New AI model releases'},
            {'id': 'tweet2', 'text': 'Test tweet 2', 'category': 'Tools and resources'}
        ]
        mock_categorizer.return_value = mock_categorizer_instance
        
        mock_summarizer_instance = Mock()
        mock_summarizer_instance.summarize_tweets.return_value = {
            'summaries': {
                'New AI model releases': {'summary': 'Test summary', 'tweet_count': 1},
                'Tools and resources': {'summary': 'Test summary 2', 'tweet_count': 1}
            },
            'total_tweets': 2,
            'generated_at': '2024-01-01T00:00:00'
        }
        mock_summarizer.return_value = mock_summarizer_instance
        
        mock_subscriber_instance = Mock()
        mock_subscriber_instance.get_all_active_subscribers.return_value = ['test@example.com']
        mock_subscriber.return_value = mock_subscriber_instance
        
        mock_email_instance = Mock()
        mock_email_instance.send_digest_email.return_value = {
            'success': True,
            'emails_sent': 1,
            'failed_emails': []
        }
        mock_email.return_value = mock_email_instance
        
        mock_s3_instance = Mock()
        mock_s3_instance.save_tweets.return_value = 'tweets/digests/test_digest.json'
        mock_s3.return_value = mock_s3_instance
        
        # Test event
        event = {}
        context = {}
        
        # Test
        response = self.lambda_function.lambda_handler(event, context)
        
        # Assertions
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['status'], 'success')
        self.assertEqual(body['tweets_processed'], 2)
        self.assertEqual(body['categories_generated'], 2)
    
    @patch('weekly_digest_lambda_function.TweetFetcher')
    def test_weekly_digest_no_tweets(self, mock_fetcher):
        """Test weekly digest when no tweets are fetched."""
        # Mock empty tweet response
        mock_fetcher_instance = Mock()
        mock_fetcher_instance.fetch_tweets.return_value = []
        mock_fetcher.return_value = mock_fetcher_instance
        
        # Test event
        event = {}
        context = {}
        
        # Test
        response = self.lambda_function.lambda_handler(event, context)
        
        # Assertions
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['status'], 'skipped')
        self.assertEqual(body['reason'], 'no_tweets')
    
    @patch('weekly_digest_lambda_function.TweetFetcher')
    @patch('weekly_digest_lambda_function.TweetCategorizer')
    @patch('weekly_digest_lambda_function.TweetSummarizer')
    @patch('weekly_digest_lambda_function.SubscriberService')
    @patch('weekly_digest_lambda_function.S3DataManager')
    def test_weekly_digest_no_subscribers(self, mock_s3, mock_subscriber, 
                                          mock_summarizer, mock_categorizer, mock_fetcher):
        """Test weekly digest when no subscribers exist."""
        # Mock services
        mock_fetcher_instance = Mock()
        mock_fetcher_instance.fetch_tweets.return_value = [{'id': 'tweet1', 'text': 'Test'}]
        mock_fetcher.return_value = mock_fetcher_instance
        
        mock_categorizer_instance = Mock()
        mock_categorizer_instance.categorize_tweets.return_value = [
            {'id': 'tweet1', 'text': 'Test', 'category': 'Tools and resources'}
        ]
        mock_categorizer.return_value = mock_categorizer_instance
        
        mock_summarizer_instance = Mock()
        mock_summarizer_instance.summarize_tweets.return_value = {
            'summaries': {'Tools and resources': {'summary': 'Test', 'tweet_count': 1}},
            'total_tweets': 1
        }
        mock_summarizer.return_value = mock_summarizer_instance
        
        mock_subscriber_instance = Mock()
        mock_subscriber_instance.get_all_active_subscribers.return_value = []
        mock_subscriber.return_value = mock_subscriber_instance
        
        mock_s3_instance = Mock()
        mock_s3_instance.save_tweets.return_value = 'tweets/digests/test_digest.json'
        mock_s3.return_value = mock_s3_instance
        
        # Test event
        event = {}
        context = {}
        
        # Test
        response = self.lambda_function.lambda_handler(event, context)
        
        # Assertions
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['status'], 'completed_no_subscribers')
        self.assertEqual(body['subscribers'], 0)
    
    def test_config_validation_failure(self):
        """Test handling of configuration validation failure."""
        # Mock config validation failure
        self.mock_config.validate_required_env_vars.return_value = False
        
        # Test event
        event = {}
        context = {}
        
        # Test
        response = self.lambda_function.lambda_handler(event, context)
        
        # Assertions
        self.assertEqual(response['statusCode'], 500)
        body = json.loads(response['body'])
        self.assertEqual(body['status'], 'error')
        self.assertIn('Missing required environment variables', body['error'])
    
    @patch('weekly_digest_lambda_function.TweetFetcher')
    def test_weekly_digest_exception_handling(self, mock_fetcher):
        """Test exception handling in weekly digest."""
        # Mock exception
        mock_fetcher.side_effect = Exception("Test error")
        
        # Test event
        event = {}
        context = {}
        
        # Test
        response = self.lambda_function.lambda_handler(event, context)
        
        # Assertions
        self.assertEqual(response['statusCode'], 500)
        body = json.loads(response['body'])
        self.assertEqual(body['status'], 'error')
        self.assertIn('Test error', body['error'])
    
    def test_manual_trigger_handler(self):
        """Test manual trigger handler."""
        # Mock the lambda_handler function within the same module
        with patch.object(self.lambda_function, 'lambda_handler') as mock_main_handler:
            mock_main_handler.return_value = {
                'statusCode': 200,
                'body': json.dumps({'status': 'success'})
            }
            
            # Test event
            event = {}
            context = {}
            
            # Test
            response = self.lambda_function.manual_trigger_handler(event, context)
            
            # Assertions
            self.assertEqual(response['statusCode'], 200)
            body = json.loads(response['body'])
            self.assertEqual(body['trigger_type'], 'manual')

if __name__ == '__main__':
    unittest.main() 