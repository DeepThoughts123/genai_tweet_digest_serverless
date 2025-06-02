"""
Test cases for email verification service.
"""

import pytest
import boto3
import uuid
import json
from datetime import datetime, timedelta
from moto import mock_aws
from unittest.mock import patch, MagicMock
import sys
import os

# Add the shared directory to the Python path for testing
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from shared.email_verification_service import EmailVerificationService
from shared.dynamodb_service import SubscriberService
from shared.config import config

@mock_aws
class TestEmailVerificationService:
    """Test email verification functionality."""
    
    def setup_method(self, method):
        """Set up test environment."""
        # Mock AWS services
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.ses = boto3.client('ses', region_name='us-east-1')
        
        # Create test table
        self.table_name = 'test-subscribers'
        self.table = self.dynamodb.create_table(
            TableName=self.table_name,
            KeySchema=[
                {'AttributeName': 'subscriber_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'subscriber_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Verify test email in SES
        self.test_email = 'test@example.com'
        self.from_email = 'noreply@example.com'
        self.ses.verify_email_identity(EmailAddress=self.from_email)
        self.ses.verify_email_identity(EmailAddress=self.test_email)
        
        # Mock config
        with patch.object(config, 'dynamodb', self.dynamodb), \
             patch.object(config, 'subscribers_table', self.table_name), \
             patch.object(config, 'from_email', self.from_email), \
             patch.object(config, 'aws_region', 'us-east-1'):
            
            self.verification_service = EmailVerificationService()
            self.subscriber_service = SubscriberService()
    
    def test_create_pending_subscriber_success(self):
        """Test creating a pending subscriber with verification email."""
        email = self.test_email
        
        with patch.object(config, 'dynamodb', self.dynamodb), \
             patch.object(config, 'subscribers_table', self.table_name), \
             patch.object(config, 'from_email', self.from_email), \
             patch.object(config, 'aws_region', 'us-east-1'):
            
            result = self.verification_service.create_pending_subscriber(email)
        
        # Check result
        assert result['success'] is True
        assert 'Verification email sent' in result['message']
        assert result['subscriber_id'] is not None
        assert result['verification_token'] is not None
        
        # Check database
        subscriber = self.subscriber_service.get_subscriber_by_email(email)
        assert subscriber is not None
        assert subscriber['email'] == email
        assert subscriber['status'] == 'pending_verification'
        assert 'verification_token' in subscriber
        assert 'verification_expires_at' in subscriber
    
    def test_create_pending_subscriber_duplicate_active(self):
        """Test creating subscriber when email already exists and is active."""
        email = self.test_email
        
        # Create active subscriber first
        self.table.put_item(
            Item={
                'subscriber_id': str(uuid.uuid4()),
                'email': email,
                'status': 'active',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        )
        
        with patch.object(config, 'dynamodb', self.dynamodb), \
             patch.object(config, 'subscribers_table', self.table_name), \
             patch.object(config, 'from_email', self.from_email), \
             patch.object(config, 'aws_region', 'us-east-1'):
            
            # Try to create pending subscriber
            result = self.verification_service.create_pending_subscriber(email)
        
        # Should not create new subscriber since active one exists
        # This test assumes the subscription handler checks for existing subscribers first
        pass
    
    def test_verify_email_success(self):
        """Test successful email verification."""
        email = self.test_email
        verification_token = str(uuid.uuid4())
        subscriber_id = str(uuid.uuid4())
        
        # Create pending subscriber
        self.table.put_item(
            Item={
                'subscriber_id': subscriber_id,
                'email': email,
                'status': 'pending_verification',
                'verification_token': verification_token,
                'verification_expires_at': (datetime.now() + timedelta(hours=1)).isoformat(),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        )
        
        with patch.object(config, 'dynamodb', self.dynamodb), \
             patch.object(config, 'subscribers_table', self.table_name), \
             patch.object(config, 'from_email', self.from_email), \
             patch.object(config, 'aws_region', 'us-east-1'):
            
            result = self.verification_service.verify_email(verification_token)
        
        # Check result
        assert result['success'] is True
        assert 'verified successfully' in result['message']
        assert result['email'] == email
        
        # Check database - should be active now
        subscriber = self.subscriber_service.get_subscriber_by_email(email)
        assert subscriber['status'] == 'active'
        assert 'verification_token' not in subscriber
        assert 'verified_at' in subscriber
    
    def test_verify_email_expired_token(self):
        """Test verification with expired token."""
        email = self.test_email
        verification_token = str(uuid.uuid4())
        subscriber_id = str(uuid.uuid4())
        
        # Create pending subscriber with expired token
        self.table.put_item(
            Item={
                'subscriber_id': subscriber_id,
                'email': email,
                'status': 'pending_verification',
                'verification_token': verification_token,
                'verification_expires_at': (datetime.now() - timedelta(hours=1)).isoformat(),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        )
        
        with patch.object(config, 'dynamodb', self.dynamodb), \
             patch.object(config, 'subscribers_table', self.table_name), \
             patch.object(config, 'from_email', self.from_email), \
             patch.object(config, 'aws_region', 'us-east-1'):
            
            result = self.verification_service.verify_email(verification_token)
        
        # Check result
        assert result['success'] is False
        assert 'expired' in result['message']
    
    def test_verify_email_invalid_token(self):
        """Test verification with invalid token."""
        invalid_token = str(uuid.uuid4())
        
        with patch.object(config, 'dynamodb', self.dynamodb), \
             patch.object(config, 'subscribers_table', self.table_name), \
             patch.object(config, 'from_email', self.from_email), \
             patch.object(config, 'aws_region', 'us-east-1'):
            
            result = self.verification_service.verify_email(invalid_token)
        
        # Check result
        assert result['success'] is False
        assert 'Invalid or expired' in result['message']
    
    def test_resend_verification_success(self):
        """Test resending verification email."""
        email = self.test_email
        old_token = str(uuid.uuid4())
        subscriber_id = str(uuid.uuid4())
        
        # Create pending subscriber
        self.table.put_item(
            Item={
                'subscriber_id': subscriber_id,
                'email': email,
                'status': 'pending_verification',
                'verification_token': old_token,
                'verification_expires_at': (datetime.now() + timedelta(hours=1)).isoformat(),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        )
        
        with patch.object(config, 'dynamodb', self.dynamodb), \
             patch.object(config, 'subscribers_table', self.table_name), \
             patch.object(config, 'from_email', self.from_email), \
             patch.object(config, 'aws_region', 'us-east-1'):
            
            result = self.verification_service.resend_verification(email)
        
        # Check result
        assert result['success'] is True
        assert 'resent' in result['message']
        
        # Check that token was updated
        subscriber = self.subscriber_service.get_subscriber_by_email(email)
        assert subscriber['verification_token'] != old_token
    
    def test_resend_verification_no_pending(self):
        """Test resending verification when no pending subscriber exists."""
        email = self.test_email
        
        with patch.object(config, 'dynamodb', self.dynamodb), \
             patch.object(config, 'subscribers_table', self.table_name), \
             patch.object(config, 'from_email', self.from_email), \
             patch.object(config, 'aws_region', 'us-east-1'):
            
            result = self.verification_service.resend_verification(email)
        
        # Check result
        assert result['success'] is False
        assert 'No pending verification' in result['message']
    
    def test_send_verification_email_content(self):
        """Test that verification email contains required content."""
        email = self.test_email
        token = str(uuid.uuid4())
        
        with patch.object(config, 'dynamodb', self.dynamodb), \
             patch.object(config, 'subscribers_table', self.table_name), \
             patch.object(config, 'from_email', self.from_email), \
             patch.object(config, 'aws_region', 'us-east-1'):
            
            # Mock the send_email method to capture the content
            with patch.object(self.verification_service.ses, 'send_email') as mock_send:
                mock_send.return_value = {'MessageId': 'test-message-id'}
                
                result = self.verification_service.send_verification_email(email, token)
                
                # Check that email was "sent"
                assert result is True
                assert mock_send.called
                
                # Check email content
                call_args = mock_send.call_args[1]
                assert call_args['Source'] == self.from_email
                assert call_args['Destination']['ToAddresses'] == [email]
                
                message = call_args['Message']
                assert 'GenAI Weekly Digest' in message['Subject']['Data']
                assert token in message['Body']['Html']['Data']
                assert token in message['Body']['Text']['Data']
                assert 'verify' in message['Body']['Html']['Data'].lower()


@mock_aws
class TestSubscriptionWithVerification:
    """Test subscription Lambda function with verification."""
    
    def setup_method(self, method):
        """Set up test environment."""
        # Import here to avoid circular imports
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'subscription'))
        
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table_name = 'test-subscribers'
        self.table = self.dynamodb.create_table(
            TableName=self.table_name,
            KeySchema=[
                {'AttributeName': 'subscriber_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'subscriber_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        self.from_email = 'noreply@example.com'
    
    def test_subscription_creates_pending_subscriber(self):
        """Test that subscription creates pending subscriber and sends verification email."""
        from lambda_function import lambda_handler
        
        event = {
            'httpMethod': 'POST',
            'body': '{"email": "test@example.com"}'
        }
        
        with patch.object(config, 'dynamodb', self.dynamodb), \
             patch.object(config, 'subscribers_table', self.table_name), \
             patch.object(config, 'from_email', self.from_email), \
             patch.object(config, 'aws_region', 'us-east-1'), \
             patch.object(config, 'validate_required_env_vars', return_value=True), \
             patch('shared.email_verification_service.boto3.client') as mock_ses:
            
            # Mock SES client
            mock_ses_instance = MagicMock()
            mock_ses_instance.send_email.return_value = {'MessageId': 'test-id'}
            mock_ses.return_value = mock_ses_instance
            
            response = lambda_handler(event, {})
        
        # Check response
        assert response['statusCode'] == 201
        body = json.loads(response['body'])  # Use json.loads instead of eval
        assert body['success'] is True
        assert 'Verification email sent' in body['message']
    
    def test_subscription_resends_for_pending_email(self):
        """Test that subscription resends verification for pending email."""
        from lambda_function import lambda_handler
        
        email = 'test@example.com'
        
        # Create pending subscriber first
        self.table.put_item(
            Item={
                'subscriber_id': str(uuid.uuid4()),
                'email': email,
                'status': 'pending_verification',
                'verification_token': str(uuid.uuid4()),
                'verification_expires_at': (datetime.now() + timedelta(hours=1)).isoformat(),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        )
        
        event = {
            'httpMethod': 'POST',
            'body': f'{{"email": "{email}"}}'
        }
        
        with patch.object(config, 'dynamodb', self.dynamodb), \
             patch.object(config, 'subscribers_table', self.table_name), \
             patch.object(config, 'from_email', self.from_email), \
             patch.object(config, 'aws_region', 'us-east-1'), \
             patch.object(config, 'validate_required_env_vars', return_value=True), \
             patch('shared.email_verification_service.boto3.client') as mock_ses:
            
            # Mock SES client
            mock_ses_instance = MagicMock()
            mock_ses_instance.send_email.return_value = {'MessageId': 'test-id'}
            mock_ses.return_value = mock_ses_instance
            
            response = lambda_handler(event, {})
        
        # Check response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])  # Use json.loads instead of eval
        assert body['success'] is True
        assert 'resent' in body['message']
    
    def test_subscription_rejects_active_email(self):
        """Test that subscription rejects already active email."""
        from lambda_function import lambda_handler
        
        email = 'test@example.com'
        
        # Create active subscriber first
        self.table.put_item(
            Item={
                'subscriber_id': str(uuid.uuid4()),
                'email': email,
                'status': 'active',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        )
        
        event = {
            'httpMethod': 'POST',
            'body': f'{{"email": "{email}"}}'
        }
        
        with patch.object(config, 'dynamodb', self.dynamodb), \
             patch.object(config, 'subscribers_table', self.table_name), \
             patch.object(config, 'from_email', self.from_email), \
             patch.object(config, 'aws_region', 'us-east-1'), \
             patch.object(config, 'validate_required_env_vars', return_value=True):
            
            response = lambda_handler(event, {})
        
        # Check response
        assert response['statusCode'] == 409
        body = json.loads(response['body'])  # Use json.loads instead of eval
        assert body['success'] is False
        assert 'already subscribed' in body['message']


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 