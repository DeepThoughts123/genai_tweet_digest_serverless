#!/usr/bin/env python3
"""
Integrated Tweet Processing Pipeline

Complete end-to-end pipeline that:
1. Fetches tweets from specified accounts (last 7 days, max 20 per account)
2. Captures visual screenshots and saves to exploration subfolder
3. Categorizes tweets using AI-powered classification

Combines functionality from tweet_processing and tweet_categorization systems.
"""

import sys
import os
import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# Add paths for imports
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambdas'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'visual_tweet_capture'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'tweet_processing'))

# Import required services
from shared.tweet_services import TweetFetcher
from visual_tweet_capturer import VisualTweetCapturer
from tweet_text_extractor import TweetTextExtractor

# For categorization - import directly
import google.generativeai as genai
from shared.config import config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleTweetCategorizer:
    """
    Simplified tweet categorizer to avoid import conflicts.
    """
    
    def __init__(self, categories_file: str = None):
        """Initialize the categorizer."""
        # Set up categories file path
        if categories_file is None:
            categories_file = os.path.join(
                os.path.dirname(__file__), 
                'tweet_categorization', 
                'categories.json'
            )
        
        self.categories_file = Path(categories_file)
        
        if not self.categories_file.exists():
            raise ValueError(f"Categories file not found: {self.categories_file}")
        
        # Set up Gemini API
        self.api_key = config.gemini_api_key
        
        if not self.api_key:
            raise ValueError("Missing Gemini API key. Set GEMINI_API_KEY in .env file")
        
        try:
            genai.configure(api_key=self.api_key)
            self.client = genai
            logger.info("SimpleTweetCategorizer initialized successfully")
        except Exception as e:
            raise ValueError(f"Failed to initialize Gemini client: {e}")
        
        # Load categories
        self.categories_data = self._load_categories()
        logger.info(f"Loaded {len(self.categories_data.get('categories', []))} categories")
    
    def _load_categories(self):
        """Load categories from JSON file."""
        try:
            with open(self.categories_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to load categories file: {e}")
    
    def _build_categorization_prompt(self, tweet_text: str) -> str:
        """Build the categorization prompt."""
        # Format categories list for the prompt
        categories_list = ""
        for i, category in enumerate(self.categories_data.get("categories", []), 1):
            categories_list += f"{i}. {category['name']}: {category['description']}\n"
        
        prompt = f"""
You are an expert AI content categorizer specializing in GenAI/AI/ML content classification.

Your task is to categorize the following tweet text into one of the existing categories OR create a new category if none of the existing categories fit well.

EXISTING CATEGORIES:
{categories_list.strip()}

TWEET TEXT TO CATEGORIZE:
"{tweet_text}"

INSTRUCTIONS:
1. Analyze the tweet text carefully to understand its main topic and intent
2. First, try to match it to one of the existing categories above
3. If the tweet fits well into an existing category, use that category name EXACTLY as listed
4. If none of the existing categories are a good fit, create a NEW category name that would be appropriate
5. New categories should follow the same naming convention (title case, descriptive)
6. New categories should be broad enough to accommodate similar future tweets

RESPONSE FORMAT:
Respond in JSON format only:
{{
  "category": "Selected or New Category Name",
  "confidence": "high|medium|low",
  "reasoning": "Brief explanation of why this category was chosen",
  "is_new_category": true|false,
  "suggested_description": "If new category, provide a description similar to existing ones"
}}

Ensure your response is valid JSON with no additional text.
"""
        return prompt.strip()
    
    def categorize_text(self, full_text: str):
        """Categorize text using Gemini 2.0 Flash."""
        try:
            if not full_text or full_text.strip() == "":
                logger.warning("Empty text provided")
                return None, None
            
            # Build prompt with current categories
            prompt = self._build_categorization_prompt(full_text)
            
            # Call Gemini 2.0 Flash API
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            
            if not response or not response.text:
                logger.error("Empty response from Gemini API")
                return None, None
            
            # Parse the response
            category_result = self._parse_response(response.text)
            
            if not category_result:
                return None, None
            
            return category_result.get('category'), category_result
            
        except Exception as e:
            logger.error(f"Error categorizing text: {e}")
            return None, None
    
    def _parse_response(self, response_text: str):
        """Parse Gemini API response."""
        try:
            # Clean up response text
            response_text = response_text.strip()
            
            # Handle markdown code blocks
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse JSON
            parsed = json.loads(response_text)
            
            # Validate required fields
            required_fields = ['category', 'confidence', 'reasoning', 'is_new_category']
            for field in required_fields:
                if field not in parsed:
                    logger.warning(f"Missing required field '{field}' in API response")
                    return None
            
            category = parsed.get('category')
            if not category or category.strip() == "":
                logger.warning("Empty category in API response")
                return None
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return None
    
    def process_metadata_file(self, metadata_file_path: Path):
        """Process a single capture_metadata.json file."""
        try:
            # Load metadata
            with open(metadata_file_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Check if already categorized
            if 'L1_category' in metadata:
                logger.info(f"Already categorized: {metadata_file_path.parent.name}")
                return True
            
            # Get full_text from tweet_metadata first, then fall back to api_metadata.text
            full_text = None
            tweet_metadata = metadata.get('tweet_metadata', {})
            if tweet_metadata and 'full_text' in tweet_metadata:
                full_text = tweet_metadata['full_text']
            elif 'api_metadata' in metadata and 'text' in metadata['api_metadata']:
                full_text = metadata['api_metadata']['text']
            
            if not full_text:
                logger.warning(f"No full_text found in {metadata_file_path}")
                return False
            
            # Categorize
            category, details = self.categorize_text(full_text)
            
            if category and details:
                # Update metadata at root level
                metadata['L1_category'] = category
                metadata['L1_categorization_confidence'] = details.get('confidence')
                metadata['L1_categorization_reasoning'] = details.get('reasoning')
                metadata['L1_categorization_timestamp'] = datetime.now().isoformat()
                
                # Save updated metadata
                with open(metadata_file_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                # Output results
                print(f"✅ {metadata_file_path.parent.name}")
                print(f"   📂 Category: {category}")
                print(f"   💭 Reasoning: {details.get('reasoning', 'No reasoning provided')}")
                
                return True
            else:
                print(f"❌ Failed to categorize: {metadata_file_path.parent.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing {metadata_file_path}: {e}")
            return False
    
    def process_base_path(self, base_path: str):
        """Process all subfolders in base path looking for capture_metadata.json files."""
        base_path = Path(base_path)
        
        if not base_path.exists():
            raise ValueError(f"Base path does not exist: {base_path}")
        
        print(f"🔍 Scanning: {base_path}")
        
        # Find all capture_metadata.json files
        metadata_files = list(base_path.rglob("capture_metadata.json"))
        
        if not metadata_files:
            print(f"❌ No capture_metadata.json files found in {base_path}")
            return
        
        print(f"📊 Found {len(metadata_files)} metadata files to process\n")
        
        # Track stats
        processed = 0
        failed = 0
        already_categorized = 0
        
        # Process each file
        for metadata_file in metadata_files:
            # Check if already categorized
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                if 'L1_category' in metadata:
                    already_categorized += 1
                    continue
            except:
                pass
            
            success = self.process_metadata_file(metadata_file)
            
            if success:
                processed += 1
            else:
                failed += 1
        
        # Summary
        print(f"\n📊 PROCESSING COMPLETE")
        print(f"   ✅ Successfully categorized: {processed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📂 Already categorized: {already_categorized}")

class IntegratedTweetPipeline:
    """
    Complete tweet processing pipeline combining capture, extraction, and categorization.
    """
    
    def __init__(self, output_base_path="./pipeline_output"):
        """Initialize the integrated pipeline."""
        self.output_base_path = Path(output_base_path)
        self.output_base_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize services
        self.tweet_fetcher = None
        self.visual_capturer = None
        self.text_extractor = None
        self.categorizer = None
        
        print(f"📁 Output directory: {self.output_base_path}")
    
    def initialize_services(self):
        """Initialize all required services."""
        print("🔧 Initializing services...")
        
        try:
            # Initialize tweet fetcher
            self.tweet_fetcher = TweetFetcher()
            print("   ✅ Tweet fetcher initialized")
            
            # Initialize visual capturer
            self.visual_capturer = VisualTweetCapturer(
                headless=True,
                crop_enabled=True,
                crop_x1=31,
                crop_y1=0,
                crop_x2=63,
                crop_y2=98
            )
            
            # Update the visual capturer's base output directory to our custom path
            self.visual_capturer.base_output_dir = str(self.output_base_path)
            os.makedirs(self.visual_capturer.base_output_dir, exist_ok=True)
            
            print("   ✅ Visual capturer initialized")
            
            # Initialize text extractor
            self.text_extractor = TweetTextExtractor()
            print("   ✅ Text extractor initialized")
            
            # Initialize categorizer
            categorizer_categories_path = os.path.join(
                os.path.dirname(__file__), 
                'tweet_categorization', 
                'categories.json'
            )
            self.categorizer = SimpleTweetCategorizer(categories_file=categorizer_categories_path)
            print("   ✅ Tweet categorizer initialized")
            
            print("✅ All services initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize services: {e}")
            return False
    
    def fetch_tweets(self, accounts, days_back=7, max_tweets=20, api_method='search'):
        """Fetch tweets from specified accounts."""
        print(f"\n🔍 STEP 1: FETCHING TWEETS")
        print("=" * 50)
        
        all_tweet_urls = []
        
        for account in accounts:
            print(f"\n📡 Fetching tweets for @{account}...")
            
            try:
                tweet_urls = self.tweet_fetcher.fetch_recent_tweets(
                    username=account,
                    days_back=days_back,
                    max_tweets=max_tweets,
                    api_method=api_method
                )
                
                if tweet_urls:
                    print(f"   ✅ Found {len(tweet_urls)} tweets")
                    all_tweet_urls.extend(tweet_urls)
                else:
                    print(f"   ⚠️ No tweets found")
                    
            except Exception as e:
                print(f"   ❌ Error fetching tweets: {e}")
        
        print(f"\n📊 Total tweets to process: {len(all_tweet_urls)}")
        return all_tweet_urls
    
    def capture_tweets(self, tweet_urls, zoom_percent=30):
        """Capture visual screenshots of tweets."""
        print(f"\n📸 STEP 2: CAPTURING TWEET VISUALS")
        print("=" * 50)
        
        captured_count = 0
        failed_count = 0
        
        for i, tweet_url in enumerate(tweet_urls, 1):
            print(f"\n📸 Capturing tweet {i}/{len(tweet_urls)}")
            print(f"🔗 {tweet_url}")
            
            try:
                result = self.visual_capturer.capture_tweet_visually(
                    tweet_url, 
                    zoom_percent=zoom_percent
                )
                
                if result:
                    print(f"   ✅ Captured successfully")
                    print(f"   📁 Saved to: {result['output_directory']}")
                    captured_count += 1
                else:
                    print(f"   ❌ Failed to capture")
                    failed_count += 1
                    
            except Exception as e:
                print(f"   ❌ Error capturing: {e}")
                failed_count += 1
            
            # Small delay between captures
            import time
            time.sleep(2)
        
        print(f"\n📊 Capture Summary:")
        print(f"   ✅ Successfully captured: {captured_count}")
        print(f"   ❌ Failed: {failed_count}")
        
        return captured_count > 0
    
    def extract_text(self):
        """Extract text from captured screenshots."""
        print(f"\n📝 STEP 3: EXTRACTING TEXT FROM SCREENSHOTS")
        print("=" * 50)
        
        # Find all account folders in our output directory
        account_folders = [d for d in self.output_base_path.iterdir() if d.is_dir()]
        
        if not account_folders:
            print("❌ No account folders found for text extraction")
            return False
        
        processed_count = 0
        
        for account_folder in account_folders:
            print(f"\n🔄 Processing @{account_folder.name}...")
            
            # Find tweet folders
            tweet_folders = [
                d for d in account_folder.iterdir() 
                if d.is_dir() and (d.name.startswith('tweet_') or d.name.startswith('retweet_'))
            ]
            
            if not tweet_folders:
                print(f"   ⚠️ No tweet folders found")
                continue
            
            print(f"   📊 Found {len(tweet_folders)} tweet folders")
            
            for tweet_folder in tweet_folders:
                try:
                    success = self.text_extractor.process_tweet_folder(str(tweet_folder))
                    if success:
                        print(f"   ✅ {tweet_folder.name}")
                        processed_count += 1
                    else:
                        print(f"   ❌ {tweet_folder.name}")
                except Exception as e:
                    print(f"   ❌ {tweet_folder.name}: {e}")
        
        print(f"\n📊 Text extraction complete: {processed_count} tweets processed")
        return processed_count > 0
    
    def categorize_tweets(self):
        """Categorize tweets based on extracted text."""
        print(f"\n🏷️ STEP 4: CATEGORIZING TWEETS")
        print("=" * 50)
        
        try:
            # Use the categorizer to process all metadata files in our output directory
            self.categorizer.process_base_path(str(self.output_base_path))
            return True
            
        except Exception as e:
            print(f"❌ Error during categorization: {e}")
            return False
    
    def run_pipeline(self, accounts, days_back=7, max_tweets=20, zoom_percent=30, api_method='search'):
        """Run the complete integrated pipeline."""
        
        print("🚀 INTEGRATED TWEET PROCESSING PIPELINE")
        print("📅 " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        print("=" * 60)
        
        print("📋 PIPELINE CONFIGURATION:")
        print(f"   👥 Accounts: {', '.join(['@' + acc for acc in accounts])}")
        print(f"   📅 Days back: {days_back}")
        print(f"   🔢 Max tweets per account: {max_tweets}")
        print(f"   🔍 Browser zoom: {zoom_percent}%")
        print(f"   🔄 API method: {api_method}")
        print(f"   📁 Output directory: {self.output_base_path}")
        
        # Initialize services
        if not self.initialize_services():
            return False
        
        # Step 1: Fetch tweets
        tweet_urls = self.fetch_tweets(accounts, days_back, max_tweets, api_method)
        if not tweet_urls:
            print("❌ No tweets fetched. Pipeline stopped.")
            return False
        
        # Step 2: Capture visuals
        if not self.capture_tweets(tweet_urls, zoom_percent):
            print("❌ No tweets captured. Pipeline stopped.")
            return False
        
        # Step 3: Extract text
        if not self.extract_text():
            print("❌ Text extraction failed. Skipping categorization.")
            return False
        
        # Step 4: Categorize tweets
        if not self.categorize_tweets():
            print("❌ Categorization failed.")
            return False
        
        # Final summary
        print(f"\n" + "=" * 60)
        print(f"🎉 PIPELINE COMPLETE")
        print("=" * 60)
        print(f"✅ Successfully processed tweets from {len(accounts)} accounts")
        print(f"✅ Visual captures, text extraction, and categorization complete")
        print(f"\n📁 Results saved to: {self.output_base_path}")
        print(f"💡 Each tweet folder contains:")
        print(f"   • Screenshots (*.png)")
        print(f"   • Enhanced metadata with text, summaries, and engagement metrics")
        print(f"   • L1_category classification with confidence and reasoning")
        print("=" * 60)
        
        return True

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Integrated Tweet Processing Pipeline",
        epilog="""
Examples:
  # Default: Process test accounts
  python integrated_tweet_pipeline.py
  
  # Custom accounts
  python integrated_tweet_pipeline.py --accounts elonmusk openai
  
  # Custom configuration
  python integrated_tweet_pipeline.py --accounts minchoi openai --days-back 10 --max-tweets 15 --zoom 50
  
  # Different output directory
  python integrated_tweet_pipeline.py --output-dir ./my_tweets
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--accounts',
        nargs='+',
        default=['minchoi', 'openai', 'rasbt'],
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
        default=20,
        help='Maximum number of tweets per account'
    )
    
    parser.add_argument(
        '--zoom',
        type=int,
        default=30,
        choices=range(25, 201),
        help='Browser zoom percentage for screenshots'
    )
    
    parser.add_argument(
        '--api-method',
        choices=['timeline', 'search'],
        default='search',
        help='API method to use for fetching tweets'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./pipeline_output',
        help='Output directory for captured tweets'
    )
    
    parser.add_argument(
        '--no-confirm',
        action='store_true',
        help='Skip confirmation prompt'
    )
    
    args = parser.parse_args()
    
    # Confirmation prompt
    if not args.no_confirm:
        print(f"🎯 About to process {len(args.accounts)} account(s):")
        for account in args.accounts:
            print(f"   👤 @{account}")
        print(f"\n📋 Configuration:")
        print(f"   📅 Look back: {args.days_back} days")
        print(f"   🔢 Max tweets per account: {args.max_tweets}")
        print(f"   🔍 Browser zoom: {args.zoom}%")
        print(f"   🔄 API method: {args.api_method}")
        print(f"   📁 Output directory: {args.output_dir}")
        
        proceed = input(f"\n🤔 Proceed with integrated pipeline? (y/N): ").strip().lower()
        if proceed not in ['y', 'yes']:
            print("❌ Operation cancelled by user")
            sys.exit(0)
    
    # Initialize and run pipeline
    try:
        pipeline = IntegratedTweetPipeline(output_base_path=args.output_dir)
        success = pipeline.run_pipeline(
            accounts=args.accounts,
            days_back=args.days_back,
            max_tweets=args.max_tweets,
            zoom_percent=args.zoom,
            api_method=args.api_method
        )
        
        if not success:
            print("❌ Pipeline execution failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 