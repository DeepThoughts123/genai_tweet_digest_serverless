# Integrated Tweet Processing Pipeline

A complete end-to-end tweet processing pipeline that combines:
1. **Tweet fetching** from specified Twitter accounts
2. **Visual capture** of tweet screenshots 
3. **Text extraction** using Gemini 2.0 Flash
4. **AI-powered categorization** of tweet content

## Features

🔍 **Tweet Fetching**: Fetches recent tweets using Twitter API (timeline or search methods)  
📸 **Visual Capture**: Takes cropped screenshots and saves to organized folders  
📝 **Text Extraction**: Uses Gemini 2.0 Flash to extract text and engagement metrics  
🏷️ **AI Categorization**: Automatically categorizes tweets with confidence scores and reasoning  
📊 **Complete Metadata**: Saves comprehensive metadata including summaries and engagement data

## Quick Start

```bash
# Default: Process minchoi, openai, rasbt (last 7 days, max 20 tweets each)
python integrated_tweet_pipeline.py

# Custom accounts
python integrated_tweet_pipeline.py --accounts elonmusk openai

# Custom configuration  
python integrated_tweet_pipeline.py --accounts minchoi openai --days-back 10 --max-tweets 15 --zoom 50

# Different output directory
python integrated_tweet_pipeline.py --output-dir ./my_tweets

# Skip confirmation prompt
python integrated_tweet_pipeline.py --no-confirm
```

## Requirements

### Environment Variables
```bash
TWITTER_BEARER_TOKEN=your_twitter_bearer_token
GEMINI_API_KEY=your_gemini_api_key
```

### Dependencies
- Twitter API access (Bearer Token)
- Google Gemini API access
- Chrome browser (for Selenium)
- Python packages: selenium, google-generativeai, python-dotenv

## Output Structure

The pipeline creates organized folders for each account:

```
pipeline_output/
├── minchoi/
│   ├── tweet_1234567890/
│   │   ├── screenshot_001.png
│   │   ├── screenshot_002.png
│   │   └── capture_metadata.json
│   └── tweet_9876543210/
│       ├── screenshot_001.png
│       └── capture_metadata.json
└── openai/
    └── tweet_5555555555/
        ├── screenshot_001.png
        └── capture_metadata.json
```

## Enhanced Metadata

Each `capture_metadata.json` file contains:

```json
{
  "api_metadata": {
    "text": "Original tweet text from API...",
    "created_at": "2024-12-01T12:00:00.000Z"
  },
  "tweet_metadata": {
    "full_text": "Complete extracted text from screenshot...",
    "summary": "AI-generated 1-2 sentence summary...",
    "reply_count": "123",
    "retweet_count": "456", 
    "like_count": "789",
    "bookmark_count": "45",
    "extraction_timestamp": "2024-12-01T12:30:00.000Z"
  },
  "L1_category": "Research & Papers",
  "L1_categorization_confidence": "high",
  "L1_categorization_reasoning": "Tweet discusses new research findings...",
  "L1_categorization_timestamp": "2024-12-01T12:35:00.000Z"
}
```

## Pipeline Steps

### Step 1: Tweet Fetching
- Fetches recent tweets from specified accounts using Twitter API
- Supports both timeline API (detailed) and search API (bulk processing)
- Configurable time window and tweet limits

### Step 2: Visual Capture
- Takes screenshots using Selenium WebDriver
- Applies intelligent cropping to focus on tweet content
- Saves multiple screenshots per tweet if needed
- Handles different tweet types (tweets, retweets, threads)

### Step 3: Text Extraction
- Uses Gemini 2.0 Flash multimodal AI to extract text from screenshots
- Captures engagement metrics (replies, retweets, likes, bookmarks)
- Generates AI-powered summaries
- Handles truncated content and complete text reconstruction

### Step 4: Categorization
- Analyzes extracted text using Gemini 2.0 Flash
- Assigns tweets to predefined categories (Research, Products, Tutorials, etc.)
- Provides confidence scores and reasoning
- Supports dynamic category creation

## Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--accounts` | `['minchoi', 'openai', 'rasbt']` | Twitter usernames to process |
| `--days-back` | `7` | Number of days back to search |
| `--max-tweets` | `20` | Maximum tweets per account |
| `--zoom` | `30` | Browser zoom percentage (25-200) |
| `--api-method` | `search` | API method (`timeline` or `search`) |
| `--output-dir` | `./pipeline_output` | Output directory |
| `--no-confirm` | `False` | Skip confirmation prompt |

## Performance

- **Processing Speed**: ~30-60 seconds per tweet (including API calls)
- **Success Rate**: Typically 85-95% depending on tweet complexity
- **Storage**: ~1-5MB per tweet (screenshots + metadata)
- **API Costs**: ~$0.02-0.05 per tweet (Gemini API usage)

## Integration with Existing Systems

This pipeline leverages components from:
- `tweet_processing/capture_and_extract.py` - Tweet fetching and visual capture
- `tweet_categorization/categorize_direct.py` - AI categorization logic
- `lambdas/shared/tweet_services.py` - Twitter API integration
- `lambdas/shared/tweet_text_extractor.py` - Text extraction

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Import errors | Ensure all paths in `sys.path` are correct |
| Twitter API errors | Check `TWITTER_BEARER_TOKEN` in `.env` |
| Gemini API errors | Verify `GEMINI_API_KEY` and quota |
| Chrome/Selenium issues | Install Chrome and check browser setup |
| Empty screenshots | Adjust zoom level or crop parameters |

## Examples

### Basic usage with default settings:
```bash
python integrated_tweet_pipeline.py
```

### Process specific accounts with custom settings:
```bash
python integrated_tweet_pipeline.py \
  --accounts elonmusk openai \
  --days-back 14 \
  --max-tweets 10 \
  --zoom 40 \
  --output-dir ./custom_output
```

### Automated processing without prompts:
```bash
python integrated_tweet_pipeline.py \
  --accounts minchoi rasbt \
  --max-tweets 5 \
  --no-confirm
```

---

> **Note**: This is a comprehensive pipeline that processes tweets end-to-end. For testing, start with `--max-tweets 5` to verify everything works before processing larger batches. 