'use client';

import { useState } from 'react';
import ApiService from '../utils/api';

interface EmailSignupProps {
  onSubscribe?: (email: string) => void;
}

export default function EmailSignup({ onSubscribe }: EmailSignupProps) {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email.trim() || !emailRegex.test(email.trim())) {
      setMessage('Please enter a valid email address');
      return;
    }

    setIsLoading(true);
    setMessage('');

    try {
      if (onSubscribe) {
        // Use custom callback if provided (for testing or custom handling)
        await onSubscribe(email.trim());
        setMessage('Thank you! You\'ll receive our weekly digest soon.');
        setEmail('');
      } else {
        // Default behavior: use ApiService for serverless backend
        await ApiService.subscribe(email.trim());
        
        // ApiService.subscribe returns the response data on success
        setMessage('Thank you! You\'ll receive our weekly digest soon.');
        setEmail('');
      }
    } catch (error) {
      console.error('Subscription error:', error);
      
      // Handle specific error messages from ApiService
      if (error instanceof Error) {
        const errorMessage = error.message;
        const status = (error as any).status;
        
        // Handle errors based on status code and message content
        if (status === 409 || errorMessage.includes('already subscribed') || errorMessage.includes('Email already subscribed')) {
          setMessage('Email already subscribed to weekly digest');
        } else if (status === 422 || errorMessage.includes('Validation error') || errorMessage.includes('field required')) {
          setMessage('Please enter a valid email address');
        } else {
          setMessage('Something went wrong. Please try again.');
        }
      } else {
        setMessage('Something went wrong. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-md">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4 sm:flex-row">
        <div className="flex-1">
          <label htmlFor="email" className="sr-only">
            Email address
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email address"
            className="w-full rounded-lg border border-gray-300 px-4 py-3 text-gray-900 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            disabled={isLoading}
            required={false}
          />
        </div>
        <button
          type="submit"
          disabled={isLoading}
          className="rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-3 font-semibold text-white shadow-lg transition-all duration-200 hover:from-blue-700 hover:to-purple-700 hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <span className="flex items-center">
              <svg className="mr-2 h-4 w-4 animate-spin" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Subscribing...
            </span>
          ) : (
            'Get Weekly Digest'
          )}
        </button>
      </form>
      
      {message && (
        <p className={`mt-3 text-sm ${
          message.includes('Thank you') 
            ? 'text-green-600' 
            : 'text-red-600'
        }`}>
          {message}
        </p>
      )}
      
      <p className="mt-3 text-xs text-gray-500">
        No spam, unsubscribe at any time. We respect your privacy.
      </p>
    </div>
  );
} 