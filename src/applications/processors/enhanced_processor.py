#!/usr/bin/env python
"""
Enhanced Optimized Tweet Processing Pipeline with Visual Extraction

Extends the optimized tweet processor with integrated visual capture and text extraction.
Provides the complete pipeline:
1. Tweet fetching from accounts
2. Visual capture and full text extraction  
3. AI-powered summarization
4. Hierarchical classification (L1/L2)
5. Enhanced metadata generation

Features:
- Parallel processing with intelligent rate limiting
- Visual capture with screenshot analysis
- Full text extraction from images using Gemini AI
- Fallback to API text when visual extraction fails
- Comprehensive error handling and recovery
- Production-ready performance optimization
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

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
except Exception as e:
    print(f"⚠️  Error loading .env file: {e}")

# Import base components
from .tweet_processor import (
    OptimizedTweetProcessor, ProcessingConfig, ProcessingResult, RateLimiter
)

# Import enhanced services
from ...shared.visual_text_extractor import VisualTextExtractor, ExtractionResult
from ...shared.tweet_services import TweetFetcher
from ...core.services.classification.classification.classifier import HierarchicalClassifier
from ...core.services.classification.classification.llm_client import LLMClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedOptimizedTweetProcessor(OptimizedTweetProcessor):
    """
    Enhanced tweet processor with integrated visual extraction capabilities.
    
    Extends the base OptimizedTweetProcessor with:
    - Visual tweet capture and screenshot analysis
    - Full text extraction using Gemini AI
    - Enhanced metadata with visual processing statistics
    - Intelligent fallback when visual extraction fails
    - Comprehensive rate limiting for visual operations
    """
    
    def __init__(self, config: ProcessingConfig):
        """
        Initialize the enhanced processor with visual extraction capabilities.
        
        Args:
            config: Enhanced processing configuration with visual settings
        """
        # Initialize base processor
        super().__init__(config)
        
        # Visual extraction components
        self.visual_extractor = None
        
        if config.enable_visual_extraction:
            self._init_visual_extractor()
            
            # Additional rate limiters for visual processing
            self.visual_extraction_limiter = RateLimiter(calls_per_minute=10)  # Conservative for browser ops
            self.screenshot_capture_limiter = RateLimiter(calls_per_minute=20)  # Screenshot operations
            
            logger.info("Enhanced processor initialized with visual extraction capabilities")
        else:
            logger.info("Enhanced processor initialized without visual extraction (disabled in config)")
    
    def _init_visual_extractor(self):
        """Initialize the visual text extraction service."""
        try:
            api_key = os.getenv('GEMINI_API_KEY') or os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.warning("No API key found for visual extraction. Set GEMINI_API_KEY")
                self.config.enable_visual_extraction = False
                return
            
            self.visual_extractor = VisualTextExtractor(
                api_key=api_key,
                zoom_percent=self.config.zoom_percent,
                max_screenshots=self.config.max_screenshots_per_tweet,
                scroll_pause=self.config.visual_scroll_pause
            )
            
            logger.info(f"Visual extractor initialized with {self.config.zoom_percent}% zoom")
            
        except Exception as e:
            logger.error(f"Failed to initialize visual extractor: {e}")
            self.config.enable_visual_extraction = False
    
    def _process_account_attempt(self, account: str, start_time: float) -> ProcessingResult:
        """
        Enhanced account processing with visual extraction.
        
        Args:
            account: Twitter account name
            start_time: Processing start time
            
        Returns:
            Enhanced ProcessingResult with visual processing statistics
        """
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
        
        # 2. Process tweets with visual extraction if enabled
        enhanced_tweets = []
        visual_stats = {
            'tweets_visually_processed': 0,
            'visual_extraction_failures': 0,
            'total_screenshots_captured': 0,
            'visual_processing_time': 0.0
        }
        
        if self.config.enable_visual_extraction and self.visual_extractor:
            enhanced_tweets, visual_stats = self._process_tweets_with_visual_extraction(account, tweets)
        else:
            # Use original tweets without visual enhancement
            enhanced_tweets = tweets
        
        # 3. Classify tweets using enhanced text (full text if available, API text as fallback)
        classified_tweets = []
        categories_found = []
        
        if self.config.enable_classification and enhanced_tweets:
            classified_tweets = self._classify_tweets_with_enhanced_text(account, enhanced_tweets)
            categories_found = list(set([
                tweet.get('classification', {}).get('level1') 
                for tweet in classified_tweets 
                if tweet.get('classification', {}).get('level1')
            ]))
        
        # 4. Save enhanced results
        self._save_enhanced_account_data(account, tweets, enhanced_tweets, classified_tweets)
        
        # 5. Create enhanced processing result
        processing_time = time.time() - start_time
        
        return ProcessingResult(
            account=account,
            success=True,
            tweets_fetched=len(tweets),
            tweets_classified=len(classified_tweets),
            categories_found=categories_found,
            processing_time=processing_time,
            tweets_visually_processed=visual_stats['tweets_visually_processed'],
            visual_extraction_failures=visual_stats['visual_extraction_failures'],
            total_screenshots_captured=visual_stats['total_screenshots_captured'],
            visual_processing_time=visual_stats['visual_processing_time']
        )
    
    def _process_tweets_with_visual_extraction(self, account: str, tweets: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Process tweets with visual extraction for full text and summaries.
        
        Args:
            account: Twitter account name
            tweets: List of tweet dictionaries
            
        Returns:
            Tuple of (enhanced_tweets, visual_statistics)
        """
        logger.info(f"🔍 @{account}: Starting visual extraction for {len(tweets)} tweets")
        
        visual_start_time = time.time()
        enhanced_tweets = []
        visual_stats = {
            'tweets_visually_processed': 0,
            'visual_extraction_failures': 0,
            'total_screenshots_captured': 0,
            'visual_processing_time': 0.0
        }
        
        # Process tweets in batches for efficiency
        batch_size = self.config.visual_extraction_batch_size
        
        for i in range(0, len(tweets), batch_size):
            batch = tweets[i:i + batch_size]
            logger.info(f"📸 Processing visual batch {i//batch_size + 1}/{(len(tweets) + batch_size - 1)//batch_size}")
            
            # Apply rate limiting for visual processing
            self.visual_extraction_limiter.wait_if_needed()
            
            # Process batch with visual extraction
            batch_results = self._process_tweet_batch_with_visual_extraction(batch)
            
            # Update statistics
            for tweet, extraction_result in zip(batch, batch_results):
                enhanced_tweet = self._enhance_tweet_metadata(tweet, extraction_result)
                enhanced_tweets.append(enhanced_tweet)
                
                if extraction_result and extraction_result.success:
                    visual_stats['tweets_visually_processed'] += 1
                    if extraction_result.screenshots_captured:
                        visual_stats['total_screenshots_captured'] += extraction_result.screenshots_captured
                else:
                    visual_stats['visual_extraction_failures'] += 1
        
        visual_stats['visual_processing_time'] = time.time() - visual_start_time
        
        logger.info(f"📊 @{account}: Visual processing complete")
        logger.info(f"   ✅ Successfully processed: {visual_stats['tweets_visually_processed']}/{len(tweets)}")
        logger.info(f"   📸 Screenshots captured: {visual_stats['total_screenshots_captured']}")
        logger.info(f"   ⏱️  Processing time: {visual_stats['visual_processing_time']:.1f}s")
        
        return enhanced_tweets, visual_stats
    
    def _process_tweet_batch_with_visual_extraction(self, tweets: List[Dict[str, Any]]) -> List[Optional[ExtractionResult]]:
        """
        Process a batch of tweets with visual extraction.
        
        Args:
            tweets: List of tweet dictionaries
            
        Returns:
            List of ExtractionResult objects (None for failures)
        """
        # Prepare tweet data for visual extractor
        tweet_data = []
        for tweet in tweets:
            if 'url' not in tweet:
                # Construct URL if not present
                tweet_url = f"https://twitter.com/{tweet.get('author', {}).get('username', 'unknown')}/status/{tweet['id']}"
                tweet['url'] = tweet_url
            
            tweet_data.append({
                'id': tweet['id'],
                'url': tweet['url']
            })
        
        try:
            # Use batch processing for efficiency
            extraction_results = self.visual_extractor.extract_batch(
                tweet_data, 
                max_workers=min(3, len(tweet_data))  # Conservative threading
            )
            
            return extraction_results
            
        except Exception as e:
            logger.error(f"Error in batch visual extraction: {e}")
            # Return None results for all tweets in case of batch failure
            return [None] * len(tweets)
    
    def _enhance_tweet_metadata(self, tweet: Dict[str, Any], extraction_result: Optional[ExtractionResult]) -> Dict[str, Any]:
        """
        Enhance tweet metadata with visual extraction results.
        
        Args:
            tweet: Original tweet dictionary
            extraction_result: Visual extraction result (can be None)
            
        Returns:
            Enhanced tweet dictionary with additional metadata
        """
        enhanced_tweet = tweet.copy()
        
        # Always preserve original API text
        enhanced_tweet['original_text'] = tweet.get('text', '')
        
        if extraction_result and extraction_result.success:
            # Use extracted full text and summary
            enhanced_tweet['full_text'] = extraction_result.full_text
            enhanced_tweet['summary'] = extraction_result.summary
            enhanced_tweet['engagement_metrics'] = extraction_result.engagement_metrics
            
            # Add visual processing metadata
            enhanced_tweet['visual_extraction'] = {
                'success': True,
                'processing_time': extraction_result.processing_time,
                'screenshots_captured': extraction_result.screenshots_captured,
                'extracted_at': datetime.now().isoformat()
            }
            
        else:
            # Fallback to API text
            enhanced_tweet['full_text'] = tweet.get('text', '')
            enhanced_tweet['summary'] = None
            enhanced_tweet['engagement_metrics'] = {}
            
            # Add failure information
            if extraction_result:
                enhanced_tweet['visual_extraction_error'] = extraction_result.error
            else:
                enhanced_tweet['visual_extraction_error'] = "Visual extraction not attempted"
        
        return enhanced_tweet
    
    def _classify_tweets_with_enhanced_text(self, account: str, enhanced_tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Classify tweets using enhanced text (full text when available, API text as fallback).
        
        Args:
            account: Twitter account name
            enhanced_tweets: List of enhanced tweet dictionaries
            
        Returns:
            List of classified tweet dictionaries
        """
        if not self.classifier:
            return enhanced_tweets
        
        classified_tweets = []
        
        # Process in batches to avoid overwhelming the API
        for i in range(0, len(enhanced_tweets), self.config.batch_size):
            batch = enhanced_tweets[i:i + self.config.batch_size]
            batch_results = []
            
            for tweet in batch:
                # Apply rate limiting for LLM API
                self.classification_limiter.wait_if_needed()
                
                try:
                    # Use full text if available, otherwise fall back to original text
                    classification_text = tweet.get('full_text', tweet.get('original_text', ''))
                    tweet_id = tweet.get('id', f"{account}_{i}")
                    
                    if not classification_text.strip():
                        # Skip empty tweets
                        tweet['classification'] = {'error': 'Empty tweet text'}
                        batch_results.append(tweet)
                        continue
                    
                    # Classify using enhanced text
                    result = self.classifier.classify(tweet_id=tweet_id, tweet_text=classification_text)
                    
                    # Add classification to tweet data
                    tweet['classification'] = {
                        'level1': result.level1,
                        'level2': result.level2,
                        'confidence_l1': result.conf_l1,
                        'confidence_l2': result.conf_l2,
                        'classified_at': datetime.now().isoformat(),
                        'version': result.version,
                        'text_source': 'full_text' if 'full_text' in tweet and tweet['full_text'] != tweet.get('original_text', '') else 'api_text'
                    }
                    
                    batch_results.append(tweet)
                    
                except Exception as e:
                    logger.error(f"Error classifying tweet {tweet_id}: {e}")
                    tweet['classification'] = {'error': str(e)}
                    batch_results.append(tweet)
            
            classified_tweets.extend(batch_results)
            
            # Brief pause between batches
            if i + self.config.batch_size < len(enhanced_tweets):
                time.sleep(0.5)
        
        logger.info(f"📊 @{account}: Classified {len(classified_tweets)} tweets (using enhanced text)")
        return classified_tweets
    
    def _save_enhanced_account_data(self, account: str, original_tweets: List[Dict[str, Any]], 
                                   enhanced_tweets: List[Dict[str, Any]], classified_tweets: List[Dict[str, Any]]):
        """
        Save enhanced tweet data with visual extraction results.
        
        Args:
            account: Twitter account name
            original_tweets: Original tweets from API
            enhanced_tweets: Tweets with visual extraction
            classified_tweets: Tweets with classification
        """
        account_dir = self.output_dir / account
        account_dir.mkdir(parents=True, exist_ok=True)
        
        # Save original tweets (for comparison)
        original_file = account_dir / "tweets_original.json"
        with open(original_file, 'w') as f:
            json.dump(original_tweets, f, indent=2, default=str)
        
        # Save enhanced tweets (with visual extraction)
        enhanced_file = account_dir / "tweets_enhanced.json"
        with open(enhanced_file, 'w') as f:
            json.dump(enhanced_tweets, f, indent=2, default=str)
        
        # Save classified tweets (final results)
        if classified_tweets:
            classified_file = account_dir / "tweets_classified.json"
            with open(classified_file, 'w') as f:
                json.dump(classified_tweets, f, indent=2, default=str)
        
        # Enhanced metadata
        enhanced_metadata = {
            'account': account,
            'processed_at': datetime.now().isoformat(),
            'original_tweets_count': len(original_tweets),
            'enhanced_tweets_count': len(enhanced_tweets),
            'classified_tweets_count': len(classified_tweets),
            'visual_extraction_enabled': self.config.enable_visual_extraction,
            'classification_enabled': self.config.enable_classification,
            'config': asdict(self.config)
        }
        
        metadata_file = account_dir / "metadata_enhanced.json"
        with open(metadata_file, 'w') as f:
            json.dump(enhanced_metadata, f, indent=2)
    
    def _print_enhanced_summary(self, summary: Dict[str, Any]):
        """Print enhanced summary with visual processing statistics."""
        super()._print_summary(summary)
        
        # Add visual processing statistics
        if 'visual_stats' in summary:
            visual_stats = summary['visual_stats']
            print(f"\n📸 VISUAL PROCESSING SUMMARY")
            print("="*60)
            print(f"Total tweets visually processed: {visual_stats['total_visually_processed']}")
            print(f"Visual extraction failures: {visual_stats['total_visual_failures']}")
            print(f"Screenshots captured: {visual_stats['total_screenshots']}")
            print(f"Visual processing time: {visual_stats['total_visual_time']:.1f}s")
            
            if visual_stats['total_visually_processed'] > 0:
                success_rate = (visual_stats['total_visually_processed'] / 
                              (visual_stats['total_visually_processed'] + visual_stats['total_visual_failures'])) * 100
                print(f"Visual extraction success rate: {success_rate:.1f}%")
    
    def _generate_enhanced_summary(self, results: Dict[str, ProcessingResult], total_time: float) -> Dict[str, Any]:
        """Generate enhanced summary with visual processing statistics."""
        base_summary = super()._generate_summary(results, total_time)
        
        # Add visual processing statistics
        successful = [r for r in results.values() if r.success]
        
        visual_stats = {
            'total_visually_processed': sum(r.tweets_visually_processed for r in successful),
            'total_visual_failures': sum(r.visual_extraction_failures for r in successful),
            'total_screenshots': sum(r.total_screenshots_captured for r in successful),
            'total_visual_time': sum(r.visual_processing_time for r in successful),
        }
        
        base_summary['visual_stats'] = visual_stats
        base_summary['visual_extraction_enabled'] = self.config.enable_visual_extraction
        
        return base_summary


def main():
    """Main entry point for enhanced processing pipeline."""
    # Test accounts for comprehensive pipeline validation
    test_accounts = [
        'sama',           # Sam Altman - OpenAI
        'AndrewYNg',      # Andrew Ng - AI Education
        'DrJimFan',       # Jim Fan - Research
    ]
    
    print("🚀 Enhanced Tweet Processing Pipeline - Full Visual + Classification Test")
    print(f"Processing {len(test_accounts)} accounts with complete pipeline...")
    print("\n📋 Processing Pipeline:")
    print("   1. 📡 Tweet fetching from accounts")
    print("   2. 📸 Visual capture and screenshot analysis")
    print("   3. 🔤 Full text extraction using Gemini AI")
    print("   4. 📝 Summary generation")
    print("   5. 🏷️  L1/L2 classification")
    print("   6. 💾 Enhanced metadata generation")
    
    # Enhanced configuration with visual extraction
    config = ProcessingConfig(
        days_back=7,
        max_tweets_per_account=8,           # Moderate sample for thorough testing
        max_concurrent_accounts=1,          # Sequential to avoid rate limits
        enable_classification=True,         # Full classification pipeline
        enable_visual_extraction=True,      # 🚀 NEW: Enable visual extraction
        visual_extraction_batch_size=2,     # Small batches for stability
        zoom_percent=60,                    # Optimal zoom for text capture
        max_screenshots_per_tweet=3,        # Reasonable screenshot limit
        batch_size=2,                       # Small batches for rate limiting
        output_dir="outputs/development/enhanced"
    )
    
    print(f"\n⚙️  Enhanced Configuration:")
    print(f"   • Days back: {config.days_back}")
    print(f"   • Max tweets per account: {config.max_tweets_per_account}")
    print(f"   • Visual extraction: {config.enable_visual_extraction}")
    print(f"   • Browser zoom: {config.zoom_percent}%")
    print(f"   • Max screenshots per tweet: {config.max_screenshots_per_tweet}")
    print(f"   • Classification enabled: {config.enable_classification}")
    
    # Process accounts
    try:
        print(f"\n🎬 Starting enhanced pipeline test...")
        processor = EnhancedOptimizedTweetProcessor(config)
        results = processor.process_accounts(test_accounts)
        
        print(f"\n✅ Enhanced pipeline test completed successfully!")
        print(f"📁 Check results in: {processor.output_dir}")
        
        # Show detailed results
        summary = results['summary']
        print(f"\n📊 Enhanced Pipeline Results:")
        print(f"   • Accounts processed: {summary['successful_accounts']}/{summary['total_accounts']}")
        print(f"   • Total tweets fetched: {summary['total_tweets_fetched']}")
        
        if 'visual_stats' in summary:
            visual_stats = summary['visual_stats']
            print(f"   • Tweets visually processed: {visual_stats['total_visually_processed']}")
            print(f"   • Screenshots captured: {visual_stats['total_screenshots']}")
            print(f"   • Visual processing time: {visual_stats['total_visual_time']:.1f}s")
        
        print(f"   • Total tweets classified: {summary['total_tweets_classified']}")
        print(f"   • Categories found: {len(summary['unique_categories_found'])}")
        
        if summary['unique_categories_found']:
            for category in sorted(summary['unique_categories_found']):
                print(f"     - {category}")
        
        # Performance assessment
        if summary['total_tweets_fetched'] > 0:
            print(f"\n🎉 SUCCESS: Enhanced pipeline processed {summary['total_tweets_fetched']} tweets!")
            
            if 'visual_stats' in summary and summary['visual_stats']['total_visually_processed'] > 0:
                visual_success_rate = (summary['visual_stats']['total_visually_processed'] / 
                                     summary['total_tweets_fetched']) * 100
                print(f"📸 Visual extraction success rate: {visual_success_rate:.1f}%")
            
            print(f"\n📁 Enhanced results structure:")
            print(f"   • Original tweets: {processor.output_dir}/[account]/tweets_original.json")
            print(f"   • Enhanced tweets: {processor.output_dir}/[account]/tweets_enhanced.json")
            print(f"   • Classified tweets: {processor.output_dir}/[account]/tweets_classified.json")
            print(f"   • Enhanced metadata: {processor.output_dir}/[account]/metadata_enhanced.json")
        
    except KeyboardInterrupt:
        print("\n⏹️  Processing interrupted by user")
    except Exception as e:
        print(f"\n❌ Enhanced pipeline test failed: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main() 