#!/bin/bash
# Deploy Lambda functions for hybrid architecture

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
    
    # Navigate to source directory
    cd "lambdas/$source_dir"
    
    # Copy shared directory if it exists
    if [ -d "../shared" ]; then
        cp -r ../shared ./shared 2>/dev/null || true
    fi
    
    # Install dependencies if requirements.txt exists
    if [ -f "requirements.txt" ]; then
        echo "📥 Installing dependencies for $function_name..."
        pip install -r requirements.txt -t . --quiet
    fi
    
    # Create deployment package
    echo "📦 Creating deployment package..."
    zip -r "../$zip_name" . -x "*.pyc" "__pycache__/*" "tests/*" "*.log" "shared/__pycache__/*" > /dev/null
    
    # Clean up shared directory copy
    rm -rf shared 2>/dev/null || true
    
    cd ../..
    
    echo "🚀 Deploying $function_name..."
    
    # Check if function exists
    if aws lambda get-function --function-name "$PROJECT_NAME-$ENVIRONMENT-$function_name" > /dev/null 2>&1; then
        # Update existing function
        aws lambda update-function-code \
            --function-name "$PROJECT_NAME-$ENVIRONMENT-$function_name" \
            --zip-file "fileb://lambdas/$zip_name" \
            --region us-east-1 > /dev/null
    else
        echo "⚠️  Function $PROJECT_NAME-$ENVIRONMENT-$function_name not found. Deploy infrastructure first."
        return 1
    fi
    
    # Clean up zip file
    rm "lambdas/$zip_name"
    
    echo "✅ $function_name deployed successfully"
}

# Check if we're in the right directory
if [ ! -d "lambdas" ]; then
    echo "❌ Error: lambdas directory not found. Run this script from the project root."
    exit 1
fi

# Deploy each Lambda function
echo "📦 Deploying visual processing dispatcher..."
deploy_lambda "visual-dispatcher" "visual-processing-dispatcher" "visual-dispatcher.zip"

echo "📦 Deploying processing complete handler..."
deploy_lambda "processing-complete" "processing-complete-handler" "processing-complete.zip" 

echo "📦 Deploying weekly digest function..."
deploy_lambda "weekly-digest" "weekly-digest" "weekly-digest.zip"

echo ""
echo "✅ All Lambda functions deployed successfully!"
echo "🔍 You can test the deployment with:"
echo "   aws lambda invoke --function-name $PROJECT_NAME-$ENVIRONMENT-weekly-digest --payload '{\"test\": true}' response.json" 