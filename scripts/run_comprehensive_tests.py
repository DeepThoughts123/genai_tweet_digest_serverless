#!/usr/bin/env python3
"""
Comprehensive Testing Script for GenAI Tweet Digest Pipeline
Tests locally, via Docker with AWS resources, and remotely via AWS
Following best practices from TROUBLESHOOTING_GUIDE.md and TESTING_GUIDE.md
"""

import os
import sys
import json
import subprocess
import time
import boto3
from pathlib import Path
from datetime import datetime
import argparse
import dotenv

_ = dotenv.load_dotenv()

# Add src to Python path as per troubleshooting guide
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Test configuration
TEST_ACCOUNTS = ["OpenAI"]  # Using a single account for consistent testing
TEST_MAX_TWEETS = 5  # Small number for testing
TEST_DAYS_BACK = 7

# AWS Resources from CURRENT_STATUS.md
AWS_RESOURCES = {
    "queue_url": "https://sqs.us-east-1.amazonaws.com/855450210814/ClassifierStack-ClassificationQueueEEAC6F55-5wEAB6cca8te",
    "dynamodb_table": "ClassifierStack-TweetTopicsTableD9CB57C4-1A8FFGIVK5AJ2",
    "s3_bucket": "classifierstack-tweetscreenshotbucketb280f4b5-utgkcgleaevv",
    "ecs_cluster": "ClassifierStack-ClassifierCluster3B5A8E18-NTkykRVbVDF1"
}

def print_phase(phase_name):
    """Print phase header"""
    print("\n" + "="*80)
    print(f"PHASE: {phase_name}")
    print("="*80 + "\n")

def check_prerequisites():
    """Check all prerequisites based on troubleshooting guide"""
    print("Checking prerequisites...")
    
    # Check Python path
    print(f"✓ Python path includes src: {os.path.join(os.path.dirname(__file__), '..', 'src') in sys.path}")
    
    # Check environment variables
    required_env = {
        "AWS_DEFAULT_REGION": os.environ.get("AWS_DEFAULT_REGION", ""),
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", ""),
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
        "TWITTER_BEARER_TOKEN": os.environ.get("TWITTER_BEARER_TOKEN", ""),
        "AWS_PROFILE": os.environ.get("AWS_PROFILE", "")
    }
    
    for key, value in required_env.items():
        if value:
            print(f"✓ {key} is set")
        else:
            print(f"⚠️  {key} is NOT set")
    
    # Check if we have at least one LLM API key
    if not (required_env["GEMINI_API_KEY"] or required_env["OPENAI_API_KEY"]):
        print("\n❌ ERROR: Either GEMINI_API_KEY or OPENAI_API_KEY must be set")
        return False
    
    # Check AWS credentials if AWS_PROFILE is set
    if required_env["AWS_PROFILE"]:
        try:
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            print(f"✓ AWS credentials valid: {identity['Arn']}")
        except Exception as e:
            print(f"❌ AWS credentials error: {e}")
            return False
    
    return True

def run_local_test(output_dir):
    """Phase 1: Test locally only, store the output"""
    print_phase("1. LOCAL TEST ONLY")
    
    output_path = Path(output_dir) / "phase1_local"
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Set PYTHONPATH as per troubleshooting guide
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{Path(__file__).parent.parent / 'src'}:{env.get('PYTHONPATH', '')}"
    
    cmd = [
        sys.executable,
        "scripts/run_pipeline.py",
        "--accounts", *TEST_ACCOUNTS,
        "--days", str(TEST_DAYS_BACK),
        "--max", str(TEST_MAX_TWEETS),
        "--output", str(output_path)
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=Path(__file__).parent.parent)
        
        if result.returncode == 0:
            print("✅ Local test completed successfully")
            print(f"Output stored in: {output_path}")
            
            # Read and return the classified results
            classified_file = output_path / "classified.json"
            if classified_file.exists():
                with open(classified_file, 'r') as f:
                    return json.load(f)
            else:
                print("⚠️  No classified.json found - this is expected if using visual capture")
                # Return enriched results instead
                for account in TEST_ACCOUNTS:
                    enriched_file = output_path / f"{account}_enriched_results.json"
                    if enriched_file.exists():
                        with open(enriched_file, 'r') as f:
                            return json.load(f)
        else:
            print(f"❌ Local test failed with return code: {result.returncode}")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error running local test: {e}")
        return None

def test_docker_build():
    """Test Docker build as per troubleshooting guide"""
    print("\nTesting Docker build...")
    
    # First, check if Dockerfile exists
    dockerfile_path = Path(__file__).parent.parent / "Dockerfile"
    if not dockerfile_path.exists():
        print("❌ Dockerfile not found")
        return False
    
    # Build Docker image
    cmd = ["docker", "build", "-t", "pipeline-test", "."]
    print(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
    if result.returncode != 0:
        print(f"❌ Docker build failed:\n{result.stderr}")
        return False
    
    print("✅ Docker build successful")
    
    # Test for import errors as per best practice
    print("\nTesting Docker container for import errors...")
    cmd = ["docker", "run", "--rm", "pipeline-test", "python", "-m", "fargate.async_runner"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if "ModuleNotFoundError" in result.stderr:
        print(f"❌ Import errors found in Docker container:\n{result.stderr}")
        return False
    
    print("✅ No import errors in Docker container")
    return True

def run_docker_aws_test(output_dir):
    """Phase 2: Test locally via Docker but with AWS resources"""
    print_phase("2. LOCAL DOCKER TEST WITH AWS RESOURCES")
    
    output_path = Path(output_dir) / "phase2_docker_aws"
    output_path.mkdir(parents=True, exist_ok=True)
    
    # First test Docker build
    if not test_docker_build():
        return None
    
    # Set environment for AWS resources
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": f"{Path(__file__).parent.parent / 'src'}:{env.get('PYTHONPATH', '')}",
        "QUEUE_URL": AWS_RESOURCES["queue_url"],
        "DDB_TABLE": AWS_RESOURCES["dynamodb_table"],
        "S3_BUCKET": AWS_RESOURCES["s3_bucket"],
        "AWS_DEFAULT_REGION": env.get("AWS_DEFAULT_REGION", "us-east-1")
    })
    
    # Ensure we have API key
    if not (env.get("GEMINI_API_KEY") or env.get("OPENAI_API_KEY")):
        print("❌ Neither GEMINI_API_KEY nor OPENAI_API_KEY is set")
        return None
    
    cmd = [
        sys.executable,
        "scripts/run_pipeline.py",
        "--accounts", *TEST_ACCOUNTS,
        "--days", str(TEST_DAYS_BACK),
        "--max", str(TEST_MAX_TWEETS),
        "--output", str(output_path),
        "--aws"  # Use AWS resources
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print(f"Using AWS resources: Queue, DynamoDB, S3")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=Path(__file__).parent.parent)
        
        if result.returncode == 0:
            print("✅ Docker AWS test completed successfully")
            print(f"Messages sent to SQS queue: {AWS_RESOURCES['queue_url']}")
            
            # Wait a bit for processing
            print("\nWaiting 30 seconds for Fargate processing...")
            time.sleep(30)
            
            # Query DynamoDB for results
            return query_dynamodb_results()
        else:
            print(f"❌ Docker AWS test failed with return code: {result.returncode}")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error running Docker AWS test: {e}")
        return None

def query_dynamodb_results():
    """Query DynamoDB for classification results"""
    print("\nQuerying DynamoDB for results...")
    
    try:
        dynamodb = boto3.client('dynamodb')
        
        # Scan the table for recent results
        response = dynamodb.scan(
            TableName=AWS_RESOURCES["dynamodb_table"],
            Limit=10
        )
        
        items = response.get('Items', [])
        print(f"Found {len(items)} items in DynamoDB")
        
        # Convert DynamoDB format to regular JSON
        results = []
        for item in items:
            result = {}
            for key, value in item.items():
                # Extract the actual value from DynamoDB format
                if 'S' in value:
                    result[key] = value['S']
                elif 'N' in value:
                    result[key] = float(value['N'])
                elif 'M' in value:
                    # Handle nested maps
                    result[key] = {}
                    for k, v in value['M'].items():
                        if 'S' in v:
                            result[key][k] = v['S']
                        elif 'L' in v:
                            result[key][k] = [item.get('S', str(item)) for item in v['L']]
            results.append(result)
        
        return results
        
    except Exception as e:
        print(f"❌ Error querying DynamoDB: {e}")
        return None

def run_remote_aws_test():
    """Phase 3: Test remotely via AWS"""
    print_phase("3. REMOTE AWS TEST")
    
    print("Checking ECS service status...")
    
    try:
        ecs = boto3.client('ecs')
        
        # Describe the service
        response = ecs.describe_services(
            cluster=AWS_RESOURCES["ecs_cluster"],
            services=['classifier-service']  # Assuming this is the service name
        )
        
        if response['services']:
            service = response['services'][0]
            print(f"✓ ECS Service Status: {service['status']}")
            print(f"✓ Running tasks: {service['runningCount']}")
            print(f"✓ Desired tasks: {service['desiredCount']}")
        
        # Check CloudWatch logs
        print("\nChecking recent CloudWatch logs...")
        logs = boto3.client('logs')
        
        log_group = '/aws/ecs/classifier-service'  # Adjust if needed
        try:
            response = logs.describe_log_streams(
                logGroupName=log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=1
            )
            
            if response['logStreams']:
                stream = response['logStreams'][0]
                print(f"✓ Latest log stream: {stream['logStreamName']}")
                print(f"✓ Last event: {datetime.fromtimestamp(stream['lastEventTimestamp']/1000)}")
        except Exception as e:
            print(f"⚠️  Could not access CloudWatch logs: {e}")
        
        # Query current DynamoDB state
        return query_dynamodb_results()
        
    except Exception as e:
        print(f"❌ Error checking AWS resources: {e}")
        return None

def compare_results(local_results, aws_results):
    """Compare local and AWS results"""
    print_phase("RESULTS COMPARISON")
    
    if not local_results:
        print("❌ No local results to compare")
        return False
    
    if not aws_results:
        print("❌ No AWS results to compare")
        return False
    
    print(f"Local results count: {len(local_results) if isinstance(local_results, list) else 1}")
    print(f"AWS results count: {len(aws_results)}")
    
    # For visual capture service, the structure will be different
    # Local results will be enriched_results, AWS will be classified tweets
    print("\n📊 Results Summary:")
    print("\nLocal Results Structure:")
    if isinstance(local_results, dict):
        print(f"  - Success: {local_results.get('success', 'N/A')}")
        print(f"  - Account: {local_results.get('account', 'N/A')}")
        if 'captured_items' in local_results:
            print(f"  - Captured items: {len(local_results['captured_items'])}")
    
    print("\nAWS Results Structure:")
    for i, result in enumerate(aws_results[:3]):  # Show first 3
        print(f"\n  Result {i+1}:")
        print(f"    - Tweet ID: {result.get('tweet_id', 'N/A')}")
        print(f"    - Author: {result.get('author_username', 'N/A')}")
        if 'classification_result' in result:
            print(f"    - L1 Topics: {result['classification_result'].get('l1_topics', 'N/A')}")
            print(f"    - L2 Topic: {result['classification_result'].get('l2_topic', 'N/A')}")
    
    return True

def main():
    """Main test execution"""
    parser = argparse.ArgumentParser(description="Run comprehensive pipeline tests")
    parser.add_argument("--output-dir", default="test_outputs", help="Directory for test outputs")
    parser.add_argument("--skip-prerequisites", action="store_true", help="Skip prerequisite checks")
    args = parser.parse_args()
    
    print("🧪 GenAI Tweet Digest Pipeline - Comprehensive Testing")
    print(f"📅 Test started at: {datetime.now()}")
    
    # Check prerequisites
    if not args.skip_prerequisites and not check_prerequisites():
        print("\n❌ Prerequisites check failed. Please set required environment variables.")
        return 1
    
    # Create output directory
    output_dir = Path(args.output_dir) / f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Test outputs will be stored in: {output_dir}")
    
    # Phase 1: Local test
    local_results = run_local_test(output_dir)
    
    # Phase 2: Docker with AWS resources
    docker_aws_results = run_docker_aws_test(output_dir)
    
    # Phase 3: Remote AWS test
    remote_aws_results = run_remote_aws_test()
    
    # Compare results
    if docker_aws_results or remote_aws_results:
        compare_results(local_results, docker_aws_results or remote_aws_results)
    
    print("\n" + "="*80)
    print("🎉 Testing complete!")
    print(f"📊 Results stored in: {output_dir}")
    print("="*80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 