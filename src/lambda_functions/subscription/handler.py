"""
Lambda function for handling email subscriptions.
Triggered by API Gateway POST requests.
"""

import json
import sys
import os
import traceback

# Add the src directory to the Python path for local development
# sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.shared.dynamodb_service import SubscriberService, validate_email
from src.shared.email_verification_service import EmailVerificationService
from src.shared.config import config

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
        
        # Check if email already exists (active or pending)
        subscriber_service = SubscriberService()
        existing_subscriber = subscriber_service.get_subscriber_by_email(email)
        
        if existing_subscriber:
            if existing_subscriber['status'] == 'active':
                return {
                    'statusCode': 409,
                    'headers': headers,
                    'body': json.dumps({
                        'success': False,
                        'message': 'Email already subscribed to weekly digest'
                    })
                }
            elif existing_subscriber['status'] == 'pending_verification':
                # Resend verification email
                verification_service = EmailVerificationService()
                result = verification_service.resend_verification(email)
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'success': True,
                        'message': 'Verification email resent. Please check your inbox.'
                    })
                }
        
        # Create new pending subscriber with verification
        verification_service = EmailVerificationService()
        result = verification_service.create_pending_subscriber(email)
        
        if result['success']:
            return {
                'statusCode': 201,
                'headers': headers,
                'body': json.dumps({
                    'success': True,
                    'message': result['message'],
                    'subscriber_id': result['subscriber_id']
                })
            }
        else:
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'message': result['message']
                })
            }
    
    except Exception as e:
        print(f"Error in subscription handler: {str(e)}")
        traceback.print_exc()
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