#!/usr/bin/env python3
"""
CLI script for discovering Twitter accounts in the generative AI field.

Usage:
    python scripts/discover_accounts.py --seed "https://x.com/AndrewYNg" --max-iterations 1
    python scripts/discover_accounts.py --seed "https://x.com/AndrewYNg" --seed "https://x.com/karpathy" --max-iterations 1
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.shared.twitter_account_discovery_service import discover_twitter_accounts, TwitterAccountDiscoveryService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Discover influential Twitter accounts in the generative AI field",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/discover_accounts.py --seed "https://x.com/AndrewYNg" --max-iterations 1
  python scripts/discover_accounts.py --seed "https://x.com/AndrewYNg" --seed "https://x.com/karpathy" --max-iterations 1
  python scripts/discover_accounts.py --seed "https://x.com/OpenAI" --output-dir "./results" --max-iterations 0
        """
    )
    
    parser.add_argument(
        '--seed', 
        action='append',
        required=True,
        help='Seed Twitter profile URL (can be specified multiple times)'
    )
    
    parser.add_argument(
        '--max-iterations',
        type=int,
        default=1,
        help='Maximum number of discovery iterations (default: 1)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='./twitter_discovery_output',
        help='Output directory for results (default: ./twitter_discovery_output)'
    )
    
    parser.add_argument(
        '--max-profiles-per-iteration',
        type=int,
        default=10,
        help='Maximum profiles to process per iteration (default: 10)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate environment variables
    logger.info("Checking environment variables...")
    gemini_key = os.getenv('GEMINI_API_KEY')
    if not gemini_key:
        logger.warning("GEMINI_API_KEY not set. Will use fallback keyword-based classification.")
    else:
        logger.info("✅ GEMINI_API_KEY found")
    
    # Display configuration
    logger.info("=" * 60)
    logger.info("Twitter Account Discovery Configuration")
    logger.info("=" * 60)
    logger.info(f"Seed URLs: {args.seed}")
    logger.info(f"Max iterations: {args.max_iterations}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Max profiles per iteration: {args.max_profiles_per_iteration}")
    logger.info(f"AI Classification: {'Gemini API' if gemini_key else 'Keyword-based fallback'}")
    logger.info("=" * 60)
    
    # Confirm before starting
    if not args.verbose:
        try:
            confirmation = input("\nProceed with discovery? [y/N]: ").strip().lower()
            if confirmation not in ['y', 'yes']:
                logger.info("Discovery cancelled by user")
                return
        except KeyboardInterrupt:
            logger.info("\nDiscovery cancelled by user")
            return
    
    # Start discovery
    start_time = datetime.now()
    logger.info(f"\n🚀 Starting discovery at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        result = discover_twitter_accounts(
            seed_urls=args.seed,
            max_iterations=args.max_iterations,
            output_dir=args.output_dir
        )
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Display results
        logger.info("\n" + "=" * 60)
        logger.info("🎉 DISCOVERY COMPLETE!")
        logger.info("=" * 60)
        logger.info(f"⏱️  Duration: {duration}")
        logger.info(f"📊 Total iterations: {result.total_iterations}")
        logger.info(f"🔍 Profiles processed: {result.total_profiles_processed}")
        logger.info(f"✅ GenAI-relevant profiles: {len(result.genai_relevant_profiles)}")
        logger.info(f"❌ Non-relevant profiles: {len(result.non_relevant_profiles)}")
        logger.info(f"⚠️  Failed profiles: {len(result.failed_profiles)}")
        logger.info(f"💾 Results saved to: {result.output_file_path}")
        
        # Display GenAI-relevant profiles
        if result.genai_relevant_profiles:
            logger.info("\n📋 GenAI-Relevant Profiles Found:")
            logger.info("-" * 40)
            for i, profile in enumerate(result.genai_relevant_profiles, 1):
                logger.info(f"{i:2d}. {profile.handle} ({profile.username})")
                logger.info(f"     Description: {profile.description[:100]}{'...' if len(profile.description) > 100 else ''}")
                logger.info(f"     Followers: {profile.followers_count or 'Unknown'}")
                if profile.discovered_following:
                    logger.info(f"     Following GenAI accounts: {len(profile.discovered_following)}")
                logger.info(f"     Classification: {profile.genai_classification_reason[:80]}{'...' if len(profile.genai_classification_reason or '') > 80 else ''}")
                logger.info("")
        
        # Display non-relevant profiles (brief)
        if result.non_relevant_profiles:
            logger.info(f"\n❌ Non-Relevant Profiles ({len(result.non_relevant_profiles)}):")
            for profile in result.non_relevant_profiles:
                logger.info(f"   • {profile.handle}: {profile.genai_classification_reason[:60]}{'...' if len(profile.genai_classification_reason or '') > 60 else ''}")
        
        # Display failures
        if result.failed_profiles:
            logger.info(f"\n⚠️  Failed Profiles ({len(result.failed_profiles)}):")
            for failure in result.failed_profiles:
                logger.info(f"   • {failure['url']}: {failure['error']}")
        
        logger.info(f"\n📁 Full results available in: {result.output_file_path}")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("\n\n⏹️  Discovery interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Discovery failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 