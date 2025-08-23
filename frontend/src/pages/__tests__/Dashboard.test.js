import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import Dashboard from '../Dashboard';

// Mock the API service
jest.mock('../../services/api', () => ({
  healthCheck: jest.fn().mockResolvedValue({ status: 'ok' }),
  getUserPreferences: jest.fn().mockResolvedValue({
    theme: 'light',
    recent_searches: ['productivity', 'journal'],
    favorite_niches: [
      {
        name: 'Productivity Journal',
        score: 78.5
      }
    ]
  })
}));

// Mock the WebSocket hook
jest.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    isConnected: true,
    connectionError: null
  }),
  useAnalysisProgress: () => ({
    activeAnalyses: [],
    progressHistory: [
      {
        id: 'recent-analysis',
        type: 'niche_discovery',
        progress: 100,
        status: 'completed',
        executionTime: 8.5,
        results: {
          niches: [
            {
              name: 'Productivity Journal',
              score: 78.5,
              competition_level: 'medium'
            }
          ]
        }
      }
    ]
  })
}));

// Mock React Router
jest.mock('react-router-dom', () => ({
  useNavigate: () => jest.fn(),
  Link: ({ children, to }) => <a href={to}>{children}</a>
}));

// Mock Chart.js
jest.mock('react-chartjs-2', () => ({
  Line: () => <div data-testid="line-chart">Line Chart</div>,
  Bar: () => <div data-testid="bar-chart">Bar Chart</div>,
  Doughnut: () => <div data-testid="doughnut-chart">Doughnut Chart</div>
}));

describe('Dashboard Page', () => {
  test('renders dashboard components', async () => {
    render(<Dashboard />);
    
    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText(/Dashboard/i)).toBeInTheDocument();
    });
    
    // Should show welcome message
    expect(screen.getByText(/Welcome to KDP Strategist/i)).toBeInTheDocument();
    
    // Should show quick stats
    expect(screen.getByText(/Quick Stats/i)).toBeInTheDocument();
    
    // Should show recent searches
    expect(screen.getByText(/Recent Searches/i)).toBeInTheDocument();
    expect(screen.getByText(/productivity/i)).toBeInTheDocument();
    expect(screen.getByText(/journal/i)).toBeInTheDocument();
    
    // Should show favorite niches
    expect(screen.getByText(/Favorite Niches/i)).toBeInTheDocument();
    expect(screen.getByText(/Productivity Journal/i)).toBeInTheDocument();
    
    // Should show charts
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });

  test('handles quick action buttons', async () => {
    const { useNavigate } = require('react-router-dom');
    const navigate = useNavigate();
    
    render(<Dashboard />);
    
    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText(/Dashboard/i)).toBeInTheDocument();
    });
    
    // Find and click quick action buttons
    const discoverButton = screen.getByRole('button', { name: /Discover Niches/i });
    fireEvent.click(discoverButton);
    
    // Should navigate to niche discovery page
    expect(navigate).toHaveBeenCalledWith('/niche-discovery');
    
    // Find and click another action button
    const trendsButton = screen.getByRole('button', { name: /Validate Trends/i });
    fireEvent.click(trendsButton);
    
    // Should navigate to trend validation page
    expect(navigate).toHaveBeenCalledWith('/trend-validation');
  });

  test('displays recent analysis results', async () => {
    render(<Dashboard />);
    
    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText(/Dashboard/i)).toBeInTheDocument();
    });
    
    // Should show recent analysis section
    expect(screen.getByText(/Recent Analysis/i)).toBeInTheDocument();
    
    // Should show recent analysis results
    expect(screen.getByText(/Productivity Journal/i)).toBeInTheDocument();
    expect(screen.getByText(/78.5/i)).toBeInTheDocument();
    expect(screen.getByText(/medium/i)).toBeInTheDocument();
  });

  test('handles empty state', async () => {
    // Mock empty state
    jest.spyOn(require('../../hooks/useWebSocket'), 'useAnalysisProgress').mockImplementation(() => ({
      activeAnalyses: [],
      progressHistory: []
    }));
    
    jest.spyOn(require('../../services/api'), 'getUserPreferences').mockResolvedValue({
      theme: 'light',
      recent_searches: [],
      favorite_niches: []
    });
    
    render(<Dashboard />);
    
    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText(/Dashboard/i)).toBeInTheDocument();
    });
    
    // Should show empty state messages
    expect(screen.getByText(/No recent searches/i)).toBeInTheDocument();
    expect(screen.getByText(/No favorite niches/i)).toBeInTheDocument();
    expect(screen.getByText(/No recent analysis/i)).toBeInTheDocument();
  });

  test('handles error state', async () => {
    // Mock API error
    jest.spyOn(require('../../services/api'), 'getUserPreferences').mockRejectedValue(
      new Error('Failed to load preferences')
    );
    
    render(<Dashboard />);
    
    // Wait for error state
    await waitFor(() => {
      expect(screen.getByText(/Error loading preferences/i)).toBeInTheDocument();
    });
    
    // Should show retry button
    const retryButton = screen.getByRole('button', { name: /Retry/i });
    expect(retryButton).toBeInTheDocument();
    
    // Click retry button
    fireEvent.click(retryButton);
    
    // Should attempt to load data again
    expect(require('../../services/api').getUserPreferences).toHaveBeenCalledTimes(2);
  });

  test('displays system status', async () => {
    render(<Dashboard />);
    
    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText(/Dashboard/i)).toBeInTheDocument();
    });
    
    // Should show system status
    expect(screen.getByText(/System Status/i)).toBeInTheDocument();
    expect(screen.getByText(/Connected/i)).toBeInTheDocument();
  });
});