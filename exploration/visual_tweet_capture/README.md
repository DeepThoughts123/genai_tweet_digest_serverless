# Visual Tweet Capture

## Overview

This feature provides browser-based visual capture of Twitter conversations and threads. It captures each tweet individually at 60% page zoom, organizing them in chronologically ordered subfolders with clean metadata.

## Key Features

- **Individual Tweet Capture**: Each tweet captured separately at 60% page zoom
- **Intelligent Duplicate Detection**: Avoids redundant screenshots 
- **ID-Based Ordering**: Tweets organized by increasing tweet ID
- **Clean Folder Structure**: Each tweet in its own subfolder
- **Complete Metadata**: JSON metadata with ID-sorted tweet information
- **Production Ready**: Optimized for serverless GenAI digest processing

## Files

### Core Implementation
- **`visual_tweet_capturer.py`** - Main implementation with browser automation using Selenium

### Test Scripts  
- **`test_individual_conversation_capture.py`** - Test individual tweet capture strategy
- **`test_flux_thread_improved.py`** - Test with specific FLUX 1 Kontext thread

### Documentation
- **`INDIVIDUAL_CONVERSATION_CAPTURE_STRATEGY.md`** - Detailed strategy documentation

### Results
- **`visual_captures/`** - Example capture results with organized folder structure

## Usage

```python
from visual_tweet_capturer import VisualTweetCapturer
from shared.tweet_services import TweetFetcher

# Get thread data
fetcher = TweetFetcher() 
threads = fetcher.detect_and_group_threads('username', 7, 10)
thread = threads[0]

# Capture thread visually
capturer = VisualTweetCapturer(headless=True)
result = capturer.capture_thread_visually(thread)
```

## Output Structure

```
visual_captures/conversation_{id}/
├── metadata.json                    ← ID-sorted metadata
├── tweet_{id_1}/                    ← First tweet by ID
│   └── page_00.png                  ← Single screenshot
├── tweet_{id_2}/                    ← Second tweet by ID  
│   └── page_00.png
└── tweet_{id_N}/                    ← Last tweet by ID
    └── page_00.png
```

## Requirements

- Chrome browser
- Python packages: `selenium`, `pillow`, `webdriver-manager`
- Environment variables for Twitter API access

## Testing

Run the test scripts to verify functionality:

```bash
python test_individual_conversation_capture.py
python test_flux_thread_improved.py
```

This feature enables robust visual capture of Twitter conversations for GenAI processing pipelines. 