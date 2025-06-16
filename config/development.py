"""Development configuration."""

import os

# Environment
ENVIRONMENT = "development"
DEBUG = True

# API Settings
TWITTER_API_RATE_LIMIT = 20  # requests per minute
GEMINI_API_RATE_LIMIT = 30   # requests per minute

# Processing Settings
MAX_CONCURRENT_ACCOUNTS = 1
MAX_CONCURRENT_TWEETS = 3
VISUAL_EXTRACTION_BATCH_SIZE = 2

# Output Settings
OUTPUT_DIR = "outputs/development"

# Logging
LOG_LEVEL = "DEBUG"
