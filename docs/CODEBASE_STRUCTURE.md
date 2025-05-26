# Codebase Structure (Serverless)

> **Overview**: This document provides a high-level overview of the GenAI Tweets Digest **serverless architecture**, its project structure, and component organization. This version is cost-optimized using AWS Lambda, S3, DynamoDB, and API Gateway.

## Table of Contents
- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [Core Components](#core-components)
- [Development and Deployment](#development-and-deployment)
- [Related Documentation](#related-documentation)

## Project Overview

The GenAI Tweets Digest (Serverless) is an AWS-based application that curates and summarizes recent, impactful Twitter content related to Generative AI. It delivers weekly digest emails. This serverless version prioritizes cost-efficiency and minimal infrastructure management by leveraging event-driven AWS Lambda functions and managed services.

Key goals of this architecture:
- Significant cost reduction compared to containerized/always-on solutions.
- Automatic scaling based on demand.
- Reduced operational overhead.

## Architecture

The serverless architecture is depicted below:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Static Site   │    │  Lambda + S3    │    │  External APIs  │
│ (S3+CloudFront) │◄──►│  (Event-driven) │◄──►│ Twitter/Gemini  │
│                 │    │   Pay-per-use   │    │ Amazon SES      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

**Core AWS Services Used:**
-   **AWS Lambda**: For backend processing (subscription handling, weekly digest generation).
-   **Amazon S3**: For hosting the static frontend website and storing data like tweets and configuration.
-   **Amazon CloudFront**: As a CDN for the static website.
-   **Amazon API Gateway**: To expose the subscription Lambda function as an HTTP API.
-   **Amazon DynamoDB**: For storing subscriber information.
-   **Amazon EventBridge (CloudWatch Events)**: To schedule the weekly execution of the digest Lambda.
-   **Amazon SES (Simple Email Service)**: For distributing the weekly digest emails.

## Directory Structure

```
genai_tweets_digest_serverless/
├── .DS_Store                 # macOS specific file (should be in .gitignore)
├── AWS_CLI_BEST_PRACTICES.md # Best practices for AWS CLI usage
├── CHANGELOG.md              # Project changelog
├── README-SERVERLESS.md      # Main README for the serverless project
├── cf-params.json            # Parameters for CloudFormation deployment
├── data/                     # Configuration files
│   └── accounts.json         # List of Twitter accounts to monitor
├── docs/                     # Project documentation
│   ├── CODEBASE_STRUCTURE.md # This file
│   ├── DEPLOYMENT_WORKAROUNDS.md # Notes on deployment issues
│   ├── E2E_TESTING_PLAN.md   # End-to-end testing strategy
│   ├── IMPLEMENTATION_PROGRESS.md # (Potentially from original project)
│   ├── MIGRATION_SUMMARY.md  # Summary of migration to serverless
│   ├── SECURITY_RECOMMENDATIONS.md # Security notes
│   ├── TESTING_GUIDE.md      # General testing guide
│   └── serverless-migration-plan.md # Initial plan for serverless migration
│   └── AMAZON_SES_INTEGRATION.md # Notes on SES
├── frontend-static/          # Static website build (e.g., from Next.js output)
│   └── out/                  # Example output directory for static files
├── infrastructure-aws/       # CloudFormation templates and related infrastructure-as-code
│   └── template.yaml         # Main CloudFormation template (example name)
├── lambdas/                  # Source code and dependencies for AWS Lambda functions
│   ├── build/                # Temporary build artifacts (should be in .gitignore)
│   ├── shared/               # Shared Python utilities for Lambda functions
│   │   └── utils.py          # (Example: common helper functions)
│   ├── subscription/         # Source code for the email subscription Lambda
│   │   └── app.py            # (Example: Lambda handler)
│   ├── weekly-digest/        # Source code for the weekly digest generation Lambda
│   │   └── app.py            # (Example: Lambda handler)
│   ├── tests/                # Unit/integration tests for Lambda functions
│   ├── requirements.txt      # Python dependencies for all Lambda functions
│   ├── subscription-function.zip # Deployment package (example, may be in build/)
│   ├── pip_weekly_debug.log  # Debug log (should be in .gitignore)
│   └── pip_weekly_debug2.log # Debug log (should be in .gitignore)
├── planning/                 # Original project planning documents
│   └── product_requirement_document.md # PRD for the original (Kubernetes) project
├── requirements.txt          # Root Python requirements (purpose to be clarified, may be legacy)
├── scripts/                  # Deployment, testing, and utility scripts
│   ├── deploy.sh             # Main script for deploying the serverless stack
│   ├── setup-frontend.sh     # Script to prepare/build the static frontend
│   └── e2e-test.sh           # End-to-end test script (as per E2E_TESTING_PLAN.md)
├── setup.py                  # Root Python setup file (purpose to be clarified, may be legacy)
└── useful_commands/          # Collection of helpful command snippets
```

**Note on `.gitignore`**: It's recommended to include temporary files, build artifacts (`lambdas/build`, `*.zip` if rebuilt), and logs (`lambdas/*.log`, `.DS_Store`) in the `.gitignore` file.

## Core Components

### 1. AWS Lambda Functions (`lambdas/`)
-   **Subscription Lambda (`lambdas/subscription/`)**:
    -   Triggered by API Gateway.
    -   Handles new email subscriptions.
    -   Validates email and stores it in DynamoDB.
    -   (Potentially sends a confirmation email via SES - needs verification from E2E plan).
-   **Weekly Digest Lambda (`lambdas/weekly-digest/`)**:
    -   Triggered by an Amazon EventBridge schedule (e.g., weekly).
    -   Fetches tweets using the Twitter API.
    -   Categorizes and summarizes tweets using the Gemini AI API.
    -   Stores generated digest content (e.g., in S3).
    -   Retrieves subscriber list from DynamoDB.
    -   Sends digest emails via Amazon SES.
-   **Shared Utilities (`lambdas/shared/`)**:
    -   Common code used by multiple Lambda functions (e.g., configuration loading, API clients).
-   **Dependencies (`lambdas/requirements.txt`)**:
    -   Python package dependencies (boto3, tweepy, google-generativeai) for the Lambda functions. Packaged with each function for deployment.

### 2. Static Frontend (`frontend-static/`)
-   Consists of HTML, CSS, and JavaScript files (likely a build output from a framework like Next.js/React).
-   Hosted on Amazon S3 and distributed via Amazon CloudFront.
-   Provides the landing page and email signup form.

### 3. Data Storage and Configuration
-   **DynamoDB**: Stores subscriber email addresses and related information.
-   **S3 Data Bucket**:
    -   Stores raw tweet data fetched by the weekly digest Lambda.
    -   Stores generated digest content.
    -   Stores configuration files like `accounts.json` (list of Twitter accounts to follow), which is read by the weekly digest Lambda.
-   **`data/accounts.json`**: Local copy of the Twitter accounts list, uploaded to S3 as part of the deployment or update process.

### 4. Infrastructure as Code (`infrastructure-aws/`)
-   Contains CloudFormation templates (`template.yaml` or similar) to define and provision all AWS resources (Lambda functions, API Gateway, DynamoDB tables, S3 buckets, IAM roles, EventBridge rules, etc.).
-   Parameters for CloudFormation are managed in `cf-params.json`.

### 5. Scripts (`scripts/`)
-   **`deploy.sh`**: Automates the packaging of Lambda functions and deployment of the CloudFormation stack.
-   **`setup-frontend.sh`**: Prepares the static frontend assets for deployment to S3.
-   **`e2e-test.sh`**: (As defined in `docs/E2E_TESTING_PLAN.md`) Script to run end-to-end tests against the deployed application.

## Development and Deployment

### Prerequisites
-   AWS Account & AWS CLI configured.
-   API Keys for Twitter, Google Gemini, and a verified SES email.
-   Environment variables set as per `README-SERVERLESS.md`.

### Deployment
1.  **Set Environment Variables**: Export necessary API keys and configuration.
2.  **Deploy Infrastructure**: Run `./scripts/deploy.sh`. This script typically packages Lambda functions (including dependencies from `lambdas/requirements.txt`) and deploys/updates the CloudFormation stack defined in `infrastructure-aws/`.
3.  **Setup Frontend**: Run `./scripts/setup-frontend.sh` to build static frontend assets.
4.  **Upload Website**: Sync the built frontend from `frontend-static/out/` (or similar) to the S3 website bucket.

### Testing
-   **Unit/Integration Tests**: Located in `lambdas/tests/`. Can be run locally before deployment.
-   **Manual Testing**: As outlined in `README-SERVERLESS.md` and `docs/E2E_TESTING_PLAN.md`, using AWS CLI to invoke Lambdas, check DynamoDB, S3, etc.
-   **End-to-End Testing**: Using the script `scripts/e2e-test.sh` against a deployed environment.

## Related Documentation

-   **[README-SERVERLESS.md](../README-SERVERLESS.md)**: The primary guide for the serverless project, including quick start, deployment, testing, and troubleshooting.
-   **[E2E Testing Plan](./E2E_TESTING_PLAN.md)**: Detailed end-to-end testing strategy.
-   **[Original Project PRD](../planning/product_requirement_document.md)**: Provides context on the original project goals (note: features may differ in the serverless version).
-   **[CloudFormation Parameters](../cf-params.json)**: Parameters used for AWS infrastructure deployment.
-   **[Deployment Scripts](../scripts/)**: Scripts used for automation.