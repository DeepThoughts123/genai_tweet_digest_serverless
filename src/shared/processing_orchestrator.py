"""
Processing Orchestrator

Decides whether to use Lambda (fast track) or EC2 (slow track) processing
based on configuration and processing requirements.
"""

import os
import boto3
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ProcessingOrchestrator:
    """
    Orchestrator that decides between Lambda and EC2 processing modes.
    """
    
    def __init__(self):
        """Initialize the processing orchestrator."""
        self.lambda_client = boto3.client('lambda')
        
        # Processing mode configuration
        self.processing_mode = os.environ.get('PROCESSING_MODE', 'lambda-only')  # lambda-only, ec2-only, hybrid
        self.enable_visual_capture = os.environ.get('ENABLE_VISUAL_CAPTURE', 'false').lower() == 'true'
        self.visual_accounts_limit = int(os.environ.get('VISUAL_ACCOUNTS_LIMIT', '10'))
        
        # Lambda function names
        self.visual_dispatcher_function = os.environ.get('VISUAL_DISPATCHER_FUNCTION_NAME')
        
        logger.info(f"Processing Orchestrator initialized:")
        logger.info(f"  Processing mode: {self.processing_mode}")
        logger.info(f"  Visual capture enabled: {self.enable_visual_capture}")
        logger.info(f"  Visual accounts limit: {self.visual_accounts_limit}")
    
    def should_use_ec2_processing(self, accounts: List[str], processing_requirements: Dict) -> bool:
        """
        Determine if EC2 processing should be used based on requirements.
        
        Args:
            accounts: List of Twitter accounts to process
            processing_requirements: Dict with processing parameters
            
        Returns:
            bool: True if EC2 processing should be used
        """
        
        # Force modes
        if self.processing_mode == 'lambda-only':
            return False
        elif self.processing_mode == 'ec2-only':
            return True
        
        # Hybrid mode decision logic
        if self.processing_mode == 'hybrid':
            
            # Use EC2 if visual capture is enabled
            if self.enable_visual_capture:
                logger.info("Using EC2 processing: Visual capture enabled")
                return True
            
            # Use EC2 if too many accounts for Lambda
            if len(accounts) > self.visual_accounts_limit:
                logger.info(f"Using EC2 processing: {len(accounts)} accounts > {self.visual_accounts_limit} limit")
                return True
            
            # Use EC2 if high tweet volume expected
            max_tweets = processing_requirements.get('max_tweets', 10)
            if len(accounts) * max_tweets > 100:  # Arbitrary threshold
                logger.info(f"Using EC2 processing: High volume ({len(accounts)} * {max_tweets} > 100)")
                return True
                
            # Use EC2 if special processing modes requested
            special_modes = ['visual_capture', 'heavy_ai', 'batch_processing']
            if processing_requirements.get('processing_mode') in special_modes:
                logger.info(f"Using EC2 processing: Special mode {processing_requirements.get('processing_mode')}")
                return True
        
        # Default to Lambda
        logger.info("Using Lambda processing: Standard text-only processing")
        return False
    
    def dispatch_ec2_processing(self, accounts: List[str], processing_config: Dict) -> Dict:
        """
        Dispatch processing to EC2 via the visual processing dispatcher Lambda.
        
        Args:
            accounts: List of Twitter accounts to process
            processing_config: Configuration for processing
            
        Returns:
            Dict: Dispatch result
        """
        
        if not self.visual_dispatcher_function:
            raise ValueError("VISUAL_DISPATCHER_FUNCTION_NAME not configured")
        
        logger.info(f"Dispatching EC2 processing for {len(accounts)} accounts")
        
        # Prepare event for dispatcher Lambda
        dispatcher_event = {
            'accounts': accounts,
            'days_back': processing_config.get('days_back', 7),
            'max_tweets': processing_config.get('max_tweets', 20),
            'zoom_percent': processing_config.get('zoom_percent', 60),
            'processing_mode': processing_config.get('processing_mode', 'visual_capture'),
            'dispatcher_metadata': {
                'triggered_by': 'processing_orchestrator',
                'original_trigger': processing_config.get('trigger_source', 'unknown')
            }
        }
        
        try:
            # Invoke the visual processing dispatcher Lambda
            response = self.lambda_client.invoke(
                FunctionName=self.visual_dispatcher_function,
                InvocationType='Event',  # Async invocation
                Payload=json.dumps(dispatcher_event)
            )
            
            if response['StatusCode'] == 202:  # Async invocation accepted
                logger.info("✅ EC2 processing dispatched successfully")
                return {
                    'success': True,
                    'processing_type': 'ec2',
                    'status': 'dispatched',
                    'message': 'EC2 visual processing dispatched',
                    'dispatcher_response': {
                        'status_code': response['StatusCode'],
                        'request_id': response.get('ResponseMetadata', {}).get('RequestId')
                    }
                }
            else:
                logger.error(f"Unexpected dispatcher response: {response['StatusCode']}")
                return {
                    'success': False,
                    'processing_type': 'ec2',
                    'status': 'dispatch_error',
                    'error': f"Unexpected response code: {response['StatusCode']}"
                }
                
        except Exception as e:
            logger.error(f"Error dispatching EC2 processing: {e}")
            return {
                'success': False,
                'processing_type': 'ec2',
                'status': 'dispatch_error',
                'error': str(e)
            }
    
    def process_with_lambda(self, accounts: List[str], processing_config: Dict) -> Dict:
        """
        Process using standard Lambda text-only pipeline.
        
        Args:
            accounts: List of Twitter accounts to process
            processing_config: Configuration for processing
            
        Returns:
            Dict: Processing result
        """
        
        logger.info(f"Processing {len(accounts)} accounts with Lambda text-only pipeline")
        
        # Import here to avoid circular imports
        from tweet_services import TweetFetcher, TweetCategorizer, TweetSummarizer
        
        try:
            # Initialize services
            tweet_fetcher = TweetFetcher()
            tweet_categorizer = TweetCategorizer()
            tweet_summarizer = TweetSummarizer()
            
            # Fetch tweets
            days_back = processing_config.get('days_back', 7)
            max_tweets = processing_config.get('max_tweets', 10)
            
            tweets = tweet_fetcher.fetch_tweets(accounts, days_back=days_back, max_tweets_per_user=max_tweets)
            
            if not tweets:
                return {
                    'success': True,
                    'processing_type': 'lambda',
                    'status': 'no_tweets',
                    'tweets_processed': 0,
                    'message': 'No tweets found for processing'
                }
            
            # Categorize tweets
            categorized_tweets = tweet_categorizer.categorize_tweets(tweets)
            
            # Generate summaries
            digest_data = tweet_summarizer.summarize_tweets(categorized_tweets)
            
            logger.info(f"✅ Lambda processing completed: {len(tweets)} tweets → {len(digest_data.get('summaries', []))} categories")
            
            return {
                'success': True,
                'processing_type': 'lambda',
                'status': 'completed',
                'tweets_processed': len(tweets),
                'categories_generated': len(digest_data.get('summaries', [])),
                'digest_data': digest_data
            }
            
        except Exception as e:
            logger.error(f"Error in Lambda processing: {e}")
            return {
                'success': False,
                'processing_type': 'lambda',
                'status': 'processing_error',
                'error': str(e)
            }
    
    def orchestrate_processing(self, accounts: List[str], processing_config: Dict) -> Dict:
        """
        Main orchestration method that decides and executes the appropriate processing mode.
        
        Args:
            accounts: List of Twitter accounts to process
            processing_config: Configuration dictionary
            
        Returns:
            Dict: Processing result with metadata about the chosen method
        """
        
        logger.info("🎯 Processing Orchestration Starting")
        logger.info(f"   Accounts: {len(accounts)} accounts")
        logger.info(f"   Config: {processing_config}")
        
        # Determine processing method
        use_ec2 = self.should_use_ec2_processing(accounts, processing_config)
        
        if use_ec2:
            logger.info("🚀 Routing to EC2 processing")
            result = self.dispatch_ec2_processing(accounts, processing_config)
        else:
            logger.info("⚡ Routing to Lambda processing")
            result = self.process_with_lambda(accounts, processing_config)
        
        # Add orchestration metadata
        result['orchestration'] = {
            'processing_mode': self.processing_mode,
            'visual_capture_enabled': self.enable_visual_capture,
            'decision_factors': {
                'account_count': len(accounts),
                'visual_accounts_limit': self.visual_accounts_limit,
                'processing_mode_config': processing_config.get('processing_mode', 'default')
            },
            'chosen_method': 'ec2' if use_ec2 else 'lambda'
        }
        
        return result
    
    def get_processing_status(self) -> Dict:
        """
        Get current processing orchestrator status and configuration.
        
        Returns:
            Dict: Status information
        """
        
        return {
            'processing_mode': self.processing_mode,
            'visual_capture_enabled': self.enable_visual_capture,
            'visual_accounts_limit': self.visual_accounts_limit,
            'visual_dispatcher_configured': bool(self.visual_dispatcher_function),
            'available_modes': ['lambda-only', 'ec2-only', 'hybrid'],
            'current_config': {
                'PROCESSING_MODE': os.environ.get('PROCESSING_MODE'),
                'ENABLE_VISUAL_CAPTURE': os.environ.get('ENABLE_VISUAL_CAPTURE'),
                'VISUAL_ACCOUNTS_LIMIT': os.environ.get('VISUAL_ACCOUNTS_LIMIT'),
                'VISUAL_DISPATCHER_FUNCTION_NAME': os.environ.get('VISUAL_DISPATCHER_FUNCTION_NAME')
            }
        } 