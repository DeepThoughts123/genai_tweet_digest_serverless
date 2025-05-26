"""
Simplified Amazon SES email service for Lambda functions.
Removes multi-provider complexity and focuses on SES only.
"""

import boto3
from typing import List, Dict, Any
from datetime import datetime
from botocore.exceptions import ClientError
from .config import config
from .unsubscribe_service import UnsubscribeService

class SESEmailService:
    """Simplified email service using Amazon SES."""
    
    def __init__(self):
        self.ses_client = config.ses_client
        self.from_email = config.from_email
        self.unsubscribe_service = UnsubscribeService()
    
    def send_digest_email(self, digest_data: Dict[str, Any], subscribers: List[str], subject: str) -> Dict[str, Any]:
        """Send digest email to all subscribers."""
        if not subscribers:
            return {
                'success': True,
                'message': 'No subscribers to send to',
                'emails_sent': 0,
                'failed_emails': []
            }
        
        # Generate HTML content
        html_content = self._generate_html_content(digest_data)
        text_content = self._generate_text_content(digest_data)
        
        sent_count = 0
        failed_emails = []
        
        # Send to each subscriber individually
        for email in subscribers:
            try:
                # Generate personalized content with unsubscribe link
                personalized_html = self._add_unsubscribe_link(html_content, email)
                personalized_text = self._add_unsubscribe_link_text(text_content, email)
                
                self._send_single_email(
                    to_email=email,
                    subject=subject,
                    html_content=personalized_html,
                    text_content=personalized_text
                )
                sent_count += 1
            except Exception as e:
                print(f"Failed to send email to {email}: {e}")
                failed_emails.append({
                    'email': email,
                    'error': str(e)
                })
        
        return {
            'success': True,
            'message': f'Sent {sent_count} emails successfully',
            'emails_sent': sent_count,
            'total_subscribers': len(subscribers),
            'failed_emails': failed_emails,
            'sent_at': datetime.now().isoformat()
        }
    
    def _send_single_email(self, to_email: str, subject: str, html_content: str, text_content: str) -> None:
        """Send email to a single recipient."""
        try:
            response = self.ses_client.send_email(
                Source=self.from_email,
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Html': {'Data': html_content, 'Charset': 'UTF-8'},
                        'Text': {'Data': text_content, 'Charset': 'UTF-8'}
                    }
                }
            )
            print(f"Email sent successfully to {to_email}. Message ID: {response['MessageId']}")
        except ClientError as e:
            print(f"Error sending email to {to_email}: {e}")
            raise
    
    def _generate_html_content(self, digest_data: Dict[str, Any]) -> str:
        """Generate HTML email content."""
        summaries = digest_data.get('summaries', {})
        total_tweets = digest_data.get('total_tweets', 0)
        generated_at = digest_data.get('generated_at', datetime.now().isoformat())
        
        # Parse date for display
        try:
            date_obj = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
            formatted_date = date_obj.strftime("%B %d, %Y")
        except:
            formatted_date = "Recent"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>GenAI Weekly Digest</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px; margin-bottom: 30px; }}
                .header h1 {{ margin: 0; font-size: 28px; font-weight: 600; }}
                .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
                .category {{ margin-bottom: 30px; padding: 20px; border-left: 4px solid #667eea; background: #f8f9fa; border-radius: 0 8px 8px 0; }}
                .category h2 {{ color: #667eea; margin-top: 0; font-size: 20px; }}
                .category p {{ margin-bottom: 10px; }}
                .tweet-count {{ color: #666; font-size: 14px; font-style: italic; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 14px; border-top: 1px solid #eee; margin-top: 30px; }}
                .stats {{ background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🤖 GenAI Weekly Digest</h1>
                <p>Your curated summary of the latest in Generative AI</p>
            </div>
            
            <div class="stats">
                <strong>{total_tweets} tweets analyzed</strong> from top AI researchers and companies
            </div>
        """
        
        # Add category summaries
        for category, data in summaries.items():
            tweet_count = data.get('tweet_count', 0)
            summary = data.get('summary', '')
            
            html += f"""
            <div class="category">
                <h2>{category}</h2>
                <p>{summary}</p>
                <div class="tweet-count">Based on {tweet_count} tweet{'s' if tweet_count != 1 else ''}</div>
            </div>
            """
        
        html += f"""
            <div class="footer">
                <p>Generated on {formatted_date}</p>
                <p>This digest was automatically curated from tweets by leading AI researchers and organizations.</p>
                <!-- Unsubscribe link will be added here -->
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generate_text_content(self, digest_data: Dict[str, Any]) -> str:
        """Generate plain text email content."""
        summaries = digest_data.get('summaries', {})
        total_tweets = digest_data.get('total_tweets', 0)
        
        text = f"""GenAI Weekly Digest
        
{total_tweets} tweets analyzed from top AI researchers and companies

"""
        
        for category, data in summaries.items():
            tweet_count = data.get('tweet_count', 0)
            summary = data.get('summary', '')
            
            text += f"""{category.upper()}
{summary}
(Based on {tweet_count} tweet{'s' if tweet_count != 1 else ''})

"""
        
        text += """
This digest was automatically curated from tweets by leading AI researchers and organizations.

<!-- Unsubscribe link will be added here -->
"""
        
        return text
    
    def _add_unsubscribe_link(self, html_content: str, email: str) -> str:
        """Add unsubscribe link to HTML content."""
        # Get the API Gateway URL from environment or config
        api_base_url = config.get_api_base_url()
        unsubscribe_token = self.unsubscribe_service.get_unsubscribe_token(email)
        unsubscribe_url = f"{api_base_url}/unsubscribe?token={unsubscribe_token}"
        
        unsubscribe_html = f"""
                <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee;">
                    <p style="font-size: 12px; color: #888;">
                        Don't want to receive these emails? 
                        <a href="{unsubscribe_url}" style="color: #667eea;">Unsubscribe here</a>
                    </p>
                </div>"""
        
        # Replace the placeholder comment
        return html_content.replace("<!-- Unsubscribe link will be added here -->", unsubscribe_html)
    
    def _add_unsubscribe_link_text(self, text_content: str, email: str) -> str:
        """Add unsubscribe link to text content."""
        # Get the API Gateway URL from environment or config
        api_base_url = config.get_api_base_url()
        unsubscribe_token = self.unsubscribe_service.get_unsubscribe_token(email)
        unsubscribe_url = f"{api_base_url}/unsubscribe?token={unsubscribe_token}"
        
        unsubscribe_text = f"""
Don't want to receive these emails? Unsubscribe here: {unsubscribe_url}
"""
        
        # Replace the placeholder comment
        return text_content.replace("<!-- Unsubscribe link will be added here -->", unsubscribe_text) 