# GenAI Tweets Digest - MLE Onboarding Guide

Welcome to the GenAI Tweets Digest serverless project! This guide will help you understand the product, get your development environment set up, and make your first contributions.

## 1. Introduction & Product Overview

**What is GenAI Tweets Digest?**
The GenAI Tweets Digest is a serverless application that:
1.  Monitors specified Twitter accounts for recent tweets.
2.  Uses Generative AI (Google's Gemini Pro) to categorize and summarize these tweets.
3.  Allows users to subscribe via email to receive a weekly digest of these categorized summaries.

**Core Goal:** To provide users with a concise, AI-curated summary of relevant Twitter activity from influential accounts, delivered conveniently to their inbox, all while running on a cost-optimized serverless architecture on AWS.

## 2. High-Level Architecture (Simplified)

The system is built entirely on AWS serverless services, meaning you don't have to manage any servers directly.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Static Site   │    │  Lambda + S3    │    │  External APIs  │
│ (S3+CloudFront) │◄──►│  (Event-driven) │◄──►│ Twitter/Gemini  │
│  (Frontend)     │    │   Pay-per-use   │    │ Amazon SES      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

**Key Components:**
*   **Static Website (S3 + CloudFront)**: A simple frontend where users can learn about the service and subscribe (currently placeholder, focus is on backend).
*   **AWS Lambda**: These are small, event-driven pieces of Python code that run in the cloud. We have Lambdas for:
    *   Handling new email subscriptions.
    *   Verifying email addresses.
    *   Processing tweets and generating the digest weekly.
    *   Handling unsubscriptions.
*   **Amazon S3 (Simple Storage Service)**: Used for:
    *   Storing raw tweet data and generated digests.
    *   Storing configuration files (like the list of Twitter accounts to follow).
    *   Hosting the static website files.
*   **Amazon DynamoDB**: A NoSQL database used to store subscriber information (email, status, etc.).
*   **Amazon API Gateway**: Creates HTTP endpoints (web links) that trigger our Lambda functions (e.g., when a user submits their email to subscribe).
*   **Amazon EventBridge (formerly CloudWatch Events)**: Acts as a scheduler to trigger the weekly digest generation Lambda automatically.
*   **Amazon SES (Simple Email Service)**: Used to send verification emails and the weekly digest emails.
*   **AWS CloudFormation**: This is an "Infrastructure as Code" service. We define all the AWS resources listed above in a template file, and CloudFormation builds or updates them automatically.
*   **IAM (Identity and Access Management) Roles**: These define permissions for our Lambda functions, allowing them to securely access other AWS services (like reading from DynamoDB or sending emails via SES).

## 3. Getting Started: Your First Setup

Follow these steps to get your local development environment ready.

### Prerequisites
1.  **AWS Account**: You'll need access to an AWS account. If you're part of a team, your AWS administrator will provide you with credentials or an IAM user.
2.  **AWS CLI (Command Line Interface)**:
    *   Install it by following the [official AWS CLI installation guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
    *   Configure it: Open your terminal and run `aws configure --profile personal`.
        *   Enter your AWS Access Key ID.
        *   Enter your AWS Secret Access Key.
        *   Set Default region name: `us-east-1` (or as specified by your team).
        *   Set Default output format: `json`.
        *(The `--profile personal` creates a named profile. Our scripts will use this profile.)*
3.  **Python**: Version 3.11 is used for this project. Ensure it's installed and accessible from your terminal.
4.  **pip**: Python's package installer (usually comes with Python).
5.  **Git**: For version control.

### Cloning the Repository
1.  Open your terminal.
2.  Navigate to the directory where you want to store the project.
3.  Clone the repository: `git clone <repository_url>` (replace `<repository_url>` with the actual URL).
4.  Navigate into the cloned project directory: `cd genai_tweet_digest_serverless` (or your project's directory name).

### API Keys & Secrets (`.env` file)
The application requires API keys for Twitter and Google Gemini, and an email address for sending digests. These are managed using a `.env` file at the root of the project.

1.  **Create the `.env` file**: In the project's root directory, create a file named `.env`.
2.  **Populate `.env`**: Add the following content, replacing placeholder values with your actual keys/emails. **Ask your team lead for these keys if you don't have them.**

    ```bash
    # .env (Example - REPLACE WITH YOUR ACTUAL VALUES)
    AWS_PROFILE=personal
    AWS_REGION=us-east-1
    
    # For your main development/testing stack, give it a unique name
    # Example: STACK_NAME=genai-tweets-digest-dev-yourname
    STACK_NAME=genai-tweets-digest-dev-yourinitials 
    
    ENVIRONMENT=development # Or 'staging', 'production' as appropriate for the STACK_NAME

    # External API Keys
    TWITTER_BEARER_TOKEN="YOUR_TWITTER_BEARER_TOKEN_HERE"
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"

    # Email Configuration (must be verified in AWS SES)
    FROM_EMAIL="your-verified-sender-email@example.com"
    TO_EMAIL="your-verified-recipient-email-for-testing@example.com" # Useful for SES sandbox mode testing
    ```
    *   **`STACK_NAME`**: This is very important. For your personal development, make this unique (e.g., `genai-tweets-digest-dev-yourname`). The deployment scripts will use this to create an isolated instance of the application for you.
    *   **`FROM_EMAIL` / `TO_EMAIL`**: These email addresses **must be verified in Amazon SES** in the `us-east-1` region for emails to work, especially if your AWS account's SES is in sandbox mode.

3.  **Security**: The `.env` file contains sensitive secrets. It is already listed in `.gitignore` and **must never be committed to version control.**

### Python Virtual Environment
It's crucial to use a virtual environment to manage project dependencies.
1.  Navigate to the project root in your terminal.
2.  Create the virtual environment:
    ```bash
    python3.11 -m venv .venv311 
    # Or if python3.11 is just `python` for you: python -m venv .venv311
    ```
3.  Activate the virtual environment:
    *   macOS/Linux: `source .venv311/bin/activate`
    *   Windows: `.venv311\Scripts\activate`
    You should see `(.venv311)` at the beginning of your terminal prompt.
4.  Install Python dependencies:
    The deployment scripts handle optimized packaging. For local development and to satisfy your IDE, you can install based on the general `lambdas/requirements.txt`:
    ```bash
    pip install --index-url https://pypi.org/simple -r lambdas/requirements.txt
    ```
    *(Note: `deploy-optimized.sh` uses function-specific requirements files for smaller deployment packages).*

## 4. Understanding the Codebase (Key Areas)

*   `genai_tweet_digest_serverless/` (Root Directory)
    *   `lambdas/`: Contains the Python source code for all AWS Lambda functions.
        *   `subscription/`: Handles new user email subscriptions.
        *   `email-verification/`: Manages the email verification process.
        *   `weekly-digest/`: Fetches tweets, uses AI for categorization/summarization, and triggers email sending. This is where most of the core MLE work might happen.
        *   `unsubscribe/`: Handles user unsubscriptions.
        *   `shared/`: Common Python utility modules used by multiple Lambda functions (e.g., for interacting with DynamoDB, SES, external APIs).
    *   `infrastructure-aws/cloudformation-template.yaml`: The "blueprint" for all AWS resources. CloudFormation reads this YAML file to create or update the entire application infrastructure (S3 buckets, DynamoDB tables, Lambdas, API Gateway, etc.).
    *   `scripts/`: Contains shell scripts for automating tasks.
        *   `deploy-optimized.sh`: **This is the primary script you will use for deployments.** It builds optimized Lambda packages and then calls `deploy.sh`.
        *   `deploy.sh`: The main deployment logic that interacts with AWS CloudFormation and updates Lambda functions.
    *   `data/accounts.json`: A JSON file where you list the Twitter accounts the system should monitor.
    *   `.env`: (You created this) Stores your secrets and deployment configuration.
    *   `README-SERVERLESS.md`: The main project README with detailed information.

## 5. Running Your Development Stack

A "stack" in CloudFormation is an isolated collection of AWS resources that run your application. For development, you'll deploy your own personal stack.

1.  **Set Your `STACK_NAME`**: Ensure the `STACK_NAME` in your `.env` file is unique for your development (e.g., `genai-tweets-digest-dev-yourinitials`). The `ENVIRONMENT` variable in `.env` can be set to `development`.
2.  **First Deployment**:
    *   Make sure your virtual environment is activated (`source .venv311/bin/activate`).
    *   From the project root directory, run:
        ```bash
        ./scripts/deploy-optimized.sh
        ```
3.  **What to Expect**:
    *   The script will first build optimized .zip packages for each Lambda function.
    *   Then, it will use CloudFormation to create all the AWS resources defined in `infrastructure-aws/cloudformation-template.yaml`. This can take 5-15 minutes for the first deployment.
    *   You'll see output in your terminal showing the progress.
    *   Finally, it will update the Lambda functions with the packaged code.
4.  **Key Outputs**: At the end of a successful deployment, the script will print "Stack Outputs". Note these down, especially:
    *   `ApiGatewayURL`: The base URL for your API.
    *   `SubscriptionEndpoint`: The specific URL for subscribing.
    *   `DataBucketName` and `WebsiteBucketName`: Names of your personal S3 buckets.
    *   `SubscribersTableName`: Name of your personal DynamoDB table.

## 6. Making & Deploying Your First Code Change

Let's make a small, safe change to see the update process.

1.  **Modify Lambda Code**:
    Open `lambdas/subscription/lambda_function.py`.
    Inside the `lambda_handler` function, find a `print()` statement or add a new one, for example:
    ```python
    # ... inside lambda_handler ...
    print("Subscription attempt for email:", email)
    print("Hello from <Your Name>'s updated Lambda!") # Add this line
    # ...
    ```
2.  **Re-deploy to Your Development Stack**:
    *   Make sure your virtual environment is active.
    *   Ensure your `.env` file has your development `STACK_NAME` (e.g., `STACK_NAME=genai-tweets-digest-dev-yourinitials`).
    *   From the project root, run:
        ```bash
        ./scripts/deploy-optimized.sh
        ```
3.  **How Updates Work**:
    *   The script rebuilds the Lambda packages (only the ones with changes if you had more complex build logic, but here it rebuilds all).
    *   CloudFormation checks if any infrastructure defined in `cloudformation-template.yaml` needs to change. For just a Python code change, it usually says "No updates are to be performed" for the infrastructure.
    *   The script then updates the code of your existing Lambda functions with the new .zip packages. This is usually very fast.

## 7. Testing Core Features (on your dev stack)

Use the outputs (like API Gateway URL) from **your development stack's deployment**.

1.  **Test Subscription**:
    *   Get your `SubscriptionEndpoint` from the deployment output.
    *   In your terminal (ensure `TO_EMAIL` in `.env` is an email you can check and is verified in SES):
        ```bash
        API_ENDPOINT="YOUR_STACK_SUBSCRIPTION_ENDPOINT_HERE"
        curl -X POST $API_ENDPOINT -H "Content-Type: application/json" -d '{"email": "your-to-email-from-dotenv@example.com"}' -w '\nStatus: %{http_code}\n'
        ```
    *   Expect a `Status: 201` and a success message. Check your email for the verification link.
    *   Click the link to verify.

2.  **Upload `accounts.json`**:
    *   Modify `data/accounts.json` if you wish.
    *   Get your `DataBucketName` from the deployment output.
    *   Upload it:
        ```bash
        DATA_BUCKET_NAME="YOUR_STACK_DATA_BUCKET_NAME"
        aws s3 cp data/accounts.json s3://$DATA_BUCKET_NAME/config/accounts.json --profile personal
        ```

3.  **Trigger Weekly Digest Lambda**:
    *   The Lambda function name will be `YOUR_STACK_NAME-weekly-digest` (e.g., `genai-tweets-digest-dev-yourinitials-weekly-digest`).
    *   Invoke it:
        ```bash
        LAMBDA_NAME="YOUR_STACK_NAME-weekly-digest"
        aws lambda invoke --function-name $LAMBDA_NAME --payload '{}' --cli-binary-format raw-in-base64-out out.json --profile personal --region us-east-1
        cat out.json # Check the output
        ```
    *   This should trigger the digest generation. Check your verified `TO_EMAIL` for the digest after a few minutes.

4.  **Checking Logs (Debugging)**:
    If things don't work as expected, CloudWatch Logs are your best friend.
    *   Lambda function log group names are `/aws/lambda/YOUR_STACK_NAME-<function-suffix>` (e.g., `/aws/lambda/genai-tweets-digest-dev-yourinitials-subscription`).
    *   Use the AWS Console (CloudWatch -> Log groups) or the AWS CLI:
        ```bash
        LOG_GROUP_NAME="/aws/lambda/YOUR_STACK_NAME-subscription"
        aws logs tail $LOG_GROUP_NAME --since 5m --profile personal --region us-east-1
        ```

## 8. Key AWS Services (A Beginner's Glossary)

*   **AWS Lambda**: Think of these as small, independent pieces of your Python code that run in the cloud when something triggers them (like an API call or a schedule). You don't manage servers.
*   **Amazon S3 (Simple Storage Service)**: A place to store files. We use it for website files, storing tweet data, and configuration.
*   **Amazon DynamoDB**: A fast and flexible NoSQL database. We use it to keep track of email subscribers.
*   **Amazon API Gateway**: This service creates a public web link (an API endpoint) that people (or other services) can use to run your Lambda functions. E.g., the `/subscribe` link.
*   **Amazon EventBridge (CloudWatch Events)**: This is a scheduler. We use it to automatically run the "weekly digest" Lambda function once a week (or every 30 mins for testing in the template).
*   **Amazon SES (Simple Email Service)**: For sending emails – both the verification emails when someone subscribes and the actual weekly digest emails.
*   **AWS CloudFormation**: This is "Infrastructure as Code." Instead of manually clicking around in the AWS console to create all these services, we define them in a text file (`cloudformation-template.yaml`). CloudFormation then reads this file and builds (or updates) everything for us. This ensures consistency.
*   **IAM (Identity and Access Management) Roles**: These are like permission slips for your Lambda functions. For a Lambda to read data from DynamoDB or send an email via SES, it needs an IAM Role that grants it permission to do so.

## 9. Common First-Timer Issues & Troubleshooting

*   **`.env` file issues**:
    *   **Symptom**: Script complains about missing `TWITTER_BEARER_TOKEN`, `GEMINI_API_KEY`, or `FROM_EMAIL`.
    *   **Fix**: Ensure your `.env` file exists in the project root and contains valid values for these keys.
*   **AWS CLI Configuration**:
    *   **Symptom**: Errors like "Unable to locate credentials," "profile personal not found," or access denied errors.
    *   **Fix**: Run `aws configure --profile personal` and provide valid AWS Access Key ID and Secret Access Key that has permissions to create the necessary resources. Ensure your default region is `us-east-1` or matches `AWS_REGION` in `.env`.
*   **SES Email Not Verified**:
    *   **Symptom**: Subscription works, but no verification email arrives, or Lambda logs show "MessageRejected: Email address is not verified."
    *   **Fix**: Both `FROM_EMAIL` and any `TO_EMAIL` you use for testing must be verified identities in Amazon SES in the `us-east-1` region, especially while SES is in sandbox mode. You can do this via the AWS SES Console.
*   **CloudFormation Stack Failure**:
    *   **Symptom**: The `./scripts/deploy-optimized.sh` script fails during the "Deploying infrastructure..." step, often with a "ROLLBACK_COMPLETE" message.
    *   **Fix**:
        1.  Go to the AWS CloudFormation console in `us-east-1`.
        2.  Find your stack (e.g., `genai-tweets-digest-dev-yourinitials`).
        3.  Look at the "Events" tab. Scroll down to find the first errors (usually in red) that caused the rollback. This will tell you which resource failed to create and why.
        4.  Common causes we've seen: naming conflicts (now largely solved by using `${AWS::StackName}` in the template), or IAM permission issues for your AWS user.
        5.  For complex deletion issues (e.g., stack stuck in `DELETE_FAILED`), refer to `docs/STACK_MANAGEMENT_GUIDE.md`.
*   **Lambda Function Errors (e.g., 500/502 from API)**:
    *   **Symptom**: API calls (like to `/subscribe`) fail with a 500 or 502 error.
    *   **Fix**:
        1.  Identify the Lambda function name (e.g., `YOUR_STACK_NAME-subscription`).
        2.  Check its CloudWatch Logs: `aws logs tail /aws/lambda/YOUR_STACK_NAME-subscription --since 10m --profile personal --region us-east-1`.
        3.  The logs will contain the Python traceback or error message from within the Lambda. Common issues:
            *   Missing environment variables (check Lambda configuration in AWS console vs. `cloudformation-template.yaml`).
            *   Bugs in the Python code.
            *   Permissions issues for the Lambda's IAM role (though `AWSLambdaBasicExecutionRole` and our custom policies cover most needs).
            *   `ImportModuleError` (see `docs/DEPLOYMENT_WORKAROUNDS.md`).

## 10. Where to Go Next (Further Reading)

This guide gives you the essentials. For more depth, refer to these documents in the `docs/` folder:

*   **`README-SERVERLESS.md`**: The main project README with more technical details.
*   **`docs/DEVELOPMENT_SETUP.md`**: More granular setup details.
*   **`docs/LAMBDA_OPTIMIZATION_STRATEGY.md`**: Explains how Lambda packaging is optimized.
*   **`docs/DEPLOYMENT_WORKAROUNDS.md`**: Details on specific tricky issues we've solved.
*   **`docs/STACK_MANAGEMENT_GUIDE.md`**: For deleting and managing CloudFormation stacks.
*   **`docs/AWS_CLI_BEST_PRACTICES.md`**: Tips for using the AWS CLI effectively.

Good luck, and welcome to the project! 