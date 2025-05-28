#!/bin/bash

# Optimized Lambda Deployment Script
# Uses function-specific requirements to minimize package sizes

# Attempt to load .env file from project root if it exists
if [ -f "$(dirname "$0")/../.env" ]; then
    echo "deploy-optimized.sh: Found .env file, sourcing variables..."
    set -a # Automatically export all variables
    source "$(dirname "$0")/../.env"
    set +a
    echo "deploy-optimized.sh: Variables from .env sourced."
fi

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting optimized Lambda deployment...${NC}"

# Check required environment variables
if [[ -z "$TWITTER_BEARER_TOKEN" || -z "$GEMINI_API_KEY" || -z "$FROM_EMAIL" ]]; then
    echo -e "${RED}❌ Missing required environment variables. Please set:${NC}"
    echo "  - TWITTER_BEARER_TOKEN"
    echo "  - GEMINI_API_KEY" 
    echo "  - FROM_EMAIL"
    exit 1
fi

cd lambdas

# Clean previous builds
echo -e "${YELLOW}🧹 Cleaning previous builds...${NC}"
rm -rf build/
rm -f *-function.zip # Remove all previously zipped functions
rm -f *-function-optimized.zip # Remove all previously optimized zipped functions

# Function definitions with their specific requirements
# Using a simpler array approach for broader compatibility
FUNC_NAMES=("subscription" "email-verification" "unsubscribe" "weekly-digest")
REQ_FILES=(
    "subscription-requirements.txt"
    "email-verification-requirements.txt"
    "unsubscribe-requirements.txt"
    "weekly-digest-requirements.txt"
)

# Build each function with optimized dependencies
for i in "${!FUNC_NAMES[@]}"; do
    func_name="${FUNC_NAMES[$i]}"
    req_file="${REQ_FILES[$i]}"
    output_zip_name="${func_name}-function.zip" # Standardized name for CFN
    
    echo -e "${BLUE}📦 Building ${func_name} function (using ${req_file}) into ${output_zip_name}...${NC}"
    
    # Create build directory
    mkdir -p "build/${func_name}"
    
    # Install function-specific dependencies
    echo "  Installing dependencies..."
    pip install --no-cache-dir -r "$req_file" -t "build/${func_name}/" \
        --index-url https://pypi.org/simple \
        --platform manylinux2014_x86_64 \
        --python-version 3.11 \
        --implementation cp \
        --abi cp311 \
        --only-binary=:all: \
        --quiet
    
    # Copy shared modules
    echo "  Copying shared modules..."
    cp -r shared "build/${func_name}/"
    
    # Copy function-specific code
    echo "  Copying function code..."
    cp "${func_name}/lambda_function.py" "build/${func_name}/"
    
    # Create optimized package with the standard name for CloudFormation
    echo "  Creating package ${output_zip_name}..."
    cd "build/${func_name}"
    zip -r "../../${output_zip_name}" . > /dev/null
    cd ../../
    
    # Report package size
    size=$(ls -lh "${output_zip_name}" | awk '{print $5}')
    echo -e "${GREEN}  ✅ ${output_zip_name} created (${size})${NC}"
done

echo -e "${GREEN}📊 Final package sizes:${NC}"
ls -lh *-function.zip # Should show the standardized names

# --- The rest of the script calls the main deploy.sh for CloudFormation ---
echo -e "${BLUE}☁️  Handing over to CloudFormation deployment (./scripts/deploy.sh)...${NC}"
cd ..

# Set a flag to indicate that optimized packages are already built
# This flag is checked by deploy.sh to skip its own packaging steps.
export OPTIMIZED_BUILD_COMPLETE=true

# Ensure STACK_NAME is exported for deploy.sh to use.
# If STACK_NAME was in .env, it's already exported due to `set -a`.
# If it was set in the calling shell, this export ensures it's passed down.
# If not set anywhere, deploy.sh will use its default.
echo "deploy-optimized.sh: Using STACK_NAME: ${STACK_NAME:-<deploy.sh default will be used>}"
export STACK_NAME 

# The main deploy.sh script will use the newly created *-function.zip files
# and the exported STACK_NAME.
./scripts/deploy.sh

# Unset the flag after use (optional, good practice)
export OPTIMIZED_BUILD_COMPLETE=

echo -e "${GREEN}🎉 Optimized Lambda packaging & CloudFormation deployment process initiated!${NC}"
echo -e "${YELLOW}💡 Next Steps:${NC}"
echo "  - Monitor CloudFormation stack creation in AWS console."
echo "  - After stack is created, verify Lambda functions and API Gateway endpoints."
echo "  - Test functionality (e.g., subscription, email verification)." 