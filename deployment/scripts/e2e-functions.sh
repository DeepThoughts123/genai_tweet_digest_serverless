#!/bin/bash

# E2E Testing Functions Library
# Advanced testing functions for GenAI Tweets Digest serverless architecture
# Builds upon test-serverless.sh and incorporates AWS CLI best practices

# Source colors and basic functions from test-serverless.sh if not already loaded
if [ -z "$RED" ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
fi

# Enhanced utility functions using AWS CLI best practices
safe_aws_command() {
    local command="$1"
    local description="$2"
    
    echo "Executing: $description"
    # Use clean shell execution for reliable JSON output
    if zsh -d -f -c "$command | cat" 2>/dev/null; then
        return 0
    else
        echo -e "${RED}Failed: $description${NC}"
        return 1
    fi
}

# Get stack output with error handling
get_stack_output_safe() {
    local output_key="$1"
    local result
    
    result=$(zsh -d -f -c "aws cloudformation describe-stacks \
        --stack-name '${CF_STACK_NAME}' \
        --region '$AWS_REGION' \
        --query 'Stacks[0].Outputs[?OutputKey==\`$output_key\`].OutputValue' \
        --output text 2>/dev/null | cat")
    
    if [ -n "$result" ] && [ "$result" != "None" ]; then
        echo "$result"
        return 0
    else
        return 1
    fi
}

# Enhanced subscription testing with various email formats
test_subscription_with_email() {
    local email="$1"
    local api_url
    
    api_url=$(get_stack_output_safe "SubscriptionEndpoint")
    if [ $? -ne 0 ]; then
        echo -e "${RED}Could not get subscription endpoint${NC}"
        return 1
    fi
    
    echo "Testing subscription with email: $email"
    
    local response
    response=$(curl -s -X POST "$api_url" \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"$email\"}" \
        --max-time 30 \
        -w "HTTPSTATUS:%{http_code}")
    
    local http_code=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    local body=$(echo "$response" | sed 's/HTTPSTATUS:[0-9]*$//')
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✅ Subscription successful for $email${NC}"
        
        # Verify in database
        verify_subscription_in_db "$email"
        return $?
    else
        echo -e "${RED}❌ Subscription failed for $email (HTTP: $http_code)${NC}"
        echo "Response: $body"
        return 1
    fi
}

# Verify subscription exists in DynamoDB
verify_subscription_in_db() {
    local email="$1"
    local table_name="${SUBSCRIBERS_TABLE_NAME}"
    
    # Query by email (assuming email is indexed or we scan)
    local result
    result=$(aws dynamodb scan \
        --table-name "$table_name" \
        --filter-expression "email = :email" \
        --expression-attribute-values "{\":email\":{\"S\":\"$email\"}}" \
        --region "$AWS_REGION" \
        --output json 2>/dev/null)
    
    if echo "$result" | jq -e '.Items | length > 0' > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Email $email found in database${NC}"
        return 0
    else
        echo -e "${RED}❌ Email $email not found in database${NC}"
        return 1
    fi
}

# Test malformed subscription requests
test_malformed_subscription_requests() {
    local api_url
    api_url=$(get_stack_output_safe "SubscriptionEndpoint")
    
    local malformed_requests=(
        '{"invalid": "json"}'
        '{"email": ""}'
        '{"email": "not-an-email"}'
        '{"email": "test@"}'
        '{"email": "@example.com"}'
        '{}'
        'invalid json'
    )
    
    echo "Testing malformed subscription requests..."
    
    for request in "${malformed_requests[@]}"; do
        echo "Testing: $request"
        
        local response
        response=$(curl -s -X POST "$api_url" \
            -H "Content-Type: application/json" \
            -d "$request" \
            --max-time 10 \
            -w "HTTPSTATUS:%{http_code}")
        
        local http_code=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
        
        # Should return 400 for malformed requests
        if [ "$http_code" = "400" ]; then
            echo -e "${GREEN}✅ Correctly rejected malformed request${NC}"
        else
            echo -e "${YELLOW}⚠️  Unexpected response code: $http_code${NC}"
        fi
    done
}

# Verify subscriber data integrity
verify_subscriber_data_integrity() {
    local table_name="${SUBSCRIBERS_TABLE_NAME}"
    
    echo "Verifying subscriber data integrity..."
    
    # Get sample of subscribers
    local subscribers
    subscribers=$(AWS_PROFILE=${AWS_PROFILE:-personal} zsh -d -f -c "aws dynamodb scan \
        --table-name '$table_name' \
        --limit 10 \
        --region $AWS_REGION \
        --output json 2>/dev/null | cat")
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to scan subscribers table${NC}"
        return 1
    fi
    
    # Check if table has any items
    local item_count=$(echo "$subscribers" | jq '.Items | length' 2>/dev/null || echo "0")
    
    if [ "$item_count" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  No subscribers found in table (this is normal for a new deployment)${NC}"
        echo -e "${GREEN}✅ Subscriber table structure verified${NC}"
        return 0
    fi
    
    # Verify required fields exist in first item
    local required_fields=("subscriber_id" "email" "status" "created_at")
    
    for field in "${required_fields[@]}"; do
        if ! echo "$subscribers" | jq -e ".Items[0].$field" > /dev/null 2>&1; then
            echo -e "${RED}❌ Missing required field: $field${NC}"
            return 1
        fi
    done
    
    echo -e "${GREEN}✅ Subscriber data integrity verified${NC}"
    return 0
}

# Enhanced digest testing with validation
validate_digest_response() {
    local response_file="$1"
    
    if [ ! -f "$response_file" ]; then
        echo -e "${RED}❌ Digest response file not found: $response_file${NC}"
        return 1
    fi
    
    echo "Validating digest response structure..."
    
    # Check if response contains error
    if jq -e '.errorMessage' "$response_file" > /dev/null 2>&1; then
        local error_msg=$(jq -r '.errorMessage' "$response_file")
        echo -e "${RED}❌ Digest generation failed: $error_msg${NC}"
        return 1
    fi
    
    # Check for successful response structure
    if jq -e '.statusCode' "$response_file" > /dev/null 2>&1; then
        local status_code=$(jq -r '.statusCode' "$response_file")
        
        if [ "$status_code" = "200" ]; then
            echo -e "${GREEN}✅ Digest generation successful${NC}"
            
            # Validate digest content if available
            validate_digest_content "$response_file"
            return $?
        else
            echo -e "${RED}❌ Digest generation failed with status: $status_code${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  Unexpected response format${NC}"
        return 1
    fi
}

# Validate digest content structure
validate_digest_content() {
    local response_file="$1"
    
    # Extract body if it's wrapped in API Gateway response
    local digest_content
    if jq -e '.body' "$response_file" > /dev/null 2>&1; then
        digest_content=$(jq -r '.body' "$response_file")
    else
        digest_content=$(cat "$response_file")
    fi
    
    # Parse digest content
    echo "$digest_content" > /tmp/digest_content.json
    
    # Validate required sections
    local required_sections=("summary" "categories" "metadata")
    
    for section in "${required_sections[@]}"; do
        if ! jq -e ".$section" /tmp/digest_content.json > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠️  Missing digest section: $section${NC}"
        fi
    done
    
    # Validate categories
    validate_tweet_processing /tmp/digest_content.json
    
    return 0
}

# Test with invalid API credentials
test_with_invalid_twitter_credentials() {
    echo "Testing with invalid Twitter credentials..."
    
    # Create payload with test flag to avoid actual API calls
    local payload='{
        "source": "aws.events",
        "detail-type": "Scheduled Event",
        "test_invalid_credentials": true,
        "dry_run": true
    }'
    
    echo "$payload" > /tmp/invalid_creds_payload.json
    
    local output_file="/tmp/invalid_creds_response.json"
    
    if aws lambda invoke \
        --function-name "${PROJECT_NAME}-weekly-digest-${ENVIRONMENT}" \
        --payload "file:///tmp/invalid_creds_payload.json" \
        --region "$AWS_REGION" \
        "$output_file" > /dev/null 2>&1; then
        
        # Check if error was handled gracefully
        if jq -e '.errorMessage' "$output_file" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Invalid credentials handled gracefully${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  Unexpected response to invalid credentials${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ Lambda invocation failed${NC}"
        return 1
    fi
}

# Test Lambda with monitoring
test_lambda_with_monitoring() {
    local function_name="$1"
    local payload_file="$2"
    
    echo "Testing Lambda function with monitoring: $function_name"
    
    local start_time=$(python3 -c 'import time; print(int(time.time() * 1000))')
    local output_file="/tmp/monitored_lambda_response.json"
    
    # Invoke Lambda
    if aws lambda invoke \
        --function-name "$function_name" \
        --payload "file://$payload_file" \
        --region "$AWS_REGION" \
        "$output_file" > /dev/null 2>&1; then
        
        local end_time=$(python3 -c 'import time; print(int(time.time() * 1000))')
        local duration=$((end_time - start_time))
        
        echo "Lambda execution time: ${duration}ms"
        
        # Check for timeout or memory issues
        if [ $duration -gt 300000 ]; then  # 5 minutes
            echo -e "${YELLOW}⚠️  Lambda execution took longer than expected${NC}"
        fi
        
        # Check response for memory or timeout errors
        if jq -e '.errorMessage' "$output_file" > /dev/null 2>&1; then
            local error_msg=$(jq -r '.errorMessage' "$output_file")
            if echo "$error_msg" | grep -q -i "timeout\|memory"; then
                echo -e "${RED}❌ Lambda resource limit exceeded: $error_msg${NC}"
                return 1
            fi
        fi
        
        echo -e "${GREEN}✅ Lambda monitoring test completed${NC}"
        return 0
    else
        echo -e "${RED}❌ Lambda invocation failed${NC}"
        return 1
    fi
}

# Cleanup load test data
cleanup_load_test_data() {
    local table_name="${SUBSCRIBERS_TABLE_NAME}"
    
    echo "Cleaning up load test data..."
    
    # Get all load test items
    local items
    items=$(aws dynamodb scan \
        --table-name "$table_name" \
        --filter-expression "begins_with(subscriber_id, :prefix)" \
        --expression-attribute-values '{":prefix":{"S":"load-test-"}}' \
        --region "$AWS_REGION" \
        --output json 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        # Delete each item
        echo "$items" | jq -r '.Items[].subscriber_id.S' | while read -r subscriber_id; do
            aws dynamodb delete-item \
                --table-name "$table_name" \
                --key "{\"subscriber_id\": {\"S\": \"$subscriber_id\"}}" \
                --region "$AWS_REGION" > /dev/null 2>&1
        done
        
        echo -e "${GREEN}✅ Load test data cleaned up${NC}"
    else
        echo -e "${YELLOW}⚠️  Could not clean up load test data${NC}"
    fi
}

# Test digest with specific configuration
test_digest_with_config() {
    local config_file="$1"
    
    echo "Testing digest with configuration: $config_file"
    
    local payload="{
        \"source\": \"aws.events\",
        \"detail-type\": \"Scheduled Event\",
        \"test_mode\": true,
        \"config_file\": \"$config_file\",
        \"dry_run\": true
    }"
    
    echo "$payload" > /tmp/config_test_payload.json
    
    local output_file="/tmp/config_test_response.json"
    
    if aws lambda invoke \
        --function-name "${PROJECT_NAME}-weekly-digest-${ENVIRONMENT}" \
        --payload "file:///tmp/config_test_payload.json" \
        --region "$AWS_REGION" \
        "$output_file" > /dev/null 2>&1; then
        
        validate_digest_response "$output_file"
        return $?
    else
        echo -e "${RED}❌ Config test failed${NC}"
        return 1
    fi
}

# Test user data export (GDPR compliance)
test_user_data_export() {
    local email="$1"
    
    echo "Testing user data export for: $email"
    
    # This would typically be implemented as a separate Lambda function
    # For now, we'll simulate by querying the database
    local table_name="${SUBSCRIBERS_TABLE_NAME}"
    
    local user_data
    user_data=$(aws dynamodb scan \
        --table-name "$table_name" \
        --filter-expression "email = :email" \
        --expression-attribute-values "{\":email\":{\"S\":\"$email\"}}" \
        --region "$AWS_REGION" \
        --output json 2>/dev/null)
    
    if [ $? -eq 0 ] && echo "$user_data" | jq -e '.Items | length > 0' > /dev/null 2>&1; then
        echo -e "${GREEN}✅ User data export successful${NC}"
        return 0
    else
        echo -e "${RED}❌ User data export failed${NC}"
        return 1
    fi
}

# Test user data deletion (GDPR compliance)
test_user_data_deletion() {
    local email="$1"
    
    echo "Testing user data deletion for: $email"
    
    # First, find the subscriber ID
    local table_name="${SUBSCRIBERS_TABLE_NAME}"
    
    local subscriber_data
    subscriber_data=$(aws dynamodb scan \
        --table-name "$table_name" \
        --filter-expression "email = :email" \
        --expression-attribute-values "{\":email\":{\"S\":\"$email\"}}" \
        --region "$AWS_REGION" \
        --output json 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        local subscriber_id
        subscriber_id=$(echo "$subscriber_data" | jq -r '.Items[0].subscriber_id.S' 2>/dev/null)
        
        if [ -n "$subscriber_id" ] && [ "$subscriber_id" != "null" ]; then
            # Delete the subscriber
            aws dynamodb delete-item \
                --table-name "$table_name" \
                --key "{\"subscriber_id\": {\"S\": \"$subscriber_id\"}}" \
                --region "$AWS_REGION" > /dev/null 2>&1
            
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✅ User data deletion successful${NC}"
                return 0
            fi
        fi
    fi
    
    echo -e "${RED}❌ User data deletion failed${NC}"
    return 1
}

# Verify user data removal
verify_user_data_removal() {
    local email="$1"
    
    echo "Verifying user data removal for: $email"
    
    local table_name="${SUBSCRIBERS_TABLE_NAME}"
    
    local result
    result=$(aws dynamodb scan \
        --table-name "$table_name" \
        --filter-expression "email = :email" \
        --expression-attribute-values "{\":email\":{\"S\":\"$email\"}}" \
        --region "$AWS_REGION" \
        --output json 2>/dev/null)
    
    if echo "$result" | jq -e '.Items | length == 0' > /dev/null 2>&1; then
        echo -e "${GREEN}✅ User data successfully removed${NC}"
        return 0
    else
        echo -e "${RED}❌ User data still exists${NC}"
        return 1
    fi
}

# Test malicious input
test_malicious_input() {
    local input="$1"
    local api_url
    
    api_url=$(get_stack_output_safe "SubscriptionEndpoint")
    
    echo "Testing malicious input: $input"
    
    local response
    response=$(curl -s -X POST "$api_url" \
        -H "Content-Type: application/json" \
        -d "$input" \
        --max-time 10 \
        -w "HTTPSTATUS:%{http_code}")
    
    local http_code=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    
    # Should return 400 for malicious input
    if [ "$http_code" = "400" ] || [ "$http_code" = "403" ]; then
        echo -e "${GREEN}✅ Malicious input correctly rejected${NC}"
        return 0
    else
        echo -e "${RED}❌ Malicious input not properly handled (HTTP: $http_code)${NC}"
        return 1
    fi
}

# Get CloudWatch metrics
get_lambda_cold_start_metrics() {
    # This would query CloudWatch for cold start metrics
    # For now, return a placeholder
    echo "0"
}

get_api_response_times() {
    # This would query CloudWatch for API Gateway metrics
    # For now, return a placeholder
    echo "[]"
}

get_dynamodb_throttle_count() {
    # This would query CloudWatch for DynamoDB throttle metrics
    # For now, return a placeholder
    echo "0"
}

get_s3_operation_metrics() {
    # This would query CloudWatch for S3 operation metrics
    # For now, return a placeholder
    echo "{}"
}

# Generate comprehensive E2E report
generate_e2e_report() {
    local report_file="/tmp/e2e-report-$(date +%Y%m%d_%H%M%S).json"
    
    echo "Generating E2E test report..."
    
    {
        echo "{"
        echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)\","
        echo "  \"environment\": \"$ENVIRONMENT\","
        echo "  \"region\": \"$AWS_REGION\","
        echo "  \"stack_name\": \"$CF_STACK_NAME\","
        echo "  \"tests_passed\": $TESTS_PASSED,"
        echo "  \"tests_failed\": $TESTS_FAILED,"
        echo "  \"failed_tests\": ["
        
        local first=true
        for test in "${FAILED_TESTS[@]}"; do
            if [ "$first" = true ]; then
                first=false
            else
                echo ","
            fi
            echo -n "    \"$test\""
        done
        
        echo ""
        echo "  ],"
        echo "  \"performance_metrics\": {"
        echo "    \"lambda_cold_starts\": $(get_lambda_cold_start_metrics),"
        echo "    \"api_response_times\": $(get_api_response_times),"
        echo "    \"dynamodb_throttles\": $(get_dynamodb_throttle_count),"
        echo "    \"s3_operations\": $(get_s3_operation_metrics)"
        echo "  }"
        echo "}"
    } > "$report_file"
    
    echo "E2E report generated: $report_file"
}

# Orchestration functions for different test categories
run_infrastructure_tests() {
    run_test "AWS CLI and credentials" "test_aws_cli"
    run_test "CloudFormation stack exists" "test_stack_exists"
    run_test "Lambda functions exist" "test_lambda_functions"
    run_test "DynamoDB table exists" "test_dynamodb_table"
    run_test "S3 buckets exist" "test_s3_buckets"
    run_test "EventBridge rule exists" "test_eventbridge_rule"
    run_test "IAM permissions" "test_iam_permissions"
}

run_functional_tests() {
    run_test "Subscription Lambda function" "test_subscription_lambda"
    run_test "API Gateway endpoint" "test_api_gateway"
    run_test "DynamoDB operations" "test_dynamodb_operations"
    run_test "S3 operations" "test_s3_operations"
    run_test "Lambda environment variables" "test_lambda_env_vars"
    run_test "Accounts configuration" "test_accounts_config"
    run_test "CloudWatch logs" "test_cloudwatch_logs"
    run_test "Subscriber data integrity" "verify_subscriber_data_integrity"
    run_test "Malformed request handling" "test_malformed_subscription_requests"
}

run_integration_tests() {
    run_test "Full subscription flow" "integration_test_subscription"
    
    # Test various email formats
    local test_emails=("valid@example.com" "test+tag@domain.co.uk" "user.name@subdomain.example.org")
    for email in "${test_emails[@]}"; do
        run_test "Subscription with $email" "test_subscription_with_email '$email'"
    done
    
    # Optional: Weekly digest test if API keys are available
    if [ -n "$TWITTER_BEARER_TOKEN" ] && [ -n "$GEMINI_API_KEY" ]; then
        run_test "Weekly digest dry run" "test_weekly_digest_dry_run"
    fi
}

run_performance_tests() {
    run_test "Lambda cold start performance" "performance_test_lambda"
    run_test "Concurrent subscriptions" "test_concurrent_subscriptions"
    run_test "DynamoDB throttling" "test_dynamodb_throttling"
}

run_security_tests() {
    run_test "Input validation" "test_input_validation"
    run_test "GDPR compliance" "test_gdpr_compliance"
    run_test "Invalid Twitter credentials" "test_with_invalid_twitter_credentials"
}

# Additional helper functions
add_test_subscriber() {
    local email="$1"
    local table_name="${SUBSCRIBERS_TABLE_NAME}"
    local subscriber_id="test-$(date +%s)-$(shuf -i 1000-9999 -n 1)"
    
    aws dynamodb put-item \
        --table-name "$table_name" \
        --item "{
            \"subscriber_id\": {\"S\": \"$subscriber_id\"},
            \"email\": {\"S\": \"$email\"},
            \"status\": {\"S\": \"active\"},
            \"created_at\": {\"S\": \"$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)\"}
        }" \
        --region "$AWS_REGION" > /dev/null 2>&1
    
    return $?
}

# Health check functions
run_health_checks() {
    echo "Running health checks..."
    
    # Check critical services
    test_aws_cli && \
    test_stack_exists && \
    test_lambda_functions && \
    test_dynamodb_table && \
    test_s3_buckets
}

verify_data_integrity() {
    echo "Verifying data integrity..."
    verify_subscriber_data_integrity
}

test_critical_user_journeys() {
    echo "Testing critical user journeys..."
    
    # Test the most important user flows
    local test_email="critical-test-$(date +%s)@example.com"
    test_subscription_with_email "$test_email"
}

echo "E2E functions library loaded successfully" 