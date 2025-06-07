"""
Validation utilities for GenAI Tweet Digest application.
"""

import re
from typing import bool


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email format is valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    return bool(re.match(pattern, email.strip()))


def validate_tweet_id(tweet_id: str) -> bool:
    """
    Validate Twitter tweet ID format.
    
    Args:
        tweet_id: Tweet ID to validate
        
    Returns:
        True if tweet ID format is valid, False otherwise
    """
    if not tweet_id or not isinstance(tweet_id, str):
        return False
    
    # Tweet IDs are numeric and typically 15-20 digits
    return bool(re.match(r'^\d{15,20}$', tweet_id.strip()))


def validate_account_name(account_name: str) -> bool:
    """
    Validate Twitter account name format.
    
    Args:
        account_name: Twitter account name to validate (without @)
        
    Returns:
        True if account name format is valid, False otherwise
    """
    if not account_name or not isinstance(account_name, str):
        return False
    
    # Remove @ if present
    clean_name = account_name.strip().lstrip('@')
    
    # Twitter usernames: 1-15 characters, alphanumeric and underscores
    return bool(re.match(r'^[a-zA-Z0-9_]{1,15}$', clean_name)) 