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
- **Intelligent Retry Mechanism**: Browser setup retries with exponential backoff and error categorization
- **Browser Failure Recovery**: Automatic cleanup and fallback configurations for improved reliability
- **Network Resilience**: Page loading retry with progressive timeouts and error recovery
- **Production Ready**: Optimized for serverless GenAI digest processing with robust error handling

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

## Reliability & Error Handling

The visual tweet capture system includes comprehensive error handling and retry mechanisms to ensure reliable operation in production environments.

### Browser Retry Mechanism

The `VisualTweetCapturer` class includes configurable retry parameters:

```python
capturer = VisualTweetCapturer(
    headless=True,
    max_browser_retries=3,     # Number of browser setup attempts
    retry_delay=2.0,           # Initial delay between retries (seconds)
    retry_backoff=2.0          # Exponential backoff multiplier
)
```

### Error Categorization

The system intelligently categorizes errors:

- **Transient Errors**: Network timeouts, WebDriver session issues → Retry with exponential backoff
- **Permanent Errors**: Chrome not installed, permission denied → Fail fast (no retry)
- **Unknown Errors**: Unexpected issues → Default to retry for safety

### Multi-Level Fallback Strategy

1. **Primary Browser Setup**: Standard Chrome configuration with retries
2. **Fallback to Non-headless**: If headless mode fails, try visible browser
3. **Minimal Configuration**: Stripped-down Chrome options for maximum compatibility
4. **Page Loading Retries**: Progressive timeouts for network issues

### Production Benefits

- ✅ **Handles ChromeDriver download failures**
- ✅ **Recovers from Chrome startup issues** 
- ✅ **Manages network-related page loading problems**
- ✅ **Prevents unnecessary retries for permanent failures**
- ✅ **Provides clear troubleshooting feedback**
- ✅ **Automatically cleans up failed browser instances**

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
- 🚀 **Production Ready**: Perfect for serverless GenAI digest processing with robust error handling
- 🔄 **Comprehensive Coverage**: Captures ALL content types within lookback window
- 📋 **Clean Metadata**: No duplicate tweet information, optimized file sizes
- ⚡ **Simplified Logic**: Removed Search API dependency for faster execution
- 🛡️ **Reliable Operation**: Intelligent retry mechanism handles browser and network issues

This feature enables robust, scalable visual capture of Twitter content for GenAI processing pipelines with clear account-based organization and production-grade reliability.