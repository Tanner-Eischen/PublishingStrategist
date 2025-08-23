import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ErrorBoundary from '../common/ErrorBoundary';

// Create a component that throws an error
const ThrowError = ({ shouldThrow }) => {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>No error</div>;
};

// Suppress console errors for cleaner test output
const originalConsoleError = console.error;
beforeAll(() => {
  console.error = jest.fn();
});

afterAll(() => {
  console.error = originalConsoleError;
});

describe('ErrorBoundary Component', () => {
  test('renders children when no error occurs', () => {
    render(
      <ErrorBoundary>
        <div>Test Content</div>
      </ErrorBoundary>
    );
    
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  test('renders fallback UI when error occurs', () => {
    // Using jest.spyOn to mock the console.error
    const spy = jest.spyOn(console, 'error');
    spy.mockImplementation(() => {});
    
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );
    
    // Should show error message
    expect(screen.getByText(/Something went wrong/i)).toBeInTheDocument();
    expect(screen.getByText(/Test error/i)).toBeInTheDocument();
    
    // Should show retry button
    expect(screen.getByRole('button', { name: /Try again/i })).toBeInTheDocument();
    
    spy.mockRestore();
  });

  test('renders custom fallback when provided', () => {
    const CustomFallback = ({ error }) => (
      <div>
        <h2>Custom Error UI</h2>
        <p>{error.message}</p>
      </div>
    );
    
    render(
      <ErrorBoundary FallbackComponent={CustomFallback}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );
    
    // Should show custom error UI
    expect(screen.getByText('Custom Error UI')).toBeInTheDocument();
    expect(screen.getByText('Test error')).toBeInTheDocument();
  });

  test('calls onError when error occurs', () => {
    const handleError = jest.fn();
    
    render(
      <ErrorBoundary onError={handleError}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );
    
    // Should call onError handler
    expect(handleError).toHaveBeenCalledWith(expect.any(Error), expect.any(Object));
  });

  test('resets error state when key changes', () => {
    const { rerender } = render(
      <ErrorBoundary resetKeys={[1]}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );
    
    // Should show error UI
    expect(screen.getByText(/Something went wrong/i)).toBeInTheDocument();
    
    // Change resetKeys to trigger reset
    rerender(
      <ErrorBoundary resetKeys={[2]}>
        <ThrowError shouldThrow={false} />
      </ErrorBoundary>
    );
    
    // Should show normal content after reset
    expect(screen.getByText('No error')).toBeInTheDocument();
  });
});