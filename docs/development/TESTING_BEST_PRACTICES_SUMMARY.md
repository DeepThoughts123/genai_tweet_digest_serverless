# Testing Best Practices Summary

## Overview

This document summarizes critical testing best practices and common pitfalls discovered through extensive end-to-end testing of the GenAI Tweet Digest serverless application. **Read this before deploying to Fargate!**

## 🚨 Critical Pre-Deployment Checklist

### 1. Dependencies MUST Be Complete

**Issue**: Missing transitive dependencies cause cascading failures in Fargate.

**Required in `requirements.txt`**:
```
tweepy==4.15.0          # Twitter API client
selenium==4.21.0        # For screenshot capture
webdriver-manager==4.0.2 # Required by selenium
Pillow==10.3.0          # Image processing (imports as PIL)
boto3>=1.34.0           # AWS SDK
google-generativeai>=0.3.0  # Gemini API
# ... other dependencies
```

**How to Test**:
```bash
docker build -t test .
docker run --rm test python -m fargate.async_runner
# Should NOT see any ModuleNotFoundError
```

### 2. Environment Variables MUST Be Set

**Issue**: Missing environment variables cause runtime failures.

**Required in CDK Stack**:
```python
environment={
    "AWS_DEFAULT_REGION": os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
    "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", ""),
    "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
    # ... other env vars
}
```

**Pre-deployment**:
```bash
export GEMINI_API_KEY=your-key  # or OPENAI_API_KEY
export AWS_DEFAULT_REGION=us-east-1
```

### 3. Data Model Consistency

**Issue**: Field name mismatches between producer and consumer cause failures.

**Common Mismatches**:
- Producer: `metadata_s3_location` → Consumer: `s3_metadata_path`
- Metadata: `tweet_metadata.text` → Expected: `full_text_ocr`

**Solution**: Always log and verify data structures:
```python
print(f"Data structure: {json.dumps(data, indent=2)}")
```

## 📋 Testing Workflow

### Step 1: Local Docker Testing (ALWAYS DO THIS FIRST!)

```bash
# 1. Build the image
docker build -t classifier-test .

# 2. Test basic startup (will fail on env vars, but no import errors)
docker run --rm classifier-test python -m fargate.async_runner

# 3. If you see ModuleNotFoundError:
#    - Add missing package to requirements.txt
#    - Rebuild and test again
#    - Repeat until no import errors

# 4. Test with minimal environment
docker run --rm \
  -e AWS_DEFAULT_REGION=us-east-1 \
  -e QUEUE_URL=test \
  -e DDB_TABLE=test \
  -e S3_BUCKET=test \
  -e GEMINI_API_KEY=$GEMINI_API_KEY \
  classifier-test
```

### Step 2: Deploy Infrastructure

```bash
cd infrastructure
npx aws-cdk deploy ClassifierStack --require-approval never
```

### Step 3: End-to-End Testing

```bash
# 1. Set environment
export PYTHONPATH=$PWD/src:$PYTHONPATH
export AWS_PROFILE=your-profile
export S3_BUCKET=your-bucket

# 2. Run pipeline
python scripts/run_pipeline.py --accounts elonmusk --max 5

# 3. Monitor processing
aws logs tail /aws/ecs/classifier-service --follow

# 4. Check results
aws dynamodb scan --table-name TweetTopicsTable --query 'Items[0]'
```

## 🔧 Common Issues and Quick Fixes

### Issue 1: ModuleNotFoundError in Container
```bash
# Quick fix: Add to requirements.txt and rebuild
echo "missing-package==version" >> requirements.txt
docker build -t test . && docker run --rm test python -m fargate.async_runner
```

### Issue 2: KeyError in Consumer
```python
# Debug data structure
print(f"Message: {json.dumps(message_body, indent=2)}")
print(f"Metadata: {json.dumps(enriched_data, indent=2)}")
```

### Issue 3: Gemini API Errors
```python
# Use generation_config for temperature
from google.generativeai import types as genai_types
generation_config = genai_types.GenerationConfig(temperature=0.0)
response = model.generate_content(prompt, generation_config=generation_config)
```

### Issue 4: AWS Credentials for Local Testing
```bash
# Option 1: Use AWS profile
export AWS_PROFILE=your-profile

# Option 2: Modify code to handle local files
if not s3_path.startswith("s3://"):
    # Handle local file path
```

## 📊 Monitoring Commands

```bash
# Check ECS service status
aws ecs describe-services \
  --cluster classifier-cluster \
  --services classifier-service \
  --query 'services[0].runningCount'

# Monitor SQS queue
aws sqs get-queue-attributes \
  --queue-url $QUEUE_URL \
  --attribute-names ApproximateNumberOfMessages

# View recent logs
aws logs tail /aws/ecs/classifier-service --since 1h

# Check DynamoDB results
aws dynamodb scan \
  --table-name TweetTopicsTable \
  --max-items 5 \
  --query 'Items[*].tweet_id.S'
```

## ✅ Success Criteria

Your deployment is successful when:
1. ECS service shows 1/1 running tasks
2. No errors in CloudWatch logs
3. SQS messages are being consumed
4. DynamoDB contains classified tweets
5. S3 has screenshot images

## 🚀 Quick Reference

### Must-Have Dependencies
- `selenium` + `webdriver-manager` for screenshots
- `Pillow` for image processing
- All API client libraries

### Must-Set Environment Variables
- `AWS_DEFAULT_REGION`
- `GEMINI_API_KEY` or `OPENAI_API_KEY`
- All service endpoints (SQS, DynamoDB, S3)

### Must-Test Locally
- Docker container startup
- No import errors
- Basic functionality

### Must-Monitor Post-Deployment
- ECS task status
- CloudWatch logs
- Queue processing
- Data flow to DynamoDB

## 📚 Additional Resources

- **[Complete Troubleshooting Guide](./TROUBLESHOOTING_GUIDE.md)** - Detailed solutions
- **[Testing Guide](./TESTING_GUIDE.md)** - Comprehensive testing procedures
- **[Fargate Deployment Checklist](../deployment/FARGATE_DEPLOYMENT_CHECKLIST.md)** - Step-by-step deployment

---

**Remember**: Most Fargate deployment issues can be prevented by thorough local Docker testing! 