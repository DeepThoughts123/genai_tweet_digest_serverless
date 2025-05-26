# Development Setup Guide

## Overview

This guide helps developers set up their local environment for working on the GenAI Tweets Digest serverless application.

## 🔧 Prerequisites

1. **Python 3.9+** installed
2. **AWS CLI** configured with appropriate credentials
3. **Git** for version control

## 📦 Package Installation Requirements

**IMPORTANT**: Always use the standard PyPI index when installing packages:

```bash
# For individual packages
pip install --index-url https://pypi.org/simple package-name

# For requirements files
pip install --index-url https://pypi.org/simple -r requirements.txt
```

This ensures you get packages from the official PyPI repository and avoids potential issues with private package repositories.

## 🚀 Quick Setup

### 1. Clone and Navigate
```bash
git clone <repository-url>
cd genai_tweet_digest_serverless
```

### 2. Activate Virtual Environment and Install Dependencies
```bash
# Activate the virtual environment
source .venv311/bin/activate

# Install development and testing dependencies
pip install --index-url https://pypi.org/simple -r dev-requirements.txt

# Install production dependencies (for Lambda functions)
pip install --index-url https://pypi.org/simple -r lambdas/requirements.txt
```

### 3. Set Environment Variables
```bash
# AWS Configuration
export AWS_PROFILE=personal
export AWS_REGION=us-east-1

# API Keys (for testing)
export TWITTER_BEARER_TOKEN="your_twitter_token"
export GEMINI_API_KEY="your_gemini_key"
export FROM_EMAIL="your-verified-ses-email@domain.com"

# Verify AWS credentials
aws sts get-caller-identity
```

## 🧪 Running Tests

### Local Unit Tests
```bash
# Activate virtual environment first
source .venv311/bin/activate

# Navigate to lambdas directory
cd lambdas

# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_email_verification_simple.py -v

# Run with coverage
python -m pytest tests/ --cov=shared --cov-report=html
```

### Integration Tests
```bash
# Run end-to-end tests against deployed infrastructure
./scripts/e2e-test.sh --functional-only
```

## 🔨 Development Workflow

### 1. Code Quality
```bash
# Format code
black lambdas/

# Check linting
flake8 lambdas/

# Type checking
mypy lambdas/shared/
```

### 2. Testing New Features
```bash
# 1. Write tests first
# 2. Run tests locally
python -m pytest tests/test_your_feature.py -v

# 3. Test deployment
./scripts/deploy.sh

# 4. Run integration tests
./scripts/e2e-test.sh
```

### 3. Email Verification Testing
```bash
# Test email verification service locally
python -m pytest tests/test_email_verification.py::TestEmailVerificationService -v

# Test subscription flow
python -m pytest tests/test_email_verification.py::TestSubscriptionWithVerification -v
```

## 📁 Project Structure for Development

```
genai_tweet_digest_serverless/
├── lambdas/                     # Lambda function code
│   ├── shared/                  # Shared utilities
│   ├── subscription/            # Subscription handler
│   ├── weekly-digest/           # Digest generation
│   ├── email-verification/      # Email verification handler
│   ├── tests/                   # Unit and integration tests
│   └── requirements.txt         # Production dependencies
├── dev-requirements.txt         # Development dependencies
├── scripts/                     # Deployment and utility scripts
├── docs/                        # Documentation
└── README-SERVERLESS.md         # Main project documentation
```

## 🐛 Debugging

### Local Development
```bash
# Run Python debugger
python -m pdb lambdas/shared/email_verification_service.py

# Interactive Python shell with project imports
cd lambdas
python -c "
import sys
sys.path.append('shared')
from shared.email_verification_service import EmailVerificationService
# Now you can test interactively
"
```

### AWS Lambda Debugging
```bash
# Check Lambda logs
aws logs tail /aws/lambda/genai-tweets-digest-subscription-production --follow

# Invoke Lambda locally (if using SAM)
sam local invoke SubscriptionFunction --event test-events/subscription.json
```

## 🔐 Security Notes

1. **Never commit API keys** to version control
2. **Use environment variables** for sensitive configuration
3. **Verify SES emails** before testing email functionality
4. **Use least privilege** AWS IAM policies

## 📝 Common Development Tasks

### Adding New Tests
```bash
# Create test file
touch lambdas/tests/test_new_feature.py

# Follow existing test patterns
# Use moto for AWS service mocking
# Include both success and failure scenarios
```

### Updating Dependencies
```bash
# Update development dependencies
pip install --index-url https://pypi.org/simple --upgrade -r dev-requirements.txt

# Update Lambda dependencies
pip install --index-url https://pypi.org/simple --upgrade -r lambdas/requirements.txt
```

### Testing Email Verification Flow
```bash
# 1. Deploy with email verification enabled
./scripts/deploy.sh

# 2. Test subscription
curl -X POST https://api-url/subscribe -d '{"email": "test@example.com"}'

# 3. Check verification email in logs
aws logs tail /aws/lambda/genai-tweets-digest-subscription-production

# 4. Test verification endpoint
curl "https://api-url/verify?token=your-verification-token"
```

## 🚨 Troubleshooting

### Common Issues

1. **Import Errors in Tests**
   - **Symptom**: `ModuleNotFoundError`, `ImportError: attempted relative import with no known parent package`, etc., during unit tests.
   - **Solution**: This project uses a specific Python import strategy to balance local testability with AWS Lambda deployment requirements.
     - Ensure unit tests are run via `./scripts/run-unit-tests.sh`. This script handles setting the correct Current Working Directory (`lambdas/`) and relies on `sys.path` modifications within test files (`lambdas/tests/test_lambda_functions.py`) for proper module resolution.
     - Refer to the "Python Import Strategy for Local Testing and Lambda Deployment" section in `docs/TESTING_GUIDE.md` for a detailed explanation of the import patterns and test setup.
   - **Quick Check Command from `lambdas/` directory** (if `run-unit-tests.sh` is not used):
     ```bash
     # From project_root/lambdas/ directory:
     python -m unittest tests.test_your_module -v
     ```

2. **AWS Credentials Issues**
   ```bash
   # Check current profile
   aws configure list
   
   # Set correct profile
   export AWS_PROFILE=personal
   ```

3. **Package Installation Issues**
   ```bash
   # Always use the standard PyPI index
   pip install --index-url https://pypi.org/simple package-name
   ```

4. **Moto Mock Issues**
   ```bash
   # Ensure moto is installed with correct extras
   pip install --index-url https://pypi.org/simple 'moto[dynamodb,ses]'
   ```

## 📚 Additional Resources

- [AWS Lambda Python Development](https://docs.aws.amazon.com/lambda/latest/dg/python-programming-model.html)
- [Pytest Documentation](https://docs.pytest.org/)
- [Moto Documentation](https://docs.getmoto.org/)
- [Email Verification Setup Guide](./EMAIL_VERIFICATION_SETUP.md)

## 🎓 Recent Development Lessons Learned

### Email Verification Implementation

#### Virtual Environment Best Practices

**Critical:** Always activate the virtual environment before any development work:
```bash
# ALWAYS start with this
source .venv311/bin/activate

# Verify you're in the right environment
which python
# Should show: /path/to/project/.venv311/bin/python
```

**Package Installation Pattern:**
```bash
# For development dependencies
pip install --index-url https://pypi.org/simple -r dev-requirements.txt

# For testing email verification
pip install --index-url https://pypi.org/simple 'moto[dynamodb,ses]' pytest

# For Lambda function dependencies
pip install --index-url https://pypi.org/simple -r lambdas/requirements.txt
```

#### Function-Specific Requirements

**Lesson:** Different Lambda functions need different dependencies. Create minimal requirements files:

```bash
# For email verification (lightweight)
# lambdas/email-verification-requirements.txt
boto3>=1.34.0
botocore>=1.34.0

# For main functions (full dependencies)
# lambdas/requirements.txt
boto3>=1.34.0
google-generativeai>=0.3.0
# ... other dependencies
```

#### Testing Email Verification Locally

**Setup:**
```bash
source .venv311/bin/activate
cd lambdas
python -m pytest tests/test_email_verification_simple.py -v
```

**Test Structure:**
- Use `@mock_aws` decorator (newer moto syntax)
- Test both success and failure scenarios
- Mock DynamoDB and SES services
- Validate email content and token generation

#### Deployment Script Integration

**Updated deployment workflow:**
```bash
# 1. Activate environment
source .venv311/bin/activate

# 2. Package with correct index
pip install --index-url https://pypi.org/simple -r requirements.txt -t build/

# 3. Deploy infrastructure first
aws cloudformation deploy ...

# 4. Update Lambda code
aws lambda update-function-code ...

# 5. Force API Gateway deployment (critical for new endpoints)
aws apigateway create-deployment --rest-api-id API_ID --stage-name production
```

### Common Development Pitfalls

#### 1. Shell Environment Issues

**Problem:** AWS CLI commands fail due to shell configuration interference.

**Solution:** Use clean shell execution for AWS commands:
```bash
zsh -d -f -c "aws command-here | cat"
```

#### 2. Lambda Package Size Issues

**Problem:** Lambda packages exceed 50MB limit due to heavy dependencies.

**Solutions:**
- Create function-specific requirements files
- Use S3 for large packages
- Optimize dependencies (remove unused packages)

#### 3. API Gateway Deployment Timing

**Problem:** New API methods not accessible after CloudFormation deployment.

**Solution:** Always create new API Gateway deployment:
```bash
aws apigateway create-deployment --rest-api-id API_ID --stage-name production
```

#### 4. Environment Variable Validation

**Problem:** Lambda functions fail due to missing environment variables.

**Solutions:**
- Provide all variables to all functions (simplest)
- Make validation function-aware
- Use function-specific variable sets

### Testing Best Practices

#### Email Verification Testing

```bash
# Local unit tests
python -m pytest tests/test_email_verification_simple.py -v

# Integration testing
curl -X POST https://api-url/subscribe -d '{"email": "test@example.com"}'
curl "https://api-url/verify?token=test-token"

# Check Lambda logs
aws logs tail /aws/lambda/function-name --follow
```

#### SES Testing Requirements

```bash
# Verify sender email for testing
aws ses verify-email-identity --email-address sender@domain.com --region us-east-1

# Check verification status
aws ses get-identity-verification-attributes --identities sender@domain.com --region us-east-1
```

### Performance Optimization

#### Lambda Cold Starts

- **Email verification:** ~2-3 seconds (minimal dependencies)
- **Subscription:** ~4-5 seconds (heavier dependencies)
- **Weekly digest:** ~5-8 seconds (full dependencies)

**Optimization strategies:**
- Use minimal dependencies for lightweight functions
- Consider provisioned concurrency for critical functions
- Optimize package size and memory allocation

#### Package Size Optimization

```bash
# Check package sizes
ls -lh *.zip

# Optimize by removing unnecessary files
zip -d package.zip "*.pyc" "__pycache__/*"
```

---

> **Remember**: Always use `--index-url https://pypi.org/simple` for pip installations in this project! 