"""
Simple test cases for email verification service.
"""

import pytest
import boto3
import uuid
from datetime import datetime, timedelta
from moto import mock_aws
from unittest.mock import patch, MagicMock
import sys
import os

# Add the shared directory to the Python path for testing
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from src.shared.email_verification_service import EmailVerificationService
from src.shared.config import config

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
    
    def test_create_pending_subscriber_success(self):
        """Test creating a pending subscriber with verification email."""
        email = self.test_email
        
        with patch.object(config, 'dynamodb', self.dynamodb), \
             patch.object(config, 'subscribers_table', self.table_name), \
             patch.object(config, 'from_email', self.from_email), \
             patch.object(config, 'aws_region', 'us-east-1'):
            
            verification_service = EmailVerificationService()
            result = verification_service.create_pending_subscriber(email)
        
        # Check result
        assert result['success'] is True
        assert 'Verification email sent' in result['message']
        assert result['subscriber_id'] is not None
        assert result['verification_token'] is not None
    
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
            
            verification_service = EmailVerificationService()
            result = verification_service.verify_email(verification_token)
        
        # Check result
        assert result['success'] is True
        assert 'verified successfully' in result['message']
        assert result['email'] == email
    
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
            
            verification_service = EmailVerificationService()
            result = verification_service.verify_email(verification_token)
        
        # Check result
        assert result['success'] is False
        assert 'expired' in result['message']


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 