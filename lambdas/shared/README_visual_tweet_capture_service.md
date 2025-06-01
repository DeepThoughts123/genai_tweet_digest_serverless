# Visual Tweet Capture Service

A production-ready service for capturing visual representations of Twitter content and storing them in S3 with organized folder structure.

## Overview

This service provides a simple, scalable way to capture visual screenshots of Twitter content (threads, individual tweets, retweets) and automatically store them in S3 with clean organization and metadata.

## Features

- 🎯 **Account-Based Organization**: Each Twitter account gets its own S3 folder
- 📊 **Content Type Detection**: Automatically detects and prefixes content (`convo_`, `tweet_`, `retweet_`)
- 🔍 **Configurable Zoom**: Adjustable browser zoom percentage for optimal capture
- 📁 **Automatic S3 Organization**: Creates folders and uploads with clean structure
- 📋 **Clean Metadata**: No duplicate information, comprehensive capture details
- ⚡ **Production Ready**: Error handling, logging, temporary file cleanup
- 🧵 **Complete Thread Capture**: Captures all tweets in threads individually
- 📸 **Intelligent Scrolling**: Avoids duplicate screenshots with smart scrolling

## Quick Start

### Simple Usage (Convenience Function)

```python
from shared.visual_tweet_capture_service import capture_twitter_account_visuals

# Capture all content for an account
result = capture_twitter_account_visuals(
    account_name='minchoi',
    s3_bucket='my-tweet-captures',
    days_back=7,
    max_tweets=25,
    zoom_percent=60
)

if result['success']:
    print(f"✅ Captured {result['total_items_captured']} items")
    print(f"📍 Summary: {result['summary_s3_location']}")
else:
    print(f"❌ Error: {result['error']}")
```

### Advanced Usage (Class-Based)

```python
from shared.visual_tweet_capture_service import VisualTweetCaptureService

# Initialize service with custom settings
service = VisualTweetCaptureService(
    s3_bucket='my-tweet-captures',
    zoom_percent=80
)

# Capture content for multiple accounts
accounts = ['AndrewYNg', 'openai', 'minchoi']
results = []

for account in accounts:
    result = service.capture_account_content(
        account_name=account,
        days_back=10,
        max_tweets=30
    )
    results.append(result)
```

## Parameters

### Core Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `account_name` | str | Required | Twitter account name (without @) |
| `s3_bucket` | str | Required | S3 bucket name for storing captures |
| `days_back` | int | 7 | Number of days to look back |
| `max_tweets` | int | 25 | Maximum tweets to retrieve from timeline |
| `zoom_percent` | int | 60 | Browser zoom percentage for captures |

### Parameter Guidelines

- **`max_tweets`**: Should be high enough to capture complete threads. If an account has a 12-tweet thread but `max_tweets=5`, only 5 tweets total will be retrieved, truncating the thread.
- **`zoom_percent`**: 60% is optimal for most content. Higher values (80%+) for detailed capture, lower values (40-50%) for overview.
- **`days_back`**: Balance between relevance and volume. 7 days for recent content, 14+ for comprehensive analysis.

## S3 Output Structure

The service creates a clean, organized folder structure in S3:

```
s3://your-bucket/
└── visual_captures/
    ├── andrewyng/                          ← Account folder
    │   ├── retweet_1928459894048330012/    ← Retweet capture
    │   │   ├── 1928459894048330012_page_00.png
    │   │   ├── 1928459894048330012_page_01.png
    │   │   └── capture_metadata.json
    │   ├── tweet_1928099650269237359/      ← Individual tweet
    │   │   ├── 1928099650269237359_page_00.png
    │   │   └── capture_metadata.json
    │   └── capture_summary.json            ← Account summary
    └── minchoi/                            ← Another account
        ├── convo_1929194553384243458/      ← Thread/conversation
        │   ├── metadata.json               ← Thread metadata
        │   ├── tweet_1929194553384243458/  ← First tweet in thread
        │   │   ├── 1929194553384243458_page_00.png
        │   │   └── 1929194553384243458_page_01.png
        │   ├── tweet_1929194556383240588/  ← Second tweet in thread
        │   │   └── 1929194556383240588_page_00.png
        │   └── tweet_1929194922298556510/  ← Last tweet in thread
        │       └── 1929194922298556510_page_00.png
        └── capture_summary.json
```

## Response Format

### Success Response

```python
{
    'success': True,
    'account': 'minchoi',
    'total_items_captured': 4,
    'threads_captured': 1,
    'individual_tweets_captured': 3,
    'summary_s3_location': 's3://my-bucket/visual_captures/minchoi/capture_summary.json',
    'captured_items': [
        {
            'type': 'thread',
            'conversation_id': '1929194553384243458',
            'total_tweets': 12,
            'captured_tweets': 12,
            's3_location': 's3://my-bucket/visual_captures/minchoi/convo_1929194553384243458/',
            'success': True
        },
        {
            'type': 'individual_tweet',
            'content_type': 'retweet',
            'tweet_id': '1929117026611515752',
            'screenshot_count': 2,
            's3_location': 's3://my-bucket/visual_captures/minchoi/retweet_1929117026611515752/',
            'success': True
        }
        # ... more items
    ]
}
```

### Error Response

```python
{
    'success': False,
    'account': 'nonexistent_user',
    'error': 'User not found: nonexistent_user',
    'captured_items': []
}
```

## Metadata Files

### Thread Metadata (`metadata.json`)
- **No Duplication**: Clean structure with tweet info only in `ordered_tweets`
- **ID-Based Ordering**: Tweets sorted by increasing tweet ID
- **Complete Info**: Each tweet includes capture results and S3 locations

### Individual Tweet Metadata (`capture_metadata.json`)
- **Content Type**: Automatically detected (tweet/retweet)
- **S3 References**: Direct links to all uploaded screenshots
- **Capture Details**: Timestamp, zoom level, browser info

### Account Summary (`capture_summary.json`)
- **Session Overview**: Total items found vs captured
- **Success Metrics**: Success rate and detailed breakdown
- **Service Config**: Zoom level, S3 bucket, capture settings

## Requirements

### Dependencies
```python
boto3>=1.26.0
selenium>=4.0.0
webdriver-manager>=3.8.0
Pillow>=9.0.0
```

### AWS Configuration
- S3 bucket with write permissions
- AWS credentials configured (IAM role, environment variables, or AWS CLI)

### Browser Requirements
- Chrome/Chromium browser installed
- ChromeDriver (handled automatically by webdriver-manager)

## Error Handling

The service includes comprehensive error handling:

- **Account Not Found**: Returns error response with clear message
- **S3 Upload Failures**: Logs errors but continues with other captures
- **Browser Issues**: Automatic browser cleanup and error recovery
- **Network Timeouts**: Configurable timeouts with graceful degradation
- **Temporary File Cleanup**: Automatic cleanup even on failures

## Production Deployment

### Lambda Function Example

```python
import json
from shared.visual_tweet_capture_service import capture_twitter_account_visuals

def lambda_handler(event, context):
    """
    AWS Lambda handler for visual tweet capture.
    """
    account_name = event.get('account_name')
    s3_bucket = event.get('s3_bucket')
    
    if not account_name or not s3_bucket:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing required parameters'})
        }
    
    result = capture_twitter_account_visuals(
        account_name=account_name,
        s3_bucket=s3_bucket,
        days_back=event.get('days_back', 7),
        max_tweets=event.get('max_tweets', 25),
        zoom_percent=event.get('zoom_percent', 60)
    )
    
    return {
        'statusCode': 200 if result['success'] else 500,
        'body': json.dumps(result)
    }
```

### Environment Variables

```bash
# Twitter API credentials
TWITTER_BEARER_TOKEN=your_bearer_token

# AWS credentials (if not using IAM role)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
```

## Testing

Use the included test script to verify functionality:

```bash
cd exploration/visual_tweet_capture
python test_service.py
```

Update the S3 bucket name in the test script before running real captures.

## Performance Considerations

- **Concurrent Captures**: Each service instance handles one account at a time
- **Memory Usage**: Temporary screenshots stored locally during processing
- **S3 Costs**: Consider lifecycle policies for captured images
- **Rate Limiting**: Twitter API rate limits apply to content fetching

## Best Practices

1. **Use appropriate `max_tweets`** values to capture complete threads
2. **Monitor S3 costs** and implement lifecycle policies
3. **Set up CloudWatch logging** for production monitoring
4. **Use VPC endpoints** for S3 access in Lambda to reduce costs
5. **Implement retry logic** for critical production workflows

This service provides a robust, production-ready solution for visual Twitter content capture with comprehensive S3 integration and clean organization. 