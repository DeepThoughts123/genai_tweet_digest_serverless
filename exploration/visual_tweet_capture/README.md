# Visual Tweet Capture

## Overview

This feature provides browser-based visual capture of Twitter conversations, individual tweets, and retweets. It captures each piece of content individually at 60% page zoom, organizing them in account-based folders with clear content type prefixes and clean metadata.

## Key Features

- **Comprehensive Content Capture**: Captures ALL content types (conversations, tweets, retweets)
- **Account-Based Organization**: Each Twitter account gets its own folder
- **Content Type Prefixes**: Clear naming with `convo_`, `tweet_`, `retweet_` prefixes
- **Individual Tweet Capture**: Each tweet captured separately at 60% page zoom
- **Intelligent Duplicate Detection**: Avoids redundant screenshots 
- **ID-Based Ordering**: Tweets organized by increasing tweet ID
- **Cross-Account Testing**: Test with any Twitter account using `--account` parameter
- **Clean Folder Structure**: Each tweet in its own subfolder
- **Complete Metadata**: JSON metadata with ID-sorted tweet information
- **Production Ready**: Optimized for serverless GenAI digest processing

## Files

### Core Implementation
- **`visual_tweet_capturer.py`** - Main implementation with browser automation using Selenium

### Test Scripts  
- **`test_individual_conversation_capture.py`** - Comprehensive capture test with account parameter support
- **`test_flux_thread_improved.py`** - Test with specific FLUX 1 Kontext thread

### Documentation
- **`INDIVIDUAL_CONVERSATION_CAPTURE_STRATEGY.md`** - Detailed strategy documentation

### Results
- **`visual_captures/`** - Account-organized capture results with content type prefixes

## Usage

### Comprehensive Account Capture
```bash
# Test with any Twitter account
python test_individual_conversation_capture.py --account AndrewYNg
python test_individual_conversation_capture.py --account minchoi
```

### Programmatic Usage
```python
from visual_tweet_capturer import VisualTweetCapturer
from shared.tweet_services import TweetFetcher

# Get all content for an account (threads + individual tweets)
fetcher = TweetFetcher() 
content = fetcher.detect_and_group_threads('username', 7, 10)

# Capture all content
capturer = VisualTweetCapturer(headless=True)
for item in content:
    if item.get('is_thread', False):
        result = capturer.capture_thread_visually(item)
    else:
        result = capturer.capture_tweet_visually(item['url'])
```

### Command Line Testing

```bash
# Basic usage with default parameters
python test_individual_conversation_capture.py --account minchoi

# Extended parameters for comprehensive capture
python test_individual_conversation_capture.py --account openai --days 10 --max-tweets 30
```

### ⚠️ Important: max_tweets Parameter

The `max_tweets` parameter controls the **total number of tweets** retrieved from a user's timeline, not per-thread. This is crucial for complete thread capture:

- ❌ **Wrong:** `max_tweets=5` with a 12-tweet thread → Only 5 tweets captured (incomplete)
- ✅ **Correct:** `max_tweets=25` with a 12-tweet thread → All 12 tweets captured (complete)

**Recommended values:**
- For testing: `--max-tweets 25-50`
- For comprehensive capture: `--max-tweets 50-100`
- For production: Set based on expected thread lengths

### Parameters

- `--account, -a`: Twitter account name to test (without @)
- `--days, -d`: Number of days to look back (default: 7)  
- `--max-tweets, -m`: Maximum number of tweets to retrieve (default: 25)

## Output Structure

### Account-Based Organization
```
visual_captures/
├── andrewyng/                           ← Account folder
│   ├── retweet_1928459894048330012/     ← Retweet capture
│   │   ├── page_00.png, page_01.png, page_02.png
│   │   └── capture_metadata.json
│   ├── tweet_1928099650269237359/       ← Individual tweet
│   │   ├── page_00.png, page_01.png, page_02.png, page_03.png  
│   │   └── capture_metadata.json
│   └── tweet_1927384264779170259/       ← Another individual tweet
│       ├── page_00.png
│       └── capture_metadata.json
└── minchoi/                             ← Another account folder
    └── convo_1929194553384243458/       ← Conversation/thread capture
        ├── metadata.json                ← Thread metadata (no duplicate tweet info)
        ├── tweet_1929194553384243458/   ← First tweet by ID
        │   └── page_00.png, page_01.png
        ├── tweet_1929194556383240588/   ← Second tweet by ID
        │   └── page_00.png
        └── tweet_1929194922298556510/   ← Last tweet by ID
            └── page_00.png
```

### Content Type Prefixes
- **`convo_`**: Conversations/threads with multiple tweets
- **`tweet_`**: Individual original tweets
- **`retweet_`**: Reposts/retweets (RT @username)

## Content Detection

The system automatically detects and captures:
- ✅ **Threads/Conversations**: Multi-tweet discussions (uses `convo_` prefix)
- ✅ **Individual Tweets**: Original posts (uses `tweet_` prefix)
- ✅ **Retweets**: Shared content starting with "RT @" (uses `retweet_` prefix)

## Clean Metadata Structure

The metadata has been optimized to eliminate duplication:
- **Before:** Had both `thread_data.thread_tweets` and `ordered_tweets` (duplicate)
- **After:** Only `ordered_tweets` with complete tweet info (no duplication)

## Requirements

- Chrome browser
- Python packages: `selenium`, `pillow`, `webdriver-manager`
- Environment variables for Twitter API access

## Testing

Run the test scripts to verify functionality:

```bash
# Test comprehensive capture with specific accounts
python test_individual_conversation_capture.py --account AndrewYNg
python test_individual_conversation_capture.py --account minchoi

# Test with extended parameters
python test_individual_conversation_capture.py --account openai --days 10 --max-tweets 30
```

## Benefits

- 🎯 **Account Organization**: All content for each account in one place
- 📊 **Content Type Clarity**: Instant visual distinction between content types
- 🔍 **Scalable Structure**: Can easily add more accounts without confusion
- 📁 **Clean Storage**: Each tweet has its own folder with multiple screenshots
- 🚀 **Production Ready**: Perfect for serverless GenAI digest processing
- 🔄 **Comprehensive Coverage**: Captures ALL content types within lookback window
- 📋 **Clean Metadata**: No duplicate tweet information, optimized file sizes
- ⚡ **Simplified Logic**: Removed Search API dependency for faster execution

This feature enables robust, scalable visual capture of Twitter content for GenAI processing pipelines with clear account-based organization.