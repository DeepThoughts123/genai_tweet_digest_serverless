# Deployment Workarounds and Key Learnings

This document outlines the key challenges encountered and the successful workarounds found during the deployment of the GenAI Tweets Digest serverless infrastructure, particularly concerning shell environment issues, AWS CloudFormation, and the critical deployment pitfalls discovered during production deployments.

## 1. CloudFormation Stack Deletion and S3 Cleanup

### Problem: Stack Stuck in DELETE_FAILED State

**Scenario:** CloudFormation stack fails to delete with error message "The following resource(s) failed to delete: [DataBucket, WebsiteBucket]" and remains in DELETE_FAILED state.

**Root Cause:** S3 buckets cannot be deleted by CloudFormation if they contain any objects, including object versions and delete markers when versioning is enabled.

### Complete Stack Deletion Process

**⚠️ IMPORTANT: Always backup data before deletion if you want to preserve it**

#### Step 1: Check S3 Bucket Contents and Backup Data
```bash
# Set your AWS profile and bucket names
export AWS_PROFILE=personal
DATA_BUCKET="genai-tweets-digest-data-production-855450210814"
WEBSITE_BUCKET="genai-tweets-digest-website-production-855450210814"

# Check what's in the buckets before deletion
echo "=== Data Bucket Contents ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 ls s3://$DATA_BUCKET --recursive | cat"

echo "=== Website Bucket Contents ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 ls s3://$WEBSITE_BUCKET --recursive | cat"

# Optional: Backup important data
mkdir -p ./backup-$(date +%Y%m%d)
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 sync s3://$DATA_BUCKET/tweets/ ./backup-$(date +%Y%m%d)/tweets/ | cat"
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 sync s3://$DATA_BUCKET/config/ ./backup-$(date +%Y%m%d)/config/ | cat"
```

#### Step 2: Empty S3 Buckets Completely
```bash
# Empty data bucket (including all object versions and delete markers)
echo "Emptying data bucket..."
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 rm s3://$DATA_BUCKET --recursive | cat"

# For versioned buckets, also remove all versions and delete markers
zsh -d -f -c "export AWS_PROFILE=personal && aws s3api delete-objects --bucket $DATA_BUCKET --delete \"\$(aws s3api list-object-versions --bucket $DATA_BUCKET --query='{Objects: Versions[].{Key:Key,VersionId:VersionId}}')\" 2>/dev/null || echo 'No versions to delete' | cat"

zsh -d -f -c "export AWS_PROFILE=personal && aws s3api delete-objects --bucket $DATA_BUCKET --delete \"\$(aws s3api list-object-versions --bucket $DATA_BUCKET --query='{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}')\" 2>/dev/null || echo 'No delete markers' | cat"

# Empty website bucket
echo "Emptying website bucket..."
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 rm s3://$WEBSITE_BUCKET --recursive | cat"
```

#### Step 3: Delete Buckets Manually (if needed)
```bash
# Try to delete the buckets manually
echo "Deleting data bucket..."
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 rb s3://$DATA_BUCKET | cat"

echo "Deleting website bucket..."
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 rb s3://$WEBSITE_BUCKET | cat"
```

#### Step 4: Complete Stack Deletion
```bash
# Now delete the CloudFormation stack
STACK_NAME="genai-tweets-digest-production"
echo "Deleting CloudFormation stack..."
zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation delete-stack --stack-name $STACK_NAME --region us-east-1 | cat"

# Wait for deletion to complete
echo "Waiting for stack deletion to complete..."
zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME --region us-east-1 | cat"

# Verify stack is gone
zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation describe-stacks --stack-name $STACK_NAME --region us-east-1 2>/dev/null && echo 'Stack still exists' || echo 'Stack successfully deleted' | cat"
```

### Verification Commands

```bash
# Check if any resources remain
echo "Checking for remaining S3 buckets..."
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 ls | grep genai-tweets-digest | cat"

echo "Checking for remaining Lambda functions..."
zsh -d -f -c "export AWS_PROFILE=personal && aws lambda list-functions --query 'Functions[?starts_with(FunctionName, \`genai-tweets-digest\`)].FunctionName' --output table --region us-east-1 | cat"

echo "Checking for remaining DynamoDB tables..."
zsh -d -f -c "export AWS_PROFILE=personal && aws dynamodb list-tables --query 'TableNames[?starts_with(@, \`genai-tweets-digest\`)]' --output table --region us-east-1 | cat"
```

## 2. Lambda Package Size Optimization

### Problem: Lambda Function Package Size Limits

**Size Limits:**
- Direct upload (zip file): 50MB
- Unzipped package: 250MB  
- S3 upload: 250MB unzipped

**Common Issues:**
- `google-generativeai` with `grpcio` dependencies create 150MB+ packages
- `botocore` includes data for all AWS services (20MB+)
- Multiple functions packaging identical dependencies

### Solution 1: Function-Specific Minimal Packaging

**For Simple Functions (Subscription, Email Verification):**
```bash
cd lambdas

# Create minimal requirements (boto3 only)
echo "Building subscription function with minimal dependencies..."
rm -rf build/subscription
mkdir -p build/subscription

# Install only essential dependencies
pip install 'boto3>=1.34.0' -t build/subscription/ \
    --index-url https://pypi.org/simple \
    --only-binary=:all:

# Copy function code
cp -r shared build/subscription/
cp subscription/lambda_function.py build/subscription/

# Package (results in ~15MB)
cd build/subscription
zip -r ../../subscription-function.zip . > /dev/null
cd ../../
ls -lh subscription-function.zip  # Should show ~15MB
```

**For AI-Heavy Functions (Weekly Digest):**
```bash
echo "Building weekly digest function with optimized dependencies..."
rm -rf build/weekly-digest
mkdir -p build/weekly-digest

# Use manylinux wheels to reduce grpcio size
pip install --no-cache-dir -r requirements.txt -t build/weekly-digest/ \
    --index-url https://pypi.org/simple \
    --platform manylinux2014_x86_64 \
    --python-version 3.11 \
    --implementation cp \
    --abi cp311 \
    --only-binary=:all:

# Copy function code
cp -r shared build/weekly-digest/
cp weekly-digest/lambda_function.py build/weekly-digest/

# Package (results in ~46MB instead of 150MB+)
cd build/weekly-digest
zip -r ../../weekly-digest-function.zip . > /dev/null
cd ../../
ls -lh weekly-digest-function.zip  # Should show ~46MB
```

### Solution 2: S3-Based Deployment for Large Packages

**For packages >50MB:**
```bash
# Upload to S3 first
DATA_BUCKET="genai-tweets-digest-data-production-855450210814"
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 cp lambdas/weekly-digest-function.zip s3://$DATA_BUCKET/lambda-packages/weekly-digest-function.zip | cat"

# Update Lambda function from S3
zsh -d -f -c "export AWS_PROFILE=personal && aws lambda update-function-code --function-name genai-tweets-digest-weekly-digest-production --s3-bucket $DATA_BUCKET --s3-key lambda-packages/weekly-digest-function.zip --region us-east-1 | cat"
```

### Package Size Verification

```bash
# Check current function code size
zsh -d -f -c "export AWS_PROFILE=personal && aws lambda get-function --function-name genai-tweets-digest-weekly-digest-production --query 'Configuration.CodeSize' --region us-east-1 | cat"

# Check unzipped size locally
unzip -l weekly-digest-function.zip | tail -1
```

## 3. SES Email Configuration Issues

### Problem: Missing Environment Variables Causing Email Failures

**Common Error:**
```
An error occurred (MessageRejected) when calling the SendEmail operation: 
Email address is not verified. The following identities failed the check: 
test@example.com, digest@genai-tweets.com
```

**Root Causes:**
1. Missing `FROM_EMAIL` environment variable in Lambda functions
2. Using unverified sender/recipient email addresses in SES sandbox mode
3. Hardcoded email addresses in code instead of using environment variables

### Solution: Complete SES Configuration

#### Step 1: Verify Email Addresses in SES
```bash
# Verify the sender email address
zsh -d -f -c "export AWS_PROFILE=personal && aws ses verify-email-identity --email-address dnn12521@gmail.com --region us-east-1 | cat"

# For testing: verify recipient email addresses  
zsh -d -f -c "export AWS_PROFILE=personal && aws ses verify-email-identity --email-address test@example.com --region us-east-1 | cat"

# Check verification status
zsh -d -f -c "export AWS_PROFILE=personal && aws ses list-identities --region us-east-1 | cat"
```

#### Step 2: Update Lambda Environment Variables

**For all email-related functions, ensure these environment variables are set:**

```bash
# Update subscription function
zsh -d -f -c "export AWS_PROFILE=personal && aws lambda update-function-configuration --function-name genai-tweets-digest-subscription-production --environment Variables='{S3_BUCKET=genai-tweets-digest-data-production-855450210814,TWITTER_BEARER_TOKEN=YOUR_TOKEN,GEMINI_API_KEY=YOUR_KEY,ENVIRONMENT=production,SUBSCRIBERS_TABLE=genai-tweets-digest-subscribers-production,FROM_EMAIL=dnn12521@gmail.com,TO_EMAIL=dnn12521@gmail.com,API_BASE_URL=https://whkkx3sqe8.execute-api.us-east-1.amazonaws.com/production}' --region us-east-1 | cat"

# Update weekly digest function  
zsh -d -f -c "export AWS_PROFILE=personal && aws lambda update-function-configuration --function-name genai-tweets-digest-weekly-digest-production --environment Variables='{S3_BUCKET=genai-tweets-digest-data-production-855450210814,TWITTER_BEARER_TOKEN=YOUR_TOKEN,GEMINI_API_KEY=YOUR_KEY,ENVIRONMENT=production,SUBSCRIBERS_TABLE=genai-tweets-digest-subscribers-production,FROM_EMAIL=dnn12521@gmail.com,TO_EMAIL=dnn12521@gmail.com,API_BASE_URL=https://whkkx3sqe8.execute-api.us-east-1.amazonaws.com/production}' --region us-east-1 | cat"
```

#### Step 3: Environment Variable Best Practices

**Create .env file for local development:**
```bash
# .env file (add to .gitignore)
AWS_PROFILE=personal
AWS_REGION=us-east-1
ENVIRONMENT=production
TWITTER_BEARER_TOKEN=your_twitter_bearer_token
GEMINI_API_KEY=your_gemini_api_key
FROM_EMAIL=your_verified_ses_email@domain.com
TO_EMAIL=your_verified_ses_email@domain.com  # For testing in sandbox mode
```

**Verify Environment Variables:**
```bash
# Check if all required variables are set in Lambda
zsh -d -f -c "export AWS_PROFILE=personal && aws lambda get-function-configuration --function-name genai-tweets-digest-subscription-production --region us-east-1 --query 'Environment.Variables' | cat"
```

#### Step 4: Test Email Functionality

```bash
# Test subscription API with verified email
API_URL="https://whkkx3sqe8.execute-api.us-east-1.amazonaws.com/production/subscribe"
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"email": "dnn12521@gmail.com"}' \
  -w '\nStatus: %{http_code}\n'

# Expected successful response:
# {"success": true, "message": "Verification email sent. Please check your inbox.", "subscriber_id": "uuid"}
# Status: 201
```

### SES Sandbox vs Production Mode

**Sandbox Mode (Default):**
- Can only send to verified email addresses
- Both sender AND recipient must be verified
- Good for testing

**Production Mode:**
- Can send to any email address  
- Only sender needs to be verified
- Requires AWS support request

**Request Production Access:**
```bash
# Check current sending quota (sandbox = 200 emails/day)
zsh -d -f -c "export AWS_PROFILE=personal && aws ses get-send-quota --region us-east-1 | cat"
```

## 4. Shell Output Issues with AWS CLI

**Problem:** AWS CLI commands, especially those intended to output JSON (e.g., `aws cloudformation describe-stacks --output json`), were having their output incorrectly piped or processed, resulting in errors like `head: |: No such file or directory` or `head: cat: No such file or directory`. This masked the actual success or failure of the commands and their JSON responses.

**Root Cause:** Determined to be related to custom configurations in the user's Zsh startup files (`~/.zshrc`, Oh My Zsh, or a sourced Instacart-specific shell profile) that interfered with default output handling or pager invocation by the AWS CLI.

**Workaround:** Execute AWS CLI commands within a temporarily clean Zsh environment that bypasses most custom startup scripts. The command is wrapped as follows, with an explicit pipe to `cat` to ensure the output is displayed:

```bash
zsh -d -f -c "YOUR_AWS_COMMAND_HERE --output json | cat"
```

For commands that don't inherently produce JSON or where we just need to ensure execution without mangled output (like `delete-stack`), `| cat` might not be strictly necessary but doesn't hurt:

```bash
zsh -d -f -c "YOUR_AWS_COMMAND_HERE"
```

**Note:** While temporarily commenting out `source /Users/jeffwu/.instacart_shell_profile` in `~/.zshrc` was attempted, it did not fully resolve the issue, suggesting other Zsh configurations were also at play.

## 5. AWS CloudFormation Stack Creation Issues

Several issues were encountered when trying to create the CloudFormation stack:

*   **Globally Unique S3 Bucket Names:** Initial failures occurred because S3 bucket names must be globally unique. A previously rolled-back stack might leave a bucket that prevents a new stack from creating a bucket with the same name.
    *   **Fix:** Modified `BucketName` properties in `infrastructure-aws/cloudformation-template.yaml` for `DataBucket` and `WebsiteBucket` to append `${AWS::AccountId}` making them globally unique: `!Sub "${ProjectName}-data-${Environment}-${AWS::AccountId}"`.

*   **IAM Role Name Uniqueness:** Similarly, IAM role names need to be unique within an account.
    *   **Fix:** Modified `RoleName` for `LambdaExecutionRole` to `!Sub "${ProjectName}-lambda-role-${Environment}-${AWS::AccountId}"`.

*   **Invalid S3 Resource ARN in IAM Policy:** The `LambdaExecutionRole` had an S3 resource specified incorrectly.
    *   **Error:** "Resource `BUCKET_NAME/*` must be in ARN format or '*'".
    *   **Fix:** Ensured the S3 `Resource` in the IAM policy for `s3:GetObject`, `s3:PutObject`, etc., used the full ARN format: `!Sub "arn:aws:s3:::${DataBucket}/*"`.

*   **Reserved Lambda Environment Variable:** The template attempted to set `AWS_REGION` as an environment variable for Lambda functions.
    *   **Error:** "Lambda was unable to configure your environment variables because the environment variables you have provided contains reserved keys... Reserved keys used in this request: AWS_REGION".
    *   **Fix:** Removed the `AWS_REGION: !Ref AWS::Region` line from the `Environment.Variables` section of both Lambda function definitions in the CloudFormation template.

*   **Invalid Resource in S3 Bucket Policy:** The `WebsiteBucketPolicy` had an invalid `Resource` ARN.
    *   **Error:** "Policy has invalid resource".
    *   **Initial Fix Attempt:** Changed `Resource: !Sub "${WebsiteBucket}/*"` to `Resource: !Sub "arn:aws:s3:::${ProjectName}-website-${Environment}-${AWS::AccountId}/*"`.
    *   **Further Refinement (More Robust):** Changed to `Resource: !Join ['', ['arn:aws:s3:::', !Ref WebsiteBucket, '/*']]`.
    *   **Final Working Version (Simpler Sub):** Reverted to `Resource: !Sub "arn:aws:s3:::${WebsiteBucket}/*"` (This worked once `${WebsiteBucket}` itself correctly resolved to the globally unique name).

*   **Passing Parameters to `create-stack`:** Long command lines with many parameters, especially API keys, were failing silently or being misinterpreted by the local shell.
    *   **Fix:** Used a JSON parameters file (`cf-params.json`) with the `aws cloudformation create-stack --parameters file://cf-params.json` option. This proved much more reliable.

## 6. Successful Deployment Strategy (Summary)

The combination that finally led to successful stack initiation was:

1.  **Corrected CloudFormation Template (`infrastructure-aws/cloudformation-template.yaml`):**
    *   Globally unique S3 bucket names (appended `-${AWS::AccountId}`).
    *   Account-unique IAM Role name (appended `-${AWS::AccountId}`).
    *   Correct S3 ARN format in IAM policies (`arn:aws:s3:::${DataBucket}/*`).
    *   Removed reserved `AWS_REGION` from Lambda environment variables.
    *   Correct `Resource` ARN in `WebsiteBucketPolicy` (`!Sub "arn:aws:s3:::${WebsiteBucket}/*"` where `WebsiteBucket` refers to the unique bucket name).
2.  **Parameters File (`cf-params.json`):** Used to pass all stack parameters cleanly.
    ```json
    [
      {
        "ParameterKey": "ProjectName",
        "ParameterValue": "genai-tweets-digest"
      },
      {
        "ParameterKey": "Environment",
        "ParameterValue": "production"
      },
      {
        "ParameterKey": "TwitterBearerToken",
        "ParameterValue": "YOUR_ACTUAL_TWITTER_TOKEN"
      },
      {
        "ParameterKey": "GeminiApiKey",
        "ParameterValue": "YOUR_ACTUAL_GEMINI_KEY"
      },
      {
        "ParameterKey": "FromEmail",
        "ParameterValue": "your_verified_ses_email@domain.com"
      }
    ]
    ```
3.  **Zsh Workaround for AWS CLI Execution:** Wrapped the `aws cloudformation create-stack` command (and subsequent `wait` or `describe-stack-events` commands) to bypass local shell interference and ensure clean output.
    ```bash
    export AWS_PROFILE=personal && \
    STACK_NAME="genai-tweets-digest-$(date +%Y%m%d-%H%M%S)" && \
    echo "Attempting to create stack: $STACK_NAME ..." && \
    zsh -d -f -c "aws cloudformation create-stack --stack-name $STACK_NAME --template-body file://infrastructure-aws/cloudformation-template.yaml --parameters file://cf-params.json --capabilities CAPABILITY_NAMED_IAM --region us-east-1 --output json | cat > cf-create-status.json" && \
    cat cf-create-status.json
    ```

This approach ensures that the CloudFormation template is correct and that the parameters and the AWS CLI command itself are processed reliably.

## 7. Quick Reference: Common Deployment Commands

### Environment Setup
```bash
export AWS_PROFILE=personal
export AWS_REGION=us-east-1
export ENVIRONMENT=production
```

### Stack Management
```bash
# Deploy new stack
./scripts/deploy.sh

# Check stack status
zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation describe-stacks --stack-name genai-tweets-digest-production --region us-east-1 --query 'Stacks[0].StackStatus' --output text | cat"

# Get stack outputs
zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation describe-stacks --stack-name genai-tweets-digest-production --region us-east-1 --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' --output table | cat"
```

### Lambda Function Management
```bash
# Update function code (for large packages)
zsh -d -f -c "export AWS_PROFILE=personal && aws lambda update-function-code --function-name genai-tweets-digest-weekly-digest-production --s3-bucket genai-tweets-digest-data-production-855450210814 --s3-key lambda-packages/weekly-digest-function.zip --region us-east-1 | cat"

# Check function status
zsh -d -f -c "export AWS_PROFILE=personal && aws lambda get-function --function-name genai-tweets-digest-subscription-production --query 'Configuration.LastUpdateStatus' --region us-east-1 --output text | cat"

# View function logs
zsh -d -f -c "export AWS_PROFILE=personal && aws logs tail /aws/lambda/genai-tweets-digest-subscription-production --since 10m --region us-east-1 | cat"
```

### Testing Commands
```bash
# Test subscription API
curl -X POST https://whkkx3sqe8.execute-api.us-east-1.amazonaws.com/production/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}' \
  -w '\nStatus: %{http_code}\n'

# Test weekly digest (manual trigger)
echo '{"source": "manual", "detail-type": "Manual Trigger"}' > /tmp/digest_payload.json
zsh -d -f -c "export AWS_PROFILE=personal && aws lambda invoke --function-name genai-tweets-digest-weekly-digest-production --payload file:///tmp/digest_payload.json --region us-east-1 /tmp/digest_response.json --cli-binary-format raw-in-base64-out | cat"
```

## 8. CloudFormation Naming Conflicts (Critical for Parallel Stacks)

### Problem: Stack Creation Fails with "already exists" or "Export ... already exported" Errors

**Scenario:** Attempting to deploy a new CloudFormation stack (e.g., for testing or a new environment that shares the same `Environment` parameter like "production") fails with errors indicating that S3 buckets, DynamoDB tables, API Gateway names, Lambda function names, or CloudFormation Output Export names already exist.

**Example Errors from Stack Events:**
- `ROLLBACK_IN_PROGRESS | Export with name genai-tweets-digest-website-bucket-production is already exported by stack genai-tweets-digest-production.`
- `DataBucket: CREATE_FAILED | genai-tweets-digest-data-production-855450210814 already exists in stack arn:aws:cloudformation:...:stack/genai-tweets-digest-production/...`
- `SubscribersTable: CREATE_FAILED | genai-tweets-digest-subscribers-production already exists ...`

**Root Cause:**
CloudFormation requires certain resource names and all Output Export names to be unique within an AWS Region and account.
1.  **Physical Resource Names:** If the `infrastructure-aws/cloudformation-template.yaml` defines explicit names for resources like S3 `BucketName`, DynamoDB `TableName`, API Gateway `Name`, Lambda `FunctionName`, IAM `RoleName`, or EventBridge Rule `Name` based *only* on parameters like `${ProjectName}` and `${Environment}`, deploying multiple stacks with the same values for these parameters will cause naming collisions.
2.  **Output Export Names:** Similarly, if `Outputs[*].Export.Name` in the template is based only on `${ProjectName}` and `${Environment}`, these will also collide.

Our deployment scripts (`deploy.sh` and `deploy-optimized.sh`) use a `STACK_NAME` environment variable (often including a timestamp for uniqueness like `genai-tweets-digest-opt-YYYYMMDD-HHMMSS`) for the CloudFormation stack itself. However, if the *internal* resource names and export names aren't also made unique based on this stack name (or another unique identifier), conflicts will occur when the `Environment` parameter (e.g., "production") is the same across these different stack deployments.

### Solution: Ensure Uniqueness with `${AWS::StackName}`

The most robust solution is to modify `infrastructure-aws/cloudformation-template.yaml` to use the CloudFormation pseudo parameter `${AWS::StackName}` for all globally or regionally unique resource names and export names. This ensures that every resource and export tied to a specific stack instance will have a unique name automatically.

**Modifications in `infrastructure-aws/cloudformation-template.yaml`:**

1.  **Physical Resource Names:**
    *   S3 Buckets (`DataBucket`, `WebsiteBucket`):
        ```yaml
        Properties:
          BucketName: !Sub "${AWS::StackName}-data" 
        # (and similarly for -website)
        ```
    *   DynamoDB Table (`SubscribersTable`):
        ```yaml
        Properties:
          TableName: !Sub "${AWS::StackName}-subscribers"
        ```
    *   API Gateway (`ApiGateway`):
        ```yaml
        Properties:
          Name: !Sub "${AWS::StackName}-api"
        ```
    *   Lambda Functions (`SubscriptionFunction`, `WeeklyDigestFunction`, etc.):
        ```yaml
        Properties:
          FunctionName: !Sub "${AWS::StackName}-subscription" 
        # (and similarly for other functions)
        ```
    *   IAM Role (`LambdaExecutionRole`):
        ```yaml
        Properties:
          RoleName: !Sub "${AWS::StackName}-lambda-role"
        ```
    *   EventBridge Rule (`WeeklyDigestSchedule`):
        ```yaml
        Properties:
          Name: !Sub "${AWS::StackName}-digest-schedule"
        ```

2.  **Output Export Names:**
    For every item in the `Outputs:` section:
    ```yaml
    Outputs:
      SomeOutput:
        Description: ...
        Value: ...
        Export:
          Name: !Sub "${AWS::StackName}-some-output-suffix"
    ```
    Example for `WebsiteBucketName`:
    ```yaml
    WebsiteBucketName:
      Description: Name of the S3 bucket for website hosting
      Value: !Ref WebsiteBucket
      Export:
        Name: !Sub "${AWS::StackName}-website-bucket"
    ```

**Deployment Script Considerations (`deploy.sh`, `deploy-optimized.sh`):**
- The scripts should set a unique `STACK_NAME` environment variable (e.g., `export STACK_NAME="project-env-$(date +%Y%m%d-%H%M%S)"`).
- The `deploy.sh` script uses this `STACK_NAME` (passed as `CFN_STACK_NAME`) for the `aws cloudformation create-stack/update-stack` calls.
- CloudFormation then uses this unique stack name (accessible via `${AWS::StackName}`) to generate unique physical resource names and export names as defined in the template.

**Benefits of this approach:**
- Allows multiple independent instances of the application (e.g., for different feature branches, testing, or even multiple production-like tenants if designed that way) to be deployed in the same AWS account/region without naming conflicts.
- Simplifies cleanup, as deleting the CloudFormation stack will remove all uniquely named resources tied to it.

**Important Note:** If you intend for an update to *replace* an existing environment (e.g., a new version of "production" replacing the old "production"), you would typically update the existing stack. If you want a blue/green deployment or a fresh parallel environment, then unique naming driven by a unique stack name is essential.

echo -e "${GREEN}🎉 Optimized Lambda packaging & CloudFormation deployment process initiated!${NC}"
echo -e "${YELLOW}�� Next Steps:${NC}"
echo "  - Monitor CloudFormation stack creation in AWS console."
echo "  - After stack is created, verify Lambda functions and API Gateway endpoints."
echo "  - Test functionality (e.g., subscription, email verification)." 

## 9. Lambda `ImportModuleError: No module named 'lambda_function'`

**Symptom:**
- API Gateway calls to a Lambda function result in a 502 Bad Gateway error.
- CloudWatch logs for the Lambda function show: `[ERROR] Runtime.ImportModuleError: Unable to import module 'lambda_function': No module named 'lambda_function'`.
- This can occur even if `unzip -l your-function.zip` shows `lambda_function.py` at the root of the archive and the Lambda handler is correctly set to `lambda_function.lambda_handler`.

**Root Cause Analysis (Context-Specific):**
In this project, this error surfaced after refactoring the CloudFormation template to use `${AWS::StackName}` for Lambda `FunctionName` properties (e.g., `FunctionName: !Sub "${AWS::StackName}-subscription"`).

The deployment script (`scripts/deploy.sh`) has an `update_lambda_code` function that performs `aws lambda update-function-code` after the CloudFormation stack is deployed or updated.
- **Initial Problem**: This `update_lambda_code` function was constructing target Lambda names using an older convention (e.g., `${PROJECT_NAME}-subscription-${ENVIRONMENT}`).
- **Conflict**: If CloudFormation created/updated a Lambda with the new name (e.g., `my-unique-stack-subscription`) but the script tried to update code for `genai-tweets-digest-subscription-production`, the *correctly named Lambda* might not have received the new code package properly through the script's update step, or an older, incorrectly named Lambda was targeted.
- The direct `aws lambda update-function-code --function-name ${CFN_STACK_NAME}-<func> ...` (using the stack name from `.env` or export, which matches `${AWS::StackName}` used in CFN) eventually resolved this by ensuring the code update targeted the correctly named function that CloudFormation was managing.

**Solution & Prevention:**
1.  **Consistent Naming**: Ensure that the script logic performing `aws lambda update-function-code` (like the `update_lambda_code` function in `scripts/deploy.sh`) constructs the target Lambda function names using the *exact same convention* as defined in the `FunctionName` property within the `infrastructure-aws/cloudformation-template.yaml`. In our case, this means using the CloudFormation stack name as the prefix: `${CFN_STACK_NAME}-<function-short-name>`.
    ```bash
    # In scripts/deploy.sh, inside update_lambda_code:
    # CFN_STACK_NAME is the actual stack name being deployed/updated.
    aws lambda update-function-code --function-name "${CFN_STACK_NAME}-subscription" ...
    ```
2.  **Verify CloudFormation Output**: After a CloudFormation deployment, always check the actual names of the created/updated Lambda functions in the AWS console or via `aws lambda list-functions` to ensure they match script expectations.
3.  **Clean Deployments for Major Refactors**: When making significant changes to resource naming logic in CloudFormation, sometimes deleting and cleanly re-creating the stack (especially for development/testing environments) can prevent subtle state mismatches. For production, careful `update-stack` monitoring is key.

## 10. Lambda Runtime Errors Due to Missing Environment Variables (e.g., SES MessageRejected)

**Symptom:**
- API Gateway calls return 500 or 502 errors.
- CloudWatch logs for the Lambda function show errors originating from *within* the Lambda code, often related to external service calls. For example:
  `Error sending verification email: An error occurred (MessageRejected) when calling the SendEmail operation: Email address is not verified. The following identities failed the check in region US-EAST-1: digest@genai-tweets.com`

**Root Cause:**
The Lambda function requires certain environment variables (e.g., `FROM_EMAIL` for SES, `API_BASE_URL` for constructing links) to be set for its proper operation. These variables are often passed as parameters to the CloudFormation template.
If the specific Lambda function's resource definition in `infrastructure-aws/cloudformation-template.yaml` does *not* include these necessary parameters in its `Properties.Environment.Variables` section, the Lambda will not receive them, even if they are correctly passed to the CloudFormation stack itself.
The Lambda code might then fall back to hardcoded defaults or fail if a required variable is missing.

**Example:** The `SubscriptionFunction` was missing `FROM_EMAIL` in its environment, causing it to default to an unverified address.

**Solution & Prevention:**
1.  **Explicit Environment Variable Mapping in CloudFormation:**
    In `infrastructure-aws/cloudformation-template.yaml`, for *every* Lambda function that requires parameters passed to the stack, ensure those parameters are explicitly mapped in its `Properties.Environment.Variables` section.
    ```yaml
    # Example for SubscriptionFunction:
    SubscriptionFunction:
      Type: AWS::Lambda::Function
      Properties:
        FunctionName: !Sub "${AWS::StackName}-subscription"
        # ... other properties ...
        Environment:
          Variables:
            ENVIRONMENT: !Ref Environment
            S3_BUCKET: !Ref DataBucket
            SUBSCRIBERS_TABLE: !Ref SubscribersTable
            TWITTER_BEARER_TOKEN: !Ref TwitterBearerToken
            GEMINI_API_KEY: !Ref GeminiApiKey
            FROM_EMAIL: !Ref FromEmail           # Ensure this is present
            API_BASE_URL: !Sub "https://${ApiGateway}.execute-api.${AWS::Region}.amazonaws.com/${Environment}" # Ensure this is present if needed
    ```
2.  **Verify Lambda Configuration:** After any deployment that modifies Lambda environment variables, use the AWS Lambda console or `aws lambda get-function-configuration --function-name YOUR_FUNCTION_NAME` to confirm that all expected environment variables are present and have the correct values.
3.  **Centralized Configuration (in code):** Utilize a shared configuration module (like `shared/config.py`) within the Lambda code that consistently reads these environment variables. This makes it easier to manage how settings are accessed.
4.  **Parameter Store/Secrets Manager (Advanced):** For more complex applications or sensitive data, consider storing configurations in AWS Systems Manager Parameter Store or AWS Secrets Manager and having the Lambda functions fetch them at runtime (requires additional IAM permissions). For this project, environment variables via CloudFormation parameters are sufficient.

echo -e "${GREEN}🎉 Optimized Lambda packaging & CloudFormation deployment process initiated!${NC}"
echo -e "${YELLOW}�� Next Steps:${NC}"
echo "  - Monitor CloudFormation stack creation in AWS console."
echo "  - After stack is created, verify Lambda functions and API Gateway endpoints."
echo "  - Test functionality (e.g., subscription, email verification)." 