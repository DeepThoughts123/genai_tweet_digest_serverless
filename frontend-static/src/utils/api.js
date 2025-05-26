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
        throw new Error(data.message || 'Subscription failed');
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
