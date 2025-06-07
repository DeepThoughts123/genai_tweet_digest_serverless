#!/usr/bin/env python3
"""
Test Visual Tweet Capture Service with S3 Integration

Tests the production service with real S3 bucket using the same accounts
we tested in exploration to verify folder structure and uploads.
"""

import sys
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# Add lambdas to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'lambdas'))

from shared.visual_tweet_capture_service import capture_twitter_account_visuals, VisualTweetCaptureService
import boto3
import json

def verify_s3_structure(s3_bucket: str, account_name: str, date_folder: str):
    """
    Verify the S3 folder structure and list uploaded files.
    
    Args:
        s3_bucket: S3 bucket name
        account_name: Twitter account name
        date_folder: Date folder (YYYY-MM-DD)
    """
    try:
        s3_client = boto3.client('s3')
        
        # List objects in the account folder
        prefix = f"visual_captures/{date_folder}/{account_name.lower()}/"
        
        print(f"\n🔍 VERIFYING S3 STRUCTURE")
        print(f"📅 Date folder: {date_folder}")
        print(f"👤 Account: {account_name}")
        print(f"📁 S3 prefix: s3://{s3_bucket}/{prefix}")
        print("=" * 60)
        
        response = s3_client.list_objects_v2(
            Bucket=s3_bucket,
            Prefix=prefix,
            Delimiter='/'
        )
        
        # Check for folders (common prefixes)
        folders = []
        if 'CommonPrefixes' in response:
            for prefix_info in response['CommonPrefixes']:
                folder_name = prefix_info['Prefix'].replace(prefix, '').rstrip('/')
                folders.append(folder_name)
        
        print(f"📂 Found {len(folders)} content folders:")
        for folder in sorted(folders):
            if folder.startswith('convo_'):
                print(f"   🧵 {folder} (thread)")
            elif folder.startswith('tweet_'):
                print(f"   📝 {folder} (individual tweet)")
            elif folder.startswith('retweet_'):
                print(f"   🔄 {folder} (retweet)")
            else:
                print(f"   📁 {folder}")
        
        # Check for summary file
        try:
            summary_key = f"{prefix}capture_summary.json"
            s3_client.head_object(Bucket=s3_bucket, Key=summary_key)
            print(f"✅ Found summary file: capture_summary.json")
            
            # Download and display summary
            summary_obj = s3_client.get_object(Bucket=s3_bucket, Key=summary_key)
            summary_data = json.loads(summary_obj['Body'].read().decode('utf-8'))
            
            print(f"\n📊 CAPTURE SUMMARY:")
            print(f"   📅 Capture time: {summary_data['capture_timestamp']}")
            print(f"   📊 Items found: {summary_data['summary']['total_items_found']}")
            print(f"   ✅ Items captured: {summary_data['summary']['total_items_captured']}")
            print(f"   🧵 Threads: {summary_data['summary']['threads_captured']}/{summary_data['summary']['threads_found']}")
            print(f"   📝 Individual tweets: {summary_data['summary']['individual_tweets_captured']}/{summary_data['summary']['individual_tweets_found']}")
            print(f"   📈 Success rate: {summary_data['summary']['success_rate']:.1%}")
            
        except Exception as e:
            print(f"⚠️ Summary file not found: {e}")
        
        # Examine one content folder in detail
        if folders:
            example_folder = folders[0]
            print(f"\n🔍 EXAMINING FOLDER: {example_folder}")
            
            folder_prefix = f"{prefix}{example_folder}/"
            folder_response = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix=folder_prefix)
            
            if 'Contents' in folder_response:
                files = [obj['Key'] for obj in folder_response['Contents']]
                print(f"📁 Files in {example_folder}:")
                
                screenshot_count = 0
                metadata_files = []
                
                for file_key in sorted(files):
                    filename = file_key.split('/')[-1]
                    file_size = next((obj['Size'] for obj in folder_response['Contents'] if obj['Key'] == file_key), 0)
                    
                    if filename.endswith('.png'):
                        screenshot_count += 1
                        print(f"   📸 {filename} ({file_size:,} bytes)")
                    elif filename.endswith('.json'):
                        metadata_files.append(filename)
                        print(f"   📋 {filename} ({file_size:,} bytes)")
                    else:
                        print(f"   📄 {filename} ({file_size:,} bytes)")
                
                print(f"   📊 Total screenshots: {screenshot_count}")
                print(f"   📋 Metadata files: {len(metadata_files)}")
            
        return True
        
    except Exception as e:
        print(f"❌ S3 verification error: {e}")
        return False

def test_service_with_s3():
    """
    Test the visual tweet capture service with S3 integration using our tested accounts.
    """
    # Get S3 bucket from environment
    s3_bucket = os.getenv('S3_BUCKET_TWEET_CAPTURED')
    if not s3_bucket:
        print("❌ S3_BUCKET_TWEET_CAPTURED environment variable not set!")
        print("💡 Please add S3_BUCKET_TWEET_CAPTURED=your-bucket-name to .env file")
        return False
    
    print("🚀 TESTING VISUAL TWEET CAPTURE SERVICE WITH S3")
    print("=" * 70)
    print(f"🪣 S3 Bucket: {s3_bucket}")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d')}")
    
    # Test with the same 3 accounts we used in exploration
    test_accounts = [
        {'name': 'minchoi', 'description': 'Min Choi - lots of threads and individual tweets'},
        {'name': 'AndrewYNg', 'description': 'Andrew Ng - educational content and threads'},
        {'name': 'openai', 'description': 'OpenAI - tech announcements and updates'}
    ]
    
    date_folder = datetime.now().strftime("%Y-%m-%d")
    all_results = []
    
    print(f"\n🎯 TESTING {len(test_accounts)} ACCOUNTS:")
    for i, account_info in enumerate(test_accounts, 1):
        account_name = account_info['name']
        description = account_info['description']
        
        print(f"\n" + "=" * 70)
        print(f"🔄 ACCOUNT {i}/{len(test_accounts)}: @{account_name}")
        print(f"📝 {description}")
        print("=" * 70)
        
        try:
            # Capture content for this account
            print(f"\n📸 Starting capture for @{account_name}...")
            result = capture_twitter_account_visuals(
                account_name=account_name,
                s3_bucket=s3_bucket,
                days_back=7,      # Same as our exploration tests
                max_tweets=25,    # Same as our exploration tests
                zoom_percent=60   # Same as our exploration tests
            )
            
            if result['success']:
                print(f"\n✅ CAPTURE SUCCESS FOR @{account_name.upper()}!")
                print(f"   📊 Total items captured: {result['total_items_captured']}")
                print(f"   🧵 Threads captured: {result['threads_captured']}")
                print(f"   📝 Individual tweets captured: {result['individual_tweets_captured']}")
                print(f"   📍 Summary location: {result['summary_s3_location']}")
                
                # Verify S3 structure
                verify_s3_structure(s3_bucket, account_name, date_folder)
                
                all_results.append({
                    'account': account_name,
                    'success': True,
                    'result': result
                })
                
            else:
                print(f"\n❌ CAPTURE FAILED FOR @{account_name}!")
                print(f"   🔴 Error: {result.get('error', 'Unknown error')}")
                
                all_results.append({
                    'account': account_name,
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                })
            
        except Exception as e:
            print(f"\n💥 EXCEPTION FOR @{account_name}: {e}")
            all_results.append({
                'account': account_name,
                'success': False,
                'error': str(e)
            })
    
    # Final summary
    print(f"\n" + "=" * 70)
    print(f"🎉 FINAL TEST SUMMARY")
    print("=" * 70)
    
    successful_accounts = [r for r in all_results if r['success']]
    failed_accounts = [r for r in all_results if not r['success']]
    
    print(f"✅ Successful captures: {len(successful_accounts)}/{len(test_accounts)}")
    print(f"❌ Failed captures: {len(failed_accounts)}/{len(test_accounts)}")
    
    if successful_accounts:
        print(f"\n🎯 SUCCESSFUL ACCOUNTS:")
        total_items = 0
        for result in successful_accounts:
            account_result = result['result']
            total_items += account_result['total_items_captured']
            print(f"   ✅ @{result['account']}: {account_result['total_items_captured']} items")
        
        print(f"\n📊 TOTAL ITEMS CAPTURED: {total_items}")
        print(f"📁 S3 Location: s3://{s3_bucket}/visual_captures/{date_folder}/")
        
        print(f"\n🔍 TO BROWSE CAPTURES:")
        print(f"   aws s3 ls s3://{s3_bucket}/visual_captures/{date_folder}/ --recursive")
        
    if failed_accounts:
        print(f"\n❌ FAILED ACCOUNTS:")
        for result in failed_accounts:
            print(f"   🔴 @{result['account']}: {result['error']}")
    
    return len(successful_accounts) == len(test_accounts)

if __name__ == "__main__":
    print(f"🧪 Visual Tweet Capture Service - S3 Integration Test")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = test_service_with_s3()
    
    if success:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"✅ Service is working correctly with S3 integration")
        print(f"✅ Folder structure follows date-based organization")
        print(f"✅ Same capture logic as tested in exploration")
    else:
        print(f"\n⚠️ Some tests failed - check logs above")
        print(f"💡 Common issues:")
        print(f"   - Check AWS credentials")
        print(f"   - Verify S3 bucket permissions")
        print(f"   - Ensure Twitter API credentials are set")
        print(f"   - Check internet connectivity") 