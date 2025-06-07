# Deployment Testing Guide

## Overview
This guide provides a step-by-step checklist for deploying and testing the GenAI Tweets Digest serverless application, incorporating lessons learned from real-world deployment experiences.

## Prerequisites Checklist

### AWS Environment
- [ ] AWS CLI configured with appropriate profile
- [ ] CloudFormation stack deployed successfully
- [ ] API keys configured in `cf-params.json`
- [ ] SES email addresses verified (sender and test recipients)

### Local Environment
- [ ] `jq` installed for JSON parsing
- [ ] Python 3.x available
- [ ] All scripts executable (`chmod +x scripts/*.sh`)

### Environment Variables
```bash
export AWS_PROFILE=your-profile-name
export ENVIRONMENT=production
export AWS_REGION=us-east-1
export STACK_NAME=your-stack-name
```

## Step-by-Step Deployment Testing

### Phase 1: Infrastructure Validation

#### 1.1 Verify Stack Status
```bash
# Check stack status
zsh -d -f -c "aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION --profile $AWS_PROFILE --query 'Stacks[0].StackStatus' --output text | cat"

# Expected: UPDATE_COMPLETE or CREATE_COMPLETE
```

#### 1.2 Get Stack Outputs
```bash
# Get all stack outputs
zsh -d -f -c "aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION --profile $AWS_PROFILE --query 'Stacks[0].Outputs' --output table | cat"

# Note down:
# - WebsiteURL (CloudFront distribution)
# - SubscriptionEndpoint (API Gateway URL)
# - DataBucketName
# - WebsiteBucketName
```

#### 1.3 Run Infrastructure Tests
```bash
./scripts/e2e-test.sh --infrastructure-only
```
**Expected Result:** All infrastructure tests should pass (8/8)

### Phase 2: Configuration Setup

#### 2.1 Upload Configuration Files
```bash
# Upload accounts configuration
aws s3 cp data/accounts.json s3://DATA_BUCKET_NAME/config/accounts.json --profile $AWS_PROFILE

# Verify upload
aws s3 cp s3://DATA_BUCKET_NAME/config/accounts.json /tmp/verify-accounts.json --profile $AWS_PROFILE
cat /tmp/verify-accounts.json
```

#### 2.2 Verify SES Email Setup
```bash
# Check verified email addresses
aws ses get-identity-verification-attributes --identities noreply@yourdomain.com your-test-email@domain.com --region $AWS_REGION --profile $AWS_PROFILE

# If not verified, verify them:
aws ses verify-email-identity --email-address noreply@yourdomain.com --region $AWS_REGION --profile $AWS_PROFILE
aws ses verify-email-identity --email-address your-test-email@domain.com --region $AWS_REGION --profile $AWS_PROFILE
```

### Phase 3: Frontend Deployment

#### 3.1 Build Frontend
```bash
./scripts/setup-frontend.sh
```

#### 3.2 Update API Configuration
```bash
# Edit frontend-static/config.js with actual API Gateway URL
# Update API_BASE_URL to match your SubscriptionEndpoint from stack outputs
```

#### 3.3 Deploy to S3
```bash
# Upload frontend files
aws s3 sync frontend-static/out/ s3://WEBSITE_BUCKET_NAME/ --profile $AWS_PROFILE --delete

# Upload configuration
aws s3 cp frontend-static/config.js s3://WEBSITE_BUCKET_NAME/config.js --profile $AWS_PROFILE
```

#### 3.4 Verify Frontend Deployment
```bash
# Test website accessibility
curl -s https://CLOUDFRONT_URL/config.js

# Expected: Should return the config.js content
```

### Phase 4: Functional Testing

#### 4.1 Run Functional Tests
```bash
./scripts/e2e-test.sh --functional-only
```
**Expected Result:** All functional tests should pass (8/8)

#### 4.2 Test Subscription API Manually
```bash
# Test subscription endpoint
curl -X POST https://API_GATEWAY_URL/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email": "test-deployment@example.com"}' \
  -w "HTTP Status: %{http_code}\n"

# Expected: HTTP Status: 200 with success message
```

#### 4.3 Verify Subscription in DynamoDB
```bash
# Check if subscription was stored
aws dynamodb scan --table-name SUBSCRIBERS_TABLE_NAME --region $AWS_REGION --profile $AWS_PROFILE --query 'Items[?email.S==`test-deployment@example.com`]'

# Expected: Should return the subscriber record
```

### Phase 5: End-to-End Workflow Testing

#### 5.1 Subscribe with Real Email
```bash
# Subscribe with your actual email for testing
curl -X POST https://API_GATEWAY_URL/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@domain.com"}' \
  -w "HTTP Status: %{http_code}\n"
```

#### 5.2 Trigger Digest Generation
```bash
# Create payload file
echo '{"source": "aws.events", "detail-type": "Scheduled Event"}' > /tmp/digest_payload.json

# Invoke weekly digest function
AWS_PROFILE=$AWS_PROFILE aws lambda invoke \
  --function-name WEEKLY_DIGEST_FUNCTION_NAME \
  --payload file:///tmp/digest_payload.json \
  --region $AWS_REGION \
  /tmp/digest_response.json \
  --cli-binary-format raw-in-base64-out

# Check response
cat /tmp/digest_response.json | jq .
```

#### 5.3 Monitor Lambda Execution
```bash
# Get latest log stream
LATEST_STREAM=$(aws logs describe-log-streams \
  --log-group-name '/aws/lambda/WEEKLY_DIGEST_FUNCTION_NAME' \
  --order-by LastEventTime --descending --max-items 1 \
  --query 'logStreams[0].logStreamName' --output text \
  --region $AWS_REGION --profile $AWS_PROFILE)

# Get log events
aws logs get-log-events \
  --log-group-name '/aws/lambda/WEEKLY_DIGEST_FUNCTION_NAME' \
  --log-stream-name "$LATEST_STREAM" \
  --region $AWS_REGION --profile $AWS_PROFILE
```

#### 5.4 Verify Digest Generation
```bash
# List generated digests
aws s3 ls s3://DATA_BUCKET_NAME/tweets/digests/ --profile $AWS_PROFILE

# Download latest digest
LATEST_DIGEST=$(aws s3 ls s3://DATA_BUCKET_NAME/tweets/digests/ --profile $AWS_PROFILE | sort | tail -n 1 | awk '{print $4}')
aws s3 cp s3://DATA_BUCKET_NAME/tweets/digests/$LATEST_DIGEST /tmp/latest_digest.json --profile $AWS_PROFILE

# Examine digest content
cat /tmp/latest_digest.json | jq '.summaries'
cat /tmp/latest_digest.json | jq '.total_tweets, .generated_at'
```

### Phase 6: Integration Testing

#### 6.1 Run Integration Tests
```bash
./scripts/e2e-test.sh --integration-only
```
**Expected Result:** All integration tests should pass

#### 6.2 Test Website Subscription Flow
1. Visit the website URL from stack outputs
2. Enter your email in the subscription form
3. Submit the form
4. Verify success message appears
5. Check DynamoDB for the new subscription

### Phase 7: Performance and Security Testing

#### 7.1 Run Performance Tests
```bash
./scripts/e2e-test.sh --performance-only
```

#### 7.2 Run Security Tests
```bash
./scripts/e2e-test.sh --security-only
```

## Troubleshooting Common Issues

### Lambda Invocation Fails with Encoding Errors
**Symptoms:** `Invalid base64` or `Unexpected character` errors

**Solution:**
```bash
# Use file-based payloads with clean shell execution
echo '{"source": "manual"}' > /tmp/payload.json
zsh -d -f -c "aws lambda invoke --function-name FUNCTION_NAME --payload file:///tmp/payload.json --region $AWS_REGION --profile $AWS_PROFILE /tmp/response.json | cat"
```

### SES Email Verification Errors
**Symptoms:** `Email address is not verified` errors

**Solution:**
```bash
# Verify both sender and recipient emails
aws ses verify-email-identity --email-address noreply@yourdomain.com --region $AWS_REGION --profile $AWS_PROFILE
aws ses verify-email-identity --email-address recipient@domain.com --region $AWS_REGION --profile $AWS_PROFILE
```

### Frontend 403 Access Denied
**Symptoms:** Website returns 403 errors

**Solution:**
```bash
# Ensure frontend files are uploaded
aws s3 sync frontend-static/out/ s3://WEBSITE_BUCKET_NAME/ --profile $AWS_PROFILE --delete
aws s3 cp frontend-static/config.js s3://WEBSITE_BUCKET_NAME/config.js --profile $AWS_PROFILE
```

### Frontend Shows Generic Error Messages
**Symptoms:** 
- All errors show "Something went wrong. Please try again."
- Duplicate email submissions don't show "Email already subscribed"
- Invalid emails don't show proper validation messages

**Root Cause:** Frontend error handling overrides API service messages

**Debugging Steps:**
```bash
# 1. Test API directly to verify it returns correct messages
curl -X POST https://API_GATEWAY_URL/subscribe -H "Content-Type: application/json" -d '{"email": "test@example.com"}' -v
curl -X POST https://API_GATEWAY_URL/subscribe -H "Content-Type: application/json" -d '{"email": "test@example.com"}' -v  # Duplicate
curl -X POST https://API_GATEWAY_URL/subscribe -H "Content-Type: application/json" -d '{"email": "invalid-email"}' -v    # Invalid

# 2. Check for conflicting API service files
ls -la frontend-static/src/utils/api.*

# 3. Verify config.js is loaded correctly
curl -s https://CLOUDFRONT_URL/config.js

# 4. Check built JavaScript for correct API integration
curl -s "https://CLOUDFRONT_URL/_next/static/chunks/app/page-HASH.js" | grep -o "API_BASE_URL"
```

**Solution:**
```bash
# 1. Remove conflicting TypeScript files
rm -f frontend-static/src/utils/api.ts

# 2. Ensure EmailSignup component uses API service messages directly
# Edit frontend-static/src/components/EmailSignup.tsx:
# Replace complex error handling with: setMessage(error.message);

# 3. Rebuild and redeploy
cd frontend-static && npm run build
cd .. && aws s3 sync frontend-static/out/ s3://WEBSITE_BUCKET_NAME/ --profile $AWS_PROFILE --delete
aws s3 cp frontend-static/config.js s3://WEBSITE_BUCKET_NAME/config.js --profile $AWS_PROFILE

# 4. Invalidate CloudFront cache
DISTRIBUTION_ID=$(zsh -d -f -c "aws cloudfront list-distributions --profile $AWS_PROFILE --query 'DistributionList.Items[?DomainName==\`CLOUDFRONT_DOMAIN\`].Id' --output text | cat")
zsh -d -f -c "aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths '/*' --profile $AWS_PROFILE | cat"

# 5. Wait for invalidation to complete
zsh -d -f -c "aws cloudfront get-invalidation --distribution-id $DISTRIBUTION_ID --id INVALIDATION_ID --profile $AWS_PROFILE --query 'Invalidation.Status' --output text | cat"
```

### CloudFront Serving Old Frontend Files
**Symptoms:**
- Website shows old behavior after frontend updates
- New JavaScript files return 404 errors
- Changes not visible despite successful S3 upload

**Root Cause:** CloudFront cache not invalidated after deployment

**Solution:**
```bash
# 1. Find CloudFront distribution ID
DISTRIBUTION_ID=$(zsh -d -f -c "aws cloudfront list-distributions --profile $AWS_PROFILE --query 'DistributionList.Items[?DomainName==\`YOUR_CLOUDFRONT_DOMAIN\`].Id' --output text | cat")

# 2. Create invalidation
INVALIDATION_RESULT=$(zsh -d -f -c "aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths '/*' --profile $AWS_PROFILE | cat")
INVALIDATION_ID=$(echo $INVALIDATION_RESULT | jq -r '.Invalidation.Id')

# 3. Monitor invalidation status
while true; do
  STATUS=$(zsh -d -f -c "aws cloudfront get-invalidation --distribution-id $DISTRIBUTION_ID --id $INVALIDATION_ID --profile $AWS_PROFILE --query 'Invalidation.Status' --output text | cat")
  echo "Invalidation status: $STATUS"
  if [ "$STATUS" = "Completed" ]; then
    break
  fi
  sleep 30
done

# 4. Verify new files are served
curl -s "https://YOUR_CLOUDFRONT_DOMAIN/_next/static/chunks/app/page-HASH.js" | wc -l
```

**Prevention:**
- Always invalidate CloudFront after frontend deployments
- Use specific paths (`/_next/static/*`) instead of `/*` to reduce costs
- Consider implementing versioned file names in build process

### Lambda Function Timeout
**Symptoms:** Function times out during execution

**Solution:**
1. Check CloudWatch logs for specific error
2. Verify API keys are correctly configured
3. Check network connectivity to external APIs
4. Consider increasing Lambda timeout if needed

## Success Criteria Checklist

### Infrastructure (8/8 tests passing)
- [ ] AWS CLI connectivity
- [ ] CloudFormation stack exists and is healthy
- [ ] Lambda functions deployed and configured
- [ ] DynamoDB table accessible
- [ ] S3 buckets created and accessible
- [ ] EventBridge rule configured
- [ ] IAM permissions working
- [ ] API Gateway endpoint responding

### Functional (8/8 tests passing)
- [ ] Subscription Lambda function working
- [ ] Weekly digest Lambda function working
- [ ] DynamoDB read/write operations
- [ ] S3 file operations
- [ ] Email template generation
- [ ] Configuration loading
- [ ] Error handling
- [ ] Data validation

### Integration (6/6 tests passing)
- [ ] End-to-end subscription flow
- [ ] Email format validation
- [ ] Digest generation with real data
- [ ] Email delivery (if SES configured)
- [ ] Website functionality
- [ ] API integration

### End-to-End Workflow
- [ ] Website accessible via CloudFront
- [ ] Subscription form works
- [ ] Email stored in DynamoDB
- [ ] Digest generation completes successfully
- [ ] Generated digest contains expected content
- [ ] All external API integrations working

## Post-Deployment Validation

### Daily Checks
- [ ] CloudWatch logs show no errors
- [ ] Lambda functions executing successfully
- [ ] No SES bounce notifications

### Weekly Checks
- [ ] Digest generation running on schedule
- [ ] Email delivery working
- [ ] Subscriber count growing as expected
- [ ] No AWS service limit warnings

### Monthly Checks
- [ ] AWS costs within expected range
- [ ] Performance metrics acceptable
- [ ] Security audit clean
- [ ] Backup and recovery procedures tested

## Emergency Procedures

### Rollback Process
1. Identify the last known good CloudFormation stack version
2. Revert to previous stack version if needed
3. Restore configuration files from backup
4. Verify all services are working

### Incident Response
1. Check CloudWatch alarms and logs
2. Verify external API status (Twitter, Gemini, SES)
3. Check AWS service health dashboard
4. Contact support if AWS service issues detected

---

**Note:** This guide should be updated whenever new deployment patterns or issues are discovered. Always test in a development environment before applying to production. 