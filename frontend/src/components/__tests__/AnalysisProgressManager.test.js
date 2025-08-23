import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import AnalysisProgressManager from '../common/AnalysisProgressManager';

// Mock the WebSocket hook
jest.mock('../../hooks/useWebSocket', () => ({
  useAnalysisProgress: () => ({
    activeAnalyses: [
      {
        id: 'test-analysis-1',
        type: 'niche_discovery',
        progress: 45,
        status: 'running',
        currentStep: 'Analyzing keywords',
        estimatedTime: 120,
        startTime: new Date().toISOString()
      },
      {
        id: 'test-analysis-2',
        type: 'trend_validation',
        progress: 80,
        status: 'running',
        currentStep: 'Calculating seasonality',
        estimatedTime: 30,
        startTime: new Date().toISOString()
      }
    ],
    progressHistory: [
      {
        id: 'completed-analysis-1',
        type: 'niche_discovery',
        progress: 100,
        status: 'completed',
        executionTime: 8.5,
        startTime: new Date(Date.now() - 3600000).toISOString(),
        results: { niches: [] }
      }
    ],
    cancelAnalysis: jest.fn(),
    pauseAnalysis: jest.fn(),
    resumeAnalysis: jest.fn()
  })
}));

describe('AnalysisProgressManager Component', () => {
  test('renders active analyses', () => {
    render(<AnalysisProgressManager />);
    
    // Should show active analyses
    expect(screen.getByText(/Analyzing keywords/i)).toBeInTheDocument();
    expect(screen.getByText(/Calculating seasonality/i)).toBeInTheDocument();
    
    // Should show progress indicators
    const progressBars = screen.getAllByRole('progressbar');
    expect(progressBars.length).toBe(2);
    
    // Should show analysis types
    expect(screen.getByText(/Niche Discovery/i)).toBeInTheDocument();
    expect(screen.getByText(/Trend Validation/i)).toBeInTheDocument();
  });

  test('renders progress history', () => {
    render(<AnalysisProgressManager showHistory={true} />);
    
    // Should show completed analysis in history
    expect(screen.getByText(/completed-analysis-1/i)).toBeInTheDocument();
    expect(screen.getByText(/Completed/i)).toBeInTheDocument();
    expect(screen.getByText(/8.5s/i)).toBeInTheDocument();
  });

  test('allows cancelling an analysis', () => {
    const { useAnalysisProgress } = require('../../hooks/useWebSocket');
    const cancelAnalysis = useAnalysisProgress().cancelAnalysis;
    
    render(<AnalysisProgressManager />);
    
    // Find and click cancel button
    const cancelButtons = screen.getAllByRole('button', { name: /cancel/i });
    fireEvent.click(cancelButtons[0]);
    
    // Should call cancelAnalysis
    expect(cancelAnalysis).toHaveBeenCalledWith('test-analysis-1');
  });

  test('allows pausing and resuming an analysis', () => {
    const { useAnalysisProgress } = require('../../hooks/useWebSocket');
    const pauseAnalysis = useAnalysisProgress().pauseAnalysis;
    const resumeAnalysis = useAnalysisProgress().resumeAnalysis;
    
    render(<AnalysisProgressManager />);
    
    // Find and click pause button
    const pauseButtons = screen.getAllByRole('button', { name: /pause/i });
    fireEvent.click(pauseButtons[0]);
    
    // Should call pauseAnalysis
    expect(pauseAnalysis).toHaveBeenCalledWith('test-analysis-1');
    
    // Mock paused state
    jest.spyOn(require('../../hooks/useWebSocket'), 'useAnalysisProgress').mockImplementation(() => ({
      activeAnalyses: [
        {
          id: 'test-analysis-1',
          type: 'niche_discovery',
          progress: 45,
          status: 'paused',
          currentStep: 'Analyzing keywords',
          estimatedTime: 120,
          startTime: new Date().toISOString(),
          pausedAt: new Date().toISOString()
        }
      ],
      progressHistory: [],
      cancelAnalysis: jest.fn(),
      pauseAnalysis: jest.fn(),
      resumeAnalysis: resumeAnalysis
    }));
    
    // Re-render with paused state
    render(<AnalysisProgressManager />);
    
    // Find and click resume button
    const resumeButton = screen.getByRole('button', { name: /resume/i });
    fireEvent.click(resumeButton);
    
    // Should call resumeAnalysis
    expect(resumeAnalysis).toHaveBeenCalledWith('test-analysis-1');
  });

  test('displays estimated time remaining', () => {
    render(<AnalysisProgressManager />);
    
    // Should show estimated time
    expect(screen.getByText(/2 minutes remaining/i)).toBeInTheDocument();
    expect(screen.getByText(/30 seconds remaining/i)).toBeInTheDocument();
  });

  test('handles empty state', () => {
    // Mock empty state
    jest.spyOn(require('../../hooks/useWebSocket'), 'useAnalysisProgress').mockImplementation(() => ({
      activeAnalyses: [],
      progressHistory: [],
      cancelAnalysis: jest.fn(),
      pauseAnalysis: jest.fn(),
      resumeAnalysis: jest.fn()
    }));
    
    render(<AnalysisProgressManager />);
    
    // Should show empty state message
    expect(screen.getByText(/No active analyses/i)).toBeInTheDocument();
  });

  test('displays error state', () => {
    // Mock error state
    jest.spyOn(require('../../hooks/useWebSocket'), 'useAnalysisProgress').mockImplementation(() => ({
      activeAnalyses: [
        {
          id: 'error-analysis',
          type: 'niche_discovery',
          progress: 30,
          status: 'error',
          currentStep: 'Analyzing keywords',
          error: 'API rate limit exceeded',
          startTime: new Date().toISOString()
        }
      ],
      progressHistory: [],
      cancelAnalysis: jest.fn()
    }));
    
    render(<AnalysisProgressManager />);
    
    // Should show error message
    expect(screen.getByText(/Error/i)).toBeInTheDocument();
    expect(screen.getByText(/API rate limit exceeded/i)).toBeInTheDocument();
  });
});