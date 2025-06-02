#!/usr/bin/env python3
"""
Capture and Extract Tweet Processing Pipeline

Step 1: Capture tweets from specified accounts using visual tweet capturer
Step 2: Run text extraction on captured content using Gemini 2.0 Flash

This script demonstrates the complete pipeline from tweet capture to text extraction.
"""

import sys
import os
import argparse
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# Add paths for imports
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'lambdas'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'visual_tweet_capture'))

from tweet_text_extractor import TweetTextExtractor
from visual_tweet_capturer import VisualTweetCapturer
from shared.tweet_services import TweetFetcher

def step1_capture_tweets(accounts, days_back, max_tweets_per_account, zoom_percent=100):
    """
    Step 1: Capture tweets from specified accounts.
    
    Args:
        accounts: List of account usernames to process
        days_back: Number of days back to search
        max_tweets_per_account: Maximum tweets per account
        zoom_percent: Browser zoom percentage for screenshots
    """
    print("🎯 STEP 1: CAPTURING TWEETS FROM SPECIFIED ACCOUNTS")
    print("=" * 70)
    
    print(f"📋 Configuration:")
    print(f"   👥 Accounts: {', '.join(['@' + acc for acc in accounts])}")
    print(f"   📅 Days back: {days_back} days")
    print(f"   📊 Max tweets per account: {max_tweets_per_account}")
    print(f"   🔍 Browser zoom: {zoom_percent}%")
    
    # Initialize services
    print(f"\n🔧 Initializing services...")
    try:
        tweet_fetcher = TweetFetcher()
        visual_capturer = VisualTweetCapturer(headless=True)
        print("✅ Services initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        print("💡 Please check your Twitter API credentials in .env file")
        return False
    
    total_captured = 0
    total_failed = 0
    
    # Process each account
    for account in accounts:
        print(f"\n" + "=" * 70)
        print(f"🔄 PROCESSING ACCOUNT: @{account}")
        print("=" * 70)
        
        # Step 1.1: Fetch recent tweet URLs
        print(f"📡 Fetching recent tweets for @{account}...")
        tweet_urls = tweet_fetcher.fetch_recent_tweets(
            username=account,
            days_back=days_back,
            max_tweets=max_tweets_per_account
        )
        
        if not tweet_urls:
            print(f"⚠️ No tweets found for @{account}")
            continue
        
        print(f"✅ Found {len(tweet_urls)} tweets to capture")
        
        # Step 1.2: Capture each tweet visually with specified zoom
        for i, tweet_url in enumerate(tweet_urls, 1):
            print(f"\n📸 Capturing tweet {i}/{len(tweet_urls)}")
            print(f"🔗 URL: {tweet_url}")
            print(f"🔍 Using {zoom_percent}% browser zoom")
            
            try:
                # Set the zoom percentage for this capture
                result = visual_capturer.capture_tweet_visually(tweet_url, zoom_percent=zoom_percent)
                
                if result:
                    print(f"✅ Successfully captured tweet {i}")
                    print(f"   📁 Saved to: {result['output_directory']}")
                    print(f"   📸 Screenshots: {result['screenshots']['count']}")
                    total_captured += 1
                else:
                    print(f"❌ Failed to capture tweet {i}")
                    total_failed += 1
                    
            except Exception as e:
                print(f"❌ Error capturing tweet {i}: {e}")
                total_failed += 1
            
            # Small delay between captures to be respectful
            import time
            time.sleep(2)
    
    print(f"\n" + "=" * 70)
    print(f"🎉 STEP 1 COMPLETE - TWEET CAPTURE SUMMARY")
    print("=" * 70)
    print(f"✅ Successfully captured: {total_captured} tweets")
    print(f"❌ Failed captures: {total_failed} tweets")
    print(f"📊 Total processed: {total_captured + total_failed} tweets")
    
    if total_captured > 0:
        print(f"\n📁 Captured tweets are stored in:")
        print(f"   visual_captures/[account]/tweet_* folders")
        print(f"   visual_captures/[account]/retweet_* folders")
        print(f"   visual_captures/[account]/convo_* folders")
        return True
    else:
        print(f"\n⚠️ No tweets were captured successfully")
        return False

def step2_extract_text():
    """
    Step 2: Run text extraction on captured tweets in local folder.
    """
    print(f"\n" + "=" * 70)
    print("🎯 STEP 2: EXTRACTING TEXT FROM CAPTURED TWEETS")
    print("=" * 70)
    
    # Initialize text extractor
    print("🔧 Initializing TweetTextExtractor...")
    try:
        extractor = TweetTextExtractor()
        print("✅ Text extractor initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize text extractor: {e}")
        print("💡 Please check your Gemini API key in .env file")
        return False
    
    # Check for local visual captures
    visual_captures_path = "visual_captures"
    if not os.path.exists(visual_captures_path):
        # Check in parent directory (visual_tweet_capture folder)
        visual_captures_path = "../visual_tweet_capture/visual_captures"
        if not os.path.exists(visual_captures_path):
            print(f"❌ No visual captures found!")
            print(f"💡 Expected to find captures in:")
            print(f"   • visual_captures/")
            print(f"   • ../visual_tweet_capture/visual_captures/")
            return False
    
    print(f"📁 Found visual captures at: {visual_captures_path}")
    
    # Process all accounts in the visual captures folder
    from pathlib import Path
    captures_path = Path(visual_captures_path)
    account_folders = [d for d in captures_path.iterdir() if d.is_dir()]
    
    if not account_folders:
        print("❌ No account folders found in visual captures")
        return False
    
    print(f"📊 Found {len(account_folders)} account(s) to process:")
    for account_folder in account_folders:
        print(f"   • @{account_folder.name}")
    
    success_count = 0
    
    # Process each account
    for account_folder in account_folders:
        account_name = account_folder.name
        print(f"\n" + "=" * 70)
        print(f"🔄 PROCESSING TEXT EXTRACTION: @{account_name}")
        print("=" * 70)
        
        # Count tweet folders to process
        tweet_folders = []
        for item in account_folder.iterdir():
            if item.is_dir() and (item.name.startswith('tweet_') or item.name.startswith('retweet_')):
                tweet_folders.append(item)
        
        if not tweet_folders:
            print(f"⚠️ No individual tweet folders found for @{account_name}")
            continue
        
        print(f"🔍 Found {len(tweet_folders)} tweet folders to process")
        
        # Process each tweet folder
        processed_successfully = 0
        failed = 0
        
        for tweet_folder in tweet_folders:
            print(f"\n📝 Processing: {tweet_folder.name}")
            
            success = extractor.process_tweet_folder(str(tweet_folder))
            
            if success:
                processed_successfully += 1
                print(f"   ✅ Successfully extracted text and summary")
                
                # Show sample of extracted content
                try:
                    import json
                    metadata_files = list(tweet_folder.glob("*metadata*.json"))
                    if metadata_files:
                        with open(metadata_files[0], 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        tweet_metadata = metadata.get('tweet_metadata', {})
                        full_text = tweet_metadata.get('full_text', '')
                        summary = tweet_metadata.get('summary', '')
                        
                        if full_text and summary:
                            print(f"   📝 Text: {full_text[:100]}{'...' if len(full_text) > 100 else ''}")
                            print(f"   📄 Summary: {summary}")
                except Exception as e:
                    print(f"   ⚠️ Could not show extracted content: {e}")
            else:
                failed += 1
                print(f"   ❌ Failed to extract text")
        
        print(f"\n✅ ACCOUNT PROCESSING COMPLETE FOR @{account_name}")
        print(f"   📊 Processed successfully: {processed_successfully}/{len(tweet_folders)}")
        print(f"   ❌ Failed: {failed}")
        
        if processed_successfully > 0:
            success_count += 1
    
    print(f"\n" + "=" * 70)
    print(f"🎉 STEP 2 COMPLETE - TEXT EXTRACTION SUMMARY")
    print("=" * 70)
    print(f"✅ Accounts processed successfully: {success_count}/{len(account_folders)}")
    
    if success_count > 0:
        print(f"\n💾 Updated metadata files contain:")
        print(f"   • full_text: Complete extracted text from screenshots")
        print(f"   • summary: AI-generated 1-2 sentence summary")
        print(f"   • extraction_timestamp: When extraction was performed")
        return True
    else:
        print(f"\n⚠️ No accounts were processed successfully")
        return False

def main(accounts, days_back, max_tweets, zoom_percent):
    """
    Main function to run the complete pipeline.
    
    Args:
        accounts: List of account usernames
        days_back: Number of days back to search
        max_tweets: Maximum tweets per account
        zoom_percent: Browser zoom percentage for screenshots
    """
    print("🚀 TWEET CAPTURE AND TEXT EXTRACTION PIPELINE")
    print("📅 " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 70)
    
    print("📋 PIPELINE OVERVIEW:")
    print(f"   1. Capture tweets from {', '.join(['@' + acc for acc in accounts])} (last {days_back} days, max {max_tweets} each)")
    print("   2. Run text extraction on captured content using Gemini 2.0 Flash")
    print("   3. Update metadata files with extracted text and summaries")
    print(f"   4. Use {zoom_percent}% browser zoom for screenshots")
    
    # Ask user if they want to proceed
    proceed = input(f"\nProceed with pipeline? (y/n): ").strip().lower()
    if proceed not in ['y', 'yes']:
        print("Pipeline cancelled.")
        return
    
    # Step 1: Capture tweets
    capture_success = step1_capture_tweets(accounts, days_back, max_tweets, zoom_percent)
    
    if not capture_success:
        print("\n❌ Tweet capture failed. Cannot proceed to text extraction.")
        print("💡 Please check:")
        print("   - Twitter API credentials in .env file")
        print("   - Internet connectivity")
        print("   - Chrome browser installation")
        return
    
    # Small delay between steps
    import time
    time.sleep(3)
    
    # Step 2: Extract text
    extraction_success = step2_extract_text()
    
    # Final summary
    print(f"\n" + "=" * 70)
    print(f"🏁 PIPELINE COMPLETE")
    print("=" * 70)
    
    if capture_success and extraction_success:
        print(f"🎉 SUCCESS! Complete pipeline executed successfully")
        print(f"✅ Tweets captured and text extracted")
        print(f"✅ Metadata files updated with extracted content")
        print(f"\n📁 Check visual_captures/ folder for results")
        print(f"💡 Each tweet folder now contains:")
        print(f"   • Screenshots (*.png) at {zoom_percent}% zoom")
        print(f"   • Original metadata (capture_metadata.json)")
        print(f"   • Enhanced metadata with extracted text")
    elif capture_success:
        print(f"⚠️ PARTIAL SUCCESS: Tweets captured but text extraction failed")
        print(f"💡 You can run text extraction separately later")
    else:
        print(f"❌ PIPELINE FAILED: Could not capture tweets")
    
    print("=" * 70)

if __name__ == "__main__":
    # Custom formatter to show both defaults and examples
    class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
        pass
    
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Tweet Capture and Text Extraction Pipeline",
        epilog="""
Examples:
  # Default: Elon Musk, 7 days, 25 tweets, 50% zoom
  python capture_and_extract.py
  
  # Multiple accounts with custom settings
  python capture_and_extract.py --accounts elonmusk openai andrewyng --days-back 10 --max-tweets 30 --zoom-percent 75
  
  # Quick run without confirmation prompt
  python capture_and_extract.py --accounts minchoi --no-confirm
  
  # High zoom for detailed screenshots
  python capture_and_extract.py --accounts elonmusk --zoom-percent 125 --days-back 3
        """,
        formatter_class=CustomFormatter
    )
    
    parser.add_argument(
        '--accounts', 
        nargs='+', 
        default=['elonmusk'],
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
        default=25,
        help='Maximum number of tweets to capture per account'
    )
    
    parser.add_argument(
        '--zoom-percent', 
        type=int, 
        default=50,
        choices=range(25, 201, 25),
        help='Browser zoom percentage for screenshots (25-200)'
    )
    
    parser.add_argument(
        '--no-confirm',
        action='store_true',
        help='Skip confirmation prompt and run immediately'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    print("🎯 TWEET CAPTURE AND TEXT EXTRACTION PIPELINE")
    print("=" * 50)
    print(f"📋 Configuration:")
    print(f"   👥 Accounts: {', '.join(['@' + acc for acc in args.accounts])}")
    print(f"   📅 Days back: {args.days_back}")
    print(f"   📊 Max tweets per account: {args.max_tweets}")
    print(f"   🔍 Browser zoom: {args.zoom_percent}%")
    print("=" * 50)
    
    # Override confirmation if --no-confirm is used
    if args.no_confirm:
        # Modify main to skip confirmation
        def main_no_confirm(accounts, days_back, max_tweets, zoom_percent):
            """Main function without confirmation prompt."""
            print("🚀 TWEET CAPTURE AND TEXT EXTRACTION PIPELINE")
            print("📅 " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            print("=" * 70)
            
            print("📋 PIPELINE OVERVIEW:")
            print(f"   1. Capture tweets from {', '.join(['@' + acc for acc in accounts])} (last {days_back} days, max {max_tweets} each)")
            print("   2. Run text extraction on captured content using Gemini 2.0 Flash")
            print("   3. Update metadata files with extracted text and summaries")
            print(f"   4. Use {zoom_percent}% browser zoom for screenshots")
            
            # Step 1: Capture tweets
            capture_success = step1_capture_tweets(accounts, days_back, max_tweets, zoom_percent)
            
            if not capture_success:
                print("\n❌ Tweet capture failed. Cannot proceed to text extraction.")
                print("💡 Please check:")
                print("   - Twitter API credentials in .env file")
                print("   - Internet connectivity")
                print("   - Chrome browser installation")
                return
            
            # Small delay between steps
            import time
            time.sleep(3)
            
            # Step 2: Extract text
            extraction_success = step2_extract_text()
            
            # Final summary
            print(f"\n" + "=" * 70)
            print(f"🏁 PIPELINE COMPLETE")
            print("=" * 70)
            
            if capture_success and extraction_success:
                print(f"🎉 SUCCESS! Complete pipeline executed successfully")
                print(f"✅ Tweets captured and text extracted")
                print(f"✅ Metadata files updated with extracted content")
                print(f"\n📁 Check visual_captures/ folder for results")
                print(f"💡 Each tweet folder now contains:")
                print(f"   • Screenshots (*.png) at {zoom_percent}% zoom")
                print(f"   • Original metadata (capture_metadata.json)")
                print(f"   • Enhanced metadata with extracted text")
            elif capture_success:
                print(f"⚠️ PARTIAL SUCCESS: Tweets captured but text extraction failed")
                print(f"💡 You can run text extraction separately later")
            else:
                print(f"❌ PIPELINE FAILED: Could not capture tweets")
            
            print("=" * 70)
        
        # Run without confirmation
        main_no_confirm(args.accounts, args.days_back, args.max_tweets, args.zoom_percent)
    else:
        # Run with confirmation
        main(args.accounts, args.days_back, args.max_tweets, args.zoom_percent) 