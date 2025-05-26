# Frontend Testing & Troubleshooting Guide

## 🔧 Avoiding "Failed to Fetch" Issues

### **1. Deployment Best Practices**

#### Always Use the Frontend Deployment Script
```bash
# Use this instead of manual deployment
./scripts/deploy-frontend.sh
```

#### Manual Deployment Steps (if needed)
```bash
# 1. Build frontend
cd frontend-static && npm run build

# 2. Upload to S3
aws s3 sync out/ s3://BUCKET_NAME/ --delete --profile personal
aws s3 cp config.js s3://BUCKET_NAME/config.js --profile personal

# 3. Invalidate CloudFront (CRITICAL!)
aws cloudfront create-invalidation --distribution-id DISTRIBUTION_ID --paths "/*" --profile personal

# 4. Wait for invalidation to complete
aws cloudfront wait invalidation-completed --distribution-id DISTRIBUTION_ID --id INVALIDATION_ID --profile personal
```

### **2. Browser Testing Best Practices**

#### Hard Refresh After Deployments
- **Chrome/Firefox**: `Ctrl+F5` or `Cmd+Shift+R`
- **Safari**: `Cmd+Option+R`

#### Use Incognito/Private Mode
- Bypasses all browser cache
- Best for testing fresh deployments

#### Developer Tools Network Tab
1. Open DevTools (`F12`)
2. Go to Network tab
3. Check "Disable cache"
4. Try the failing request
5. Look for actual error messages

### **3. API Testing Workflow**

#### Test API Directly First
```bash
# Test subscription endpoint
curl -X POST https://API_URL/production/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}' \
  -v

# Check CORS
curl -X OPTIONS https://API_URL/production/subscribe \
  -H "Origin: https://your-domain.cloudfront.net" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v
```

#### Verify Configuration
```bash
# Check config.js is updated
curl -s https://your-domain.cloudfront.net/config.js

# Check API Gateway URL
aws cloudformation describe-stacks --stack-name STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayURL`].OutputValue' \
  --output text
```

### **4. Common Issues & Solutions**

#### Issue: "Failed to fetch"
**Causes:**
- CloudFront cache not invalidated
- Browser cache
- CORS misconfiguration
- API Gateway deployment not updated

**Solutions:**
1. Invalidate CloudFront cache
2. Hard refresh browser
3. Test in incognito mode
4. Check browser console for actual error
5. Test API directly with curl

#### Issue: API returns 404
**Causes:**
- API Gateway deployment not updated
- Wrong API URL in config

**Solutions:**
```bash
# Create new API Gateway deployment
aws apigateway create-deployment \
  --rest-api-id API_ID \
  --stage-name production \
  --region us-east-1
```

#### Issue: CORS errors
**Causes:**
- Missing OPTIONS method
- Incorrect CORS headers

**Solutions:**
- Verify OPTIONS method exists in CloudFormation
- Check CORS headers in Lambda response

### **5. Testing Checklist**

#### Before Testing
- [ ] Deploy backend changes
- [ ] Deploy frontend changes
- [ ] Invalidate CloudFront cache
- [ ] Wait for invalidation to complete (2-3 minutes)

#### During Testing
- [ ] Use hard refresh or incognito mode
- [ ] Check browser console for errors
- [ ] Test API directly if frontend fails
- [ ] Verify config.js has correct API URL

#### After Issues
- [ ] Check CloudWatch logs for Lambda errors
- [ ] Verify API Gateway deployment is latest
- [ ] Test CORS with curl
- [ ] Check S3 bucket has latest files

### **6. Development Workflow**

#### Local Development
```bash
# 1. Make frontend changes
cd frontend-static
npm run dev  # Test locally first

# 2. Test against deployed API
# Update config.js with production API URL for local testing
```

#### Staging Deployment
```bash
# 1. Deploy to staging first
./scripts/deploy.sh staging

# 2. Test staging environment
# 3. Deploy to production
./scripts/deploy.sh production
```

#### Production Deployment
```bash
# 1. Deploy backend
./scripts/deploy.sh

# 2. Deploy frontend
./scripts/deploy-frontend.sh

# 3. Test end-to-end
```

### **7. Monitoring & Debugging**

#### CloudWatch Logs
```bash
# Check Lambda logs
aws logs describe-log-streams --log-group-name '/aws/lambda/FUNCTION_NAME'
aws logs get-log-events --log-group-name '/aws/lambda/FUNCTION_NAME' --log-stream-name 'STREAM_NAME'
```

#### API Gateway Logs
```bash
# Enable API Gateway logging in CloudFormation
# Check execution logs for request/response details
```

#### CloudFront Logs
```bash
# Check CloudFront access logs
# Monitor cache hit/miss ratios
```

### **8. Emergency Fixes**

#### Quick Frontend Fix
```bash
# 1. Fix the issue locally
# 2. Build and deploy immediately
cd frontend-static && npm run build
aws s3 sync out/ s3://BUCKET_NAME/ --delete
aws cloudfront create-invalidation --distribution-id DIST_ID --paths "/*"
```

#### API Gateway Reset
```bash
# Force new API Gateway deployment
aws apigateway create-deployment \
  --rest-api-id API_ID \
  --stage-name production \
  --description "Emergency fix deployment"
```

#### Cache Bypass for Testing
```bash
# Add cache-busting parameter
https://your-domain.cloudfront.net/?v=$(date +%s)
``` 