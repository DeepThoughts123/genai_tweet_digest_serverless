#!/usr/bin/env python3
"""
Reorganize Captured Tweets

Move tweets from the "unknown" folder to proper account-based folders
by extracting account names from the tweet URLs in metadata files.
"""

import os
import json
import shutil
import re
from pathlib import Path

def extract_username_from_url(tweet_url: str) -> str:
    """
    Extract username from tweet URL.
    
    Args:
        tweet_url: Tweet URL in format https://twitter.com/username/status/tweet_id
        
    Returns:
        Username without @ symbol, or "unknown" if extraction fails
    """
    # Pattern to match Twitter URL: https://twitter.com/username/status/tweet_id
    match = re.search(r'twitter\.com/([^/]+)/status/', tweet_url)
    if match:
        return match.group(1)
    
    # Also try x.com format
    match = re.search(r'x\.com/([^/]+)/status/', tweet_url)
    if match:
        return match.group(1)
    
    return "unknown"

def reorganize_captures():
    """
    Reorganize captured tweets from unknown folder to proper account folders.
    """
    print("🔄 REORGANIZING CAPTURED TWEETS")
    print("=" * 60)
    
    # Check if unknown folder exists
    unknown_folder = Path("visual_captures/unknown")
    if not unknown_folder.exists():
        print("❌ No unknown folder found to reorganize")
        return False
    
    # Get all tweet folders in unknown
    tweet_folders = [d for d in unknown_folder.iterdir() if d.is_dir()]
    if not tweet_folders:
        print("❌ No tweet folders found in unknown directory")
        return False
    
    print(f"📊 Found {len(tweet_folders)} tweet folders to reorganize")
    
    moved_count = 0
    failed_count = 0
    
    for tweet_folder in tweet_folders:
        print(f"\n📁 Processing: {tweet_folder.name}")
        
        # Find metadata file
        metadata_files = list(tweet_folder.glob("*metadata*.json"))
        if not metadata_files:
            print(f"   ⚠️ No metadata file found, skipping")
            failed_count += 1
            continue
        
        try:
            # Load metadata to get tweet URL
            with open(metadata_files[0], 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Get tweet URL from metadata
            tweet_url = metadata.get('tweet_url')
            if not tweet_url:
                # Try api_metadata
                api_metadata = metadata.get('api_metadata', {})
                if 'id' in api_metadata and api_metadata['id'] != 'unknown':
                    # Reconstruct URL - need to find account name first
                    author = api_metadata.get('author', {})
                    username = author.get('username', 'unknown')
                    if username != 'unknown':
                        tweet_url = f"https://twitter.com/{username}/status/{api_metadata['id']}"
                    else:
                        print(f"   ⚠️ No tweet URL or username found in metadata, skipping")
                        failed_count += 1
                        continue
                else:
                    print(f"   ⚠️ No tweet URL found in metadata, skipping")
                    failed_count += 1
                    continue
            
            # Extract account name from URL
            account_name = extract_username_from_url(tweet_url)
            if account_name == "unknown":
                print(f"   ⚠️ Could not extract account name from URL: {tweet_url}")
                failed_count += 1
                continue
            
            print(f"   📝 Detected account: @{account_name}")
            print(f"   🔗 Tweet URL: {tweet_url}")
            
            # Create target account folder
            target_account_folder = Path(f"visual_captures/{account_name.lower()}")
            target_account_folder.mkdir(parents=True, exist_ok=True)
            
            # Create target tweet folder path
            target_tweet_folder = target_account_folder / tweet_folder.name
            
            # Check if target already exists
            if target_tweet_folder.exists():
                print(f"   ⚠️ Target already exists: {target_tweet_folder}")
                print(f"   🔄 Removing existing target and moving")
                shutil.rmtree(target_tweet_folder)
            
            # Move the folder
            shutil.move(str(tweet_folder), str(target_tweet_folder))
            print(f"   ✅ Moved to: {target_tweet_folder}")
            moved_count += 1
            
        except Exception as e:
            print(f"   ❌ Error processing {tweet_folder.name}: {e}")
            failed_count += 1
    
    print(f"\n" + "=" * 60)
    print(f"🎉 REORGANIZATION COMPLETE")
    print("=" * 60)
    print(f"✅ Successfully moved: {moved_count} folders")
    print(f"❌ Failed to move: {failed_count} folders")
    
    # Check if unknown folder is now empty
    remaining_items = list(unknown_folder.iterdir())
    # Filter out .DS_Store files
    remaining_items = [item for item in remaining_items if item.name != '.DS_Store']
    
    if not remaining_items:
        print(f"\n📁 Unknown folder is now empty - removing it")
        shutil.rmtree(unknown_folder)
    else:
        print(f"\n📁 Unknown folder still contains {len(remaining_items)} items")
    
    return moved_count > 0

if __name__ == "__main__":
    success = reorganize_captures()
    
    if success:
        print(f"\n🎯 NEXT STEPS:")
        print(f"   1. Check visual_captures/ folder for properly organized tweets")
        print(f"   2. Each account should now have its own folder")
        print(f"   3. Text extraction results are preserved in metadata files")
        print(f"\n💡 Folder structure should now be:")
        print(f"   visual_captures/")
        print(f"   ├── minchoi/")
        print(f"   ├── openai/")
        print(f"   └── andrewyng/")
    else:
        print(f"\n❌ Reorganization failed or nothing to reorganize") 