#!/bin/bash

# GenAI Tweets Digest - Serverless Deployment Script
# This script deploys the entire serverless infrastructure to AWS

set -e

# Configuration
PROJECT_NAME="genai-tweets-digest"
ENVIRONMENT="${ENVIRONMENT:-production}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 GenAI Tweets Digest - Serverless Deployment${NC}"
echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"
echo ""

# Check required environment variables
check_env_vars() {
    echo -e "${YELLOW}Checking environment variables...${NC}"
    
    required_vars=("TWITTER_BEARER_TOKEN" "GEMINI_API_KEY" "FROM_EMAIL")
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        echo -e "${RED}❌ Missing required environment variables:${NC}"
        printf '%s\n' "${missing_vars[@]}"
        echo ""
        echo "Please set these variables and run again:"
        echo "export TWITTER_BEARER_TOKEN='your_token'"
        echo "export GEMINI_API_KEY='your_key'"
        echo "export FROM_EMAIL='your_verified_ses_email'"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All required environment variables are set${NC}"
}

# Check AWS CLI
check_aws_cli() {
    echo -e "${YELLOW}Checking AWS CLI...${NC}"
    
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        echo -e "${RED}❌ AWS credentials not configured. Please run 'aws configure'.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ AWS CLI is configured${NC}"
}

# Package Lambda functions
package_lambdas() {
    echo -e "${YELLOW}📦 Packaging Lambda functions...${NC}"
    
    # Create build directory
    BUILD_DIR="lambdas/build"
    rm -rf $BUILD_DIR
    mkdir -p $BUILD_DIR
    
    # Package subscription function
    echo "Packaging subscription function..."
    cd lambdas
    pip install --index-url https://pypi.org/simple -r requirements.txt -t build/subscription/
    cp -r shared build/subscription/
    cp subscription/lambda_function.py build/subscription/
    cd build/subscription
    zip -r ../../subscription-function.zip . > /dev/null
    cd ../../../
    
    # Package weekly digest function
    echo "Packaging weekly digest function..."
    cd lambdas
    pip install --index-url https://pypi.org/simple -r requirements.txt -t build/weekly-digest/
    cp -r shared build/weekly-digest/
    cp weekly-digest/lambda_function.py build/weekly-digest/
    cd build/weekly-digest
    zip -r ../../weekly-digest-function.zip . > /dev/null
    cd ../../../
    
    # Package email verification function
    echo "Packaging email verification function..."
    cd lambdas
    pip install --index-url https://pypi.org/simple -r requirements.txt -t build/email-verification/
    cp -r shared build/email-verification/
    cp email-verification/lambda_function.py build/email-verification/
    cd build/email-verification
    zip -r ../../email-verification-function.zip . > /dev/null
    cd ../../../
    
    echo -e "${GREEN}✅ Lambda functions packaged${NC}"
}

# Upload accounts configuration to S3
upload_config() {
    echo -e "${YELLOW}📤 Uploading configuration to S3...${NC}"
    
    BUCKET_NAME="${PROJECT_NAME}-data-${ENVIRONMENT}"
    
    # Check if bucket exists, create if not
    if ! aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
        echo "Uploading accounts configuration..."
        aws s3 cp data/accounts.json "s3://$BUCKET_NAME/config/accounts.json"
        echo -e "${GREEN}✅ Configuration uploaded${NC}"
    else
        echo -e "${YELLOW}⚠️  Data bucket not found. Will be created by CloudFormation.${NC}"
    fi
}

# Deploy CloudFormation stack
deploy_infrastructure() {
    echo -e "${YELLOW}🏗️  Deploying infrastructure...${NC}"
    
    STACK_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    
    aws cloudformation deploy \
        --template-file infrastructure-aws/cloudformation-template.yaml \
        --stack-name $STACK_NAME \
        --parameter-overrides \
            ProjectName=$PROJECT_NAME \
            Environment=$ENVIRONMENT \
            TwitterBearerToken=$TWITTER_BEARER_TOKEN \
            GeminiApiKey=$GEMINI_API_KEY \
            FromEmail=$FROM_EMAIL \
        --capabilities CAPABILITY_NAMED_IAM \
        --region $AWS_REGION
    
    echo -e "${GREEN}✅ Infrastructure deployed${NC}"
}

# Update Lambda function code
update_lambda_code() {
    echo -e "${YELLOW}🔄 Updating Lambda function code...${NC}"
    
    # Update subscription function
    aws lambda update-function-code \
        --function-name "${PROJECT_NAME}-subscription-${ENVIRONMENT}" \
        --zip-file fileb://subscription-function.zip \
        --region $AWS_REGION > /dev/null
    
    # Update weekly digest function
    aws lambda update-function-code \
        --function-name "${PROJECT_NAME}-weekly-digest-${ENVIRONMENT}" \
        --zip-file fileb://weekly-digest-function.zip \
        --region $AWS_REGION > /dev/null
    
    # Update email verification function
    aws lambda update-function-code \
        --function-name "${PROJECT_NAME}-email-verification-${ENVIRONMENT}" \
        --zip-file fileb://email-verification-function.zip \
        --region $AWS_REGION > /dev/null
    
    echo -e "${GREEN}✅ Lambda functions updated${NC}"
}

# Get stack outputs
get_outputs() {
    echo -e "${YELLOW}📋 Getting deployment outputs...${NC}"
    
    STACK_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    
    echo ""
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    echo ""
    echo "📊 Stack Outputs:"
    
    aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $AWS_REGION \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table
    
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Upload your static website to the Website S3 bucket"
    echo "2. Verify your FROM_EMAIL address in Amazon SES"
    echo "3. Upload the accounts configuration if not done automatically"
    echo "4. Test the subscription endpoint"
    echo "5. Manually trigger the weekly digest function to test"
}

# Cleanup build files
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up...${NC}"
    rm -rf lambdas/build/
    rm -f subscription-function.zip
    rm -f weekly-digest-function.zip
    rm -f email-verification-function.zip
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Main deployment flow
main() {
    check_env_vars
    check_aws_cli
    package_lambdas
    deploy_infrastructure
    update_lambda_code
    upload_config
    get_outputs
    cleanup
}

# Run main function
main 