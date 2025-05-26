#!/bin/bash

# Frontend Deployment Script with Cache Invalidation
set -e

echo "🚀 Starting frontend deployment..."

# Get CloudFront distribution ID
DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
    --stack-name genai-tweets-digest-production \
    --region us-east-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
    --output text \
    --profile personal)

# Get S3 bucket name
BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name genai-tweets-digest-production \
    --region us-east-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`WebsiteBucketName`].OutputValue' \
    --output text \
    --profile personal)

# Build frontend
echo "📦 Building frontend..."
cd frontend-static
npm run build

# Upload to S3
echo "☁️ Uploading to S3..."
aws s3 sync out/ s3://$BUCKET_NAME/ --delete --profile personal
aws s3 cp config.js s3://$BUCKET_NAME/config.js --profile personal

# Invalidate CloudFront cache
echo "🔄 Invalidating CloudFront cache..."
INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id $DISTRIBUTION_ID \
    --paths "/*" \
    --profile personal \
    --query 'Invalidation.Id' \
    --output text)

echo "⏳ Waiting for invalidation to complete..."
aws cloudfront wait invalidation-completed \
    --distribution-id $DISTRIBUTION_ID \
    --id $INVALIDATION_ID \
    --profile personal

echo "✅ Frontend deployment complete!"
echo "🌐 Website: https://$(aws cloudfront get-distribution --id $DISTRIBUTION_ID --profile personal --query 'Distribution.DomainName' --output text)" 