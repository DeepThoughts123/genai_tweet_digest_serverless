// Jest environment setup for API testing
// This file sets up the environment variables and globals needed for testing

// Mock the CONFIG object that would normally be loaded from config.js
global.window = global.window || {};
global.window.CONFIG = {
  API_BASE_URL: 'https://dzin6h5zvf.execute-api.us-east-1.amazonaws.com/production'
};

// Set up environment variables for testing
process.env.NEXT_PUBLIC_API_BASE_URL = 'https://dzin6h5zvf.execute-api.us-east-1.amazonaws.com/production';

// Mock console methods to reduce noise in tests (optional)
global.console = {
  ...console,
  log: jest.fn(),
  error: console.error, // Keep error logs for debugging
  warn: console.warn,
  info: jest.fn(),
}; 