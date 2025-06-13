# Documentation Navigation Guide

Welcome to the GenAI Tweets Digest documentation! This guide helps you quickly find the information you need.

## 🚀 Quick Start

**New to the project?** Start here:
1. [Codebase Structure](CODEBASE_STRUCTURE.md) - Understanding the project structure
2. [Development Setup](development/DEVELOPMENT_SETUP.md) - Environment setup
3. [Testing Guide](development/TESTING_GUIDE.md) - Running tests (130/130 backend tests passing)
4. [Deployment Guide](deployment/DEPLOYMENT_WORKAROUNDS.md) - Deploying the application

## 📂 Documentation Categories

### 🏗️ **Architecture**
Learn about the system design and components:

| Document | Description |
|----------|-------------|
| [Hybrid Architecture Plan](architecture/hybrid_architecture_plan.md) | Complete Lambda + Fargate architecture design |
| [Implementation Summary](architecture/implementation_summary.md) | Current implementation status |
| [Visual Tweet Capture Service](architecture/visual_tweet_capture_service.md) | Visual processing documentation |
| [Tweet Processing Pipeline](architecture/tweet_processing_pipeline.md) | AI-powered tweet processing |
| [Enhanced Tweet Services](architecture/ENHANCED_TWEET_SERVICES.md) | Twitter API integration details |
| [Email Verification Setup](architecture/EMAIL_VERIFICATION_SETUP.md) | Email verification system |
| [Onboarding Guide](architecture/ONBOARDING_GUIDE.md) | New team member guide |
| **[Twitter Account Discovery](../src/shared/twitter_account_discovery_service.py)** | **NEW** - GenAI account discovery service |
| **[Twitter Account Discovery Service](architecture/TWITTER_ACCOUNT_DISCOVERY_SERVICE.md)** | **NEW** - Complete documentation for GenAI account discovery |

### 🛠️ **Development**
Development guides and testing documentation:

| Document | Description |
|----------|-------------|
| [Development Setup](development/DEVELOPMENT_SETUP.md) | Environment setup and configuration |
| [Testing Guide](development/TESTING_GUIDE.md) | Comprehensive testing documentation |
| [Testing Best Practices Summary](development/TESTING_BEST_PRACTICES_SUMMARY.md) | Critical testing insights and common pitfalls |
| [Troubleshooting Guide](development/TROUBLESHOOTING_GUIDE.md) | Solutions to common issues |
| [Onboarding Quick Start](development/ONBOARDING_QUICK_START.md) | Quick start guide for newcomers |
| [Frontend Testing Guide](development/FRONTEND_TESTING_GUIDE.md) | Frontend-specific testing |
| [E2E Testing Plan](development/E2E_TESTING_PLAN.md) | End-to-end testing strategy |
| [E2E Testing Quick Reference](development/E2E_TESTING_QUICK_REFERENCE.md) | Testing commands and examples |
| [Debugging Guide](development/DEBUGGING_FAILED_TO_FETCH.md) | Common debugging scenarios |

### 🚀 **Deployment**
Deployment guides and operational documentation:

| Document | Description |
|----------|-------------|
| [Deployment Workarounds](deployment/DEPLOYMENT_WORKAROUNDS.md) | Production deployment guide |
| [Deployment Testing Guide](deployment/DEPLOYMENT_TESTING_GUIDE.md) | Testing deployment procedures |
| [Fargate Deployment Checklist](deployment/FARGATE_DEPLOYMENT_CHECKLIST.md) | Pre-deployment verification steps |
| [Lambda Optimization Strategy](deployment/LAMBDA_OPTIMIZATION_STRATEGY.md) | Performance optimization |
| [Stack Management Guide](deployment/STACK_MANAGEMENT_GUIDE.md) | CloudFormation management |
| [Schedule Management Guide](deployment/SCHEDULE_MANAGEMENT_GUIDE.md) | EventBridge scheduling |

### 📚 **Reference**
Quick references and best practices:

| Document | Description |
|----------|-------------|
| [AWS CLI Best Practices](reference/AWS_CLI_BEST_PRACTICES.md) | AWS deployment best practices |
| [Security Recommendations](reference/SECURITY_RECOMMENDATIONS.md) | Security guidelines |
| [Amazon SES Integration](reference/AMAZON_SES_INTEGRATION.md) | Email service integration |
| [AWS CLI Deployment Guide (PDF)](reference/AWS%20CLI%20Deployment%20Guide%20\(Next.js%20Frontend%20+%20Python%20Serverless%20Backend\).pdf) | Comprehensive deployment reference |

### 📦 **Historical**
Implementation history and migration documentation:

| Document | Description |
|----------|-------------|
| [Implementation Progress](historical/IMPLEMENTATION_PROGRESS.md) | Complete development history (790 lines) |
| [Task Completion](historical/task_completion.md) | Development milestone tracking |

#### **Testing Results**
| Document | Description |
|----------|-------------|
| [Comprehensive Testing Results](historical/testing_results/COMPREHENSIVE_TESTING_RESULTS.md) | Overall test results |
| [Email Verification Testing](historical/testing_results/EMAIL_VERIFICATION_TESTING_RESULTS.md) | Email system testing |
| [Production Deployment Success](historical/testing_results/PRODUCTION_DEPLOYMENT_SUCCESS.md) | Production validation |

#### **Migration Documentation** 
| Document | Description |
|----------|-------------|
| [Migration Summary](historical/migration/MIGRATION_SUMMARY.md) | Serverless migration overview |
| [Serverless Migration Plan](historical/migration/serverless-migration-plan.md) | Original migration planning |

## 🎯 Common Use Cases

### **I want to...**

**🔧 Set up development environment**
→ [Development Setup](development/DEVELOPMENT_SETUP.md)

**🧪 Run tests**
→ [Testing Guide](development/TESTING_GUIDE.md)

**🚀 Deploy to production**
→ [Deployment Workarounds](deployment/DEPLOYMENT_WORKAROUNDS.md)

**🏗️ Understand the architecture** 
→ [Codebase Structure](CODEBASE_STRUCTURE.md) + [Hybrid Architecture Plan](architecture/hybrid_architecture_plan.md)

**🐛 Debug issues**
→ [Debugging Guide](development/DEBUGGING_FAILED_TO_FETCH.md) + [AWS CLI Best Practices](reference/AWS_CLI_BEST_PRACTICES.md)

**📧 Configure email system**
→ [Email Verification Setup](architecture/EMAIL_VERIFICATION_SETUP.md) + [Amazon SES Integration](reference/AMAZON_SES_INTEGRATION.md)

**🔍 Understand tweet processing**
→ [Tweet Processing Pipeline](architecture/tweet_processing_pipeline.md) + [Visual Tweet Capture Service](architecture/visual_tweet_capture_service.md)

**📊 Review implementation history**
→ [Implementation Progress](historical/IMPLEMENTATION_PROGRESS.md)

## 📋 Document Types

- **📖 Architecture**: System design and component documentation
- **🛠️ Development**: Setup, testing, and debugging guides  
- **🚀 Deployment**: Production deployment and operations
- **📚 Reference**: Quick references and best practices
- **📦 Historical**: Implementation history and migration records

## 🔄 Documentation Maintenance

This documentation is organized to be:
- **Easy to Navigate**: Clear categories and quick start guides
- **Current**: Reflects the latest src/ based architecture
- **Comprehensive**: Covers development, deployment, and operations
- **Maintainable**: Historical content separated from current guides

**Last Updated**: December 2024 - After codebase reorganization to hybrid Lambda + Fargate architecture

---

> **Need help?** Check the relevant category above or search for specific topics using your IDE's search functionality. 