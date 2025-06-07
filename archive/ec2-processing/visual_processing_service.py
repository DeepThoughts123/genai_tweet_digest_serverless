#!/usr/bin/env python3
"""
EC2 Visual Tweet Processing Service

Production service that runs on EC2 instances to perform long-running
visual tweet capture, text extraction, and categorization.

Adapted from exploration/integrated_tweet_pipeline.py for production EC2 execution.
"""

import sys
import os
import argparse
import json
import logging
import boto3
from datetime import datetime
from pathlib import Path
import time
import traceback

# Add shared directory to path
sys.path.append('/opt/visual-processing/shared')

# Import required services
try:
    from tweet_services import TweetFetcher
    from visual_tweet_capture_service import VisualTweetCaptureService
except ImportError as e:
    print(f"Failed to import required services: {e}")
    print("Make sure shared services are available in /opt/visual-processing/shared/")
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/visual-processing.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class EC2VisualProcessingService:
    """
    Production visual processing service for EC2 execution.
    """
    
    def __init__(self, s3_bucket, output_dir="/tmp/visual-processing"):
        """Initialize the EC2 processing service."""
        self.s3_bucket = s3_bucket
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize AWS clients
        self.s3_client = boto3.client('s3')
        self.sns_client = boto3.client('sns')
        
        # Initialize processing services
        self.tweet_fetcher = None
        self.visual_capturer = None
        
        logger.info(f"EC2 Visual Processing Service initialized")
        logger.info(f"S3 Bucket: {s3_bucket}")
        logger.info(f"Output Directory: {self.output_dir}")
    
    def initialize_services(self):
        """Initialize all required processing services."""
        logger.info("Initializing processing services...")
        
        try:
            # Initialize tweet fetcher
            self.tweet_fetcher = TweetFetcher()
            logger.info("✅ Tweet fetcher initialized")
            
            # Initialize visual capturer with S3 integration
            self.visual_capturer = VisualTweetCaptureService(
                s3_bucket=self.s3_bucket,
                zoom_percent=60,  # Will be overridden by parameters
                max_browser_retries=3,
                retry_delay=2.0,
                retry_backoff=2.0
            )
            logger.info("✅ Visual capturer initialized")
            
            logger.info("✅ All services initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def process_accounts(self, accounts, days_back=7, max_tweets=20, zoom_percent=60, processing_mode='visual_capture'):
        """Process visual capture for specified accounts."""
        logger.info(f"🚀 Starting visual processing for {len(accounts)} accounts")
        logger.info(f"📋 Configuration: {days_back} days back, {max_tweets} tweets per account, {zoom_percent}% zoom")
        
        results = {
            'job_id': f"ec2-visual-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'start_time': datetime.now().isoformat(),
            'accounts_processed': [],
            'total_accounts': len(accounts),
            'total_captures': 0,
            'success_rate': 0.0,
            'errors': []
        }
        
        successful_accounts = 0
        total_captures = 0
        
        for i, account in enumerate(accounts, 1):
            logger.info(f"\n📸 Processing account {i}/{len(accounts)}: @{account}")
            
            try:
                # Process visual capture for this account
                account_result = self.process_single_account(
                    account_name=account,
                    days_back=days_back,
                    max_tweets=max_tweets,
                    zoom_percent=zoom_percent
                )
                
                if account_result['success']:
                    successful_accounts += 1
                    total_captures += account_result['total_items_captured']
                    logger.info(f"✅ @{account}: {account_result['total_items_captured']} items captured")
                else:
                    logger.error(f"❌ @{account}: {account_result['error']}")
                    results['errors'].append({
                        'account': account,
                        'error': account_result['error']
                    })
                
                results['accounts_processed'].append({
                    'account': account,
                    'success': account_result['success'],
                    'items_captured': account_result.get('total_items_captured', 0),
                    'processing_time': account_result.get('processing_time', 0)
                })
                
                # Small delay between accounts to be respectful
                if i < len(accounts):
                    time.sleep(5)
                    
            except Exception as e:
                logger.error(f"❌ Error processing @{account}: {e}")
                logger.error(traceback.format_exc())
                results['errors'].append({
                    'account': account,
                    'error': str(e)
                })
        
        # Calculate final statistics
        results['end_time'] = datetime.now().isoformat()
        results['successful_accounts'] = successful_accounts
        results['total_captures'] = total_captures
        results['success_rate'] = successful_accounts / len(accounts) if accounts else 0.0
        
        # Save results to S3
        self.save_results_to_s3(results)
        
        logger.info(f"\n🎉 Processing Complete!")
        logger.info(f"✅ Successfully processed: {successful_accounts}/{len(accounts)} accounts")
        logger.info(f"📊 Total captures: {total_captures}")
        logger.info(f"📈 Success rate: {results['success_rate']:.1%}")
        
        return results
    
    def process_single_account(self, account_name, days_back, max_tweets, zoom_percent):
        """Process visual capture for a single account."""
        start_time = time.time()
        
        try:
            # Use the visual capture service
            result = self.visual_capturer.capture_account_content(
                account_name=account_name,
                days_back=days_back,
                max_tweets=max_tweets
            )
            
            processing_time = time.time() - start_time
            result['processing_time'] = processing_time
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error processing @{account_name}: {e}")
            return {
                'success': False,
                'account': account_name,
                'error': str(e),
                'processing_time': processing_time
            }
    
    def save_results_to_s3(self, results):
        """Save processing results to S3."""
        try:
            # Save detailed results
            results_key = f"visual-processing/results/{results['job_id']}/processing_results.json"
            
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=results_key,
                Body=json.dumps(results, indent=2, default=str),
                ContentType='application/json'
            )
            
            # Save completion marker
            completion_key = f"visual-processing/status/{results['job_id']}/processing_complete.json"
            completion_data = {
                'job_id': results['job_id'],
                'completion_time': datetime.now().isoformat(),
                'success': results['success_rate'] > 0.5,  # Consider successful if >50% accounts processed
                'total_accounts': results['total_accounts'],
                'successful_accounts': results['successful_accounts'],
                'total_captures': results['total_captures']
            }
            
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=completion_key,
                Body=json.dumps(completion_data, indent=2, default=str),
                ContentType='application/json'
            )
            
            logger.info(f"📁 Results saved to S3:")
            logger.info(f"   Results: s3://{self.s3_bucket}/{results_key}")
            logger.info(f"   Completion: s3://{self.s3_bucket}/{completion_key}")
            
        except Exception as e:
            logger.error(f"Error saving results to S3: {e}")
    
    def send_notification(self, topic_arn, results):
        """Send processing completion notification."""
        if not topic_arn:
            return
            
        try:
            message = {
                'job_id': results['job_id'],
                'status': 'completed',
                'accounts_processed': results['successful_accounts'],
                'total_accounts': results['total_accounts'],
                'total_captures': results['total_captures'],
                'success_rate': f"{results['success_rate']:.1%}",
                'processing_time': results.get('processing_time', 'unknown')
            }
            
            self.sns_client.publish(
                TopicArn=topic_arn,
                Subject='Visual Tweet Processing Complete',
                Message=json.dumps(message, indent=2)
            )
            
            logger.info("📧 Notification sent successfully")
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")

def main():
    """Main function for EC2 visual processing."""
    parser = argparse.ArgumentParser(
        description="EC2 Visual Tweet Processing Service",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--accounts',
        nargs='+',
        required=True,
        help='Twitter account usernames to process (without @)'
    )
    
    parser.add_argument(
        '--days-back',
        type=int,
        default=7,
        help='Number of days back to search for tweets'
    )
    
    parser.add_argument(
        '--max-tweets',
        type=int,
        default=20,
        help='Maximum number of tweets per account'
    )
    
    parser.add_argument(
        '--zoom',
        type=int,
        default=60,
        help='Browser zoom percentage for screenshots'
    )
    
    parser.add_argument(
        '--s3-bucket',
        required=True,
        help='S3 bucket for storing results'
    )
    
    parser.add_argument(
        '--processing-mode',
        default='visual_capture',
        help='Processing mode (for future expansion)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='/tmp/visual-processing',
        help='Local output directory for temporary files'
    )
    
    parser.add_argument(
        '--sns-topic-arn',
        help='SNS topic ARN for notifications'
    )
    
    args = parser.parse_args()
    
    logger.info("🚀 EC2 Visual Tweet Processing Starting")
    logger.info(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"👥 Accounts: {', '.join(['@' + acc for acc in args.accounts])}")
    logger.info(f"📊 Configuration: {args.days_back} days, {args.max_tweets} tweets/account, {args.zoom}% zoom")
    
    try:
        # Initialize processing service
        service = EC2VisualProcessingService(
            s3_bucket=args.s3_bucket,
            output_dir=args.output_dir
        )
        
        # Initialize services
        if not service.initialize_services():
            logger.error("❌ Service initialization failed")
            sys.exit(1)
        
        # Process accounts
        results = service.process_accounts(
            accounts=args.accounts,
            days_back=args.days_back,
            max_tweets=args.max_tweets,
            zoom_percent=args.zoom,
            processing_mode=args.processing_mode
        )
        
        # Send notification if SNS topic provided
        if args.sns_topic_arn:
            service.send_notification(args.sns_topic_arn, results)
        
        # Determine exit code based on success rate
        if results['success_rate'] >= 0.5:  # 50% success rate threshold
            logger.info("✅ Processing completed successfully")
            sys.exit(0)
        else:
            logger.error("❌ Processing completed with low success rate")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️ Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error in processing: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 