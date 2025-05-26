"""
Lambda function for handling email subscriptions.
Triggered by API Gateway POST requests.
"""

import json
import sys
import os

# Add the shared directory to the Python path
# sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared')) # Removed for Lambda packaging

from shared.dynamodb_service import SubscriberService, validate_email
from shared.config import config

def lambda_handler(event, context):
    """
    Handle subscription requests from API Gateway.
    
    Expected event structure:
    {
        "body": "{\"email\": \"user@example.com\"}"
    }
    """
    
    # CORS headers
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
    }
    
    try:
        # Handle preflight OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight'})
            }
        
        # Validate environment variables
        if not config.validate_required_env_vars():
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Server configuration error'
                })
            }
        
        # Parse request body
        if not event.get('body'):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Request body is required'
                })
            }
        
        try:
            body = json.loads(event['body'])
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Invalid JSON in request body'
                })
            }
        
        # Validate email
        email = body.get('email', '').strip().lower()
        if not email:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Email is required'
                })
            }
        
        if not validate_email(email):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': 'Invalid email format'
                })
            }
        
        # Add subscriber
        subscriber_service = SubscriberService()
        result = subscriber_service.add_subscriber(email)
        
        if result['success']:
            return {
                'statusCode': 201,
                'headers': headers,
                'body': json.dumps({
                    'success': True,
                    'message': 'Successfully subscribed to GenAI Weekly Digest!',
                    'subscriber_id': result['subscriber_id']
                })
            }
        else:
            # Email already exists
            return {
                'statusCode': 409,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': result['message']
                })
            }
    
    except Exception as e:
        print(f"Error in subscription handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'success': False,
                'message': 'Internal server error'
            })
        }

def get_subscriber_count_handler(event, context):
    """
    Handle requests to get subscriber count.
    Separate function for GET requests.
    """
    
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, OPTIONS'
    }
    
    try:
        # Handle preflight OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight'})
            }
        
        subscriber_service = SubscriberService()
        count = subscriber_service.get_subscriber_count()
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'subscriber_count': count
            })
        }
    
    except Exception as e:
        print(f"Error getting subscriber count: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'success': False,
                'message': 'Internal server error'
            })
        } 