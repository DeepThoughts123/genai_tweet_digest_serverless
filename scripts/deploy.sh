#!/bin/bash

# GenAI Tweets Digest - Serverless Deployment Script
# This script deploys the entire serverless infrastructure to AWS

# Attempt to load .env file from project root if it exists
if [ -f "$(dirname "$0")/../.env" ]; then
    echo "Found .env file, sourcing variables..."
    set -a # Automatically export all variables
    source "$(dirname "$0")/../.env"
    set +a
    echo "Variables from .env sourced."
    echo "DEBUG: AWS_PROFILE after source is: [$AWS_PROFILE]"
else
    echo ".env file not found in project root ($(dirname "$0")/../)."
fi

set -e

# Configuration
PROJECT_NAME="genai-tweets-digest"
ENVIRONMENT="${ENVIRONMENT:-production}"
# AWS_REGION will be used if set from .env or environment
# AWS_PROFILE will be used if set from .env or environment
DEFAULT_STACK_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
# Use STACK_NAME from environment if set, otherwise use default
CFN_STACK_NAME=${STACK_NAME:-$DEFAULT_STACK_NAME}
PARAMS_FILE="/tmp/cf-params-${CFN_STACK_NAME}.json"
TEMPLATE_FILE="infrastructure-aws/cloudformation-template.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 GenAI Tweets Digest - Serverless Deployment${NC}"
echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"
echo "CloudFormation Stack Name: $CFN_STACK_NAME"
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
    
    local aws_cli_profile_arg=""
    local aws_cli_region_arg=""
    local profile_display_name="default"
    local region_display_name="CLI default or profile config"

    if [ -n "$AWS_PROFILE" ]; then
        aws_cli_profile_arg="--profile $AWS_PROFILE"
        profile_display_name="$AWS_PROFILE"
        echo "Attempting to use AWS Profile (from .env or environment): $AWS_PROFILE"
    else
        echo "AWS_PROFILE not set from .env or environment; will use default AWS CLI profile."
    fi

    if [ -n "$AWS_REGION" ]; then
        aws_cli_region_arg="--region $AWS_REGION"
        region_display_name="$AWS_REGION"
    else
        # Use the script's default AWS_REGION if $AWS_REGION is empty after .env sourcing
        # The script initializes AWS_REGION itself if not set by env or .env
        # However, the initial echo for AWS_REGION at the script top might show blank if .env doesn't set it AND it's not in shell env.
        # Let's ensure AWS_REGION used here is the one defined at the script top as default if not overridden
        # This is already implicitly handled as $AWS_REGION will hold the script's default if not set by .env
        echo "Attempting to use AWS Region: ${AWS_REGION:-using script default or AWS CLI default}"
        if [ -n "$AWS_REGION" ]; then # Check again in case it was set by script default
             aws_cli_region_arg="--region $AWS_REGION"
             region_display_name="$AWS_REGION"
        fi
    fi
    
    local cmd_to_check="aws sts get-caller-identity $aws_cli_profile_arg $aws_cli_region_arg"

    if ! $cmd_to_check &> /dev/null; then # Execute directly
        echo -e "${RED}❌ AWS credentials check failed. Profile: '$profile_display_name', Region: '$region_display_name'. Please verify AWS CLI configuration and that the profile/region combination is valid.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ AWS CLI is configured (For Profile: $profile_display_name, Region: $region_display_name)${NC}"
}

# Check if optimized build is already done
# This flag is set by deploy-optimized.sh
if [ "$OPTIMIZED_BUILD_COMPLETE" != "true" ]; then
    echo -e "${YELLOW}📦 Packaging Lambda functions using monolithic requirements.txt...${NC}"
    cd lambdas

    # Package subscription function
    echo "Packaging subscription function..."
    pip install --no-cache-dir -r requirements.txt -t build/subscription/ --index-url https://pypi.org/simple --platform manylinux2014_x86_64 --python-version 3.11 --implementation cp --abi cp311 --only-binary=:all: --quiet
    cp -r shared build/subscription/
    cp subscription/lambda_function.py build/subscription/
    cd build/subscription
    zip -r ../../subscription-function.zip . > /dev/null
    cd ../../

    # Package weekly digest function
    echo "Packaging weekly digest function..."
    pip install --no-cache-dir -r requirements.txt -t build/weekly-digest/ --index-url https://pypi.org/simple --platform manylinux2014_x86_64 --python-version 3.11 --implementation cp --abi cp311 --only-binary=:all: --quiet
    cp -r shared build/weekly-digest/
    cp weekly-digest/lambda_function.py build/weekly-digest/
    cd build/weekly-digest
    zip -r ../../weekly-digest-function.zip . > /dev/null
    cd ../../

    # Package email verification function
    echo "Packaging email verification function..."
    pip install --no-cache-dir -r requirements.txt -t build/email-verification/ --index-url https://pypi.org/simple --platform manylinux2014_x86_64 --python-version 3.11 --implementation cp --abi cp311 --only-binary=:all: --quiet
    cp -r shared build/email-verification/
    cp email-verification/lambda_function.py build/email-verification/
    cd build/email-verification
    zip -r ../../email-verification-function.zip . > /dev/null
    cd ../../

    # Package unsubscribe function
    echo "Packaging unsubscribe function..."
    pip install --no-cache-dir -r requirements.txt -t build/unsubscribe/ --index-url https://pypi.org/simple --platform manylinux2014_x86_64 --python-version 3.11 --implementation cp --abi cp311 --only-binary=:all: --quiet
    cp -r shared build/unsubscribe/
    cp unsubscribe/lambda_function.py build/unsubscribe/
    cd build/unsubscribe
    zip -r ../../unsubscribe-function.zip . > /dev/null
    cd ../../

    echo -e "${GREEN}✅ Lambda functions packaged${NC}"
    cd .. # Return to project root
else
    echo -e "${GREEN}📦 Optimized Lambda packages (from deploy-optimized.sh) already built. Skipping packaging step.${NC}"
fi

# Upload accounts configuration to S3
upload_config() {
    echo -e "${YELLOW}📤 Uploading configuration to S3...${NC}"
    
    local aws_profile_arg=""
    if [ -n "$AWS_PROFILE" ]; then aws_profile_arg="--profile $AWS_PROFILE"; fi
    local aws_region_arg=""
    if [ -n "$AWS_REGION" ]; then aws_region_arg="--region $AWS_REGION"; fi

    BUCKET_NAME="${PROJECT_NAME}-data-${ENVIRONMENT}"
    
    if ! aws s3api head-bucket --bucket "$BUCKET_NAME" $aws_profile_arg $aws_region_arg &> /dev/null; then # Execute directly
        echo -e "${YELLOW}⚠️  Data bucket '$BUCKET_NAME' not found or not accessible. It should be created by CloudFormation. Config upload skipped.${NC}"
    else
        echo "Uploading accounts configuration to s3://$BUCKET_NAME/config/accounts.json ..."
        if aws s3 cp data/accounts.json "s3://$BUCKET_NAME/config/accounts.json" $aws_profile_arg $aws_region_arg; then # Execute directly, show output
            echo -e "${GREEN}✅ Configuration uploaded${NC}"
        else
            echo -e "${RED}❌ Failed to upload configuration to S3.${NC}"
        fi
    fi
}

# Deploy CloudFormation stack
deploy_infrastructure() {
    echo -e "${YELLOW}🏗️  Deploying infrastructure...${NC}"
    
    echo "Generating CloudFormation parameters file: $PARAMS_FILE"
    # Use printf for safer value insertion into JSON, though direct expansion is often fine for these vars.
    # Ensuring variables are correctly escaped for JSON if they contain quotes/newlines is hard in pure bash.
    # For this case, assuming environment variables are clean enough for direct insertion.
    cat <<EOF > "$PARAMS_FILE"
[
  {"ParameterKey": "ProjectName", "ParameterValue": "${PROJECT_NAME}"},
  {"ParameterKey": "Environment", "ParameterValue": "${ENVIRONMENT}"},
  {"ParameterKey": "TwitterBearerToken", "ParameterValue": "${TWITTER_BEARER_TOKEN}"},
  {"ParameterKey": "GeminiApiKey", "ParameterValue": "${GEMINI_API_KEY}"},
  {"ParameterKey": "FromEmail", "ParameterValue": "${FROM_EMAIL}"}
]
EOF
    echo "Parameters file content being used by CloudFormation:"
    cat $PARAMS_FILE
    echo ""
    
    echo "Executing CloudFormation deployment for stack: $CFN_STACK_NAME"

    echo "DEBUG: PARAMS_FILE ($PARAMS_FILE) contents:"
    cat "$PARAMS_FILE"
    echo "DEBUG: Would run: aws cloudformation deploy --template-file $TEMPLATE_FILE --stack-name $CFN_STACK_NAME --parameters file://$PARAMS_FILE --capabilities CAPABILITY_NAMED_IAM --region $AWS_REGION --output json --no-fail-on-empty-changeset"

    # Check if stack exists
    if ! aws cloudformation describe-stacks --stack-name $CFN_STACK_NAME --region $AWS_REGION --profile $AWS_PROFILE > /dev/null 2>&1; then
        echo "Stack $CFN_STACK_NAME does not exist. Creating stack..."
        aws cloudformation create-stack \
            --stack-name $CFN_STACK_NAME \
            --template-body file://$TEMPLATE_FILE \
            --parameters file://$PARAMS_FILE \
            --capabilities CAPABILITY_NAMED_IAM \
            --region $AWS_REGION --profile $AWS_PROFILE
        
        echo "Waiting for stack $CFN_STACK_NAME to be created..."
        aws cloudformation wait stack-create-complete --stack-name $CFN_STACK_NAME --region $AWS_REGION --profile $AWS_PROFILE
    else
        echo "Stack $CFN_STACK_NAME exists. Updating stack..."
        aws cloudformation update-stack \
            --stack-name $CFN_STACK_NAME \
            --template-body file://$TEMPLATE_FILE \
            --parameters file://$PARAMS_FILE \
            --capabilities CAPABILITY_NAMED_IAM \
            --region $AWS_REGION --profile $AWS_PROFILE
        
        echo "Waiting for stack $CFN_STACK_NAME update to complete..."
        aws cloudformation wait stack-update-complete --stack-name $CFN_STACK_NAME --region $AWS_REGION --profile $AWS_PROFILE
    fi
    
    # Check the exit code of the deployment (the wait command will typically exit non-zero on failure)
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ CloudFormation deployment failed. Check output above and CloudFormation console events.${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ Infrastructure deployed/updated${NC}"
}

# Update Lambda function code
update_lambda_code() {
    echo -e "${YELLOW}🔄 Updating Lambda function code...${NC}"
    local aws_profile_arg=""
    if [ -n "$AWS_PROFILE" ]; then aws_profile_arg="--profile $AWS_PROFILE"; fi
    local aws_region_arg=""
    if [ -n "$AWS_REGION" ]; then aws_region_arg="--region $AWS_REGION"; fi
    local success=true

    echo "Updating subscription function..."
    zsh -d -f -c "export AWS_PROFILE=$AWS_PROFILE && aws lambda update-function-code --function-name ${CFN_STACK_NAME}-subscription --zip-file fileb://lambdas/subscription-function.zip --region $AWS_REGION --output json | cat || echo 'Error updating subscription function'"
    
    echo "Updating weekly digest function..."
    zsh -d -f -c "export AWS_PROFILE=$AWS_PROFILE && aws lambda update-function-code --function-name ${CFN_STACK_NAME}-weekly-digest --zip-file fileb://lambdas/weekly-digest-function.zip --region $AWS_REGION --output json | cat || echo 'Error updating weekly digest function'"
    
    echo "Updating email verification function..."
    zsh -d -f -c "export AWS_PROFILE=$AWS_PROFILE && aws lambda update-function-code --function-name ${CFN_STACK_NAME}-email-verification --zip-file fileb://lambdas/email-verification-function.zip --region $AWS_REGION --output json | cat || echo 'Error updating email verification function'"
    
    echo "Updating unsubscribe function..."
    zsh -d -f -c "export AWS_PROFILE=$AWS_PROFILE && aws lambda update-function-code --function-name ${CFN_STACK_NAME}-unsubscribe --zip-file fileb://lambdas/unsubscribe-function.zip --region $AWS_REGION --output json | cat || echo 'Error updating unsubscribe function'"
    
    if [ "$success" = true ]; then
        echo -e "${GREEN}✅ Lambda functions updated${NC}"
    else
        echo -e "${RED}❌ Some Lambda functions failed to update. Check AWS console.${NC}"
    fi
}

# Get stack outputs
get_outputs() {
    echo -e "${YELLOW}📋 Getting deployment outputs...${NC}"
    local aws_profile_arg=""
    if [ -n "$AWS_PROFILE" ]; then aws_profile_arg="--profile $AWS_PROFILE"; fi
    local aws_region_arg=""
    if [ -n "$AWS_REGION" ]; then aws_region_arg="--region $AWS_REGION"; fi

    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    echo ""
    echo -e "${YELLOW}📊 Stack Outputs:${NC}"
    
    STACK_OUTPUTS=$(zsh -d -f -c "export AWS_PROFILE=$AWS_PROFILE && aws cloudformation describe-stacks --stack-name $CFN_STACK_NAME --region $AWS_REGION --query 'Stacks[0].Outputs' --output json | cat")
    echo "$STACK_OUTPUTS" | jq -r '.[] | "\(.OutputKey): \(.OutputValue)"'
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
    rm -f unsubscribe-function.zip
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Main deployment flow
main() {
    check_env_vars
    check_aws_cli
    deploy_infrastructure
    update_lambda_code
    upload_config
    get_outputs
    cleanup
}

# Run main function
main 