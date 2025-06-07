# CloudFormation Stack Management Guide

This guide provides step-by-step procedures for managing CloudFormation stacks in the GenAI Tweets Digest serverless project, with particular focus on troubleshooting failed deletions and handling S3-related cleanup issues.

## 🎯 Overview

CloudFormation stack management becomes complex when dealing with stateful resources like S3 buckets and DynamoDB tables. This guide covers:

- **Safe stack deletion procedures**
- **S3 bucket cleanup strategies** 
- **Troubleshooting DELETE_FAILED states**
- **Data backup and recovery**
- **Environment cleanup verification**

## 🗂️ Quick Reference Commands

### Environment Setup
```bash
export AWS_PROFILE=personal
export AWS_REGION=us-east-1
export STACK_NAME="genai-tweets-digest-production"
```

### Check Stack Status
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation describe-stacks --stack-name $STACK_NAME --region us-east-1 --query 'Stacks[0].StackStatus' --output text | cat"
```

### Get Stack Resources
```bash
zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation list-stack-resources --stack-name $STACK_NAME --region us-east-1 --output table | cat"
```

## 📋 Complete Stack Deletion Procedure

### Phase 1: Pre-Deletion Assessment

#### 1.1 Check Current Stack Status
```bash
echo "=== Current Stack Status ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation describe-stacks --stack-name $STACK_NAME --region us-east-1 --query 'Stacks[0].[StackStatus,CreationTime]' --output table | cat"
```

#### 1.2 Identify S3 Buckets in Stack
```bash
echo "=== S3 Buckets in Stack ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation list-stack-resources --stack-name $STACK_NAME --region us-east-1 --query 'StackResourceSummaries[?ResourceType==\`AWS::S3::Bucket\`].[LogicalResourceId,PhysicalResourceId]' --output table | cat"

# Extract bucket names for cleanup
DATA_BUCKET=$(zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation describe-stack-resource --stack-name $STACK_NAME --logical-resource-id DataBucket --region us-east-1 --query 'StackResourceDetail.PhysicalResourceId' --output text | cat")
WEBSITE_BUCKET=$(zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation describe-stack-resource --stack-name $STACK_NAME --logical-resource-id WebsiteBucket --region us-east-1 --query 'StackResourceDetail.PhysicalResourceId' --output text | cat")

echo "Data Bucket: $DATA_BUCKET"
echo "Website Bucket: $WEBSITE_BUCKET"
```

#### 1.3 Assess Data in Buckets
```bash
echo "=== Data Bucket Contents ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 ls s3://$DATA_BUCKET --recursive --human-readable --summarize | cat"

echo "=== Website Bucket Contents ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 ls s3://$WEBSITE_BUCKET --recursive --human-readable --summarize | cat"

# Check for versioned objects
echo "=== Checking for Object Versions ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws s3api list-object-versions --bucket $DATA_BUCKET --query 'length(Versions)' --output text | cat" 2>/dev/null || echo "No versions found"
```

### Phase 2: Data Backup (Optional but Recommended)

#### 2.1 Create Backup Directory
```bash
BACKUP_DIR="./backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
echo "Created backup directory: $BACKUP_DIR"
```

#### 2.2 Backup Critical Data
```bash
echo "=== Backing up configuration files ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 sync s3://$DATA_BUCKET/config/ $BACKUP_DIR/config/ | cat" 2>/dev/null || echo "No config files found"

echo "=== Backing up latest digest data ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 sync s3://$DATA_BUCKET/tweets/digests/ $BACKUP_DIR/digests/ | cat" 2>/dev/null || echo "No digest files found"

echo "=== Backing up DynamoDB subscribers table ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws dynamodb scan --table-name genai-tweets-digest-subscribers-production --region us-east-1 --output json > $BACKUP_DIR/subscribers-backup.json | cat" 2>/dev/null || echo "No subscribers table found"

echo "Backup completed in: $BACKUP_DIR"
ls -la "$BACKUP_DIR"
```

### Phase 3: S3 Bucket Cleanup

#### 3.1 Empty Data Bucket
```bash
echo "=== Step 1: Removing current objects from data bucket ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 rm s3://$DATA_BUCKET --recursive | cat" 2>/dev/null || echo "No current objects to remove"

echo "=== Step 2: Removing object versions from data bucket ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws s3api delete-objects --bucket $DATA_BUCKET --delete \"\$(aws s3api list-object-versions --bucket $DATA_BUCKET --query='{Objects: Versions[].{Key:Key,VersionId:VersionId}}' --output json)\" --region us-east-1 | cat" 2>/dev/null || echo "No object versions to remove"

echo "=== Step 3: Removing delete markers from data bucket ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws s3api delete-objects --bucket $DATA_BUCKET --delete \"\$(aws s3api list-object-versions --bucket $DATA_BUCKET --query='{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' --output json)\" --region us-east-1 | cat" 2>/dev/null || echo "No delete markers to remove"

echo "=== Verifying data bucket is empty ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 ls s3://$DATA_BUCKET --recursive | cat" 2>/dev/null && echo "⚠️  Data bucket still has objects!" || echo "✅ Data bucket is empty"
```

#### 3.2 Empty Website Bucket
```bash
echo "=== Emptying website bucket ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 rm s3://$WEBSITE_BUCKET --recursive | cat" 2>/dev/null || echo "No objects to remove from website bucket"

echo "=== Verifying website bucket is empty ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 ls s3://$WEBSITE_BUCKET --recursive | cat" 2>/dev/null && echo "⚠️  Website bucket still has objects!" || echo "✅ Website bucket is empty"
```

#### 3.3 Manual Bucket Deletion (If Needed)
```bash
# Only needed if CloudFormation deletion fails
echo "=== Manually deleting data bucket ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 rb s3://$DATA_BUCKET --region us-east-1 | cat" 2>/dev/null || echo "Data bucket not found or already deleted"

echo "=== Manually deleting website bucket ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 rb s3://$WEBSITE_BUCKET --region us-east-1 | cat" 2>/dev/null || echo "Website bucket not found or already deleted"
```

### Phase 4: CloudFormation Stack Deletion

#### 4.1 Initiate Stack Deletion
```bash
echo "=== Initiating CloudFormation stack deletion ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation delete-stack --stack-name $STACK_NAME --region us-east-1 | cat"
echo "Stack deletion initiated at $(date)"
```

#### 4.2 Monitor Deletion Progress
```bash
echo "=== Monitoring stack deletion progress ==="
while true; do
  STATUS=$(zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation describe-stacks --stack-name $STACK_NAME --region us-east-1 --query 'Stacks[0].StackStatus' --output text 2>/dev/null | cat")
  
  if [ $? -ne 0 ]; then
    echo "✅ Stack successfully deleted at $(date)"
    break
  fi
  
  echo "$(date): Stack status: $STATUS"
  
  if [[ "$STATUS" == "DELETE_FAILED" ]]; then
    echo "❌ Stack deletion failed. Checking stack events..."
    zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation describe-stack-events --stack-name $STACK_NAME --region us-east-1 --query 'StackEvents[?ResourceStatus==\`DELETE_FAILED\`].[LogicalResourceId,ResourceStatusReason]' --output table | cat"
    break
  fi
  
  sleep 30
done
```

#### 4.3 Handle DELETE_FAILED State
```bash
# If stack is in DELETE_FAILED state, check which resources failed
echo "=== Analyzing DELETE_FAILED resources ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation describe-stack-events --stack-name $STACK_NAME --region us-east-1 --query 'StackEvents[?ResourceStatus==\`DELETE_FAILED\`].[LogicalResourceId,ResourceType,ResourceStatusReason]' --output table | cat"

# Retry deletion after manual cleanup
echo "=== Retrying stack deletion ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation delete-stack --stack-name $STACK_NAME --region us-east-1 | cat"
```

### Phase 5: Post-Deletion Verification

#### 5.1 Verify All Resources Are Cleaned Up
```bash
echo "=== Verifying S3 buckets are deleted ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 ls | grep genai-tweets-digest | cat" 2>/dev/null && echo "⚠️  Some S3 buckets still exist" || echo "✅ All S3 buckets deleted"

echo "=== Verifying Lambda functions are deleted ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws lambda list-functions --query 'Functions[?starts_with(FunctionName, \`genai-tweets-digest\`)].FunctionName' --output table --region us-east-1 | cat"

echo "=== Verifying DynamoDB tables are deleted ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws dynamodb list-tables --query 'TableNames[?starts_with(@, \`genai-tweets-digest\`)]' --output table --region us-east-1 | cat"

echo "=== Verifying API Gateway APIs are deleted ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws apigateway get-rest-apis --query 'items[?starts_with(name, \`genai-tweets-digest\`)].name' --output table --region us-east-1 | cat"

echo "=== Verifying IAM roles are deleted ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws iam list-roles --query 'Roles[?starts_with(RoleName, \`genai-tweets-digest\`)].RoleName' --output table | cat"
```

#### 5.2 Check for Orphaned Resources
```bash
echo "=== Checking for orphaned CloudWatch log groups ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws logs describe-log-groups --log-group-name-prefix '/aws/lambda/genai-tweets-digest' --region us-east-1 --query 'logGroups[].logGroupName' --output table | cat"

echo "=== Checking for orphaned EventBridge rules ==="
zsh -d -f -c "export AWS_PROFILE=personal && aws events list-rules --name-prefix 'genai-tweets-digest' --region us-east-1 --query 'Rules[].Name' --output table | cat"
```

## 🔄 Stack Redeployment After Cleanup

### Prepare for Fresh Deployment
```bash
echo "=== Environment ready for fresh deployment ==="
echo "AWS Profile: $AWS_PROFILE"
echo "AWS Region: $AWS_REGION"
echo "Backup Location: $BACKUP_DIR"

# Verify environment variables are set
echo "=== Checking required environment variables ==="
echo "TWITTER_BEARER_TOKEN: ${TWITTER_BEARER_TOKEN:0:20}..."
echo "GEMINI_API_KEY: ${GEMINI_API_KEY:0:20}..."
echo "FROM_EMAIL: $FROM_EMAIL"
echo "TO_EMAIL: $TO_EMAIL"
```

### Deploy New Stack
```bash
echo "=== Ready to deploy new stack ==="
echo "Run: ./scripts/deploy.sh"
```

## 🚨 Troubleshooting Common Issues

### Issue 1: S3 Bucket "Access Denied" During Deletion
```bash
# Check bucket policy and ownership
zsh -d -f -c "export AWS_PROFILE=personal && aws s3api get-bucket-ownership-controls --bucket $DATA_BUCKET --region us-east-1 | cat" 2>/dev/null || echo "No ownership controls"

# Try force deletion with different approach
zsh -d -f -c "export AWS_PROFILE=personal && aws s3 rb s3://$DATA_BUCKET --force --region us-east-1 | cat"
```

### Issue 2: DynamoDB Table Deletion Fails
```bash
# Check if table has point-in-time recovery enabled
zsh -d -f -c "export AWS_PROFILE=personal && aws dynamodb describe-continuous-backups --table-name genai-tweets-digest-subscribers-production --region us-east-1 | cat"

# Delete table manually if needed
zsh -d -f -c "export AWS_PROFILE=personal && aws dynamodb delete-table --table-name genai-tweets-digest-subscribers-production --region us-east-1 | cat"
```

### Issue 3: Lambda Function Deletion Fails
```bash
# Check if function has reserved concurrency
zsh -d -f -c "export AWS_PROFILE=personal && aws lambda get-provisioned-concurrency-config --function-name genai-tweets-digest-weekly-digest-production --region us-east-1 | cat" 2>/dev/null || echo "No reserved concurrency"

# Delete function manually if needed
zsh -d -f -c "export AWS_PROFILE=personal && aws lambda delete-function --function-name genai-tweets-digest-weekly-digest-production --region us-east-1 | cat"
```

### Issue 4: CloudWatch Log Groups Remain After Stack Deletion
```bash
# Log groups are not automatically deleted by CloudFormation
# Manual cleanup required
zsh -d -f -c "export AWS_PROFILE=personal && aws logs delete-log-group --log-group-name '/aws/lambda/genai-tweets-digest-subscription-production' --region us-east-1 | cat" 2>/dev/null || echo "Log group not found"

zsh -d -f -c "export AWS_PROFILE=personal && aws logs delete-log-group --log-group-name '/aws/lambda/genai-tweets-digest-weekly-digest-production' --region us-east-1 | cat" 2>/dev/null || echo "Log group not found"
```

## 📊 Cost Monitoring During Cleanup

### Check Current AWS Costs
```bash
# Get current month's costs for the project (requires billing access)
echo "=== Current month AWS costs ==="
START_DATE=$(date -d "$(date +'%Y-%m-01')" +'%Y-%m-%d')
END_DATE=$(date +'%Y-%m-%d')

zsh -d -f -c "export AWS_PROFILE=personal && aws ce get-cost-and-usage --time-period Start=$START_DATE,End=$END_DATE --granularity MONTHLY --metrics BlendedCost --group-by Type=DIMENSION,Key=SERVICE | cat" 2>/dev/null || echo "Cost Explorer access not available"
```

## 📋 Pre-Deployment Checklist

Before deploying a new stack after cleanup:

- [ ] ✅ All S3 buckets deleted
- [ ] ✅ All Lambda functions deleted  
- [ ] ✅ DynamoDB tables deleted
- [ ] ✅ API Gateway APIs deleted
- [ ] ✅ IAM roles deleted
- [ ] ✅ CloudWatch log groups cleaned up (optional)
- [ ] ✅ Environment variables verified
- [ ] ✅ SES email addresses verified
- [ ] ✅ Backup data saved (if needed)
- [ ] ✅ AWS CLI credentials working
- [ ] ✅ Latest code pulled from repository

## 🔐 Security Considerations

### Secure Data Handling
- Always backup sensitive data before deletion
- Verify S3 bucket encryption settings before deletion
- Check for any hardcoded secrets in backed-up data
- Ensure .env files are not committed to version control

### Access Control
- Use least-privilege IAM policies for cleanup operations
- Consider using AWS CloudTrail to audit deletion activities
- Verify you have the correct AWS profile/account selected

### Data Retention Compliance
- Check if any data has legal retention requirements
- Document deletion activities for compliance purposes
- Consider data anonymization before backup if required

---

> **⚠️ Important Note**: This guide uses the `zsh -d -f -c` wrapper to ensure clean shell execution in environments with custom shell configurations. This is essential for reliable AWS CLI operations in the GenAI Tweets Digest project environment. 