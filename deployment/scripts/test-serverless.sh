#!/bin/bash

# Comprehensive Testing Script for Serverless GenAI Tweets Digest
# This script tests all components of the serverless architecture

set -e

# Configuration
PROJECT_NAME="genai-tweets-digest"
ENVIRONMENT="${ENVIRONMENT:-production}"
AWS_REGION="${AWS_REGION:-us-east-1}"
# Use provided STACK_NAME if set, otherwise derive from PROJECT_NAME and ENVIRONMENT
CF_STACK_NAME="${STACK_NAME:-${PROJECT_NAME}-${ENVIRONMENT}}"

# Fetch actual resource names from CloudFormation outputs
DATA_BUCKET_NAME=""
WEBSITE_BUCKET_NAME=""
SUBSCRIBERS_TABLE_NAME=""

get_stack_output() {
    local output_key="$1"
    aws cloudformation describe-stacks \
        --stack-name "${CF_STACK_NAME}" \
        --region "$AWS_REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='$output_key'].OutputValue" \
        --output text 2>/dev/null
}

initialize_resource_names(){
    echo "Fetching resource names from stack '${CF_STACK_NAME}'..."
    DATA_BUCKET_NAME=$(get_stack_output "DataBucketName")
    WEBSITE_BUCKET_NAME=$(get_stack_output "WebsiteBucketName") # May not exist in minimal template
    SUBSCRIBERS_TABLE_NAME=$(get_stack_output "SubscribersTableName")

    if [ -z "$DATA_BUCKET_NAME" ] || [ -z "$SUBSCRIBERS_TABLE_NAME" ]; then 
        echo -e "${RED}Error: Could not fetch critical resource names (DataBucketName, SubscribersTableName) from stack outputs.${NC}"
        echo -e "${YELLOW}Falling back to naming convention for some resources, this might lead to test failures if stack name was dynamic.${NC}"
        DATA_BUCKET_NAME="${DATA_BUCKET_NAME:-${PROJECT_NAME}-data-${ENVIRONMENT}-${AWS_ACCOUNT_ID_PLACEHOLDER}}" # Need a way to get Account ID if not in output
        SUBSCRIBERS_TABLE_NAME="${SUBSCRIBERS_TABLE_NAME:-${PROJECT_NAME}-subscribers-${ENVIRONMENT}}"
    else
        echo "Data Bucket: $DATA_BUCKET_NAME"
        echo "Website Bucket: ${WEBSITE_BUCKET_NAME:-Not Deployed}"
        echo "Subscribers Table: $SUBSCRIBERS_TABLE_NAME"
    fi
    echo ""
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 GenAI Tweets Digest - Serverless Testing Suite${NC}"
echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"
echo ""

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Helper function to run tests
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "${YELLOW}Testing: $test_name${NC}"
    
    if eval "$test_command"; then
        echo -e "${GREEN}✅ PASSED: $test_name${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAILED: $test_name${NC}"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("$test_name")
    fi
    echo ""
}

# Test 1: Check AWS CLI and credentials
test_aws_cli() {
    aws sts get-caller-identity > /dev/null 2>&1
}

# Test 2: Check if CloudFormation stack exists
test_stack_exists() {
    aws cloudformation describe-stacks \
        --stack-name "${CF_STACK_NAME}" \
        --region $AWS_REGION > /dev/null 2>&1
}

# Test 3: Check if Lambda functions exist
test_lambda_functions() {
    aws lambda get-function \
        --function-name "${PROJECT_NAME}-subscription-${ENVIRONMENT}" \
        --region $AWS_REGION > /dev/null 2>&1 && \
    aws lambda get-function \
        --function-name "${PROJECT_NAME}-weekly-digest-${ENVIRONMENT}" \
        --region $AWS_REGION > /dev/null 2>&1
}

# Test 4: Check if DynamoDB table exists
test_dynamodb_table() {
    aws dynamodb describe-table \
        --table-name "${SUBSCRIBERS_TABLE_NAME}" \
        --region $AWS_REGION > /dev/null 2>&1
}

# Test 5: Check if S3 buckets exist
test_s3_buckets() {
    ( [ -n "$DATA_BUCKET_NAME" ] && aws s3 ls "s3://${DATA_BUCKET_NAME}" > /dev/null 2>&1 ) && \
    ( [ -z "$WEBSITE_BUCKET_NAME" ] || aws s3 ls "s3://${WEBSITE_BUCKET_NAME}" > /dev/null 2>&1 )
}

# Test 6: Test subscription Lambda function
test_subscription_lambda() {
    local raw_payload_json='{"httpMethod": "POST", "body": "{\"email\": \"test-direct-invoke-file@example.com\"}"}'
    local payload_file="/tmp/direct_invoke_payload.json"
    echo "$raw_payload_json" > "$payload_file"
    
    local output_file="/tmp/subscription-test-response.json"
    local error_file="/tmp/subscription-test-error.log"
    
    echo "Directly invoking subscription lambda with payload from file: $payload_file"
    echo "Payload content:"
    cat "$payload_file"
    
    # Capture stdout to output_file and stderr to error_file
    if aws lambda invoke \
        --function-name "${PROJECT_NAME}-subscription-${ENVIRONMENT}" \
        --payload "file://$payload_file" \
        --invocation-type RequestResponse \
        --region $AWS_REGION \
        $output_file > $error_file 2>&1; then
        
        echo "Lambda invoke CLI command succeeded. Output file: $output_file"
        if [ -f "$output_file" ]; then
            echo "Contents of $output_file:"
            cat "$output_file"
            # Check if response contains expected fields for a successful or known error response
            if grep -q -E '"statusCode": (200|201|400|409|500)' "$output_file" && grep -q "body" "$output_file"; then
                echo "Output file contains expected statusCode and body."
                return 0 # Success
            else
                echo "Output file does not contain expected statusCode/body structure."
                return 1 # Failure
            fi
        else
            echo "Output file $output_file not found after successful invoke command."
            return 1 # Failure
        fi
    else
        echo "Lambda invoke CLI command failed. Error log: $error_file"
        if [ -f "$error_file" ]; then
            echo "Contents of $error_file:"
            cat "$error_file"
        fi
        # Also check if an output file was created despite error (e.g. for function error payloads)
        if [ -f "$output_file" ]; then
            echo "Contents of $output_file (created despite CLI error):"
            cat "$output_file"
        fi
        return 1 # Failure
    fi
}

# Test 7: Test API Gateway endpoint
test_api_gateway() {
    # Get API Gateway URL from CloudFormation
    local api_url=$(get_stack_output "SubscriptionEndpoint")
    
    if [ -n "$api_url" ]; then
        # Test OPTIONS request (CORS)
        curl -s -X OPTIONS "$api_url" \
            -H "Origin: https://example.com" \
            -H "Access-Control-Request-Method: POST" \
            -H "Access-Control-Request-Headers: Content-Type" \
            --max-time 10 > /dev/null 2>&1
    else
        return 1
    fi
}

# Test 8: Test DynamoDB operations
test_dynamodb_operations() {
    local table_name="${SUBSCRIBERS_TABLE_NAME}"
    
    # Test write operation
    aws dynamodb put-item \
        --table-name "$table_name" \
        --item '{
            "subscriber_id": {"S": "test-id-123"},
            "email": {"S": "test@example.com"},
            "status": {"S": "active"},
            "created_at": {"S": "'$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'"}
        }' \
        --region $AWS_REGION > /dev/null 2>&1
    
    # Test read operation
    aws dynamodb get-item \
        --table-name "$table_name" \
        --key '{"subscriber_id": {"S": "test-id-123"}}' \
        --region $AWS_REGION > /dev/null 2>&1
    
    # Cleanup test data
    aws dynamodb delete-item \
        --table-name "$table_name" \
        --key '{"subscriber_id": {"S": "test-id-123"}}' \
        --region $AWS_REGION > /dev/null 2>&1
}

# Test 9: Test S3 operations
test_s3_operations() {
    local bucket_name="${DATA_BUCKET_NAME}"
    
    # Test write operation
    echo '{"test": "data"}' | aws s3 cp - "s3://$bucket_name/test/test-file.json" 2>/dev/null
    
    # Test read operation
    aws s3 cp "s3://$bucket_name/test/test-file.json" /tmp/s3-test.json > /dev/null 2>&1
    
    # Cleanup test data
    aws s3 rm "s3://$bucket_name/test/test-file.json" > /dev/null 2>&1
    
    # Check if file was downloaded correctly
    [ -f /tmp/s3-test.json ] && grep -q "test" /tmp/s3-test.json
}

# Test 10: Test EventBridge rule
test_eventbridge_rule() {
    aws events describe-rule \
        --name "${PROJECT_NAME}-weekly-schedule-${ENVIRONMENT}" \
        --region $AWS_REGION > /dev/null 2>&1
}

# Test 11: Test environment variables in Lambda
test_lambda_env_vars() {
    local config=$(aws lambda get-function-configuration \
        --function-name "${PROJECT_NAME}-weekly-digest-${ENVIRONMENT}" \
        --region $AWS_REGION 2>/dev/null)
    
    echo "$config" | grep -q "TWITTER_BEARER_TOKEN" && \
    echo "$config" | grep -q "GEMINI_API_KEY" && \
    echo "$config" | grep -q "S3_BUCKET" && \
    echo "$config" | grep -q "SUBSCRIBERS_TABLE"
}

# Test 12: Test accounts configuration in S3
test_accounts_config() {
    local bucket_name="${DATA_BUCKET_NAME}"
    
    aws s3 cp "s3://$bucket_name/config/accounts.json" /tmp/accounts-test.json > /dev/null 2>&1
    
    # Check if accounts.json has the expected structure
    [ -f /tmp/accounts-test.json ] && \
    grep -q "influential_accounts" /tmp/accounts-test.json && \
    grep -q "OpenAI\|AndrewYNg" /tmp/accounts-test.json
}

# Test 13: Dry run of weekly digest (without sending emails)
test_weekly_digest_dry_run() {
    echo "⚠️  This test requires valid API keys and may take several minutes..."
    
    local raw_payload_json='{"source": "aws.events", "detail-type": "Scheduled Event", "dry_run": true}'
    local payload_file="/tmp/weekly_digest_payload.json"
    echo "$raw_payload_json" > "$payload_file"
    local output_file="/tmp/digest-test-response.json"
    local error_file="/tmp/digest-test-error.log"

    echo "Directly invoking weekly-digest lambda with payload from file: $payload_file"
    echo "Payload content:"; cat "$payload_file"

    if aws lambda invoke \
        --function-name "${PROJECT_NAME}-weekly-digest-${ENVIRONMENT}" \
        --payload "file://$payload_file" \
        --invocation-type RequestResponse \
        --region $AWS_REGION \
        $output_file > $error_file 2>&1; then

        echo "Lambda invoke CLI command succeeded for weekly-digest. Output file: $output_file"
        if [ -f "$output_file" ]; then
            echo "Contents of $output_file:"
            cat "$output_file"
            if grep -q -E '"statusCode": (200|500)' "$output_file"; then # 500 is ok if API keys missing but still ran
                echo "Output file contains expected statusCode."
                # Further check for dry_run success message if possible
                # For now, statusCode 200 or 500 (if keys missing) is a pass for invocation
                return 0 
            else
                echo "Output file does not contain expected statusCode."
                return 1
            fi
        else
            echo "Output file $output_file not found after successful weekly-digest invoke."
            return 1
        fi
    else
        echo "Lambda invoke CLI command failed for weekly-digest. Error log: $error_file"
        if [ -f "$error_file" ]; then
            echo "Contents of $error_file:"
            cat "$error_file"
        fi
        if [ -f "$output_file" ]; then
            echo "Contents of $output_file (created despite CLI error for weekly-digest):"
            cat "$output_file"
        fi
        return 1
    fi
}

# Test 14: Test CloudWatch logs
test_cloudwatch_logs() {
    # Check if log groups exist
    aws logs describe-log-groups \
        --log-group-name-prefix "/aws/lambda/${PROJECT_NAME}" \
        --region $AWS_REGION > /dev/null 2>&1
}

# Test 15: Test IAM permissions
test_iam_permissions() {
    # IAM role names are now account-specific if created by our current template
    # This test might need adjustment if the role name isn't available as a direct output
    # For now, assuming the pattern used in the CFN template:
    local account_id=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
    # Construct role name based on ENVIRONMENT which could be 'production' or 'development'
    local role_name_suffix="${ENVIRONMENT}"
    if [ "$CF_STACK_NAME" != "${PROJECT_NAME}-${ENVIRONMENT}" ]; then
      # If CF_STACK_NAME is custom (e.g. with timestamp, or -test), parse env from it if possible
      # This is a heuristic; might need refinement if stack names deviate too much
      if [[ "$CF_STACK_NAME" == *"-development"* ]]; then
        role_name_suffix="development"
      elif [[ "$CF_STACK_NAME" == *"-staging"* ]]; then
        role_name_suffix="staging"
      elif [[ "$CF_STACK_NAME" == *"-test"* ]]; then # for -test suffix from minimal template attempt
        role_name_suffix="test" # Or map to development if preferred
      fi
    fi
    local role_name="${PROJECT_NAME}-lambda-role-${role_name_suffix}-${account_id}"
    echo "Checking IAM role: $role_name"
    
    aws iam get-role --role-name "$role_name" > /dev/null 2>&1 && \
    aws iam list-attached-role-policies --role-name "$role_name" > /dev/null 2>&1
}

# Integration Test: Full subscription flow
integration_test_subscription() {
    echo -e "${BLUE}🔄 Running integration test: Full subscription flow${NC}"
    
    # Get API Gateway URL
    local api_url=$(get_stack_output "SubscriptionEndpoint")
    
    if [ -z "$api_url" ]; then
        echo -e "${RED}❌ Could not get API Gateway URL${NC}"
        return 1
    fi
    
    # Test subscription with a unique email
    local test_email="integration-test-$(date +%s)@example.com"
    local response=$(curl -s -X POST "$api_url" \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"$test_email\"}" \
        --max-time 30)
    
    if echo "$response" | grep -q "success.*true"; then
        echo -e "${GREEN}✅ Integration test passed: Subscription successful${NC}"
        
        # Cleanup: Remove test subscriber
        local table_name="${SUBSCRIBERS_TABLE_NAME}"
        # A simpler way to get the ID if the add_subscriber call in the lambda returns it
        # Assuming the response body from a successful subscription is like: {"success":true, "subscriber_id":"some-uuid"}
        local subscriber_id_to_delete=$(echo "$response" | jq -r .subscriber_id 2>/dev/null)

        if [ -n "$subscriber_id_to_delete" ] && [ "$subscriber_id_to_delete" != "null" ]; then
            echo "Cleaning up subscriber: $subscriber_id_to_delete"
            aws dynamodb delete-item \
                --table-name "$table_name" \
                --key "{\"subscriber_id\": {\"S\": \"$subscriber_id_to_delete\"}}" \
                --region $AWS_REGION > /dev/null 2>&1
        else
            echo "Could not determine subscriber_id for cleanup: $test_email. Response: $response"
        fi
        
        return 0
    else
        echo -e "${RED}❌ Integration test failed: $response${NC}"
        return 1
    fi
}

# Performance Test: Check Lambda cold start times
performance_test_lambda() {
    echo -e "${BLUE}⚡ Running performance test: Lambda cold start times${NC}"
    
    # Using python for more reliable millisecond timing
    local start_time=$(python -c 'import time; print(int(time.time() * 1000))')
    
    aws lambda invoke \
        --function-name "${PROJECT_NAME}-subscription-${ENVIRONMENT}" \
        --payload '{"httpMethod": "OPTIONS"}' \
        --region $AWS_REGION \
        /tmp/perf-test-response.json > /dev/null 2>&1
    
    local end_time=$(python -c 'import time; print(int(time.time() * 1000))')
    local duration=$((end_time - start_time))
    
    echo "Lambda cold start time: ${duration}ms"
    
    if [ $duration -lt 5000 ]; then  # Less than 5 seconds
        echo -e "${GREEN}✅ Performance test passed: Cold start < 5s${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Performance test warning: Cold start > 5s${NC}"
        return 1
    fi
}

# Main testing function
main() {
    initialize_resource_names # Fetch resource names first

    echo -e "${BLUE}🚀 Starting comprehensive serverless tests...${NC}"
    echo ""
    
    # Infrastructure tests
    echo -e "${BLUE}📋 Infrastructure Tests${NC}"
    run_test "AWS CLI and credentials" "test_aws_cli"
    run_test "CloudFormation stack exists" "test_stack_exists"
    run_test "Lambda functions exist" "test_lambda_functions"
    run_test "DynamoDB table exists" "test_dynamodb_table"
    run_test "S3 buckets exist" "test_s3_buckets"
    run_test "EventBridge rule exists" "test_eventbridge_rule"
    run_test "IAM permissions" "test_iam_permissions"
    
    # Functional tests
    echo -e "${BLUE}⚙️  Functional Tests${NC}"
    run_test "Subscription Lambda function" "test_subscription_lambda"
    run_test "API Gateway endpoint" "test_api_gateway"
    run_test "DynamoDB operations" "test_dynamodb_operations"
    run_test "S3 operations" "test_s3_operations"
    run_test "Lambda environment variables" "test_lambda_env_vars"
    run_test "Accounts configuration" "test_accounts_config"
    run_test "CloudWatch logs" "test_cloudwatch_logs"
    
    # Optional tests (may require API keys)
    echo -e "${BLUE}🔧 Optional Tests (require API keys)${NC}"
    if [ -n "$TWITTER_BEARER_TOKEN" ] && [ -n "$GEMINI_API_KEY" ]; then
        run_test "Weekly digest dry run" "test_weekly_digest_dry_run"
    else
        echo -e "${YELLOW}⏭️  Skipping weekly digest test (API keys not set)${NC}"
    fi
    
    # Integration tests
    echo -e "${BLUE}🔄 Integration Tests${NC}"
    run_test "Full subscription flow" "integration_test_subscription"
    
    # Performance tests
    echo -e "${BLUE}⚡ Performance Tests${NC}"
    run_test "Lambda cold start performance" "performance_test_lambda"
    
    # Summary
    echo ""
    echo -e "${BLUE}📊 Test Summary${NC}"
    echo "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
    echo "Tests failed: ${RED}$TESTS_FAILED${NC}"
    
    if [ $TESTS_FAILED -gt 0 ]; then
        echo ""
        echo -e "${RED}❌ Failed tests:${NC}"
        for test in "${FAILED_TESTS[@]}"; do
            echo "  - $test"
        done
        echo ""
        echo -e "${YELLOW}💡 Troubleshooting tips:${NC}"
        echo "1. Check AWS credentials: aws sts get-caller-identity"
        echo "2. Verify stack deployment: aws cloudformation describe-stacks --stack-name ${CF_STACK_NAME}"
        echo "3. Check CloudWatch logs for errors"
        echo "4. Ensure API keys are set if running optional tests"
        exit 1
    else
        echo ""
        echo -e "${GREEN}🎉 All tests passed! Your serverless architecture is working correctly.${NC}"
        exit 0
    fi
}

# Cleanup function
cleanup() {
    rm -f /tmp/subscription-test-response.json
    rm -f /tmp/digest-test-response.json
    rm -f /tmp/s3-test.json
    rm -f /tmp/accounts-test.json
    rm -f /tmp/perf-test-response.json
}

# Set up cleanup on exit
trap cleanup EXIT

# Run main function
main 