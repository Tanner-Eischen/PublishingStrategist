import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ProgressIndicator from '../common/ProgressIndicator';

describe('ProgressIndicator Component', () => {
  test('renders with default props', () => {
    render(<ProgressIndicator />);
    
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toBeInTheDocument();
    expect(progressBar).toHaveAttribute('aria-valuenow', '0');
  });

  test('renders with custom progress value', () => {
    render(<ProgressIndicator progress={75} />);
    
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveAttribute('aria-valuenow', '75');
  });

  test('renders with custom label', () => {
    render(<ProgressIndicator progress={50} label="Processing..." />);
    
    expect(screen.getByText('Processing...')).toBeInTheDocument();
  });

  test('renders with step information', () => {
    render(
      <ProgressIndicator 
        progress={60} 
        currentStep={2} 
        totalSteps={5} 
        stepName="Analyzing competitors" 
      />
    );
    
    expect(screen.getByText(/Step 2 of 5/i)).toBeInTheDocument();
    expect(screen.getByText(/Analyzing competitors/i)).toBeInTheDocument();
  });

  test('renders with estimated time remaining', () => {
    render(
      <ProgressIndicator 
        progress={30} 
        estimatedTimeRemaining={120} 
      />
    );
    
    expect(screen.getByText(/2 minutes remaining/i)).toBeInTheDocument();
  });

  test('renders completed state', () => {
    render(<ProgressIndicator progress={100} isComplete={true} />);
    
    expect(screen.getByText(/Complete/i)).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveClass('complete');
  });

  test('renders error state', () => {
    render(
      <ProgressIndicator 
        progress={45} 
        hasError={true} 
        errorMessage="API rate limit exceeded" 
      />
    );
    
    expect(screen.getByText(/Error/i)).toBeInTheDocument();
    expect(screen.getByText(/API rate limit exceeded/i)).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveClass('error');
  });

  test('renders with custom size', () => {
    render(<ProgressIndicator progress={50} size="large" />);
    
    expect(screen.getByRole('progressbar')).toHaveClass('large');
  });

  test('renders with custom theme', () => {
    render(<ProgressIndicator progress={50} theme="secondary" />);
    
    expect(screen.getByRole('progressbar')).toHaveClass('secondary');
  });
});