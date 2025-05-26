# End-to-End Testing Plan

## Overview
This document outlines the complete end-to-end testing strategy for the GenAI Tweets Digest serverless architecture. It covers testing the entire workflow from subscription to digest delivery.

## Prerequisites
- AWS CLI configured with appropriate permissions
- CloudFormation stack deployed
- API keys configured in `cf-params.json`
- Test email addresses available

## E2E Test Scenarios

### 1. Complete Subscription Flow
**Objective**: Test the entire subscription process from website to database storage.

**Steps**:
1. Open the static website (S3/CloudFront URL)
2. Enter a test email address in the subscription form
3. Submit the form
4. Verify API Gateway receives the request
5. Verify Lambda function processes the subscription
6. Verify email is stored in DynamoDB
7. Verify confirmation email is sent via SES

**Expected Results**:
- Subscription form submits successfully
- Email appears in DynamoDB `subscribers` table
- Confirmation email received at test address
- No errors in CloudWatch logs

### 2. Weekly Digest Generation
**Objective**: Test the complete digest generation and delivery process.

**Steps**:
1. Trigger the weekly digest Lambda manually (or wait for scheduled run)
2. Verify tweets are fetched from configured accounts
3. Verify tweets are categorized using Gemini AI
4. Verify summary is generated
5. Verify digest is stored in S3
6. Verify emails are sent to all subscribers
7. Verify unsubscribe links work

**Expected Results**:
- Digest JSON file created in S3 `digests/` folder
- HTML email generated with proper formatting
- All subscribers receive the digest email
- Unsubscribe links function correctly
- CloudWatch logs show successful execution

### 3. Data Portability Test
**Objective**: Verify that all data can be easily exported and migrated.

**Steps**:
1. Export subscriber data from DynamoDB
2. Download all digest files from S3
3. Export Twitter accounts configuration
4. Verify data integrity and completeness
5. Test import process (optional)

**Expected Results**:
- All subscriber emails exported successfully
- All digest files downloaded
- Data format is portable (JSON/CSV)
- No data corruption or loss

### 4. Error Handling and Recovery
**Objective**: Test system behavior under various failure conditions.

**Steps**:
1. Test with invalid Twitter API credentials
2. Test with invalid Gemini API credentials
3. Test with malformed email addresses
4. Test with SES sending limits exceeded
5. Test Lambda timeout scenarios
6. Test DynamoDB throttling

**Expected Results**:
- Graceful error handling in all scenarios
- Appropriate error messages in CloudWatch
- System recovers automatically where possible
- No data corruption during failures

### 5. Performance and Scalability
**Objective**: Verify system performance under realistic load.

**Steps**:
1. Test with 100+ subscribers
2. Test with large tweet volumes (100+ tweets)
3. Test concurrent subscription requests
4. Monitor Lambda cold start times
5. Monitor memory usage and execution time

**Expected Results**:
- Digest generation completes within 15 minutes
- Lambda functions handle concurrent requests
- Cold start times under 5 seconds
- Memory usage within allocated limits

## Manual Testing Procedures

### Test 1: Subscription Workflow
```bash
# 1. Get the website URL
aws cloudformation describe-stacks \
  --stack-name genai-tweets-digest-production \
  --query 'Stacks[0].Outputs[?OutputKey==`WebsiteURL`].OutputValue' \
  --output text

# 2. Test subscription API directly
curl -X POST \
  "$(aws cloudformation describe-stacks --stack-name genai-tweets-digest-production --query 'Stacks[0].Outputs[?OutputKey==`SubscriptionApiUrl`].OutputValue' --output text)" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# 3. Verify in DynamoDB
aws dynamodb scan \
  --table-name genai-tweets-digest-production-subscribers \
  --query 'Items[?email.S==`test@example.com`]'
```

### Test 2: Manual Digest Trigger
```bash
# Trigger the weekly digest Lambda
aws lambda invoke \
  --function-name genai-tweets-digest-production-weekly-digest \
  --payload '{}' \
  response.json

# Check the response
cat response.json

# Verify digest was created
aws s3 ls s3://genai-tweets-digest-production-data/digests/
```

### Test 3: Data Export
```bash
# Export all subscribers
aws dynamodb scan \
  --table-name genai-tweets-digest-production-subscribers \
  --output json > subscribers_backup.json

# Download all digests
aws s3 sync s3://genai-tweets-digest-production-data/digests/ ./digests_backup/

# Verify accounts configuration
cat data/accounts.json
```

## Automated E2E Test Script

Create `scripts/e2e-test.sh`:

```bash
#!/bin/bash
set -e

echo "Starting E2E Tests..."

# Test 1: Subscription
echo "Testing subscription..."
SUBSCRIPTION_URL=$(aws cloudformation describe-stacks \
  --stack-name genai-tweets-digest-production \
  --query 'Stacks[0].Outputs[?OutputKey==`SubscriptionApiUrl`].OutputValue' \
  --output text)

curl -X POST "$SUBSCRIPTION_URL" \
  -H "Content-Type: application/json" \
  -d '{"email": "e2e-test@example.com"}' \
  -w "HTTP Status: %{http_code}\n"

# Test 2: Verify subscription in DB
echo "Verifying subscription in database..."
aws dynamodb get-item \
  --table-name genai-tweets-digest-production-subscribers \
  --key '{"email": {"S": "e2e-test@example.com"}}' \
  --query 'Item.email.S'

# Test 3: Trigger digest
echo "Triggering weekly digest..."
aws lambda invoke \
  --function-name genai-tweets-digest-production-weekly-digest \
  --payload '{}' \
  /tmp/digest-response.json

# Test 4: Verify digest created
echo "Verifying digest was created..."
aws s3 ls s3://genai-tweets-digest-production-data/digests/ | tail -1

# Test 5: Cleanup
echo "Cleaning up test data..."
aws dynamodb delete-item \
  --table-name genai-tweets-digest-production-subscribers \
  --key '{"email": {"S": "e2e-test@example.com"}}'

echo "E2E Tests completed successfully!"
```

## Test Data Management

### Test Accounts
Create test Twitter accounts list in `data/accounts-test.json`:
```json
[
  {
    "username": "elonmusk",
    "category": "Tech Leaders"
  },
  {
    "username": "sundarpichai",
    "category": "Tech Leaders"
  }
]
```

### Test Email Addresses
- Use disposable email services for testing
- Set up email forwarding for automated verification
- Use different domains to test email delivery

## Success Criteria

### Functional Requirements
- ✅ Subscription form works on static website
- ✅ Emails are stored in DynamoDB
- ✅ Weekly digest generates successfully
- ✅ Emails are delivered to subscribers
- ✅ Unsubscribe functionality works
- ✅ Data can be exported/imported

### Performance Requirements
- ✅ Digest generation completes within 15 minutes
- ✅ API responses under 5 seconds
- ✅ Website loads within 3 seconds
- ✅ Lambda cold starts under 5 seconds

### Reliability Requirements
- ✅ System handles API failures gracefully
- ✅ No data loss during errors
- ✅ Automatic retry mechanisms work
- ✅ Error notifications are sent

## Monitoring and Observability

### CloudWatch Dashboards
Monitor key metrics:
- Lambda execution duration
- Error rates
- DynamoDB read/write capacity
- S3 storage usage
- SES sending statistics

### Alerts
Set up alerts for:
- Lambda function failures
- DynamoDB throttling
- SES bounce rates
- API Gateway 5xx errors

## Rollback Plan

If E2E tests fail:
1. Check CloudWatch logs for errors
2. Verify API keys and permissions
3. Test individual components
4. Rollback to previous working version
5. Investigate and fix issues
6. Re-run E2E tests

## Conclusion

This E2E testing plan ensures the serverless GenAI Tweets Digest system works correctly from end to end. Regular execution of these tests will maintain system reliability and catch issues early. 