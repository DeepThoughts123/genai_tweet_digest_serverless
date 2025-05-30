// Configuration for the static frontend
// Update these values after deploying the serverless infrastructure

const config = {
  // API Gateway endpoint (update after deployment)
  API_BASE_URL: 'https://dzin6h5zvf.execute-api.us-east-1.amazonaws.com/production',
  
  // Subscription endpoint
  SUBSCRIPTION_ENDPOINT: '/subscribe',
  
  // Environment
  ENVIRONMENT: process.env.NODE_ENV || 'production',
  
  // Feature flags
  FEATURES: {
    SUBSCRIPTION: true,
    ANALYTICS: false
  }
};

// Export for both CommonJS and ES modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = config;
} else if (typeof window !== 'undefined') {
  window.APP_CONFIG = config;
  window.CONFIG = config;
}

export default config; 