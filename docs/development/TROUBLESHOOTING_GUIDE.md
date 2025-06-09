# Troubleshooting Guide

This document catalogs common and advanced issues encountered during the development, testing, and deployment of the GenAI Tweet Digest pipeline. Refer to this guide to avoid common pitfalls and resolve complex environment-specific problems.

---

## ⚠️ Critical Deployment Issues - Must Read

**These issues were discovered during the June 2025 deployment and MUST be addressed for successful Fargate deployment:**

### 1. **Missing Python Dependencies in requirements.txt**
**Problem**: The application uses `selenium` for screenshot capture, which has transitive dependencies not automatically installed.

**Required Dependencies**:
```
tweepy==4.15.0          # Twitter API client
selenium==4.21.0        # Web scraping for screenshots
webdriver-manager==4.0.2 # Manages Chrome/Firefox drivers for selenium
Pillow==10.3.0          # Image processing (imported as PIL)
```

**How to Detect**: Run `docker run --rm <image> python -m fargate.async_runner` locally. You'll see cascading `ModuleNotFoundError` messages.

### 2. **Missing AWS_DEFAULT_REGION Environment Variable**
**Problem**: The Fargate container fails with `botocore.exceptions.NoRegionError` because boto3 doesn't know which AWS region to use.

**Solution**: Add to CDK stack (`infrastructure/classifier_stack.py`):
```python
environment={
    "AWS_DEFAULT_REGION": os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
    # ... other env vars
}
```

### 3. **Missing API Keys in Environment**
**Problem**: The LLM client requires either `OPENAI_API_KEY` or `GEMINI_API_KEY` to be set.

**Solution**: Set before deployment:
```bash
export GEMINI_API_KEY=your-api-key  # or OPENAI_API_KEY
npx aws-cdk deploy ClassifierStack
```

### 4. **Docker Platform Architecture Mismatch**
**Problem**: M1/M2 Macs build ARM images by default, but Fargate requires AMD64.

**Solution**: Already fixed in Dockerfile with `FROM --platform=linux/amd64 python:3.11-slim`

---

## 1. Local Development Issues

### 1.1 `ModuleNotFoundError: No module named 'shared'` (Local Shell)

*   **Symptom:** Running a script from the command line (e.g., `run_pipeline.py`) results in a `ModuleNotFoundError` for a top-level module like `shared`.
*   **Cause:** The Python interpreter cannot find the `src` directory where the application's modules reside. The `PYTHONPATH` is not correctly set for the current shell session.
*   **Solution:** Before running any script, prepend the project's `src` directory to the `PYTHONPATH`.

    ```bash
    export PYTHONPATH=$PWD/src:$PYTHONPATH
    python3 scripts/run_pipeline.py --accounts ...
    ```

### 1.2 Twitter API: `400 Bad Request` on `max_results`

*   **Symptom:** The `TweetFetcher` service fails with a `400 Bad Request` error. The error message from the Twitter API states: `The \`max_results\` query parameter value [N] is not between 5 and 100`.
*   **Cause:** A call was made to the Twitter Timeline API with a `max_results` (or `--max` in the `run_pipeline.py` script) parameter less than 5. The API enforces a minimum of 5.
*   **Solution:** Ensure that any method calling the `get_users_tweets` endpoint of the `tweepy` client provides a `max_results` value that is at least 5. This is enforced in the `detect_and_group_threads` method in `src/shared/tweet_services.py`.

    ```python
    # src/shared/tweet_services.py
    # ...
            # Timeline API requires a minimum of 5 results
            api_max_results = max(5, max_tweets)

            # Fetch recent tweets with conversation_id
            tweets = self.client_v2.get_users_tweets(
                id=user_id,
                max_results=api_max_results,
    # ...
    ```

---

## 2. Docker & AWS Fargate Deployment Issues

### 2.1 `ModuleNotFoundError` in Docker Container

*   **Symptom:** The Docker container fails to start, or the Fargate task exits immediately, with a `ModuleNotFoundError` in the logs.
*   **Primary Cause:** The `PYTHONPATH` is not set correctly inside the container's environment, or the application files are not in the expected location.
*   **Solution:**
    1.  Ensure the `Dockerfile` copies the application source code into the correct directory. Copy the *contents* of `src` into the working directory.
    2.  Set the `PYTHONPATH` to the working directory.
    3.  Update the `ENTRYPOINT` to reflect the new module path.

    ```dockerfile
    # Dockerfile

    # ...
    WORKDIR /app

    COPY requirements.txt .
    RUN pip install -r requirements.txt

    # Copy the contents of the src directory directly into /app
    COPY src/ .

    # Set the PYTHONPATH to the workdir
    ENV PYTHONPATH=/app

    # The entrypoint no longer needs the "src." prefix
    ENTRYPOINT ["python", "-m", "fargate.async_runner"]
    ```

### 2.2 `exec format error` in Fargate Task

*   **Symptom:** The Fargate task fails to start. The logs in CloudWatch show the error: `exec /usr/local/bin/python: exec format error`.
*   **Cause:** The Docker image was built on a machine with a different CPU architecture (e.g., Apple Silicon, `arm64`) than the Fargate runtime environment (which is typically `x86_64`). The container's binaries are not compatible.
*   **Solution:** Explicitly specify the target platform when building the Docker image. This can be done by adding the `--platform=linux/amd64` flag to the `FROM` instruction in the `Dockerfile`.

    ```dockerfile
    # Dockerfile
    FROM --platform=linux/amd64 python:3.11-slim
    # ...
    ```
    Then rebuild the image.

### 2.3 Fargate Service Not Using the Latest Docker Image

*   **Symptom:** After pushing a new Docker image with a fix, the Fargate service continues to run the old, broken code. The error persists even after forcing a new deployment.
*   **Cause:** The service is likely using the `:latest` tag, which can be subject to caching or race conditions in a distributed environment. Fargate may not immediately pull the newest image if the tag name hasn't changed.
*   **Solution:** Use unique, immutable tags for each Docker build. The git commit hash is a perfect candidate.
    1.  Tag the image with the git commit hash.
        ```bash
        GIT_HASH=$(git rev-parse --short HEAD)
        docker tag my-image:latest my-repo.ecr.aws.com/my-image:$GIT_HASH
        docker push my-repo.ecr.aws.com/my-image:$GIT_HASH
        ```
    2.  Update the CDK stack (`infrastructure/classifier_stack.py`) to use the specific tag.
        ```python
        # infrastructure/classifier_stack.py
        image = ecs.ContainerImage.from_ecr_repository(ecr_repo, "515e2cf") # Use the specific git hash
        ```
    3.  Redeploy the CDK stack. This guarantees that the new service revision will pull the exact image version intended.

### 2.4 Data Mismatch: `KeyError: 's3_metadata_path'` in Consumer

*   **Symptom:** The `ClassifierService` (the consumer) fails with a `KeyError` when processing a message from the SQS queue.
*   **Cause:** The message producer (`run_pipeline.py`) and the consumer (`ClassifierService`) disagree on the message format. The producer was sending `{"tweet_id": ...}` while the consumer was expecting `{"s3_metadata_path": ...}`.
*   **Solution:** Ensure that the producer script is updated to generate messages in the format expected by the consumer. In this case, the `run_pipeline.py` script was modified to always use the `VisualTweetCaptureService`, which correctly generates the metadata file, uploads it to S3, and enqueues the path.

### 2.5 `ModuleNotFoundError` Cascade in Fargate (`tweepy`, `webdriver_manager`, `PIL`)

*   **Symptom:** The Fargate task exits immediately. CloudWatch logs show a `ModuleNotFoundError` for a seemingly installed package (e.g., `tweepy`). Running the container locally reveals a cascade of similar errors for other packages like `webdriver_manager` or `PIL`.
*   **Cause:** This issue arises from incomplete dependency specification in `requirements.txt`. While a primary package might be listed, its transitive dependencies required for specific features (like `selenium`'s need for `webdriver-manager` or image processing needing `Pillow`) are missing. The Fargate error for `tweepy` was misleading; it was the first sign of a brittle environment.
*   **Solution:** The most effective way to debug this is to replicate the Fargate entrypoint command in a local Docker run.
    1.  Build the image locally: `docker build -t my-image .`
    2.  Run the container with the same command as the Fargate task definition, but without environment-specific variables initially:
        ```bash
        # This command attempts to start the application, which will quickly fail on the first missing module.
        docker run --rm my-image python -m fargate.async_runner
        ```
    3.  Observe the `ModuleNotFoundError`, add the missing package to `requirements.txt`, and repeat the build/run cycle. In this case, `selenium`, `webdriver-manager`, and `Pillow` were added.
    4.  This local, iterative process is much faster than debugging via repeated cloud deployments. Once the local command runs without module errors (it may fail on configuration/env-var errors, which is expected), the image is ready for deployment.

---

## 3. Data Model and Field Name Mismatches

### 3.1 Field Name Inconsistencies Between Producer and Consumer

*   **Symptom:** The `ClassifierService` fails with `KeyError` when trying to access fields from the SQS message or downloaded metadata.
*   **Cause:** Field naming inconsistencies between components:
    - Producer sends `metadata_s3_location` but consumer expects `s3_metadata_path`
    - Metadata has `tweet_metadata.text` but classifier expects `full_text_ocr`
*   **Solution:** Ensure consistent field naming across all components:

    ```python
    # In run_pipeline.py (producer)
    queue_message = {
        "s3_metadata_path": s3_metadata_path  # Use consistent naming
    }
    
    # In classifier_service.py (consumer)
    s3_metadata_path = message_body["s3_metadata_path"]  # Match the producer
    
    # When extracting tweet text
    tweet_text = enriched_data.get("tweet_metadata", {}).get("text", "")  # Match actual structure
    ```

### 3.2 Missing or Incorrect Data Extraction

*   **Symptom:** Classifier fails with `None` or empty values for tweet data.
*   **Cause:** Incorrect assumptions about data structure in metadata files.
*   **Solution:** Always check the actual structure of the data:

    ```python
    # Debug by printing the structure
    print(f"Metadata structure: {json.dumps(enriched_data, indent=2)}")
    
    # Safely extract nested fields
    tweet_metadata = enriched_data.get("tweet_metadata", {})
    author_info = tweet_metadata.get("author", {})
    tweet_text = tweet_metadata.get("text", "")
    ```

---

## 4. LLM API Compatibility Issues

### 4.1 Gemini API Parameter Errors

*   **Symptom:** `TypeError: GenerativeModel.generate_content() got an unexpected keyword argument 'temperature'`
*   **Cause:** The Gemini API doesn't accept `temperature` as a direct parameter to `generate_content()`.
*   **Solution:** Use `generation_config` to pass temperature:

    ```python
    # In llm_client.py
    from google.generativeai import types as genai_types
    
    generation_config = genai_types.GenerationConfig(
        temperature=temperature
    )
    response = self._backend.generate_content(
        prompt, 
        generation_config=generation_config
    )
    ```

### 4.2 Outdated Model Names

*   **Symptom:** API errors about invalid or unavailable model names.
*   **Cause:** Model names change over time (e.g., "gemini-pro" → "gemini-2.9-flash").
*   **Solution:** Update to current model names:

    ```python
    # In llm_client.py
    _DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"  # Updated from "gemini-pro"
    ```

---

## 5. Local Testing with AWS Services

### 5.1 AWS Credentials for S3 Access in Local Testing

*   **Symptom:** Local testing fails with `NoCredentialsError` when trying to download from S3.
*   **Cause:** The test script doesn't have AWS credentials configured.
*   **Solution:** Ensure AWS credentials are available:

    ```bash
    # Option 1: Use AWS CLI profile
    export AWS_PROFILE=your-profile
    
    # Option 2: Use environment variables
    export AWS_ACCESS_KEY_ID=your-key
    export AWS_SECRET_ACCESS_KEY=your-secret
    export AWS_DEFAULT_REGION=us-east-1
    
    # Option 3: For testing, create local files instead
    # Modify test to use local files in run_artifacts/ directory
    ```

### 5.2 S3 Path Handling in Local vs Production

*   **Symptom:** Code works in production but fails locally with file path errors.
*   **Cause:** Production uses S3 paths (`s3://bucket/key`) while local testing might use file paths.
*   **Solution:** Handle both cases in your code:

    ```python
    def _download_metadata_from_s3(self, s3_path: str) -> dict:
        if not s3_path.startswith("s3://"):
            # Handle local file path for testing
            local_path = Path("run_artifacts") / s3_path
            with open(local_path, "r") as f:
                return json.load(f)
        
        # Handle S3 path for production
        bucket, key = s3_path.replace("s3://", "").split("/", 1)
        # ... S3 download logic
    ```

---

## 3. AWS Environment & CLI

### 3.1 AWS CLI Commands Fail or Produce No Output

*   **Symptom:** AWS CLI commands, especially those with complex `--query` parameters, fail with errors like `zsh: command not found: AWS::ECS::Cluster` or produce no output at all (e.g., `list-clusters`).
*   **Cause:** This is typically caused by custom configurations in the user's local shell environment (e.g., `~/.zshrc`, Oh My Zsh plugins) that interfere with the AWS CLI's output piping or argument parsing.
*   **Solution:** Execute the AWS CLI command inside a "clean" Zsh subshell that bypasses most custom startup scripts. This is done using the `zsh -d -f -c "..."` wrapper. Piping the output to `cat` can also help ensure the full, unbuffered output is displayed.
    
    ```bash
    # Example for a command with a complex query
    zsh -d -f -c "aws ecs describe-task-definition --task-definition <task-def-arn> --region us-east-1 | cat"
    
    # Example for a simpler list command
    zsh -d -f -c "aws ecs list-clusters --region us-east-1 | cat"
    ``` 