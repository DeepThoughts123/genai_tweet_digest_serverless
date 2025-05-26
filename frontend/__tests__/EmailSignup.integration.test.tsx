import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EmailSignup from '@/components/EmailSignup';

// Mock fetch for API calls
global.fetch = jest.fn();

describe('EmailSignup Backend Integration', () => {
  beforeEach(() => {
    (fetch as jest.Mock).mockClear();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  it('should successfully submit email to backend API', async () => {
    const user = userEvent.setup();
    
    // Mock successful API response
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => ({
        message: 'Successfully subscribed to weekly digest',
        email: 'test@example.com',
        subscription_id: 'sub_123',
        subscribed_at: '2024-01-01T00:00:00Z'
      })
    });

    render(<EmailSignup />);
    
    const emailInput = screen.getByPlaceholderText('Enter your email address');
    const submitButton = screen.getByRole('button', { name: /get weekly digest/i });
    
    // Enter email and submit
    await user.type(emailInput, 'test@example.com');
    await user.click(submitButton);
    
    // Verify API call was made
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/v1/subscription', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: 'test@example.com' })
      });
    });
    
    // Verify success message is displayed
    await waitFor(() => {
      expect(screen.getByText(/thank you! you'll receive our weekly digest soon/i)).toBeInTheDocument();
    });
    
    // Verify email input is cleared
    expect(emailInput).toHaveValue('');
  });

  it('should handle client-side validation errors', async () => {
    render(<EmailSignup />);
    
    const emailInput = screen.getByPlaceholderText('Enter your email address');
    const form = emailInput.closest('form');
    
    // Enter invalid email
    fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
    expect(emailInput).toHaveValue('invalid-email');
    
    // Submit form directly
    fireEvent.submit(form!);
    
    // Verify client-side validation error message is displayed
    await waitFor(() => {
      expect(screen.getByText(/please enter a valid email address/i)).toBeInTheDocument();
    });
    
    // Verify fetch was not called due to client-side validation
    expect(fetch).not.toHaveBeenCalled();
  });

  it('should handle API validation errors (422)', async () => {
    const user = userEvent.setup();
    
    // Mock validation error response for edge case that passes client validation but fails server validation
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({
        detail: [
          {
            loc: ['body', 'email'],
            msg: 'field required',
            type: 'value_error.missing'
          }
        ]
      })
    });

    render(<EmailSignup />);
    
    const emailInput = screen.getByPlaceholderText('Enter your email address');
    const submitButton = screen.getByRole('button', { name: /get weekly digest/i });
    
    // Enter email that passes client validation but might fail server validation
    await user.type(emailInput, 'test@example.com');
    await user.click(submitButton);
    
    // Verify server validation error message is displayed
    await waitFor(() => {
      expect(screen.getByText(/please enter a valid email address/i)).toBeInTheDocument();
    });
  });

  it('should handle duplicate email error (409)', async () => {
    const user = userEvent.setup();
    
    // Mock conflict error response
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 409,
      json: async () => ({
        error: 'Email already subscribed to weekly digest',
        detail: 'This email address is already in our subscription list'
      })
    });

    render(<EmailSignup />);
    
    const emailInput = screen.getByPlaceholderText('Enter your email address');
    const submitButton = screen.getByRole('button', { name: /get weekly digest/i });
    
    // Enter email and submit
    await user.type(emailInput, 'existing@example.com');
    await user.click(submitButton);
    
    // Verify error message is displayed
    await waitFor(() => {
      expect(screen.getByText(/email already subscribed to weekly digest/i)).toBeInTheDocument();
    });
  });

  it('should handle network errors', async () => {
    const user = userEvent.setup();
    
    // Mock network error
    (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

    render(<EmailSignup />);
    
    const emailInput = screen.getByPlaceholderText('Enter your email address');
    const submitButton = screen.getByRole('button', { name: /get weekly digest/i });
    
    // Enter email and submit
    await user.type(emailInput, 'test@example.com');
    await user.click(submitButton);
    
    // Verify error message is displayed
    await waitFor(() => {
      expect(screen.getByText(/something went wrong. please try again/i)).toBeInTheDocument();
    });
  });

  it('should handle server errors (500)', async () => {
    const user = userEvent.setup();
    
    // Mock server error response
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({
        error: 'Internal server error',
        detail: 'An unexpected error occurred'
      })
    });

    render(<EmailSignup />);
    
    const emailInput = screen.getByPlaceholderText('Enter your email address');
    const submitButton = screen.getByRole('button', { name: /get weekly digest/i });
    
    // Enter email and submit
    await user.type(emailInput, 'test@example.com');
    await user.click(submitButton);
    
    // Verify error message is displayed
    await waitFor(() => {
      expect(screen.getByText(/something went wrong. please try again/i)).toBeInTheDocument();
    });
  });

  it('should show loading state during API call', async () => {
    const user = userEvent.setup();
    
    // Mock delayed API response
    (fetch as jest.Mock).mockImplementationOnce(() => 
      new Promise(resolve => 
        setTimeout(() => resolve({
          ok: true,
          status: 201,
          json: async () => ({
            message: 'Successfully subscribed to weekly digest',
            email: 'test@example.com',
            subscription_id: 'sub_123',
            subscribed_at: '2024-01-01T00:00:00Z'
          })
        }), 100)
      )
    );

    render(<EmailSignup />);
    
    const emailInput = screen.getByPlaceholderText('Enter your email address');
    const submitButton = screen.getByRole('button', { name: /get weekly digest/i });
    
    // Enter email and submit
    await user.type(emailInput, 'test@example.com');
    await user.click(submitButton);
    
    // Verify loading state is shown
    expect(screen.getByText(/subscribing.../i)).toBeInTheDocument();
    expect(submitButton).toBeDisabled();
    expect(emailInput).toBeDisabled();
    
    // Wait for completion
    await waitFor(() => {
      expect(screen.getByText(/thank you! you'll receive our weekly digest soon/i)).toBeInTheDocument();
    });
  });

  it('should use correct API endpoint URL', async () => {
    const user = userEvent.setup();
    
    // Mock successful API response
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => ({
        message: 'Successfully subscribed to weekly digest',
        email: 'test@example.com',
        subscription_id: 'sub_123',
        subscribed_at: '2024-01-01T00:00:00Z'
      })
    });

    render(<EmailSignup />);
    
    const emailInput = screen.getByPlaceholderText('Enter your email address');
    const submitButton = screen.getByRole('button', { name: /get weekly digest/i });
    
    // Enter email and submit
    await user.type(emailInput, 'test@example.com');
    await user.click(submitButton);
    
    // Verify correct endpoint is called
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/v1/subscription', expect.any(Object));
    });
  });

  it('should handle custom onSubscribe callback', async () => {
    const user = userEvent.setup();
    const mockOnSubscribe = jest.fn().mockResolvedValue(undefined);
    
    render(<EmailSignup onSubscribe={mockOnSubscribe} />);
    
    const emailInput = screen.getByPlaceholderText('Enter your email address');
    const submitButton = screen.getByRole('button', { name: /get weekly digest/i });
    
    // Enter email and submit
    await user.type(emailInput, 'test@example.com');
    await user.click(submitButton);
    
    // Verify custom callback is called instead of API
    await waitFor(() => {
      expect(mockOnSubscribe).toHaveBeenCalledWith('test@example.com');
    });
    
    // Verify fetch is not called when custom callback is provided
    expect(fetch).not.toHaveBeenCalled();
  });

  it('should trim whitespace from email before sending to API', async () => {
    const user = userEvent.setup();
    
    // Mock successful API response
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => ({
        message: 'Successfully subscribed to weekly digest',
        email: 'test@example.com',
        subscription_id: 'sub_123',
        subscribed_at: '2024-01-01T00:00:00Z'
      })
    });

    render(<EmailSignup />);
    
    const emailInput = screen.getByPlaceholderText('Enter your email address');
    const submitButton = screen.getByRole('button', { name: /get weekly digest/i });
    
    // Enter email with whitespace and submit
    await user.type(emailInput, '  test@example.com  ');
    await user.click(submitButton);
    
    // Verify API call was made with trimmed email
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/v1/subscription', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: 'test@example.com' })
      });
    });
  });
}); 