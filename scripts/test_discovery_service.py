#!/usr/bin/env python3
"""
Test script for the updated Twitter Account Discovery Service

This script tests the enhanced service with:
- Image-based profile extraction using Gemini AI
- Twitter login functionality
- Following page analysis with screenshots
"""

import sys
import os
import logging

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.shared.twitter_account_discovery_service import TwitterAccountDiscoveryService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_discovery_service():
    """Test the updated discovery service with image-based extraction."""
    logger.info("🧪 Testing Twitter Account Discovery Service with Image-based Extraction")
    
    # Test with a well-known AI account
    seed_urls = ["https://x.com/AndrewYNg"]
    
    # Create service instance
    output_dir = "./test_discovery_output"
    service = TwitterAccountDiscoveryService(output_dir=output_dir)
    
    try:
        logger.info("📋 Test Configuration:")
        logger.info(f"  - Seed URLs: {seed_urls}")
        logger.info(f"  - Max iterations: 0 (profile extraction only)")
        logger.info(f"  - Output directory: {output_dir}")
        logger.info(f"  - Gemini API: {'✅ Available' if service.genai_model else '❌ Not configured'}")
        
        # Run discovery with 0 iterations (just test profile extraction)
        result = service.discover_accounts(
            seed_urls=seed_urls,
            max_iterations=0,  # Just test profile processing
            max_profiles_per_iteration=1
        )
        
        # Display results
        logger.info("\n" + "=" * 60)
        logger.info("🎉 TEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"📊 Profiles processed: {result.total_profiles_processed}")
        logger.info(f"✅ GenAI-relevant: {len(result.genai_relevant_profiles)}")
        logger.info(f"❌ Non-relevant: {len(result.non_relevant_profiles)}")
        logger.info(f"⚠️  Failed: {len(result.failed_profiles)}")
        
        if result.genai_relevant_profiles:
            profile = result.genai_relevant_profiles[0]
            logger.info(f"\n📋 Profile Details for {profile.handle}:")
            logger.info(f"  - Description: {profile.description[:100]}{'...' if len(profile.description) > 100 else ''}")
            logger.info(f"  - Followers: {profile.followers_count or 'Unknown'}")
            logger.info(f"  - Following: {profile.following_count or 'Unknown'}")
            logger.info(f"  - GenAI Classification: {profile.genai_classification_reason[:80]}{'...' if len(profile.genai_classification_reason or '') > 80 else ''}")
            
            if profile.discovered_following:
                logger.info(f"  - Following accounts discovered: {len(profile.discovered_following)}")
                logger.info(f"  - Sample following: {profile.discovered_following[:5]}")
        
        if result.failed_profiles:
            logger.info(f"\n⚠️  Failures:")
            for failure in result.failed_profiles:
                logger.info(f"  • {failure['url']}: {failure['error']}")
        
        logger.info(f"\n💾 Results saved to: {result.output_file_path}")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    logger.info("Starting Twitter Account Discovery Service Test")
    
    # Check environment
    gemini_key = os.getenv('GEMINI_API_KEY')
    if not gemini_key:
        logger.warning("⚠️  GEMINI_API_KEY not set. Service will use fallback classification.")
    else:
        logger.info("✅ GEMINI_API_KEY found")
    
    # Run test
    success = test_discovery_service()
    
    if success:
        logger.info("✅ Test completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 