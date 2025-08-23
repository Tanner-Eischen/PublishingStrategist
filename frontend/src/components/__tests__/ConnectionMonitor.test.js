import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ConnectionMonitor from '../common/ConnectionMonitor';

// Mock the WebSocket hook
jest.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    isConnected: true,
    connectionError: null,
    reconnectAttempts: 0,
    connect: jest.fn(),
    disconnect: jest.fn()
  })
}));

describe('ConnectionMonitor Component', () => {
  test('renders connected state correctly', () => {
    render(<ConnectionMonitor />);
    
    expect(screen.getByText(/Connected/i)).toBeInTheDocument();
    expect(screen.getByTestId('connection-status')).toHaveClass('connected');
  });

  test('renders disconnected state correctly', () => {
    // Override the mock for this test
    jest.spyOn(require('../../hooks/useWebSocket'), 'useWebSocket').mockImplementation(() => ({
      isConnected: false,
      connectionError: null,
      reconnectAttempts: 0,
      connect: jest.fn(),
      disconnect: jest.fn()
    }));

    render(<ConnectionMonitor />);
    
    expect(screen.getByText(/Disconnected/i)).toBeInTheDocument();
    expect(screen.getByTestId('connection-status')).toHaveClass('disconnected');
  });

  test('renders error state correctly', () => {
    // Override the mock for this test
    jest.spyOn(require('../../hooks/useWebSocket'), 'useWebSocket').mockImplementation(() => ({
      isConnected: false,
      connectionError: 'Connection failed',
      reconnectAttempts: 2,
      connect: jest.fn(),
      disconnect: jest.fn()
    }));

    render(<ConnectionMonitor />);
    
    expect(screen.getByText(/Error/i)).toBeInTheDocument();
    expect(screen.getByText(/Connection failed/i)).toBeInTheDocument();
    expect(screen.getByText(/Reconnect attempts: 2/i)).toBeInTheDocument();
    expect(screen.getByTestId('connection-status')).toHaveClass('error');
  });

  test('reconnect button calls connect function', () => {
    const connectMock = jest.fn();
    
    // Override the mock for this test
    jest.spyOn(require('../../hooks/useWebSocket'), 'useWebSocket').mockImplementation(() => ({
      isConnected: false,
      connectionError: 'Connection failed',
      reconnectAttempts: 3,
      connect: connectMock,
      disconnect: jest.fn()
    }));

    render(<ConnectionMonitor />);
    
    const reconnectButton = screen.getByText(/Reconnect/i);
    reconnectButton.click();
    
    expect(connectMock).toHaveBeenCalledTimes(1);
  });
});