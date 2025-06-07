# Debugging "Failed to Fetch" Issues

## 🔍 **Step-by-Step Debugging Process**

### **1. Browser Developer Tools Investigation**

#### Open Browser DevTools
1. **Right-click** on the page → **Inspect** (or press `F12`)
2. Go to **Console** tab first
3. Look for any JavaScript errors

#### Check Network Tab
1. Go to **Network** tab
2. **Clear** existing requests
3. Try the subscription again
4. Look for the failed request

#### What to Look For:
```
❌ Failed Request Indicators:
- Red status (failed/error)
- Status codes: 0, 404, 500, etc.
- CORS errors
- Timeout errors

✅ Successful Request Indicators:
- Green status (200, 201)
- Response data visible
- Proper headers
```

### **2. Console Error Analysis**

#### Common Error Messages & Meanings:

**Error: "Failed to fetch"**
```javascript
TypeError: Failed to fetch
```
**Causes:**
- Network connectivity issues
- CORS policy blocking request
- Invalid URL
- Server not responding

**Error: "CORS policy"**
```javascript
Access to fetch at 'https://api...' from origin 'https://domain...' 
has been blocked by CORS policy
```
**Causes:**
- Missing CORS headers
- Incorrect Origin header
- Missing OPTIONS method

**Error: "NetworkError"**
```javascript
NetworkError when attempting to fetch resource
```
**Causes:**
- DNS resolution failure
- SSL certificate issues
- Firewall blocking

### **3. API Configuration Verification**

#### Check Config Loading
Open browser console and run:
```javascript
// Check if config is loaded
console.log('Window CONFIG:', window.CONFIG);
console.log('Window APP_CONFIG:', window.APP_CONFIG);

// Check API service
console.log('API Service baseURL:', window.apiService?.baseURL);
```

#### Verify API URL
```javascript
// Test if API URL is reachable
fetch('https://dzin6h5zvf.execute-api.us-east-1.amazonaws.com/production/subscribe', {
  method: 'OPTIONS'
}).then(response => {
  console.log('OPTIONS response:', response.status);
}).catch(error => {
  console.error('OPTIONS failed:', error);
});
```

### **4. Network Layer Testing**

#### Test API Directly (Terminal)
```bash
# Test basic connectivity
curl -v https://dzin6h5zvf.execute-api.us-east-1.amazonaws.com/production/subscribe

# Test CORS preflight
curl -X OPTIONS \
  -H "Origin: https://d3nb4wb7d39hqj.cloudfront.net" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  https://dzin6h5zvf.execute-api.us-east-1.amazonaws.com/production/subscribe \
  -v

# Test actual POST request
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Origin: https://d3nb4wb7d39hqj.cloudfront.net" \
  -d '{"email": "test@example.com"}' \
  https://dzin6h5zvf.execute-api.us-east-1.amazonaws.com/production/subscribe \
  -v
```

### **5. CloudFront Cache Investigation**

#### Check if Files are Updated
```bash
# Check config.js timestamp
curl -I https://d3nb4wb7d39hqj.cloudfront.net/config.js

# Check JavaScript files
curl -I https://d3nb4wb7d39hqj.cloudfront.net/_next/static/chunks/app/page-*.js
```

#### Force Cache Bypass
```javascript
// In browser console, test with cache-busting
const timestamp = Date.now();
fetch(`https://d3nb4wb7d39hqj.cloudfront.net/config.js?v=${timestamp}`)
  .then(response => response.text())
  .then(text => console.log('Config content:', text));
```

### **6. JavaScript Loading Issues**

#### Check Script Loading
```javascript
// In browser console
console.log('Scripts loaded:', document.scripts.length);
Array.from(document.scripts).forEach((script, index) => {
  console.log(`Script ${index}:`, script.src, script.readyState);
});
```

#### Test API Service Manually
```javascript
// In browser console, test API service directly
const testEmail = 'test@example.com';
fetch('https://dzin6h5zvf.execute-api.us-east-1.amazonaws.com/production/subscribe', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ email: testEmail }),
})
.then(response => {
  console.log('Response status:', response.status);
  console.log('Response headers:', Object.fromEntries(response.headers.entries()));
  return response.json();
})
.then(data => console.log('Response data:', data))
.catch(error => console.error('Fetch error:', error));
```

### **7. Environment-Specific Debugging**

#### Check Environment Variables
```javascript
// In browser console
console.log('Process env:', typeof process !== 'undefined' ? process.env : 'Not available');
console.log('Next public vars:', Object.keys(window).filter(key => key.includes('NEXT')));
```

#### Verify Build Configuration
```bash
# Check if build includes correct config
cd frontend-static
npm run build
cat out/config.js
```

### **8. Common Root Causes & Solutions**

#### Issue 1: Config Not Loading
**Symptoms:** `window.CONFIG` is undefined
**Debug:**
```javascript
// Check if config.js is loaded
console.log('Config script:', document.querySelector('script[src*="config.js"]'));
```
**Solution:** Ensure config.js is properly uploaded and referenced

#### Issue 2: CORS Misconfiguration
**Symptoms:** CORS error in console
**Debug:**
```bash
# Check CORS headers
curl -X OPTIONS -H "Origin: https://d3nb4wb7d39hqj.cloudfront.net" \
  https://dzin6h5zvf.execute-api.us-east-1.amazonaws.com/production/subscribe -v
```
**Solution:** Update API Gateway CORS configuration

#### Issue 3: CloudFront Cache
**Symptoms:** Old JavaScript files being served
**Debug:**
```bash
# Check file timestamps
curl -I https://d3nb4wb7d39hqj.cloudfront.net/_next/static/chunks/app/page-*.js
```
**Solution:** Invalidate CloudFront cache

#### Issue 4: API Gateway Deployment
**Symptoms:** 404 or "Missing Authentication Token"
**Debug:**
```bash
# Check API Gateway deployment
aws apigateway get-deployments --rest-api-id dzin6h5zvf --region us-east-1
```
**Solution:** Create new API Gateway deployment

### **9. Debugging Checklist**

#### Browser Investigation
- [ ] Check Console for JavaScript errors
- [ ] Check Network tab for failed requests
- [ ] Verify config.js is loaded correctly
- [ ] Test API calls manually in console

#### Network Testing
- [ ] Test API with curl
- [ ] Verify CORS preflight works
- [ ] Check DNS resolution
- [ ] Test from different networks

#### Infrastructure Verification
- [ ] Verify CloudFront invalidation completed
- [ ] Check API Gateway deployment status
- [ ] Verify Lambda function is updated
- [ ] Check S3 bucket has latest files

#### Environment Checks
- [ ] Verify config.js has correct API URL
- [ ] Check environment variables
- [ ] Verify build process completed successfully
- [ ] Test in incognito mode

### **10. Quick Diagnostic Script**

Run this in browser console for comprehensive check:
```javascript
// Comprehensive diagnostic
const diagnostic = {
  config: window.CONFIG || window.APP_CONFIG,
  apiService: window.apiService,
  scripts: Array.from(document.scripts).map(s => s.src),
  location: window.location.href,
  userAgent: navigator.userAgent,
  timestamp: new Date().toISOString()
};

console.log('🔍 Diagnostic Report:', diagnostic);

// Test API connectivity
if (diagnostic.config?.API_BASE_URL) {
  fetch(`${diagnostic.config.API_BASE_URL}/subscribe`, {
    method: 'OPTIONS'
  })
  .then(response => console.log('✅ API reachable:', response.status))
  .catch(error => console.error('❌ API unreachable:', error));
} else {
  console.error('❌ No API URL found in config');
}
``` 