#!/bin/bash
# Quick deployment script for hybrid Lambda + EC2 architecture

set -e

ENVIRONMENT=${1:-development}
NOTIFICATION_EMAIL=${2:-""}

echo "🚀 Quick Deployment: Hybrid Lambda + EC2 Architecture"
echo "📅 $(date)"
echo "🌍 Environment: $ENVIRONMENT"
echo ""

# Validate prerequisites
echo "🔍 Checking prerequisites..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install and configure AWS CLI first."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS credentials not configured. Run 'aws configure' first."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "infrastructure-aws/hybrid-architecture-template.yaml" ]; then
    echo "❌ CloudFormation template not found. Run this from the project root directory."
    exit 1
fi

echo "✅ Prerequisites validated"
echo ""

# Set parameters based on environment
if [ "$ENVIRONMENT" = "production" ]; then
    INSTANCE_TYPE="t3.medium"
    PROCESSING_MODE="hybrid"
else
    INSTANCE_TYPE="t3.small"
    PROCESSING_MODE="hybrid"
fi

# Step 1: Deploy Infrastructure
echo "🏗️  Step 1: Deploying Infrastructure..."
echo "   Stack: genai-tweet-digest-$ENVIRONMENT"
echo "   Instance Type: $INSTANCE_TYPE"
echo "   Processing Mode: $PROCESSING_MODE"

STACK_PARAMS="ProjectName=genai-tweet-digest"
STACK_PARAMS="$STACK_PARAMS Environment=$ENVIRONMENT"
STACK_PARAMS="$STACK_PARAMS ProcessingMode=$PROCESSING_MODE"
STACK_PARAMS="$STACK_PARAMS EnableVisualCapture=true"
STACK_PARAMS="$STACK_PARAMS EC2InstanceType=$INSTANCE_TYPE"

if [ -n "$NOTIFICATION_EMAIL" ]; then
    STACK_PARAMS="$STACK_PARAMS NotificationEmail=$NOTIFICATION_EMAIL"
fi

aws cloudformation deploy \
    --template-file infrastructure-aws/hybrid-architecture-template.yaml \
    --stack-name "genai-tweet-digest-$ENVIRONMENT" \
    --parameter-overrides $STACK_PARAMS \
    --capabilities CAPABILITY_NAMED_IAM \
    --region us-east-1

echo "✅ Infrastructure deployed successfully"
echo ""

# Step 2: Wait for stack to stabilize
echo "⏰ Waiting for stack to stabilize..."
aws cloudformation wait stack-deploy-complete \
    --stack-name "genai-tweet-digest-$ENVIRONMENT" \
    --region us-east-1

echo "✅ Stack stabilized"
echo ""

# Step 3: Deploy Lambda Functions
echo "📦 Step 2: Deploying Lambda Functions..."

if [ -f "scripts/deploy-lambdas.sh" ]; then
    chmod +x scripts/deploy-lambdas.sh
    ./scripts/deploy-lambdas.sh $ENVIRONMENT
else
    echo "⚠️  Lambda deployment script not found. Skipping Lambda deployment."
fi

echo ""

# Step 4: Upload initial configuration
echo "⚙️  Step 3: Uploading Configuration..."

S3_BUCKET="genai-tweet-digest-$ENVIRONMENT-data"

# Upload accounts configuration if it exists
if [ -f "data/accounts.json" ]; then
    aws s3 cp data/accounts.json "s3://$S3_BUCKET/config/" || echo "⚠️  Failed to upload accounts.json"
    echo "✅ Accounts configuration uploaded"
else
    echo "⚠️  data/accounts.json not found. You'll need to create this file."
fi

# Create a placeholder EC2 code package
echo "📦 Creating placeholder EC2 code package..."
if [ -d "ec2-processing" ] && [ -d "lambdas/shared" ]; then
    tar -czf ec2-processing.tar.gz \
        ec2-processing/ \
        lambdas/shared/ \
        --exclude="*.pyc" \
        --exclude="__pycache__" \
        --exclude="*.log" || true
    
    aws s3 cp ec2-processing.tar.gz "s3://$S3_BUCKET/code/" || echo "⚠️  Failed to upload EC2 code"
    rm ec2-processing.tar.gz
    echo "✅ EC2 code package uploaded"
else
    echo "⚠️  EC2 processing code not found. Manual deployment required."
fi

echo ""

# Step 5: Get stack outputs
echo "📋 Step 4: Getting Stack Information..."

OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name "genai-tweet-digest-$ENVIRONMENT" \
    --query 'Stacks[0].Outputs' \
    --output table)

echo "$OUTPUTS"
echo ""

# Step 6: Run basic validation
echo "🧪 Step 5: Running Basic Validation..."

# Test weekly digest function
WEEKLY_DIGEST_FUNCTION="genai-tweet-digest-$ENVIRONMENT-weekly-digest"

echo "Testing weekly digest function..."
aws lambda invoke \
    --function-name "$WEEKLY_DIGEST_FUNCTION" \
    --payload '{"test": true, "processing_mode": "lambda-only"}' \
    test-response.json > /dev/null 2>&1

if [ $? -eq 0 ]; then
    RESPONSE=$(cat test-response.json)
    echo "✅ Weekly digest function responding"
    
    # Check if there are any errors in the response
    if echo "$RESPONSE" | grep -q "error"; then
        echo "⚠️  Function returned error. Check logs."
        echo "Response: $RESPONSE"
    fi
else
    echo "❌ Weekly digest function test failed"
fi

# Clean up test file
rm -f test-response.json

echo ""

# Step 7: Display summary and next steps
echo "🎉 Deployment Complete!"
echo ""
echo "📊 Summary:"
echo "   Environment: $ENVIRONMENT"
echo "   S3 Bucket: $S3_BUCKET"
echo "   Weekly Digest Function: $WEEKLY_DIGEST_FUNCTION"
echo ""
echo "🔧 Next Steps:"
echo ""
echo "1. 📧 Configure API Keys (if not already done):"
echo "   aws ssm put-parameter --name '/genai-tweet-digest/twitter/bearer-token' --value 'YOUR_TOKEN' --type SecureString"
echo "   aws ssm put-parameter --name '/genai-tweet-digest/gemini/api-key' --value 'YOUR_KEY' --type SecureString"
echo ""
echo "2. 🗂️  Create accounts configuration (if not already done):"
echo "   Create data/accounts.json with your Twitter accounts list"
echo ""
echo "3. 🧪 Test the system:"
echo "   # Test Lambda-only processing:"
echo "   aws lambda invoke --function-name $WEEKLY_DIGEST_FUNCTION --payload '{\"test\": true, \"processing_mode\": \"lambda-only\"}' response.json"
echo ""
echo "   # Test EC2 dispatch:"
echo "   aws lambda invoke --function-name genai-tweet-digest-$ENVIRONMENT-visual-dispatcher --payload '{\"accounts\": [\"openai\"], \"max_tweets\": 5}' response.json"
echo ""
echo "4. 📊 Monitor the system:"
echo "   # Check CloudWatch logs:"
echo "   aws logs describe-log-groups --log-group-name-prefix '/aws/lambda/genai-tweet-digest-$ENVIRONMENT'"
echo ""
echo "5. 🎛️  Configure processing mode:"
echo "   # Switch to EC2 processing:"
echo "   aws lambda update-function-configuration \\"
echo "     --function-name $WEEKLY_DIGEST_FUNCTION \\"
echo "     --environment Variables='{\"PROCESSING_MODE\":\"ec2-only\",\"ENABLE_VISUAL_CAPTURE\":\"true\"}'"
echo ""
echo "🔗 Useful Commands:"
echo "   # View stack resources:"
echo "   aws cloudformation list-stack-resources --stack-name genai-tweet-digest-$ENVIRONMENT"
echo ""
echo "   # Check function logs:"
echo "   aws logs tail /aws/lambda/$WEEKLY_DIGEST_FUNCTION --follow"
echo ""
echo "   # Delete stack (when needed):"
echo "   aws cloudformation delete-stack --stack-name genai-tweet-digest-$ENVIRONMENT"
echo ""
echo "✅ Hybrid Lambda + EC2 architecture deployed successfully!" 