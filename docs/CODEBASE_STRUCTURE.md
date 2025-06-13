# Codebase Structure (Hybrid Serverless Architecture)

> **Overview**: This document provides a high-level overview of the GenAI Tweets Digest **hybrid serverless architecture** with its current project structure and component organization. The system uses AWS Lambda for fast processing and AWS Fargate for long-running visual tweet processing.

## Table of Contents
- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [Core Components](#core-components)
- [Development and Deployment](#development-and-deployment)
- [Related Documentation](#related-documentation)

## Project Overview

The GenAI Tweets Digest is an AWS-based hybrid serverless application that curates and summarizes recent, impactful Twitter content related to Generative AI. It delivers weekly digest emails with double opt-in email verification, combining the cost-efficiency of AWS Lambda for fast operations with the unlimited processing time of AWS Fargate for visual tweet capture.

Key goals of this architecture:
- **Hybrid Processing**: Lambda for fast track (< 15 minutes), Fargate for slow track (unlimited time)
- **Cost Optimization**: 85-95% cost reduction compared to always-on solutions
- **Automatic Scaling**: Event-driven architecture that scales with demand
- **Production-Ready**: Real-world validation with comprehensive testing

## Architecture

The hybrid serverless architecture combines Lambda and Fargate:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Static Site   │    │ Lambda (Fast)   │    │ Fargate (Slow)  │
│ (S3+CloudFront) │◄──►│ < 15 minutes    │◄──►│ Unlimited time  │
│                 │    │ Text processing │    │ Visual capture  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Email Signup   │    │ Email Verification│    │ Weekly Digest   │
│   Subscription  │    │  & Unsubscribe   │    │   Generation    │
│                 │    │                  │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

**Core AWS Services:**
- **AWS Lambda**: Fast processing (subscription, email verification, digest generation)
- **AWS Fargate**: Long-running visual tweet capture with Selenium/Chrome
- **Amazon S3**: Static website hosting and data storage
- **Amazon CloudFront**: CDN for static website
- **Amazon API Gateway**: REST APIs for Lambda functions
- **Amazon DynamoDB**: Subscriber data with verification status
- **Amazon EventBridge**: Weekly scheduling for digest generation
- **Amazon SES**: Email delivery for verification and digests

## Directory Structure

```
genai_tweet_digest_serverless/
├── README.md                           # Main project documentation
├── .gitignore                          # Git ignore rules
├── dev-requirements.txt                # Development dependencies
├── CHANGELOG.md                        # Project changelog
│
├── src/                               # 🔥 Main application source code
│   ├── shared/                        # 📦 Shared libraries (single source of truth)
│   │   ├── __init__.py               # Package initialization with service exports
│   │   ├── config.py                 # Centralized configuration management
│   │   ├── tweet_services.py         # Twitter API & Gemini AI integration
│   │   ├── dynamodb_service.py       # Database operations and email validation
│   │   ├── ses_service.py            # Amazon SES email service integration
│   │   ├── visual_tweet_capture_service.py # Visual processing service
│   │   ├── email_verification_service.py # Email verification logic
│   │   ├── unsubscribe_service.py    # Unsubscribe functionality
│   │   └── utils/                    # Utility functions
│   │       ├── __init__.py
│   │       ├── logging.py            # Logging utilities
│   │       └── validators.py         # Input validation
│   │
│   ├── lambda_functions/              # ⚡ Lambda functions (fast track < 15 min)
│   │   ├── __init__.py
│   │   ├── weekly_digest/            # Main digest processor
│   │   │   ├── handler.py            # Lambda entry point
│   │   │   └── requirements.txt      # Function-specific dependencies
│   │   ├── subscription/             # Email subscription handler
│   │   │   ├── handler.py
│   │   │   └── requirements.txt
│   │   ├── email_verification/       # Email verification handler
│   │   │   ├── handler.py
│   │   │   └── requirements.txt
│   │   ├── unsubscribe/             # Unsubscribe handler
│   │   │   ├── handler.py
│   │   │   └── requirements.txt
│   │   └── fargate_dispatcher/       # 🔥 Fargate job dispatcher
│   │       ├── handler.py            # Dispatch long-running visual jobs
│   │       └── requirements.txt
│   │
│   ├── fargate/                      # 🐳 Fargate containers (slow track)
│   │   └── visual_processor/         # Visual tweet processing container
│   │       ├── Dockerfile            # Chrome + Selenium + Python container
│   │       ├── app.py               # Main Fargate application entry point
│   │       ├── requirements.txt     # Container dependencies
│   │       └── healthcheck.sh       # Container health check
│   │
│   └── frontend/                     # 🌐 Static Next.js website
│       ├── src/                      # React/Next.js source code
│       │   ├── components/           # React components
│       │   └── utils/                # Frontend utilities
│       ├── public/                   # Static assets
│       ├── package.json              # Node.js dependencies
│       └── out/                      # Built static files for S3
│
├── infrastructure/                   # ☁️ Infrastructure as Code
│   └── cloudformation/               # CloudFormation templates
│       ├── hybrid-architecture-template.yaml # Complete hybrid infrastructure
│       ├── cloudformation-template.yaml      # Lambda-only infrastructure  
│       ├── cloudformation-template-minimal.yaml # Minimal setup
│       └── parameters/               # Environment-specific parameters
│           └── production.json       # Production deployment parameters
│
├── deployment/                       # 🚀 Deployment automation
│   └── scripts/                      # Deployment and utility scripts
│       ├── deploy.sh                # Main deployment script
│       ├── deploy-frontend.sh       # Frontend deployment
│       ├── setup-frontend.sh        # Frontend preparation
│       ├── e2e-test.sh             # End-to-end testing
│       ├── test-serverless.sh      # Serverless testing
│       └── utils/                  # Utility scripts
│
├── config/                          # 📋 Configuration files
│   ├── accounts.json               # Twitter accounts to monitor
│   └── accounts-test.json          # Test account configuration
│
├── tests/                           # 🧪 Comprehensive test suite
│   ├── unit/                       # Unit tests
│   │   ├── test_shared/            # Shared library tests (31 tests)
│   │   └── test_lambda_functions/   # Lambda function tests
│   ├── integration/                # Integration tests
│   └── conftest.py                 # Pytest configuration
│
├── docs/                           # 📚 Organized documentation
│   ├── README.md                   # Documentation navigation guide
│   ├── CODEBASE_STRUCTURE.md       # This file
│   ├── architecture/               # Architecture and design docs
│   ├── development/                # Development guides and testing
│   ├── deployment/                 # Deployment guides and troubleshooting
│   ├── reference/                  # Quick references and best practices
│   └── historical/                 # Historical implementation records
│
├── tools/                          # 🔧 Development tools
│   └── useful_commands/            # Helpful command snippets
│
├── archive/                        # 📦 Legacy and reference code
│   ├── exploration/                # Original exploration and prototypes
│   ├── prototypes/                 # Experimental features
│   ├── ec2-processing/             # Legacy EC2 implementation
│   └── visual_captures/            # Historical visual captures
│
└── planning/                       # 📋 Project planning documents
    ├── product_requirement_document.md # Original PRD
    ├── migration_plan.md           # Migration planning
    └── new_project_structure.md    # Architecture planning
```

## Core Components

### 1. **Shared Libraries (`src/shared/`)**

**Single Source of Truth**: All core business logic consolidated in one location.

- **`config.py`**: Centralized configuration management with environment variables
- **`tweet_services.py`**: Enhanced Twitter API & Gemini AI integration with:
  - Complete text extraction from truncated tweets
  - Thread detection and reconstruction
  - Intelligent categorization and summarization
- **`twitter_account_discovery_service.py`**: **NEW** - Production-ready Twitter account discovery with:
  - Iterative crawling of GenAI-relevant accounts from seed URLs
  - Selenium-based profile scraping with retry mechanisms
  - Gemini AI classification of profile relevance (with keyword fallback)
  - Following page extraction and account handle discovery
  - Comprehensive results export with JSON serialization
- **`visual_tweet_capture_service.py`**: Production-ready visual capture with S3 integration
- **`ses_service.py`**: Professional email templates and delivery
- **`dynamodb_service.py`**: Subscriber management with verification status
- **`email_verification_service.py`**: Double opt-in verification system
- **`unsubscribe_service.py`**: Secure token-based unsubscription

### 2. **Lambda Functions (`src/lambda_functions/`)**

**Fast Track Processing** (< 15 minutes execution time):

#### **Weekly Digest (`weekly_digest/handler.py`)**
- **Trigger**: Amazon EventBridge (weekly schedule)
- **Function**: Complete tweet processing and email distribution
- **Performance**: 127.3 seconds execution, ~$0.02 cost per run

#### **Subscription (`subscription/handler.py`)**
- **Trigger**: API Gateway POST `/subscribe`
- **Function**: Email subscription with validation and verification email

#### **Email Verification (`email_verification/handler.py`)**
- **Trigger**: API Gateway GET `/verify`
- **Function**: Secure token validation and subscriber activation

#### **Unsubscribe (`unsubscribe/handler.py`)**
- **Trigger**: API Gateway GET `/unsubscribe`
- **Function**: Token-based unsubscription with confirmation

#### **Fargate Dispatcher (`fargate_dispatcher/handler.py`)**
- **Trigger**: EventBridge or API Gateway
- **Function**: Launches Fargate visual processing jobs for unlimited runtime

### 3. **Fargate Containers (`src/fargate/`)**

**Slow Track Processing** (unlimited execution time):

#### **Visual Processor (`visual_processor/app.py`)**
- **Runtime**: AWS Fargate with Chrome + Selenium
- **Function**: Long-running visual tweet capture and processing
- **Features**: 
  - Intelligent retry mechanisms
  - S3 integration for screenshot storage
  - Health checks and monitoring

### 4. **Static Frontend (`src/frontend/`)**
- **Technology**: Next.js with static export
- **Hosting**: Amazon S3 with CloudFront CDN
- **Features**: Responsive email signup with real-time validation

### 5. **Infrastructure (`infrastructure/cloudformation/`)**
- **Hybrid Template**: Complete Lambda + Fargate infrastructure
- **Lambda-Only Template**: Traditional serverless setup
- **Parameter Management**: Environment-specific configurations

## Development and Deployment

### **Testing Strategy**
- **Backend**: 31 unit tests for shared libraries with 100% pass rate
- **Frontend**: 24 tests for React components with full coverage
- **E2E Testing**: 23 comprehensive end-to-end tests (96% success rate)

### **Deployment Process**
1. **Backend**: `deployment/scripts/deploy.sh` - CloudFormation + Lambda packaging
2. **Frontend**: `deployment/scripts/deploy-frontend.sh` - Static site to S3
3. **Infrastructure**: CloudFormation templates with parameter management

### **Configuration Management**
- **Environment Variables**: Lambda function configuration
- **S3 Configuration**: Twitter accounts and processing parameters
- **Parameter Store**: Secure API key management

## Related Documentation

### **Quick Start**
- [Development Setup](development/DEVELOPMENT_SETUP.md) - Environment setup guide
- [Testing Guide](development/TESTING_GUIDE.md) - Comprehensive testing documentation

### **Architecture Deep Dive**  
- [Hybrid Architecture Plan](architecture/hybrid_architecture_plan.md) - Detailed architecture design
- [Visual Tweet Capture](architecture/visual_tweet_capture_service.md) - Visual processing documentation

### **Deployment & Operations**
- [Deployment Guide](deployment/DEPLOYMENT_WORKAROUNDS.md) - Production deployment guide
- [AWS CLI Best Practices](reference/AWS_CLI_BEST_PRACTICES.md) - Deployment best practices

### **Historical Reference**
- [Implementation Progress](historical/IMPLEMENTATION_PROGRESS.md) - Development history
- [Migration Summary](historical/migration/MIGRATION_SUMMARY.md) - Serverless migration details

---

> **For complete documentation navigation, see [docs/README.md](README.md)**