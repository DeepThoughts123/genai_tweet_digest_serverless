#!/usr/bin/env python
"""Local-only pipeline driver - NO AWS dependencies.

This script runs the entire tweet processing pipeline locally without touching any AWS services.
All files are stored within the project directory under local_outputs/.

Example:
    python scripts/run_pipeline_local.py --accounts openai --days 7 --max 5
"""

import argparse
import json
import os
import sys
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from shared.tweet_services import TweetFetcher
from shared.classification.classifier import HierarchicalClassifier
from shared.classification.llm_client import LLMClient
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LocalVisualTweetCaptureService:
    """Local-only version of visual tweet capture service."""
    
    def __init__(self, output_dir: str, zoom_percent: int = 60):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.zoom_percent = zoom_percent
        self.tweet_fetcher = TweetFetcher()
        self.date_folder = datetime.now().strftime("%Y-%m-%d")
        
        # Create temp directory within project
        self.temp_dir = self.output_dir / "temp" / f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"LocalVisualTweetCaptureService initialized - output: {self.output_dir}")
    
    def capture_account_content(self, account_name: str, days_back: int = 7, max_tweets: int = 25) -> Dict[str, Any]:
        """Capture tweets and save locally."""
        logger.info(f"Starting local capture for @{account_name} - {days_back} days, {max_tweets} max tweets")
        
        try:
            # Get all content for the account
            grouped_content = self.tweet_fetcher.detect_and_group_threads(
                account_name, days_back, max_tweets
            )
            
            if not grouped_content:
                logger.warning(f"No content found for @{account_name}")
                return {
                    'success': False,
                    'message': f'No content found for @{account_name}',
                    'account': account_name,
                    'captured_items': []
                }
            
            # Separate threads and individual tweets
            threads = [item for item in grouped_content if item.get('is_thread', False)]
            individual_tweets = [item for item in grouped_content if not item.get('is_thread', False)]
            
            logger.info(f"Found {len(threads)} threads and {len(individual_tweets)} individual tweets")
            
            captured_results = []
            
            # Process threads
            for i, thread in enumerate(threads, 1):
                logger.info(f"Processing thread {i}/{len(threads)}: {thread['conversation_id']}")
                result = self._save_thread_locally(thread, account_name)
                if result:
                    captured_results.append(result)
            
            # Process individual tweets
            for i, tweet in enumerate(individual_tweets, 1):
                logger.info(f"Processing tweet {i}/{len(individual_tweets)}: {tweet['id']}")
                result = self._save_tweet_locally(tweet, account_name)
                if result:
                    captured_results.append(result)
            
            # Create summary
            summary = self._create_capture_summary(account_name, captured_results, threads, individual_tweets)
            summary_path = self.output_dir / self.date_folder / account_name / "capture_summary.json"
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"✅ Local capture complete for @{account_name}: {len(captured_results)} items")
            
            return {
                'success': True,
                'account': account_name,
                'total_items_captured': len(captured_results),
                'threads_captured': len([r for r in captured_results if r['type'] == 'thread']),
                'individual_tweets_captured': len([r for r in captured_results if r['type'] == 'individual_tweet']),
                'summary_location': str(summary_path),
                'captured_items': captured_results
            }
            
        except Exception as e:
            logger.error(f"Error capturing content for @{account_name}: {e}")
            return {
                'success': False,
                'account': account_name,
                'error': str(e),
                'captured_items': []
            }
        finally:
            # Clean up temp directory
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
    
    def _save_thread_locally(self, thread_data: Dict[str, Any], account_name: str) -> Optional[Dict[str, Any]]:
        """Save thread data locally."""
        try:
            conversation_id = thread_data.get('conversation_id', thread_data['id'])
            thread_tweets = thread_data.get('thread_tweets', [])
            
            # Create local folder structure
            thread_dir = self.output_dir / self.date_folder / account_name / f"thread_{conversation_id}"
            thread_dir.mkdir(parents=True, exist_ok=True)
            
            # Save thread metadata
            metadata = {
                'conversation_id': conversation_id,
                'capture_timestamp': datetime.now().isoformat(),
                'thread_summary': thread_data,
                'total_tweets_in_thread': len(thread_tweets),
                'tweet_texts': [tweet.get('text', '') for tweet in thread_tweets]
            }
            
            metadata_path = thread_dir / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return {
                'type': 'thread',
                'conversation_id': conversation_id,
                'total_tweets': len(thread_tweets),
                'location': str(thread_dir),
                'metadata_location': str(metadata_path),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error saving thread {conversation_id}: {e}")
            return None
    
    def _save_tweet_locally(self, tweet_data: Dict[str, Any], account_name: str) -> Optional[Dict[str, Any]]:
        """Save individual tweet data locally."""
        try:
            tweet_id = tweet_data['id']
            content_type = self._detect_content_type(tweet_data)
            
            # Create local folder structure
            tweet_dir = self.output_dir / self.date_folder / account_name / f"{content_type}_{tweet_id}"
            tweet_dir.mkdir(parents=True, exist_ok=True)
            
            # Save tweet metadata
            metadata = {
                'tweet_id': tweet_id,
                'tweet_url': tweet_data.get('url', ''),
                'content_type': content_type,
                'capture_timestamp': datetime.now().isoformat(),
                'tweet_text': tweet_data.get('text', ''),
                'tweet_metadata': tweet_data
            }
            
            metadata_path = tweet_dir / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return {
                'type': 'individual_tweet',
                'content_type': content_type,
                'tweet_id': tweet_id,
                'location': str(tweet_dir),
                'metadata_location': str(metadata_path),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error saving tweet {tweet_id}: {e}")
            return None
    
    def _detect_content_type(self, tweet_data: Dict[str, Any]) -> str:
        """Detect the type of tweet content."""
        text = tweet_data.get('text', '')
        if text.startswith('RT @'):
            return "retweet"
        return "tweet"
    
    def _create_capture_summary(self, account_name: str, captured_results: List[Dict[str, Any]], 
                              threads: List[Dict[str, Any]], individual_tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a summary of the capture session."""
        return {
            'account': account_name,
            'capture_timestamp': datetime.now().isoformat(),
            'summary': {
                'total_items_found': len(threads) + len(individual_tweets),
                'total_items_captured': len(captured_results),
                'threads_found': len(threads),
                'threads_captured': len([r for r in captured_results if r['type'] == 'thread']),
                'individual_tweets_found': len(individual_tweets),
                'individual_tweets_captured': len([r for r in captured_results if r['type'] == 'individual_tweet'])
            },
            'captured_content': captured_results
        }


class LocalClassifierService:
    """Local-only classifier service."""
    
    def __init__(self, classifier: HierarchicalClassifier, output_dir: str):
        self.classifier = classifier
        self.output_dir = Path(output_dir)
        self.classified_results = []
    
    def classify_item(self, metadata_path: str) -> Optional[Dict[str, Any]]:
        """Classify a single item from its metadata."""
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Extract tweet text
            if 'tweet_text' in metadata:
                tweet_text = metadata['tweet_text']
                tweet_id = metadata.get('tweet_id', 'unknown')
            elif 'tweet_texts' in metadata:  # Thread
                tweet_text = ' '.join(metadata['tweet_texts'])
                tweet_id = metadata.get('conversation_id', 'unknown')
            else:
                logger.warning(f"No tweet text found in {metadata_path}")
                return None
            
            # Classify
            logger.info(f"Classifying item {tweet_id}")
            result = self.classifier.classify(tweet_id=tweet_id, tweet_text=tweet_text)
            
            classified_data = {
                'item_id': tweet_id,
                'item_type': 'thread' if 'conversation_id' in metadata else 'tweet',
                'text': tweet_text[:200] + '...' if len(tweet_text) > 200 else tweet_text,
                'classification': {
                    'l1_topics': result.level1.topics,
                    'l2_topic': result.level2.topic if result.level2 else None,
                    'model_used': result.classification_model
                },
                'classified_at': datetime.now().isoformat(),
                'metadata_path': str(metadata_path)
            }
            
            self.classified_results.append(classified_data)
            return classified_data
            
        except Exception as e:
            logger.error(f"Error classifying item from {metadata_path}: {e}")
            return None
    
    def save_results(self):
        """Save all classification results."""
        if self.classified_results:
            results_path = self.output_dir / "classification_results.json"
            with open(results_path, 'w') as f:
                json.dump(self.classified_results, f, indent=2)
            logger.info(f"Saved {len(self.classified_results)} classification results to {results_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Run tweet pipeline locally (no AWS)")
    parser.add_argument("--accounts", nargs="+", required=True, help="Twitter handles without @")
    parser.add_argument("--days", type=int, default=7, help="Look-back window (days)")
    parser.add_argument("--max", type=int, default=20, help="Max tweets per account")
    parser.add_argument("--output", default="local_outputs", help="Local output directory")
    parser.add_argument("--classify", action="store_true", help="Run classification (requires API key)")
    return parser.parse_args()


def main():
    args = parse_args()
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize capture service
    capture_service = LocalVisualTweetCaptureService(output_dir=str(output_dir))
    
    # Process each account
    all_metadata_files = []
    
    for account in args.accounts:
        print(f"\n=== Processing @{account} ===")
        
        # Capture content
        result = capture_service.capture_account_content(
            account_name=account,
            days_back=args.days,
            max_tweets=args.max
        )
        
        # Save enriched results
        results_file = output_dir / f"{account}_enriched_results.json"
        with open(results_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"✅ Saved results to {results_file}")
        
        # Collect metadata files for classification
        if result['success'] and args.classify:
            for item in result['captured_items']:
                if 'metadata_location' in item:
                    all_metadata_files.append(item['metadata_location'])
    
    # Run classification if requested
    if args.classify and all_metadata_files:
        print(f"\n=== Running Classification on {len(all_metadata_files)} items ===")
        
        # Check for API key
        api_key = os.getenv('OPENAI_API_KEY') or os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("❌ No API key found. Set OPENAI_API_KEY or GEMINI_API_KEY to enable classification.")
            return
        
        # Initialize classifier
        llm_client = LLMClient(api_key=api_key)
        classifier = HierarchicalClassifier(llm_client)
        classifier_service = LocalClassifierService(classifier=classifier, output_dir=str(output_dir))
        
        # Classify each item
        for metadata_path in all_metadata_files:
            classifier_service.classify_item(metadata_path)
        
        # Save results
        classifier_service.save_results()
        print(f"✅ Classification complete!")
    
    print(f"\n🎉 Local pipeline complete! All outputs saved to: {output_dir.absolute()}")


if __name__ == "__main__":
    main() 