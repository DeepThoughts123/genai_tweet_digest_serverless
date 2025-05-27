import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EmailSignup from '@/components/EmailSignup';

describe('EmailSignup Component', () => {
  const mockOnSubscribe = jest.fn();

  beforeEach(() => {
    mockOnSubscribe.mockClear();
  });

  describe('Rendering', () => {
    it('renders email input field', () => {
      render(<EmailSignup />);
      expect(screen.getByPlaceholderText(/enter your email address/i)).toBeInTheDocument();
    });

    it('renders submit button with correct text', () => {
      render(<EmailSignup />);
      expect(screen.getByRole('button', { name: /get weekly digest/i })).toBeInTheDocument();
    });

    it('renders privacy notice', () => {
      render(<EmailSignup />);
      expect(screen.getByText(/no spam, unsubscribe at any time/i)).toBeInTheDocument();
    });

    it('has proper accessibility labels', () => {
      render(<EmailSignup />);
      const emailInput = screen.getByLabelText(/email address/i);
      expect(emailInput).toBeInTheDocument();
      expect(emailInput).toHaveAttribute('type', 'email');
    });
  });

  describe('Form Validation', () => {
    it('shows error for empty email', async () => {
      const user = userEvent.setup();
      render(<EmailSignup onSubscribe={mockOnSubscribe} />);
      
      const submitButton = screen.getByRole('button', { name: /get weekly digest/i });
      await user.click(submitButton);
      
      expect(screen.getByText(/please enter a valid email address/i)).toBeInTheDocument();
      expect(mockOnSubscribe).not.toHaveBeenCalled();
    });

    it('shows error for invalid email format', async () => {
      const user = userEvent.setup();
      render(<EmailSignup onSubscribe={mockOnSubscribe} />);
      
      const emailInput = screen.getByPlaceholderText(/enter your email address/i);
      const submitButton = screen.getByRole('button', { name: /get weekly digest/i });
      
      await user.type(emailInput, 'invalid@email');
      await user.click(submitButton);
      
      expect(screen.getByText(/please enter a valid email address/i)).toBeInTheDocument();
      expect(mockOnSubscribe).not.toHaveBeenCalled();
    });

    it('accepts valid email format', async () => {
      const user = userEvent.setup();
      render(<EmailSignup onSubscribe={mockOnSubscribe} />);
      
      const emailInput = screen.getByPlaceholderText(/enter your email address/i);
      const submitButton = screen.getByRole('button', { name: /get weekly digest/i });
      
      await user.type(emailInput, 'test@example.com');
      await user.click(submitButton);
      
      expect(mockOnSubscribe).toHaveBeenCalledWith('test@example.com');
    });
  });

  describe('Form Submission', () => {
    it('calls onSubscribe with email when form is submitted', async () => {
      const user = userEvent.setup();
      render(<EmailSignup onSubscribe={mockOnSubscribe} />);
      
      const emailInput = screen.getByPlaceholderText(/enter your email address/i);
      const submitButton = screen.getByRole('button', { name: /get weekly digest/i });
      
      await user.type(emailInput, 'user@example.com');
      await user.click(submitButton);
      
      expect(mockOnSubscribe).toHaveBeenCalledWith('user@example.com');
    });

    it('shows loading state during submission', async () => {
      const user = userEvent.setup();
      const slowOnSubscribe = jest.fn(() => new Promise(resolve => setTimeout(resolve, 100)));
      
      render(<EmailSignup onSubscribe={slowOnSubscribe} />);
      
      const emailInput = screen.getByPlaceholderText(/enter your email address/i);
      const submitButton = screen.getByRole('button', { name: /get weekly digest/i });
      
      await user.type(emailInput, 'user@example.com');
      await user.click(submitButton);
      
      expect(screen.getByText(/subscribing.../i)).toBeInTheDocument();
      expect(submitButton).toBeDisabled();
      expect(emailInput).toBeDisabled();
    });

    it('shows success message after successful submission', async () => {
      const user = userEvent.setup();
      const successfulOnSubscribe = jest.fn(() => Promise.resolve());
      render(<EmailSignup onSubscribe={successfulOnSubscribe} />);
      
      const emailInput = screen.getByPlaceholderText(/enter your email address/i);
      const submitButton = screen.getByRole('button', { name: /get weekly digest/i });
      
      await user.type(emailInput, 'user@example.com');
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/thank you! you'll receive our weekly digest soon/i)).toBeInTheDocument();
      });
    });

    it('clears email field after successful submission', async () => {
      const user = userEvent.setup();
      const successfulOnSubscribe = jest.fn(() => Promise.resolve());
      render(<EmailSignup onSubscribe={successfulOnSubscribe} />);
      
      const emailInput = screen.getByPlaceholderText(/enter your email address/i) as HTMLInputElement;
      const submitButton = screen.getByRole('button', { name: /get weekly digest/i });
      
      await user.type(emailInput, 'user@example.com');
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(emailInput.value).toBe('');
      });
    });

    it('shows error message when submission fails', async () => {
      const user = userEvent.setup();
      const failingOnSubscribe = jest.fn(() => Promise.reject(new Error('Network error')));
      
      render(<EmailSignup onSubscribe={failingOnSubscribe} />);
      
      const emailInput = screen.getByPlaceholderText(/enter your email address/i);
      const submitButton = screen.getByRole('button', { name: /get weekly digest/i });
      
      await user.type(emailInput, 'user@example.com');
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/network error/i)).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('supports keyboard navigation', async () => {
      const user = userEvent.setup();
      render(<EmailSignup onSubscribe={mockOnSubscribe} />);
      
      const emailInput = screen.getByPlaceholderText(/enter your email address/i);
      const submitButton = screen.getByRole('button', { name: /get weekly digest/i });
      
      // Tab to email input
      await user.tab();
      expect(emailInput).toHaveFocus();
      
      // Type email
      await user.type(emailInput, 'user@example.com');
      
      // Tab to submit button
      await user.tab();
      expect(submitButton).toHaveFocus();
      
      // Submit with Enter
      await user.keyboard('{Enter}');
      
      expect(mockOnSubscribe).toHaveBeenCalledWith('user@example.com');
    });

    it('has proper ARIA attributes', () => {
      render(<EmailSignup />);
      
      const emailInput = screen.getByPlaceholderText(/enter your email address/i);
      expect(emailInput).toHaveAttribute('type', 'email');
      expect(emailInput).toHaveAttribute('id', 'email');
    });
  });
}); 