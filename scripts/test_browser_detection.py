#!/usr/bin/env python3
"""
Simple test script to diagnose Twitter browser detection issues

This script tests:
1. Basic browser setup
2. Twitter access without login
3. Detection of "browser not supported" messages
4. Fallback configurations
"""

import sys
import os
import logging
import time

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.shared.twitter_account_discovery_service import TwitterAccountDiscoveryService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_browser_setup():
    """Test if we can set up a browser that Twitter accepts."""
    logger.info("🧪 Testing Browser Setup for Twitter Access")
    
    service = TwitterAccountDiscoveryService(output_dir="./test_browser_output")
    
    try:
        # Test main browser setup
        logger.info("\n1️⃣ Testing main browser setup...")
        if service.setup_browser():
            logger.info("✅ Main browser setup successful")
            
            # Test Twitter access
            logger.info("\n2️⃣ Testing Twitter access...")
            service.driver.get("https://x.com")
            time.sleep(5)
            
            page_source = service.driver.page_source
            current_url = service.driver.current_url
            
            logger.info(f"📄 Current URL: {current_url}")
            
            if "This browser is no longer supported" in page_source:
                logger.error("❌ Twitter detected browser as unsupported")
                logger.info("📸 Taking screenshot for debugging...")
                
                # Take screenshot for debugging
                os.makedirs("./test_browser_output", exist_ok=True)
                screenshot_path = "./test_browser_output/browser_detection_error.png"
                service.driver.save_screenshot(screenshot_path)
                logger.info(f"Screenshot saved to: {screenshot_path}")
                
                # Try fallback
                logger.info("\n3️⃣ Testing fallback browser configurations...")
                if service._setup_browser_fallback():
                    logger.info("✅ Fallback browser setup successful")
                    
                    service.driver.get("https://x.com")
                    time.sleep(5)
                    
                    if "This browser is no longer supported" not in service.driver.page_source:
                        logger.info("✅ Fallback browser bypassed detection!")
                        return True
                    else:
                        logger.error("❌ Fallback browser still detected")
                        return False
                else:
                    logger.error("❌ All fallback configurations failed")
                    return False
            else:
                logger.info("✅ Twitter access successful - no detection issues")
                
                # Test profile access
                logger.info("\n3️⃣ Testing profile page access...")
                test_profile = "https://x.com/elonmusk"
                service.driver.get(test_profile)
                time.sleep(5)
                
                if "This browser is no longer supported" not in service.driver.page_source:
                    logger.info("✅ Profile page access successful")
                    
                    # Take screenshot of successful profile access
                    screenshot_path = "./test_browser_output/successful_profile_access.png"
                    service.driver.save_screenshot(screenshot_path)
                    logger.info(f"Success screenshot saved to: {screenshot_path}")
                    
                    return True
                else:
                    logger.error("❌ Profile page shows browser detection")
                    return False
        else:
            logger.error("❌ Main browser setup failed")
            
            # Try fallback immediately
            logger.info("\n2️⃣ Main setup failed, testing fallback configurations...")
            if service._setup_browser_fallback():
                logger.info("✅ Fallback browser setup successful")
                return True
            else:
                logger.error("❌ All browser configurations failed")
                return False
                
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        service.cleanup_browser()

def main():
    """Main test function."""
    logger.info("Starting Browser Detection Test for Twitter/X")
    
    # Run test
    success = test_browser_setup()
    
    if success:
        logger.info("\n✅ Browser setup test PASSED - Twitter access should work!")
        logger.info("💡 You can now run the main discovery service")
        sys.exit(0)
    else:
        logger.error("\n❌ Browser setup test FAILED - Twitter is blocking our browser")
        logger.info("💡 Possible solutions:")
        logger.info("   - Try running on a different machine/environment")
        logger.info("   - Use a VPN with a different IP address")
        logger.info("   - Wait and try again later (rate limiting)")
        logger.info("   - Consider using Twitter API directly instead of scraping")
        sys.exit(1)

if __name__ == "__main__":
    main() 