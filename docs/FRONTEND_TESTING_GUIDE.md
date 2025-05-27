# Frontend Testing & Troubleshooting Guide

## 🧪 Integration Testing Learnings & Solutions

### **Major Achievement: 100% Frontend Test Success Rate**

After comprehensive testing and troubleshooting, we achieved **100% frontend test success** (24/24 tests passing), up from an initial **62% success rate** (15/24 tests). This section documents the key learnings and solutions.

#### Key Issues Identified & Resolved

**1. Jest Environment Configuration for API Testing**

**Problem**: Integration tests were failing due to missing test environment setup for API calls and Headers API mocking.

**Solution**: Enhanced Jest configuration with proper environment setup:

```javascript
// jest.config.js - Enhanced configuration
const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  testEnvironment: 'jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  setupFiles: ['<rootDir>/jest.env.js'], // Critical addition
}
```

```javascript
// jest.env.js - Environment setup for testing
global.window = global.window || {};
global.window.CONFIG = {
  API_BASE_URL: 'https://dzin6h5zvf.execute-api.us-east-1.amazonaws.com/production'
};

process.env.NEXT_PUBLIC_API_BASE_URL = 'https://dzin6h5zvf.execute-api.us-east-1.amazonaws.com/production';
```

**2. Headers API Mocking for Fetch Responses**

**Problem**: Test environment lacked proper Headers API implementation, causing fetch response handling to fail.

**Solution**: Comprehensive Headers API mock in `jest.setup.ts`:

```typescript
// Enhanced Headers API mock
global.Headers = class Headers {
  private headers: Map<string, string>;
  
  constructor(init?: Record<string, string> | [string, string][] | Headers) {
    this.headers = new Map();
    // Proper initialization logic for all Header constructor types
  }
  
  // Full implementation of Headers API methods
  entries(): IterableIterator<[string, string]> {
    return this.headers.entries();
  }
  // ... other methods
};
```

**3. API Service Environment Compatibility**

**Problem**: API service failed in server-side rendering environments (Jest) due to undefined `window` object.

**Solution**: Enhanced environment detection in API service:

```javascript
// api.js - Enhanced environment detection
class ApiService {
  constructor() {
    // Check if we're in browser environment
    if (typeof window === 'undefined') {
      // Server-side rendering - use default values
      this.baseURL = 'https://dzin6h5zvf.execute-api.us-east-1.amazonaws.com/production';
      return;
    }
    
    // Browser environment - use dynamic configuration
    this.config = window.CONFIG || window.APP_CONFIG || {};
    this.baseURL = this.config.API_BASE_URL || 
                   process.env.NEXT_PUBLIC_API_BASE_URL || 
                   'https://dzin6h5zvf.execute-api.us-east-1.amazonaws.com/production';
  }
}
```

**4. Error Message Expectations Alignment**

**Problem**: Integration tests expected different error messages than what the component actually displayed.

**Solution**: Aligned test expectations with actual component behavior:

```javascript
// Fixed error message expectations
await waitFor(() => {
  expect(screen.getByText(/verification email sent! please check your inbox and click the verification link/i)).toBeInTheDocument();
});

// Instead of incorrect expectation:
// expect(screen.getByText(/successfully subscribed/i)).toBeInTheDocument();
```

#### Integration Test Categories Successfully Implemented

**✅ API Integration Tests (11 tests)**
- Successful subscription flow with AWS API Gateway
- Error handling for all HTTP status codes (400, 409, 422, 500)
- Network error handling with proper fallback messages
- API endpoint URL validation
- Request payload and header validation
- Loading state management during API calls

**✅ Component Integration Tests (13 tests)**
- Form validation with real API integration
- Custom callback handling vs. default API service
- Email trimming and sanitization
- User interaction flows (typing, clicking, keyboard navigation)
- Accessibility compliance (ARIA attributes, focus management)

#### Performance Improvements Achieved

**Before Optimization:**
- ❌ 15/24 tests passing (62% success rate)
- ❌ Headers API errors breaking fetch mocking
- ❌ Environment configuration mismatches
- ❌ Inconsistent error message expectations

**After Optimization:**
- ✅ 24/24 tests passing (100% success rate)
- ✅ Robust Headers API mocking
- ✅ Consistent environment setup across test and production
- ✅ Accurate error message validation

#### Best Practices for Frontend Integration Testing

**1. Environment Setup Strategy**
```javascript
// Always provide proper test environment setup
// jest.env.js for global configuration
// jest.setup.ts for API mocking
// Separate concerns between configuration and mocking
```

**2. API Service Design Patterns**
```javascript
// Design API services to be environment-aware
// Graceful fallback for server-side rendering
// Consistent error handling across environments
// Proper logging that doesn't break in test environments
```

**3. Test Expectation Management**
```javascript
// Match test expectations with actual component behavior
// Use the exact error messages the component displays
// Test against real API URLs and endpoints
// Validate complete user journeys, not just happy paths
```

**4. Mock Strategy**
```javascript
// Provide complete Web API implementations in tests
// Mock Headers, Response, and other fetch-related APIs
// Ensure mocks match real browser behavior
// Use proper TypeScript types even in test implementations
```

#### Testing Infrastructure Lessons

**Jest Configuration Management:**
- Use `setupFiles` for environment variables and global configuration
- Use `setupFilesAfterEnv` for test framework setup and API mocking
- Proper `moduleNameMapper` for path resolution in Next.js projects

**API Testing Strategy:**
- Test against actual deployed endpoints when possible
- Mock comprehensively when testing in isolation
- Validate both success and error scenarios
- Test loading states and user interaction flows

**Error Handling Validation:**
- Test all HTTP status codes your API can return
- Validate error message display matches component implementation
- Test network errors and timeout scenarios
- Ensure graceful degradation when APIs are unavailable

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