# Visual Tweet Capture Service

## Overview

Production-ready service for capturing visual screenshots of Twitter content with **intelligent retry mechanism** and S3 storage integration. Designed for serverless environments with comprehensive error handling and reliability features.

## Key Features

### **🔄 Production-Grade Retry Mechanism (NEW)**
- **Intelligent Error Categorization**: Automatic detection of transient vs permanent vs unknown errors
- **Smart Retry Logic**: Only retry appropriate errors, fail fast for permanent issues
- **Exponential Backoff**: Configurable delay progression (default: 2.0s, 2x multiplier)
- **Multi-Level Fallback**: Primary browser setup → minimal config → graceful failure
- **Network Resilience**: Page loading retry with progressive timeouts
- **Resource Management**: Automatic cleanup of failed browser instances

### **📸 Content Capture**
- **Account-based Organization**: Separate folders for each Twitter account
- **Content Type Detection**: Automatically detects threads (convo_), individual tweets (tweet_), and retweets (retweet_)
- **Intelligent Scrolling**: Avoids duplicate screenshots with smart scrolling detection
- **Configurable Zoom**: Adjustable browser zoom percentage for optimal capture quality

### **☁️ S3 Integration**  
- **Date-based Folder Structure**: `YYYY-MM-DD/account/content_type_id/`
- **Automatic Upload**: Screenshots and metadata uploaded to S3 with proper naming
- **Comprehensive Metadata**: Complete capture information with S3 references and no duplication

### **🧪 Comprehensive Testing (24 Tests)**
- **100% Test Coverage**: All retry mechanism functionality thoroughly tested
- **Mocked Dependencies**: Reliable testing with comprehensive mocking strategy
- **Production Validation**: Tested with real browser automation scenarios

## Reliability & Retry Mechanism

### Error Categorization

The service intelligently categorizes errors to determine the appropriate retry strategy:

**Transient Errors** (will retry with backoff):
- Connection timeouts
- Network errors  
- ChromeDriver session creation failures
- Resource temporarily unavailable
- Address already in use

**Permanent Errors** (fail fast, no retry):
- Chrome not found
- Executable not found
- Permission denied
- Unsupported Chrome version

**Unknown Errors** (default to retry):
- Any error not matching specific patterns

### Retry Configuration

```python
service = VisualTweetCaptureService(
    s3_bucket="your-bucket",
    max_browser_retries=3,    # Number of browser setup attempts
    retry_delay=2.0,          # Initial delay between retries (seconds)
    retry_backoff=2.0         # Exponential backoff multiplier
)
```

### Fallback Strategies

1. **Primary Setup**: Full Chrome configuration with all optimization flags
2. **Minimal Configuration**: Basic Chrome options for maximum compatibility
3. **Graceful Failure**: Clear error reporting with troubleshooting suggestions

### Network Resilience

- **Page Loading Retry**: Progressive timeout increases (10s + 5s per retry)
- **Content Loading Wait**: Dynamic wait times based on retry attempt
- **WebDriver Error Recovery**: Specific handling for WebDriver exceptions

## Usage

### Basic Usage

```python
from lambdas.shared.visual_tweet_capture_service import capture_twitter_account_visuals

# Capture with default retry settings
result = capture_twitter_account_visuals(
    account_name="AndrewYNg",
    s3_bucket="my-tweet-captures",
    days_back=7,
    max_tweets=25
)
```

### Advanced Configuration with Custom Retry Settings

```python
from lambdas.shared.visual_tweet_capture_service import VisualTweetCaptureService

# Configure service with custom retry parameters
service = VisualTweetCaptureService(
    s3_bucket="my-tweet-captures",
    zoom_percent=60,
    max_browser_retries=5,      # More aggressive retry for unreliable environments
    retry_delay=1.5,            # Faster initial retry
    retry_backoff=3.0           # More aggressive backoff
)

# Capture account content
result = service.capture_account_content(
    account_name="AndrewYNg",
    days_back=7,
    max_tweets=25
)
```

## Testing

### Comprehensive Test Suite (24 Tests)

The service includes a comprehensive test suite specifically for the retry mechanism:

```bash
cd lambdas
python -m pytest tests/test_visual_tweet_capture_service.py -v
```

#### Test Categories

**Retry Mechanism Tests (12 tests)**:
- Browser setup success/failure scenarios
- Error categorization validation
- Max retries behavior with exponential backoff  
- Automatic cleanup of failed browser instances

**Fallback Configuration Tests (3 tests)**:
- Primary browser setup success validation
- Minimal configuration fallback testing
- All options failure handling scenarios

**Page Navigation Retry Tests (4 tests)**:
- Successful navigation scenarios
- Timeout retry with progressive delays
- WebDriver error recovery testing
- Max retries exceeded behavior

**Integration & Configuration Tests (5 tests)**:
- End-to-end screenshot capture with retry mechanism
- Parameter validation and default values
- Exponential backoff calculation verification
- Exception cleanup and resource management

### Running Specific Test Categories

```bash
# Test intelligent error categorization
python -m pytest tests/test_visual_tweet_capture_service.py::TestRetryMechanism::test_error_categorization_transient -v

# Test browser setup retry logic
python -m pytest tests/test_visual_tweet_capture_service.py::TestRetryMechanism::test_browser_setup_retry_transient_error -v

# Test fallback strategies
python -m pytest tests/test_visual_tweet_capture_service.py::TestFallbackBrowserSetup::test_fallback_minimal_config_success -v

# Test page navigation resilience
python -m pytest tests/test_visual_tweet_capture_service.py::TestPageNavigationRetry::test_page_navigation_retry_timeout_success -v
```

## Architecture

This service provides a simple, scalable way to capture visual screenshots of Twitter content (threads, individual tweets, retweets) and automatically store them in S3 with clean organization and metadata.

## Features

- 🎯 **Account-Based Organization**: Each Twitter account gets its own S3 folder
- 📊 **Content Type Detection**: Automatically detects and prefixes content (`convo_`, `tweet_`, `retweet_`)
- 🔍 **Configurable Zoom**: Adjustable browser zoom percentage for optimal capture
- 📁 **Automatic S3 Organization**: Creates folders and uploads with clean structure
- 📋 **Clean Metadata**: No duplicate information, comprehensive capture details
- ⚡ **Production Ready**: Error handling, logging, temporary file cleanup
- 🛡️ **Robust Retry Mechanism**: Intelligent error categorization and exponential backoff retries
- 🔄 **Browser Failure Recovery**: Automatic cleanup and fallback configurations
- 🌐 **Network Resilience**: Page loading retry with progressive timeouts
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

The service creates a clean, date-based organized folder structure in S3:

```
s3://your-bucket/
└── visual_captures/
    └── 2024-12-19/                         ← Date folder (YYYY-MM-DD)
        ├── andrewyng/                      ← Account folder
        │   ├── retweet_1928459894048330012/    ← Retweet capture
        │   │   ├── 1928459894048330012_20241219_143022_page_00.png
        │   │   ├── 1928459894048330012_20241219_143022_page_01.png
        │   │   └── capture_metadata.json
        │   ├── tweet_1928099650269237359/      ← Individual tweet
        │   │   ├── 1928099650269237359_20241219_143045_page_00.png
        │   │   └── capture_metadata.json
        │   └── capture_summary.json            ← Account summary
        ├── minchoi/                            ← Another account
        │   ├── convo_1929194553384243458/      ← Thread/conversation
        │   │   ├── metadata.json               ← Thread metadata
        │   │   ├── tweet_1929194553384243458/  ← First tweet in thread
        │   │   │   ├── 1929194553384243458_20241219_143102_page_00.png
        │   │   │   └── 1929194553384243458_20241219_143102_page_01.png
        │   │   ├── tweet_1929194556383240588/  ← Second tweet in thread
        │   │   │   └── 1929194556383240588_20241219_143115_page_00.png
        │   │   └── tweet_1929194922298556510/  ← Last tweet in thread
        │   │       └── 1929194922298556510_20241219_143128_page_00.png
        │   └── capture_summary.json
        └── openai/                             ← Third account
            └── capture_summary.json
```

### Folder Structure Benefits

- **📅 Date Organization**: Each day's captures are isolated in date folders (YYYY-MM-DD format)
- **👤 Account Separation**: Clean separation by Twitter account within each date
- **🏷️ Content Type Prefixes**: Easy identification with `convo_`, `tweet_`, `retweet_` prefixes
- **⏰ Timestamped Files**: Screenshot files include capture timestamp for uniqueness
- **📋 Comprehensive Metadata**: Summary files at account level, detailed metadata per content item

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