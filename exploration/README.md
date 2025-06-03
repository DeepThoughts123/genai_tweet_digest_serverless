# Exploration

This folder contains experimental features and prototypes for the GenAI Tweet Digest serverless application. Each subfolder represents a distinct feature or idea being explored.

## Current Features

### 📸 Visual Tweet Capture (`visual_tweet_capture/`)

Browser-based visual capture of Twitter conversations and threads using Selenium automation.

**Key Features:**
- Individual tweet capture at configurable zoom levels
- Intelligent duplicate detection  
- ID-based tweet ordering
- Clean subfolder organization
- Production-ready metadata structure

**Status:** ✅ Complete and production-ready

### 📝 Tweet Processing (`tweet_processing/`)

Complete pipeline for capturing tweets and extracting text content using Gemini 2.0 Flash multimodal capabilities.

**Key Features:**
- Dual API support (Timeline/Search)
- Visual screenshot capture with configurable zoom
- AI-powered text extraction and summarization
- Engagement metrics extraction (replies, retweets, likes, bookmarks)
- Professional CLI with comprehensive options

**Status:** ✅ Complete and production-ready

### 🏷️ Tweet Categorization (`tweet_categorization/`)

Intelligent tweet categorization system that automatically classifies tweets based on content using Gemini 2.0 Flash.

**Key Features:**
- AI-powered content classification with 10 GenAI-focused categories
- Dynamic category creation when existing categories don't fit
- Metadata enrichment with L1_category field
- Confidence scoring and AI reasoning
- Persistent category management

**Status:** ✅ Ready for testing and development

## Project Structure

```
exploration/
├── README.md                          ← This file
├── env_template.txt                   ← Environment setup template
├── .gitignore                         ← Git ignore configuration
├── visual_tweet_capture/              ← Visual tweet capture feature
│   ├── README.md                      ← Feature documentation
│   ├── visual_tweet_capturer.py       ← Core implementation
│   ├── test_*.py                      ← Test scripts
│   └── visual_captures/               ← Example results
├── tweet_processing/                  ← Text extraction and processing
│   ├── README.md                      ← Feature documentation
│   ├── capture_and_extract.py         ← Main pipeline script
│   ├── tweet_text_extractor.py        ← Gemini-powered text extraction
│   └── test_text_extraction.py        ← Testing framework
└── tweet_categorization/              ← Content categorization system
    ├── README.md                      ← Feature documentation
    ├── categorize_tweets.py            ← Main categorization script
    ├── tweet_categorizer.py            ← Core classification logic
    ├── categories.json                 ← Category definitions
    └── test_categorization.py          ← Testing framework
```

## Feature Integration

The exploration features can be used independently or as part of an integrated pipeline:

### Complete Pipeline Example

```bash
# Step 1: Capture tweets with visual screenshots
cd visual_tweet_capture
python visual_tweet_capturer.py --account andrewyng --max-tweets 10

# Step 2: Extract text and engagement metrics  
cd ../tweet_processing
python capture_and_extract.py --account andrewyng --max-tweets 10

# Step 3: Categorize tweets based on content
cd ../tweet_categorization  
python categorize_tweets.py --account andrewyng
```

### Individual Feature Usage

```bash
# Visual capture only
cd visual_tweet_capture && python visual_tweet_capturer.py --account andrewyng

# Text processing only (requires existing captures)
cd tweet_processing && python test_text_extraction.py

# Categorization only (requires text extraction)
cd tweet_categorization && python categorize_tweets.py --account andrewyng
```

## Adding New Features

When exploring new ideas or features:

1. Create a new subfolder with a descriptive name
2. Add a README.md explaining the feature
3. Include implementation files and tests
4. Update this main README to list the new feature

## Environment Setup

Copy `env_template.txt` to `.env` and configure your API keys:

```bash
cp env_template.txt .env
# Edit .env with your actual API keys
```

Required environment variables:
```bash
TWITTER_BEARER_TOKEN=your_twitter_bearer_token
GEMINI_API_KEY=your_gemini_api_key
```

## Requirements

See individual feature folders for specific requirements. Generally:
- Python 3.8+
- Required packages vary by feature
- API keys for Twitter and Gemini services

Each feature folder contains its own detailed setup and usage instructions. 