#!/usr/bin/env python3
"""Check AWS resources status for the classifier pipeline."""

import boto3
import json
from datetime import datetime

# AWS Resources from CURRENT_STATUS.md
AWS_RESOURCES = {
    "queue_url": "https://sqs.us-east-1.amazonaws.com/855450210814/ClassifierStack-ClassificationQueueEEAC6F55-5wEAB6cca8te",
    "dynamodb_table": "ClassifierStack-TweetTopicsTableD9CB57C4-1A8FFGIVK5AJ2",
    "s3_bucket": "classifierstack-tweetscreenshotbucketb280f4b5-utgkcgleaevv",
    "ecs_cluster": "ClassifierStack-ClassifierCluster3B5A8E18-NTkykRVbVDF1"
}

def check_sqs_queue():
    """Check SQS queue status and messages."""
    print("\n📬 Checking SQS Queue...")
    try:
        sqs = boto3.client('sqs', region_name='us-east-1')
        
        # Get queue attributes
        response = sqs.get_queue_attributes(
            QueueUrl=AWS_RESOURCES["queue_url"],
            AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
        )
        
        attrs = response['Attributes']
        print(f"✓ Messages available: {attrs['ApproximateNumberOfMessages']}")
        print(f"✓ Messages in flight: {attrs['ApproximateNumberOfMessagesNotVisible']}")
        
    except Exception as e:
        print(f"❌ Error checking SQS: {e}")

def check_ecs_service():
    """Check ECS service status."""
    print("\n🚢 Checking ECS Service...")
    try:
        ecs = boto3.client('ecs', region_name='us-east-1')
        
        # List services in the cluster
        services_response = ecs.list_services(
            cluster=AWS_RESOURCES["ecs_cluster"]
        )
        
        if not services_response['serviceArns']:
            print("❌ No services found in the cluster")
            return
        
        print(f"✓ Found {len(services_response['serviceArns'])} service(s)")
        
        # Describe each service
        for service_arn in services_response['serviceArns']:
            service_name = service_arn.split('/')[-1]
            print(f"\n  Service: {service_name}")
            
            describe_response = ecs.describe_services(
                cluster=AWS_RESOURCES["ecs_cluster"],
                services=[service_arn]
            )
            
            if describe_response['services']:
                service = describe_response['services'][0]
                print(f"  - Status: {service['status']}")
                print(f"  - Running tasks: {service['runningCount']}")
                print(f"  - Desired tasks: {service['desiredCount']}")
                print(f"  - Launch type: {service.get('launchType', 'N/A')}")
                
                # Check if tasks are running
                if service['runningCount'] == 0:
                    print("  ⚠️  No tasks are running!")
                
    except Exception as e:
        print(f"❌ Error checking ECS: {e}")

def check_dynamodb():
    """Check DynamoDB for recent entries."""
    print("\n💾 Checking DynamoDB...")
    try:
        dynamodb = boto3.client('dynamodb', region_name='us-east-1')
        
        # Scan the table for recent results
        response = dynamodb.scan(
            TableName=AWS_RESOURCES["dynamodb_table"],
            Limit=5
        )
        
        items = response.get('Items', [])
        print(f"✓ Found {len(items)} recent items")
        
        # Show first few items
        for i, item in enumerate(items[:3]):
            print(f"\n  Item {i+1}:")
            if 'tweet_id' in item:
                print(f"    - Tweet ID: {item['tweet_id'].get('S', 'N/A')}")
            if 'author_username' in item:
                print(f"    - Author: {item['author_username'].get('S', 'N/A')}")
            if 'classified_at' in item:
                print(f"    - Classified at: {item['classified_at'].get('S', 'N/A')}")
                
    except Exception as e:
        print(f"❌ Error checking DynamoDB: {e}")

def check_cloudwatch_logs():
    """Check CloudWatch logs for errors."""
    print("\n📊 Checking CloudWatch Logs...")
    try:
        logs = boto3.client('logs', region_name='us-east-1')
        
        # Try different log group names
        log_groups = [
            '/aws/ecs/classifier-service',
            '/ecs/ClassifierStack',
            '/aws/fargate/classifier'
        ]
        
        found_log_group = None
        for log_group in log_groups:
            try:
                logs.describe_log_groups(logGroupNamePrefix=log_group, limit=1)
                found_log_group = log_group
                break
            except:
                continue
        
        if not found_log_group:
            print("⚠️  No log groups found for the classifier service")
            print("  Trying to list all ECS log groups...")
            
            # List all log groups with ECS prefix
            response = logs.describe_log_groups(logGroupNamePrefix='/aws/ecs/', limit=10)
            if response['logGroups']:
                print("\n  Available ECS log groups:")
                for lg in response['logGroups']:
                    print(f"    - {lg['logGroupName']}")
            
    except Exception as e:
        print(f"❌ Error checking CloudWatch: {e}")

def main():
    """Run all checks."""
    print("🔍 AWS Resources Status Check")
    print("=" * 50)
    
    check_sqs_queue()
    check_ecs_service()
    check_dynamodb()
    check_cloudwatch_logs()
    
    print("\n" + "=" * 50)
    print("✅ Status check complete")

if __name__ == "__main__":
    main() 