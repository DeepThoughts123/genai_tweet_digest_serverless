"""
Unit tests for Lambda function handlers.
Tests the Lambda entry points and event handling.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os

# Add the shared directory to sys.path for the handlers to find it
# CWD for tests run via run-unit-tests.sh will be lambdas/
base_dir = os.path.dirname(__file__) # lambdas/tests
# sys.path.insert(0, os.path.join(base_dir, '..')) # Add lambdas/ to sys.path (already there due to CWD)
sys.path.insert(0, os.path.join(base_dir, '..', 'shared')) # Add lambdas/shared
sys.path.insert(0, os.path.join(base_dir, '..', 'subscription')) # Add lambdas/subscription
sys.path.insert(0, os.path.join(base_dir, '..', 'weekly-digest'))
sys.path.insert(0, os.path.join(base_dir, '..', 'email-verification'))
sys.path.insert(0, os.path.join(base_dir, '..', 'unsubscribe'))

from subscription.lambda_function import lambda_handler, get_subscriber_count_handler # MODIFIED
# For TestWeeklyDigestLambda, it dynamically imports its lambda_function, which should now work if it uses 'from shared...'

class TestSubscriptionLambda(unittest.TestCase):
    """Test the subscription Lambda function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config_patcher = patch('subscription.lambda_function.config') # MODIFIED
        self.mock_config_module = self.config_patcher.start()
        self.mock_config_module.validate_required_env_vars.return_value = True
        self.mock_config_module.subscribers_table = 'fake-table'
        self.mock_config_module.aws_region = 'us-east-1'
        self.mock_config_module.from_email = 'test@example.com'
        self.mock_config_module.get_api_base_url.return_value = 'https://api.example.com'
        self.mock_config_module.dynamodb = Mock()
        self.mock_config_module.ses_client = Mock()

        self.ev_service_patcher = patch('subscription.lambda_function.EmailVerificationService') # MODIFIED
        self.MockEmailVerificationService = self.ev_service_patcher.start()
        self.mock_ev_instance = self.MockEmailVerificationService.return_value

        self.sub_service_patcher = patch('subscription.lambda_function.SubscriberService') # MODIFIED
        self.MockSubscriberService = self.sub_service_patcher.start()
        self.mock_sub_instance = self.MockSubscriberService.return_value
    
    def tearDown(self):
        """Clean up patches."""
        self.config_patcher.stop()
        self.ev_service_patcher.stop()
        self.sub_service_patcher.stop()
    
    def test_subscription_success(self):
        self.mock_sub_instance.get_subscriber_by_email.return_value = None
        self.mock_ev_instance.create_pending_subscriber.return_value = {
            'success': True,
            'message': 'Verification email sent. Please check your inbox.',
            'subscriber_id': 'test-subscriber-id'
        }
        event_data = {'body': json.dumps({'email': 'test@example.com'}), 'httpMethod': 'POST'}
        response = lambda_handler(event_data, None)
        self.assertEqual(response['statusCode'], 201)
        body = json.loads(response['body'])
        self.assertTrue(body['success'])
        self.assertEqual(body['subscriber_id'], 'test-subscriber-id')
    
    def test_subscription_duplicate_email(self):
        self.mock_sub_instance.get_subscriber_by_email.return_value = {
            'status': 'active', 'email': 'test@example.com', 'subscriber_id': 'prev-id'
        }
        event_data = {'body': json.dumps({'email': 'test@example.com'}), 'httpMethod': 'POST'}
        response = lambda_handler(event_data, None)
        self.assertEqual(response['statusCode'], 409)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertIn('Email already subscribed', body['message'])

        self.mock_sub_instance.reset_mock() # Reset for next part of test
        self.mock_ev_instance.reset_mock()
        self.mock_sub_instance.get_subscriber_by_email.return_value = {
            'status': 'pending_verification', 'email': 'pending@example.com', 'subscriber_id': 'pending-id'
        }
        self.mock_ev_instance.resend_verification.return_value = {
            'success': True,
            'message': 'Verification email resent. Please check your inbox.'
        }
        event_data = {'body': json.dumps({'email': 'pending@example.com'}), 'httpMethod': 'POST'}
        response = lambda_handler(event_data, None)
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['success'])
        self.assertIn('Verification email resent', body['message'])
        self.mock_ev_instance.resend_verification.assert_called_once_with('pending@example.com')
    
    def test_subscription_invalid_email(self):
        event_data = {'body': json.dumps({'email': 'invalid-email'}), 'httpMethod': 'POST'}
        response = lambda_handler(event_data, None)
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertEqual(body['message'], 'Invalid email format')
    
    def test_subscription_missing_body(self):
        event_data = {'httpMethod': 'POST'}
        response = lambda_handler(event_data, None)
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertEqual(body['message'], 'Request body is required')
    
    def test_subscription_invalid_json(self):
        event_data = {'body': 'not a json', 'httpMethod': 'POST'}
        response = lambda_handler(event_data, None)
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertEqual(body['message'], 'Invalid JSON in request body')
    
    def test_options_request(self):
        event_data = {'httpMethod': 'OPTIONS'}
        response = lambda_handler(event_data, None)
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['message'], 'CORS preflight')
    
    def test_config_validation_failure(self):
        self.mock_config_module.validate_required_env_vars.return_value = False
        event_data = {'body': json.dumps({'email': 'test@example.com'}), 'httpMethod': 'POST'}
        response = lambda_handler(event_data, None)
        self.assertEqual(response['statusCode'], 500)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertEqual(body['message'], 'Server configuration error')
        self.mock_config_module.validate_required_env_vars.return_value = True
    
    def test_get_subscriber_count(self):
        self.mock_sub_instance.get_subscriber_count.return_value = 123
        event_data = {'httpMethod': 'GET', 'path': '/subscribers/count'} 
        response = get_subscriber_count_handler(event_data, None)
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['success'])
        self.assertEqual(body['subscriber_count'], 123)

class TestWeeklyDigestLambda(unittest.TestCase):
    """Test the weekly digest Lambda function."""
    
    def setUp(self):
        """Set up test fixtures."""
        import importlib.util
        weekly_digest_module_path = os.path.join('weekly-digest', 'lambda_function.py')
        spec = importlib.util.spec_from_file_location("weekly_digest_lambda_module", weekly_digest_module_path)
        self.weekly_digest_lambda_module = importlib.util.module_from_spec(spec)
        sys.modules["weekly_digest_lambda_module"] = self.weekly_digest_lambda_module
        spec.loader.exec_module(self.weekly_digest_lambda_module)
        
        self.config_patcher = patch.object(self.weekly_digest_lambda_module, 'config')
        self.mock_config = self.config_patcher.start()
        self.mock_config.validate_required_env_vars.return_value = True
        self.mock_config.get_influential_accounts.return_value = ['testuser1', 'testuser2']

        # Patch services using patch.object
        self.fetcher_patcher = patch.object(self.weekly_digest_lambda_module, 'TweetFetcher')
        self.MockTweetFetcher = self.fetcher_patcher.start()
        self.categorizer_patcher = patch.object(self.weekly_digest_lambda_module, 'TweetCategorizer')
        self.MockTweetCategorizer = self.categorizer_patcher.start()
        self.summarizer_patcher = patch.object(self.weekly_digest_lambda_module, 'TweetSummarizer')
        self.MockTweetSummarizer = self.summarizer_patcher.start()
        self.subscriber_patcher = patch.object(self.weekly_digest_lambda_module, 'SubscriberService')
        self.MockSubscriberService = self.subscriber_patcher.start()
        self.ses_patcher = patch.object(self.weekly_digest_lambda_module, 'SESEmailService')
        self.MockSESEmailService = self.ses_patcher.start()
        self.s3_patcher = patch.object(self.weekly_digest_lambda_module, 'S3DataManager')
        self.MockS3DataManager = self.s3_patcher.start()
    
    def tearDown(self):
        self.config_patcher.stop()
        self.fetcher_patcher.stop()
        self.categorizer_patcher.stop()
        self.summarizer_patcher.stop()
        self.subscriber_patcher.stop()
        self.ses_patcher.stop()
        self.s3_patcher.stop()
    
    def test_weekly_digest_success(self):
        mock_fetcher_instance = self.MockTweetFetcher.return_value
        mock_fetcher_instance.fetch_tweets.return_value = [
            {'id': 'tweet1', 'text': 'Test tweet 1'},
            {'id': 'tweet2', 'text': 'Test tweet 2'}
        ]
        
        mock_categorizer_instance = self.MockTweetCategorizer.return_value
        mock_categorizer_instance.categorize_tweets.return_value = [
            {'id': 'tweet1', 'text': 'Test tweet 1', 'category': 'New AI model releases'},
            {'id': 'tweet2', 'text': 'Test tweet 2', 'category': 'Tools and resources'}
        ]
        
        mock_summarizer_instance = self.MockTweetSummarizer.return_value
        mock_summarizer_instance.summarize_tweets.return_value = {
            'summaries': {
                'New AI model releases': {'summary': 'Test summary', 'tweet_count': 1},
                'Tools and resources': {'summary': 'Test summary 2', 'tweet_count': 1}
            },
            'total_tweets': 2,
            'generated_at': '2024-01-01T00:00:00'
        }
        
        mock_subscriber_instance = self.MockSubscriberService.return_value
        mock_subscriber_instance.get_all_active_subscribers.return_value = ['test@example.com']
        
        mock_email_instance = self.MockSESEmailService.return_value
        mock_email_instance.send_digest_email.return_value = {
            'success': True,
            'emails_sent': 1,
            'failed_emails': []
        }
        
        mock_s3_instance = self.MockS3DataManager.return_value
        mock_s3_instance.save_tweets.return_value = 'tweets/digests/test_digest.json'
        
        event = {}
        context = {}
        response = self.weekly_digest_lambda_module.lambda_handler(event, context)
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['status'], 'success')
        self.assertEqual(body['tweets_processed'], 2)
        self.assertEqual(body['categories_generated'], 2)
    
    def test_weekly_digest_no_tweets(self):
        mock_fetcher_instance = self.MockTweetFetcher.return_value
        mock_fetcher_instance.fetch_tweets.return_value = []
        event = {}
        context = {}
        response = self.weekly_digest_lambda_module.lambda_handler(event, context)
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['status'], 'skipped')
        self.assertEqual(body['reason'], 'no_tweets')
    
    def test_weekly_digest_no_subscribers(self):
        mock_fetcher_instance = self.MockTweetFetcher.return_value
        mock_fetcher_instance.fetch_tweets.return_value = [{'id': 'tweet1', 'text': 'Test'}]
        
        mock_categorizer_instance = self.MockTweetCategorizer.return_value
        mock_categorizer_instance.categorize_tweets.return_value = [
            {'id': 'tweet1', 'text': 'Test', 'category': 'Tools and resources'}
        ]
        
        mock_summarizer_instance = self.MockTweetSummarizer.return_value
        mock_summarizer_instance.summarize_tweets.return_value = {
            'summaries': {'Tools and resources': {'summary': 'Test', 'tweet_count': 1}},
            'total_tweets': 1
        }
        
        mock_subscriber_instance = self.MockSubscriberService.return_value
        mock_subscriber_instance.get_all_active_subscribers.return_value = []
        
        mock_s3_instance = self.MockS3DataManager.return_value
        mock_s3_instance.save_tweets.return_value = 'tweets/digests/test_digest.json'
        
        event = {}
        context = {}
        response = self.weekly_digest_lambda_module.lambda_handler(event, context)
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['status'], 'completed_no_subscribers')
        self.assertEqual(body['subscribers'], 0)
    
    def test_config_validation_failure(self):
        self.mock_config.validate_required_env_vars.return_value = False
        event = {}
        context = {}
        response = self.weekly_digest_lambda_module.lambda_handler(event, context)
        self.assertEqual(response['statusCode'], 500)
        body = json.loads(response['body'])
        self.assertEqual(body['status'], 'error')
        self.assertIn('Missing required environment variables', body['error'])
        self.mock_config.validate_required_env_vars.return_value = True # Reset

    def test_weekly_digest_exception_handling(self):
        # Mock exception on TweetFetcher, for example
        self.MockTweetFetcher.return_value.fetch_tweets.side_effect = Exception("Test error")
        event = {}
        context = {}
        response = self.weekly_digest_lambda_module.lambda_handler(event, context)
        self.assertEqual(response['statusCode'], 500)
        body = json.loads(response['body'])
        self.assertEqual(body['status'], 'error')
        self.assertIn('Test error', body['error'])
    
    def test_manual_trigger_handler(self):
        with patch.object(self.weekly_digest_lambda_module, 'lambda_handler') as mock_main_handler:
            mock_main_handler.return_value = {
                'statusCode': 200,
                'body': json.dumps({'status': 'success'})
            }
            event = {}
            context = {}
            response = self.weekly_digest_lambda_module.manual_trigger_handler(event, context)
            self.assertEqual(response['statusCode'], 200)
            body = json.loads(response['body'])
            self.assertEqual(body['trigger_type'], 'manual')

if __name__ == '__main__':
    unittest.main() 