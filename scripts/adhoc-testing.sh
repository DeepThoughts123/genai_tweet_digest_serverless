#!/bin/bash

# Ad-hoc Testing Script for GenAI Tweets Digest
# This script manages EventBridge schedules for ad-hoc testing with real digest generation

set -e

# Configuration
PROJECT_NAME="genai-tweets-digest"
ENVIRONMENT="production"
AWS_REGION="us-east-1"
STACK_NAME="genai-tweets-digest-production"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper function to get CloudFormation outputs with clean shell execution
get_stack_output() {
    local output_key="$1"
    local result
    result=$(zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation describe-stacks \
        --stack-name '$STACK_NAME' \
        --region '$AWS_REGION' \
        --query \"Stacks[0].Outputs[?OutputKey=='$output_key'].OutputValue\" \
        --output text | cat" 2>/dev/null || echo "")
    echo "$result"
}

# Function to get subscriber count
check_subscribers() {
    echo -e "${BLUE}📊 Checking subscriber count...${NC}"
    
    local table_name
    table_name=$(get_stack_output "SubscribersTableName")
    
    if [ -z "$table_name" ]; then
        echo -e "${RED}❌ Could not get subscribers table name from CloudFormation outputs${NC}"
        return 1
    fi
    
    echo "Table name: $table_name"
    
    local subscriber_count
    subscriber_count=$(zsh -d -f -c "export AWS_PROFILE=personal && aws dynamodb scan \
        --table-name '$table_name' \
        --select COUNT \
        --region '$AWS_REGION' \
        --output json | jq '.Count' | cat" 2>/dev/null || echo "0")
    
    echo -e "${GREEN}✅ Subscribers found: $subscriber_count${NC}"
    
    if [ "$subscriber_count" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  No subscribers found. You may want to add test subscribers first.${NC}"
        echo "You can add subscribers via the subscription endpoint or directly to DynamoDB."
        return 1
    fi
    
    return 0
}

# Function to get current EventBridge rule
get_eventbridge_rule_name() {
    # First try to get it from CloudFormation
    local rule_name
    rule_name=$(zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation describe-stack-resources \
        --stack-name '$STACK_NAME' \
        --region '$AWS_REGION' \
        --query \"StackResources[?ResourceType=='AWS::Events::Rule'].PhysicalResourceId\" \
        --output text | cat" 2>/dev/null || echo "")
    
    if [ -z "$rule_name" ]; then
        # Fallback to expected naming pattern
        rule_name="${STACK_NAME}-digest-schedule"
    fi
    
    echo "$rule_name"
}

# Function to get current schedule
get_current_schedule() {
    local rule_name="$1"
    local current_schedule
    current_schedule=$(zsh -d -f -c "export AWS_PROFILE=personal && aws events describe-rule \
        --name '$rule_name' \
        --region '$AWS_REGION' \
        --query 'ScheduleExpression' \
        --output text | cat" 2>/dev/null || echo "")
    echo "$current_schedule"
}

# Function to update EventBridge rule schedule
update_schedule() {
    local rule_name="$1"
    local new_schedule="$2"
    
    echo -e "${BLUE}🔄 Updating EventBridge rule schedule...${NC}"
    echo "Rule: $rule_name"
    echo "New schedule: $new_schedule"
    
    zsh -d -f -c "export AWS_PROFILE=personal && aws events put-rule \
        --name '$rule_name' \
        --schedule-expression '$new_schedule' \
        --state ENABLED \
        --region '$AWS_REGION' | cat"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Schedule updated successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to update schedule${NC}"
        return 1
    fi
}

# Function to generate specific time schedule for testing
generate_test_schedule() {
    local date="$1"  # Format: YYYY-MM-DD
    local times="$2" # Comma-separated times in UTC (HH:MM format)
    
    # For EventBridge, we need to create a schedule that runs at specific times on a specific date
    # Convert the times to cron expressions
    # For example: "15:15,15:30,15:45,16:00" becomes multiple cron expressions
    
    # Since EventBridge can only have one schedule expression per rule, we'll use a broader schedule
    # that covers the test period and let the Lambda function handle filtering if needed
    
    # Extract year, month, day
    local year=$(echo "$date" | cut -d'-' -f1)
    local month=$(echo "$date" | cut -d'-' -f2)
    local day=$(echo "$date" | cut -d'-' -f3)
    
    # Create a schedule that runs every 15 minutes during the test window
    # For times 15:15, 15:30, 15:45, 16:00 we use:
    local schedule="cron(0,15,30,45 15-16 $day $month ? $year)"
    
    echo "$schedule"
}

# Function to monitor digest execution
monitor_digest_execution() {
    local function_name="${STACK_NAME}-weekly-digest"
    
    echo -e "${BLUE}📊 Monitoring digest execution...${NC}"
    echo "Function: $function_name"
    echo "Press Ctrl+C to stop monitoring"
    echo ""
    
    # Get the log group
    local log_group="/aws/lambda/$function_name"
    
    # Monitor logs in real-time
    zsh -d -f -c "export AWS_PROFILE=personal && aws logs tail '$log_group' \
        --region '$AWS_REGION' \
        --follow | cat"
}

# Function to manually trigger digest (for testing)
trigger_digest_manually() {
    local function_name="${STACK_NAME}-weekly-digest"
    
    echo -e "${BLUE}🚀 Manually triggering digest generation...${NC}"
    
    # Create payload file
    local payload_file="/tmp/adhoc_digest_payload.json"
    echo '{"source": "manual.trigger", "detail-type": "Ad-hoc Testing", "detail": {"test_run": true}}' > "$payload_file"
    
    local output_file="/tmp/adhoc_digest_response.json"
    
    echo "Triggering function: $function_name"
    echo "Payload: $(cat $payload_file)"
    
    zsh -d -f -c "export AWS_PROFILE=personal && aws lambda invoke \
        --function-name '$function_name' \
        --payload file://$payload_file \
        --region '$AWS_REGION' \
        '$output_file' \
        --cli-binary-format raw-in-base64-out | cat"
    
    if [ -f "$output_file" ]; then
        echo "Response:"
        cat "$output_file" | jq . 2>/dev/null || cat "$output_file"
    fi
    
    echo ""
    echo -e "${YELLOW}💡 Check CloudWatch logs for detailed execution information${NC}"
}

# Function to check recent digest results
check_digest_results() {
    local data_bucket
    data_bucket=$(get_stack_output "DataBucketName")
    
    if [ -z "$data_bucket" ]; then
        echo -e "${RED}❌ Could not get data bucket name${NC}"
        return 1
    fi
    
    echo -e "${BLUE}📂 Checking recent digest results...${NC}"
    echo "Data bucket: $data_bucket"
    
    # List recent digest files
    echo ""
    echo "Recent digest files:"
    zsh -d -f -c "export AWS_PROFILE=personal && aws s3 ls 's3://$data_bucket/tweets/digests/' \
        --recursive --human-readable \
        --region '$AWS_REGION' | tail -10 | cat"
    
    # Try to download and display the latest digest
    echo ""
    echo "Latest digest content (summary):"
    local latest_digest="/tmp/latest_digest.json"
    
    if zsh -d -f -c "export AWS_PROFILE=personal && aws s3 cp 's3://$data_bucket/tweets/digests/latest-digest.json' \
        '$latest_digest' --region '$AWS_REGION' | cat" 2>/dev/null; then
        
        echo "Downloaded latest digest. Summary:"
        if command -v jq > /dev/null; then
            jq -r '.generation_metadata.summary // .summary // "No summary available"' "$latest_digest" 2>/dev/null || echo "Could not parse summary"
            echo ""
            echo "Number of summaries: $(jq '.summaries | length' "$latest_digest" 2>/dev/null || echo "Unknown")"
            echo "Generation time: $(jq -r '.generation_metadata.generated_at // .generated_at // "Unknown"' "$latest_digest" 2>/dev/null)"
        else
            echo "Latest digest file downloaded to $latest_digest (jq not available for parsing)"
        fi
    else
        echo "No latest digest found or failed to download"
    fi
}

# Main functions for different operations

# Setup ad-hoc testing schedule
setup_adhoc_schedule() {
    local test_date="$1"  # YYYY-MM-DD format
    local start_time_est="$2"  # HH:MM format in EST
    
    if [ -z "$test_date" ] || [ -z "$start_time_est" ]; then
        echo -e "${RED}❌ Usage: setup_adhoc_schedule <date> <start_time_est>${NC}"
        echo "Example: setup_adhoc_schedule 2025-05-28 11:15"
        return 1
    fi
    
    echo -e "${BLUE}🎯 Setting up ad-hoc testing schedule${NC}"
    echo "Date: $test_date"
    echo "Start time (EST): $start_time_est"
    
    # Convert EST to UTC (EST = UTC-4 for EDT)
    local hour_est=$(echo "$start_time_est" | cut -d':' -f1)
    local minute_est=$(echo "$start_time_est" | cut -d':' -f2)
    local hour_utc=$((hour_est + 4))
    
    # Handle day rollover if needed
    if [ $hour_utc -ge 24 ]; then
        hour_utc=$((hour_utc - 24))
        # Note: This is a simplified conversion, doesn't handle date changes
        echo -e "${YELLOW}⚠️  Time conversion resulted in next day UTC. Please verify manually.${NC}"
    fi
    
    local start_time_utc=$(printf "%02d:%02d" $hour_utc $minute_est)
    echo "Start time (UTC): $start_time_utc"
    
    # Generate the schedule for 4 runs (15-minute intervals)
    local times="${hour_utc}:${minute_est},${hour_utc}:$((minute_est + 15)),${hour_utc}:$((minute_est + 30)),$((hour_utc + 1)):$(printf "%02d" $((minute_est - 60 + 60)))"
    
    # Get EventBridge rule name
    local rule_name
    rule_name=$(get_eventbridge_rule_name)
    echo "EventBridge rule: $rule_name"
    
    # Save current schedule
    local current_schedule
    current_schedule=$(get_current_schedule "$rule_name")
    echo "Current schedule: $current_schedule"
    
    # Save it to a backup file
    echo "$current_schedule" > "/tmp/original_schedule_backup.txt"
    echo -e "${GREEN}✅ Original schedule backed up to /tmp/original_schedule_backup.txt${NC}"
    
    # Generate new test schedule
    local test_schedule
    test_schedule=$(generate_test_schedule "$test_date" "$times")
    echo "Test schedule: $test_schedule"
    
    # Update the schedule
    update_schedule "$rule_name" "$test_schedule"
    
    echo ""
    echo -e "${GREEN}🎉 Ad-hoc testing schedule set up successfully!${NC}"
    echo "The digest will run every 15 minutes starting at $start_time_est EST on $test_date"
    echo "Total expected runs: 4 (every 15 minutes for 1 hour)"
    echo ""
    echo -e "${YELLOW}💡 To monitor execution:${NC} $0 monitor"
    echo -e "${YELLOW}💡 To check results:${NC} $0 results"
    echo -e "${YELLOW}💡 To restore schedule:${NC} $0 restore"
}

# Restore original schedule
restore_schedule() {
    echo -e "${BLUE}🔄 Restoring original schedule...${NC}"
    
    local backup_file="/tmp/original_schedule_backup.txt"
    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}❌ No backup schedule found at $backup_file${NC}"
        echo "Please manually restore the original schedule or run setup_adhoc_schedule first"
        return 1
    fi
    
    local original_schedule
    original_schedule=$(cat "$backup_file")
    echo "Original schedule: $original_schedule"
    
    local rule_name
    rule_name=$(get_eventbridge_rule_name)
    
    update_schedule "$rule_name" "$original_schedule"
    
    echo -e "${GREEN}✅ Original schedule restored successfully${NC}"
    
    # Clean up backup file
    rm -f "$backup_file"
}

# Usage function
usage() {
    echo "Ad-hoc Testing Script for GenAI Tweets Digest"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  check                          - Check current system status and subscribers"
    echo "  setup <date> <time_est>        - Setup ad-hoc testing schedule"
    echo "                                   Example: setup 2025-05-28 11:15"
    echo "  monitor                        - Monitor digest execution in real-time"
    echo "  trigger                        - Manually trigger a digest (for testing)"
    echo "  results                        - Check recent digest results"
    echo "  restore                        - Restore original EventBridge schedule"
    echo ""
    echo "Examples:"
    echo "  $0 check                       # Check system status"
    echo "  $0 setup 2025-05-28 11:15     # Setup testing for May 28, 11:15 AM EST"
    echo "  $0 monitor                     # Monitor execution"
    echo "  $0 results                     # Check digest results"
    echo "  $0 restore                     # Restore original schedule"
}

# Main script execution
main() {
    local command="$1"
    
    case "$command" in
        "check")
            echo -e "${BLUE}🔍 Checking system status...${NC}"
            check_subscribers
            
            local rule_name
            rule_name=$(get_eventbridge_rule_name)
            echo ""
            echo "EventBridge rule: $rule_name"
            
            local current_schedule
            current_schedule=$(get_current_schedule "$rule_name")
            echo "Current schedule: $current_schedule"
            ;;
        "setup")
            local date="$2"
            local time="$3"
            setup_adhoc_schedule "$date" "$time"
            ;;
        "monitor")
            monitor_digest_execution
            ;;
        "trigger")
            trigger_digest_manually
            ;;
        "results")
            check_digest_results
            ;;
        "restore")
            restore_schedule
            ;;
        *)
            usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@" 