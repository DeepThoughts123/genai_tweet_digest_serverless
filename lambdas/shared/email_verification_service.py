"""
Email verification service for double opt-in subscriptions.
"""

import boto3
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError
from .config import config

class EmailVerificationService:
    """Manage email verification for subscribers."""
    
    def __init__(self):
        self.dynamodb = config.dynamodb
        self.ses = boto3.client('ses', region_name=config.aws_region)
        self.table_name = config.subscribers_table
        self.table = self.dynamodb.Table(self.table_name)
        self.from_email = config.from_email
    
    def send_verification_email(self, email: str, verification_token: str) -> bool:
        """Send verification email to the subscriber."""
        
        # Create verification URL using the actual API Gateway URL
        verification_url = f"https://zjqk5961gc.execute-api.us-east-1.amazonaws.com/production/verify?token={verification_token}"
        
        # Email content
        subject = "Confirm your subscription to GenAI Weekly Digest"
        
        html_body = f"""
        <html>
        <head></head>
        <body>
            <h2>Welcome to GenAI Weekly Digest!</h2>
            <p>Thank you for subscribing to our weekly digest of the latest in Generative AI.</p>
            <p>To complete your subscription, please click the button below to verify your email address:</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}" 
                   style="background-color: #4CAF50; color: white; padding: 15px 32px; 
                          text-decoration: none; display: inline-block; border-radius: 4px; 
                          font-size: 16px;">
                    Verify Email Address
                </a>
            </div>
            
            <p>Or copy and paste this link into your browser:</p>
            <p><a href="{verification_url}">{verification_url}</a></p>
            
            <p>This verification link will expire in 24 hours.</p>
            
            <p>If you didn't subscribe to this newsletter, you can safely ignore this email.</p>
            
            <hr>
            <p style="font-size: 12px; color: #666;">
                GenAI Weekly Digest - Your weekly dose of AI insights
            </p>
        </body>
        </html>
        """
        
        text_body = f"""
        Welcome to GenAI Weekly Digest!
        
        Thank you for subscribing to our weekly digest of the latest in Generative AI.
        
        To complete your subscription, please visit this link to verify your email address:
        {verification_url}
        
        This verification link will expire in 24 hours.
        
        If you didn't subscribe to this newsletter, you can safely ignore this email.
        
        ---
        GenAI Weekly Digest - Your weekly dose of AI insights
        """
        
        try:
            response = self.ses.send_email(
                Source=self.from_email,
                Destination={'ToAddresses': [email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Text': {'Data': text_body, 'Charset': 'UTF-8'},
                        'Html': {'Data': html_body, 'Charset': 'UTF-8'}
                    }
                }
            )
            print(f"Verification email sent to {email}. MessageId: {response['MessageId']}")
            return True
            
        except ClientError as e:
            print(f"Error sending verification email: {e}")
            return False
    
    def create_pending_subscriber(self, email: str) -> Dict[str, Any]:
        """Create a pending subscriber with verification token."""
        
        # Generate verification token
        verification_token = str(uuid.uuid4())
        subscriber_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
        
        try:
            # Store with pending status
            self.table.put_item(
                Item={
                    'subscriber_id': subscriber_id,
                    'email': email,
                    'status': 'pending_verification',
                    'verification_token': verification_token,
                    'verification_expires_at': expires_at,
                    'subscribed_at': timestamp,
                    'created_at': timestamp,
                    'updated_at': timestamp
                }
            )
            
            # Send verification email
            email_sent = self.send_verification_email(email, verification_token)
            
            if email_sent:
                return {
                    'success': True,
                    'message': 'Verification email sent. Please check your inbox.',
                    'subscriber_id': subscriber_id,
                    'verification_token': verification_token
                }
            else:
                # Clean up if email failed
                self.table.delete_item(Key={'subscriber_id': subscriber_id})
                return {
                    'success': False,
                    'message': 'Failed to send verification email',
                    'subscriber_id': None
                }
                
        except ClientError as e:
            print(f"Error creating pending subscriber: {e}")
            return {
                'success': False,
                'message': 'Failed to process subscription',
                'subscriber_id': None
            }
    
    def verify_email(self, verification_token: str) -> Dict[str, Any]:
        """Verify email using the verification token."""
        
        try:
            # Find subscriber by verification token
            response = self.table.scan(
                FilterExpression='verification_token = :token AND #status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':token': verification_token,
                    ':status': 'pending_verification'
                }
            )
            
            if not response['Items']:
                return {
                    'success': False,
                    'message': 'Invalid or expired verification token'
                }
            
            subscriber = response['Items'][0]
            
            # Check if token has expired
            expires_at = datetime.fromisoformat(subscriber['verification_expires_at'])
            if datetime.now() > expires_at:
                return {
                    'success': False,
                    'message': 'Verification token has expired'
                }
            
            # Update subscriber status to active
            self.table.update_item(
                Key={'subscriber_id': subscriber['subscriber_id']},
                UpdateExpression='SET #status = :status, verified_at = :verified_at, updated_at = :updated_at REMOVE verification_token, verification_expires_at',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'active',
                    ':verified_at': datetime.now().isoformat(),
                    ':updated_at': datetime.now().isoformat()
                }
            )
            
            return {
                'success': True,
                'message': 'Email verified successfully! You are now subscribed.',
                'email': subscriber['email']
            }
            
        except ClientError as e:
            print(f"Error verifying email: {e}")
            return {
                'success': False,
                'message': 'Verification failed'
            }
    
    def resend_verification(self, email: str) -> Dict[str, Any]:
        """Resend verification email for pending subscribers."""
        
        try:
            # Find pending subscriber
            response = self.table.scan(
                FilterExpression='email = :email AND #status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':email': email,
                    ':status': 'pending_verification'
                }
            )
            
            if not response['Items']:
                return {
                    'success': False,
                    'message': 'No pending verification found for this email'
                }
            
            subscriber = response['Items'][0]
            
            # Generate new token and extend expiry
            new_token = str(uuid.uuid4())
            new_expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
            
            # Update with new token
            self.table.update_item(
                Key={'subscriber_id': subscriber['subscriber_id']},
                UpdateExpression='SET verification_token = :token, verification_expires_at = :expires, updated_at = :updated_at',
                ExpressionAttributeValues={
                    ':token': new_token,
                    ':expires': new_expires_at,
                    ':updated_at': datetime.now().isoformat()
                }
            )
            
            # Send new verification email
            email_sent = self.send_verification_email(email, new_token)
            
            if email_sent:
                return {
                    'success': True,
                    'message': 'Verification email resent. Please check your inbox.'
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to resend verification email'
                }
                
        except ClientError as e:
            print(f"Error resending verification: {e}")
            return {
                'success': False,
                'message': 'Failed to resend verification'
            } 