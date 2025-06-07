# Hybrid Architecture Deployment Guide

## Overview

This guide covers the complete deployment strategy for the hybrid Lambda + EC2 architecture, including infrastructure, code deployment, configuration management, and CI/CD considerations.

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT STRATEGY                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  │ INFRASTRUCTURE  │    │    CODE         │    │ CONFIGURATION   │
│  │ (CloudFormation)│    │ (Lambda + EC2)  │    │ (SSM/S3)        │
│  │                 │    │                 │    │                 │
│  │ • VPC/Subnets   │    │ • Lambda zips   │    │ • API keys      │
│  │ • Auto Scaling  │    │ • EC2 AMI       │    │ • Account lists │
│  │ • IAM roles     │    │ • Shared libs   │    │ • Feature flags │
│  │ • Lambda funcs  │    │ • Dependencies  │    │ • Environment   │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Phase 1: Infrastructure Deployment

### 1.1 Prerequisites

Before deploying, ensure you have:

```bash
# AWS CLI configured
aws configure

# Required permissions
# - CloudFormation full access
# - Lambda full access  
# - EC2 full access
# - IAM role creation
# - S3 full access
# - DynamoDB full access

# Store secrets in SSM Parameter Store
aws ssm put-parameter \
  --name "/genai-tweet-digest/twitter/bearer-token" \
  --value "your_twitter_bearer_token" \
  --type "SecureString"

aws ssm put-parameter \
  --name "/genai-tweet-digest/gemini/api-key" \
  --value "your_gemini_api_key" \
  --type "SecureString"
```

### 1.2 Deploy Infrastructure

Deploy the CloudFormation stack:

```bash
# Development environment
aws cloudformation deploy \
  --template-file infrastructure-aws/hybrid-architecture-template.yaml \
  --stack-name genai-tweet-digest-dev \
  --parameter-overrides \
    ProjectName=genai-tweet-digest \
    Environment=development \
    ProcessingMode=hybrid \
    EnableVisualCapture=true \
    EC2InstanceType=t3.small \
    NotificationEmail=your-email@example.com \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Production environment
aws cloudformation deploy \
  --template-file infrastructure-aws/hybrid-architecture-template.yaml \
  --stack-name genai-tweet-digest-prod \
  --parameter-overrides \
    ProjectName=genai-tweet-digest \
    Environment=production \
    ProcessingMode=hybrid \
    EnableVisualCapture=true \
    EC2InstanceType=t3.medium \
    NotificationEmail=your-email@example.com \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### 1.3 Verify Infrastructure

```bash
# Check stack status
aws cloudformation describe-stacks \
  --stack-name genai-tweet-digest-dev \
  --query 'Stacks[0].StackStatus'

# Get outputs
aws cloudformation describe-stacks \
  --stack-name genai-tweet-digest-dev \
  --query 'Stacks[0].Outputs'
```

## Phase 2: Code Deployment

### 2.1 Lambda Function Deployment

Create deployment scripts for Lambda functions:

```bash
#!/bin/bash
# scripts/deploy-lambdas.sh

set -e

ENVIRONMENT=${1:-development}
PROJECT_NAME="genai-tweet-digest"

echo "🚀 Deploying Lambda functions for $ENVIRONMENT environment..."

# Function to deploy a single Lambda
deploy_lambda() {
    local function_name=$1
    local source_dir=$2
    local zip_name=$3
    
    echo "📦 Packaging $function_name..."
    
    cd "lambdas/$source_dir"
    
    # Install dependencies if requirements.txt exists
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt -t .
    fi
    
    # Create deployment package
    zip -r "../$zip_name" . -x "*.pyc" "__pycache__/*" "tests/*"
    
    cd ../..
    
    echo "🚀 Deploying $function_name..."
    aws lambda update-function-code \
        --function-name "$PROJECT_NAME-$ENVIRONMENT-$function_name" \
        --zip-file "fileb://lambdas/$zip_name" \
        --region us-east-1
    
    echo "✅ $function_name deployed successfully"
}

# Deploy each Lambda function
deploy_lambda "visual-dispatcher" "visual-processing-dispatcher" "visual-dispatcher.zip"
deploy_lambda "processing-complete" "processing-complete-handler" "processing-complete.zip"
deploy_lambda "weekly-digest" "weekly-digest" "weekly-digest.zip"

echo "✅ All Lambda functions deployed successfully!"
```

### 2.2 EC2 Code Deployment

Create AMI with pre-installed dependencies:

```bash
#!/bin/bash
# scripts/build-ec2-ami.sh

set -e

echo "🏗️ Building EC2 AMI for visual processing..."

# Launch temporary EC2 instance
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --instance-type t3.micro \
    --key-name your-key-pair \
    --security-group-ids sg-xxxxxxxx \
    --subnet-id subnet-xxxxxxxx \
    --user-data file://scripts/ec2-setup.sh \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=visual-processing-build}]' \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "📦 Launched instance $INSTANCE_ID for AMI creation"

# Wait for instance to be ready
aws ec2 wait instance-running --instance-ids $INSTANCE_ID
echo "⏰ Waiting for setup to complete (this may take 10-15 minutes)..."
sleep 900  # Wait for user-data script to complete

# Create AMI
AMI_ID=$(aws ec2 create-image \
    --instance-id $INSTANCE_ID \
    --name "genai-tweet-digest-visual-processing-$(date +%Y%m%d-%H%M%S)" \
    --description "Visual tweet processing AMI with Chrome and dependencies" \
    --query 'ImageId' \
    --output text)

echo "📸 Creating AMI $AMI_ID..."

# Wait for AMI to be available
aws ec2 wait image-available --image-ids $AMI_ID

# Terminate build instance
aws ec2 terminate-instances --instance-ids $INSTANCE_ID

echo "✅ AMI $AMI_ID created successfully!"
echo "📝 Update the LaunchTemplate in CloudFormation with this AMI ID"
```

### 2.3 EC2 Setup Script

```bash
#!/bin/bash
# scripts/ec2-setup.sh

set -e

echo "🛠️ Setting up EC2 instance for visual processing..."

# Update system
yum update -y

# Install Python 3.11
yum install -y python3.11 python3.11-pip git wget unzip

# Install Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | rpm --import -
cat > /etc/yum.repos.d/google-chrome.repo << EOF
[google-chrome]
name=google-chrome
baseurl=http://dl.google.com/linux/chrome/rpm/stable/x86_64
enabled=1
gpgcheck=1
gpgkey=https://dl.google.com/linux/linux_signing_key.pub
EOF
yum install -y google-chrome-stable

# Install dependencies
pip3.11 install boto3 selenium webdriver-manager pillow requests

# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm

# Create application directory
mkdir -p /opt/visual-processing
chown ec2-user:ec2-user /opt/visual-processing

# Download application code (will be updated during deployment)
echo "📥 EC2 setup complete. Ready for application deployment."
```

### 2.4 Deploy EC2 Code

```bash
#!/bin/bash
# scripts/deploy-ec2-code.sh

set -e

ENVIRONMENT=${1:-development}
S3_BUCKET="genai-tweet-digest-$ENVIRONMENT-data"

echo "📦 Packaging EC2 application code..."

# Create deployment package
tar -czf ec2-processing.tar.gz \
    ec2-processing/ \
    lambdas/shared/ \
    --exclude="*.pyc" \
    --exclude="__pycache__" \
    --exclude="*.log"

# Upload to S3
aws s3 cp ec2-processing.tar.gz "s3://$S3_BUCKET/code/"

echo "✅ EC2 code deployed to S3"

# Optionally update launch template with new user data
echo "📝 Consider updating the Launch Template if EC2 setup has changed"
```

## Phase 3: Configuration Management

### 3.1 Environment-Specific Configuration

```bash
#!/bin/bash
# scripts/configure-environment.sh

ENVIRONMENT=${1:-development}
S3_BUCKET="genai-tweet-digest-$ENVIRONMENT-data"

echo "⚙️ Configuring $ENVIRONMENT environment..."

# Upload account configuration
aws s3 cp data/accounts.json "s3://$S3_BUCKET/config/"

# Set environment-specific Lambda variables
aws lambda update-function-configuration \
    --function-name "genai-tweet-digest-$ENVIRONMENT-weekly-digest" \
    --environment Variables="{
        PROCESSING_MODE=hybrid,
        ENABLE_VISUAL_CAPTURE=true,
        VISUAL_ACCOUNTS_LIMIT=10,
        S3_BUCKET_NAME=$S3_BUCKET
    }"

echo "✅ Environment configured"
```

### 3.2 Feature Flags

```bash
# Enable/disable visual processing
aws lambda update-function-configuration \
    --function-name "genai-tweet-digest-production-weekly-digest" \
    --environment Variables="{
        PROCESSING_MODE=lambda-only,
        ENABLE_VISUAL_CAPTURE=false
    }"
```

## Phase 4: CI/CD Pipeline

### 4.1 GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy Hybrid Architecture

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  AWS_REGION: us-east-1

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          pip install -r dev-requirements.txt
          
      - name: Run tests
        run: |
          cd lambdas
          python -m pytest tests/ -v
          
  deploy-dev:
    if: github.ref == 'refs/heads/develop'
    needs: test
    runs-on: ubuntu-latest
    environment: development
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
          
      - name: Deploy infrastructure
        run: |
          aws cloudformation deploy \
            --template-file infrastructure-aws/hybrid-architecture-template.yaml \
            --stack-name genai-tweet-digest-dev \
            --parameter-overrides Environment=development \
            --capabilities CAPABILITY_NAMED_IAM
            
      - name: Deploy Lambda functions
        run: |
          chmod +x scripts/deploy-lambdas.sh
          ./scripts/deploy-lambdas.sh development
          
      - name: Deploy EC2 code
        run: |
          chmod +x scripts/deploy-ec2-code.sh
          ./scripts/deploy-ec2-code.sh development
          
  deploy-prod:
    if: github.ref == 'refs/heads/main'
    needs: test
    runs-on: ubuntu-latest
    environment: production
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
          
      - name: Deploy infrastructure
        run: |
          aws cloudformation deploy \
            --template-file infrastructure-aws/hybrid-architecture-template.yaml \
            --stack-name genai-tweet-digest-prod \
            --parameter-overrides Environment=production \
            --capabilities CAPABILITY_NAMED_IAM
            
      - name: Deploy Lambda functions
        run: |
          chmod +x scripts/deploy-lambdas.sh
          ./scripts/deploy-lambdas.sh production
          
      - name: Deploy EC2 code
        run: |
          chmod +x scripts/deploy-ec2-code.sh
          ./scripts/deploy-ec2-code.sh production
          
      - name: Run smoke tests
        run: |
          # Test Lambda-only mode
          aws lambda invoke \
            --function-name genai-tweet-digest-production-weekly-digest \
            --payload '{"test": true, "processing_mode": "lambda-only"}' \
            response.json
            
          # Verify response
          cat response.json
```

### 4.2 Deployment Scripts

Create a master deployment script:

```bash
#!/bin/bash
# scripts/deploy.sh

set -e

ENVIRONMENT=${1:-development}
DEPLOY_INFRASTRUCTURE=${2:-true}
DEPLOY_CODE=${3:-true}

echo "🚀 Starting deployment to $ENVIRONMENT environment..."

if [ "$DEPLOY_INFRASTRUCTURE" = "true" ]; then
    echo "🏗️ Deploying infrastructure..."
    aws cloudformation deploy \
        --template-file infrastructure-aws/hybrid-architecture-template.yaml \
        --stack-name "genai-tweet-digest-$ENVIRONMENT" \
        --parameter-overrides Environment=$ENVIRONMENT \
        --capabilities CAPABILITY_NAMED_IAM
    
    echo "⏰ Waiting for stack to stabilize..."
    aws cloudformation wait stack-update-complete \
        --stack-name "genai-tweet-digest-$ENVIRONMENT" || true
fi

if [ "$DEPLOY_CODE" = "true" ]; then
    echo "📦 Deploying Lambda functions..."
    ./scripts/deploy-lambdas.sh $ENVIRONMENT
    
    echo "📦 Deploying EC2 code..."
    ./scripts/deploy-ec2-code.sh $ENVIRONMENT
    
    echo "⚙️ Configuring environment..."
    ./scripts/configure-environment.sh $ENVIRONMENT
fi

echo "✅ Deployment to $ENVIRONMENT completed successfully!"

# Run health checks
echo "🔍 Running health checks..."
aws lambda invoke \
    --function-name "genai-tweet-digest-$ENVIRONMENT-weekly-digest" \
    --payload '{"test": true}' \
    response.json

if grep -q "success" response.json; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    cat response.json
    exit 1
fi
```

## Phase 5: Deployment Validation

### 5.1 Automated Testing

```bash
#!/bin/bash
# scripts/validate-deployment.sh

ENVIRONMENT=${1:-development}

echo "🧪 Validating deployment..."

# Test Lambda-only processing
echo "Testing Lambda processing..."
aws lambda invoke \
    --function-name "genai-tweet-digest-$ENVIRONMENT-weekly-digest" \
    --payload '{"test": true, "processing_mode": "lambda-only"}' \
    lambda-response.json

# Test EC2 dispatch
echo "Testing EC2 dispatch..."
aws lambda invoke \
    --function-name "genai-tweet-digest-$ENVIRONMENT-visual-dispatcher" \
    --payload '{"accounts": ["openai"], "max_tweets": 5}' \
    dispatcher-response.json

# Check Auto Scaling Group
echo "Checking Auto Scaling Group..."
aws autoscaling describe-auto-scaling-groups \
    --auto-scaling-group-names "genai-tweet-digest-$ENVIRONMENT-visual-processing"

# Verify S3 bucket
echo "Checking S3 bucket..."
aws s3 ls "genai-tweet-digest-$ENVIRONMENT-data/"

echo "✅ Validation complete"
```

### 5.2 Monitoring Setup

```bash
#!/bin/bash
# scripts/setup-monitoring.sh

ENVIRONMENT=${1:-development}

echo "📊 Setting up monitoring and alerts..."

# Create CloudWatch alarms
aws cloudwatch put-metric-alarm \
    --alarm-name "GenAI-$ENVIRONMENT-Lambda-Errors" \
    --alarm-description "Lambda function errors" \
    --metric-name Errors \
    --namespace AWS/Lambda \
    --statistic Sum \
    --period 300 \
    --threshold 1 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --dimensions Name=FunctionName,Value="genai-tweet-digest-$ENVIRONMENT-weekly-digest" \
    --evaluation-periods 1

# Set up cost alerts
aws budgets create-budget \
    --account-id $(aws sts get-caller-identity --query Account --output text) \
    --budget '{
        "BudgetName": "GenAI-Tweet-Digest-Monthly",
        "BudgetLimit": {
            "Amount": "10",
            "Unit": "USD"
        },
        "TimeUnit": "MONTHLY",
        "BudgetType": "COST"
    }'

echo "✅ Monitoring configured"
```

## Phase 6: Rollback Strategy

### 6.1 Quick Rollback

```bash
#!/bin/bash
# scripts/rollback.sh

ENVIRONMENT=${1:-development}
ROLLBACK_TYPE=${2:-lambda-only}

echo "🔄 Rolling back to $ROLLBACK_TYPE mode..."

case $ROLLBACK_TYPE in
    "lambda-only")
        aws lambda update-function-configuration \
            --function-name "genai-tweet-digest-$ENVIRONMENT-weekly-digest" \
            --environment Variables="{
                PROCESSING_MODE=lambda-only,
                ENABLE_VISUAL_CAPTURE=false
            }"
        echo "✅ Rolled back to Lambda-only processing"
        ;;
    "infrastructure")
        aws cloudformation cancel-update-stack \
            --stack-name "genai-tweet-digest-$ENVIRONMENT"
        echo "✅ Infrastructure rollback initiated"
        ;;
    *)
        echo "❌ Unknown rollback type: $ROLLBACK_TYPE"
        exit 1
        ;;
esac
```

## Summary

### Deployment Order

1. **Infrastructure** (CloudFormation) 
2. **Lambda Functions** (zip files)
3. **EC2 Code** (AMI + S3 artifacts)
4. **Configuration** (environment variables)
5. **Validation** (health checks)

### Key Commands

```bash
# Full deployment
./scripts/deploy.sh production true true

# Code-only deployment  
./scripts/deploy.sh production false true

# Rollback to safe mode
./scripts/rollback.sh production lambda-only

# Validate deployment
./scripts/validate-deployment.sh production
```

### Best Practices

1. **Always deploy to development first**
2. **Use feature flags for gradual rollouts**
3. **Monitor costs and performance metrics**
4. **Keep rollback scripts ready**
5. **Test both processing modes in staging**
6. **Use infrastructure as code for all resources**

This deployment strategy ensures reliable, repeatable deployments with minimal risk and maximum flexibility for your hybrid architecture. 