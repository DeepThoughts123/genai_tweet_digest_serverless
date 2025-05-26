#!/bin/bash

# Unit Testing Script for Serverless GenAI Tweets Digest
# This script runs unit tests for the Lambda functions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Running Unit Tests for Serverless Lambda Functions${NC}"
echo ""

# Check if we're in the right directory
if [ ! -d "lambdas" ]; then
    echo -e "${RED}❌ Error: lambdas directory not found. Please run this from the project root.${NC}"
    exit 1
fi

# Create test results directory
mkdir -p test-results

# Function to run tests with coverage
run_tests() {
    local test_file="$1"
    local test_name="$2"
    
    echo -e "${YELLOW}Running $test_name...${NC}"
    
    cd lambdas
    
    # Install test dependencies if not already installed
    if [ ! -f ".test_deps_installed" ]; then
        echo "Installing test dependencies..."
        pip install pytest pytest-cov coverage > /dev/null 2>&1
        touch .test_deps_installed
    fi
    
    # Run the specific test
    if python -m pytest "$test_file" -v --tb=short; then
        echo -e "${GREEN}✅ $test_name passed${NC}"
        cd ..
        return 0
    else
        echo -e "${RED}❌ $test_name failed${NC}"
        cd ..
        return 1
    fi
}

# Function to run tests with unittest
run_unittest() {
    local test_file="$1"
    local test_name="$2"
    
    echo -e "${YELLOW}Running $test_name...${NC}"
    
    cd lambdas
    
    # Run the specific test
    if python -m unittest "$test_file" -v; then
        echo -e "${GREEN}✅ $test_name passed${NC}"
        cd ..
        return 0
    else
        echo -e "${RED}❌ $test_name failed${NC}"
        cd ..
        return 1
    fi
}

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Test 1: Tweet Services Unit Tests
echo -e "${BLUE}📋 Testing Tweet Processing Services${NC}"
if run_unittest "tests.test_tweet_services" "Tweet Services"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
    FAILED_TESTS+=("Tweet Services")
fi
echo ""

# Test 2: Lambda Functions Unit Tests
echo -e "${BLUE}⚡ Testing Lambda Function Handlers${NC}"
if run_unittest "tests.test_lambda_functions" "Lambda Functions"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
    FAILED_TESTS+=("Lambda Functions")
fi
echo ""

# Test 3: Configuration Tests
echo -e "${BLUE}⚙️  Testing Configuration Module${NC}"
cd lambdas
if python -c "
import sys
import os
sys.path.append('shared')
from config import LambdaConfig

# Test basic configuration
try:
    config = LambdaConfig()
    print('✅ Configuration module loads successfully')
    
    # Test environment detection
    if hasattr(config, 'environment'):
        print('✅ Environment detection works')
    else:
        print('❌ Environment detection missing')
        exit(1)
        
    # Test required methods
    if hasattr(config, 'validate_required_env_vars'):
        print('✅ Validation method exists')
    else:
        print('❌ Validation method missing')
        exit(1)
        
    print('✅ All configuration tests passed')
except Exception as e:
    print(f'❌ Configuration test failed: {e}')
    exit(1)
"; then
    echo -e "${GREEN}✅ Configuration tests passed${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Configuration tests failed${NC}"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("Configuration")
fi
cd ..
echo ""

# Test 4: Import Tests
echo -e "${BLUE}📦 Testing Module Imports${NC}"
cd lambdas
if python -c "
import sys
import os
sys.path.append('shared')

# Test all imports
modules_to_test = [
    'config',
    'tweet_services', 
    'dynamodb_service',
    'ses_service'
]

failed_imports = []

for module in modules_to_test:
    try:
        __import__(module)
        print(f'✅ {module} imports successfully')
    except Exception as e:
        print(f'❌ {module} import failed: {e}')
        failed_imports.append(module)

if failed_imports:
    print(f'❌ Failed to import: {failed_imports}')
    exit(1)
else:
    print('✅ All module imports successful')
"; then
    echo -e "${GREEN}✅ Import tests passed${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Import tests failed${NC}"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("Imports")
fi
cd ..
echo ""

# Test 5: JSON Configuration Tests
echo -e "${BLUE}📄 Testing JSON Configuration Files${NC}"
if python -c "
import json
import os

# Test accounts.json
try:
    with open('data/accounts.json', 'r') as f:
        accounts_data = json.load(f)
    
    if 'influential_accounts' in accounts_data:
        if isinstance(accounts_data['influential_accounts'], list):
            if len(accounts_data['influential_accounts']) > 0:
                print('✅ accounts.json is valid and contains accounts')
            else:
                print('❌ accounts.json is empty')
                exit(1)
        else:
            print('❌ influential_accounts is not a list')
            exit(1)
    else:
        print('❌ accounts.json missing influential_accounts key')
        exit(1)
        
except FileNotFoundError:
    print('❌ accounts.json not found')
    exit(1)
except json.JSONDecodeError as e:
    print(f'❌ accounts.json is invalid JSON: {e}')
    exit(1)

print('✅ JSON configuration tests passed')
"; then
    echo -e "${GREEN}✅ JSON configuration tests passed${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ JSON configuration tests failed${NC}"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("JSON Configuration")
fi
echo ""

# Test 6: Requirements Tests
echo -e "${BLUE}📋 Testing Requirements File${NC}"
if python -c "
import os

# Check if requirements.txt exists and is valid
try:
    with open('lambdas/requirements.txt', 'r') as f:
        requirements = f.read().strip().split('\n')
    
    required_packages = ['boto3', 'tweepy', 'google-generativeai', 'botocore']
    
    for package in required_packages:
        found = any(package in req for req in requirements)
        if found:
            print(f'✅ {package} found in requirements')
        else:
            print(f'❌ {package} missing from requirements')
            exit(1)
    
    print('✅ Requirements file is valid')
    
except FileNotFoundError:
    print('❌ requirements.txt not found')
    exit(1)
"; then
    echo -e "${GREEN}✅ Requirements tests passed${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Requirements tests failed${NC}"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("Requirements")
fi
echo ""

# Summary
echo -e "${BLUE}📊 Unit Test Summary${NC}"
echo "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
echo "Tests failed: ${RED}$TESTS_FAILED${NC}"

if [ $TESTS_FAILED -gt 0 ]; then
    echo ""
    echo -e "${RED}❌ Failed tests:${NC}"
    for test in "${FAILED_TESTS[@]}"; do
        echo "  - $test"
    done
    echo ""
    echo -e "${YELLOW}💡 Troubleshooting tips:${NC}"
    echo "1. Ensure all dependencies are installed: pip install -r lambdas/requirements.txt"
    echo "2. Check Python path and module imports"
    echo "3. Verify JSON configuration files are valid"
    echo "4. Run individual tests for more detailed error messages"
    exit 1
else
    echo ""
    echo -e "${GREEN}🎉 All unit tests passed! Your Lambda functions are ready for deployment.${NC}"
    echo ""
    echo -e "${BLUE}📋 Next steps:${NC}"
    echo "1. Run integration tests: ./scripts/test-serverless.sh"
    echo "2. Deploy to AWS: ./scripts/deploy.sh"
    echo "3. Test the deployed system end-to-end"
    exit 0
fi 