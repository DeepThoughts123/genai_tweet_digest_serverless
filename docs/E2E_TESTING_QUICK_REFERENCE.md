# E2E Testing Quick Reference Guide

## Overview
This guide provides quick reference for using the enhanced E2E testing system for the GenAI Tweets Digest serverless architecture.

## Quick Start

### Basic Usage
```bash
# Run all E2E tests
./scripts/e2e-test.sh

# Run specific test categories
./scripts/e2e-test.sh --infrastructure-only
./scripts/e2e-test.sh --functional-only
./scripts/e2e-test.sh --integration-only
./scripts/e2e-test.sh --performance-only
./scripts/e2e-test.sh --security-only
./scripts/e2e-test.sh --data-only
```

### Environment Configuration
```bash
# Basic environment setup
export ENVIRONMENT="production"
export AWS_REGION="us-east-1"
export STACK_NAME="genai-tweets-digest-production"

# Optional: Enable advanced testing
export E2E_LOAD_TESTS="true"
export E2E_GDPR_TESTS="true"
export E2E_REPORT_DIR="./test-reports"

# Optional: API keys for full testing
export TWITTER_BEARER_TOKEN="your_twitter_token"
export GEMINI_API_KEY="your_gemini_key"
```

## Test Categories

### 1. Infrastructure Tests
**Purpose**: Verify AWS resources are properly deployed
**Duration**: ~30 seconds
**Prerequisites**: AWS CLI configured, CloudFormation stack deployed

```bash
./scripts/e2e-test.sh --infrastructure-only
```

**Tests Include**:
- AWS CLI and credentials
- CloudFormation stack status
- Lambda functions existence
- DynamoDB table existence
- S3 buckets existence
- EventBridge rules
- IAM permissions
- CloudWatch logs

### 2. Functional Tests
**Purpose**: Test individual component functionality
**Duration**: ~2-3 minutes
**Prerequisites**: Infrastructure tests passing

```bash
./scripts/e2e-test.sh --functional-only
```

**Tests Include**:
- Lambda function invocations
- API Gateway endpoints
- DynamoDB operations
- S3 operations
- Environment variables
- Configuration files
- Data integrity
- Error handling

### 3. Integration Tests
**Purpose**: Test end-to-end workflows
**Duration**: ~3-5 minutes (longer with API keys)
**Prerequisites**: Functional tests passing

```bash
./scripts/e2e-test.sh --integration-only
```

**Tests Include**:
- Complete subscription flow
- Various email format validation
- API Gateway to Lambda to DynamoDB flow
- Weekly digest generation (if API keys provided)
- Email template generation

### 4. Performance Tests
**Purpose**: Verify system performance under load
**Duration**: ~2-5 minutes (longer with load tests enabled)
**Prerequisites**: Integration tests passing

```bash
# Basic performance tests
./scripts/e2e-test.sh --performance-only

# With load testing enabled
E2E_LOAD_TESTS=true ./scripts/e2e-test.sh --performance-only
```

**Tests Include**:
- Lambda cold start times
- Concurrent subscription handling (if enabled)
- DynamoDB throttling simulation (if enabled)
- Large dataset processing (if enabled)

### 5. Security Tests
**Purpose**: Verify security measures and compliance
**Duration**: ~1-2 minutes
**Prerequisites**: Basic infrastructure

```bash
# Basic security tests
./scripts/e2e-test.sh --security-only

# With GDPR compliance tests
E2E_GDPR_TESTS=true ./scripts/e2e-test.sh --security-only
```

**Tests Include**:
- Input validation
- Malicious input handling
- Invalid credentials handling
- GDPR compliance (if enabled)

### 6. Data Integrity Tests
**Purpose**: Test data export and integrity
**Duration**: ~1-2 minutes
**Prerequisites**: Some data in the system

```bash
./scripts/e2e-test.sh --data-only
```

**Tests Include**:
- Comprehensive data export
- Data format validation
- Export completeness verification

## Common Usage Scenarios

### Pre-Deployment Validation
```bash
# Quick infrastructure check before deployment
./scripts/e2e-test.sh --infrastructure-only

# Full validation after deployment
./scripts/e2e-test.sh
```

### CI/CD Pipeline Integration
```bash
# In GitHub Actions or similar
export ENVIRONMENT="staging"
export AWS_REGION="us-east-1"
./scripts/e2e-test.sh --infrastructure-only
./scripts/e2e-test.sh --functional-only
./scripts/e2e-test.sh --integration-only
```

### Production Health Check
```bash
# Regular production health monitoring
export ENVIRONMENT="production"
./scripts/e2e-test.sh --infrastructure-only
./scripts/e2e-test.sh --functional-only
```

### Performance Monitoring
```bash
# Weekly performance validation
export E2E_LOAD_TESTS="true"
export E2E_REPORT_DIR="./weekly-reports"
./scripts/e2e-test.sh --performance-only
```

### Security Audit
```bash
# Comprehensive security testing
export E2E_GDPR_TESTS="true"
./scripts/e2e-test.sh --security-only
```

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `production` | Target environment |
| `AWS_REGION` | `us-east-1` | AWS region |
| `STACK_NAME` | `genai-tweets-digest-${ENVIRONMENT}` | CloudFormation stack name |
| `E2E_CLEANUP_ENABLED` | `true` | Enable test cleanup |
| `E2E_LOAD_TESTS` | `false` | Enable load testing |
| `E2E_GDPR_TESTS` | `false` | Enable GDPR compliance tests |
| `E2E_REPORT_DIR` | `/tmp` | Report output directory |
| `TWITTER_BEARER_TOKEN` | - | Twitter API token (optional) |
| `GEMINI_API_KEY` | - | Gemini API key (optional) |

## Output and Reports

### Console Output
The tests provide color-coded output with:
- 🔵 Blue: Information and progress
- 🟢 Green: Successful tests
- 🔴 Red: Failed tests
- 🟡 Yellow: Warnings and skipped tests
- 🟣 Purple: Section headers

### Generated Reports
1. **JSON Report**: `/tmp/e2e-comprehensive-report-YYYYMMDD_HHMMSS.json`
   - Machine-readable test results
   - Performance metrics
   - Environment information

2. **Summary Report**: `/tmp/e2e-summary-YYYYMMDD_HHMMSS.txt`
   - Human-readable summary
   - Failed test details
   - Resource information

### Sample Report Structure
```json
{
  "test_session": {
    "timestamp": "2024-01-15T10:30:00.000Z",
    "duration_seconds": 180,
    "environment": "production",
    "region": "us-east-1",
    "stack_name": "genai-tweets-digest-production"
  },
  "results": {
    "total_tests": 25,
    "tests_passed": 24,
    "tests_failed": 1,
    "success_rate_percent": 96
  },
  "failed_tests": [
    "[Performance] Lambda cold start performance"
  ],
  "environment_info": {
    "data_bucket": "genai-tweets-digest-data-production-123456789",
    "subscribers_table": "genai-tweets-digest-subscribers-production",
    "website_bucket": "not_deployed"
  }
}
```

## Troubleshooting

### Common Issues

#### AWS Credentials
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Configure if needed
aws configure
```

#### Stack Not Found
```bash
# List available stacks
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE

# Use correct stack name
export STACK_NAME="your-actual-stack-name"
```

#### Permission Errors
```bash
# Check IAM permissions
aws iam get-user
aws sts get-caller-identity

# Ensure your user/role has necessary permissions for:
# - CloudFormation (read)
# - Lambda (invoke, get-function)
# - DynamoDB (read/write)
# - S3 (read/write)
# - API Gateway (read)
```

#### Test Failures
1. **Infrastructure Tests Failing**: Check CloudFormation stack status
2. **Functional Tests Failing**: Check Lambda function logs in CloudWatch
3. **Integration Tests Failing**: Verify API Gateway endpoints and Lambda permissions
4. **Performance Tests Failing**: Check Lambda timeout and memory settings

### Debug Mode
```bash
# Enable verbose output
set -x
./scripts/e2e-test.sh --infrastructure-only
set +x
```

### Manual Verification
```bash
# Test individual components
aws lambda invoke --function-name genai-tweets-digest-subscription-production --payload '{}' /tmp/test.json
aws dynamodb scan --table-name genai-tweets-digest-subscribers-production --limit 1
aws s3 ls s3://your-data-bucket-name/
```

## Best Practices

### Regular Testing Schedule
- **Daily**: Infrastructure tests in CI/CD
- **Weekly**: Full E2E test suite
- **Monthly**: Performance and security audits
- **Before Releases**: Complete test suite with load testing

### Test Environment Management
- Use separate AWS accounts/regions for testing when possible
- Clean up test data regularly
- Monitor AWS costs from testing activities
- Use test-specific resource naming

### Reporting and Monitoring
- Archive test reports for trend analysis
- Set up alerts for test failures
- Monitor test execution times
- Track success rates over time

### Security Considerations
- Never commit API keys to version control
- Use IAM roles with minimal required permissions
- Regularly rotate test credentials
- Monitor for unusual test activity

## Integration with CI/CD

### GitHub Actions Example
```yaml
name: E2E Tests
on:
  push:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'  # Weekly

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Run E2E Tests
        env:
          ENVIRONMENT: staging
          E2E_REPORT_DIR: ./reports
        run: |
          ./scripts/e2e-test.sh
      
      - name: Upload Reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: e2e-reports
          path: ./reports/
```

This quick reference guide should help you effectively use the enhanced E2E testing system for the GenAI Tweets Digest serverless architecture. 