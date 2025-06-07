"""
Unit tests for email verification Lambda function.
Tests the email verification Lambda handler.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os

# Add path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from lambda_function import lambda_handler


class TestEmailVerificationLambda(unittest.TestCase):
    """Test the email verification Lambda function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config_patcher = patch('lambda_function.config')
        self.mock_config = self.config_patcher.start()
        self.mock_config.validate_required_env_vars.return_value = True
        
        self.service_patcher = patch('lambda_function.EmailVerificationService')
        self.MockEmailVerificationService = self.service_patcher.start()
        self.mock_service_instance = self.MockEmailVerificationService.return_value
    
    def tearDown(self):
        """Clean up patches."""
        self.config_patcher.stop()
        self.service_patcher.stop()
    
    def test_verify_email_success(self):
        """Test successful email verification."""
        verification_token = 'test-token-123'
        test_email = 'test@example.com'
        
        self.mock_service_instance.verify_email.return_value = {
            'success': True,
            'message': 'Email verified successfully',
            'email': test_email
        }
        
        event = {
            'httpMethod': 'GET',
            'queryStringParameters': {
                'token': verification_token
            }
        }
        
        response = lambda_handler(event, None)
        
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(response['headers']['Content-Type'], 'text/html')
        self.assertIn('Email Verified Successfully', response['body'])
        self.assertIn(test_email, response['body'])
        self.mock_service_instance.verify_email.assert_called_once_with(verification_token)
    
    def test_verify_email_missing_token(self):
        """Test error when token is missing."""
        event = {
            'httpMethod': 'GET',
            'queryStringParameters': {}
        }
        
        response = lambda_handler(event, None)
        
        self.assertEqual(response['statusCode'], 400)
        self.assertIn('Verification token is required', response['body'])
        self.assertIn('Verification Error', response['body'])
    
    def test_verify_email_invalid_token(self):
        """Test error with invalid token."""
        self.mock_service_instance.verify_email.return_value = {
            'success': False,
            'message': 'Invalid or expired verification token'
        }
        
        event = {
            'httpMethod': 'GET',
            'queryStringParameters': {
                'token': 'invalid-token'
            }
        }
        
        response = lambda_handler(event, None)
        
        self.assertEqual(response['statusCode'], 400)
        self.assertIn('Invalid or expired verification token', response['body'])
        self.assertIn('Verification Error', response['body'])
    
    def test_verify_email_expired_token(self):
        """Test error with expired token."""
        self.mock_service_instance.verify_email.return_value = {
            'success': False,
            'message': 'Verification token has expired'
        }
        
        event = {
            'httpMethod': 'GET',
            'queryStringParameters': {
                'token': 'expired-token'
            }
        }
        
        response = lambda_handler(event, None)
        
        self.assertEqual(response['statusCode'], 400)
        self.assertIn('Verification token has expired', response['body'])
        self.assertIn('Verification Error', response['body'])
    
    def test_verify_email_config_validation_failure(self):
        """Test handling of configuration validation failure."""
        self.mock_config.validate_required_env_vars.return_value = False
        
        event = {
            'httpMethod': 'GET',
            'queryStringParameters': {
                'token': 'test-token'
            }
        }
        
        response = lambda_handler(event, None)
        
        self.assertEqual(response['statusCode'], 500)
        self.assertIn('Server configuration error', response['body'])
    
    def test_verify_email_exception_handling(self):
        """Test handling of unexpected exceptions."""
        self.mock_service_instance.verify_email.side_effect = Exception("Database error")
        
        event = {
            'httpMethod': 'GET',
            'queryStringParameters': {
                'token': 'test-token'
            }
        }
        
        response = lambda_handler(event, None)
        
        self.assertEqual(response['statusCode'], 500)
        self.assertIn('Internal server error', response['body'])
    
    def test_verify_email_null_query_parameters(self):
        """Test handling when queryStringParameters is None."""
        event = {
            'httpMethod': 'GET',
            'queryStringParameters': None
        }
        
        response = lambda_handler(event, None)
        
        self.assertEqual(response['statusCode'], 400)
        self.assertIn('Verification token is required', response['body'])
    
    def test_html_response_structure(self):
        """Test that HTML responses have correct structure."""
        self.mock_service_instance.verify_email.return_value = {
            'success': True,
            'message': 'Email verified successfully',
            'email': 'test@example.com'
        }
        
        event = {
            'httpMethod': 'GET',
            'queryStringParameters': {
                'token': 'test-token'
            }
        }
        
        response = lambda_handler(event, None)
        
        # Check response structure
        self.assertIn('statusCode', response)
        self.assertIn('headers', response)
        self.assertIn('body', response)
        
        # Check headers
        headers = response['headers']
        self.assertEqual(headers['Content-Type'], 'text/html')
        self.assertEqual(headers['Access-Control-Allow-Origin'], '*')
        
        # Check HTML content
        body = response['body']
        self.assertIn('<!DOCTYPE html>', body)
        self.assertIn('<html', body)
        self.assertIn('</html>', body)
        self.assertIn('GenAI Weekly Digest', body)


class TestEmailVerificationHTMLGeneration(unittest.TestCase):
    """Test HTML page generation functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Import the functions here to avoid import issues
        sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        
        try:
            from lambda_function import get_success_html, get_error_html
            self.get_success_html = get_success_html
            self.get_error_html = get_error_html
        except ImportError:
            self.skipTest("Email verification lambda function not available")
    
    def test_generate_success_page(self):
        """Test generation of success page HTML."""
        email = 'test@example.com'
        html = self.get_success_html(email)
        
        self.assertIn('Email Verified Successfully', html)
        self.assertIn(email, html)
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('GenAI Weekly Digest', html)
        self.assertIn('Thank you for confirming', html)
        self.assertIn('Welcome to the GenAI community', html)
    
    def test_generate_error_page(self):
        """Test generation of error page HTML."""
        error_message = 'Test error message'
        html = self.get_error_html(error_message)
        
        self.assertIn('Verification Error', html)
        self.assertIn(error_message, html)
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('GenAI Weekly Digest', html)
        self.assertIn('Verification Failed', html)
    
    def test_success_page_contains_required_elements(self):
        """Test that success page contains all required elements."""
        email = 'test@example.com'
        html = self.get_success_html(email)
        
        # Check for key elements
        self.assertIn('✅', html)  # Success icon
        self.assertIn('verified', html.lower())
        self.assertIn('welcome', html.lower())
        self.assertIn('weekly digest', html.lower())
        
        # Check for proper HTML structure
        self.assertIn('<head>', html)
        self.assertIn('<body>', html)
        self.assertIn('<style>', html)
        self.assertIn('viewport', html)
    
    def test_error_page_contains_required_elements(self):
        """Test that error page contains all required elements."""
        error_message = 'Token expired'
        html = self.get_error_html(error_message)
        
        # Check for key elements
        self.assertIn('❌', html)  # Error icon
        self.assertIn('error', html.lower())
        self.assertIn('failed', html.lower())
        self.assertIn(error_message, html)
        
        # Check for proper HTML structure
        self.assertIn('<head>', html)
        self.assertIn('<body>', html)
        self.assertIn('<style>', html)
        self.assertIn('viewport', html)


if __name__ == '__main__':
    unittest.main() 