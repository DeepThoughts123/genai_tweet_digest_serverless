# Amazon SES Integration Guide

> **Overview**: This document provides detailed information about the Amazon SES email provider integration, including setup, configuration, and migration from SendGrid.

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Migration Guide](#migration-guide)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Overview

The GenAI Tweets Digest now supports Amazon Simple Email Service (SES) as an alternative to SendGrid for email distribution. This implementation follows a provider pattern that allows seamless switching between email services while maintaining the same API interface.

### Key Benefits
- **Cost Optimization**: Amazon SES offers competitive pricing for high-volume email sending
- **AWS Integration**: Native integration with AWS ecosystem and services
- **Reliability**: AWS SES provides high deliverability and uptime
- **Flexibility**: Easy switching between providers without code changes

### Implementation Highlights
- **Strategy Pattern**: Abstract `EmailProvider` base class with concrete implementations
- **Backward Compatibility**: Existing SendGrid functionality preserved
- **Configuration-Driven**: Provider selection via environment variables
- **Comprehensive Testing**: 48 total tests covering all scenarios

## Architecture

### Provider Pattern Implementation
```
EmailService
├── EmailProvider (Abstract Base Class)
│   ├── SendGridEmailProvider
│   └── AmazonSESEmailProvider
└── Configuration Management
```

### Key Components
- **`EmailProvider`**: Abstract base class defining the email provider interface
- **`AmazonSESEmailProvider`**: Concrete implementation using boto3 SES client
- **`SendGridEmailProvider`**: Existing SendGrid implementation (unchanged)
- **`EmailService`**: Main service class with provider selection logic

## Configuration

### Environment Variables
```bash
# Provider Selection
EMAIL_PROVIDER=amazon_ses  # Options: sendgrid, amazon_ses

# Amazon SES Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_REGION=us-east-1  # Default: us-east-1

# SendGrid Configuration (for comparison)
SENDGRID_API_KEY=your_sendgrid_api_key
```

### AWS SES Setup Requirements
1. **AWS Account**: Active AWS account with SES access
2. **SES Configuration**: 
   - Verify sender email addresses or domains
   - Request production access (if needed)
   - Configure DKIM and SPF records
3. **IAM Permissions**: Ensure the AWS credentials have `ses:SendEmail` and `ses:SendRawEmail` permissions

### Kubernetes Secrets
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: email-secrets
type: Opaque
data:
  aws-access-key-id: <base64-encoded-value>
  aws-secret-access-key: <base64-encoded-value>
  aws-region: <base64-encoded-value>
```

## Usage Examples

### Basic Usage
```python
from app.services.email_service import EmailService

# Configuration-based initialization (recommended)
email_service = EmailService()

# Explicit Amazon SES configuration
email_service = EmailService(
    provider="amazon_ses",
    aws_access_key_id="AKIA...",
    aws_secret_access_key="...",
    aws_region="us-east-1"
)
```

### Sending Emails
```python
# Single email
response = await email_service.send_email(
    to_email="user@example.com",
    subject="Weekly AI Digest",
    html_content="<h1>Your digest content</h1>"
)

# Bulk emails
subscribers = ["user1@example.com", "user2@example.com"]
response = await email_service.send_bulk_emails(
    subscribers=subscribers,
    subject="Weekly AI Digest",
    html_content="<h1>Your digest content</h1>"
)
```

### Response Format
```python
{
    "success": True,
    "message": "Emails sent successfully",
    "total_sent": 2,
    "failed_emails": [],
    "provider": "amazon_ses",
    "details": {
        "message_id": "0000014a-f896-4c07-b62f-...",
        "request_id": "a1b2c3d4-e5f6-7890-abcd-..."
    }
}
```

## Migration Guide

### From SendGrid to Amazon SES

#### Step 1: AWS Setup
1. Create AWS account and configure SES
2. Verify sender email addresses/domains
3. Create IAM user with SES permissions
4. Note down access key and secret key

#### Step 2: Configuration Update
```bash
# Update environment variables
EMAIL_PROVIDER=amazon_ses
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
```

#### Step 3: Testing
```bash
# Run tests to verify configuration
cd backend
python -m pytest tests/services/test_amazon_ses_email_provider.py -v
```

#### Step 4: Deployment
- Update Kubernetes secrets with AWS credentials
- Deploy updated configuration
- Monitor email delivery and logs

### Rollback Plan
```bash
# Revert to SendGrid
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=your_sendgrid_key
```

## Testing

### Test Coverage
- **Unit Tests**: 12 tests covering core functionality
- **Integration Tests**: 6 tests with mocked AWS SES API
- **Multi-Provider Tests**: 10 tests for provider switching
- **Error Handling**: Comprehensive coverage of AWS SES error scenarios

### Running Tests
```bash
# Amazon SES provider tests
python -m pytest tests/services/test_amazon_ses_email_provider.py -v

# Multi-provider tests
python -m pytest tests/services/test_email_service_multi_provider.py -v

# Integration tests
python -m pytest tests/integration/test_amazon_ses_integration.py -v

# All email-related tests
python -m pytest tests/ -k "email" -v
```

### Test Scenarios Covered
- ✅ Successful email sending (single and bulk)
- ✅ AWS credential validation
- ✅ Error handling (ClientError, NoCredentialsError)
- ✅ Provider switching and configuration
- ✅ Email template generation
- ✅ Partial failure scenarios

## Troubleshooting

### Common Issues

#### 1. AWS Credentials Not Found
```
Error: NoCredentialsError - Unable to locate credentials
```
**Solution**: Ensure AWS credentials are properly configured in environment variables or AWS credentials file.

#### 2. SES Sending Quota Exceeded
```
Error: Sending quota exceeded
```
**Solution**: Request quota increase in AWS SES console or wait for quota reset.

#### 3. Email Address Not Verified
```
Error: Email address not verified
```
**Solution**: Verify sender email address in AWS SES console.

#### 4. Region Configuration Issues
```
Error: Could not connect to the endpoint URL
```
**Solution**: Verify AWS_REGION is correctly set and SES is available in that region.

### Debugging Tips
1. **Enable Debug Logging**: Set log level to DEBUG to see detailed AWS API calls
2. **Check AWS CloudTrail**: Monitor SES API calls and responses
3. **Verify IAM Permissions**: Ensure the IAM user has necessary SES permissions
4. **Test with AWS CLI**: Verify SES configuration using AWS CLI commands

### Monitoring
- **Email Delivery**: Monitor SES sending statistics in AWS console
- **Error Rates**: Track failed email attempts in application logs
- **Cost Monitoring**: Monitor SES usage and costs in AWS billing

## Security Considerations

### AWS Credentials Security
- Store credentials in secure secret management systems
- Use IAM roles instead of access keys when possible
- Rotate credentials regularly
- Limit IAM permissions to minimum required (ses:SendEmail, ses:SendRawEmail)

### Email Security
- Implement DKIM signing for email authentication
- Configure SPF records for domain verification
- Monitor bounce and complaint rates
- Use SES reputation monitoring

---

> **For additional support and questions, refer to the main [Implementation Progress](IMPLEMENTATION_PROGRESS.md) documentation or contact the development team.** 