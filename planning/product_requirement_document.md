# Product Requirements Document (PRD)

> **Project**: GenAI Tweets Digest (Serverless Architecture)
> **Version**: 2.0 (Serverless)
> **Last Updated**: October 2023 
> **Status**: ✅ Serverless Migration Complete

**Product Overview**: The GenAI Tweets Digest is an **AWS serverless application** that curates and summarizes recent, impactful Twitter content related to Generative AI. The service leverages **AWS Lambda, S3, DynamoDB, API Gateway, Amazon SES, and Amazon EventBridge** to provide weekly digest emails, appealing to a broad audience with a focus on **cost-optimization and minimal operational overhead**.

## Table of Contents
- [Executive Summary](#executive-summary)
- [Product Overview](#product-overview)
- [Functional Requirements](#functional-requirements)
- [Technical Specifications](#technical-specifications)
- [Implementation Roadmap](#implementation-roadmap)
- [Success Criteria](#success-criteria)

## Executive Summary

The core functionality of the GenAI Tweets Digest has been successfully migrated to a cost-optimized serverless architecture on AWS.
- Complete tweet processing pipeline (fetch, categorize, summarize) using AWS Lambda.
- Email subscription system with API Gateway, Lambda, and DynamoDB persistence.
- Email distribution service using Amazon SES.
- Serverless deployment infrastructure using AWS CloudFormation.
- Comprehensive testing and validation adapted for the serverless environment.

### Key Achievements (Serverless Migration)
- **Cost-Optimized Architecture**: Significantly reduced operational costs by leveraging pay-per-use AWS serverless services.
- **Event-Driven Processing**: Robust and scalable backend logic using AWS Lambda triggered by API Gateway and Amazon EventBridge.
- **Simplified Deployment**: Infrastructure managed via AWS CloudFormation and streamlined deployment scripts.
- **Reduced Maintenance**: Minimized infrastructure management overhead.
- **Real API Integration**: All services validated with live Twitter, Gemini, and Amazon SES APIs in the serverless context.
- **Scalable by Design**: Architecture inherently scales with demand based on AWS managed services.

### Key Value Propositions (Retained and Enhanced)
- **Automated Curation**: AI-powered content discovery and categorization.
- **Expert Insights**: Summaries from top influential GenAI accounts.
- **Time-Saving**: Weekly digest format reduces information overload.
- **Accessibility**: Content suitable for beginners to experts.

---

## Product Overview

### Target Audience
- **Primary**: AI researchers, developers, and enthusiasts
- **Secondary**: Business leaders interested in AI trends
- **Tertiary**: Students and newcomers to the AI field

### Core Features
1. **Intelligent Tweet Curation**: Automated fetching from influential accounts and viral content (via Lambda).
2. **AI-Powered Categorization**: 5 predefined categories using Gemini 2.0 Flash (orchestrated by Lambda).
3. **Professional Summarization**: Newsletter-quality content generation (orchestrated by Lambda).
4. **Email Distribution**: Weekly automated digest delivery via Amazon SES (triggered by EventBridge, processed by Lambda).
5. **Responsive Landing Page**: Modern subscription interface (hosted on S3/CloudFront).

### User Journey
```
Landing Page (S3/CloudFront) → Email Signup (API Gateway + Lambda) → Weekly Digest (EventBridge + Lambda + SES) → Engagement
```

---

## Functional Requirements

### Backend Services (AWS Lambda Functions)

#### Tweet Processing Pipeline
**Requirement**: Automated content curation and analysis with enhanced text extraction.

**Components**:
- **Enhanced Tweet Fetching (Lambda)**
  - **Complete Text Extraction**: Retrieves full tweet content with advanced handling for truncated text
  - **Thread Detection and Reconstruction**: Automatically identifies and reconstructs multi-tweet threads from the same user
  - **Full Retweet Text**: Expands retweets to include complete original tweet content using referenced tweet data
  - **Conversation Analysis**: Uses conversation_id to find related tweets and build complete context
  - **Advanced API Integration**: Leverages Twitter API v2 expansions and search capabilities for comprehensive data
  - Sources: Top ~200 influential GenAI accounts + viral content (configurable via S3)
  - Twitter API v2 integration with intelligent rate limiting handled within Lambda
  
- **Tweet Categorization (Lambda + Gemini 2.0 Flash)**
  - **Categories**:
    - New AI model releases
    - Breakthrough research findings
    - Applications and case studies
    - Ethical discussions and regulations
    - Tools and resources
  - Confidence scoring (0-1 scale)
  - Intelligent prompt engineering optimized for complete tweet content

- **Content Summarization (Lambda + Gemini 2.0 Flash)**
  - Category-based grouping and summarization using enhanced tweet data
  - Professional tone suitable for all experience levels
  - 2-4 sentences per category with improved context from complete tweets
  - Newsletter-quality output leveraging full thread content

#### Email System
**Requirement**: Automated weekly digest distribution and subscription management.

**Components**:
- **Subscription Management (API Gateway + Lambda + DynamoDB)**
  - Email validation and duplicate prevention.
  - UUID-based subscription tracking with persistence in DynamoDB.
  - GDPR-compliant data handling principles.
  
- **Email Distribution (Lambda + Amazon SES)**
  - Primarily uses Amazon SES for email delivery.
  - Responsive HTML email templates.
  - Batch processing considerations for large subscriber lists within Lambda.
  - Professional newsletter design.
  - Mobile optimization.

### Frontend Application (Static Site - e.g., React.js/Next.js build output)

#### Landing Page
**Requirement**: Engaging user acquisition interface.

**Components**:
- **Hero Section**: Clear value proposition and benefits.
- **Email Signup Form**: Accessible subscription interface, submitting to API Gateway.
- **Features Showcase**: Grid highlighting capabilities.
- **Responsive Design**: Mobile-first approach.
- **Performance**: Optimized for fast loading via S3/CloudFront.

**Technical Stack (Frontend Build)**:
- (Example) Next.js with App Router, built to static HTML/CSS/JS.
- TypeScript for type safety.
- Tailwind CSS for styling.

---

## Technical Specifications

### Architecture Overview (Serverless)
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Static Site   │    │  Lambda + S3    │    │  External APIs  │
│ (S3+CloudFront) │◄──►│  (Event-driven) │◄──►│ Twitter/Gemini  │
│                 │    │   Pay-per-use   │    │ Amazon SES      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Technology Stack

#### Backend (AWS Serverless)
- **Language**: Python 3.11
- **Compute**: AWS Lambda (using Boto3 SDK for AWS services).
- **API Layer**: Amazon API Gateway (for subscription endpoint).
- **AI Processing**: Gemini 2.0 Flash API integration.
- **Email Service**: Amazon SES.
- **Database**: Amazon DynamoDB (for subscriber data).
- **Configuration**: JSON files on S3, Lambda environment variables.
- **Security**: IAM roles & policies, API Gateway security features (e.g., throttling, request validation), S3 bucket policies.
- **Scheduler**: Amazon EventBridge (for weekly digest).
- **Storage (Data/Artifacts)**: Amazon S3 (for tweets, generated digests, configurations).

#### Frontend
- **Framework (Build)**: e.g., React.js with Next.js (outputting static files).
- **Language**: TypeScript.
- **Styling**: e.g., Tailwind CSS.
- **Hosting**: Amazon S3 (static website hosting) with Amazon CloudFront (CDN).

#### Infrastructure
- **Provisioning**: AWS CloudFormation (template in `infrastructure-aws/`).
- **CI/CD**: GitHub Actions with automated testing and deployment scripts (`scripts/deploy.sh`).
- **Monitoring**: Amazon CloudWatch (Logs, Metrics, Alarms).
- **Security (AWS Native)**: IAM, VPC (if Lambdas need private resources), AWS WAF (optional for API Gateway/CloudFront).

### Non-Functional Requirements

#### Performance
- **Backend Lambda**: < 15 minutes for complete weekly processing (Lambda max timeout). Aim for < 1 hour including all steps.
- **Frontend**: Fast load times via S3/CloudFront, optimized Core Web Vitals.
- **Email**: Efficient processing of subscriber list by SES.

#### Scalability
- **Email Distribution**: Amazon SES scales automatically. DynamoDB and Lambda scale based on demand/concurrency limits.
- **API Processing**: API Gateway and Lambda scale for concurrent subscription requests.
- **Infrastructure**: AWS managed services scale automatically or with configuration.

#### Security
- **Authentication**: IAM roles for Lambda permissions (least privilege). API Gateway can use API keys or IAM authorization if needed for administrative functions (not currently planned for public API).
- **Data Protection**: GDPR-compliant email handling. Encryption at rest for S3 and DynamoDB.
- **Infrastructure**: Secure S3 bucket policies, CloudFront OAI.
- **Rate Limiting**: API Gateway throttling, potential custom logic in Lambda if needed.

#### Reliability
- **Uptime**: High availability via AWS managed services.
- **Error Handling**: Lambda dead-letter queues (DLQs), retries. Comprehensive fallback mechanisms within Lambda logic.
- **Monitoring**: CloudWatch alarms for Lambda errors, DynamoDB throttling, SES bounce rates.
- **Backup**: DynamoDB point-in-time recovery (PITR), S3 versioning.

---

## Implementation Roadmap

### ✅ Milestone 1: MVP Development (Original Kubernetes Project - Completed)
**Status**: ✅ **COMPLETED & VALIDATED (Legacy)**
_(Details of original Kubernetes project - retained for historical context)_

### ✅ Milestone 1.1: Architectural Enhancements (Original Kubernetes Project - Completed)
**Status**: ✅ **COMPLETED & VALIDATED (Legacy)**
_(Details of original Kubernetes project - retained for historical context)_

### ✅ Milestone S1: Serverless Migration & Core Functionality (Completed)
**Duration**: 4-6 weeks (example)
**Status**: ✅ **COMPLETED & VALIDATED**

#### Core Deliverables
- ✅ **Serverless Backend**: Tweet processing (fetch, categorize, summarize) implemented with AWS Lambda.
- ✅ **Subscription API**: API Gateway endpoint invoking Lambda for email subscriptions, data stored in DynamoDB.
- ✅ **Email Distribution**: Weekly digest emails sent via Amazon SES, orchestrated by Lambda and EventBridge.
- ✅ **Static Frontend Deployment**: Landing page hosted on S3 with CloudFront.
- ✅ **Infrastructure as Code**: AWS resources defined and deployed using CloudFormation (`scripts/deploy.sh`).
- ✅ **Configuration Management**: Account lists and settings managed via S3 and Lambda environment variables.
- ✅ **Testing**: E2E testing plan adapted and executed for the serverless stack.

#### Validation Results
- **Cost Reduction**: Significant decrease in monthly operational costs confirmed.
- **End-to-End Pipeline**: Complete serverless workflow validated from subscription to email delivery.
- **Scalability & Reliability**: Basic load testing confirms AWS services scale as expected.
- **Simplified Operations**: Deployment and maintenance processes streamlined.

### Milestone S2: Enhanced NLP & User Experience (Planned)
**Duration**: 4-6 weeks  
**Status**: 📋 **PLANNED**

#### Objectives
- **Task S2.1**: Refine tweet categorization logic for improved accuracy (Lambda optimization).
- **Task S2.2**: Optimize summarization quality via Gemini fine-tuning or advanced prompt engineering (Lambda optimization).
- **Task S2.3**: Implement detailed CloudWatch logging & custom metrics for model performance and pipeline monitoring.
- **Task S2.4**: Conduct user feedback collection on summary effectiveness.
- **Task S2.5**: Improve subscription confirmation (e.g., double opt-in if required) and management workflow (e.g., unsubscribe handling triggered via SES/Lambda).

### Milestone S3: Scaling, Optimization & Analytics (Planned)
**Duration**: 3-4 weeks  
**Status**: 📋 **PLANNED**

#### Objectives
- **Task S3.1**: Further optimize Lambda functions for cost and performance (memory, duration).
- **Task S3.2**: Implement robust unsubscribe handling and preference management.
- **Task S3.3**: Improve CloudFormation templates for modularity and different environments (dev/staging/prod).
- **Task S3.4**: Set up comprehensive CloudWatch Dashboards and Alarms for backend health and key metrics.
- **Task S3.5**: Integrate basic analytics for subscription trends and email engagement (e.g., using SES event publishing to S3/Athena or CloudWatch).

---

## Success Criteria

### Technical Metrics
- **Accuracy**: > 95% confidence in tweet categorization (remains critical).
- **Performance**: Weekly digest generation completes well within Lambda limits (e.g., < 10 minutes average).
- **Reliability**: > 99.9% availability for API Gateway, Lambda, SES, S3, DynamoDB (leveraging AWS SLA).
- **Scalability**: Support for 10,000+ weekly subscribers with graceful scaling.
- **Cost**: Monthly AWS bill significantly lower than original Kubernetes hosting (e.g., < $20/month at current scale).

### Business Metrics
- **User Engagement**: > 25% email open rate.
- **Content Quality**: Positive user feedback on summary relevance.
- **Growth**: Steady subscriber acquisition and retention.
- **Operational**: Automated weekly execution without manual intervention.

### Quality Metrics
- **Test Coverage**: > 80% for Lambda function logic.
- **Security**: Zero critical security vulnerabilities identified in AWS Well-Architected reviews or scans.
- **Documentation**: Updated PRD, README-SERVERLESS, and Codebase Structure documents.
- **Compliance**: GDPR-compliant data handling and user consent mechanisms.

---

## Risk Assessment & Mitigation

### Technical Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| **API Rate Limits (Twitter/Gemini)** | High | Intelligent rate limiting and error handling within Lambda functions; caching strategies (e.g., S3 for fetched tweets). |
| **AI Model Changes (Gemini)** | Medium | Version pinning for Gemini API if possible; robust error handling and monitoring for API changes. |
| **Email Deliverability (SES)** | High | Monitor SES reputation, handle bounces and complaints (SNS notifications), use verified sender, adhere to sending best practices. Consider dedicated IP if volume grows significantly. |
| **Lambda Cold Starts** | Medium | Optimize Lambda package size, memory allocation. Consider provisioned concurrency for critical functions if latency is an issue (trade-off with cost). |
| **Vendor Lock-in (AWS)** | Medium | Design Lambdas with clear separation of concerns; core logic can be ported if necessary, though AWS service integration is deep. |


### Business Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| **Content Quality** | High | Continuous model improvement (prompt engineering) and user feedback.
| **User Acquisition** | Medium | SEO optimization for static site (if applicable), content marketing, community engagement.
| **Competition** | Medium | Focus on unique AI-powered curation and quality of summaries.

---

## Appendices

### A. API Documentation
- **Subscription API**: Defined by Amazon API Gateway. OpenAPI specification can be exported from API Gateway console.
- **External APIs**: Twitter API v2, Google Gemini API.

### B. Deployment Guide
- **Primary Guide**: See `README-SERVERLESS.md`.
- **Infrastructure**: AWS CloudFormation templates in `infrastructure-aws/`.
- **Deployment Script**: `scripts/deploy.sh`.
- **Frontend Upload**: Manual or scripted sync to S3 website bucket.

### C. Security Guidelines
- **AWS Well-Architected Framework**: Adhere to security pillar best practices.
- **IAM**: Least privilege for all Lambda functions and AWS services.
- **Data**: Encryption at rest for S3 and DynamoDB. Secure handling of API keys (e.g., AWS Secrets Manager or Parameter Store for Lambda, not committed to repo).
- **Network**: Secure S3 bucket policies, CloudFront Origin Access Identity (OAI).
- **Logging & Monitoring**: CloudWatch for security event logging and alerting.

---

> **For detailed serverless implementation, quick start, and operational procedures, see [README-SERVERLESS.md](../README-SERVERLESS.md)**
