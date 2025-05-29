#!/usr/bin/env python3
"""
Test script for the unified scoring implementation.
Creates sample data files and runs the unified score calculator.
"""

import json
import os
import sys
from pathlib import Path

def create_sample_data():
    """Create sample data files for testing the unified scoring system."""
    
    # Create directories if they don't exist
    os.makedirs("../graph_base", exist_ok=True)
    os.makedirs("../content_base/content_discovery_results", exist_ok=True)
    os.makedirs("../engagement_base/engagement_discovery_results", exist_ok=True)
    
    # Sample graph-based candidates (list format)
    graph_candidates = [
        {
            "handle": "andrewng",
            "display_name": "Andrew Ng",
            "pagerank_score": 0.85,
            "weighted_in_degree": 12.5
        },
        {
            "handle": "openai",
            "display_name": "OpenAI",
            "pagerank_score": 0.92,
            "weighted_in_degree": 15.2
        },
        {
            "handle": "jimfan_",
            "display_name": "Jim Fan",
            "pagerank_score": 0.75,
            "weighted_in_degree": 8.3
        },
        {
            "handle": "ylecun",
            "display_name": "Yann LeCun",
            "pagerank_score": 0.88,
            "weighted_in_degree": 14.1
        }
    ]
    
    # Sample content-based candidates (dict format)
    content_candidates = {
        "andrewng": {
            "display_name": "Andrew Ng",
            "overall_score": 0.89,
            "bio_score": 0.95,
            "topic_score": 0.85
        },
        "openai": {
            "display_name": "OpenAI",
            "overall_score": 0.94,
            "bio_score": 0.98,
            "topic_score": 0.92
        },
        "karpathy": {
            "display_name": "Andrej Karpathy",
            "overall_score": 0.91,
            "bio_score": 0.90,
            "topic_score": 0.93
        }
    }
    
    # Sample engagement-based candidates (dict format)
    engagement_candidates = {
        "openai": {
            "display_name": "OpenAI",
            "overall_engagement_score": 0.87,
            "reply_score": 0.85,
            "viral_score": 0.90
        },
        "jimfan_": {
            "display_name": "Jim Fan",
            "overall_engagement_score": 0.82,
            "reply_score": 0.80,
            "viral_score": 0.85
        },
        "karpathy": {
            "display_name": "Andrej Karpathy",
            "overall_engagement_score": 0.88,
            "reply_score": 0.90,
            "viral_score": 0.85
        },
        "chollet": {
            "display_name": "François Chollet",
            "overall_engagement_score": 0.79,
            "reply_score": 0.82,
            "viral_score": 0.75
        }
    }
    
    # Write sample data files
    with open("../graph_base/genai_following_nodes.json", "w") as f:
        json.dump(graph_candidates, f, indent=2)
        
    with open("../content_base/content_discovery_results/content_candidates.json", "w") as f:
        json.dump(content_candidates, f, indent=2)
        
    with open("../engagement_base/engagement_discovery_results/engagement_candidates.json", "w") as f:
        json.dump(engagement_candidates, f, indent=2)
    
    print("✅ Sample data files created successfully!")
    print("  - Graph candidates: 4 accounts")
    print("  - Content candidates: 3 accounts") 
    print("  - Engagement candidates: 4 accounts")
    print("  - Total unique accounts: 5 (andrewng, openai, jimfan_, karpathy, chollet)")
    print("  - Multi-source accounts: 3 (openai=3 sources, jimfan_=2 sources, karpathy=2 sources)")

def run_test():
    """Run the unified scoring test."""
    print("\n" + "="*60)
    print("RUNNING UNIFIED SCORING TEST")
    print("="*60)
    
    # Import and run the unified score calculator
    sys.path.append('.')
    try:
        from unified_score_calculator import main
        main()
        print("\n✅ Test completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

def cleanup_test_data():
    """Clean up test data files."""
    test_files = [
        "../graph_base/genai_following_nodes.json",
        "../content_base/content_discovery_results/content_candidates.json",
        "../engagement_base/engagement_discovery_results/engagement_candidates.json",
        "final_curated_list.json"
    ]
    
    for file_path in test_files:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️  Cleaned up: {file_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test the unified scoring system")
    parser.add_argument("--cleanup", action="store_true", help="Clean up test data files")
    parser.add_argument("--create-data", action="store_true", help="Only create sample data")
    
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_test_data()
    elif args.create_data:
        create_sample_data()
    else:
        create_sample_data()
        run_test()
        print(f"\n📊 Check the 'final_curated_list.json' file for results!")
        print("💡 Run with --cleanup to remove test files") 