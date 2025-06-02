"""
Unit tests for unsubscribe functionality.
Tests the unsubscribe Lambda function and service.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'unsubscribe'))

from unsubscribe.lambda_function import lambda_handler, generate_success_page, generate_error_page
from shared.unsubscribe_service import UnsubscribeService


class TestUnsubscribeLambda(unittest.TestCase):
    """Test the unsubscribe Lambda function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config_patcher = patch('unsubscribe.lambda_function.config')
        self.mock_config = self.config_patcher.start()
        self.mock_config.validate_required_env_vars.return_value = True
        
        self.service_patcher = patch('unsubscribe.lambda_function.UnsubscribeService')
        self.MockUnsubscribeService = self.service_patcher.start()
        self.mock_service_instance = self.MockUnsubscribeService.return_value
    
    def tearDown(self):
        """Clean up patches."""
        self.config_patcher.stop()
        self.service_patcher.stop()
    
    def test_unsubscribe_with_email_success(self):
        """Test successful unsubscribe with email parameter."""
        self.mock_service_instance.unsubscribe_email.return_value = {
            'success': True,
            'message': 'Successfully unsubscribed'
        }
        
        event = {
            'httpMethod': 'GET',
            'queryStringParameters': {
                'email': 'test@example.com'
            }
        }
        
        response = lambda_handler(event, None)
        
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(response['headers']['Content-Type'], 'text/html')
        self.assertIn('Successfully Unsubscribed', response['body'])
        self.assertIn('test@example.com', response['body'])
        self.mock_service_instance.unsubscribe_email.assert_called_once_with('test@example.com')
    
    def test_unsubscribe_with_token_success(self):
        """Test successful unsubscribe with token parameter."""
        test_token = 'test-token-123'
        test_email = 'test@example.com'
        
        self.mock_service_instance.decode_unsubscribe_token.return_value = test_email
        self.mock_service_instance.unsubscribe_email.return_value = {
            'success': True,
            'message': 'Successfully unsubscribed'
        }
        
        event = {
            'httpMethod': 'GET',
            'queryStringParameters': {
                'token': test_token
            }
        }
        
        response = lambda_handler(event, None)
        
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('Successfully Unsubscribed', response['body'])
        self.assertIn(test_email, response['body'])
        self.mock_service_instance.decode_unsubscribe_token.assert_called_once_with(test_token)
        self.mock_service_instance.unsubscribe_email.assert_called_once_with(test_email)
    
    def test_unsubscribe_missing_parameters(self):
        """Test error when both email and token are missing."""
        event = {
            'httpMethod': 'GET',
            'queryStringParameters': {}
        }
        
        response = lambda_handler(event, None)
        
        self.assertEqual(response['statusCode'], 400)
        self.assertIn('Missing email or token parameter', response['body'])
        self.assertIn('Unsubscribe Error', response['body'])
    
    def test_unsubscribe_invalid_token(self):
        """Test error with invalid token."""
        self.mock_service_instance.decode_unsubscribe_token.return_value = None
        
        event = {
            'httpMethod': 'GET',
            'queryStringParameters': {
                'token': 'invalid-token'
            }
        }
        
        response = lambda_handler(event, None)
        
        self.assertEqual(response['statusCode'], 400)
        self.assertIn('Invalid unsubscribe token', response['body'])
    
    def test_unsubscribe_service_failure(self):
        """Test handling of service failure."""
        self.mock_service_instance.unsubscribe_email.return_value = {
            'success': False,
            'message': 'Email not found',
            'status_code': 404
        }
        
        event = {
            'httpMethod': 'GET',
            'queryStringParameters': {
                'email': 'notfound@example.com'
            }
        }
        
        response = lambda_handler(event, None)
        
        self.assertEqual(response['statusCode'], 404)
        self.assertIn('Email not found', response['body'])
        self.assertIn('Unsubscribe Error', response['body'])
    
    def test_unsubscribe_config_validation_failure(self):
        """Test handling of configuration validation failure."""
        # Make config validation raise an exception
        self.mock_config.validate_required_env_vars.side_effect = Exception("Missing config")
        
        event = {
            'httpMethod': 'GET',
            'queryStringParameters': {
                'email': 'test@example.com'
            }
        }
        
        response = lambda_handler(event, None)
        
        self.assertEqual(response['statusCode'], 500)
        self.assertIn('Server configuration error', response['body'])
    
    def test_unsubscribe_exception_handling(self):
        """Test handling of unexpected exceptions."""
        self.mock_service_instance.unsubscribe_email.side_effect = Exception("Database error")
        
        event = {
            'httpMethod': 'GET',
            'queryStringParameters': {
                'email': 'test@example.com'
            }
        }
        
        response = lambda_handler(event, None)
        
        self.assertEqual(response['statusCode'], 500)
        self.assertIn('Server configuration error', response['body'])
    
    def test_generate_success_page(self):
        """Test generation of success page HTML."""
        email = 'test@example.com'
        html = generate_success_page(email)
        
        self.assertIn('Successfully Unsubscribed', html)
        self.assertIn(email, html)
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('GenAI Weekly Digest', html)
        self.assertIn('You have been unsubscribed', html)
    
    def test_generate_error_page(self):
        """Test generation of error page HTML."""
        error_message = 'Test error message'
        html = generate_error_page(error_message)
        
        self.assertIn('Unsubscribe Error', html)
        self.assertIn(error_message, html)
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('GenAI Weekly Digest', html)
        self.assertIn('Unsubscribe Failed', html)


class TestUnsubscribeService(unittest.TestCase):
    """Test the UnsubscribeService class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config_patcher = patch('shared.unsubscribe_service.config')
        self.mock_config = self.config_patcher.start()
        
        self.subscriber_service_patcher = patch('shared.unsubscribe_service.SubscriberService')
        self.MockSubscriberService = self.subscriber_service_patcher.start()
        self.mock_subscriber_service = self.MockSubscriberService.return_value
        
        self.service = UnsubscribeService()
    
    def tearDown(self):
        """Clean up patches."""
        self.config_patcher.stop()
        self.subscriber_service_patcher.stop()
    
    def test_unsubscribe_email_success(self):
        """Test successful email unsubscription."""
        email = 'test@example.com'
        subscriber_id = 'test-id'
        
        # Mock SubscriberService responses
        self.mock_subscriber_service.get_subscriber_by_email.return_value = {
            'subscriber_id': subscriber_id,
            'email': email,
            'status': 'active'
        }
        self.mock_subscriber_service.unsubscribe.return_value = True
        
        result = self.service.unsubscribe_email(email)
        
        self.assertTrue(result['success'])
        self.assertIn('Successfully unsubscribed', result['message'])
        self.assertEqual(result['status_code'], 200)
        self.assertEqual(result['subscriber_id'], subscriber_id)
        
        # Verify method calls
        self.mock_subscriber_service.get_subscriber_by_email.assert_called_once_with(email)
        self.mock_subscriber_service.unsubscribe.assert_called_once_with(subscriber_id)
    
    def test_unsubscribe_email_not_found(self):
        """Test unsubscribe with email not found."""
        email = 'notfound@example.com'
        
        self.mock_subscriber_service.get_subscriber_by_email.return_value = None
        
        result = self.service.unsubscribe_email(email)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['status_code'], 404)
        self.assertIn('not found', result['message'])
    
    def test_unsubscribe_email_already_unsubscribed(self):
        """Test unsubscribe with already unsubscribed email."""
        email = 'test@example.com'
        
        self.mock_subscriber_service.get_subscriber_by_email.return_value = {
            'subscriber_id': 'test-id',
            'email': email,
            'status': 'unsubscribed'
        }
        
        result = self.service.unsubscribe_email(email)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['status_code'], 404)
        self.assertIn('already unsubscribed', result['message'])
        
        # Should not call unsubscribe since already unsubscribed
        self.mock_subscriber_service.unsubscribe.assert_not_called()
    
    def test_decode_unsubscribe_token_success(self):
        """Test successful token decoding."""
        import base64
        
        email = 'test@example.com'
        token = base64.urlsafe_b64encode(email.encode()).decode()
        
        result = self.service.decode_unsubscribe_token(token)
        
        self.assertEqual(result, email)
    
    def test_decode_unsubscribe_token_invalid(self):
        """Test invalid token decoding."""
        invalid_token = 'invalid-token'
        
        result = self.service.decode_unsubscribe_token(invalid_token)
        
        self.assertIsNone(result)
    
    def test_get_unsubscribe_token(self):
        """Test unsubscribe token generation."""
        email = 'test@example.com'
        
        token = self.service.get_unsubscribe_token(email)
        
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)
        
        # Verify token can be decoded back to email
        decoded_email = self.service.decode_unsubscribe_token(token)
        self.assertEqual(decoded_email, email)
    
    def test_unsubscribe_email_service_failure(self):
        """Test handling when SubscriberService.unsubscribe fails."""
        email = 'test@example.com'
        subscriber_id = 'test-id'
        
        self.mock_subscriber_service.get_subscriber_by_email.return_value = {
            'subscriber_id': subscriber_id,
            'email': email,
            'status': 'active'
        }
        self.mock_subscriber_service.unsubscribe.return_value = False
        
        result = self.service.unsubscribe_email(email)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['status_code'], 500)
        self.assertIn('Failed to unsubscribe', result['message'])
    
    def test_unsubscribe_email_exception_handling(self):
        """Test handling of exceptions from SubscriberService."""
        email = 'test@example.com'
        
        self.mock_subscriber_service.get_subscriber_by_email.side_effect = Exception("Database error")
        
        result = self.service.unsubscribe_email(email)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['status_code'], 500)
        self.assertIn('error occurred', result['message'])


if __name__ == '__main__':
    unittest.main() 