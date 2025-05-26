import config from '../../config.js';

class ApiService {
  constructor() {
    this.baseUrl = config.API_BASE_URL;
  }

  async subscribe(email) {
    try {
      const response = await fetch(`${this.baseUrl}${config.SUBSCRIPTION_ENDPOINT}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        // Create error with status code information for better error handling
        let errorMessage = data.message || data.error || 'Subscription failed';
        
        // Handle specific status codes with proper messages
        if (response.status === 422) {
          errorMessage = 'Please enter a valid email address';
        } else if (response.status === 409) {
          // Use the actual message from the API response
          errorMessage = data.message || 'Email already subscribed to weekly digest';
        } else if (response.status === 400) {
          errorMessage = 'Please enter a valid email address';
        }
        
        const error = new Error(errorMessage);
        error.status = response.status;
        throw error;
      }

      return data;
    } catch (error) {
      console.error('Subscription error:', error);
      throw error;
    }
  }

  async getSubscriberCount() {
    try {
      const response = await fetch(`${this.baseUrl}/subscriber-count`, {
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

export default new ApiService();
