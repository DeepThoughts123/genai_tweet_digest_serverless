"""
Lambda function for handling email verification.
Triggered by API Gateway GET requests to /verify endpoint.
"""

import json
import sys
import os

# Add the shared directory to the Python path
# sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared')) # Removed for Lambda packaging

from shared.email_verification_service import EmailVerificationService
from shared.config import config

def lambda_handler(event, context):
    """
    Handle email verification requests from API Gateway.
    
    Expected event structure:
    {
        "queryStringParameters": {
            "token": "verification-token-uuid"
        }
    }
    """
    
    # CORS headers
    headers = {
        'Content-Type': 'text/html',
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
        
        # Validate environment variables
        if not config.validate_required_env_vars():
            return {
                'statusCode': 500,
                'headers': headers,
                'body': get_error_html('Server configuration error')
            }
        
        # Get verification token from query parameters
        query_params = event.get('queryStringParameters') or {}
        verification_token = query_params.get('token')
        
        if not verification_token:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': get_error_html('Verification token is required')
            }
        
        # Verify the email
        verification_service = EmailVerificationService()
        result = verification_service.verify_email(verification_token)
        
        if result['success']:
            return {
                'statusCode': 200,
                'headers': headers,
                'body': get_success_html(result['email'])
            }
        else:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': get_error_html(result['message'])
            }
    
    except Exception as e:
        print(f"Error in verification handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': get_error_html('Internal server error')
        }

def get_success_html(email: str) -> str:
    """Generate success HTML page."""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Email Verified - GenAI Weekly Digest</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 600px;
                margin: 50px auto;
                background: white;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                text-align: center;
            }}
            .success-icon {{
                font-size: 64px;
                color: #4CAF50;
                margin-bottom: 20px;
            }}
            h1 {{
                color: #333;
                margin-bottom: 20px;
            }}
            p {{
                color: #666;
                margin-bottom: 15px;
            }}
            .email {{
                background-color: #f8f9fa;
                padding: 10px;
                border-radius: 4px;
                font-family: monospace;
                color: #333;
                margin: 20px 0;
            }}
            .next-steps {{
                background-color: #e3f2fd;
                padding: 20px;
                border-radius: 4px;
                margin-top: 30px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="success-icon">✅</div>
            <h1>Email Verified Successfully!</h1>
            <p>Thank you for confirming your subscription to the GenAI Weekly Digest.</p>
            
            <div class="email">{email}</div>
            
            <div class="next-steps">
                <h3>What's Next?</h3>
                <p>🎉 You're all set! You'll receive your first digest on the next scheduled delivery (Sundays at 9 AM UTC).</p>
                <p>📧 Each week, you'll get a curated summary of the latest developments in Generative AI.</p>
                <p>🔗 You can unsubscribe at any time using the link in any digest email.</p>
            </div>
            
            <p style="margin-top: 30px; font-size: 14px; color: #888;">
                Welcome to the GenAI community! 🚀
            </p>
        </div>
    </body>
    </html>
    """

def get_error_html(error_message: str) -> str:
    """Generate error HTML page."""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Verification Error - GenAI Weekly Digest</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 600px;
                margin: 50px auto;
                background: white;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                text-align: center;
            }}
            .error-icon {{
                font-size: 64px;
                color: #f44336;
                margin-bottom: 20px;
            }}
            h1 {{
                color: #333;
                margin-bottom: 20px;
            }}
            p {{
                color: #666;
                margin-bottom: 15px;
            }}
            .error-message {{
                background-color: #ffebee;
                padding: 15px;
                border-radius: 4px;
                color: #c62828;
                margin: 20px 0;
            }}
            .help-section {{
                background-color: #f8f9fa;
                padding: 20px;
                border-radius: 4px;
                margin-top: 30px;
            }}
            .retry-button {{
                display: inline-block;
                background-color: #2196F3;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 4px;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="error-icon">❌</div>
            <h1>Verification Failed</h1>
            
            <div class="error-message">{error_message}</div>
            
            <div class="help-section">
                <h3>Need Help?</h3>
                <p>If your verification link has expired or you're having trouble, you can:</p>
                <ul style="text-align: left; display: inline-block;">
                    <li>Try subscribing again to get a new verification email</li>
                    <li>Check your spam/junk folder for the verification email</li>
                    <li>Make sure you're clicking the complete link from the email</li>
                </ul>
                
                <a href="/" class="retry-button">Go Back to Subscribe</a>
            </div>
        </div>
    </body>
    </html>
    """ 