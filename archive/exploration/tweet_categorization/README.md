# Tweet Categorization System

An intelligent tweet categorization system that automatically classifies tweets based on their content using Gemini 2.0 Flash. Features dynamic category management, metadata enrichment, and support for GenAI-focused content classification.

> **Features**: AI-powered categorization, Dynamic category creation, Metadata enrichment, GenAI-optimized categories  
> **Status**: ✅ Ready for testing and development  
> **Last Updated**: December 2024

## Overview

This system automatically categorizes captured tweets by analyzing their summary text using Gemini 2.0 Flash. It supports both predefined categories and dynamic category creation, making it adaptive to evolving content patterns.

### Key Features

- 🤖 **AI-Powered Classification**: Uses Gemini 2.0 Flash for intelligent content categorization
- 📂 **Dynamic Categories**: Automatically creates new categories when existing ones don't fit
- 📝 **Metadata Enrichment**: Adds `L1_category` and categorization details to tweet metadata
- 🎯 **GenAI Optimized**: Pre-configured with 10 GenAI-focused categories for broad audience appeal
- 📊 **Confidence Scoring**: Provides AI confidence levels and reasoning for each categorization
- 💾 **Persistent Storage**: Updates and maintains categories.json file automatically

## Initial Categories

The system starts with 10 comprehensive GenAI categories designed to appeal to both researchers and newcomers:

1. **Research & Papers** - Academic research, paper releases, scientific findings
2. **Product Announcements** - New AI product launches, feature updates, company announcements  
3. **Tutorials & Education** - Educational content, how-to guides, learning resources
4. **Industry News** - AI industry updates, market trends, business developments
5. **Technical Insights** - Technical deep-dives, architecture discussions, implementation details
6. **Tools & Resources** - AI tools, frameworks, libraries, datasets, useful resources
7. **Career & Jobs** - AI job opportunities, career advice, hiring trends
8. **Events & Conferences** - AI conferences, workshops, meetups, webinars
9. **Opinion & Commentary** - Personal opinions, industry commentary, predictions
10. **Startup News** - AI startup announcements, funding news, acquisitions

## Quick Start

### Basic Usage

```bash
# Categorize tweets for a specific account (original method)
python categorize_tweets.py --account andrewyng

# Direct categorization from capture_metadata.json files (new method)
python categorize_direct.py ./visual_captures

# List available accounts that can be categorized
python categorize_tweets.py --list-accounts

# Test the categorization system
python test_categorization.py
```

### Direct Categorization (Recommended)

The new `categorize_direct.py` script provides a streamlined approach for categorizing tweets directly from `capture_metadata.json` files:

```bash
# Process all capture_metadata.json files in a directory tree
python categorize_direct.py /path/to/base/folder

# Use custom categories file
python categorize_direct.py ./visual_captures --categories custom_categories.json
```

**Features:**
- 🔍 **Recursive scanning**: Finds all `capture_metadata.json` files in subdirectories
- 📝 **Direct text processing**: Uses `tweet_metadata.full_text` or falls back to `api_metadata.text`
- 🏷️ **L1_ prefixed fields**: Future-ready for hierarchical categorization (L2, L3, etc.)
- ⚡ **Simple workflow**: No need to specify account names or folder structures
- 🔄 **Idempotent**: Safely skips already categorized files

### Requirements

```bash
# Install dependencies
pip install google-generativeai python-dotenv pathlib

# Set up environment variables
export GEMINI_API_KEY=your_gemini_api_key
```

## Usage Examples

### Categorize Specific Account

```bash
# Categorize all tweets for @andrewyng
python categorize_tweets.py --account andrewyng

# Use custom base path
python categorize_tweets.py --account andrewyng --base-path ../visual_tweet_capture

# Use custom categories file
python categorize_tweets.py --account andrewyng --categories my_categories.json
```

### Testing and Development

```bash
# Run all tests
python test_categorization.py

# Test specific functionality
python test_categorization.py --test-type single        # Test with sample summaries
python test_categorization.py --test-type andrewyng     # Test with real data
python test_categorization.py --test-type category-mgmt # Test category creation
```

## Output Structure

### Enhanced Metadata

After categorization, tweet metadata files are enriched with L1_ prefixed fields for hierarchical categorization support:

```json
{
  "tweet_metadata": {
    "full_text": "Original tweet text...",
    "summary": "AI-generated summary...",
    "extraction_timestamp": "2025-06-02T20:54:28.970150"
  },
  "L1_category": "Research & Papers",
  "L1_categorization_confidence": "high",
  "L1_categorization_reasoning": "The tweet discusses a new research paper on transformer efficiency, which clearly fits the Research & Papers category.",
  "L1_categorization_timestamp": "2024-12-01T21:40:50.665306"
}
```

### Dynamic Categories File

The `categories.json` file is automatically updated when new categories are discovered:

```json
{
  "categories": [
    {
      "name": "Research & Papers",
      "description": "Academic research, paper releases, scientific findings, and theoretical developments in AI/ML"
    },
    {
      "name": "AI Ethics & Safety", 
      "description": "Discussions about AI ethics, safety concerns, and responsible AI development"
    }
  ],
  "metadata": {
    "created_date": "2024-12-01",
    "last_updated": "2024-12-01",
    "version": "1.0",
    "total_categories": 11
  }
}
```

## Example Processing Output

```bash
🎯 TWEET CATEGORIZATION PIPELINE
======================================================================
📋 PROCESSING OVERVIEW:
   👤 Account: @andrewyng
   📁 Base path: .
   🤖 AI Model: Gemini 2.0 Flash

🔧 Initializing TweetCategorizer...
✅ Categorizer initialized successfully

📊 Current categories (10 total):
   1. Research & Papers
   2. Product Announcements
   3. Tutorials & Education
   4. Industry News
   5. Technical Insights
   [...]

🔄 Processing @andrewyng tweets...

✅ Successfully categorized tweet_1234567890
   📂 Category: Tutorials & Education
   🎯 Confidence: high
   💭 Reasoning: The tweet shares educational content about machine learning fundamentals

✅ CATEGORIZATION SUCCESS FOR @ANDREWYNG!
   📊 Total folders: 15
   ✅ Processed successfully: 14
   ❌ Failed: 1

📊 FINAL STATISTICS:
   📈 Total categories: 11
   🆕 New categories created: 1
   📝 New categories: AI Ethics & Safety
```

## Integration with Existing Pipeline

### Standalone Usage

```bash
# Step 1: Capture tweets (existing pipeline)
python ../tweet_processing/capture_and_extract.py --account andrewyng

# Step 2: Categorize tweets (new feature)
python categorize_tweets.py --account andrewyng
```

### Programmatic Integration

```python
from tweet_categorizer import TweetCategorizer

# Initialize categorizer
categorizer = TweetCategorizer()

# Categorize single summary
category, details = categorizer.categorize_tweet_summary(
    "Announces new breakthrough in transformer efficiency research"
)

# Process entire account
result = categorizer.process_account_captures(".", "andrewyng")
```

## Configuration

### Custom Categories

Create your own `categories.json` file:

```json
{
  "categories": [
    {
      "name": "Custom Category",
      "description": "Description of the custom category"
    }
  ],
  "metadata": {
    "created_date": "2024-12-01",
    "last_updated": "2024-12-01", 
    "version": "1.0",
    "total_categories": 1
  }
}
```

### Environment Variables

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key

# Optional - default model is gemini-2.0-flash
GEMINI_MODEL=gemini-2.0-flash
```

## File Structure

```
tweet_categorization/
├── README.md                    ← This file
├── categories.json              ← Category definitions (now with 11 categories)
├── prompt_templates.py          ← Categorization prompts
├── tweet_categorizer.py         ← Core categorization logic
├── categorize_tweets.py         ← Account-based pipeline script
├── categorize_direct.py         ← Direct metadata file processing (recommended)
└── test_categorization.py       ← Testing framework
```

## How It Works

### 1. **Content Analysis**
- Reads tweet summary from metadata files
- Sends summary to Gemini 2.0 Flash with current categories
- AI analyzes content and assigns appropriate category

### 2. **Dynamic Category Management**
- If AI determines existing categories don't fit, it creates a new one
- New categories are automatically added to `categories.json`
- Future categorizations use the updated category list

### 3. **Metadata Enrichment**
- Adds `L1_category` field to tweet metadata
- Includes confidence score and AI reasoning
- Timestamps the categorization for tracking

### 4. **Quality Assurance**
- Validates AI responses for required fields
- Handles edge cases (empty summaries, API failures)
- Provides detailed logging for debugging

## Best Practices

### For Production Use

1. **Review New Categories**: Periodically review auto-generated categories for relevance
2. **Backup Categories**: Keep backups of your `categories.json` file
3. **Monitor Confidence**: Low confidence scores may indicate need for category refinement
4. **Batch Processing**: Process accounts in batches to manage API costs

### For Development

1. **Test with Samples**: Use `test_categorization.py` for development testing
2. **Custom Categories**: Start with domain-specific categories for your use case
3. **Iterative Refinement**: Let the system learn and create categories organically
4. **Monitor Performance**: Track categorization accuracy over time

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Categories file not found" | Ensure `categories.json` exists in the script directory |
| "Missing Gemini API key" | Set `GEMINI_API_KEY` in your `.env` file |
| "No summary found in metadata" | Run text extraction pipeline first to generate summaries |
| "Empty response from Gemini API" | Check API key validity and quota limits |
| "Account folder not found" | Verify the account has captured tweets with metadata |

### Debug Commands

```bash
# Test with sample data
python test_categorization.py --test-type single

# Check available accounts
python categorize_tweets.py --list-accounts

# Test specific account
python test_categorization.py --test-type andrewyng
```

## Performance Metrics

- **Processing Speed**: ~2-3 seconds per tweet (API call latency)
- **Accuracy**: Depends on summary quality and category definitions
- **API Costs**: ~$0.01-0.02 per tweet (Gemini 2.0 Flash pricing)
- **Category Growth**: Typically 1-3 new categories per 100 tweets

## Related Documentation

- [Tweet Processing Pipeline](../tweet_processing/README.md) - Text extraction prerequisite
- [Visual Tweet Capture](../visual_tweet_capture/README.md) - Tweet capture system
- [Main Exploration README](../README.md) - Overview of all exploration features

## Script Comparison

### `categorize_direct.py` (Recommended)
- **Input**: Base path containing `capture_metadata.json` files
- **Text source**: `tweet_metadata.full_text` or `api_metadata.text`
- **Output**: L1_ prefixed categorization fields in same metadata files
- **Use case**: Simple, direct processing of captured tweets
- **Advantages**: Simpler workflow, future-ready field naming, recursive scanning

### `categorize_tweets.py` (Legacy)
- **Input**: Account names and folder structures
- **Text source**: `tweet_metadata.summary` field
- **Output**: Categorization fields in tweet metadata
- **Use case**: Account-specific processing with existing pipeline integration
- **Advantages**: Integration with existing tweet processing pipeline

---

> **Dynamic Categories**: System automatically evolves its categorization as it encounters new content patterns  
> **GenAI Optimized**: Pre-configured categories span from academic research to practical tutorials  
> **Production Ready**: ✅ Comprehensive error handling and testing framework included 