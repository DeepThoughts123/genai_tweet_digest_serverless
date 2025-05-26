# AWS CLI Best Practices and Lessons Learned

This document outlines best practices and key lessons learned while working with the AWS CLI, particularly in the context of shell environments that might interfere with command execution or output, and when performing multi-step operations like CloudFormation deployments for the GenAI Tweets Digest serverless project.

## 1. Shell Environment and AWS CLI Output

**Problem:** AWS CLI commands, especially those intended to output JSON (e.g., `aws cloudformation describe-stacks --output json`), were having their output incorrectly piped or processed, resulting in errors like `head: |: No such file or directory` or `head: cat: No such file or directory`. This masked the actual success or failure of the commands and their JSON responses.

**Root Cause (Likely):** Custom configurations in the user's Zsh startup files (`~/.zshrc`, Oh My Zsh plugins/themes, or other sourced profiles like `~/.instacart_shell_profile`) interfering with the AWS CLI's default output handling, possibly by misconfiguring a pager (like `less`) or aliasing output-related commands (`cat`, `head`, etc.).

**Effective Workaround:** Execute problematic AWS CLI commands within a temporarily "clean" Zsh subshell that bypasses most custom startup scripts. Piping to `cat` can help ensure the output is displayed directly.

```bash
# For commands expected to produce JSON and be displayed
zsh -d -f -c "YOUR_AWS_COMMAND_HERE --output json | cat"

# For commands where clean execution is needed (output might not be JSON)
zsh -d -f -c "YOUR_AWS_COMMAND_HERE"
```
*   `zsh -d -f -c "..."`: Ensures the command runs in a Zsh instance without user/global rc files.

**File Redirection with Workaround:** When redirecting output to a file, ensure the redirection happens for the output of the clean Zsh subshell if you want to capture the AWS command's direct output:
```bash
# Incorrect - parent shell redirection might capture Zsh -c wrapper's output
# zsh -d -f -c "aws cloudformation create-stack ... --output json" > output.json 

# Correct - capture output from within the clean Zsh subshell
zsh -d -f -c "aws cloudformation create-stack ... --output json | cat > output.json"
# OR, if cat is part of the problem:
zsh -d -f -c "aws cloudformation create-stack ... --output json" > output.json 2>&1 
# (The last one captures stderr too, useful if the aws command itself fails before producing JSON)
```

## 2. AWS CLI Command Execution Strategy

**Observation:** Long, chained AWS CLI commands (linking multiple operations with `&&` or `||`) are hard to debug and obscure granular feedback.

**Best Practice:** Execute AWS CLI operations as separate, sequential commands. This provides clear feedback for each step and simplifies troubleshooting.
    *   Verify outcomes in the AWS console after each significant step.
    *   Check local output files immediately after commands that create them.
    *   Use `aws ... wait` commands judiciously for long-running operations.

## 3. CloudFormation Best Practices & Troubleshooting

*   **Stack Naming:** Use unique stack names (e.g., appending a timestamp `$(date +%Y%m%d-%H%M%S)`) for new deployments, especially during iterative testing, to avoid conflicts with stacks in `DELETE_FAILED` or `ROLLBACK_COMPLETE` states.
*   **Parameter Passing:** For `aws cloudformation create-stack` or `update-stack` with multiple or complex parameters (especially sensitive ones like API keys):
    *   **Avoid Direct Command Line Expansion:** Shell expansion of variables containing special characters can be unreliable.
    *   **Use a Parameters File:** This is the most robust method. Create a JSON file (e.g., `cf-params.json`) and use `--parameters file://cf-params.json`.
*   **Resource Naming (Uniqueness):
    *   **S3 Buckets:** Names must be globally unique. Append `-${AWS::AccountId}` in the template: `!Sub "${ProjectName}-mybucket-${Environment}-${AWS::AccountId}"`.
    *   **IAM Roles:** Names must be unique within an account. Appending `-${AWS::AccountId}` is a good practice: `!Sub "${ProjectName}-myrole-${Environment}-${AWS::AccountId}"`.
*   **IAM Policy Resource ARNs:**
    *   **S3 Bucket Objects:** Ensure correct ARN format: `!Sub "arn:aws:s3:::${BucketNameRefOrName}/*"` or `!Join ['', ['arn:aws:s3:::', !Ref BucketLogicalId, '/*']]`.
    *   **S3 Bucket Itself:** Use `!GetAtt BucketLogicalId.Arn` for actions like `s3:ListBucket` on the bucket itself.
*   **Reserved Lambda Environment Variables:** Do not try to set `AWS_REGION` in the `Environment.Variables` section of a Lambda function in CloudFormation; it's a reserved variable automatically provided by the Lambda runtime.
*   **Debugging Failures (`ROLLBACK_COMPLETE`, `DELETE_FAILED`):
    *   **Check Stack Events:** This is the primary source of truth. Use `aws cloudformation describe-stack-events --stack-name YOUR_STACK_NAME --region YOUR_REGION` (ideally with the Zsh workaround for clean JSON output) and look for the first `CREATE_FAILED` or `UPDATE_FAILED` event to find the root cause.
    *   **S3 Buckets in `DELETE_FAILED` Stacks:** If a stack is in `DELETE_FAILED` because an S3 bucket with versioning is not empty, you must manually empty all object versions and delete markers from the bucket, then delete the bucket itself, before CloudFormation can successfully delete the stack.
        ```bash
        # Example to empty a versioned bucket (use with caution)
        BUCKET_NAME="your-bucket-name"
        aws s3api delete-objects --bucket $BUCKET_NAME --delete "$(aws s3api list-object-versions --bucket $BUCKET_NAME --query='{Objects: Versions[].{Key:Key,VersionId:VersionId}}' --output json)" --region YOUR_REGION
        aws s3api delete-objects --bucket $BUCKET_NAME --delete "$(aws s3api list-object-versions --bucket $BUCKET_NAME --query='{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' --output json)" --region YOUR_REGION
        aws s3 rb s3://$BUCKET_NAME --force --region YOUR_REGION
        ```

## 4. Lambda Function Packaging & Dependencies

*   **Python Imports in Lambda:**
    *   **Local `sys.path.append`:** Avoid `sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))` in Lambda handler code. This is for local testing.
    *   **Correct Packaging Structure:** When packaging, if you have a `shared` directory with common modules, copy it into the root of your Lambda deployment package (alongside `lambda_function.py`).
    *   **Correct Imports for Packaged Code:** In `lambda_function.py`, import using the package name: `from shared.dynamodb_service import ...`. Within modules inside the `shared` directory (e.g., `shared/dynamodb_service.py` importing `shared/config.py`), use relative imports: `from .config import config`.
*   **C-Extension Dependencies (e.g., `grpcio` for `google-generativeai`):
    *   **Problem:** `Runtime.ImportModuleError: ... cannot import name 'cygrpc' from 'grpc._cython'` indicates an incompatibility between the compiled C-extensions in the packaged `grpcio` and the Lambda (Amazon Linux) runtime.
    *   **Solution:** Ensure `pip install` fetches or builds wheels compatible with the Lambda environment (e.g., `manylinux` wheels for x86_64 architecture).
        *   Use `--no-cache-dir` with `pip install -r requirements.txt -t ./build_dir` to avoid local incompatible caches.
        *   More robustly, for `pip install` targeting the Lambda build directory:
            ```bash
            pip install --no-cache-dir -r requirements.txt -t ../build/lambda_package_dir/ \
                --index-url https://pypi.org/simple \
                --platform manylinux2014_x86_64 \
                --python-version 3.11 \
                --implementation cp \
                --abi cp311 \
                --only-binary=:all:
            ```
            (Adjust `manylinux` tag, Python version, and ABI as needed for your Lambda runtime.)
        *   Alternatively, build the entire package inside a Docker container that matches the Lambda runtime environment.
*   **Lambda Payload for Direct `invoke` CLI:**
    *   The `aws lambda invoke` CLI can be finicky with JSON string payloads. Providing the payload via `file:///tmp/payload.json` is generally more reliable.
    *   If you still get `Invalid base64` errors with `file://`, this indicates a persistent CLI/shell environment issue for direct invocation. However, if the Lambda works correctly when triggered by its actual event source (e.g., API Gateway, EventBridge), the core Lambda logic is sound.

## 5. API Rate Limiting

*   **Be Mindful:** When integrating with external APIs (Twitter, Google Gemini), be aware of their rate limits, especially on free or basic tiers.
*   **Testing Strategy:**
    *   Start tests with a minimal scope (e.g., 1 Twitter account) to isolate functionality from rate limit issues.
    *   Wait sufficiently between tests for rolling rate limit windows to reset.
    *   Check the respective developer portals for your current quota and usage.
*   **Production Code:** Implement proper rate limit handling (checking response headers, exponential backoff, queuing) for robust operation.

## 6. End-to-End Deployment Testing Lessons Learned

### Lambda Function Invocation Issues

**Problem:** Direct Lambda invocation using `aws lambda invoke` with JSON payloads often fails with encoding errors like:
```
Could not parse payload into json: Unexpected character ('²' (code 178))
Invalid base64: "{"source": "manual", "detail-type": "Manual Trigger"}"
```

**Root Cause:** Shell environment interference with JSON payload encoding, especially when using complex shell configurations (Oh My Zsh, custom profiles, etc.).

**Effective Solutions:**
1. **Use file-based payloads with clean shell execution:**
   ```bash
   echo '{"source": "manual"}' > /tmp/payload.json
   zsh -d -f -c "aws lambda invoke --function-name FUNCTION_NAME --payload file:///tmp/payload.json --region REGION --profile PROFILE /tmp/response.json | cat"
   ```

2. **Use the `--cli-binary-format raw-in-base64-out` flag:**
   ```bash
   AWS_PROFILE=profile aws lambda invoke --function-name FUNCTION_NAME --payload file:///tmp/payload.json --region REGION /tmp/response.json --cli-binary-format raw-in-base64-out
   ```

3. **Alternative: Use EventBridge for scheduled functions:**
   ```bash
   zsh -d -f -c "aws events put-events --entries '[{\"Source\": \"manual.trigger\", \"DetailType\": \"Manual Test\", \"Detail\": \"{\\\"test\\\": true}\"}]' --region REGION --profile PROFILE | cat"
   ```

### Amazon SES Email Verification Requirements

**Problem:** Lambda functions attempting to send emails fail with:
```
MessageRejected: Email address is not verified. The following identities failed the check in region US-EAST-1: recipient@example.com, noreply@example.com
```

**Root Cause:** Amazon SES operates in "sandbox mode" by default, requiring verification of both sender and recipient email addresses.

**Solutions:**
1. **Verify sender email address in SES console:**
   ```bash
   aws ses verify-email-identity --email-address noreply@yourdomain.com --region us-east-1
   ```

2. **For testing, verify recipient emails individually:**
   ```bash
   aws ses verify-email-identity --email-address test@example.com --region us-east-1
   ```

3. **For production, request SES production access** to send to any email address without verification.

4. **Check verification status:**
   ```bash
   aws ses get-identity-verification-attributes --identities noreply@yourdomain.com --region us-east-1
   ```

### Frontend Deployment to S3/CloudFront

**Problem:** Static website not accessible after CloudFormation deployment, returning 403 Access Denied errors.

**Root Cause:** Frontend files not uploaded to S3 bucket, or incorrect API configuration.

**Solution Process:**
1. **Build the frontend:**
   ```bash
   ./scripts/setup-frontend.sh
   ```

2. **Update API configuration:**
   ```bash
   # Edit frontend-static/config.js with actual API Gateway URL
   API_BASE_URL: 'https://your-api-id.execute-api.region.amazonaws.com/stage'
   ```

3. **Upload to S3:**
   ```bash
   aws s3 sync frontend-static/out/ s3://website-bucket-name/ --profile PROFILE --delete
   aws s3 cp frontend-static/config.js s3://website-bucket-name/config.js --profile PROFILE
   ```

4. **Verify deployment:**
   ```bash
   curl -s https://cloudfront-distribution-url/config.js
   ```

### Real-World Testing Workflow

**Effective End-to-End Testing Process:**

1. **Verify Infrastructure:**
   ```bash
   ./scripts/e2e-test.sh --infrastructure-only
   ```

2. **Test Individual Components:**
   ```bash
   ./scripts/e2e-test.sh --functional-only
   ```

3. **Deploy and Configure Frontend:**
   ```bash
   ./scripts/setup-frontend.sh
   # Update config.js with real API URLs
   aws s3 sync frontend-static/out/ s3://bucket/ --delete
   ```

4. **Test Subscription Flow:**
   ```bash
   curl -X POST https://api-url/subscribe -H "Content-Type: application/json" -d '{"email": "test@example.com"}'
   ```

5. **Trigger Digest Generation:**
   ```bash
   # Use clean shell execution for Lambda invocation
   echo '{}' > /tmp/payload.json
   AWS_PROFILE=profile aws lambda invoke --function-name digest-function --payload file:///tmp/payload.json --region region /tmp/response.json --cli-binary-format raw-in-base64-out
   ```

6. **Monitor Execution:**
   ```bash
   # Check CloudWatch logs
   aws logs describe-log-streams --log-group-name '/aws/lambda/function-name' --order-by LastEventTime --descending --max-items 1
   aws logs get-log-events --log-group-name '/aws/lambda/function-name' --log-stream-name 'stream-name'
   ```

7. **Verify Results:**
   ```bash
   # Check generated digest
   aws s3 cp s3://data-bucket/tweets/digests/latest-digest.json /tmp/digest.json
   cat /tmp/digest.json | jq '.summaries'
   ```

### Configuration Management Best Practices

**Upload Configuration Files:**
```bash
aws s3 cp data/accounts.json s3://data-bucket/config/accounts.json --profile PROFILE
```

**Verify Configuration:**
```bash
aws s3 cp s3://data-bucket/config/accounts.json /tmp/verify.json --profile PROFILE
cat /tmp/verify.json
```

**Update Configuration for Testing:**
```json
{
  "influential_accounts": ["OpenAI", "AndrewYNg", "ClaudeAI"],
  "max_tweets_per_account": 10,
  "days_back": 14
}
```

### Debugging Lambda Execution

**Check Function Configuration:**
```bash
aws lambda get-function-configuration --function-name FUNCTION_NAME --query 'Environment.Variables'
```

**Monitor Real-Time Logs:**
```bash
# Get latest log stream
LATEST_STREAM=$(aws logs describe-log-streams --log-group-name '/aws/lambda/function-name' --order-by LastEventTime --descending --max-items 1 --query 'logStreams[0].logStreamName' --output text)

# Get log events
aws logs get-log-events --log-group-name '/aws/lambda/function-name' --log-stream-name "$LATEST_STREAM"
```

**Verify Function Response:**
```bash
# Check response file after invocation
cat /tmp/response.json | jq .
```

### CloudFront Cache Management and Frontend Deployment Issues

**Problem:** After deploying updated frontend files to S3, CloudFront continues serving old cached versions, causing users to see outdated JavaScript with incorrect error handling or missing features.

**Root Cause:** CloudFront caches static assets (JavaScript, CSS, images) for performance. When files are updated in S3, CloudFront doesn't automatically serve the new versions until the cache expires or is manually invalidated.

**Symptoms:**
- Website shows old error messages or behavior after frontend updates
- New JavaScript files return 404 errors when accessed directly
- Browser developer tools show old file hashes in network requests

**Solutions:**

1. **Find CloudFront Distribution ID:**
   ```bash
   # Method 1: From CloudFormation outputs (if available)
   aws cloudformation describe-stacks --stack-name STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' --output text

   # Method 2: By matching domain name
   zsh -d -f -c "aws cloudfront list-distributions --profile PROFILE --query 'DistributionList.Items[?DomainName==\`your-domain.cloudfront.net\`].Id' --output text | cat"
   ```

2. **Create CloudFront Invalidation:**
   ```bash
   # Invalidate all files (use sparingly due to cost)
   zsh -d -f -c "aws cloudfront create-invalidation --distribution-id DISTRIBUTION_ID --paths '/*' --profile PROFILE | cat"

   # Invalidate specific paths (more cost-effective)
   zsh -d -f -c "aws cloudfront create-invalidation --distribution-id DISTRIBUTION_ID --paths '/_next/static/*' '/config.js' --profile PROFILE | cat"
   ```

3. **Monitor Invalidation Status:**
   ```bash
   zsh -d -f -c "aws cloudfront get-invalidation --distribution-id DISTRIBUTION_ID --id INVALIDATION_ID --profile PROFILE --query 'Invalidation.Status' --output text | cat"
   ```

4. **Verify New Files Are Served:**
   ```bash
   # Check if new JavaScript files are accessible
   curl -s "https://your-domain.cloudfront.net/_next/static/chunks/app/page-HASH.js" | wc -l

   # Verify config.js is updated
   curl -s "https://your-domain.cloudfront.net/config.js"
   ```

**Best Practices:**
- **Always invalidate after frontend deployments** that change JavaScript logic
- **Use specific paths** instead of `/*` to minimize invalidation costs
- **Wait for invalidation completion** before testing (typically 1-3 minutes)
- **Consider versioned file names** in build process to avoid cache issues

### Frontend Error Handling and API Integration Issues

**Problem:** Frontend shows generic "Something went wrong" messages instead of specific API error responses, making it difficult for users to understand what action to take.

**Root Cause:** Frontend error handling logic overrides API service error messages with hardcoded fallback messages, ignoring the specific status codes and messages returned by the backend.

**Common Symptoms:**
- All errors show "Something went wrong. Please try again."
- Duplicate email submissions show generic error instead of "Email already subscribed"
- Invalid email formats show generic error instead of validation message

**Debugging Process:**

1. **Test API Directly:**
   ```bash
   # Test successful subscription
   curl -X POST https://api-url/subscribe -H "Content-Type: application/json" -d '{"email": "new@example.com"}' -v

   # Test duplicate subscription
   curl -X POST https://api-url/subscribe -H "Content-Type: application/json" -d '{"email": "new@example.com"}' -v

   # Test invalid email
   curl -X POST https://api-url/subscribe -H "Content-Type: application/json" -d '{"email": "invalid-email"}' -v
   ```

2. **Verify API Service Configuration:**
   ```bash
   # Check if config.js is properly loaded
   curl -s https://cloudfront-url/config.js

   # Verify API service in built JavaScript
   curl -s "https://cloudfront-url/_next/static/chunks/app/page-HASH.js" | grep -o "API_BASE_URL"
   ```

3. **Check for File Conflicts:**
   ```bash
   # List API service files to check for conflicts
   ls -la frontend-static/src/utils/api.*
   
   # Remove conflicting TypeScript files if using JavaScript
   rm -f frontend-static/src/utils/api.ts
   ```

**Solution Pattern:**

1. **API Service Should Handle Status Codes:**
   ```javascript
   // In api.js - Handle specific status codes and return appropriate messages
   if (!response.ok) {
     let errorMessage = data.message || data.error || 'Subscription failed';
     
     if (response.status === 422) {
       errorMessage = 'Please enter a valid email address';
     } else if (response.status === 409) {
       errorMessage = data.message || 'Email already subscribed to weekly digest';
     } else if (response.status === 400) {
       errorMessage = 'Please enter a valid email address';
     }
     
     const error = new Error(errorMessage);
     error.status = response.status;
     throw error;
   }
   ```

2. **Frontend Should Use API Messages:**
   ```javascript
   // In EmailSignup component - Use actual error messages from API service
   catch (error) {
     if (error instanceof Error) {
       // Use the actual error message from the API service
       setMessage(error.message);
     } else {
       setMessage('Something went wrong. Please try again.');
     }
   }
   ```

3. **Avoid Complex Override Logic:**
   ```javascript
   // AVOID: Complex logic that ignores API messages
   if (status === 409 || errorMessage.includes('already subscribed')) {
     setMessage('Email already subscribed to weekly digest');
   } else if (status === 422 || errorMessage.includes('Validation error')) {
     setMessage('Please enter a valid email address');
   } else {
     setMessage('Something went wrong. Please try again.');
   }

   // PREFER: Simple logic that trusts API messages
   setMessage(errorMessage);
   ```

**Deployment Workflow for Frontend Changes:**

1. **Make Changes and Remove Conflicts:**
   ```bash
   # Remove any conflicting files
   rm -f frontend-static/src/utils/api.ts
   ```

2. **Rebuild Frontend:**
   ```bash
   cd frontend-static && npm run build
   ```

3. **Deploy to S3:**
   ```bash
   aws s3 sync frontend-static/out/ s3://bucket-name/ --profile PROFILE --delete
   aws s3 cp frontend-static/config.js s3://bucket-name/config.js --profile PROFILE
   ```

4. **Invalidate CloudFront Cache:**
   ```bash
   zsh -d -f -c "aws cloudfront create-invalidation --distribution-id DISTRIBUTION_ID --paths '/*' --profile PROFILE | cat"
   ```

5. **Wait and Verify:**
   ```bash
   # Wait for invalidation to complete
   zsh -d -f -c "aws cloudfront get-invalidation --distribution-id DISTRIBUTION_ID --id INVALIDATION_ID --profile PROFILE --query 'Invalidation.Status' --output text | cat"

   # Test the website with different scenarios
   ```

## 7. Email Verification System Implementation Lessons Learned

### Lambda Function Packaging for Email Verification

**Problem:** Email verification Lambda functions require minimal dependencies but were being packaged with heavy dependencies like `google-generativeai` and `grpcio`, causing package sizes to exceed Lambda's 50MB direct upload limit.

**Root Cause:** Using the same `requirements.txt` for all Lambda functions, regardless of their actual dependencies.

**Solution:** Create function-specific requirements files for minimal dependency packaging:

```bash
# Create minimal requirements for email verification
# lambdas/email-verification-requirements.txt
boto3>=1.34.0
botocore>=1.34.0

# Package with minimal dependencies
cd lambdas
pip install --index-url https://pypi.org/simple -r email-verification-requirements.txt -t build/email-verification/
cp -r shared build/email-verification/
cp email-verification/lambda_function.py build/email-verification/
cd build/email-verification
zip -r ../../email-verification-function.zip . > /dev/null
```

**Results:**
- Email verification package reduced from 51MB to 15MB
- Successful direct Lambda function updates without S3 staging
- Faster deployment times for lightweight functions

### CloudFormation Template Updates for New Lambda Functions

**Problem:** Adding new Lambda functions to existing CloudFormation stacks requires careful dependency management and API Gateway deployment updates.

**Key Requirements:**
1. **Add Lambda Function Resource:**
   ```yaml
   EmailVerificationFunction:
     Type: AWS::Lambda::Function
     Properties:
       FunctionName: !Sub "${ProjectName}-email-verification-${Environment}"
       # ... other properties
   ```

2. **Add API Gateway Resources:**
   ```yaml
   VerifyResource:
     Type: AWS::ApiGateway::Resource
     Properties:
       PathPart: verify
   
   VerifyMethod:
     Type: AWS::ApiGateway::Method
     Properties:
       HttpMethod: GET
       # ... integration with Lambda
   ```

3. **Update API Gateway Deployment Dependencies:**
   ```yaml
   ApiDeployment:
     Type: AWS::ApiGateway::Deployment
     DependsOn:
       - SubscriptionMethod
       - SubscriptionOptionsMethod
       - VerifyMethod  # Add new method here
   ```

4. **Add Lambda Permissions:**
   ```yaml
   EmailVerificationLambdaPermission:
     Type: AWS::Lambda::Permission
     Properties:
       FunctionName: !Ref EmailVerificationFunction
       Action: lambda:InvokeFunction
       Principal: apigateway.amazonaws.com
   ```

**Critical Step:** After CloudFormation update, create new API Gateway deployment:
```bash
zsh -d -f -c "aws apigateway create-deployment --rest-api-id API_ID --stage-name production --region us-east-1 | cat"
```

### Environment Variable Management for Lambda Functions

**Problem:** Different Lambda functions require different environment variables, but shared configuration validation was checking for all variables in all functions.

**Solution Approaches:**

1. **Function-Specific Environment Variables:**
   ```bash
   # Email verification function needs minimal variables
   aws lambda update-function-configuration \
     --function-name email-verification-function \
     --environment 'Variables={
       SUBSCRIBERS_TABLE=table-name,
       FROM_EMAIL=sender@domain.com,
       ENVIRONMENT=production
     }'
   ```

2. **Conditional Configuration Validation:**
   ```python
   # In shared/config.py - make validation function-aware
   def validate_required_env_vars(function_type=None):
       if function_type == 'email_verification':
           required = ['SUBSCRIBERS_TABLE', 'FROM_EMAIL', 'ENVIRONMENT']
       else:
           required = ['TWITTER_BEARER_TOKEN', 'GEMINI_API_KEY', ...]
   ```

3. **Provide All Variables for Simplicity:**
   ```bash
   # Simpler approach: provide all variables to all functions
   # Even if not used, avoids configuration complexity
   ```

### Lambda Function Code Updates via S3

**Problem:** Large Lambda packages (>50MB) cannot be updated directly and must be uploaded via S3.

**Effective Workflow:**
```bash
# 1. Upload package to S3
zsh -d -f -c "aws s3 cp function.zip s3://data-bucket/lambda-packages/function.zip --region us-east-1 | cat"

# 2. Update Lambda function from S3
zsh -d -f -c "aws lambda update-function-code --function-name FUNCTION_NAME --s3-bucket data-bucket --s3-key lambda-packages/function.zip --region us-east-1 | cat"

# 3. Verify update
zsh -d -f -c "aws lambda get-function --function-name FUNCTION_NAME --query 'Configuration.LastModified' --output text | cat"
```

### SES Email Verification for Testing

**Problem:** Amazon SES requires verification of both sender and recipient emails in sandbox mode, causing email verification testing to fail.

**Testing Workflow:**
```bash
# 1. Verify sender email
aws ses verify-email-identity --email-address sender@domain.com --region us-east-1

# 2. Check verification status
aws ses get-identity-verification-attributes --identities sender@domain.com --region us-east-1

# 3. For testing, verify recipient emails too
aws ses verify-email-identity --email-address test@domain.com --region us-east-1

# 4. List all verified identities
aws ses list-identities --region us-east-1
```

**Production Considerations:**
- Request SES production access to send to unverified recipients
- Set up SPF, DKIM, and DMARC records for better deliverability
- Monitor bounce and complaint rates

### API Gateway Method Integration Issues

**Problem:** New API Gateway methods may not be accessible immediately after CloudFormation deployment due to deployment timing.

**Symptoms:**
- `curl` requests return "Missing Authentication Token"
- API Gateway console shows method exists but returns 403/404

**Solution:**
```bash
# Force new API Gateway deployment after CloudFormation update
API_ID=$(aws cloudformation describe-stacks --stack-name STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayId`].OutputValue' --output text)

zsh -d -f -c "aws apigateway create-deployment --rest-api-id $API_ID --stage-name production --region us-east-1 | cat"

# Verify deployment
zsh -d -f -c "aws apigateway get-deployments --rest-api-id $API_ID --region us-east-1 --query 'items[0].createdDate' --output text | cat"
```

### Virtual Environment and Package Management

**Critical Practice:** Always activate virtual environment and use correct PyPI index:

```bash
# 1. Activate virtual environment
source .venv311/bin/activate

# 2. Install with correct index
pip install --index-url https://pypi.org/simple package-name

# 3. Verify environment
which python
pip list | grep package-name
```

**Deployment Script Integration:**
```bash
# In deployment scripts, ensure clean environment
source .venv311/bin/activate
pip install --index-url https://pypi.org/simple -r requirements.txt -t build/
```

By applying these learnings, deployments become smoother, and troubleshooting is more effective. 