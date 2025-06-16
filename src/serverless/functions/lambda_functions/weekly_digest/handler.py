"""
Lambda function for generating and sending weekly digest.
Triggered by EventBridge on a weekly schedule.
"""

import json
import sys
import os
from datetime import datetime

# Add the src directory to the Python path for local development
# sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.shared.tweet_services import TweetFetcher, TweetCategorizer, TweetSummarizer, S3DataManager
from src.shared.dynamodb_service import SubscriberService
from src.shared.ses_service import SESEmailService
from src.shared.config import config

def lambda_handler(event, context):
    """
    Main handler for weekly digest generation and distribution.
    
    This function:
    1. Fetches tweets from influential accounts
    2. Categorizes tweets using Gemini
    3. Generates summaries by category
    4. Sends digest emails to all subscribers
    5. Saves data to S3 for portability
    """
    
    print("Starting weekly digest generation...")
    
    try:
        # Validate environment variables
        if not config.validate_required_env_vars():
            raise Exception("Missing required environment variables")
        
        # Initialize services
        tweet_fetcher = TweetFetcher()
        tweet_categorizer = TweetCategorizer()
        tweet_summarizer = TweetSummarizer()
        subscriber_service = SubscriberService()
        email_service = SESEmailService()
        s3_manager = S3DataManager()
        
        # Step 1: Fetch tweets from influential accounts
        print("Fetching tweets from influential accounts...")
        accounts = config.get_influential_accounts()
        print(f"Fetching from {len(accounts)} accounts: {accounts}")
        
        tweets = tweet_fetcher.fetch_tweets(accounts, days_back=7, max_tweets_per_user=10)
        print(f"Fetched {len(tweets)} tweets")
        
        if not tweets:
            print("No tweets fetched, skipping digest generation")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'skipped',
                    'reason': 'no_tweets',
                    'message': 'No tweets were fetched from the accounts'
                })
            }
        
        # Step 2: Categorize tweets
        print("Categorizing tweets...")
        categorized_tweets = tweet_categorizer.categorize_tweets(tweets)
        print(f"Categorized {len(categorized_tweets)} tweets")
        
        # Step 3: Generate summaries
        print("Generating summaries...")
        digest_data = tweet_summarizer.summarize_tweets(categorized_tweets)
        print(f"Generated summaries for {len(digest_data['summaries'])} categories")
        
        # Step 4: Get subscribers
        print("Getting subscriber list...")
        subscribers = subscriber_service.get_all_active_subscribers()
        print(f"Found {len(subscribers)} active subscribers")
        
        if not subscribers:
            print("No active subscribers found, skipping email distribution")
            # Still save data to S3 for record keeping
            s3_key = s3_manager.save_tweets(tweets, digest_data)
            print(f"Data saved to S3: {s3_key}")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'completed_no_subscribers',
                    'tweets_processed': len(tweets),
                    'categories_generated': len(digest_data['summaries']),
                    'subscribers': 0,
                    's3_key': s3_key
                })
            }
        
        # Step 5: Send digest emails
        print("Sending digest emails...")
        current_date = datetime.now().strftime("%B %d, %Y")
        subject = f"GenAI Weekly Digest - {current_date}"
        
        email_result = email_service.send_digest_email(
            digest_data=digest_data,
            subscribers=subscribers,
            subject=subject
        )
        
        print(f"Email sending completed: {email_result['emails_sent']} sent, {len(email_result['failed_emails'])} failed")
        
        # Step 6: Save data to S3 for portability
        print("Saving data to S3...")
        s3_key = s3_manager.save_tweets(tweets, digest_data)
        print(f"Data saved to S3: {s3_key}")
        
        # Prepare response
        response_data = {
            'status': 'success',
            'tweets_processed': len(tweets),
            'categories_generated': len(digest_data['summaries']),
            'email_result': email_result,
            's3_key': s3_key,
            'generated_at': digest_data['generated_at']
        }
        
        print("Weekly digest generation completed successfully")
        print(f"Summary: {len(tweets)} tweets → {len(digest_data['summaries'])} categories → {email_result['emails_sent']} emails sent")
        
        return {
            'statusCode': 200,
            'body': json.dumps(response_data, default=str)
        }
    
    except Exception as e:
        error_message = f"Error in weekly digest generation: {str(e)}"
        print(error_message)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'error': str(e),
                'message': 'Weekly digest generation failed'
            })
        }

def manual_trigger_handler(event, context):
    """
    Handler for manual digest generation (for testing).
    Can be triggered via API Gateway or directly.
    """
    
    print("Manual digest generation triggered")
    
    # Add some context to distinguish manual vs scheduled runs
    event['manual_trigger'] = True
    
    # Call the main handler
    result = lambda_handler(event, context)
    
    # Add manual trigger info to response
    if result.get('body'):
        body = json.loads(result['body'])
        body['trigger_type'] = 'manual'
        result['body'] = json.dumps(body, default=str)
    
    return result 