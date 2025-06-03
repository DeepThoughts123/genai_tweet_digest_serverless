# This module will be responsible for summarizing categorized tweets using Gemini 2.0 Flash API.
import logging
from typing import List, Dict, Any, Optional
from collections import defaultdict

import google.generativeai as genai
from .config import config

class TweetSummarizer:
    """
    Service class for summarizing categorized tweets using Gemini 2.0 Flash API.
    
    This class takes a list of categorized tweets and generates summaries for each
    category, highlighting key findings, advancements, discussions, or breakthroughs.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the TweetSummarizer with Gemini API credentials.
        
        Args:
            api_key: Optional Gemini API key. If not provided, will use config.
            
        Raises:
            ValueError: If no API key is available
        """
        self.api_key = api_key or config.gemini_api_key
        
        if not self.api_key:
            logging.error("Gemini API key is not configured. Cannot initialize TweetSummarizer.")
            raise ValueError("Missing Gemini API key. Set GEMINI_API_KEY in .env file or provide api_key parameter.")
        
        try:
            genai.configure(api_key=self.api_key)
            self.client = genai
            logging.info("TweetSummarizer initialized successfully with Gemini API")
        except Exception as e:
            logging.error(f"Failed to initialize Gemini client: {e}")
            raise ValueError(f"Failed to initialize Gemini client: {e}")
    
    def summarize_tweets(self, categorized_tweets: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Summarize categorized tweets by grouping them by category and generating summaries.
        
        Args:
            categorized_tweets: List of tweet dictionaries with 'category' field from TweetCategorizer
            
        Returns:
            Dictionary with category names as keys and summary data as values.
            Each summary data contains:
            - summary: Generated summary text
            - tweet_count: Number of tweets in this category
            - tweets: List of original tweets in this category
            
        Raises:
            TypeError: If categorized_tweets is None
        """
        if categorized_tweets is None:
            raise TypeError("categorized_tweets parameter cannot be None")
        
        if not categorized_tweets:
            return {}
        
        # Group tweets by category
        tweets_by_category = self._group_tweets_by_category(categorized_tweets)
        
        # Generate summaries for each category
        summaries = {}
        for category, tweets in tweets_by_category.items():
            try:
                summary_text = self._generate_summary_for_category(category, tweets)
                summaries[category] = {
                    "summary": summary_text,
                    "tweet_count": len(tweets),
                    "tweets": tweets
                }
                logging.debug(f"Generated summary for category '{category}' with {len(tweets)} tweets")
                
            except Exception as e:
                logging.error(f"Error generating summary for category '{category}': {e}")
                # Add fallback summary if individual category summarization fails
                summaries[category] = {
                    "summary": f"Unable to generate summary for {category} due to processing error.",
                    "tweet_count": len(tweets),
                    "tweets": tweets
                }
        
        return summaries
    
    def _group_tweets_by_category(self, categorized_tweets: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group tweets by their category field.
        
        Args:
            categorized_tweets: List of tweet dictionaries with 'category' field
            
        Returns:
            Dictionary with category names as keys and lists of tweets as values
        """
        tweets_by_category = defaultdict(list)
        
        for tweet in categorized_tweets:
            # Handle tweets without category field gracefully
            category = tweet.get('category', 'Uncategorized')
            tweets_by_category[category].append(tweet)
        
        return dict(tweets_by_category)
    
    def _generate_summary_for_category(self, category: str, tweets: List[Dict[str, Any]]) -> str:
        """
        Generate a summary for a specific category using Gemini API.
        
        Args:
            category: The category name
            tweets: List of tweets in this category
            
        Returns:
            Generated summary text
        """
        try:
            prompt = self._build_summarization_prompt(category, tweets)
            
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            
            if not response or not response.text:
                logging.warning(f"Empty response from Gemini API for category: {category}")
                return f"Unable to generate summary for {category} - empty response from API."
            
            return response.text.strip()
            
        except Exception as e:
            logging.error(f"Gemini API error for category '{category}': {e}")
            return f"Unable to generate summary for {category} due to API error."
    
    def _build_summarization_prompt(self, category: str, tweets: List[Dict[str, Any]]) -> str:
        """
        Build the prompt for Gemini API to summarize tweets in a category.
        
        Args:
            category: The category name
            tweets: List of tweets in this category
            
        Returns:
            Formatted prompt string for Gemini API
        """
        if not tweets:
            return f"""
Please provide a brief summary indicating that no tweets were found for the category "{category}" in this week's digest.

Keep the response concise and professional.
            """.strip()
        
        # Extract tweet texts
        tweet_texts = []
        for i, tweet in enumerate(tweets, 1):
            text = tweet.get('text', '')
            if text:
                tweet_texts.append(f"{i}. {text}")
        
        if not tweet_texts:
            return f"""
Please provide a brief summary indicating that no valid tweet content was found for the category "{category}" in this week's digest.

Keep the response concise and professional.
            """.strip()
        
        tweets_section = "\n".join(tweet_texts)
        
        prompt = f"""
Please summarize the following tweets from the "{category}" category for a weekly GenAI digest email.

Focus on:
- Key findings, advancements, or breakthroughs mentioned
- Important discussions or trends
- Notable developments or announcements
- Overall significance to the GenAI community

Tweets to summarize:
{tweets_section}

Provide a concise, informative summary (2-4 sentences) that captures the most important insights and developments from these tweets. Write in a professional tone suitable for a newsletter audience ranging from beginners to experts in AI.
        """
        
        return prompt.strip() 