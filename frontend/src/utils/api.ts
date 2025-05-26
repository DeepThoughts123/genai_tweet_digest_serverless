// Placeholder ApiService for development
// This file will be replaced by setup-frontend.sh with the actual implementation

interface ApiResponse {
  success: boolean;
  message?: string;
  subscriber_id?: string;
  subscriber_count?: number;
}

class ApiService {
  private baseUrl: string;

  constructor() {
    // Fallback URL for development
    this.baseUrl = process.env.NEXT_PUBLIC_API_URL || '/api/v1';
  }

  async subscribe(email: string): Promise<ApiResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/subscription`, {
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
        
        // Add status code context for specific error handling
        if (response.status === 422) {
          errorMessage = 'Validation error: ' + errorMessage;
        } else if (response.status === 409) {
          errorMessage = data.error || 'Email already subscribed to weekly digest';
        }
        
        const error = new Error(errorMessage) as Error & { status: number };
        error.status = response.status;
        throw error;
      }

      return data;
    } catch (error) {
      console.error('Subscription error:', error);
      throw error;
    }
  }

  async getSubscriberCount(): Promise<ApiResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/subscriber-count`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        return { success: true, subscriber_count: 0 };
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching subscriber count:', error);
      return { success: true, subscriber_count: 0 };
    }
  }
}

const apiService = new ApiService();
export default apiService; 