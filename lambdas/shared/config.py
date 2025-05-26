import os
import json
import boto3
from typing import List, Optional

class LambdaConfig:
    """Simplified configuration for Lambda functions."""
    
    def __init__(self):
        # Environment detection
        self.environment = os.getenv("ENVIRONMENT", "production")
        self.is_test = self.environment == "test"
        
        # API Keys from environment variables
        self.twitter_bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        # AWS Configuration
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        
        # Email Configuration
        self.from_email = os.getenv("FROM_EMAIL", "digest@genai-tweets.com")
        
        # S3 Configuration
        self.s3_bucket = os.getenv("S3_BUCKET", "genai-tweets-digest")
        self.accounts_key = "config/accounts.json"
        self.tweets_prefix = "tweets/"
        
        # DynamoDB Configuration
        self.subscribers_table = os.getenv("SUBSCRIBERS_TABLE", "genai-digest-subscribers")
        
        # Initialize AWS clients
        self.s3_client = boto3.client('s3', region_name=self.aws_region)
        self.dynamodb = boto3.resource('dynamodb', region_name=self.aws_region)
        self.ses_client = boto3.client('ses', region_name=self.aws_region)
    
    def get_influential_accounts(self) -> List[str]:
        """Load influential accounts from S3."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=self.accounts_key
            )
            accounts_data = json.loads(response['Body'].read().decode('utf-8'))
            return accounts_data.get('influential_accounts', [])
        except Exception as e:
            print(f"Error loading accounts from S3: {e}")
            # Fallback to default accounts
            return [
                "AndrewYNg", "OpenAI", "GoogleDeepMind", 
                "ylecun", "karpathy", "jeffdean"
            ]
    
    def validate_required_env_vars(self) -> bool:
        """Validate that all required environment variables are set."""
        required_vars = [
            "TWITTER_BEARER_TOKEN",
            "GEMINI_API_KEY", 
            "S3_BUCKET",
            "SUBSCRIBERS_TABLE"
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"Missing required environment variables: {missing_vars}")
            return False
        
        return True

# Global config instance
config = LambdaConfig() 