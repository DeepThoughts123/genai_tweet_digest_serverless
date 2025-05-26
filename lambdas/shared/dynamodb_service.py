"""
DynamoDB service for managing subscribers.
Replaces the SQLAlchemy database models with serverless DynamoDB.
"""

import boto3
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError
from .config import config

class SubscriberService:
    """Manage subscribers in DynamoDB."""
    
    def __init__(self):
        self.dynamodb = config.dynamodb
        self.table_name = config.subscribers_table
        self.table = self.dynamodb.Table(self.table_name)
    
    def add_subscriber(self, email: str) -> Dict[str, Any]:
        """Add a new subscriber to DynamoDB."""
        # Check if email already exists
        if self.email_exists(email):
            return {
                'success': False,
                'message': 'Email already subscribed',
                'subscriber_id': None
            }
        
        # Generate unique subscriber ID
        subscriber_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        try:
            # Add to DynamoDB
            self.table.put_item(
                Item={
                    'subscriber_id': subscriber_id,
                    'email': email,
                    'subscribed_at': timestamp,
                    'status': 'active',
                    'created_at': timestamp,
                    'updated_at': timestamp
                }
            )
            
            return {
                'success': True,
                'message': 'Successfully subscribed',
                'subscriber_id': subscriber_id
            }
            
        except ClientError as e:
            print(f"Error adding subscriber: {e}")
            return {
                'success': False,
                'message': 'Failed to subscribe',
                'subscriber_id': None
            }
    
    def email_exists(self, email: str) -> bool:
        """Check if email already exists in the database."""
        try:
            response = self.table.scan(
                FilterExpression='email = :email',
                ExpressionAttributeValues={':email': email}
            )
            return len(response['Items']) > 0
        except ClientError:
            return False
    
    def get_all_active_subscribers(self) -> List[str]:
        """Get all active subscriber emails."""
        try:
            response = self.table.scan(
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': 'active'}
            )
            
            return [item['email'] for item in response['Items']]
            
        except ClientError as e:
            print(f"Error fetching subscribers: {e}")
            return []
    
    def get_subscriber_count(self) -> int:
        """Get total count of active subscribers."""
        try:
            response = self.table.scan(
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': 'active'},
                Select='COUNT'
            )
            return response['Count']
        except ClientError:
            return 0
    
    def unsubscribe(self, subscriber_id: str) -> bool:
        """Unsubscribe a user by setting status to inactive."""
        try:
            self.table.update_item(
                Key={'subscriber_id': subscriber_id},
                UpdateExpression='SET #status = :status, updated_at = :updated_at',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'inactive',
                    ':updated_at': datetime.now().isoformat()
                }
            )
            return True
        except ClientError as e:
            print(f"Error unsubscribing user: {e}")
            return False
    
    def get_subscriber_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get subscriber details by email."""
        try:
            response = self.table.scan(
                FilterExpression='email = :email',
                ExpressionAttributeValues={':email': email}
            )
            
            if response['Items']:
                return response['Items'][0]
            return None
            
        except ClientError as e:
            print(f"Error fetching subscriber: {e}")
            return None

def validate_email(email: str) -> bool:
    """Simple email validation."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None 