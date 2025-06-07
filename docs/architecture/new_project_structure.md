# New Project Structure Design

## Overview
This document outlines the new folder structure for the hybrid Lambda + Fargate architecture, designed for maintainability, clarity, and future extensibility.

## Design Principles

1. **Separation of Concerns**: Clear boundaries between Lambda (fast track) and Fargate (slow track)
2. **Single Source of Truth**: Unified shared libraries, no duplication
3. **Deployment-Focused**: Structure supports clean CI/CD workflows
4. **Developer-Friendly**: Intuitive navigation and clear responsibility boundaries
5. **Future-Proof**: Easy to extend with new processing modes or services

## Proposed Structure

```
genai_tweet_digest_serverless/
├── README.md                           # Main project documentation
├── .gitignore                          # Git ignore rules
├── .env.template                       # Environment variables template
├── requirements.txt                    # Root-level Python dependencies
│
├── src/                               # 🔥 NEW: All application source code
│   ├── shared/                        # 📦 Shared libraries (consolidated)
│   │   ├── __init__.py
│   │   ├── config.py                  # Configuration management
│   │   ├── tweet_services.py          # Twitter API & AI services
│   │   ├── dynamodb_service.py        # Database operations
│   │   ├── ses_service.py             # Email services
│   │   ├── visual_tweet_capture_service.py  # Visual processing
│   │   ├── processing_orchestrator.py  # Hybrid processing logic
│   │   └── utils/                     # Utility functions
│   │       ├── __init__.py
│   │       ├── logging.py
│   │       └── validators.py
│   │
│   ├── lambda/                        # ⚡ Lambda functions (fast track)
│   │   ├── __init__.py
│   │   ├── weekly_digest/             # Main digest processor
│   │   │   ├── handler.py
│   │   │   ├── requirements.txt
│   │   │   └── tests/
│   │   ├── subscription/              # Email subscription
│   │   │   ├── handler.py
│   │   │   ├── requirements.txt
│   │   │   └── tests/
│   │   ├── email_verification/        # Email verification
│   │   │   ├── handler.py
│   │   │   ├── requirements.txt
│   │   │   └── tests/
│   │   ├── unsubscribe/              # Unsubscribe handling
│   │   │   ├── handler.py
│   │   │   ├── requirements.txt
│   │   │   └── tests/
│   │   └── fargate_dispatcher/        # 🔥 NEW: Fargate job dispatcher
│   │       ├── handler.py
│   │       ├── requirements.txt
│   │       └── tests/
│   │
│   ├── fargate/                       # 🐳 Fargate containers (slow track)
│   │   ├── visual_processor/          # Visual tweet processing
│   │   │   ├── Dockerfile
│   │   │   ├── app.py                 # Main application entry
│   │   │   ├── requirements.txt
│   │   │   ├── config/
│   │   │   └── tests/
│   │   └── batch_processor/           # 🔥 Future: Other batch jobs
│   │       ├── Dockerfile
│   │       ├── app.py
│   │       └── requirements.txt
│   │
│   └── frontend/                      # 🌐 Static website
│       ├── src/                       # React/Next.js source
│       ├── public/                    # Static assets
│       ├── package.json
│       └── out/                       # Built static files
│
├── infrastructure/                    # ☁️ Infrastructure as Code
│   ├── cloudformation/                # CloudFormation templates
│   │   ├── hybrid-architecture.yaml  # Main template
│   │   ├── lambda-only.yaml          # Fallback template
│   │   └── parameters/                # Parameter files
│   │       ├── development.json
│   │       ├── staging.json
│   │       └── production.json
│   ├── docker/                        # Docker configurations
│   │   ├── base.Dockerfile           # Base image for all containers
│   │   └── scripts/
│   └── terraform/                     # 🔥 Future: Terraform alternative
│
├── deployment/                        # 🚀 Deployment automation
│   ├── scripts/                       # Deployment scripts
│   │   ├── deploy-full.sh            # Complete deployment
│   │   ├── deploy-lambda.sh          # Lambda-only deployment
│   │   ├── deploy-fargate.sh         # Fargate-only deployment
│   │   ├── build-containers.sh       # Container build script
│   │   └── utils/                    # Utility scripts
│   ├── ci-cd/                        # CI/CD configurations
│   │   ├── github-actions/           # GitHub Actions workflows
│   │   ├── buildspec.yml             # AWS CodeBuild
│   │   └── docker-compose.yml        # Local development
│   └── testing/                      # Testing scripts
│       ├── integration-tests.sh
│       ├── smoke-tests.sh
│       └── load-tests/
│
├── config/                           # 📋 Configuration files
│   ├── accounts.json                 # Twitter accounts to monitor
│   ├── categories.json               # Tweet categories
│   ├── email-templates/              # Email template files
│   └── environments/                 # Environment-specific configs
│       ├── development.env
│       ├── staging.env
│       └── production.env
│
├── docs/                            # 📚 Documentation
│   ├── architecture/                # Architecture documentation
│   │   ├── hybrid-design.md
│   │   ├── lambda-functions.md
│   │   └── fargate-containers.md
│   ├── deployment/                  # Deployment guides
│   │   ├── quick-start.md
│   │   ├── production-deployment.md
│   │   └── troubleshooting.md
│   ├── development/                 # Developer guides
│   │   ├── setup.md
│   │   ├── testing.md
│   │   └── contributing.md
│   └── api/                        # API documentation
│       ├── lambda-apis.md
│       └── internal-apis.md
│
├── tests/                           # 🧪 Test suite
│   ├── unit/                       # Unit tests
│   │   ├── test_shared/
│   │   ├── test_lambda/
│   │   └── test_fargate/
│   ├── integration/                # Integration tests
│   │   ├── test_end_to_end/
│   │   └── test_hybrid_flow/
│   ├── fixtures/                   # Test data and fixtures
│   └── conftest.py                 # Pytest configuration
│
├── tools/                          # 🔧 Development tools
│   ├── local-dev/                  # Local development utilities
│   │   ├── docker-compose.yml      # Local service stack
│   │   └── mock-services/          # Mock external services
│   ├── monitoring/                 # Monitoring setup
│   │   ├── cloudwatch-dashboards/
│   │   └── alerts/
│   └── data-analysis/              # Data analysis tools
│       ├── tweet-analyzer.py
│       └── performance-analyzer.py
│
└── archive/                        # 📦 Legacy/reference code
    ├── exploration/                # Original exploration code
    ├── prototypes/                 # Experimental features
    └── migration-logs/             # Migration documentation
```

## Key Improvements

### 1. **Unified Source Structure (`src/`)**
- All application code lives under `src/`
- Clear separation between shared libraries, Lambda functions, Fargate containers, and frontend
- Single source of truth for shared code (no more duplication)

### 2. **Processing Mode Separation**
- `src/lambda/` - Fast track (< 15 minutes)
- `src/fargate/` - Slow track (unlimited time)
- `src/shared/` - Common libraries used by both

### 3. **Deployment-Centric Organization**
- `deployment/` contains all deployment automation
- `infrastructure/` contains all infrastructure definitions
- Clear separation between application code and deployment code

### 4. **Configuration Management**
- `config/` directory for all configuration files
- Environment-specific configurations clearly separated
- Template files for easy setup

### 5. **Testing Strategy**
- Comprehensive test structure with unit, integration, and fixtures
- Tests organized by component type
- Easy to run focused test suites

### 6. **Documentation Structure**
- Architecture, deployment, and development docs clearly separated
- API documentation in dedicated location
- Easy navigation for different user types

### 7. **Development Tools**
- Local development support with Docker Compose
- Monitoring and analysis tools organized
- Mock services for offline development

## Migration Benefits

1. **Maintainability**: Clear boundaries and responsibilities
2. **Scalability**: Easy to add new Lambda functions or Fargate containers
3. **Testing**: Comprehensive test organization
4. **Deployment**: Streamlined CI/CD with dedicated deployment directory
5. **Onboarding**: New developers can easily understand the structure
6. **Future-Proofing**: Structure supports additional processing modes

## File Movement Summary

### Major Consolidations:
- `lambdas/shared/` + scattered shared code → `src/shared/`
- `lambdas/*/lambda_function.py` → `src/lambda/*/handler.py`
- `exploration/integrated_tweet_pipeline.py` → `src/fargate/visual_processor/app.py`
- `scripts/` → `deployment/scripts/`
- Current documentation → `docs/` with clear categorization

### New Additions:
- `src/fargate/` for containerized processing
- `deployment/` for all deployment automation
- `config/` for centralized configuration
- `tools/` for development utilities

This structure provides a solid foundation for the hybrid architecture while maintaining clarity and supporting future growth. 