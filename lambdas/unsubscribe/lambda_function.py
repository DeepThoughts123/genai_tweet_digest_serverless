import json
import os
from shared.config import config
from shared.unsubscribe_service import UnsubscribeService

def lambda_handler(event, context):
    """
    Handle unsubscribe requests
    
    Expected event format:
    {
        "httpMethod": "GET",
        "queryStringParameters": {
            "email": "user@example.com"
        }
    }
    """
    try:
        # Validate configuration
        config.validate_required_env_vars()
        
        # Extract email from query parameters
        query_params = event.get('queryStringParameters') or {}
        email = query_params.get('email')
        token = query_params.get('token')
        
        if not email and not token:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'text/html',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS'
                },
                'body': generate_error_page("Missing email or token parameter")
            }
        
        # Initialize unsubscribe service
        unsubscribe_service = UnsubscribeService()
        
        # If token provided, decode it to get email
        if token and not email:
            email = unsubscribe_service.decode_unsubscribe_token(token)
            if not email:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'text/html',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Access-Control-Allow-Methods': 'GET, OPTIONS'
                    },
                    'body': generate_error_page("Invalid unsubscribe token")
                }
        
        # Perform unsubscribe
        result = unsubscribe_service.unsubscribe_email(email)
        
        if result['success']:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'text/html',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS'
                },
                'body': generate_success_page(email)
            }
        else:
            return {
                'statusCode': result['status_code'],
                'headers': {
                    'Content-Type': 'text/html',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS'
                },
                'body': generate_error_page(result['message'])
            }
            
    except Exception as e:
        print(f"Error in unsubscribe handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'text/html',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET, OPTIONS'
            },
            'body': generate_error_page("Server configuration error")
        }

def generate_success_page(email):
    """Generate HTML success page for unsubscribe"""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Unsubscribed - GenAI Weekly Digest</title>
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
            .info-section {{
                background-color: #e3f2fd;
                padding: 20px;
                border-radius: 4px;
                margin-top: 30px;
            }}
            .resubscribe-button {{
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
            <div class="success-icon">✅</div>
            <h1>Successfully Unsubscribed</h1>
            <p>You have been unsubscribed from the GenAI Weekly Digest.</p>
            
            <div class="email">{email}</div>
            
            <div class="info-section">
                <h3>What This Means</h3>
                <p>📧 You will no longer receive weekly digest emails from us.</p>
                <p>🔒 Your email has been marked as inactive in our system.</p>
                <p>💡 You can resubscribe at any time if you change your mind.</p>
            </div>
            
            <p style="margin-top: 30px; font-size: 14px; color: #888;">
                Thank you for being part of the GenAI community! 🚀
            </p>
        </div>
    </body>
    </html>
    """

def generate_error_page(error_message):
    """Generate HTML error page for unsubscribe failures"""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Unsubscribe Error - GenAI Weekly Digest</title>
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
            .contact-button {{
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
            <h1>Unsubscribe Failed</h1>
            
            <div class="error-message">{error_message}</div>
            
            <div class="help-section">
                <h3>Need Help?</h3>
                <p>If you're having trouble unsubscribing, you can:</p>
                <ul style="text-align: left; display: inline-block;">
                    <li>Check that you're using the correct email address</li>
                    <li>Make sure you're clicking the complete link from the email</li>
                    <li>Try again in a few minutes</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """ 