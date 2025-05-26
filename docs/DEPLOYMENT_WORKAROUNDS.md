# Deployment Workarounds and Key Learnings

This document outlines the key challenges encountered and the successful workarounds found during the deployment of the GenAI Tweets Digest serverless infrastructure, particularly concerning shell environment issues and AWS CloudFormation.

## 1. Shell Output Issues with AWS CLI

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

## 2. AWS CloudFormation Stack Creation Issues

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

## 3. Successful Deployment Strategy (Summary)

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
        "ParameterValue": "noreply@example.com"
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
    # फॉलोड बाइ वेट एंड अन्य चेक्स...
    ```

This approach ensures that the CloudFormation template is correct and that the parameters and the AWS CLI command itself are processed reliably. 