#!/usr/bin/env python3
"""
Fargate Visual Tweet Processing Application

Long-running containerized service for visual tweet capture and processing.
This service handles the time-intensive browser automation tasks that exceed Lambda's 15-minute limit.

Key Features:
- Visual tweet screenshot capture using Selenium
- Text extraction from screenshots  
- AI-powered tweet categorization
- S3 integration for data storage
- CloudWatch logging and monitoring
"""

import sys
import os
import argparse
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import from shared libraries
sys.path.append('/app/src')
from src.shared.config import config
from src.shared.tweet_services import TweetFetcher
from src.shared.visual_tweet_capture_service import VisualTweetCaptureService
from src.shared.utils.logging import setup_logger

# Set up logging
logger = setup_logger(__name__, level="INFO")

class FargateVisualProcessor:
    """
    Main visual processing service for Fargate containers.
    """
    
    def __init__(self, output_dir: str = "/tmp/visual-processing"):
        """Initialize the visual processor."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Service instances
        self.tweet_fetcher = None
        self.visual_capture_service = None
        
        # Processing stats
        self.stats = {
            'tweets_fetched': 0,
            'screenshots_captured': 0,
            'screenshots_failed': 0,
            'start_time': None,
            'end_time': None
        }
        
        logger.info(f"Visual processor initialized with output directory: {self.output_dir}")
    
    def initialize_services(self) -> bool:
        """Initialize all required services."""
        logger.info("Initializing visual processing services...")
        
        try:
            # Validate environment variables
            if not config.validate_required_env_vars():
                raise Exception("Missing required environment variables")
            
            # Initialize tweet fetcher
            self.tweet_fetcher = TweetFetcher()
            logger.info("Tweet fetcher initialized")
            
            # Initialize visual capture service
            self.visual_capture_service = VisualTweetCaptureService()
            logger.info("Visual capture service initialized")
            
            logger.info("All services initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            return False
    
    def fetch_tweets(self, accounts: List[str], days_back: int = 7, max_tweets: int = 20) -> List[str]:
        """
        Fetch tweets from specified accounts.
        
        Args:
            accounts: List of Twitter account usernames
            days_back: Number of days to look back
            max_tweets: Maximum tweets per account
            
        Returns:
            List of tweet URLs
        """
        logger.info(f"Fetching tweets from {len(accounts)} accounts")
        logger.info(f"Accounts: {accounts}")
        logger.info(f"Days back: {days_back}, Max tweets per account: {max_tweets}")
        
        all_tweet_urls = []
        
        for account in accounts:
            logger.info(f"Fetching tweets for @{account}...")
            
            try:
                # Use the TweetFetcher to get tweets
                tweets = self.tweet_fetcher.fetch_tweets([account], days_back=days_back, max_tweets_per_user=max_tweets)
                
                # Extract URLs from tweet objects
                tweet_urls = []
                for tweet in tweets:
                    username = tweet.get('username', account)
                    tweet_id = tweet.get('id')
                    if tweet_id:
                        url = f"https://twitter.com/{username}/status/{tweet_id}"
                        tweet_urls.append(url)
                
                if tweet_urls:
                    logger.info(f"Found {len(tweet_urls)} tweets for @{account}")
                    all_tweet_urls.extend(tweet_urls)
                else:
                    logger.warning(f"No tweets found for @{account}")
                    
            except Exception as e:
                logger.error(f"Error fetching tweets for @{account}: {e}")
        
        self.stats['tweets_fetched'] = len(all_tweet_urls)
        logger.info(f"Total tweets to process: {len(all_tweet_urls)}")
        return all_tweet_urls
    
    def capture_tweet_visuals(self, tweet_urls: List[str], zoom_percent: int = 30) -> Dict[str, Any]:
        """
        Capture visual screenshots of tweets.
        
        Args:
            tweet_urls: List of tweet URLs to capture
            zoom_percent: Browser zoom level
            
        Returns:
            Results dictionary with success/failure counts
        """
        logger.info(f"Starting visual capture of {len(tweet_urls)} tweets")
        logger.info(f"Browser zoom level: {zoom_percent}%")
        
        captured_count = 0
        failed_count = 0
        results = []
        
        for i, tweet_url in enumerate(tweet_urls, 1):
            logger.info(f"Capturing tweet {i}/{len(tweet_urls)}: {tweet_url}")
            
            try:
                # Use the visual capture service
                result = self.visual_capture_service.capture_tweet(
                    tweet_url=tweet_url,
                    output_dir=str(self.output_dir),
                    zoom_percent=zoom_percent
                )
                
                if result and result.get('success'):
                    logger.info(f"Successfully captured tweet {i}")
                    logger.info(f"Output: {result.get('output_path', 'Unknown')}")
                    captured_count += 1
                    results.append({
                        'url': tweet_url,
                        'success': True,
                        'output_path': result.get('output_path'),
                        'metadata': result.get('metadata', {})
                    })
                else:
                    logger.warning(f"Failed to capture tweet {i}")
                    failed_count += 1
                    results.append({
                        'url': tweet_url,
                        'success': False,
                        'error': result.get('error', 'Unknown error')
                    })
                    
            except Exception as e:
                logger.error(f"Error capturing tweet {i}: {e}")
                failed_count += 1
                results.append({
                    'url': tweet_url,
                    'success': False,
                    'error': str(e)
                })
            
            # Small delay between captures to be respectful
            time.sleep(2)
        
        # Update stats
        self.stats['screenshots_captured'] = captured_count
        self.stats['screenshots_failed'] = failed_count
        
        logger.info(f"Visual capture completed:")
        logger.info(f"  Successfully captured: {captured_count}")
        logger.info(f"  Failed: {failed_count}")
        
        return {
            'total_processed': len(tweet_urls),
            'successful_captures': captured_count,
            'failed_captures': failed_count,
            'results': results
        }
    
    def upload_to_s3(self, s3_bucket: str, s3_prefix: str = None) -> bool:
        """
        Upload processing results to S3.
        
        Args:
            s3_bucket: S3 bucket name
            s3_prefix: Optional S3 prefix for organization
            
        Returns:
            Success status
        """
        logger.info(f"Uploading results to S3 bucket: {s3_bucket}")
        
        try:
            import boto3
            s3_client = boto3.client('s3')
            
            if s3_prefix is None:
                s3_prefix = f"visual-processing/{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
            
            # Upload all files in output directory
            uploaded_files = 0
            
            for file_path in self.output_dir.rglob('*'):
                if file_path.is_file():
                    # Calculate relative path
                    relative_path = file_path.relative_to(self.output_dir)
                    s3_key = f"{s3_prefix}/{relative_path}"
                    
                    # Upload file
                    s3_client.upload_file(str(file_path), s3_bucket, s3_key)
                    uploaded_files += 1
                    logger.debug(f"Uploaded: {s3_key}")
            
            logger.info(f"Successfully uploaded {uploaded_files} files to S3")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
            return False
    
    def generate_processing_report(self) -> Dict[str, Any]:
        """Generate a summary report of the processing run."""
        
        duration = None
        if self.stats['start_time'] and self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        report = {
            'processing_summary': {
                'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
                'end_time': self.stats['end_time'].isoformat() if self.stats['end_time'] else None,
                'duration_seconds': duration,
                'tweets_fetched': self.stats['tweets_fetched'],
                'screenshots_captured': self.stats['screenshots_captured'],
                'screenshots_failed': self.stats['screenshots_failed'],
                'success_rate': (
                    self.stats['screenshots_captured'] / max(self.stats['tweets_fetched'], 1) * 100
                ) if self.stats['tweets_fetched'] > 0 else 0
            },
            'output_directory': str(self.output_dir),
            'generated_at': datetime.now().isoformat()
        }
        
        return report
    
    def run_processing(self, 
                      accounts: List[str],
                      days_back: int = 7,
                      max_tweets: int = 20,
                      zoom_percent: int = 30,
                      s3_bucket: Optional[str] = None,
                      s3_prefix: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the complete visual processing pipeline.
        
        Args:
            accounts: Twitter accounts to process
            days_back: Days to look back for tweets
            max_tweets: Maximum tweets per account
            zoom_percent: Browser zoom level
            s3_bucket: Optional S3 bucket for upload
            s3_prefix: Optional S3 prefix
            
        Returns:
            Processing results
        """
        self.stats['start_time'] = datetime.now()
        
        logger.info("="*60)
        logger.info("FARGATE VISUAL TWEET PROCESSING PIPELINE")
        logger.info(f"Started at: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)
        
        logger.info("Configuration:")
        logger.info(f"  Accounts: {accounts}")
        logger.info(f"  Days back: {days_back}")
        logger.info(f"  Max tweets per account: {max_tweets}")
        logger.info(f"  Browser zoom: {zoom_percent}%")
        logger.info(f"  Output directory: {self.output_dir}")
        if s3_bucket:
            logger.info(f"  S3 bucket: {s3_bucket}")
            logger.info(f"  S3 prefix: {s3_prefix or 'auto-generated'}")
        
        try:
            # Initialize services
            if not self.initialize_services():
                raise Exception("Failed to initialize services")
            
            # Step 1: Fetch tweets
            logger.info("\n" + "="*40)
            logger.info("STEP 1: FETCHING TWEETS")
            logger.info("="*40)
            
            tweet_urls = self.fetch_tweets(accounts, days_back, max_tweets)
            
            if not tweet_urls:
                raise Exception("No tweets found to process")
            
            # Step 2: Capture visuals
            logger.info("\n" + "="*40)
            logger.info("STEP 2: CAPTURING VISUALS")
            logger.info("="*40)
            
            capture_results = self.capture_tweet_visuals(tweet_urls, zoom_percent)
            
            # Step 3: Upload to S3 (if configured)
            if s3_bucket:
                logger.info("\n" + "="*40)
                logger.info("STEP 3: UPLOADING TO S3")
                logger.info("="*40)
                
                upload_success = self.upload_to_s3(s3_bucket, s3_prefix)
            else:
                logger.info("\nSkipping S3 upload (no bucket specified)")
                upload_success = None
            
            # Complete processing
            self.stats['end_time'] = datetime.now()
            
            # Generate final report
            logger.info("\n" + "="*40)
            logger.info("PROCESSING COMPLETE")
            logger.info("="*40)
            
            report = self.generate_processing_report()
            
            logger.info("Final Statistics:")
            summary = report['processing_summary']
            logger.info(f"  Duration: {summary['duration_seconds']:.1f} seconds")
            logger.info(f"  Tweets fetched: {summary['tweets_fetched']}")
            logger.info(f"  Screenshots captured: {summary['screenshots_captured']}")
            logger.info(f"  Screenshots failed: {summary['screenshots_failed']}")
            logger.info(f"  Success rate: {summary['success_rate']:.1f}%")
            
            # Save report to file
            report_file = self.output_dir / "processing_report.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Report saved to: {report_file}")
            
            return {
                'status': 'success',
                'report': report,
                'capture_results': capture_results,
                's3_upload_success': upload_success
            }
            
        except Exception as e:
            self.stats['end_time'] = datetime.now()
            logger.error(f"Processing failed: {e}")
            
            error_report = self.generate_processing_report()
            error_report['error'] = str(e)
            
            return {
                'status': 'error',
                'error': str(e),
                'report': error_report
            }

def main():
    """Main entry point for the Fargate application."""
    
    parser = argparse.ArgumentParser(description='Fargate Visual Tweet Processing')
    parser.add_argument('--accounts', nargs='+', required=True,
                       help='Twitter accounts to process (without @)')
    parser.add_argument('--days-back', type=int, default=7,
                       help='Days to look back for tweets (default: 7)')
    parser.add_argument('--max-tweets', type=int, default=20,
                       help='Maximum tweets per account (default: 20)')
    parser.add_argument('--zoom', type=int, default=30,
                       help='Browser zoom percentage (default: 30)')
    parser.add_argument('--output-dir', default='/tmp/visual-processing',
                       help='Output directory (default: /tmp/visual-processing)')
    parser.add_argument('--s3-bucket',
                       help='S3 bucket for uploading results')
    parser.add_argument('--s3-prefix',
                       help='S3 prefix for organizing uploads')
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = FargateVisualProcessor(output_dir=args.output_dir)
    
    # Run processing
    results = processor.run_processing(
        accounts=args.accounts,
        days_back=args.days_back,
        max_tweets=args.max_tweets,
        zoom_percent=args.zoom,
        s3_bucket=args.s3_bucket,
        s3_prefix=args.s3_prefix
    )
    
    # Exit with appropriate code
    if results['status'] == 'success':
        logger.info("Visual processing completed successfully")
        sys.exit(0)
    else:
        logger.error("Visual processing failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 