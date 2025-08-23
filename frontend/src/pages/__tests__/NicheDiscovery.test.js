import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import NicheDiscovery from '../NicheDiscovery';
import * as apiService from '../../services/api';

// Mock the API service
jest.mock('../../services/api', () => ({
  discoverNiches: jest.fn(),
  startAnalysisWithProgress: jest.fn()
}));

// Mock the WebSocket hook
jest.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    isConnected: true,
    connectionError: null,
    reconnectAttempts: 0
  }),
  useAnalysisProgress: () => ({
    startAnalysis: jest.fn(),
    activeAnalyses: [],
    progressHistory: []
  })
}));

// Mock React Router
jest.mock('react-router-dom', () => ({
  useNavigate: () => jest.fn(),
  Link: ({ children, to }) => <a href={to}>{children}</a>
}));

describe('NicheDiscovery Page', () => {
  const mockNicheResponse = {
    niches: [
      {
        name: 'Productivity Journal',
        primary_keyword: 'productivity journal',
        category: 'Self-Help',
        score: 78.5,
        competition_level: 'medium',
        profitability_tier: 'high',
        confidence_score: 0.82,
        keywords: ['productivity', 'journal', 'daily']
      },
      {
        name: 'Time Management Workbook',
        primary_keyword: 'time management',
        category: 'Self-Help',
        score: 72.3,
        competition_level: 'medium',
        profitability_tier: 'medium',
        confidence_score: 0.75
      }
    ],
    total_analyzed: 10,
    execution_time: 5.2
  };

  beforeEach(() => {
    jest.clearAllMocks();
    apiService.discoverNiches.mockResolvedValue(mockNicheResponse);
    apiService.startAnalysisWithProgress.mockImplementation((type, params, onProgress, onComplete) => {
      // Simulate completion after a short delay
      setTimeout(() => {
        if (onComplete) onComplete({ results: mockNicheResponse });
      }, 100);
      return { analysisId: 'test-analysis-id', status: 'started' };
    });
  });

  test('renders the niche discovery form', () => {
    render(<NicheDiscovery />);
    
    expect(screen.getByText(/Discover Profitable Niches/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Keywords/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Discover Niches/i })).toBeInTheDocument();
  });

  test('submits the form and displays results', async () => {
    render(<NicheDiscovery />);
    
    // Fill out the form
    const keywordsInput = screen.getByLabelText(/Keywords/i);
    fireEvent.change(keywordsInput, { target: { value: 'productivity, time management' } });
    
    // Submit the form
    const submitButton = screen.getByRole('button', { name: /Discover Niches/i });
    fireEvent.click(submitButton);
    
    // Check loading state
    expect(screen.getByText(/Analyzing/i)).toBeInTheDocument();
    
    // Wait for results
    await waitFor(() => {
      expect(screen.getByText(/Productivity Journal/i)).toBeInTheDocument();
    });
    
    expect(screen.getByText(/Time Management Workbook/i)).toBeInTheDocument();
    
    // Verify API was called correctly
    expect(apiService.startAnalysisWithProgress).toHaveBeenCalledWith(
      'niche_discovery',
      expect.objectContaining({
        base_keywords: ['productivity', 'time management']
      }),
      expect.any(Function),
      expect.any(Function)
    );
  });

  test('displays error message when API fails', async () => {
    // Mock API failure
    apiService.startAnalysisWithProgress.mockImplementation((type, params, onProgress, onError) => {
      setTimeout(() => {
        if (onError) onError({ error: 'API rate limit exceeded' });
      }, 100);
      return { analysisId: 'test-analysis-id', status: 'started' };
    });
    
    render(<NicheDiscovery />);
    
    // Fill out the form
    const keywordsInput = screen.getByLabelText(/Keywords/i);
    fireEvent.change(keywordsInput, { target: { value: 'productivity' } });
    
    // Submit the form
    const submitButton = screen.getByRole('button', { name: /Discover Niches/i });
    fireEvent.click(submitButton);
    
    // Wait for error message
    await waitFor(() => {
      expect(screen.getByText(/API rate limit exceeded/i)).toBeInTheDocument();
    });
  });

  test('filters and sorts niche results', async () => {
    render(<NicheDiscovery />);
    
    // Fill out the form and submit
    const keywordsInput = screen.getByLabelText(/Keywords/i);
    fireEvent.change(keywordsInput, { target: { value: 'productivity' } });
    
    const submitButton = screen.getByRole('button', { name: /Discover Niches/i });
    fireEvent.click(submitButton);
    
    // Wait for results
    await waitFor(() => {
      expect(screen.getByText(/Productivity Journal/i)).toBeInTheDocument();
    });
    
    // Test sorting (if sorting controls are available)
    const sortSelect = screen.getByLabelText(/Sort by/i);
    fireEvent.change(sortSelect, { target: { value: 'score' } });
    
    // Test filtering (if filtering controls are available)
    const filterSelect = screen.getByLabelText(/Competition Level/i);
    fireEvent.change(filterSelect, { target: { value: 'medium' } });
    
    // Verify filtered results are displayed correctly
    expect(screen.getByText(/Productivity Journal/i)).toBeInTheDocument();
    expect(screen.getByText(/Time Management Workbook/i)).toBeInTheDocument();
  });
});