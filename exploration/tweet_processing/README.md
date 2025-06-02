# Tweet Processing Pipeline

This folder contains a comprehensive pipeline that combines **visual tweet capture** and **multimodal text extraction** using Gemini 2.0 Flash. The pipeline provides a complete end-to-end solution with professional command-line interface and robust error handling.

## 🎯 Purpose

The pipeline performs:
- **🔍 Visual Tweet Capture**: Screenshots of Twitter content with configurable zoom
- **📝 Complete Text Extraction**: Using Gemini 2.0 Flash multimodal AI
- **📄 AI-Generated Summaries**: Concise 1-2 sentence summaries
- **🛡️ Rate Limit Resilience**: Intelligent fallback when Twitter API fails
- **⚙️ Professional CLI**: Argparse-based interface with comprehensive help

## 📁 Files

- **`capture_and_extract.py`** - Main pipeline with argparse CLI interface
- **`tweet_text_extractor.py`** - Multimodal text extraction service using Gemini 2.0 Flash
- **`test_text_extraction.py`** - Comprehensive testing for both local and S3 scenarios
- **`reorganize_captures.py`** - Utility to reorganize captures by account
- **`README.md`** - This documentation

## 🚀 Quick Start

### Prerequisites

1. **Environment variables** in your `.env` file:
   ```bash
   TWITTER_BEARER_TOKEN=your_twitter_bearer_token
   GEMINI_API_KEY=your_gemini_api_key
   ```

2. **Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Basic Usage

```bash
# Default: elonmusk, 7 days, 25 tweets, 50% zoom
python capture_and_extract.py

# Custom configuration
python capture_and_extract.py --accounts openai andrewyng --days-back 10 --max-tweets 30 --zoom-percent 75

# Automated execution (no confirmation prompt)
python capture_and_extract.py --accounts minchoi --no-confirm

# Get help with all options
python capture_and_extract.py --help
```

## 🎛️ Command Line Interface

### Available Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--accounts` | list | `['elonmusk']` | Twitter usernames to process (without @) |
| `--days-back` | int | `7` | Number of days back to search |
| `--max-tweets` | int | `25` | Maximum tweets to capture per account |
| `--zoom-percent` | int | `50` | Browser zoom percentage (25-200) |
| `--no-confirm` | flag | `False` | Skip confirmation prompt |

### Usage Examples

```bash
# Multiple accounts with custom settings
python capture_and_extract.py \
  --accounts elonmusk openai andrewyng \
  --days-back 10 \
  --max-tweets 30 \
  --zoom-percent 75

# High-resolution screenshots for detailed analysis
python capture_and_extract.py \
  --accounts technical_researcher \
  --zoom-percent 125 \
  --days-back 3

# Automated CI/CD execution
python capture_and_extract.py \
  --accounts account1 account2 \
  --no-confirm
```

## 🔧 How It Works

### Pipeline Overview

The pipeline consists of two main steps:

**Step 1: Tweet Capture**
- Fetches recent tweets from specified accounts using Twitter API
- Creates visual screenshots with configurable zoom levels
- Handles rate limiting with intelligent URL-based username extraction
- Organizes captures in account-based folder structure

**Step 2: Text Extraction**
- Processes captured screenshots using Gemini 2.0 Flash
- Extracts complete text content from visual representations
- Generates AI-powered summaries (1-2 sentences)
- Updates metadata files with enhanced information

### Rate Limit Resilience

When Twitter API fails (429 Too Many Requests):
```
⚠️ Could not fetch API metadata, proceeding with visual capture only
📝 Extracted username from URL: @elonmusk
```

The system automatically:
- Extracts usernames from tweet URLs
- Continues with visual capture
- Maintains proper folder organization
- Preserves data integrity

### Content Processing
- **Processes**: Individual tweets (tweet_*) and retweets (retweet_*)
- **Skips**: Conversation folders (convo_*) to avoid duplication
- **Detects**: Content types automatically for proper handling

## 🧪 Testing

### Running Tests

```bash
# Test the complete pipeline
python capture_and_extract.py --accounts test_account --max-tweets 5

# Test only text extraction
python test_text_extraction.py
```

### Test Options in test_text_extraction.py

1. **S3 captures** - Downloads and processes S3 captures
2. **Local captures** - Processes local visual_captures folder  
3. **Single folder** - Debug mode for specific folders
4. **All tests** - Comprehensive test suite

### Test Results Example

```
🎯 TEXT EXTRACTION TESTING
📅 2025-06-01 21:40:50
======================================================================

📁 Found visual captures at: visual_captures
📊 Found 1 account(s) to process:
   • @elonmusk

======================================================================
🔄 PROCESSING TEXT EXTRACTION: @elonmusk
======================================================================
🔍 Found 25 tweet folders to process

📝 Processing: tweet_1929239888144081201
   ✅ Successfully extracted text and summary
   📝 Text: Tesla Owners Silicon Valley @teslaownersSV BREAKING: X chat has video calling...
   📄 Summary: Tesla Owners Silicon Valley announced that X chat now has video calling...

✅ ACCOUNT PROCESSING COMPLETE FOR @elonmusk
   📊 Processed successfully: 24/25
   ❌ Failed: 1

Success Rate: 96%
```

## 📊 Expected Output

### Before Processing
```json
{
  "tweet_metadata": {
    "id": "1928839759603867952", 
    "text": "9. Colorize and restore old photo\\nhttps://t.co/X4GkBgXmvS",
    "metrics": {
      "likes": 102,
      "retweets": 3
    }
  }
}
```

### After Processing  
```json
{
  "tweet_metadata": {
    "id": "1928839759603867952",
    "text": "9. Colorize and restore old photo\\nhttps://t.co/X4GkBgXmvS", 
    "full_text": "9. Colorize and restore old photo\n\nmin @minchoi\n102 likes, 3 retweets, 4 replies\nPosted on 2025-05-31T15:43:29+00:00\n\nImage shows before/after photo restoration example",
    "summary": "Demonstrates AI-powered photo colorization and restoration capabilities with before/after comparison.",
    "extraction_timestamp": "2025-06-01T13:30:45.123456",
    "metrics": {
      "likes": 102, 
      "retweets": 3
    }
  }
}
```

## 🔄 Integration with Visual Capture Service

This service works seamlessly with our Visual Tweet Capture Service:

1. **Capture**: Visual Tweet Capture Service creates screenshots and metadata
2. **Extract**: This service processes screenshots and extracts text
3. **Enhance**: Metadata is updated with complete text and summaries

### Folder Structure Support
```
s3://bucket/visual_captures/2025-06-01/minchoi/
├── tweet_1928839759603867952/           ← ✅ Processes individual tweets
│   ├── 1928839759603867952_*.png
│   └── capture_metadata.json           ← Updates this file
├── retweet_1928459894048330012/         ← ✅ Processes retweets  
│   ├── 1928459894048330012_*.png
│   └── capture_metadata.json           ← Updates this file
└── convo_1929194553384243458/           ← ❌ Skips conversations
    ├── metadata.json
    └── tweet_*/
```

## 🧪 Testing Examples

### Test with S3 Captures
```bash
python test_text_extraction.py
# Choose option 1: Test with S3 captures
```

### Test with Local Files
```bash
# Download some captures first
aws s3 sync s3://tweets-captured/visual_captures/2025-06-01/minchoi/ ./visual_captures/2025-06-01/minchoi/

python test_text_extraction.py
# Choose option 2: Test with local captures
```

### Debug Single Folder
```bash
python test_text_extraction.py
# Choose option 3: Test single folder
# Enter path: ./visual_captures/2025-06-01/minchoi/tweet_1928839759603867952
```

## ⚠️ Important Notes

1. **API Costs**: Each image sent to Gemini 2.0 Flash incurs API costs
2. **Rate Limits**: Gemini API has rate limits - service includes error handling
3. **Conversation Skipping**: Only processes individual tweets, not thread conversations
4. **File Updates**: Modifies existing metadata.json files in place
5. **Base64 Encoding**: Currently uses base64 for image transfer (efficient for small images)

## 🔧 Configuration

### Environment Variables
```bash
# Required
GEMINI_API_KEY=your_gemini_api_key

# Optional (for S3 testing)
S3_BUCKET_TWEET_CAPTURED=tweets-captured
AWS_PROFILE=your_aws_profile
```

### Customization
You can modify the service for different use cases:
- **Prompt Engineering**: Edit `_build_extraction_prompt()` for different extraction goals
- **Response Parsing**: Modify `_parse_extraction_response()` for different output formats  
- **Filtering Logic**: Change `_is_conversation_folder()` to process different content types

## 🚀 Production Usage

This service is designed for:
- **Batch processing** of captured tweets
- **Enhancement** of existing visual captures
- **Integration** with digest generation pipelines
- **Research** and content analysis workflows

Perfect for extracting structured data from visual tweet content for further processing and analysis! 📊 