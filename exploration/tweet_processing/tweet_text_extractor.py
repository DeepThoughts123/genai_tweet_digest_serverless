#!/usr/bin/env python3
"""
Tweet Text Extractor Service

Uses Gemini 2.0 Flash multimodal capabilities to extract complete text content
and generate summaries from tweet screenshots. Updates metadata.json files
with extracted information.
"""

import os
import sys
import json
import base64
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

# Add lambdas to path for shared utilities
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'lambdas'))

import google.generativeai as genai
from shared.config import config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TweetTextExtractor:
    """
    Service for extracting complete text content and generating summaries 
    from tweet screenshots using Gemini 2.0 Flash multimodal API.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the TweetTextExtractor with Gemini API credentials.
        
        Args:
            api_key: Optional Gemini API key. If not provided, will use config.
            
        Raises:
            ValueError: If no API key is available
        """
        self.api_key = api_key or config.gemini_api_key
        
        if not self.api_key:
            logger.error("Gemini API key is not configured")
            raise ValueError("Missing Gemini API key. Set GEMINI_API_KEY in .env file")
        
        try:
            genai.configure(api_key=self.api_key)
            self.client = genai
            logger.info("TweetTextExtractor initialized successfully with Gemini API")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise ValueError(f"Failed to initialize Gemini client: {e}")
    
    def process_tweet_folder(self, tweet_folder_path: str) -> bool:
        """
        Process a single tweet folder - extract text and summary from screenshots,
        then update the metadata.json file.
        
        Args:
            tweet_folder_path: Path to the tweet folder containing screenshots and metadata
            
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
            
            # Find screenshot files
            screenshot_files = list(tweet_folder.glob("*.png"))
            if not screenshot_files:
                logger.warning(f"No screenshot files found in {tweet_folder_path}")
                return False
            
            logger.info(f"Processing tweet folder: {tweet_folder.name}")
            logger.info(f"Found {len(screenshot_files)} screenshots")
            
            # Load existing metadata
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Check if this is a conversation (skip if it is)
            if self._is_conversation_folder(tweet_folder, metadata):
                logger.info(f"Skipping conversation folder: {tweet_folder.name}")
                return True
            
            # Extract text and generate summary from screenshots
            full_text, summary = self._extract_text_and_summary(screenshot_files)
            
            if full_text and summary:
                # Update metadata with extracted information
                self._update_metadata_with_extraction(metadata, full_text, summary)
                
                # Save updated metadata
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                logger.info(f"✅ Successfully updated metadata for {tweet_folder.name}")
                logger.info(f"   📝 Extracted text length: {len(full_text)} characters")
                logger.info(f"   📄 Summary: {summary[:100]}...")
                
                return True
            else:
                logger.warning(f"Failed to extract text/summary for {tweet_folder.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing tweet folder {tweet_folder_path}: {e}")
            return False
    
    def process_account_captures(self, base_path: str, account_name: str, date_folder: str = None) -> Dict[str, Any]:
        """
        Process all tweet captures for a specific account, extracting text and summaries.
        
        Args:
            base_path: Base path containing visual captures
            account_name: Twitter account name
            date_folder: Specific date folder (YYYY-MM-DD). If None, uses most recent.
            
        Returns:
            Dictionary with processing results and statistics
        """
        try:
            # Build path to account captures
            if date_folder:
                account_path = Path(base_path) / "visual_captures" / date_folder / account_name.lower()
            else:
                # Find most recent date folder
                captures_path = Path(base_path) / "visual_captures"
                if not captures_path.exists():
                    logger.error(f"Visual captures path does not exist: {captures_path}")
                    return {"success": False, "error": "Visual captures path not found"}
                
                date_folders = [d for d in captures_path.iterdir() if d.is_dir() and d.name.match(r'\d{4}-\d{2}-\d{2}')]
                if not date_folders:
                    logger.error("No date folders found in visual captures")
                    return {"success": False, "error": "No date folders found"}
                
                latest_date = max(date_folders, key=lambda x: x.name)
                account_path = latest_date / account_name.lower()
            
            if not account_path.exists():
                logger.error(f"Account path does not exist: {account_path}")
                return {"success": False, "error": f"Account folder not found: {account_name}"}
            
            logger.info(f"🔍 Processing captures for @{account_name} in {account_path}")
            
            # Find all tweet folders (not conversation folders)
            tweet_folders = []
            for item in account_path.iterdir():
                if item.is_dir() and (item.name.startswith('tweet_') or item.name.startswith('retweet_')):
                    tweet_folders.append(item)
            
            if not tweet_folders:
                logger.info(f"No individual tweet folders found for @{account_name}")
                return {"success": True, "processed": 0, "message": "No individual tweets to process"}
            
            logger.info(f"Found {len(tweet_folders)} individual tweet folders to process")
            
            # Process each tweet folder
            results = {
                "success": True,
                "account": account_name,
                "total_folders": len(tweet_folders),
                "processed_successfully": 0,
                "failed": 0,
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
            
            logger.info(f"✅ Processing complete for @{account_name}")
            logger.info(f"   📊 Processed: {results['processed_successfully']}/{results['total_folders']}")
            logger.info(f"   ❌ Failed: {results['failed']}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing account captures for @{account_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def _is_conversation_folder(self, tweet_folder: Path, metadata: Dict[str, Any]) -> bool:
        """
        Check if this is a conversation/thread folder that should be skipped.
        
        Args:
            tweet_folder: Path to the tweet folder
            metadata: Loaded metadata dictionary
            
        Returns:
            True if this is a conversation folder, False if individual tweet
        """
        # Check folder name pattern
        if tweet_folder.name.startswith('convo_'):
            return True
        
        # Check metadata for conversation indicators
        if metadata.get('capture_strategy') == 'individual_tweet_capture':
            return True
        
        if 'ordered_tweets' in metadata and len(metadata.get('ordered_tweets', [])) > 1:
            return True
        
        return False
    
    def _extract_text_and_summary(self, screenshot_files: List[Path]) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract complete text and generate summary from tweet screenshots using Gemini 2.0 Flash.
        
        Args:
            screenshot_files: List of screenshot file paths
            
        Returns:
            Tuple of (full_text, summary) or (None, None) if extraction failed
        """
        try:
            # Convert screenshots to base64
            image_data = []
            for screenshot_file in sorted(screenshot_files):
                try:
                    with open(screenshot_file, 'rb') as f:
                        image_bytes = f.read()
                        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                        image_data.append({
                            "mime_type": "image/png",
                            "data": image_b64
                        })
                        logger.debug(f"Loaded screenshot: {screenshot_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to load screenshot {screenshot_file}: {e}")
            
            if not image_data:
                logger.error("No screenshots could be loaded")
                return None, None
            
            # Build prompt for text extraction and summarization
            prompt = self._build_extraction_prompt()
            
            # Prepare content for Gemini API (text + images)
            content_parts = [prompt]
            content_parts.extend(image_data)
            
            # Call Gemini 2.0 Flash multimodal API
            logger.info(f"Calling Gemini 2.0 Flash with {len(image_data)} images...")
            
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(content_parts)
            
            if not response or not response.text:
                logger.error("Empty response from Gemini API")
                return None, None
            
            # Parse the response
            return self._parse_extraction_response(response.text)
            
        except Exception as e:
            logger.error(f"Error extracting text and summary: {e}")
            return None, None
    
    def _build_extraction_prompt(self) -> str:
        """
        Build the prompt for Gemini API to extract text and generate summary.
        
        Returns:
            Formatted prompt string for multimodal Gemini API
        """
        return """
Please analyze the provided tweet screenshot(s) and extract the following information:

1. COMPLETE TEXT EXTRACTION:
   - Extract ALL text content from the tweet, including the main tweet text, any quoted text, and all visible text elements
   - Include usernames, timestamps, and engagement metrics if visible
   - Preserve the exact wording and formatting as much as possible
   - If there are multiple screenshots, combine the text content logically

2. SUMMARY GENERATION:
   - Create a concise 1-2 sentence summary that captures the key information and main point of the tweet
   - Focus on the core message, findings, announcements, or insights
   - Keep it informative but brief, suitable for a digest format

Please respond in the following JSON format:
{
  "full_text": "Complete extracted text from the tweet...",
  "summary": "Concise 1-2 sentence summary of the tweet content..."
}

Ensure the JSON is valid and properly formatted. If you cannot extract text or generate a summary, use null values.
        """.strip()
    
    def _parse_extraction_response(self, response_text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse the Gemini API response to extract full_text and summary.
        
        Args:
            response_text: Raw response text from Gemini API
            
        Returns:
            Tuple of (full_text, summary) or (None, None) if parsing failed
        """
        try:
            # Try to extract JSON from the response
            response_text = response_text.strip()
            
            # Handle markdown code blocks
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse JSON
            parsed = json.loads(response_text)
            
            full_text = parsed.get('full_text')
            summary = parsed.get('summary')
            
            # Validate extracted data
            if not full_text or not summary:
                logger.warning("Missing full_text or summary in API response")
                return None, None
            
            if full_text == "null" or summary == "null":
                logger.warning("API returned null values for extraction")
                return None, None
            
            return full_text.strip(), summary.strip()
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response_text[:500]}...")
            return None, None
        except Exception as e:
            logger.error(f"Error parsing extraction response: {e}")
            return None, None
    
    def _update_metadata_with_extraction(self, metadata: Dict[str, Any], full_text: str, summary: str) -> None:
        """
        Update metadata dictionary with extracted text and summary.
        
        Args:
            metadata: Metadata dictionary to update
            full_text: Extracted complete text
            summary: Generated summary
        """
        # Ensure tweet_metadata exists
        if 'tweet_metadata' not in metadata:
            logger.warning("No tweet_metadata found in metadata, creating new section")
            metadata['tweet_metadata'] = {}
        
        # Add extracted information to tweet_metadata
        metadata['tweet_metadata']['full_text'] = full_text
        metadata['tweet_metadata']['summary'] = summary
        
        # Add extraction timestamp for tracking
        from datetime import datetime
        metadata['tweet_metadata']['extraction_timestamp'] = datetime.now().isoformat()
        
        logger.debug("Updated metadata with extracted text and summary") 