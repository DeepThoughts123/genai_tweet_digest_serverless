# End-to-End Testing Plan

## Overview
This document outlines the complete end-to-end testing strategy for the GenAI Tweets Digest serverless architecture. It covers testing the entire workflow from subscription to digest delivery, incorporating lessons learned from AWS CLI best practices and building upon the existing comprehensive test suite.

## Prerequisites
- AWS CLI configured with appropriate permissions
- CloudFormation stack deployed
- API keys configured in `cf-params.json`
- Test email addresses available
- `jq` installed for JSON parsing
- Python 3.x available for timing calculations

## Test Environment Setup

### Environment Variables
```bash
export PROJECT_NAME="genai-tweets-digest"
export ENVIRONMENT="${ENVIRONMENT:-production}"
export AWS_REGION="${AWS_REGION:-us-east-1}"
export CF_STACK_NAME="${STACK_NAME:-${PROJECT_NAME}-${ENVIRONMENT}}"

# Optional: API keys for full testing
export TWITTER_BEARER_TOKEN="your_twitter_token"
export GEMINI_API_KEY="your_gemini_key"
```

### AWS CLI Best Practices Integration
Based on the AWS CLI best practices document, all AWS commands in tests should:
- Use clean shell execution for JSON output: `zsh -d -f -c "aws command --output json | cat"`
- Execute commands sequentially rather than chained for better debugging
- Use file-based payloads for Lambda invocations to avoid shell expansion issues
- Include proper error handling and logging

## E2E Test Scenarios

### 1. Infrastructure Validation Tests
**Objective**: Verify all AWS resources are properly deployed and configured.

**Test Categories**:
- **Resource Existence**: CloudFormation stack, Lambda functions, DynamoDB tables, S3 buckets, EventBridge rules
- **IAM Permissions**: Verify Lambda execution roles and policies
- **Network Configuration**: API Gateway endpoints, CORS settings
- **Environment Variables**: Lambda function configurations

**Implementation**: Already covered in `scripts/test-serverless.sh` tests 1-15

### 2. Complete Subscription Flow (Enhanced)
**Objective**: Test the entire subscription process with comprehensive validation.

**Enhanced Steps**:
1. **Frontend Integration Test**:
   ```bash
   # Test static website accessibility (if deployed)
   WEBSITE_URL=$(get_stack_output "WebsiteURL")
   if [ -n "$WEBSITE_URL" ]; then
       curl -s -o /dev/null -w "%{http_code}" "$WEBSITE_URL" | grep -q "200"
   fi
   ```

2. **API Gateway CORS Validation**:
   ```bash
   # Test preflight OPTIONS request
   SUBSCRIPTION_URL=$(get_stack_output "SubscriptionEndpoint")
   curl -s -X OPTIONS "$SUBSCRIPTION_URL" \
       -H "Origin: https://example.com" \
       -H "Access-Control-Request-Method: POST" \
       -H "Access-Control-Request-Headers: Content-Type" \
       -w "%{http_code}" | grep -q "200"
   ```

3. **Subscription API Validation**:
   ```bash
   # Test various email formats and edge cases
   test_emails=(
       "valid@example.com"
       "test+tag@domain.co.uk"
       "user.name@subdomain.example.org"
   )
   
   for email in "${test_emails[@]}"; do
       test_subscription_with_email "$email"
   done
   ```

4. **DynamoDB Data Validation**:
   ```bash
   # Verify subscriber data structure and constraints
   verify_subscriber_data_integrity
   ```

5. **Error Handling Tests**:
   ```bash
   # Test malformed requests
   test_malformed_subscription_requests
   ```

### 3. Weekly Digest Generation (Comprehensive)
**Objective**: Test the complete digest generation pipeline with real and mock data.

**Enhanced Test Scenarios**:

#### 3.1 Dry Run Testing
```bash
# Test with minimal Twitter accounts to avoid rate limits
test_weekly_digest_dry_run() {
    local payload='{
        "source": "aws.events",
        "detail-type": "Scheduled Event",
        "dry_run": true,
        "test_mode": true,
        "max_accounts": 2
    }'
    
    echo "$payload" > /tmp/digest_payload.json
    
    # Use clean shell execution for reliable results
    zsh -d -f -c "aws lambda invoke \
        --function-name '${PROJECT_NAME}-weekly-digest-${ENVIRONMENT}' \
        --payload 'file:///tmp/digest_payload.json' \
        --region '$AWS_REGION' \
        /tmp/digest_response.json | cat"
    
    # Validate response structure
    validate_digest_response "/tmp/digest_response.json"
}
```

#### 3.2 Tweet Processing Validation
```bash
# Verify tweet categorization and summarization
validate_tweet_processing() {
    local digest_file="$1"
    
    # Check for required categories
    local required_categories=(
        "New AI model releases"
        "Breakthrough research findings"
        "Applications and case studies"
        "Ethical discussions and regulations"
        "Tools and resources"
    )
    
    for category in "${required_categories[@]}"; do
        if ! jq -e ".categories[] | select(.name == \"$category\")" "$digest_file" > /dev/null; then
            echo "Missing category: $category"
            return 1
        fi
    done
}
```

#### 3.3 Email Generation Testing
```bash
# Test HTML email template generation
test_email_template_generation() {
    # Verify HTML structure, unsubscribe links, responsive design
    local email_html=$(jq -r '.email_content.html' /tmp/digest_response.json)
    
    # Check for required elements
    echo "$email_html" | grep -q "unsubscribe" || return 1
    echo "$email_html" | grep -q "viewport" || return 1  # Mobile responsive
    echo "$email_html" | grep -q "GenAI Tweets Digest" || return 1
}
```

### 4. Data Integrity and Portability Tests
**Objective**: Ensure data can be safely exported, imported, and migrated.

**Enhanced Data Tests**:

#### 4.1 Comprehensive Data Export
```bash
# Export all system data with validation
comprehensive_data_export() {
    local backup_dir="./e2e_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Export subscribers with metadata
    aws dynamodb scan \
        --table-name "${SUBSCRIBERS_TABLE_NAME}" \
        --region "$AWS_REGION" \
        --output json > "$backup_dir/subscribers.json"
    
    # Export all digest files with timestamps
    aws s3 sync "s3://${DATA_BUCKET_NAME}/digests/" "$backup_dir/digests/"
    
    # Export configuration files
    aws s3 sync "s3://${DATA_BUCKET_NAME}/config/" "$backup_dir/config/"
    
    # Validate export completeness
    validate_export_completeness "$backup_dir"
}
```

#### 4.2 Data Validation
```bash
# Validate exported data integrity
validate_export_completeness() {
    local backup_dir="$1"
    
    # Check file existence and structure
    [ -f "$backup_dir/subscribers.json" ] || return 1
    [ -d "$backup_dir/digests" ] || return 1
    [ -d "$backup_dir/config" ] || return 1
    
    # Validate JSON structure
    jq empty "$backup_dir/subscribers.json" || return 1
    
    # Check for required configuration files
    [ -f "$backup_dir/config/accounts.json" ] || return 1
}
```

### 5. Error Handling and Recovery Tests
**Objective**: Verify system resilience under various failure conditions.

**Enhanced Error Scenarios**:

#### 5.1 API Rate Limiting Tests
```bash
# Test Twitter API rate limit handling
test_twitter_rate_limits() {
    # Simulate rate limit by making multiple rapid requests
    # This should be done carefully to avoid actual rate limiting
    echo "Testing rate limit handling (simulated)"
    
    # Test with invalid credentials
    test_with_invalid_twitter_credentials
}
```

#### 5.2 Lambda Timeout and Memory Tests
```bash
# Test Lambda function limits
test_lambda_limits() {
    # Test with large payload that might cause timeout
    local large_payload='{
        "source": "aws.events",
        "detail-type": "Scheduled Event",
        "test_mode": true,
        "simulate_large_dataset": true
    }'
    
    echo "$large_payload" > /tmp/large_payload.json
    
    # Monitor execution time and memory usage
    test_lambda_with_monitoring "${PROJECT_NAME}-weekly-digest-${ENVIRONMENT}" \
        "/tmp/large_payload.json"
}
```

#### 5.3 DynamoDB Throttling Tests
```bash
# Test DynamoDB throttling scenarios
test_dynamodb_throttling() {
    # Simulate high write volume
    for i in {1..50}; do
        aws dynamodb put-item \
            --table-name "${SUBSCRIBERS_TABLE_NAME}" \
            --item "{
                \"subscriber_id\": {\"S\": \"load-test-$i\"},
                \"email\": {\"S\": \"loadtest$i@example.com\"},
                \"status\": {\"S\": \"active\"},
                \"created_at\": {\"S\": \"$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)\"}
            }" \
            --region "$AWS_REGION" &
    done
    
    wait  # Wait for all background jobs
    
    # Cleanup
    cleanup_load_test_data
}
```

### 6. Performance and Scalability Tests
**Objective**: Verify system performance under realistic and stress conditions.

**Enhanced Performance Tests**:

#### 6.1 Concurrent Subscription Tests
```bash
# Test concurrent API Gateway requests
test_concurrent_subscriptions() {
    local concurrent_requests=20
    local pids=()
    
    for i in $(seq 1 $concurrent_requests); do
        {
            local test_email="concurrent-test-$i-$(date +%s)@example.com"
            curl -s -X POST "$SUBSCRIPTION_URL" \
                -H "Content-Type: application/json" \
                -d "{\"email\": \"$test_email\"}" \
                --max-time 30
        } &
        pids+=($!)
    done
    
    # Wait for all requests and check success rate
    local success_count=0
    for pid in "${pids[@]}"; do
        if wait "$pid"; then
            ((success_count++))
        fi
    done
    
    echo "Concurrent test: $success_count/$concurrent_requests successful"
    [ $success_count -ge $((concurrent_requests * 8 / 10)) ]  # 80% success rate
}
```

#### 6.2 Large Dataset Processing
```bash
# Test digest generation with large tweet volumes
test_large_dataset_processing() {
    # Configure test with many Twitter accounts
    local test_config='{
        "influential_accounts": [
            "OpenAI", "AndrewYNg", "ylecun", "karpathy",
            "elonmusk", "sundarpichai", "satyanadella",
            "jeffdean", "fchollet", "goodfellow_ian"
        ]
    }'
    
    # Upload test configuration
    echo "$test_config" > /tmp/test_accounts.json
    aws s3 cp /tmp/test_accounts.json "s3://${DATA_BUCKET_NAME}/config/accounts-test.json"
    
    # Run digest with test configuration
    test_digest_with_config "accounts-test.json"
}
```

### 7. Security and Compliance Tests
**Objective**: Verify security measures and compliance requirements.

#### 7.1 Data Privacy Tests
```bash
# Test GDPR compliance features
test_gdpr_compliance() {
    # Test data export for specific user
    test_user_data_export "test@example.com"
    
    # Test data deletion
    test_user_data_deletion "test@example.com"
    
    # Verify data is actually removed
    verify_user_data_removal "test@example.com"
}
```

#### 7.2 Input Validation Tests
```bash
# Test various malicious inputs
test_input_validation() {
    local malicious_inputs=(
        '{"email": "<script>alert(1)</script>@example.com"}'
        '{"email": "test@example.com\"; DROP TABLE subscribers; --"}'
        '{"email": "' + 'A' * 1000 + '@example.com"}'  # Very long email
    )
    
    for input in "${malicious_inputs[@]}"; do
        test_malicious_input "$input"
    done
}
```

## Automated E2E Test Script (Enhanced)

Create `scripts/e2e-test.sh` that builds upon the existing `test-serverless.sh`:

```bash
#!/bin/bash
set -e

# Enhanced E2E Testing Script
# Builds upon the comprehensive test-serverless.sh

# Source the existing test functions
source "$(dirname "$0")/test-serverless.sh"

# Additional E2E specific functions
source "$(dirname "$0")/e2e-functions.sh"

# Configuration
E2E_TEST_EMAIL_PREFIX="e2e-test-$(date +%s)"
E2E_CLEANUP_ENABLED="${E2E_CLEANUP_ENABLED:-true}"

echo -e "${BLUE}🚀 Starting Enhanced E2E Testing Suite${NC}"

# Run infrastructure tests first
echo -e "${BLUE}📋 Infrastructure Validation${NC}"
run_infrastructure_tests

# Run functional tests
echo -e "${BLUE}⚙️ Functional Testing${NC}"
run_functional_tests

# Run integration tests
echo -e "${BLUE}🔄 Integration Testing${NC}"
run_integration_tests

# Run performance tests
echo -e "${BLUE}⚡ Performance Testing${NC}"
run_performance_tests

# Run security tests
echo -e "${BLUE}🔒 Security Testing${NC}"
run_security_tests

# Generate comprehensive report
generate_e2e_report

echo -e "${GREEN}🎉 E2E Testing Complete!${NC}"
```

## Test Data Management (Enhanced)

### Dynamic Test Data Generation
```bash
# Generate realistic test data
generate_test_data() {
    local num_subscribers="${1:-100}"
    
    for i in $(seq 1 $num_subscribers); do
        local email="test-user-$i@domain-$((i % 10)).com"
        add_test_subscriber "$email"
    done
}
```

### Test Environment Isolation
```bash
# Ensure test isolation
setup_test_environment() {
    # Create test-specific resources if needed
    # Use test-specific prefixes for all operations
    export TEST_PREFIX="e2e-test-$(date +%s)"
}
```

## Monitoring and Observability (Enhanced)

### Real-time Test Monitoring
```bash
# Monitor CloudWatch metrics during tests
monitor_test_execution() {
    local test_name="$1"
    local start_time=$(date -u +%Y-%m-%dT%H:%M:%S)
    
    # Start CloudWatch monitoring
    monitor_cloudwatch_metrics "$start_time" &
    local monitor_pid=$!
    
    # Run the test
    run_test "$test_name"
    
    # Stop monitoring
    kill $monitor_pid 2>/dev/null || true
}
```

### Custom Metrics Collection
```bash
# Collect custom performance metrics
collect_performance_metrics() {
    local metrics_file="/tmp/e2e-metrics-$(date +%s).json"
    
    {
        echo "{"
        echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)\","
        echo "  \"lambda_cold_starts\": $(get_lambda_cold_start_metrics),"
        echo "  \"api_response_times\": $(get_api_response_times),"
        echo "  \"dynamodb_throttles\": $(get_dynamodb_throttle_count),"
        echo "  \"s3_operations\": $(get_s3_operation_metrics)"
        echo "}"
    } > "$metrics_file"
    
    echo "Metrics saved to: $metrics_file"
}
```

## Success Criteria (Enhanced)

### Functional Requirements
- ✅ All infrastructure components deployed correctly
- ✅ Subscription form works with various email formats
- ✅ Emails are stored in DynamoDB with proper validation
- ✅ Weekly digest generates successfully with real data
- ✅ Emails are delivered to subscribers with proper formatting
- ✅ Unsubscribe functionality works correctly
- ✅ Data can be exported/imported without loss
- ✅ Error handling works for all failure scenarios
- ✅ Security measures prevent malicious inputs

### Performance Requirements
- ✅ Digest generation completes within 15 minutes for 100+ accounts
- ✅ API responses under 3 seconds (95th percentile)
- ✅ Website loads within 2 seconds
- ✅ Lambda cold starts under 5 seconds
- ✅ System handles 100+ concurrent subscription requests
- ✅ DynamoDB operations complete within 100ms (average)

### Reliability Requirements
- ✅ System handles API failures gracefully with retries
- ✅ No data loss during any error scenarios
- ✅ Automatic retry mechanisms work correctly
- ✅ Error notifications are sent to administrators
- ✅ System recovers automatically from transient failures
- ✅ 99.9% uptime during testing period

### Security Requirements
- ✅ Input validation prevents injection attacks
- ✅ GDPR compliance features work correctly
- ✅ API keys are properly secured and not exposed
- ✅ IAM permissions follow least privilege principle
- ✅ Data encryption at rest and in transit

## Continuous Integration Integration

### GitHub Actions Workflow
```yaml
name: E2E Testing
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'  # Weekly on Monday

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Run E2E Tests
        env:
          TWITTER_BEARER_TOKEN: ${{ secrets.TWITTER_BEARER_TOKEN }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: |
          chmod +x scripts/e2e-test.sh
          ./scripts/e2e-test.sh
      
      - name: Upload Test Results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: e2e-test-results
          path: /tmp/e2e-*.json
```

## Rollback and Recovery Plan (Enhanced)

### Automated Rollback
```bash
# Automated rollback on test failures
rollback_on_failure() {
    local exit_code=$1
    
    if [ $exit_code -ne 0 ]; then
        echo -e "${RED}Tests failed, initiating rollback...${NC}"
        
        # Restore previous stack version if available
        restore_previous_stack_version
        
        # Clean up test data
        cleanup_test_data
        
        # Send failure notifications
        send_failure_notification
    fi
}
```

### Recovery Validation
```bash
# Validate system recovery
validate_recovery() {
    # Run basic health checks
    run_health_checks
    
    # Verify data integrity
    verify_data_integrity
    
    # Test critical paths
    test_critical_user_journeys
}
```

## Conclusion

This enhanced E2E testing plan provides comprehensive coverage of the GenAI Tweets Digest serverless system, incorporating:

1. **Robust Infrastructure Testing**: Building on the existing comprehensive test suite
2. **AWS CLI Best Practices**: Clean shell execution, proper error handling, file-based payloads
3. **Advanced Scenarios**: Performance, security, and compliance testing
4. **Real-world Simulation**: Concurrent users, large datasets, failure scenarios
5. **Continuous Monitoring**: Real-time metrics and observability
6. **Automated Recovery**: Rollback and recovery procedures

Regular execution of these tests ensures system reliability, performance, and security while catching issues early in the development cycle. The modular design allows for selective test execution based on deployment scope and risk assessment. 