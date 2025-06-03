#!/usr/bin/env python3
"""
Tweet Categorization Pipeline

Categorizes captured tweets based on their summary text using Gemini 2.0 Flash.
Supports dynamic category management and metadata enrichment.
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

from tweet_categorizer import TweetCategorizer
from pathlib import Path

def categorize_account_tweets(account_name, base_path=".", categories_file=None):
    """
    Categorize all tweets for a specific account.
    
    Args:
        account_name: Twitter account name to process
        base_path: Base path containing visual captures
        categories_file: Optional custom categories file path
    """
    print("🎯 TWEET CATEGORIZATION PIPELINE")
    print("=" * 70)
    
    print(f"📋 PROCESSING OVERVIEW:")
    print(f"   👤 Account: @{account_name}")
    print(f"   📁 Base path: {base_path}")
    if categories_file:
        print(f"   📂 Categories file: {categories_file}")
    print(f"   🤖 AI Model: Gemini 2.0 Flash")
    
    try:
        # Initialize categorizer
        print(f"\n🔧 Initializing TweetCategorizer...")
        categorizer = TweetCategorizer(categories_file=categories_file)
        print("✅ Categorizer initialized successfully")
        
        # Show current categories
        stats = categorizer.get_category_stats()
        print(f"\n📊 Current categories ({stats['total_categories']} total):")
        for i, category in enumerate(stats['categories'], 1):
            print(f"   {i}. {category}")
        
        # Process the account
        print(f"\n🔄 Processing @{account_name} tweets...")
        result = categorizer.process_account_captures(base_path, account_name)
        
        if result['success']:
            print(f"\n✅ CATEGORIZATION SUCCESS FOR @{account_name.upper()}!")
            print(f"   📊 Total folders: {result['total_folders']}")
            print(f"   ✅ Processed successfully: {result['processed_successfully']}")
            print(f"   ❌ Failed: {result['failed']}")
            
            # Show sample results
            if result.get('processed_folders'):
                print(f"\n📁 SAMPLE RESULTS:")
                sample_count = min(3, len([f for f in result['processed_folders'] if f['status'] == 'success']))
                successful_folders = [f for f in result['processed_folders'] if f['status'] == 'success']
                
                for folder_info in successful_folders[:sample_count]:
                    print(f"   ✅ {folder_info['folder']}")
                    show_categorization_details(base_path, account_name, folder_info['folder'])
            
            # Show category statistics
            final_stats = categorizer.get_category_stats()
            print(f"\n📊 FINAL STATISTICS:")
            print(f"   📈 Total categories: {final_stats['total_categories']}")
            
            if final_stats['total_categories'] > stats['total_categories']:
                new_count = final_stats['total_categories'] - stats['total_categories']
                print(f"   🆕 New categories created: {new_count}")
                
                # Show new categories
                initial_names = set(stats['categories'])
                new_categories = [cat for cat in final_stats['categories'] if cat not in initial_names]
                if new_categories:
                    print(f"   📝 New categories: {', '.join(new_categories)}")
            
            print(f"\n💾 Updated metadata files now contain:")
            print(f"   • L1_category: Assigned category name")
            print(f"   • categorization_confidence: AI confidence level")
            print(f"   • categorization_reasoning: AI explanation")
            print(f"   • categorization_timestamp: When categorization was performed")
            
            return True
            
        else:
            print(f"\n❌ CATEGORIZATION FAILED FOR @{account_name}!")
            print(f"   🔴 Error: {result.get('error', 'Unknown error')}")
            print(f"💡 Please check:")
            print(f"   - Account folder exists in visual_captures/")
            print(f"   - Tweet folders contain metadata with summary field")
            print(f"   - Gemini API key is configured correctly")
            return False
            
    except Exception as e:
        print(f"❌ Error during categorization: {e}")
        print(f"💡 Please check:")
        print(f"   - Gemini API key in .env file")
        print(f"   - Categories.json file exists")
        print(f"   - Tweet metadata contains summary field")
        return False

def show_categorization_details(base_path, account_name, folder_name):
    """
    Show categorization details for a specific folder.
    
    Args:
        base_path: Base path to data
        account_name: Account name
        folder_name: Folder name to show details for
    """
    try:
        # Try different path structures
        possible_paths = [
            Path(base_path) / "visual_captures" / account_name.lower() / folder_name,
            Path(base_path) / account_name.lower() / folder_name
        ]
        
        folder_path = None
        for path in possible_paths:
            if path.exists():
                folder_path = path
                break
        
        if not folder_path:
            return
        
        metadata_files = list(folder_path.glob("*metadata*.json"))
        if not metadata_files:
            return
        
        import json
        with open(metadata_files[0], 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        tweet_metadata = metadata.get('tweet_metadata', {})
        category = tweet_metadata.get('L1_category')
        confidence = tweet_metadata.get('categorization_confidence')
        summary = tweet_metadata.get('summary')
        
        if category:
            print(f"       📂 Category: {category}")
            if confidence:
                print(f"       🎯 Confidence: {confidence}")
            if summary:
                print(f"       📝 Summary: {summary[:100]}{'...' if len(summary) > 100 else ''}")
        
    except Exception as e:
        print(f"       ⚠️ Could not show details: {e}")

def list_available_accounts(base_path="."):
    """
    List available accounts that can be categorized.
    
    Args:
        base_path: Base path to search for accounts
    """
    print("📋 AVAILABLE ACCOUNTS FOR CATEGORIZATION")
    print("=" * 70)
    
    # Try different structures
    search_paths = [
        Path(base_path) / "visual_captures",
        Path(base_path)
    ]
    
    found_accounts = set()
    
    for search_path in search_paths:
        if not search_path.exists():
            continue
        
        print(f"🔍 Searching in: {search_path}")
        
        # Look for account folders
        for item in search_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Check if it contains tweet folders
                tweet_folders = [d for d in item.iterdir() 
                               if d.is_dir() and (d.name.startswith('tweet_') or d.name.startswith('retweet_'))]
                
                if tweet_folders:
                    found_accounts.add(item.name)
    
    if found_accounts:
        print(f"\n✅ Found {len(found_accounts)} account(s) with tweet data:")
        for account in sorted(found_accounts):
            print(f"   👤 @{account}")
        
        print(f"\n💡 Usage examples:")
        for account in sorted(list(found_accounts)[:3]):  # Show first 3 as examples
            print(f"   python categorize_tweets.py --account {account}")
    else:
        print(f"\n❌ No accounts with tweet data found")
        print(f"💡 Expected structure:")
        print(f"   visual_captures/account_name/tweet_*/")
        print(f"   or")
        print(f"   account_name/tweet_*/")

def main():
    """
    Main function to run tweet categorization.
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Tweet Categorization Pipeline",
        epilog="""
Examples:
  # Categorize tweets for andrewyng account
  python categorize_tweets.py --account andrewyng
  
  # List available accounts
  python categorize_tweets.py --list-accounts
  
  # Use custom categories file
  python categorize_tweets.py --account andrewyng --categories custom_categories.json
  
  # Use different base path
  python categorize_tweets.py --account andrewyng --base-path ../visual_tweet_capture
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--account',
        type=str,
        help='Twitter account name to categorize (without @)'
    )
    
    parser.add_argument(
        '--base-path',
        type=str,
        default='.',
        help='Base path containing visual captures (default: current directory)'
    )
    
    parser.add_argument(
        '--categories',
        type=str,
        help='Path to custom categories.json file (default: uses categories.json in same directory)'
    )
    
    parser.add_argument(
        '--list-accounts',
        action='store_true',
        help='List available accounts that can be categorized'
    )
    
    args = parser.parse_args()
    
    # Handle list accounts
    if args.list_accounts:
        list_available_accounts(args.base_path)
        return
    
    # Validate account argument
    if not args.account:
        print("❌ Error: --account argument is required")
        print("💡 Use --list-accounts to see available accounts")
        parser.print_help()
        sys.exit(1)
    
    print("🚀 TWEET CATEGORIZATION PIPELINE")
    print("📅 " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 70)
    
    # Run categorization
    success = categorize_account_tweets(
        account_name=args.account,
        base_path=args.base_path,
        categories_file=args.categories
    )
    
    # Final summary
    print(f"\n" + "=" * 70)
    print(f"🏁 CATEGORIZATION COMPLETE")
    print("=" * 70)
    
    if success:
        print(f"🎉 SUCCESS! Tweets categorized successfully")
        print(f"✅ Account @{args.account} processed")
        print(f"✅ Metadata files updated with L1_category field")
        print(f"\n📁 Check tweet folders for updated metadata.json files")
    else:
        print(f"❌ CATEGORIZATION FAILED")
        print(f"💡 Check error messages above for troubleshooting")
    
    print("=" * 70)

if __name__ == "__main__":
    main() 