#!/usr/bin/env python3
"""
Tweet Categorizer Service

Uses Gemini 2.0 Flash to categorize tweets based on their summary text.
Supports dynamic category management - new categories are automatically
added to the categories.json file when discovered.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'lambdas'))
sys.path.append(os.path.dirname(__file__))

import google.generativeai as genai
from shared.config import config
from prompt_templates import build_categorization_prompt

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TweetCategorizer:
    """
    Service for categorizing tweets based on their summary text using Gemini 2.0 Flash.
    Automatically manages categories and updates the categories.json file when new categories are discovered.
    """
    
    def __init__(self, categories_file: str = None, api_key: Optional[str] = None):
        """
        Initialize the TweetCategorizer with categories file and Gemini API credentials.
        
        Args:
            categories_file: Path to categories.json file. If None, uses default in same directory.
            api_key: Optional Gemini API key. If not provided, will use config.
            
        Raises:
            ValueError: If no API key is available or categories file not found
        """
        # Set up categories file path
        if categories_file is None:
            categories_file = os.path.join(os.path.dirname(__file__), "categories.json")
        
        self.categories_file = Path(categories_file)
        
        if not self.categories_file.exists():
            raise ValueError(f"Categories file not found: {self.categories_file}")
        
        # Set up Gemini API
        self.api_key = api_key or config.gemini_api_key
        
        if not self.api_key:
            logger.error("Gemini API key is not configured")
            raise ValueError("Missing Gemini API key. Set GEMINI_API_KEY in .env file")
        
        try:
            genai.configure(api_key=self.api_key)
            self.client = genai
            logger.info("TweetCategorizer initialized successfully with Gemini API")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise ValueError(f"Failed to initialize Gemini client: {e}")
        
        # Load categories
        self.categories_data = self._load_categories()
        logger.info(f"Loaded {len(self.categories_data.get('categories', []))} categories")
    
    def _load_categories(self) -> Dict[str, Any]:
        """
        Load categories from the JSON file.
        
        Returns:
            Dictionary containing categories data
        """
        try:
            with open(self.categories_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load categories file: {e}")
            raise ValueError(f"Failed to load categories file: {e}")
    
    def _save_categories(self) -> None:
        """
        Save the current categories data back to the JSON file.
        """
        try:
            # Update metadata
            self.categories_data['metadata']['last_updated'] = datetime.now().strftime('%Y-%m-%d')
            self.categories_data['metadata']['total_categories'] = len(self.categories_data.get('categories', []))
            
            with open(self.categories_file, 'w', encoding='utf-8') as f:
                json.dump(self.categories_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Categories saved to {self.categories_file}")
        except Exception as e:
            logger.error(f"Failed to save categories file: {e}")
            raise ValueError(f"Failed to save categories file: {e}")
    
    def _add_new_category(self, category_name: str, description: str) -> None:
        """
        Add a new category to the categories data and save it.
        
        Args:
            category_name: Name of the new category
            description: Description of the new category
        """
        new_category = {
            "name": category_name,
            "description": description
        }
        
        # Check if category already exists
        existing_names = [cat['name'] for cat in self.categories_data.get('categories', [])]
        if category_name in existing_names:
            logger.warning(f"Category '{category_name}' already exists, skipping addition")
            return
        
        # Add new category
        self.categories_data.setdefault('categories', []).append(new_category)
        
        # Save updated categories
        self._save_categories()
        
        logger.info(f"✅ Added new category: '{category_name}'")
        logger.info(f"   📝 Description: {description}")
    
    def categorize_tweet_summary(self, tweet_summary: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Categorize a tweet based on its summary text.
        
        Args:
            tweet_summary: Summary text from tweet metadata
            
        Returns:
            Tuple of (category_name, categorization_details) or (None, None) if failed
        """
        try:
            if not tweet_summary or tweet_summary.strip() == "":
                logger.warning("Empty tweet summary provided")
                return None, None
            
            # Build prompt with current categories
            prompt = build_categorization_prompt(self.categories_data, tweet_summary)
            
            logger.info(f"Categorizing tweet summary: {tweet_summary[:100]}...")
            
            # Call Gemini 2.0 Flash API
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            
            if not response or not response.text:
                logger.error("Empty response from Gemini API")
                return None, None
            
            # Parse the response
            category_result = self._parse_categorization_response(response.text)
            
            if not category_result:
                return None, None
            
            # Handle new category if needed
            if category_result.get('is_new_category', False):
                category_name = category_result.get('category')
                description = category_result.get('suggested_description', 'User-generated category')
                
                if category_name:
                    self._add_new_category(category_name, description)
            
            return category_result.get('category'), category_result
            
        except Exception as e:
            logger.error(f"Error categorizing tweet summary: {e}")
            return None, None
    
    def _parse_categorization_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse the Gemini API response to extract categorization result.
        
        Args:
            response_text: Raw response text from Gemini API
            
        Returns:
            Dictionary with categorization details or None if parsing failed
        """
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
            logger.debug(f"Raw response: {response_text[:500]}...")
            return None
        except Exception as e:
            logger.error(f"Error parsing categorization response: {e}")
            return None
    
    def process_tweet_folder(self, tweet_folder_path: str) -> bool:
        """
        Process a single tweet folder - categorize based on summary and update metadata.
        
        Args:
            tweet_folder_path: Path to the tweet folder containing metadata
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            tweet_folder = Path(tweet_folder_path)
            
            if not tweet_folder.exists():
                logger.error(f"Tweet folder does not exist: {tweet_folder_path}")
                return False
            
            # Find metadata file
            metadata_files = list(tweet_folder.glob("*metadata*.json"))
            if not metadata_files:
                logger.warning(f"No metadata file found in {tweet_folder_path}")
                return False
            
            metadata_file = metadata_files[0]
            
            # Load existing metadata
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Get tweet summary
            tweet_metadata = metadata.get('tweet_metadata', {})
            summary = tweet_metadata.get('summary')
            
            if not summary:
                logger.warning(f"No summary found in metadata for {tweet_folder.name}")
                return False
            
            # Check if already categorized
            if 'L1_category' in tweet_metadata:
                logger.info(f"Tweet {tweet_folder.name} already categorized as: {tweet_metadata['L1_category']}")
                return True
            
            logger.info(f"Processing tweet folder: {tweet_folder.name}")
            
            # Categorize the tweet
            category, categorization_details = self.categorize_tweet_summary(summary)
            
            if category and categorization_details:
                # Update metadata with categorization
                self._update_metadata_with_category(metadata, category, categorization_details)
                
                # Save updated metadata
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                logger.info(f"✅ Successfully categorized {tweet_folder.name}")
                logger.info(f"   📂 Category: {category}")
                logger.info(f"   🎯 Confidence: {categorization_details.get('confidence', 'unknown')}")
                logger.info(f"   💭 Reasoning: {categorization_details.get('reasoning', 'No reasoning provided')}")
                
                return True
            else:
                logger.warning(f"Failed to categorize {tweet_folder.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing tweet folder {tweet_folder_path}: {e}")
            return False
    
    def _update_metadata_with_category(self, metadata: Dict[str, Any], category: str, categorization_details: Dict[str, Any]) -> None:
        """
        Update metadata dictionary with categorization information.
        
        Args:
            metadata: Metadata dictionary to update
            category: Assigned category name
            categorization_details: Full categorization response from Gemini
        """
        # Ensure tweet_metadata exists
        if 'tweet_metadata' not in metadata:
            logger.warning("No tweet_metadata found in metadata, creating new section")
            metadata['tweet_metadata'] = {}
        
        # Add categorization information
        metadata['tweet_metadata']['L1_category'] = category
        metadata['tweet_metadata']['categorization_confidence'] = categorization_details.get('confidence')
        metadata['tweet_metadata']['categorization_reasoning'] = categorization_details.get('reasoning')
        metadata['tweet_metadata']['categorization_timestamp'] = datetime.now().isoformat()
        
        # Store if this was a new category
        if categorization_details.get('is_new_category'):
            metadata['tweet_metadata']['was_new_category'] = True
        
        logger.debug("Updated metadata with categorization information")
    
    def process_account_captures(self, base_path: str, account_name: str, date_folder: str = None) -> Dict[str, Any]:
        """
        Process all tweet captures for a specific account, categorizing each tweet.
        
        Args:
            base_path: Base path containing visual captures
            account_name: Twitter account name
            date_folder: Specific date folder (YYYY-MM-DD). If None, uses most recent.
            
        Returns:
            Dictionary with processing results and statistics
        """
        try:
            # Build path to account captures (similar to text extractor)
            if date_folder:
                account_path = Path(base_path) / "visual_captures" / date_folder / account_name.lower()
            else:
                # Find most recent date folder or direct account structure
                captures_path = Path(base_path) / "visual_captures"
                if not captures_path.exists():
                    # Try direct structure
                    account_path = Path(base_path) / account_name.lower()
                else:
                    date_folders = [d for d in captures_path.iterdir() if d.is_dir() and d.name.match(r'\d{4}-\d{2}-\d{2}')]
                    if date_folders:
                        latest_date = max(date_folders, key=lambda x: x.name)
                        account_path = latest_date / account_name.lower()
                    else:
                        # Direct account structure
                        account_path = captures_path / account_name.lower()
            
            if not account_path.exists():
                logger.error(f"Account path does not exist: {account_path}")
                return {"success": False, "error": f"Account folder not found: {account_name}"}
            
            logger.info(f"🔍 Processing categorization for @{account_name} in {account_path}")
            
            # Find all tweet folders (not conversation folders)
            tweet_folders = []
            for item in account_path.iterdir():
                if item.is_dir() and (item.name.startswith('tweet_') or item.name.startswith('retweet_')):
                    tweet_folders.append(item)
            
            if not tweet_folders:
                logger.info(f"No individual tweet folders found for @{account_name}")
                return {"success": True, "processed": 0, "message": "No individual tweets to process"}
            
            logger.info(f"Found {len(tweet_folders)} individual tweet folders to categorize")
            
            # Process each tweet folder
            results = {
                "success": True,
                "account": account_name,
                "total_folders": len(tweet_folders),
                "processed_successfully": 0,
                "failed": 0,
                "new_categories_created": 0,
                "processed_folders": []
            }
            
            for tweet_folder in tweet_folders:
                success = self.process_tweet_folder(str(tweet_folder))
                
                if success:
                    results["processed_successfully"] += 1
                    results["processed_folders"].append({
                        "folder": tweet_folder.name,
                        "status": "success"
                    })
                else:
                    results["failed"] += 1
                    results["processed_folders"].append({
                        "folder": tweet_folder.name,
                        "status": "failed"
                    })
            
            logger.info(f"✅ Categorization complete for @{account_name}")
            logger.info(f"   📊 Processed: {results['processed_successfully']}/{results['total_folders']}")
            logger.info(f"   ❌ Failed: {results['failed']}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing account captures for @{account_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_category_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current categories.
        
        Returns:
            Dictionary with category statistics
        """
        categories = self.categories_data.get('categories', [])
        metadata = self.categories_data.get('metadata', {})
        
        return {
            "total_categories": len(categories),
            "categories": [cat['name'] for cat in categories],
            "last_updated": metadata.get('last_updated'),
            "version": metadata.get('version')
        } 