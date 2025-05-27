# GenAI Tweets Digest - Serverless Architecture

## 🎯 Overview

This is a **cost-optimized serverless version** of the GenAI Tweets Digest that eliminates the need for 24/7 running infrastructure. The system now runs on AWS Lambda functions triggered by events, reducing monthly costs from $50-200+ to just $5-15.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Static Site   │    │  Lambda + S3    │    │  External APIs  │
│ (S3+CloudFront) │◄──►│  (Event-driven) │◄──►│ Twitter/Gemini  │
│                 │    │   Pay-per-use   │    │ Amazon SES      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Components

- **Static Website**: S3 + CloudFront for the landing page
- **Subscription API**: Lambda function triggered by API Gateway
- **Weekly Processing**: Lambda function triggered by EventBridge (weekly schedule)
- **Data Storage**: DynamoDB for subscribers, S3 for tweets and configuration
- **Email Service**: Amazon SES for digest distribution

## 💰 Cost Comparison

| Component | Current (Kubernetes) | Serverless | Savings |
|-----------|---------------------|------------|---------|
| Compute | $30-100/month | $1-3/month | 90-97% |
| Load Balancer | $15-25/month | $0.50/month | 98% |
| Storage | $5-10/month | $1-2/month | 80% |
| Monitoring | $10-20/month | $0/month | 100% |
| **Total** | **$60-155/month** | **$4-10/month** | **85-95%** |

## 🚀 Quick Start

### Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured (`aws configure`)
3. **API Keys**:
   - Twitter Bearer Token
   - Google Gemini API Key
4. **Verified SES Email** for sending digests

### 1. Set Environment Variables

```bash
# Set AWS Profile (use 'personal' profile for this project)
export AWS_PROFILE=personal

# Set API keys and configuration
export TWITTER_BEARER_TOKEN="your_twitter_bearer_token"
export GEMINI_API_KEY="your_gemini_api_key"
export FROM_EMAIL="your_verified_ses_email@domain.com"
export AWS_REGION="us-east-1"  # Optional, defaults to us-east-1

# Verify AWS credentials are working
aws sts get-caller-identity
```

**📦 Important**: For all pip installations in this project, always use:
```bash
pip install --index-url https://pypi.org/simple package-name
```

**🐍 Virtual Environment**: Always activate the virtual environment for local development:
```bash
source .venv311/bin/activate
```

### 2. Deploy Infrastructure

```bash
# Deploy everything with one command
./scripts/deploy.sh
```

This script will:
- ✅ Package Lambda functions
- ✅ Deploy CloudFormation stack
- ✅ Update function code
- ✅ Upload configuration to S3
- ✅ Display deployment outputs

### 3. Setup Frontend

```bash
# Prepare static frontend
./scripts/setup-frontend.sh
```

### 4. Upload Website

After deployment, upload your static website to the S3 bucket:

```bash
# Get bucket name from CloudFormation outputs
WEBSITE_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name genai-tweets-digest-production \
  --query 'Stacks[0].Outputs[?OutputKey==`WebsiteBucketName`].OutputValue' \
  --output text)

# Upload static files
aws s3 sync frontend-static/out/ s3://$WEBSITE_BUCKET/
```

## 📁 Directory Structure

```
genai_tweets_digest/
├── 📁 lambdas/                  # AWS Lambda functions
│   ├── subscription/            # Email subscription handler
│   ├── weekly-digest/           # Weekly processing
│   ├── shared/                  # Shared utilities
│   └── requirements.txt         # Python dependencies
├── 📁 frontend-static/          # Static website build
├── 📁 infrastructure-aws/       # CloudFormation templates
├── 📁 data/                     # Configuration files
│   └── accounts.json           # Curated Twitter accounts
├── 📁 scripts/                 # Deployment scripts
│   ├── deploy.sh               # Main deployment script
│   └── setup-frontend.sh       # Frontend preparation
└── 📄 README-SERVERLESS.md     # This file
```

## 🔧 Configuration

### Twitter Accounts

Edit `data/accounts.json` to customize the list of accounts to monitor:

```json
{
  "influential_accounts": [
    "AndrewYNg",
    "OpenAI", 
    "GoogleDeepMind",
    "ylecun",
    "karpathy"
  ]
}
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TWITTER_BEARER_TOKEN` | Twitter API Bearer Token | ✅ |
| `GEMINI_API_KEY` | Google Gemini API Key | ✅ |
| `FROM_EMAIL` | Verified SES email address | ✅ |
| `AWS_REGION` | AWS region for deployment | ❌ (default: us-east-1) |
| `ENVIRONMENT` | Environment name | ❌ (default: production) |

## 📅 Scheduling

The weekly digest runs automatically every **Sunday at 9 AM UTC**. You can modify the schedule in the CloudFormation template:

```yaml
ScheduleExpression: "cron(0 9 ? * SUN *)"  # Every Sunday at 9 AM UTC
```

## 🧪 Testing

This project includes a suite of local unit tests and integration tests. For comprehensive details on testing procedures, including the Python import strategy for local unit tests vs. Lambda deployment, please refer to the **[Testing Guide](docs/TESTING_GUIDE.md)**.

### Comprehensive Testing Results ✅ PRODUCTION READY

**Achievement**: **100% Frontend Test Success Rate** and **99% Overall System Test Success**

| Testing Category | Tests Passed | Total Tests | Success Rate | Status |
|------------------|--------------|-------------|--------------|--------|
| **Backend Unit Tests** | 28 | 28 | **100%** | ✅ |
| **Frontend Tests** | 24 | 24 | **100%** | ✅ |
| **E2E Integration Tests** | 23 | 24 | **96%** | ✅ |
| **Overall System** | **75** | **76** | **99%** | ✅ |

### Testing Infrastructure

**Backend Testing:**
- Complete Lambda function validation (subscription, weekly digest, email verification)
- AWS service integration testing (DynamoDB, S3, SES, API Gateway)
- External API integration (Twitter, Gemini AI)
- Error handling and edge case validation

**Frontend Testing:**
- React component testing with Jest and React Testing Library
- API integration testing with AWS API Gateway
- Complete user journey validation (form submission, error handling, loading states)
- Accessibility compliance testing (ARIA attributes, keyboard navigation)

**Enhanced Features:**
- Environment-aware API service design (browser, SSR, Jest compatibility)
- Complete Headers API mocking for reliable fetch testing
- Comprehensive error scenario coverage (all HTTP status codes)
- Perfect test-component behavior alignment

### Quick Testing Commands

**Run Backend Tests:**
```bash
# Ensure you have activated the virtual environment and installed dependencies
# (see Prerequisites and docs/DEVELOPMENT_SETUP.md)
./scripts/run-unit-tests.sh
```

**Run Frontend Tests:**
```bash
cd frontend-static
npm test

# Run with coverage
npm run test:coverage
```

**Run End-to-End Tests:**
```bash
# Run comprehensive E2E testing (requires deployed infrastructure)
./scripts/test-serverless.sh
```

For detailed testing results and learnings, see **[Comprehensive Testing Results](docs/COMPREHENSIVE_TESTING_RESULTS.md)**.

To run local frontend development server and tests:
```bash
cd frontend
npm run dev
# (Refer to docs/FRONTEND_TESTING_GUIDE.md for more details)
```

### Test Subscription with Email Verification

```bash
# Set AWS Profile
export AWS_PROFILE=personal

# Get API endpoint from CloudFormation outputs (use actual stack name)
API_URL=$(zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation describe-stacks \
  --stack-name genai-tweets-digest-20250525-210414 \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==\`SubscriptionEndpoint\`].OutputValue' \
  --output text | cat")

# Test subscription (this will send a verification email)
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"email": "your-verified-email@domain.com"}'

# Expected response: "Verification email sent. Please check your inbox."
```

### Email Verification Flow ✅ PRODUCTION READY

1. **User subscribes** → Receives verification email
2. **User clicks verification link** → Email is verified and subscription activated
3. **User receives weekly digests** → Only verified subscribers get emails

**Status**: ✅ **Fully implemented and tested** - Complete double opt-in verification system with professional HTML emails, security features, and comprehensive error handling.

**Note**: You need to verify your sender email in SES first:
```bash
export AWS_PROFILE=personal
aws ses verify-email-identity --email-address your-sender@domain.com
```

### Test Weekly Digest (Adhoc Run)

```bash
# Set AWS Profile
export AWS_PROFILE=personal

# Create payload file for clean execution
echo '{"source": "manual", "detail-type": "Manual Trigger"}' > /tmp/digest_payload.json

# Manually trigger the weekly digest function using clean shell execution
zsh -d -f -c "export AWS_PROFILE=personal && aws lambda invoke \
  --function-name genai-tweets-digest-weekly-digest-production \
  --payload file:///tmp/digest_payload.json \
  --region us-east-1 \
  /tmp/digest_response.json \
  --cli-binary-format raw-in-base64-out | cat"

# Check the response
cat /tmp/digest_response.json | jq .

# Monitor the execution logs
aws logs tail /aws/lambda/genai-tweets-digest-weekly-digest-production --follow
```

## 📊 Monitoring

### CloudWatch Logs

View Lambda function logs:

```bash
# Subscription function logs
aws logs tail /aws/lambda/genai-tweets-digest-subscription-production --follow

# Weekly digest function logs
aws logs tail /aws/lambda/genai-tweets-digest-weekly-digest-production --follow
```

### DynamoDB Data

Check subscriber data:

```bash
# List all subscribers
aws dynamodb scan --table-name genai-tweets-digest-subscribers-production
```

### S3 Data

View stored tweets and digests:

```bash
# List stored data
aws s3 ls s3://genai-tweets-digest-data-production/tweets/ --recursive
```

## 🔄 Data Portability

All data is stored in easily portable formats:

- **Subscribers**: DynamoDB (can export to JSON)
- **Tweets**: S3 as JSON files
- **Configuration**: S3 as JSON files

### Export Data

```bash
# Export subscribers
aws dynamodb scan \
  --table-name genai-tweets-digest-subscribers-production \
  --output json > subscribers-backup.json

# Download all tweet data
aws s3 sync s3://genai-tweets-digest-data-production/tweets/ ./tweets-backup/

# Download configuration
aws s3 cp s3://genai-tweets-digest-data-production/config/accounts.json ./accounts-backup.json
```

## 🛠️ Maintenance

### Update Twitter Accounts

1. Edit `data/accounts.json`
2. Upload to S3:
   ```bash
   aws s3 cp data/accounts.json s3://genai-tweets-digest-data-production/config/accounts.json
   ```

### Update Lambda Code

```bash
# Redeploy with updated code
./scripts/deploy.sh
```

### Update Frontend

```bash
# Rebuild and upload
./scripts/setup-frontend.sh
aws s3 sync frontend-static/out/ s3://$WEBSITE_BUCKET/
```

## 🚨 Troubleshooting

### Common Issues

1. **Missing Environment Variables**
   ```bash
   # Check if all required variables are set
   echo $TWITTER_BEARER_TOKEN
   echo $GEMINI_API_KEY
   echo $FROM_EMAIL
   ```

2. **SES Email Not Verified**
   ```bash
   # Verify your email in SES
   aws ses verify-email-identity --email-address your-email@domain.com
   ```

3. **Lambda Function Timeout**
   - Weekly digest function has 15-minute timeout
   - If processing takes longer, consider reducing the number of accounts or tweets per account

4. **API Gateway CORS Issues**
   - The CloudFormation template includes CORS configuration
   - If issues persist, check the API Gateway console

### Logs and Debugging

```bash
# Set AWS Profile
export AWS_PROFILE=personal

# Check CloudFormation stack status (use actual stack name)
zsh -d -f -c "export AWS_PROFILE=personal && aws cloudformation describe-stacks \
  --stack-name genai-tweets-digest-20250525-210414 \
  --region us-east-1 | cat"

# View Lambda function configuration
zsh -d -f -c "export AWS_PROFILE=personal && aws lambda get-function \
  --function-name genai-tweets-digest-weekly-digest-production \
  --region us-east-1 | cat"

# Check recent Lambda invocations
zsh -d -f -c "export AWS_PROFILE=personal && aws logs describe-log-groups \
  --log-group-name-prefix /aws/lambda/genai-tweets-digest \
  --region us-east-1 | cat"
```

## 🔐 Security

- **IAM Roles**: Minimal permissions for Lambda functions
- **API Keys**: Stored as CloudFormation parameters (encrypted)
- **CORS**: Properly configured for frontend access
- **S3 Buckets**: Private data bucket, public website bucket

## 📈 Scaling

The serverless architecture automatically scales:

- **Lambda**: Handles concurrent executions automatically
- **DynamoDB**: Pay-per-request scaling
- **S3**: Unlimited storage
- **SES**: Handles email volume automatically

## 🆘 Support

If you encounter issues:

1. Check CloudWatch logs for error details
2. Verify all environment variables are set correctly
3. Ensure SES email is verified
4. Check AWS service limits and quotas

## 🎉 Benefits of Serverless Migration

✅ **85-95% cost reduction**  
✅ **Zero infrastructure maintenance**  
✅ **Automatic scaling**  
✅ **Pay only for actual usage**  
✅ **Easy data portability**  
✅ **Simplified deployment**  
✅ **Built-in monitoring**  

## 📚 Documentation

For detailed implementation guidance and lessons learned:

- **[Development Setup Guide](docs/DEVELOPMENT_SETUP.md)** - Updated with email verification lessons and virtual environment best practices
- **[Email Verification Setup](docs/EMAIL_VERIFICATION_SETUP.md)** - Updated with implementation lessons, deployment challenges, and solutions
- **[Email Verification Testing Results](docs/EMAIL_VERIFICATION_TESTING_RESULTS.md)** - ✅ **NEW** - Complete end-to-end testing validation results
- **[AWS CLI Best Practices](docs/AWS_CLI_BEST_PRACTICES.md)** - Updated with Lambda packaging, CloudFormation, and deployment lessons
- **[E2E Testing Guide](docs/E2E_TESTING_PLAN.md)** - Comprehensive testing strategy and implementation
- **[Implementation Progress](docs/IMPLEMENTATION_PROGRESS.md)** - Updated with email verification completion status

### Recent Documentation Updates

The documentation has been enhanced with lessons learned from implementing the email verification system, including:

- **Lambda Function Packaging Optimization** - Reducing package sizes from 51MB to 15MB
- **CloudFormation Template Management** - Adding new Lambda functions and API Gateway endpoints
- **Environment Variable Management** - Handling function-specific requirements
- **SES Integration Testing** - Working with sandbox mode and email verification
- **API Gateway Deployment Timing** - Ensuring new endpoints are accessible
- **Virtual Environment Best Practices** - Consistent development environment setup

---

> **Migration from Kubernetes**: This serverless version provides the same functionality as the original Kubernetes-based system but with dramatically reduced costs and complexity. All core features (tweet processing, categorization, summarization, email distribution) are preserved while eliminating unnecessary infrastructure overhead. 