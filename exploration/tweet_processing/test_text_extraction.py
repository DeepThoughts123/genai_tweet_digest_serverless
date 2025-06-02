#!/usr/bin/env python3
"""
Test Tweet Text Extraction Service

Demonstrates the TweetTextExtractor service by processing captured tweet screenshots
and extracting complete text content and summaries using Gemini 2.0 Flash.
"""

import sys
import os
import re
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# Add current path for imports
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'lambdas'))

from tweet_text_extractor import TweetTextExtractor
import boto3
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

def download_s3_captures_for_testing(s3_bucket: str, date_folder: str, account_name: str, temp_dir: str) -> str:
    """
    Download captured tweets from S3 to a temporary directory for testing.
    
    Args:
        s3_bucket: S3 bucket name
        date_folder: Date folder (YYYY-MM-DD)
        account_name: Twitter account name
        temp_dir: Temporary directory path
        
    Returns:
        Path to base directory (parent of visual_captures)
    """
    try:
        s3_client = boto3.client('s3')
        
        # Create local directory structure: temp_dir/visual_captures/date/account
        local_base = Path(temp_dir) / "visual_captures" / date_folder / account_name.lower()
        local_base.mkdir(parents=True, exist_ok=True)
        
        # List all objects for this account
        prefix = f"visual_captures/{date_folder}/{account_name.lower()}/"
        
        print(f"📥 Downloading captures from s3://{s3_bucket}/{prefix}")
        
        response = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix=prefix)
        
        if 'Contents' not in response:
            print(f"❌ No objects found with prefix: {prefix}")
            return None
        
        downloaded_files = 0
        for obj in response['Contents']:
            # Skip if it's just the prefix (directory)
            if obj['Key'].endswith('/'):
                continue
            
            # Extract relative path after the account folder
            relative_path = obj['Key'][len(prefix):]
            local_file_path = local_base / relative_path
            
            # Create parent directories
            local_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download the file
            s3_client.download_file(s3_bucket, obj['Key'], str(local_file_path))
            downloaded_files += 1
        
        print(f"✅ Downloaded {downloaded_files} files to {local_base}")
        # Return the base directory (parent of visual_captures)
        return str(temp_dir)
        
    except Exception as e:
        print(f"❌ Error downloading S3 captures: {e}")
        return None

def test_with_s3_captures():
    """
    Test the text extraction service with captures from S3.
    """
    # Get S3 bucket from environment
    s3_bucket = os.getenv('S3_BUCKET_TWEET_CAPTURED')
    if not s3_bucket:
        print("❌ S3_BUCKET_TWEET_CAPTURED environment variable not set!")
        print("💡 Please add S3_BUCKET_TWEET_CAPTURED=your-bucket-name to .env file")
        return False
    
    print("🧪 TESTING TWEET TEXT EXTRACTION SERVICE WITH S3 CAPTURES")
    print("=" * 70)
    print(f"🪣 S3 Bucket: {s3_bucket}")
    
    # Use today's date folder
    date_folder = datetime.now().strftime("%Y-%m-%d")
    test_accounts = ['minchoi', 'AndrewYNg']  # Accounts we know have captures
    
    # Create temporary directory for downloads
    temp_dir = tempfile.mkdtemp(prefix="tweet_extraction_test_")
    print(f"📁 Temporary directory: {temp_dir}")
    
    try:
        # Initialize the text extractor
        print(f"\n🔧 Initializing TweetTextExtractor...")
        extractor = TweetTextExtractor()
        
        # Test with each account
        for account_name in test_accounts:
            print(f"\n" + "=" * 70)
            print(f"🔄 TESTING ACCOUNT: @{account_name}")
            print("=" * 70)
            
            # Download S3 captures to temporary directory
            base_path = download_s3_captures_for_testing(s3_bucket, date_folder, account_name, temp_dir)
            
            if not base_path:
                print(f"⚠️ Skipping @{account_name} - no captures found or download failed")
                continue
            
            # Process the account captures
            print(f"\n📝 Processing text extraction for @{account_name}...")
            result = extractor.process_account_captures(base_path, account_name, date_folder)
            
            if result['success']:
                print(f"\n✅ TEXT EXTRACTION SUCCESS FOR @{account_name.upper()}!")
                print(f"   📊 Total folders: {result['total_folders']}")
                print(f"   ✅ Processed successfully: {result['processed_successfully']}")
                print(f"   ❌ Failed: {result['failed']}")
                
                # Show details of processed folders
                if result['processed_folders']:
                    print(f"\n📁 PROCESSED FOLDERS:")
                    for folder_info in result['processed_folders']:
                        status_emoji = "✅" if folder_info['status'] == 'success' else "❌"
                        print(f"   {status_emoji} {folder_info['folder']}")
                        
                        # Show a sample of extracted content
                        if folder_info['status'] == 'success':
                            account_path = Path(base_path) / "visual_captures" / date_folder / account_name.lower()
                            show_extracted_content_sample(str(account_path), folder_info['folder'])
                
            else:
                print(f"\n❌ TEXT EXTRACTION FAILED FOR @{account_name}!")
                print(f"   🔴 Error: {result.get('error', 'Unknown error')}")
        
        return True
        
    finally:
        # Clean up temporary directory
        print(f"\n🧹 Cleaning up temporary directory: {temp_dir}")
        shutil.rmtree(temp_dir, ignore_errors=True)

def show_extracted_content_sample(account_path: str, folder_name: str):
    """
    Show a sample of the extracted content from a processed folder.
    
    Args:
        account_path: Path to the account folder
        folder_name: Name of the specific tweet folder
    """
    try:
        folder_path = Path(account_path) / folder_name
        metadata_files = list(folder_path.glob("*metadata*.json"))
        
        if not metadata_files:
            return
        
        import json
        with open(metadata_files[0], 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        tweet_metadata = metadata.get('tweet_metadata', {})
        full_text = tweet_metadata.get('full_text')
        summary = tweet_metadata.get('summary')
        
        if full_text and summary:
            print(f"       📝 Extracted text: {full_text[:150]}{'...' if len(full_text) > 150 else ''}")
            print(f"       📄 Summary: {summary}")
        
    except Exception as e:
        print(f"       ⚠️ Could not show sample content: {e}")

def test_with_local_captures():
    """
    Test the text extraction service with local capture files.
    """
    print("🧪 TESTING TWEET TEXT EXTRACTION SERVICE WITH LOCAL CAPTURES")
    print("=" * 70)
    
    # Look for local visual captures in multiple locations
    base_paths = [
        ".",  # Current directory
        "..",  # Parent directory
        "../..",  # Grandparent directory
        "../visual_tweet_capture",  # Exploration folder
        os.path.expanduser("~/Desktop"),  # Desktop
        os.path.expanduser("~/Documents")  # Documents
    ]
    
    local_captures_base = None
    visual_captures_path = None
    
    for base_path in base_paths:
        potential_path = os.path.join(base_path, "visual_captures")
        if os.path.exists(potential_path):
            local_captures_base = base_path
            visual_captures_path = potential_path
            print(f"📁 Found local captures at: {potential_path}")
            break
    
    if not local_captures_base:
        print("⚠️ No local visual captures found. Tried:")
        for base_path in base_paths:
            potential_path = os.path.join(base_path, "visual_captures")
            print(f"   • {potential_path}")
        print("\n💡 You can:")
        print("   1. Run the S3 test instead")
        print("   2. Create a visual_captures folder with captured content")
        print("   3. Download captures from S3 manually")
        return False
    
    try:
        # Initialize the text extractor
        print(f"\n🔧 Initializing TweetTextExtractor...")
        extractor = TweetTextExtractor()
        
        # Check if this is date-based structure or direct account structure
        captures_path = Path(visual_captures_path)
        available_accounts = []
        
        # First, check for date-based structure (YYYY-MM-DD folders)
        date_folders = [d for d in captures_path.iterdir() if d.is_dir() and re.match(r'\d{4}-\d{2}-\d{2}', d.name)]
        
        if date_folders:
            print("📅 Detected date-based folder structure")
            # Date-based structure: visual_captures/YYYY-MM-DD/account/
            for date_folder in date_folders:
                for account_folder in date_folder.iterdir():
                    if account_folder.is_dir():
                        available_accounts.append((date_folder.name, account_folder.name))
        else:
            print("👤 Detected direct account folder structure") 
            # Direct account structure: visual_captures/account/
            for account_folder in captures_path.iterdir():
                if account_folder.is_dir():
                    # Use None to indicate direct structure
                    available_accounts.append((None, account_folder.name))
        
        if not available_accounts:
            print("❌ No account folders found in local captures")
            return False
        
        print(f"📊 Found {len(available_accounts)} account(s) to process:")
        for date, account in available_accounts:
            if date:
                print(f"   • @{account} ({date})")
            else:
                print(f"   • @{account} (direct structure)")
        
        # Process each account
        success_count = 0
        for date_folder, account_name in available_accounts:
            print(f"\n" + "=" * 70)
            if date_folder:
                print(f"🔄 PROCESSING: @{account_name} ({date_folder})")
            else:
                print(f"🔄 PROCESSING: @{account_name} (direct structure)")
            print("=" * 70)
            
            if date_folder:
                # Use the standard process_account_captures for date-based structure
                # Pass local_captures_base (parent of visual_captures), not visual_captures_path
                result = extractor.process_account_captures(local_captures_base, account_name, date_folder)
                account_path = Path(visual_captures_path) / date_folder / account_name.lower()
            else:
                # Handle direct account structure - create a temp structure for processing
                result = process_direct_account_structure(extractor, visual_captures_path, account_name)
                account_path = Path(visual_captures_path) / account_name.lower()
            
            if result['success']:
                print(f"\n✅ TEXT EXTRACTION SUCCESS FOR @{account_name.upper()}!")
                print(f"   📊 Total folders: {result['total_folders']}")
                print(f"   ✅ Processed successfully: {result['processed_successfully']}")
                print(f"   ❌ Failed: {result['failed']}")
                
                success_count += 1
                
                # Show sample extracted content
                if result.get('processed_folders'):
                    print(f"\n📝 SAMPLE EXTRACTED CONTENT:")
                    for folder_info in result['processed_folders'][:2]:  # Show first 2
                        if folder_info['status'] == 'success':
                            show_extracted_content_sample(str(account_path), folder_info['folder'])
            else:
                print(f"\n❌ TEXT EXTRACTION FAILED FOR @{account_name}!")
                print(f"   🔴 Error: {result.get('error', 'Unknown error')}")
        
        return success_count > 0
        
    except Exception as e:
        print(f"❌ Error during local testing: {e}")
        return False

def process_direct_account_structure(extractor: TweetTextExtractor, visual_captures_path: str, account_name: str) -> Dict[str, Any]:
    """
    Process account captures in direct structure (visual_captures/account/) without date folders.
    Creates a temporary date-based structure to work with the extractor.
    
    Args:
        extractor: TweetTextExtractor instance
        visual_captures_path: Path to visual_captures folder
        account_name: Account name
        
    Returns:
        Dictionary with processing results
    """
    try:
        # Create a temporary directory with date-based structure
        temp_dir = tempfile.mkdtemp(prefix="direct_structure_")
        temp_date = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # Create the expected structure: temp_dir/visual_captures/date/account
            temp_visual_captures = Path(temp_dir) / "visual_captures" / temp_date / account_name.lower()
            temp_visual_captures.mkdir(parents=True, exist_ok=True)
            
            # Create symlinks to the original tweet folders
            original_account_path = Path(visual_captures_path) / account_name.lower()
            
            if not original_account_path.exists():
                return {"success": False, "error": f"Account folder not found: {account_name}"}
            
            # Find tweet folders and create symlinks
            tweet_folders = []
            for item in original_account_path.iterdir():
                if item.is_dir() and (item.name.startswith('tweet_') or item.name.startswith('retweet_')):
                    # Create symlink
                    symlink_path = temp_visual_captures / item.name
                    symlink_path.symlink_to(item, target_is_directory=True)
                    tweet_folders.append(item.name)
            
            if not tweet_folders:
                return {"success": True, "processed": 0, "message": "No individual tweets to process"}
            
            print(f"📁 Created temporary structure with {len(tweet_folders)} tweet folders")
            
            # Use the extractor's standard method with the temporary structure
            result = extractor.process_account_captures(temp_dir, account_name, temp_date)
            
            print(f"✅ Processing complete for @{account_name}")
            
            return result
            
        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        print(f"Error processing direct account structure for @{account_name}: {e}")
        return {"success": False, "error": str(e)}

def test_single_folder():
    """
    Test the text extraction service with a single folder for debugging.
    """
    print("🧪 TESTING SINGLE FOLDER PROCESSING")
    print("=" * 70)
    
    # You can manually specify a folder path here for testing
    test_folder = input("Enter path to tweet folder (or press Enter to skip): ").strip()
    
    if not test_folder:
        print("⚠️ No folder specified, skipping single folder test")
        return True
    
    if not os.path.exists(test_folder):
        print(f"❌ Folder does not exist: {test_folder}")
        return False
    
    try:
        print(f"📁 Testing folder: {test_folder}")
        
        # Initialize the text extractor
        extractor = TweetTextExtractor()
        
        # Process the single folder
        success = extractor.process_tweet_folder(test_folder)
        
        if success:
            print(f"✅ Successfully processed folder!")
            show_extracted_content_sample(os.path.dirname(test_folder), os.path.basename(test_folder))
        else:
            print(f"❌ Failed to process folder")
        
        return success
        
    except Exception as e:
        print(f"❌ Error during single folder testing: {e}")
        return False

if __name__ == "__main__":
    print(f"🧪 Tweet Text Extraction Service - Testing Suite")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test options
    print("Choose test mode:")
    print("1. Test with S3 captures (recommended)")
    print("2. Test with local captures")
    print("3. Test single folder (debug mode)")
    print("4. Run all tests")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    success_count = 0
    total_tests = 0
    
    if choice == "1" or choice == "4":
        print(f"\n{'='*70}")
        print("RUNNING S3 CAPTURE TESTS")
        print('='*70)
        total_tests += 1
        if test_with_s3_captures():
            success_count += 1
    
    if choice == "2" or choice == "4":
        print(f"\n{'='*70}")
        print("RUNNING LOCAL CAPTURE TESTS")
        print('='*70)
        total_tests += 1
        if test_with_local_captures():
            success_count += 1
    
    if choice == "3" or choice == "4":
        print(f"\n{'='*70}")
        print("RUNNING SINGLE FOLDER TEST")
        print('='*70)
        total_tests += 1
        if test_single_folder():
            success_count += 1
    
    if choice not in ["1", "2", "3", "4"]:
        print("❌ Invalid choice")
        sys.exit(1)
    
    # Final summary
    print(f"\n{'='*70}")
    print(f"🎉 FINAL TEST SUMMARY")
    print('='*70)
    
    if total_tests > 0:
        print(f"✅ Successful tests: {success_count}/{total_tests}")
        print(f"❌ Failed tests: {total_tests - success_count}/{total_tests}")
        
        if success_count == total_tests:
            print(f"\n🎉 ALL TESTS PASSED!")
            print(f"✅ TweetTextExtractor is working correctly with Gemini 2.0 Flash")
            print(f"✅ Text extraction and summarization completed successfully")
            print(f"✅ Metadata files updated with extracted content")
        else:
            print(f"\n⚠️ Some tests failed - check logs above for details")
            print(f"💡 Common issues:")
            print(f"   - Check Gemini API key in .env file")
            print(f"   - Verify S3 bucket permissions")
            print(f"   - Ensure captured content exists")
            print(f"   - Check internet connectivity for API calls")
    else:
        print("No tests were run")
    
    print('='*70) 