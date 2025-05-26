// API service for GenAI Tweets Digest
class ApiService {
  constructor() {
    // Check if we're in browser environment
    if (typeof window === 'undefined') {
      // Server-side rendering - use default values
      this.baseURL = 'https://dzin6h5zvf.execute-api.us-east-1.amazonaws.com/production';
      return;
    }
    
    // Try to get config from window object first (loaded from config.js)
    this.config = window.CONFIG || window.APP_CONFIG || {};
    
    // Fallback to environment variables or defaults
    this.baseURL = this.config.API_BASE_URL || 
                   process.env.NEXT_PUBLIC_API_BASE_URL || 
                   'https://dzin6h5zvf.execute-api.us-east-1.amazonaws.com/production';
    
    console.log('API Service initialized with baseURL:', this.baseURL);
  }

  async subscribe(email) {
    const url = `${this.baseURL}/subscribe`;
    
    console.log('Making subscription request to:', url);
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      console.log('Response status:', response.status);
      console.log('Response headers:', Object.fromEntries(response.headers.entries()));

      const data = await response.json();
      console.log('Response data:', data);

      if (!response.ok) {
        let errorMessage = data.message || data.error || 'Subscription failed';
        
        // Handle specific status codes
        if (response.status === 422) {
          errorMessage = 'Please enter a valid email address';
        } else if (response.status === 409) {
          errorMessage = data.message || 'Email already subscribed to weekly digest';
        } else if (response.status === 400) {
          errorMessage = 'Please enter a valid email address';
        } else if (response.status === 500) {
          errorMessage = 'Server error. Please try again later.';
        }
        
        const error = new Error(errorMessage);
        error.status = response.status;
        error.data = data;
        throw error;
      }

      return data;
    } catch (error) {
      console.error('API request failed:', error);
      
      // Handle network errors
      if (error instanceof TypeError && error.message.includes('fetch')) {
        const networkError = new Error('Network error. Please check your connection and try again.');
        networkError.status = 0;
        networkError.originalError = error;
        throw networkError;
      }
      
      // Re-throw API errors
      throw error;
    }
  }

  // Health check method for debugging
  async healthCheck() {
    try {
      const response = await fetch(`${this.baseURL}/health`, {
        method: 'GET',
      });
      return response.ok;
    } catch (error) {
      console.error('Health check failed:', error);
      return false;
    }
  }

  async getSubscriberCount() {
    try {
      const response = await fetch(`${this.baseURL}/subscriber-count`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        return { subscriber_count: 0 };
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching subscriber count:', error);
      return { subscriber_count: 0 };
    }
  }
}

// Export singleton instance
const apiService = new ApiService();
export default apiService;
