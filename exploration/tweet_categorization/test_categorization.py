#!/usr/bin/env python3
"""
Test Tweet Categorization Service

Tests the TweetCategorizer service by processing captured tweet metadata
and categorizing them based on their summary text using Gemini 2.0 Flash.
"""

import sys
import os
import argparse
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# Add current path for imports
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'lambdas'))

from tweet_categorizer import TweetCategorizer
from pathlib import Path
import json

def test_single_tweet_summary():
    """
    Test categorization with a single tweet summary for debugging.
    """
    print("🧪 TESTING SINGLE TWEET SUMMARY CATEGORIZATION")
    print("=" * 70)
    
    # Example summaries for testing
    test_summaries = [
        "Announces the release of GPT-5 with improved reasoning capabilities and multimodal features.",
        "Shares a beginner's guide to fine-tuning large language models with practical examples.",
        "Discusses new research paper on transformer efficiency published at NeurIPS conference.",
        "Reports on $100M funding round for AI startup focused on autonomous vehicles.",
        "Provides career advice for aspiring AI engineers and data scientists."
    ]
    
    try:
        print("🔧 Initializing TweetCategorizer...")
        categorizer = TweetCategorizer()
        
        print("📊 Current categories:")
        stats = categorizer.get_category_stats()
        for i, category in enumerate(stats['categories'], 1):
            print(f"   {i}. {category}")
        
        print(f"\n🧪 Testing categorization with {len(test_summaries)} sample summaries...")
        
        for i, summary in enumerate(test_summaries, 1):
            print(f"\n" + "-" * 50)
            print(f"📝 Test {i}: {summary}")
            
            category, details = categorizer.categorize_tweet_summary(summary)
            
            if category and details:
                print(f"✅ Category: {category}")
                print(f"🎯 Confidence: {details.get('confidence')}")
                print(f"💭 Reasoning: {details.get('reasoning')}")
                if details.get('is_new_category'):
                    print(f"🆕 This is a NEW category!")
            else:
                print(f"❌ Failed to categorize")
        
        # Show updated categories
        print(f"\n📊 Final categories after testing:")
        final_stats = categorizer.get_category_stats()
        for i, category in enumerate(final_stats['categories'], 1):
            print(f"   {i}. {category}")
        
        if final_stats['total_categories'] > stats['total_categories']:
            print(f"\n🆕 Added {final_stats['total_categories'] - stats['total_categories']} new categories!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during single summary testing: {e}")
        return False

def test_with_andrewyng_data():
    """
    Test categorization with actual andrewyng tweet data.
    """
    print("🧪 TESTING WITH ANDREWYNG TWEET DATA")
    print("=" * 70)
    
    # Look for andrewyng data in visual_captures
    data_paths = [
        "visual_captures/andrewyng",
        "../visual_tweet_capture/visual_captures/andrewyng",
        "../../visual_captures/andrewyng"
    ]
    
    andrewyng_path = None
    for path in data_paths:
        if os.path.exists(path):
            andrewyng_path = path
            break
    
    if not andrewyng_path:
        print("❌ No andrewyng data found!")
        print("💡 Expected to find data in:")
        for path in data_paths:
            print(f"   • {path}")
        return False
    
    print(f"📁 Found andrewyng data at: {andrewyng_path}")
    
    try:
        print("🔧 Initializing TweetCategorizer...")
        categorizer = TweetCategorizer()
        
        print("📊 Current categories:")
        initial_stats = categorizer.get_category_stats()
        for i, category in enumerate(initial_stats['categories'], 1):
            print(f"   {i}. {category}")
        
        # Process the andrewyng account
        print(f"\n🔄 Processing @andrewyng tweets...")
        
        # Get parent directory for base_path
        base_path = os.path.dirname(andrewyng_path)
        
        result = categorizer.process_account_captures(base_path, "andrewyng")
        
        if result['success']:
            print(f"\n✅ CATEGORIZATION SUCCESS FOR @ANDREWYNG!")
            print(f"   📊 Total folders: {result['total_folders']}")
            print(f"   ✅ Processed successfully: {result['processed_successfully']}")
            print(f"   ❌ Failed: {result['failed']}")
            
            # Show details of processed folders
            if result.get('processed_folders'):
                print(f"\n📁 PROCESSED FOLDERS:")
                for folder_info in result['processed_folders']:
                    status_emoji = "✅" if folder_info['status'] == 'success' else "❌"
                    print(f"   {status_emoji} {folder_info['folder']}")
                    
                    # Show categorization details for successful ones
                    if folder_info['status'] == 'success':
                        show_categorization_sample(andrewyng_path, folder_info['folder'])
            
            # Show category statistics
            final_stats = categorizer.get_category_stats()
            print(f"\n📊 CATEGORY STATISTICS:")
            print(f"   📈 Total categories: {final_stats['total_categories']}")
            
            if final_stats['total_categories'] > initial_stats['total_categories']:
                new_count = final_stats['total_categories'] - initial_stats['total_categories']
                print(f"   🆕 New categories created: {new_count}")
                
                # Show new categories
                initial_names = set(initial_stats['categories'])
                new_categories = [cat for cat in final_stats['categories'] if cat not in initial_names]
                if new_categories:
                    print(f"   📝 New categories: {', '.join(new_categories)}")
            
            print(f"\n📂 FINAL CATEGORIES LIST:")
            for i, category in enumerate(final_stats['categories'], 1):
                print(f"   {i}. {category}")
                
        else:
            print(f"\n❌ CATEGORIZATION FAILED FOR @ANDREWYNG!")
            print(f"   🔴 Error: {result.get('error', 'Unknown error')}")
        
        return result['success']
        
    except Exception as e:
        print(f"❌ Error during andrewyng testing: {e}")
        return False

def show_categorization_sample(account_path: str, folder_name: str):
    """
    Show a sample of the categorization result from a processed folder.
    
    Args:
        account_path: Path to the account folder
        folder_name: Name of the specific tweet folder
    """
    try:
        folder_path = Path(account_path) / folder_name
        metadata_files = list(folder_path.glob("*metadata*.json"))
        
        if not metadata_files:
            return
        
        with open(metadata_files[0], 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        tweet_metadata = metadata.get('tweet_metadata', {})
        summary = tweet_metadata.get('summary')
        category = tweet_metadata.get('L1_category')
        confidence = tweet_metadata.get('categorization_confidence')
        reasoning = tweet_metadata.get('categorization_reasoning')
        
        if category:
            print(f"       📂 Category: {category}")
            if confidence:
                print(f"       🎯 Confidence: {confidence}")
            if summary:
                print(f"       📝 Summary: {summary[:100]}{'...' if len(summary) > 100 else ''}")
            if reasoning:
                print(f"       💭 Reasoning: {reasoning[:100]}{'...' if len(reasoning) > 100 else ''}")
        
    except Exception as e:
        print(f"       ⚠️ Could not show categorization sample: {e}")

def test_category_management():
    """
    Test the category management functionality.
    """
    print("🧪 TESTING CATEGORY MANAGEMENT")
    print("=" * 70)
    
    try:
        print("🔧 Initializing TweetCategorizer...")
        categorizer = TweetCategorizer()
        
        print("📊 Initial categories:")
        initial_stats = categorizer.get_category_stats()
        for i, category in enumerate(initial_stats['categories'], 1):
            print(f"   {i}. {category}")
        
        # Test with a summary that might create a new category
        test_summary = "Discusses the ethical implications of artificial general intelligence and potential societal risks."
        
        print(f"\n📝 Testing with summary that might create new category:")
        print(f"   {test_summary}")
        
        category, details = categorizer.categorize_tweet_summary(test_summary)
        
        if category and details:
            print(f"\n✅ Categorization result:")
            print(f"   📂 Category: {category}")
            print(f"   🎯 Confidence: {details.get('confidence')}")
            print(f"   💭 Reasoning: {details.get('reasoning')}")
            print(f"   🆕 Is new category: {details.get('is_new_category')}")
            
            if details.get('is_new_category'):
                print(f"   📝 Description: {details.get('suggested_description')}")
        
        # Show final categories
        final_stats = categorizer.get_category_stats()
        print(f"\n📊 Final categories:")
        for i, category in enumerate(final_stats['categories'], 1):
            print(f"   {i}. {category}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during category management testing: {e}")
        return False

def main():
    """
    Main function to run categorization tests.
    """
    parser = argparse.ArgumentParser(description="Test Tweet Categorization Service")
    parser.add_argument('--test-type', choices=['single', 'andrewyng', 'category-mgmt', 'all'], 
                       default='all', help='Type of test to run')
    
    args = parser.parse_args()
    
    print("🚀 TWEET CATEGORIZATION TESTING")
    print("📅 " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 70)
    
    success_count = 0
    total_tests = 0
    
    if args.test_type in ['single', 'all']:
        print("\n" + "=" * 70)
        total_tests += 1
        if test_single_tweet_summary():
            success_count += 1
    
    if args.test_type in ['andrewyng', 'all']:
        print("\n" + "=" * 70)
        total_tests += 1
        if test_with_andrewyng_data():
            success_count += 1
    
    if args.test_type in ['category-mgmt', 'all']:
        print("\n" + "=" * 70)
        total_tests += 1
        if test_category_management():
            success_count += 1
    
    # Final summary
    print(f"\n" + "=" * 70)
    print(f"🏁 TESTING COMPLETE")
    print("=" * 70)
    print(f"✅ Successful tests: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print(f"🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️ Some tests failed")
    
    print("=" * 70)

if __name__ == "__main__":
    main() 