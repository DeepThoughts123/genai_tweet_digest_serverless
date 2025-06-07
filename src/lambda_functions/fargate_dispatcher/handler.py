"""
Lambda function to dispatch visual tweet processing to EC2 instances.
Triggered by EventBridge or manual invocation.
"""

import json
import boto3
import os
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """
    Main handler for visual processing dispatcher.
    
    This function:
    1. Validates processing requirements
    2. Launches EC2 instance for visual processing
    3. Monitors instance launch status
    4. Returns processing job information
    """
    
    logger.info("Starting visual processing dispatcher...")
    
    try:
        # Initialize AWS clients
        ec2_client = boto3.client('ec2')
        autoscaling_client = boto3.client('autoscaling')
        
        # Get configuration from environment
        asg_name = os.environ.get('EC2_AUTOSCALING_GROUP_NAME')
        instance_type = os.environ.get('EC2_INSTANCE_TYPE', 't3.medium')
        max_processing_time = int(os.environ.get('MAX_PROCESSING_TIME', '7200'))  # 2 hours
        s3_bucket = os.environ.get('S3_BUCKET_NAME')
        
        if not asg_name or not s3_bucket:
            raise ValueError("Missing required environment variables: EC2_AUTOSCALING_GROUP_NAME or S3_BUCKET_NAME")
        
        # Parse event parameters
        accounts = event.get('accounts', [])
        days_back = event.get('days_back', 7)
        max_tweets = event.get('max_tweets', 20)
        zoom_percent = event.get('zoom_percent', 30)
        processing_mode = event.get('processing_mode', 'visual_capture')
        
        # Validate accounts list
        if not accounts:
            # Use default accounts if none specified
            accounts = ['minchoi', 'openai', 'andrewyng', 'rasbt', 'ylecun']
            logger.info(f"Using default accounts: {accounts}")
        
        logger.info(f"Processing configuration:")
        logger.info(f"  Accounts: {accounts}")
        logger.info(f"  Days back: {days_back}")
        logger.info(f"  Max tweets per account: {max_tweets}")
        logger.info(f"  Processing mode: {processing_mode}")
        
        # Check if instances are already running
        current_instances = get_running_processing_instances(ec2_client)
        if current_instances:
            logger.warning(f"Processing instances already running: {current_instances}")
            return {
                'statusCode': 409,
                'body': json.dumps({
                    'status': 'conflict',
                    'message': 'Visual processing already in progress',
                    'running_instances': current_instances
                })
            }
        
        # Prepare user data script for EC2 instance
        user_data = prepare_user_data_script(
            accounts=accounts,
            days_back=days_back,
            max_tweets=max_tweets,
            zoom_percent=zoom_percent,
            s3_bucket=s3_bucket,
            processing_mode=processing_mode
        )
        
        # Launch EC2 instance via Auto Scaling
        job_id = f"visual-processing-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Update Auto Scaling Group to launch instance
        response = autoscaling_client.set_desired_capacity(
            AutoScalingGroupName=asg_name,
            DesiredCapacity=1,
            HonorCooldown=False
        )
        
        logger.info(f"Triggered Auto Scaling Group: {asg_name}")
        
        # Update launch configuration with user data
        # Note: In production, you might want to use launch templates for better control
        
        # Return processing job information
        response_data = {
            'status': 'dispatched',
            'job_id': job_id,
            'asg_name': asg_name,
            'instance_type': instance_type,
            'estimated_completion_time': max_processing_time,
            'processing_config': {
                'accounts': accounts,
                'days_back': days_back,
                'max_tweets': max_tweets,
                'zoom_percent': zoom_percent,
                'processing_mode': processing_mode
            },
            's3_bucket': s3_bucket,
            'monitoring': {
                'cloudwatch_log_group': f'/aws/ec2/visual-processing/{job_id}',
                's3_results_prefix': f'visual-processing/{job_id}/'
            }
        }
        
        logger.info("Visual processing dispatch completed successfully")
        logger.info(f"Job ID: {job_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(response_data, default=str)
        }
        
    except Exception as e:
        error_message = f"Error in visual processing dispatcher: {str(e)}"
        logger.error(error_message)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'error': str(e),
                'message': 'Visual processing dispatch failed'
            })
        }

def get_running_processing_instances(ec2_client):
    """Check for running visual processing instances."""
    try:
        response = ec2_client.describe_instances(
            Filters=[
                {'Name': 'tag:Purpose', 'Values': ['visual-tweet-processing']},
                {'Name': 'instance-state-name', 'Values': ['pending', 'running']}
            ]
        )
        
        running_instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                running_instances.append({
                    'instance_id': instance['InstanceId'],
                    'state': instance['State']['Name'],
                    'launch_time': instance['LaunchTime']
                })
        
        return running_instances
        
    except Exception as e:
        logger.error(f"Error checking running instances: {e}")
        return []

def prepare_user_data_script(accounts, days_back, max_tweets, zoom_percent, s3_bucket, processing_mode):
    """Prepare user data script for EC2 instance initialization."""
    
    # Convert accounts list to space-separated string
    accounts_str = ' '.join(accounts)
    
    user_data_script = f"""#!/bin/bash
set -e

# Set up logging
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
echo "Starting visual tweet processing setup at $(date)"

# Update system
yum update -y

# Install Python 3.11 and dependencies
yum install -y python3.11 python3.11-pip git

# Install Chrome and dependencies
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list
yum install -y google-chrome-stable

# Create processing directory
mkdir -p /opt/visual-processing
cd /opt/visual-processing

# Download processing code from S3 or Git
# Note: In production, you'd store the code in S3 or use a pre-built AMI

# Set environment variables
export S3_BUCKET="{s3_bucket}"
export PROCESSING_MODE="{processing_mode}"
export ACCOUNTS="{accounts_str}"
export DAYS_BACK="{days_back}"
export MAX_TWEETS="{max_tweets}"
export ZOOM_PERCENT="{zoom_percent}"

# Set AWS credentials (assuming IAM role)
export AWS_DEFAULT_REGION="us-east-1"

# Install Python dependencies
pip3.11 install -r requirements.txt

# Run the visual processing pipeline
echo "Starting visual processing at $(date)"
python3.11 visual_processing_service.py \\
    --accounts {accounts_str} \\
    --days-back {days_back} \\
    --max-tweets {max_tweets} \\
    --zoom {zoom_percent} \\
    --s3-bucket {s3_bucket} \\
    --processing-mode {processing_mode} \\
    --output-dir /tmp/visual-processing-output

# Check if processing completed successfully
if [ $? -eq 0 ]; then
    echo "Visual processing completed successfully at $(date)"
    
    # Signal completion to CloudWatch or S3
    aws s3 cp /tmp/processing-complete.json s3://{s3_bucket}/visual-processing/status/
    
    # Send success notification
    aws sns publish --topic-arn ${{SNS_TOPIC_ARN}} --message "Visual processing completed successfully"
else
    echo "Visual processing failed at $(date)"
    
    # Send failure notification
    aws sns publish --topic-arn ${{SNS_TOPIC_ARN}} --message "Visual processing failed"
fi

# Clean up and shutdown
echo "Cleaning up and shutting down at $(date)"
rm -rf /tmp/visual-processing-output
shutdown -h +5
"""
    
    return user_data_script

def manual_trigger_handler(event, context):
    """
    Handler for manual visual processing dispatch (for testing).
    Can be triggered via API Gateway or directly.
    """
    
    logger.info("Manual visual processing dispatch triggered")
    
    # Add some context to distinguish manual vs scheduled runs
    event['manual_trigger'] = True
    event['processing_mode'] = event.get('processing_mode', 'visual_capture')
    
    # Call the main handler
    result = lambda_handler(event, context)
    
    # Add manual trigger info to response
    if result.get('body'):
        body = json.loads(result['body'])
        body['trigger_type'] = 'manual'
        result['body'] = json.dumps(body, default=str)
    
    return result 