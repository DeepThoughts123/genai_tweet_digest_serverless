# Serverless Migration Plan: GenAI Tweets Digest

## Overview
Migrate from Kubernetes-based 24/7 infrastructure to cost-optimized serverless AWS architecture that only runs when needed.

## Current vs Target Architecture

### Current (High Cost)
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Next.js       │    │    FastAPI      │    │  External APIs  │
│   (Vercel)      │◄──►│  (Kubernetes)   │◄──►│ Twitter/Gemini  │
│                 │    │   24/7 Running  │    │ Amazon SES      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```
**Monthly Cost**: $50-200+ (Kubernetes cluster, load balancers, monitoring)

### Target (Low Cost)
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Static Site   │    │  Lambda + S3    │    │  External APIs  │
│ (S3+CloudFront) │◄──►│  (Event-driven) │◄──►│ Twitter/Gemini  │
│                 │    │   Pay-per-use   │    │ Amazon SES      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```
**Monthly Cost**: $5-15 (only pay for actual usage)

## Migration Components

### 1. Static Website (S3 + CloudFront)
- **Current**: Next.js on Vercel/Netlify
- **Target**: Static build deployed to S3 with CloudFront CDN
- **Cost**: ~$1-3/month
- **Changes**: Minimal frontend modifications

### 2. Subscription Management (API Gateway + Lambda)
- **Current**: FastAPI endpoint running 24/7
- **Target**: Single Lambda function triggered by API Gateway
- **Cost**: ~$0.20/month (assuming 1000 subscriptions/month)
- **Changes**: Extract subscription logic to standalone Lambda

### 3. Weekly Digest Processing (EventBridge + Lambda)
- **Current**: Kubernetes CronJob with SchedulerService
- **Target**: EventBridge rule triggering Lambda weekly
- **Cost**: ~$2-5/month (runs once per week)
- **Changes**: Refactor SchedulerService to Lambda handler

### 4. Data Storage
- **Current**: SQLite/PostgreSQL in containers
- **Target**: 
  - Subscriber data: DynamoDB (serverless) or RDS Serverless
  - Tweet data: S3 (JSON files for easy portability)
  - Curated accounts: S3 (JSON configuration file)
- **Cost**: ~$1-5/month
- **Benefits**: Easy data export/import, no database maintenance

### 5. Email Service
- **Current**: Multi-provider (SendGrid + Amazon SES)
- **Target**: Amazon SES only (simpler, cheaper)
- **Cost**: $0.10 per 1000 emails
- **Changes**: Remove SendGrid complexity

## Implementation Steps

### Phase 1: Core Lambda Functions
1. Create subscription Lambda function
2. Create weekly digest Lambda function
3. Migrate core business logic (tweet fetching, categorization, summarization)
4. Set up DynamoDB for subscribers
5. Set up S3 for tweet data and configuration

### Phase 2: Static Website
1. Modify Next.js to generate static build
2. Update API calls to use API Gateway endpoints
3. Deploy to S3 with CloudFront

### Phase 3: Automation & Monitoring
1. Set up EventBridge for weekly scheduling
2. Add CloudWatch monitoring and alerts
3. Create deployment scripts

### Phase 4: Data Migration & Cleanup
1. Export existing data
2. Import to new storage systems
3. Remove old infrastructure

## File Structure Changes

### New Serverless Structure
```
genai_tweets_digest/
├── 📁 lambdas/                  # AWS Lambda functions
│   ├── subscription/            # Subscription management
│   ├── weekly-digest/           # Weekly processing
│   └── shared/                  # Shared utilities
├── 📁 frontend-static/          # Static Next.js build
├── 📁 infrastructure-aws/       # CloudFormation/CDK
├── 📁 data/                     # Configuration files
│   ├── accounts.json           # Curated Twitter accounts
│   └── email-templates/        # Email templates
└── 📁 scripts/                 # Deployment scripts
```

### Reusable Components
- `tweet_fetcher.py` ✅ (minimal changes)
- `tweet_categorizer.py` ✅ (minimal changes)  
- `tweet_summarizer.py` ✅ (minimal changes)
- `email_service.py` ✅ (simplify to SES only)
- Email templates ✅ (reuse as-is)
- Frontend components ✅ (minimal changes)

### Components to Remove
- FastAPI server and all endpoints
- Kubernetes configurations
- Docker containers
- Monitoring stack (Prometheus/Grafana)
- Rate limiting middleware
- API authentication
- Database models (replace with DynamoDB)

## Cost Comparison

### Current Monthly Costs
- Kubernetes cluster: $30-100
- Load balancer: $15-25
- Monitoring: $10-20
- Storage: $5-10
- **Total**: $60-155/month

### Target Monthly Costs
- S3 + CloudFront: $1-3
- Lambda executions: $1-3
- DynamoDB: $1-2
- API Gateway: $0.50
- EventBridge: $0.10
- SES emails: $0.10-1
- **Total**: $4-10/month

**Savings**: 85-95% cost reduction

## Next Steps
1. Create Lambda function templates
2. Set up AWS infrastructure with CloudFormation/CDK
3. Migrate core business logic
4. Test end-to-end workflow
5. Deploy and validate

Would you like me to start implementing any specific component? 