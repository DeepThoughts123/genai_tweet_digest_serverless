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

# Check if we're in the right directory (project root)
if [ ! -d "lambdas" ]; then
    echo -e "${RED}❌ Error: lambdas directory not found. Please run this from the project root.${NC}"
    exit 1
fi

# Change to lambdas directory for test execution
cd lambdas
echo -e "${YELLOW}Changed current directory to $(pwd) for test execution.${NC}"
echo ""


# Create test results directory (relative to lambdas dir, e.g. lambdas/test-results)
mkdir -p test-results

# Function to run tests with coverage (not currently used by default)
run_tests() {
    local test_file="$1"
    local test_name="$2"
    
    echo -e "${YELLOW}Running $test_name...${NC}"
    
    # Assumes CWD is lambdas/
    # Install test dependencies if not already installed
    if [ ! -f ".test_deps_installed" ]; then # .test_deps_installed will be in lambdas/
        echo "Installing test dependencies..."
        pip install pytest pytest-cov coverage > /dev/null 2>&1
        touch .test_deps_installed
    fi
    
    # Run the specific test
    if python -m pytest "$test_file" -v --tb=short; then
        echo -e "${GREEN}✅ $test_name passed${NC}"
        return 0
    else
        echo -e "${RED}❌ $test_name failed${NC}"
        return 1
    fi
}

# Function to run tests with unittest
run_unittest() {
    local test_module_path="$1" # e.g., tests.test_tweet_services (relative to lambdas/)
    local test_name="$2"
    
    echo -e "${YELLOW}Running $test_name...${NC}"
    
    # CWD is lambdas/
    # Python's -m flag will search sys.path, which includes '.' (current dir)
    if python -m unittest "$test_module_path" -v; then
        echo -e "${GREEN}✅ $test_name passed${NC}"
        return 0
    else
        echo -e "${RED}❌ $test_name failed${NC}"
        return 1
    fi
}

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Test 1: Tweet Services Unit Tests
echo -e "${BLUE}📋 Testing Tweet Processing Services${NC}"
if run_unittest "tests.test_tweet_services" "Tweet Services"; then # Path relative to lambdas/
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
    FAILED_TESTS+=("Tweet Services")
fi
echo ""

# Test 2: Lambda Functions Unit Tests
echo -e "${BLUE}⚡ Testing Lambda Function Handlers${NC}"
if run_unittest "tests.test_lambda_functions" "Lambda Functions"; then # Path relative to lambdas/
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
    FAILED_TESTS+=("Lambda Functions")
fi
echo ""

# Test 3: Configuration Tests (CWD is lambdas/)
echo -e "${BLUE}⚙️  Testing Configuration Module${NC}"
if python -c "
import sys
import os
# Add 'shared' to sys.path (it's a subdir of current dir 'lambdas')
sys.path.insert(0, os.path.abspath('shared')) 
# sys.path.insert(0, os.path.abspath('.')) # Current dir 'lambdas' is already on path with -m

from config import LambdaConfig # Should find shared/config.py

# Test basic configuration
try:
    config_obj = LambdaConfig() # Renamed to avoid conflict with module
    print('✅ Configuration module loads successfully')
    
    if hasattr(config_obj, 'environment'):
        print('✅ Environment detection works')
    else:
        print('❌ Environment detection missing')
        exit(1)
        
    if hasattr(config_obj, 'validate_required_env_vars'):
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
echo ""

# Test 4: Import Tests (CWD is lambdas/)
echo -e "${BLUE}📦 Testing Module Imports${NC}"
if python -c "
import sys
import os
# CWD is lambdas/, which should be on sys.path implicitly when python -c is run.
# Ensure 'shared' can be imported as a package and its modules.

modules_to_test = [
    'shared.config',            # Test import shared.config
    'shared.tweet_services',    # Test import shared.tweet_services (will test its internal .config)
    'shared.dynamodb_service',  # Test import shared.dynamodb_service (will test its internal .config)
    'shared.ses_service',         # Test import shared.ses_service (will test its internal .config, .unsubscribe_service)
    'shared.email_verification_service',
    'shared.unsubscribe_service' # Test import shared.unsubscribe_service (will test its internal .config, .dynamodb_service)
]

failed_imports = []

for module_name in modules_to_test:
    try:
        __import__(module_name)
        print(f'✅ {module_name} imports successfully')
    except Exception as e:
        print(f'❌ {module_name} import failed: {e}')
        failed_imports.append(module_name)

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
echo ""

# Test 5: JSON Configuration Tests (CWD is lambdas/)
echo -e "${BLUE}📄 Testing JSON Configuration Files${NC}"
if python -c "
import json
import os

# Test accounts.json (path is now ../data/accounts.json)
try:
    with open('../data/accounts.json', 'r') as f: # Adjusted path
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
    print('❌ ../data/accounts.json not found') # Adjusted path in message
    exit(1)
except json.JSONDecodeError as e:
    print(f'❌ ../data/accounts.json is invalid JSON: {e}') # Adjusted path in message
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

# Test 6: Requirements Tests (CWD is lambdas/)
echo -e "${BLUE}📋 Testing Requirements File${NC}"
if python -c "
import os

# Check if requirements.txt exists (path is now 'requirements.txt')
try:
    with open('requirements.txt', 'r') as f: # Adjusted path
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
    print('❌ requirements.txt not found in lambdas/ directory') # Adjusted message
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

# Go back to project root before finishing
cd ..
echo -e "${YELLOW}Changed current directory back to $(pwd).${NC}"


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
    echo "2. Check Python path and module imports from within the 'lambdas' directory context."
    echo "3. Verify JSON configuration files are valid and paths are correct relative to 'lambdas/'."
    echo "4. Run individual tests for more detailed error messages (e.g., python -m unittest tests.test_module -v from 'lambdas/' dir)."
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