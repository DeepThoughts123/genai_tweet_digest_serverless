import boto3
import uuid
from datetime import datetime
from .config import config
from .dynamodb_service import SubscriberService

class UnsubscribeService:
    def __init__(self):
        self.subscriber_service = SubscriberService()
        
    def unsubscribe_email(self, email):
        """
        Unsubscribe an email address from the digest
        
        Args:
            email (str): Email address to unsubscribe
            
        Returns:
            dict: Result of unsubscribe operation
        """
        try:
            # Find the subscriber by email
            subscriber = self.subscriber_service.get_subscriber_by_email(email)
            
            if not subscriber or subscriber.get('status') != 'active':
                return {
                    'success': False,
                    'message': 'Email address not found or already unsubscribed',
                    'status_code': 404
                }
            
            # Update subscriber status to inactive using the existing unsubscribe method
            subscriber_id = subscriber['subscriber_id']
            success = self.subscriber_service.unsubscribe(subscriber_id)
            
            if success:
                return {
                    'success': True,
                    'message': 'Successfully unsubscribed from GenAI Weekly Digest',
                    'status_code': 200,
                    'subscriber_id': subscriber_id
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to unsubscribe. Please try again.',
                    'status_code': 500
                }
                
        except Exception as e:
            print(f"Error unsubscribing email {email}: {str(e)}")
            return {
                'success': False,
                'message': 'An error occurred while unsubscribing',
                'status_code': 500
            }
    
    def get_unsubscribe_token(self, email):
        """
        Generate an unsubscribe token for secure unsubscribe links
        
        Args:
            email (str): Email address
            
        Returns:
            str: Unsubscribe token
        """
        # For simplicity, we'll use email-based unsubscribe
        # In production, you might want to use encrypted tokens
        import base64
        return base64.urlsafe_b64encode(email.encode()).decode()
    
    def decode_unsubscribe_token(self, token):
        """
        Decode an unsubscribe token to get the email
        
        Args:
            token (str): Unsubscribe token
            
        Returns:
            str: Email address or None if invalid
        """
        try:
            import base64
            return base64.urlsafe_b64decode(token.encode()).decode()
        except Exception:
            return None 