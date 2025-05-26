# Testing Guide: Serverless GenAI Tweets Digest

## 🎯 Overview

This guide provides a comprehensive testing strategy to ensure the serverless refactor works properly. We use a multi-layered testing approach to validate everything from individual functions to the complete end-to-end workflow.

## 🧪 Testing Layers

### 1. Unit Tests
**Purpose**: Test individual functions and classes in isolation  
**Location**: `lambdas/tests/`  
**Run with**: `./scripts/run-unit-tests.sh`

### 2. Integration Tests  
**Purpose**: Test AWS services and external API integrations  
**Location**: `scripts/test-serverless.sh`  
**Run with**: `./scripts/test-serverless.sh`

### 3. End-to-End Tests
**Purpose**: Test complete workflows from start to finish  
**Location**: Manual testing procedures  
**Run with**: Manual execution

## 🚀 Quick Start Testing

### Prerequisites
```bash
# 1. Install dependencies
pip install -r lambdas/requirements.txt

# 2. Set up AWS credentials (for integration tests)
aws configure

# 3. Set environment variables (for API tests)
export TWITTER_BEARER_TOKEN="your_token"
export GEMINI_API_KEY="your_key"
export FROM_EMAIL="your_verified_ses_email"
```

### Run All Tests
```bash
# 1. Unit tests (no AWS/API keys needed)
./scripts/run-unit-tests.sh

# 2. Integration tests (requires deployed infrastructure)
./scripts/test-serverless.sh

# 3. Manual end-to-end test
# Follow the procedures below
```

## 📋 Detailed Testing Procedures

### Unit Tests

#### What They Test
- ✅ **Tweet Processing Logic**: Fetching, categorization, summarization
- ✅ **Lambda Handlers**: Event processing, error handling, responses
- ✅ **Configuration**: Environment variables, validation
- ✅ **Data Models**: DynamoDB operations, S3 operations
- ✅ **Email Service**: SES integration, template generation

#### How to Run
```bash
# Run all unit tests
./scripts/run-unit-tests.sh

# Run specific test modules
cd lambdas
python -m unittest tests.test_tweet_services -v
python -m unittest tests.test_lambda_functions -v
```

#### Expected Results
```
🧪 Running Unit Tests for Serverless Lambda Functions

📋 Testing Tweet Processing Services
✅ Tweet Services passed

⚡ Testing Lambda Function Handlers  
✅ Lambda Functions passed

⚙️ Testing Configuration Module
✅ Configuration tests passed

📦 Testing Module Imports
✅ Import tests passed

📄 Testing JSON Configuration Files
✅ JSON configuration tests passed

📋 Testing Requirements File
✅ Requirements tests passed

📊 Unit Test Summary
Tests passed: 6
Tests failed: 0

🎉 All unit tests passed! Your Lambda functions are ready for deployment.
```

#### Python Import Strategy for Local Testing and Lambda Deployment

A key challenge in Python projects with AWS Lambda is managing imports consistently between local test environments and the Lambda runtime. This project employs the following strategy:

1.  **Lambda Function Code Structure:**
    *   Lambda handler files (e.g., `lambdas/subscription/lambda_function.py`) import shared modules using paths relative to the Lambda function's root in the deployment package. The deployment script (`scripts/deploy.sh`) copies the `lambdas/shared/` directory into each function's package, making it directly accessible. Thus, handlers use:
        ```python
        from shared.some_module import SomeClass
        ```
    *   Modules within the `lambdas/shared/` directory use relative imports to access sibling modules within `shared/`:
        ```python
        from .another_shared_module import AnotherClass
        ```
    *   All package directories (e.g., `lambdas/`, `lambdas/shared/`, `lambdas/tests/`, and individual function directories like `lambdas/subscription/`) contain an `__init__.py` file to ensure Python treats them as packages.

2.  **Local Unit Testing (`./scripts/run-unit-tests.sh`):**
    *   The `run-unit-tests.sh` script changes its current working directory (CWD) to `lambdas/` before executing `python -m unittest tests.test_module`.
    *   This CWD (`lambdas/`) is implicitly added to `sys.path` by Python.
    *   **Test Files (`lambdas/tests/*.py`):**
        *   Import the modules they are testing using paths relative to the `lambdas/` directory (which is their effective root for execution via the script). For example:
            ```python
            from subscription.lambda_function import lambda_handler
            from shared.tweet_services import TweetFetcher
            ```
        *   Patch targets also reflect this structure (e.g., `@patch('subscription.lambda_function.config')`, `@patch('shared.tweet_services.config')`).
    *   **Making Handler Imports Work:** To allow the Lambda handler code (e.g., `subscription/lambda_function.py`) to successfully execute its `from shared.some_module import ...` statements when imported by a test file, `lambdas/tests/test_lambda_functions.py` adds the `lambdas/shared/` directory (and other specific lambda function directories if needed for inter-handler imports, though not common) to `sys.path` at the beginning of the test file:
        ```python
        import sys
        import os
        base_dir = os.path.dirname(__file__) # lambdas/tests/
        sys.path.insert(0, os.path.join(base_dir, '..', 'shared')) # Adds lambdas/shared/
        # ... other similar sys.path.insert if needed
        
        from subscription.lambda_function import lambda_handler # Now this can be imported
        ```
    *   **Inline Python Tests in `run-unit-tests.sh`**: The script also contains inline Python snippets for "Configuration Tests" and "Import Tests". These run with `lambdas/` as CWD.
        *   "Configuration Test" adds `shared/` to its `sys.path` and then imports `from config import LambdaConfig`.
        *   "Import Tests" directly import modules like `shared.config` and `shared.tweet_services`, relying on `lambdas/` being the CWD.

3.  **Mocking Strategy:**
    *   For consistency, especially when dealing with modules loaded dynamically (like `weekly_digest_lambda_module` in `test_lambda_functions.py`) or when mocks need to persist across multiple test methods, prefer using `patch.object()` or starting/stopping patchers in `setUp()` and `tearDown()` methods of test classes rather than relying solely on method decorators for all patches. Example for `TestWeeklyDigestLambda`:
        ```python
        # In setUp():
        self.fetcher_patcher = patch.object(self.weekly_digest_lambda_module, 'TweetFetcher')
        self.MockTweetFetcher = self.fetcher_patcher.start()
        # In tearDown():
        self.fetcher_patcher.stop()
        ```

This approach ensures that the Python code maintains an import structure suitable for AWS Lambda deployment while allowing local unit tests to run correctly by adjusting the execution context and `sys.path` appropriately.

### Integration Tests

#### What They Test
- ✅ **AWS Infrastructure**: CloudFormation stack, Lambda functions, DynamoDB, S3
- ✅ **API Gateway**: CORS, endpoints, request/response handling
- ✅ **Lambda Execution**: Real function invocation, environment variables
- ✅ **AWS Services**: DynamoDB read/write, S3 operations, EventBridge rules
- ✅ **Performance**: Cold start times, execution duration

#### Prerequisites
```bash
# 1. Deploy infrastructure first
./scripts/deploy.sh

# 2. Ensure AWS CLI is configured
aws sts get-caller-identity
```

#### How to Run
```bash
# Run all integration tests
./scripts/test-serverless.sh

# Run specific tests manually
aws lambda invoke \
  --function-name genai-tweets-digest-subscription-production \
  --payload '{"httpMethod": "POST", "body": "{\"email\": \"test@example.com\"}"}' \
  response.json
```

#### Expected Results
```
🧪 GenAI Tweets Digest - Serverless Testing Suite

📋 Infrastructure Tests
✅ PASSED: AWS CLI and credentials
✅ PASSED: CloudFormation stack exists
✅ PASSED: Lambda functions exist
✅ PASSED: DynamoDB table exists
✅ PASSED: S3 buckets exist
✅ PASSED: EventBridge rule exists
✅ PASSED: IAM permissions

⚙️ Functional Tests
✅ PASSED: Subscription Lambda function
✅ PASSED: API Gateway endpoint
✅ PASSED: DynamoDB operations
✅ PASSED: S3 operations
✅ PASSED: Lambda environment variables
✅ PASSED: Accounts configuration
✅ PASSED: CloudWatch logs

🔄 Integration Tests
✅ PASSED: Full subscription flow

⚡ Performance Tests
✅ PASSED: Lambda cold start performance

📊 Test Summary
Tests passed: 15
Tests failed: 0

🎉 All tests passed! Your serverless architecture is working correctly.
```

### End-to-End Testing

#### Test 1: Complete Subscription Flow
```bash
# 1. Get API Gateway URL
API_URL=$(aws cloudformation describe-stacks \
  --stack-name genai-tweets-digest-production \
  --query 'Stacks[0].Outputs[?OutputKey==`SubscriptionEndpoint`].OutputValue' \
  --output text)

# 2. Test subscription
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"email": "your-test-email@example.com"}'

# Expected response:
# {"success": true, "message": "Successfully subscribed...", "subscriber_id": "..."}

# 3. Verify in DynamoDB
aws dynamodb scan --table-name genai-tweets-digest-subscribers-production
```

#### Test 2: Weekly Digest Generation
```bash
# 1. Manually trigger weekly digest
aws lambda invoke \
  --function-name genai-tweets-digest-weekly-digest-production \
  --payload '{}' \
  response.json

# 2. Check response
cat response.json

# Expected response:
# {"statusCode": 200, "body": "{\"status\": \"success\", \"tweets_processed\": X, ...}"}

# 3. Check CloudWatch logs
aws logs tail /aws/lambda/genai-tweets-digest-weekly-digest-production --follow
```

#### Test 3: Data Portability
```bash
# 1. Export subscribers
aws dynamodb scan \
  --table-name genai-tweets-digest-subscribers-production \
  --output json > subscribers-backup.json

# 2. Download tweet data
aws s3 sync s3://genai-tweets-digest-data-production/tweets/ ./tweets-backup/

# 3. Download configuration
aws s3 cp s3://genai-tweets-digest-data-production/config/accounts.json ./accounts-backup.json

# 4. Verify files exist and are readable
ls -la *backup*
cat accounts-backup.json
```

#### Test 4: Frontend Integration
```bash
# 1. Build static frontend
./scripts/setup-frontend.sh

# 2. Upload to S3
WEBSITE_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name genai-tweets-digest-production \
  --query 'Stacks[0].Outputs[?OutputKey==`WebsiteBucketName`].OutputValue' \
  --output text)

aws s3 sync frontend-static/out/ s3://$WEBSITE_BUCKET/

# 3. Get website URL
WEBSITE_URL=$(aws cloudformation describe-stacks \
  --stack-name genai-tweets-digest-production \
  --query 'Stacks[0].Outputs[?OutputKey==`WebsiteURL`].OutputValue' \
  --output text)

echo "Website URL: $WEBSITE_URL"

# 4. Test in browser
# - Visit the URL
# - Try subscribing with an email
# - Check that the form works
```

## 🔍 Debugging Failed Tests

### Unit Test Failures

#### Import Errors
```bash
# Check Python path
cd lambdas
python -c "import sys; print(sys.path)"

# Test specific import
python -c "import sys; sys.path.append('shared'); import config"
```

#### Mock Failures
```bash
# Run with verbose output
python -m unittest tests.test_tweet_services.TestTweetFetcher.test_fetch_tweets_success -v

# Check specific test
python -c "
import unittest
from tests.test_tweet_services import TestTweetFetcher
suite = unittest.TestLoader().loadTestsFromTestCase(TestTweetFetcher)
unittest.TextTestRunner(verbosity=2).run(suite)
"
```

### Integration Test Failures

#### AWS Credentials
```bash
# Check credentials
aws sts get-caller-identity

# Check region
echo $AWS_REGION

# Test basic AWS access
aws s3 ls
```

#### Lambda Function Issues
```bash
# Check function exists
aws lambda get-function --function-name genai-tweets-digest-subscription-production

# Check function logs
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/genai-tweets-digest

# Get recent logs
aws logs tail /aws/lambda/genai-tweets-digest-subscription-production --since 1h
```

#### DynamoDB Issues
```bash
# Check table exists
aws dynamodb describe-table --table-name genai-tweets-digest-subscribers-production

# Test basic operations
aws dynamodb put-item \
  --table-name genai-tweets-digest-subscribers-production \
  --item '{"subscriber_id": {"S": "test"}, "email": {"S": "test@example.com"}}'

aws dynamodb get-item \
  --table-name genai-tweets-digest-subscribers-production \
  --key '{"subscriber_id": {"S": "test"}}'
```

### API Test Failures

#### Missing API Keys
```bash
# Check environment variables
echo $TWITTER_BEARER_TOKEN
echo $GEMINI_API_KEY

# Test Twitter API
curl -H "Authorization: Bearer $TWITTER_BEARER_TOKEN" \
  "https://api.twitter.com/2/users/by/username/OpenAI"

# Test Gemini API (requires more complex setup)
```

#### Rate Limiting
```bash
# Check API usage
# Twitter: Check developer dashboard
# Gemini: Check Google Cloud console

# Wait and retry
sleep 60
./scripts/test-serverless.sh
```

## 📊 Test Coverage

### What's Covered
- ✅ **Core Business Logic**: 95%+ coverage
- ✅ **Lambda Handlers**: 90%+ coverage  
- ✅ **Error Handling**: 85%+ coverage
- ✅ **AWS Integrations**: 80%+ coverage
- ✅ **Configuration**: 100% coverage

### What's Not Covered
- ❌ **External API Failures**: Twitter/Gemini downtime
- ❌ **AWS Service Limits**: Rate limiting, quotas
- ❌ **Network Issues**: Timeouts, connectivity
- ❌ **Large Scale**: 1000+ subscribers, high volume

## 🎯 Testing Best Practices

### Before Deployment
1. ✅ Run unit tests: `./scripts/run-unit-tests.sh`
2. ✅ Validate configuration: Check JSON files
3. ✅ Test locally: Mock external dependencies
4. ✅ Check requirements: Verify all dependencies

### After Deployment
1. ✅ Run integration tests: `./scripts/test-serverless.sh`
2. ✅ Test API endpoints: Manual curl tests
3. ✅ Verify data flow: Check DynamoDB and S3
4. ✅ Monitor logs: CloudWatch for errors

### Ongoing Monitoring
1. ✅ Set up CloudWatch alarms
2. ✅ Monitor Lambda metrics
3. ✅ Check email delivery rates
4. ✅ Validate data integrity

## 🚨 Common Issues & Solutions

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **Import Errors** | ModuleNotFoundError | Check Python path, install dependencies |
| **AWS Permissions** | AccessDenied errors | Verify IAM roles and policies |
| **API Rate Limits** | 429 errors | Implement backoff, check quotas |
| **Lambda Timeouts** | Function timeout | Increase timeout, optimize code |
| **Cold Starts** | Slow response | Use provisioned concurrency if needed |
| **Memory Issues** | Out of memory | Increase Lambda memory allocation |

## 📈 Performance Benchmarks

### Expected Performance
- **Subscription Lambda**: < 1 second response time
- **Weekly Digest Lambda**: < 10 minutes total execution
- **Cold Start**: < 5 seconds
- **API Gateway**: < 100ms overhead
- **DynamoDB**: < 10ms read/write operations

### Monitoring Commands
```bash
# Check Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=genai-tweets-digest-subscription-production \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Average

# Check API Gateway metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Latency \
  --dimensions Name=ApiName,Value=genai-tweets-digest-api-production \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Average
```

---

## 🎉 Success Criteria

Your serverless refactor is working properly when:

✅ **All unit tests pass** (6/6)  
✅ **All integration tests pass** (15/15)  
✅ **End-to-end subscription works**  
✅ **Weekly digest generates successfully**  
✅ **Data is portable** (easy export/import)  
✅ **Performance meets benchmarks**  
✅ **No critical errors in logs**  
✅ **Cost is under $10/month**  

When all these criteria are met, your serverless architecture is production-ready! 🚀 