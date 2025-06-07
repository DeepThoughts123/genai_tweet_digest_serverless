#!/usr/bin/env python3
"""
Direct Tweet Categorization Script

Processes folders containing capture_metadata.json files, categorizes tweets
based on their full_text field using Gemini 2.0 Flash, and updates the same
metadata files with L1_category field.
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# Add paths for imports
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'lambdas'))

import google.generativeai as genai
from shared.config import config
from prompt_templates import build_categorization_prompt

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DirectTweetCategorizer:
    """
    Categorizes tweets directly from capture_metadata.json files using full_text field.
    """
    
    def __init__(self, categories_file: str = None):
        """Initialize the categorizer."""
        # Set up categories file path
        if categories_file is None:
            categories_file = os.path.join(os.path.dirname(__file__), "categories.json")
        
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
            logger.info("DirectTweetCategorizer initialized successfully")
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
    
    def _save_categories(self):
        """Save categories to JSON file."""
        try:
            # Update metadata
            self.categories_data['metadata']['last_updated'] = datetime.now().strftime('%Y-%m-%d')
            self.categories_data['metadata']['total_categories'] = len(self.categories_data.get('categories', []))
            
            with open(self.categories_file, 'w', encoding='utf-8') as f:
                json.dump(self.categories_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Categories saved to {self.categories_file}")
        except Exception as e:
            raise ValueError(f"Failed to save categories file: {e}")
    
    def _add_new_category(self, category_name: str, description: str):
        """Add new category to categories data."""
        # Check if category already exists
        existing_names = [cat['name'] for cat in self.categories_data.get('categories', [])]
        if category_name in existing_names:
            logger.warning(f"Category '{category_name}' already exists, skipping addition")
            return False
        
        # Add new category
        new_category = {
            "name": category_name,
            "description": description
        }
        self.categories_data.setdefault('categories', []).append(new_category)
        
        # Save updated categories
        self._save_categories()
        
        print(f"🆕 NEW CATEGORY CREATED: {category_name}")
        print(f"   📝 Description: {description}")
        return True
    
    def categorize_text(self, full_text: str):
        """Categorize text using Gemini 2.0 Flash."""
        try:
            if not full_text or full_text.strip() == "":
                logger.warning("Empty text provided")
                return None, None
            
            # Build prompt with current categories
            prompt = build_categorization_prompt(self.categories_data, full_text)
            
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
            
            # Handle new category if needed
            if category_result.get('is_new_category', False):
                category_name = category_result.get('category')
                description = category_result.get('suggested_description', 'Auto-generated category')
                
                if category_name:
                    self._add_new_category(category_name, description)
            
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
        new_categories_created = 0
        initial_category_count = len(self.categories_data.get('categories', []))
        
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
        
        # Calculate new categories created
        final_category_count = len(self.categories_data.get('categories', []))
        new_categories_created = final_category_count - initial_category_count
        
        # Summary
        print(f"\n📊 PROCESSING COMPLETE")
        print(f"   ✅ Successfully categorized: {processed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📂 Already categorized: {already_categorized}")
        print(f"   🆕 New categories created: {new_categories_created}")
        print(f"   📈 Total categories: {final_category_count}")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Direct Tweet Categorization")
    parser.add_argument('base_path', help='Base path containing subfolders with capture_metadata.json files')
    parser.add_argument('--categories', help='Path to custom categories.json file')
    
    args = parser.parse_args()
    
    try:
        print("🚀 DIRECT TWEET CATEGORIZATION")
        print("=" * 50)
        
        # Initialize categorizer
        categorizer = DirectTweetCategorizer(categories_file=args.categories)
        
        # Process base path
        categorizer.process_base_path(args.base_path)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 