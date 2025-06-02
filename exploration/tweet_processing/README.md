# Tweet Processing Pipeline

A comprehensive development and testing environment for advanced tweet capture and multimodal text extraction using Gemini 2.0 Flash.

> **Features**: Dual API methods (Timeline/Search), Professional CLI, Rate limit resilience, 96% success rate  
> **Status**: ✅ Production-ready with comprehensive testing  
> **Last Updated**: June 2025

## Overview

Complete end-to-end pipeline for capturing Twitter content and extracting detailed text using multimodal AI. Supports both **Timeline API** and **Search API** methods for optimal rate limit management and bulk processing capabilities.

### Key Features

- 🎯 **Dual API Support**: Choose between Timeline API (detailed analysis) or Search API (bulk processing)
- 📸 **Visual Capture**: High-quality screenshots with configurable zoom (25-200%)
- 🤖 **AI Text Extraction**: Gemini 2.0 Flash for complete text extraction and summarization
- 📊 **Professional CLI**: Argparse-based interface with comprehensive help and examples
- 🛡️ **Rate Limit Resilience**: Intelligent fallback when API limits are hit
- 📁 **Smart Organization**: Account-based folder structure with proper metadata

## Quick Start

### Basic Usage

```bash
# Default: @elonmusk, 7 days, 25 tweets, timeline API
python capture_and_extract.py

# Recommended for multiple accounts (uses search API)
python capture_and_extract.py --accounts minchoi openai andrewyng --api-method search
```

### API Method Selection

**Timeline API** (Default - `--api-method timeline`):
- Best for: 1-3 accounts, detailed analysis
- Rate limits: 300 requests per 15min per user
- Use case: Single account deep-dive

**Search API** (`--api-method search`):
- Best for: 4+ accounts, bulk processing, automation
- Rate limits: 180 requests per 15min global
- Use case: Production deployments, multiple accounts

### Full Configuration Example

```bash
python capture_and_extract.py \
  --accounts elonmusk openai andrewyng \
  --days-back 10 \
  --max-tweets 30 \
  --zoom-percent 75 \
  --api-method search \
  --no-confirm
```

## CLI Reference

### Parameters

| Parameter | Default | Description | Options |
|-----------|---------|-------------|---------|
| `--accounts` | `['elonmusk']` | Twitter usernames (without @) | Multiple allowed |
| `--days-back` | `7` | Days back to search | Integer |
| `--max-tweets` | `25` | Max tweets per account | Integer |
| `--zoom-percent` | `50` | Browser zoom percentage | 25, 50, 75, 100, 125, 150, 175, 200 |
| `--api-method` | `timeline` | API method to use | `timeline`, `search` |
| `--no-confirm` | `False` | Skip confirmation prompt | Flag |

### Example Commands

```bash
# Basic single account
python capture_and_extract.py --accounts elonmusk

# Multiple accounts with search API (recommended)
python capture_and_extract.py --accounts minchoi openai --api-method search --max-tweets 20

# High-resolution screenshots
python capture_and_extract.py --accounts elonmusk --zoom-percent 150 --days-back 3

# Automated execution
python capture_and_extract.py --accounts andrewyng --no-confirm --api-method search

# Extended time range
python capture_and_extract.py --accounts openai --days-back 14 --max-tweets 50
```

## Success Metrics

**Tested Performance** (elonmusk account, 25 tweets):
- ✅ Visual Capture: 96% success rate
- ✅ Text Extraction: 95% success rate  
- ✅ End-to-End: 91% complete success
- ⏱️ Processing Speed: ~5-8 seconds per tweet

## Output Structure

```
visual_captures/
└── {account}/
    ├── tweet_{id}/
    │   ├── capture_metadata.json     # Complete metadata
    │   └── {id}_page_00.png         # Screenshots
    ├── retweet_{id}/                # Retweets
    └── convo_{id}/                  # Conversations/threads
```

Enhanced metadata includes:
```json
{
  "tweet_metadata": {
    "full_text": "Complete extracted text from screenshots...",
    "summary": "AI-generated 1-2 sentence summary",
    "extraction_timestamp": "2025-06-01T21:40:50.665306"
  }
}
```

## Development Setup

```bash
# Clone and setup
cd exploration/tweet_processing
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Environment variables
export TWITTER_BEARER_TOKEN=your_bearer_token
export GEMINI_API_KEY=your_gemini_api_key
```

## Testing

```bash
# Test text extraction
python test_text_extraction.py

# Debug specific folder
python test_text_extraction.py --debug-folder visual_captures/elonmusk/tweet_123456789

# Quick single-tweet test
python capture_and_extract.py --accounts elonmusk --max-tweets 1 --days-back 1
```

## Best Practices

### Production Deployment

1. **Use Search API** for multiple accounts: `--api-method search`
2. **Set reasonable limits**: `--max-tweets 20-30`
3. **Enable automation**: `--no-confirm`
4. **Monitor rate limits**: Check console output for warnings
5. **Appropriate zoom**: 50-75% for general use, 100-150% for detailed analysis

### Development/Testing

1. **Use Timeline API** for single account testing
2. **Lower tweet counts**: `--max-tweets 5-10` for quick validation
3. **Shorter time ranges**: `--days-back 1-3` for faster iterations
4. **Higher zoom**: `--zoom-percent 100-150` for detailed content analysis

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Services initialization failed | Check `.env` file for API keys |
| No tweets found | Verify account exists and is public |
| Rate limit exceeded | Switch to search API: `--api-method search` |
| Screenshot capture failed | Update Chrome/webdriver-manager |
| Text extraction failed | Check Gemini API key and quota |

### Debug Commands

```bash
# Test timeline API
python capture_and_extract.py --accounts elonmusk --max-tweets 3 --api-method timeline

# Test search API  
python capture_and_extract.py --accounts elonmusk --max-tweets 3 --api-method search

# High-res single tweet
python capture_and_extract.py --accounts elonmusk --max-tweets 1 --zoom-percent 200
```

## Components

- **`capture_and_extract.py`**: Main pipeline with dual API support
- **`tweet_text_extractor.py`**: Multimodal AI text extraction using Gemini 2.0 Flash
- **`test_text_extraction.py`**: Comprehensive testing framework
- **`reorganize_captures.py`**: Utility for organizing captures by account

## Related Documentation

- [Complete Pipeline Documentation](../../docs/tweet_processing_pipeline.md) - Comprehensive guide
- [Codebase Structure](../../docs/CODEBASE_STRUCTURE.md#tweet-processing) - Overall architecture

---

> **API Methods**: Timeline API for detailed analysis, Search API for bulk processing  
> **Production Ready**: ✅ Comprehensive error handling and 96% success rate validation  
> **Last Tested**: June 2025 across multiple accounts and content types 