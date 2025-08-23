import { renderHook, act } from '@testing-library/react-hooks';
import { useWebSocket, useAnalysisProgress } from '../useWebSocket';

// Mock WebSocket
class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = 0; // CONNECTING
    this.CONNECTING = 0;
    this.OPEN = 1;
    this.CLOSING = 2;
    this.CLOSED = 3;
    
    // Simulate connection after a short delay
    setTimeout(() => {
      this.readyState = 1; // OPEN
      if (this.onopen) this.onopen();
    }, 50);
  }
  
  send(data) {
    if (this.readyState === this.OPEN) {
      return true;
    }
    return false;
  }
  
  close() {
    this.readyState = 3; // CLOSED
    if (this.onclose) this.onclose({ code: 1000, reason: 'Normal closure' });
  }
}

// Mock localStorage and sessionStorage
const mockStorage = {};
Object.defineProperty(window, 'localStorage', {
  value: {
    getItem: jest.fn(key => mockStorage[key] || null),
    setItem: jest.fn((key, value) => { mockStorage[key] = value; }),
    removeItem: jest.fn(key => { delete mockStorage[key]; }),
    clear: jest.fn(() => { Object.keys(mockStorage).forEach(key => delete mockStorage[key]); })
  },
  writable: true
});

Object.defineProperty(window, 'sessionStorage', {
  value: {
    getItem: jest.fn(key => mockStorage[key] || null),
    setItem: jest.fn((key, value) => { mockStorage[key] = value; }),
    removeItem: jest.fn(key => { delete mockStorage[key]; }),
    clear: jest.fn(() => { Object.keys(mockStorage).forEach(key => delete mockStorage[key]); })
  },
  writable: true
});

// Mock fetch
global.fetch = jest.fn(() => 
  Promise.resolve({
    json: () => Promise.resolve({ success: true })
  })
);

describe('useWebSocket Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.WebSocket = MockWebSocket;
    jest.useFakeTimers();
  });
  
  afterEach(() => {
    jest.useRealTimers();
  });
  
  test('establishes WebSocket connection on mount', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws'));
    
    // Initially not connected
    expect(result.current.isConnected).toBe(false);
    
    // Advance timers to trigger connection
    act(() => {
      jest.advanceTimersByTime(100);
    });
    
    // Should be connected now
    expect(result.current.isConnected).toBe(true);
  });
  
  test('sends messages when connected', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws'));
    
    // Connect WebSocket
    act(() => {
      jest.advanceTimersByTime(100);
    });
    
    // Send a message
    let sendResult;
    act(() => {
      sendResult = result.current.sendMessage({ type: 'test', data: 'test-data' });
    });
    
    expect(sendResult).toBe(true);
  });
  
  test('handles disconnection', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws'));
    
    // Connect WebSocket
    act(() => {
      jest.advanceTimersByTime(100);
    });
    
    // Disconnect
    act(() => {
      result.current.disconnect();
    });
    
    expect(result.current.isConnected).toBe(false);
  });
  
  test('subscribes to message types', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws'));
    
    // Connect WebSocket
    act(() => {
      jest.advanceTimersByTime(100);
    });
    
    // Create a message handler
    const handler = jest.fn();
    
    // Subscribe to a message type
    let unsubscribe;
    act(() => {
      unsubscribe = result.current.subscribe('test-type', handler);
    });
    
    // Simulate receiving a message
    act(() => {
      const ws = result.current;
      const mockEvent = {
        data: JSON.stringify({ type: 'test-type', data: 'test-data' })
      };
      ws.current?.onmessage(mockEvent);
    });
    
    // Unsubscribe
    act(() => {
      unsubscribe();
    });
    
    // Handler should have been called
    expect(handler).toHaveBeenCalledWith(expect.objectContaining({
      type: 'test-type',
      data: 'test-data'
    }));
  });
});

describe('useAnalysisProgress Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.WebSocket = MockWebSocket;
    jest.useFakeTimers();
  });
  
  afterEach(() => {
    jest.useRealTimers();
  });
  
  test('starts analysis and tracks progress', () => {
    // Mock the useWebSocket hook
    jest.mock('../useWebSocket', () => ({
      useWebSocket: () => ({
        isConnected: true,
        sendMessage: jest.fn(() => true),
        subscribe: jest.fn((type, handler) => {
          // Store handlers for simulation
          if (type === 'analysis_progress') {
            progressHandler = handler;
          } else if (type === 'analysis_complete') {
            completeHandler = handler;
          }
          return jest.fn();
        })
      })
    }));
    
    let progressHandler;
    let completeHandler;
    
    const { result } = renderHook(() => useAnalysisProgress());
    
    // Start an analysis
    let analysisId;
    act(() => {
      analysisId = result.current.startAnalysis('niche_discovery', { base_keywords: ['test'] });
    });
    
    // Simulate progress updates
    act(() => {
      if (progressHandler) {
        progressHandler({
          analysis_id: analysisId,
          progress: 50,
          status: 'running',
          step: 'Analyzing keywords',
          estimated_time: 30
        });
      }
    });
    
    // Verify active analysis is tracked
    expect(result.current.activeAnalyses.length).toBe(1);
    expect(result.current.activeAnalyses[0].progress).toBe(50);
    expect(result.current.activeAnalyses[0].currentStep).toBe('Analyzing keywords');
    
    // Simulate completion
    act(() => {
      if (completeHandler) {
        completeHandler({
          analysis_id: analysisId,
          results: { niches: [] },
          execution_time: 5.2
        });
      }
    });
    
    // Advance timer to move completed analysis to history
    act(() => {
      jest.advanceTimersByTime(6000);
    });
    
    // Verify analysis moved to history
    expect(result.current.activeAnalyses.length).toBe(0);
    expect(result.current.progressHistory.length).toBe(1);
  });
  
  test('cancels analysis', () => {
    // Mock sendMessage function
    const sendMessageMock = jest.fn(() => true);
    
    // Mock the useWebSocket hook
    jest.mock('../useWebSocket', () => ({
      useWebSocket: () => ({
        isConnected: true,
        sendMessage: sendMessageMock,
        subscribe: jest.fn(() => jest.fn())
      })
    }));
    
    const { result } = renderHook(() => useAnalysisProgress());
    
    // Start an analysis
    let analysisId;
    act(() => {
      analysisId = result.current.startAnalysis('niche_discovery', { base_keywords: ['test'] });
    });
    
    // Cancel the analysis
    act(() => {
      result.current.cancelAnalysis(analysisId);
    });
    
    // Verify cancel message was sent
    expect(sendMessageMock).toHaveBeenCalledWith(expect.objectContaining({
      type: 'cancel_analysis',
      analysis_id: analysisId
    }));
  });
});