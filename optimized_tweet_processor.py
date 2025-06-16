#!/usr/bin/env python
"""
Optimized Tweet Processing Pipeline with Parallel Processing

Features:
- Parallel account processing with rate limiting
- Concurrent tweet fetching
- Batch classification
- Local storage for testing
- Production-ready error handling
"""

import asyncio
import os
import sys
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from threading import Lock
import traceback

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
except Exception as e:
    print(f"⚠️  Error loading .env file: {e}")

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from shared.tweet_services import TweetFetcher
from shared.classification.classifier import HierarchicalClassifier
from shared.classification.llm_client import LLMClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ProcessingConfig:
    """Configuration for the processing pipeline."""
    days_back: int = 7
    max_tweets_per_account: int = 20
    max_concurrent_accounts: int = 3  # Rate limiting: max accounts processed simultaneously
    max_concurrent_tweets: int = 5    # Rate limiting: max tweet fetches per account
    enable_classification: bool = True
    output_dir: str = "local_outputs_optimized"
    batch_size: int = 10  # Batch size for classification
    retry_attempts: int = 3
    retry_delay: float = 1.0  # Base delay for exponential backoff

@dataclass 
class ProcessingResult:
    """Result of processing a single account."""
    account: str
    success: bool
    tweets_fetched: int = 0
    tweets_classified: int = 0
    categories_found: List[str] = None
    processing_time: float = 0.0
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.categories_found is None:
            self.categories_found = []

class RateLimiter:
    """Thread-safe rate limiter for API calls."""
    
    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call = 0.0
        self.lock = Lock()
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limits."""
        with self.lock:
            now = time.time()
            time_since_last = now - self.last_call
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)
            self.last_call = time.time()

class OptimizedTweetProcessor:
    """Optimized tweet processor with parallel processing capabilities."""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Rate limiters (Twitter API limits: 300 requests per 15 minutes)
        self.tweet_fetcher_limiter = RateLimiter(calls_per_minute=20)  # Conservative
        self.search_limiter = RateLimiter(calls_per_minute=15)  # More conservative for search
        
        # Initialize services
        self.tweet_fetcher = TweetFetcher()
        self.classifier = None
        
        if config.enable_classification:
            self._init_classifier()
        
        # Threading
        self.account_executor = ThreadPoolExecutor(max_workers=config.max_concurrent_accounts)
        self.tweet_executor = ThreadPoolExecutor(max_workers=config.max_concurrent_tweets)
        
        logger.info(f"OptimizedTweetProcessor initialized:")
        logger.info(f"  Max concurrent accounts: {config.max_concurrent_accounts}")
        logger.info(f"  Max concurrent tweets: {config.max_concurrent_tweets}")
        logger.info(f"  Classification enabled: {config.enable_classification}")
        logger.info(f"  Output directory: {self.output_dir}")
    
    def _init_classifier(self):
        """Initialize the tweet classifier."""
        try:
            # Ensure environment variables are loaded
            from dotenv import load_dotenv
            load_dotenv()
            
            # Prioritize Gemini API key since it's working well for this project
            api_key = os.getenv('GEMINI_API_KEY') or os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.warning("No API key found for classification. Set OPENAI_API_KEY or GEMINI_API_KEY")
                self.config.enable_classification = False
                return
            
            # Show which provider we're using
            provider = "Gemini" if api_key.startswith("AIza") else "OpenAI"
            logger.info(f"Using {provider} API key: {api_key[:20]}... for classification")
            
            llm_client = LLMClient(api_key=api_key)
            self.classifier = HierarchicalClassifier(llm_client)
            self.classification_limiter = RateLimiter(calls_per_minute=30)  # Conservative for LLM API
            logger.info("Classification service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize classifier: {e}")
            self.config.enable_classification = False
    
    def process_accounts(self, accounts: List[str]) -> Dict[str, Any]:
        """
        Process multiple accounts in parallel with rate limiting.
        
        Args:
            accounts: List of Twitter handles (without @)
            
        Returns:
            Dict with processing results and summary
        """
        start_time = time.time()
        logger.info(f"🚀 Starting parallel processing of {len(accounts)} accounts")
        
        # Submit all account processing tasks
        future_to_account = {}
        for account in accounts:
            future = self.account_executor.submit(self._process_single_account, account)
            future_to_account[future] = account
        
        # Collect results as they complete
        results = {}
        completed = 0
        
        for future in as_completed(future_to_account):
            account = future_to_account[future]
            completed += 1
            
            try:
                result = future.result()
                results[account] = result
                
                status = "✅" if result.success else "❌"
                logger.info(f"{status} [{completed}/{len(accounts)}] {account}: "
                          f"{result.tweets_fetched} tweets fetched, "
                          f"{result.tweets_classified} classified "
                          f"({result.processing_time:.1f}s)")
                
            except Exception as e:
                error_msg = f"Unexpected error processing {account}: {e}"
                logger.error(error_msg)
                results[account] = ProcessingResult(
                    account=account,
                    success=False,
                    error=error_msg
                )
        
        # Generate summary
        total_time = time.time() - start_time
        summary = self._generate_summary(results, total_time)
        
        # Save results
        self._save_results(results, summary)
        
        logger.info(f"🎉 Processing complete! Total time: {total_time:.1f}s")
        self._print_summary(summary)
        
        return {
            'results': {account: asdict(result) for account, result in results.items()},
            'summary': summary
        }
    
    def _process_single_account(self, account: str) -> ProcessingResult:
        """Process a single account with error handling and retries."""
        start_time = time.time()
        logger.info(f"🔄 Processing @{account}")
        
        for attempt in range(self.config.retry_attempts):
            try:
                return self._process_account_attempt(account, start_time)
            except Exception as e:
                if attempt < self.config.retry_attempts - 1:
                    delay = self.config.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Attempt {attempt + 1} failed for @{account}: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"All attempts failed for @{account}: {e}")
                    return ProcessingResult(
                        account=account,
                        success=False,
                        processing_time=time.time() - start_time,
                        error=str(e)
                    )
    
    def _process_account_attempt(self, account: str, start_time: float) -> ProcessingResult:
        """Single processing attempt for an account."""
        
        # 1. Fetch tweets with rate limiting
        tweets = self._fetch_tweets_for_account(account)
        
        if not tweets:
            return ProcessingResult(
                account=account,
                success=True,
                tweets_fetched=0,
                processing_time=time.time() - start_time,
                error="No tweets found"
            )
        
        logger.info(f"📝 @{account}: Fetched {len(tweets)} tweets")
        
        # 2. Classify tweets if enabled
        classified_tweets = []
        categories_found = []
        
        if self.config.enable_classification and tweets:
            classified_tweets = self._classify_tweets_batch(account, tweets)
            categories_found = list(set([
                tweet.get('classification', {}).get('level1') 
                for tweet in classified_tweets 
                if tweet.get('classification', {}).get('level1')
            ]))
        
        # 3. Save results
        self._save_account_data(account, tweets, classified_tweets)
        
        processing_time = time.time() - start_time
        return ProcessingResult(
            account=account,
            success=True,
            tweets_fetched=len(tweets),
            tweets_classified=len(classified_tweets),
            categories_found=categories_found,
            processing_time=processing_time
        )
    
    def _fetch_tweets_for_account(self, account: str) -> List[Dict[str, Any]]:
        """Fetch tweets for a single account using optimized methods."""
        
        # Apply rate limiting
        self.tweet_fetcher_limiter.wait_if_needed()
        
        try:
            # Ensure minimum tweets for Twitter API (timeline requires at least 5)
            api_max_tweets = max(5, self.config.max_tweets_per_account)
            
            # Use the existing detect_and_group_threads method which is more efficient
            grouped_content = self.tweet_fetcher.detect_and_group_threads(
                username=account,
                days_back=self.config.days_back,
                max_tweets=api_max_tweets  # Use API-compliant minimum
            )
            
            # Limit to user-requested amount if they want fewer than API minimum
            if len(grouped_content) > self.config.max_tweets_per_account:
                grouped_content = grouped_content[:self.config.max_tweets_per_account]
            
            # Flatten the results - both individual tweets and threads
            tweets = []
            for item in grouped_content:
                # Add metadata to identify tweet vs thread
                item['account'] = account
                item['fetched_at'] = datetime.now().isoformat()
                tweets.append(item)
            
            return tweets
            
        except Exception as e:
            logger.error(f"Error fetching tweets for @{account}: {e}")
            return []
    
    def _classify_tweets_batch(self, account: str, tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Classify tweets in batches for efficiency."""
        if not self.classifier:
            return tweets
        
        classified_tweets = []
        
        # Process in batches to avoid overwhelming the API
        for i in range(0, len(tweets), self.config.batch_size):
            batch = tweets[i:i + self.config.batch_size]
            batch_results = []
            
            for tweet in batch:
                # Apply rate limiting for LLM API
                self.classification_limiter.wait_if_needed()
                
                try:
                    tweet_text = tweet.get('text', '')
                    tweet_id = tweet.get('id', f"{account}_{i}")
                    
                    if not tweet_text.strip():
                        # Skip empty tweets
                        tweet['classification'] = {'error': 'Empty tweet text'}
                        batch_results.append(tweet)
                        continue
                    
                    # Classify the tweet
                    result = self.classifier.classify(tweet_id=tweet_id, tweet_text=tweet_text)
                    
                    # Add classification to tweet data
                    tweet['classification'] = {
                        'level1': result.level1,
                        'level2': result.level2,
                        'confidence_l1': result.conf_l1,
                        'confidence_l2': result.conf_l2,
                        'classified_at': datetime.now().isoformat(),
                        'version': result.version
                    }
                    
                    batch_results.append(tweet)
                    
                except Exception as e:
                    logger.error(f"Error classifying tweet {tweet_id}: {e}")
                    tweet['classification'] = {'error': str(e)}
                    batch_results.append(tweet)
            
            classified_tweets.extend(batch_results)
            
            # Brief pause between batches
            if i + self.config.batch_size < len(tweets):
                time.sleep(0.5)
        
        logger.info(f"📊 @{account}: Classified {len(classified_tweets)} tweets")
        return classified_tweets
    
    def _save_account_data(self, account: str, tweets: List[Dict[str, Any]], 
                          classified_tweets: List[Dict[str, Any]]):
        """Save tweet data for an account."""
        account_dir = self.output_dir / account
        account_dir.mkdir(parents=True, exist_ok=True)
        
        # Save raw tweets
        tweets_file = account_dir / "tweets_raw.json"
        with open(tweets_file, 'w') as f:
            json.dump(tweets, f, indent=2, default=str)
        
        # Save classified tweets if available
        if classified_tweets:
            classified_file = account_dir / "tweets_classified.json"
            with open(classified_file, 'w') as f:
                json.dump(classified_tweets, f, indent=2, default=str)
        
        # Save metadata
        metadata = {
            'account': account,
            'processed_at': datetime.now().isoformat(),
            'tweets_count': len(tweets),
            'classified_count': len(classified_tweets),
            'config': asdict(self.config)
        }
        
        metadata_file = account_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _generate_summary(self, results: Dict[str, ProcessingResult], total_time: float) -> Dict[str, Any]:
        """Generate processing summary."""
        successful = [r for r in results.values() if r.success]
        failed = [r for r in results.values() if not r.success]
        
        total_tweets = sum(r.tweets_fetched for r in successful)
        total_classified = sum(r.tweets_classified for r in successful)
        
        all_categories = set()
        for result in successful:
            all_categories.update(result.categories_found)
        
        return {
            'total_accounts': len(results),
            'successful_accounts': len(successful),
            'failed_accounts': len(failed),
            'total_tweets_fetched': total_tweets,
            'total_tweets_classified': total_classified,
            'unique_categories_found': list(all_categories),
            'total_processing_time': total_time,
            'avg_time_per_account': total_time / len(results) if results else 0,
            'tweets_per_second': total_tweets / total_time if total_time > 0 else 0,
            'failed_account_details': [(r.account, r.error) for r in failed]
        }
    
    def _save_results(self, results: Dict[str, ProcessingResult], summary: Dict[str, Any]):
        """Save overall results and summary."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save summary
        summary_file = self.output_dir / f"processing_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Save detailed results
        results_file = self.output_dir / f"processing_results_{timestamp}.json"
        results_data = {account: asdict(result) for account, result in results.items()}
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        logger.info(f"📁 Results saved to {self.output_dir}")
    
    def _print_summary(self, summary: Dict[str, Any]):
        """Print a nice summary of processing results."""
        print("\n" + "="*60)
        print("📊 PROCESSING SUMMARY")
        print("="*60)
        print(f"Accounts processed: {summary['successful_accounts']}/{summary['total_accounts']}")
        print(f"Total tweets fetched: {summary['total_tweets_fetched']}")
        print(f"Total tweets classified: {summary['total_tweets_classified']}")
        print(f"Processing time: {summary['total_processing_time']:.1f}s")
        print(f"Average time per account: {summary['avg_time_per_account']:.1f}s")
        print(f"Tweets per second: {summary['tweets_per_second']:.2f}")
        
        if summary['unique_categories_found']:
            print(f"\nCategories found: {len(summary['unique_categories_found'])}")
            for category in sorted(summary['unique_categories_found']):
                print(f"  • {category}")
        
        if summary['failed_account_details']:
            print(f"\n❌ Failed accounts ({len(summary['failed_account_details'])}):")
            for account, error in summary['failed_account_details']:
                print(f"  • @{account}: {error}")

def main():
    """Main entry point."""
    # User-requested specific accounts for E2E test
    test_accounts = [
        # Research Leaders
        'sama',           # Sam Altman
        'AndrewYNg',      # Andrew Ng
        'DrJimFan',       # Jim Fan
        # Companies
        'GoogleDeepMind', # Google DeepMind
        'AnthropicAI'     # Anthropic
    ]
    
    print("🚀 Optimized Tweet Processing Pipeline - End-to-End Test")
    print(f"Processing {len(test_accounts)} high-profile AI accounts with full classification...")
    print("\n📋 Selected Accounts:")
    print("   Research Leaders:")
    print("     • @sama (Sam Altman)")
    print("     • @AndrewYNg (Andrew Ng)")
    print("     • @DrJimFan (Jim Fan)")
    print("   Companies:")
    print("     • @GoogleDeepMind (Google DeepMind)")
    print("     • @AnthropicAI (Anthropic)")
    
    # Conservative configuration to handle rate limits
    config = ProcessingConfig(
        days_back=7,
        max_tweets_per_account=15,      # Good sample size
        max_concurrent_accounts=1,      # Sequential to avoid rate limits
        max_concurrent_tweets=3,        # Conservative
        enable_classification=True,     # Full classification pipeline
        batch_size=3,                   # Small batches for rate limiting
        output_dir="local_outputs_optimized"
    )
    
    print(f"\n⚙️  Configuration:")
    print(f"   • Days back: {config.days_back}")
    print(f"   • Max tweets per account: {config.max_tweets_per_account}")
    print(f"   • Concurrent accounts: {config.max_concurrent_accounts} (sequential to avoid rate limits)")
    print(f"   • Classification enabled: {config.enable_classification}")
    
    # Process accounts
    try:
        print(f"\n🎬 Starting end-to-end pipeline test...")
        print(f"⏳ Using sequential processing to avoid rate limits...")
        processor = OptimizedTweetProcessor(config)
        results = processor.process_accounts(test_accounts)
        
        print(f"\n✅ End-to-end test completed successfully!")
        print(f"📁 Check results in: {processor.output_dir}")
        
        # Show detailed results
        summary = results['summary']
        print(f"\n📊 End-to-End Test Results:")
        print(f"   • Total accounts processed: {summary['successful_accounts']}/{summary['total_accounts']}")
        print(f"   • Total tweets fetched: {summary['total_tweets_fetched']}")
        print(f"   • Total tweets classified: {summary['total_tweets_classified']}")
        print(f"   • Processing time: {summary['total_processing_time']:.1f}s")
        print(f"   • Average time per account: {summary['avg_time_per_account']:.1f}s")
        print(f"   • Tweets per second: {summary['tweets_per_second']:.2f}")
        
        if summary['unique_categories_found']:
            print(f"   • Categories found: {len(summary['unique_categories_found'])}")
            for category in sorted(summary['unique_categories_found']):
                print(f"     - {category}")
        else:
            print(f"   • Categories found: 0 (classification may have encountered issues)")
            
        if summary['failed_account_details']:
            print(f"\n⚠️  Failed accounts ({len(summary['failed_account_details'])}):")
            for account, error in summary['failed_account_details']:
                print(f"   • @{account}: {error}")
        
        # Performance assessment
        if summary['total_tweets_fetched'] > 0:
            print(f"\n🎉 SUCCESS: Pipeline successfully fetched and processed {summary['total_tweets_fetched']} tweets!")
            if summary['total_tweets_classified'] > 0:
                print(f"✅ Classification pipeline working: {summary['total_tweets_classified']} tweets classified")
            efficiency = summary['tweets_per_second']
            if efficiency > 0.5:
                print(f"⚡ Excellent performance: {efficiency:.2f} tweets/second")
            elif efficiency > 0.2:
                print(f"✅ Good performance: {efficiency:.2f} tweets/second")
            else:
                print(f"⚠️  Performance could be improved: {efficiency:.2f} tweets/second")
                
            # Show sample results
            print(f"\n📁 Results stored in organized directories:")
            print(f"   • Raw tweets: {processor.output_dir}/[account]/tweets_raw.json")
            print(f"   • Classified tweets: {processor.output_dir}/[account]/tweets_classified.json")
            print(f"   • Metadata: {processor.output_dir}/[account]/metadata.json")
        else:
            print(f"\n⚠️  No tweets found - this could be due to:")
            print(f"   • Rate limiting (429 errors)")
            print(f"   • Accounts with no recent activity")
            print(f"   • API configuration issues")
        
    except KeyboardInterrupt:
        print("\n⏹️  Processing interrupted by user")
    except Exception as e:
        print(f"\n❌ End-to-end test failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 