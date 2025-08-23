import { useState, useEffect, useRef, useCallback } from 'react';
import { toast } from 'react-toastify';

/**
 * WebSocket hook for real-time updates and progress tracking
 */
export const useWebSocket = (url = null) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [connectionError, setConnectionError] = useState(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  
  const ws = useRef(null);
  const reconnectTimer = useRef(null);
  const heartbeatTimer = useRef(null);
  const messageHandlers = useRef(new Map());
  
  // Get user preferences for WebSocket settings
  const getPreferences = () => {
    try {
      const saved = localStorage.getItem('kdp_strategist_preferences');
      if (saved) {
        const parsed = JSON.parse(saved);
        return parsed.websocket || {};
      }
    } catch (error) {
      console.error('Error loading WebSocket preferences:', error);
    }
    return {};
  };
  
  const prefs = getPreferences();
  const maxReconnectAttempts = prefs.reconnect_attempts || 5;
  const reconnectDelay = prefs.reconnect_delay || 3000;
  const heartbeatInterval = prefs.heartbeat_interval || 30000;
  const autoReconnect = prefs.auto_reconnect !== false;

  // Default WebSocket URL
  const wsUrl = url || `ws://${window.location.hostname}:8000/ws`;

  // Stop heartbeat
  const stopHeartbeat = useCallback(() => {
    if (heartbeatTimer.current) {
      clearInterval(heartbeatTimer.current);
      heartbeatTimer.current = null;
    }
  }, []);

  // Generate unique client ID
  const generateClientId = useCallback(() => {
    const clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    sessionStorage.setItem('client_id', clientId);
    return clientId;
  }, []);

  // Start heartbeat to keep connection alive
  const startHeartbeat = useCallback(() => {
    if (heartbeatTimer.current) {
      clearInterval(heartbeatTimer.current);
    }

    heartbeatTimer.current = setInterval(() => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({
          type: 'ping',
          timestamp: new Date().toISOString(),
          client_id: sessionStorage.getItem('client_id') || generateClientId()
        }));
      }
    }, heartbeatInterval);
  }, [heartbeatInterval, generateClientId]);

  const connect = useCallback(() => {
    try {
      ws.current = new WebSocket(wsUrl);
      
      ws.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setConnectionError(null);
        setReconnectAttempts(0);
        
        // Send initial connection message with a small delay to ensure connection is ready
        setTimeout(() => {
          if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({
              type: 'connection',
              timestamp: new Date().toISOString(),
              client_id: sessionStorage.getItem('client_id') || generateClientId()
            }));
          }
        }, 100);

        // Start heartbeat if enabled
        if (heartbeatInterval > 0) {
          startHeartbeat();
        }
      };

      ws.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          setLastMessage(message);
          
          // Call registered message handlers
          messageHandlers.current.forEach((handler, type) => {
            if (message.type === type) {
              handler(message);
            }
          });
          
          // Handle global message types
          handleGlobalMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        stopHeartbeat();
        
        // Attempt reconnection if not a clean close and auto-reconnect is enabled
        if (autoReconnect && event.code !== 1000 && (maxReconnectAttempts === -1 || reconnectAttempts < maxReconnectAttempts)) {
          setReconnectAttempts(prev => prev + 1);
          reconnectTimer.current = setTimeout(() => {
            console.log(`Attempting to reconnect... (${reconnectAttempts + 1}/${maxReconnectAttempts === -1 ? '∞' : maxReconnectAttempts})`);
            connect();
          }, reconnectDelay * Math.pow(2, Math.min(reconnectAttempts, 5))); // Exponential backoff with max
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionError('WebSocket connection error');
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionError('Failed to create WebSocket connection');
    }
  }, [wsUrl, reconnectAttempts, startHeartbeat, stopHeartbeat, autoReconnect, heartbeatInterval, maxReconnectAttempts, reconnectDelay, generateClientId]);

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
    }
    
    stopHeartbeat();
    
    if (ws.current) {
      ws.current.close(1000, 'Client disconnect');
    }
    
    setIsConnected(false);
    setReconnectAttempts(0);
  }, [stopHeartbeat]);

  const sendMessage = useCallback((message) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      try {
        ws.current.send(JSON.stringify({
          ...message,
          timestamp: new Date().toISOString(),
          client_id: sessionStorage.getItem('client_id') || generateClientId()
        }));
        return true;
      } catch (error) {
        console.error('Error sending WebSocket message:', error);
        return false;
      }
    } else {
      console.warn('WebSocket not connected, message not sent:', message);
      return false;
    }
  }, [generateClientId]);

  const subscribe = useCallback((messageType, handler) => {
    messageHandlers.current.set(messageType, handler);
    
    // Return unsubscribe function
    return () => {
      messageHandlers.current.delete(messageType);
    };
  }, []);

  // Handle global message types
  const handleGlobalMessage = (message) => {
    switch (message.type) {
      case 'error':
        toast.error(message.message || 'An error occurred');
        break;
      case 'notification':
        if (message.level === 'success') {
          toast.success(message.message);
        } else if (message.level === 'warning') {
          toast.warning(message.message);
        } else {
          toast.info(message.message);
        }
        break;
      case 'system':
        if (message.action === 'maintenance') {
          toast.warning('System maintenance in progress');
        }
        break;
      default:
        // Handle unknown message types
        console.log('Unknown message type:', message.type);
        break;
    }
  };



  // Auto-connect on mount
  useEffect(() => {
    connect();
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  // Update API service with client ID when connected
  useEffect(() => {
    if (isConnected && typeof window !== 'undefined') {
      const clientId = sessionStorage.getItem('client_id');
      if (clientId) {
        // Import API service dynamically to avoid circular dependencies
        import('../services/api').then(({ apiService }) => {
          apiService.setClientId(clientId);
        }).catch(console.error);
      }
    }
  }, [isConnected]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      if (heartbeatTimer.current) {
        clearInterval(heartbeatTimer.current);
      }
    };
  }, []);

  return {
    isConnected,
    lastMessage,
    connectionError,
    reconnectAttempts,
    sendMessage,
    subscribe,
    connect,
    disconnect
  };
};

/**
 * Hook for tracking analysis progress via WebSocket
 */
export const useAnalysisProgress = () => {
  const { isConnected, sendMessage, subscribe } = useWebSocket();
  const [activeAnalyses, setActiveAnalyses] = useState(new Map());
  const [progressHistory, setProgressHistory] = useState([]);

  // Subscribe to progress updates
  useEffect(() => {
    const unsubscribeProgress = subscribe('analysis_progress', (message) => {
      const { analysis_id, progress, status, step, estimated_time, error } = message;
      
      setActiveAnalyses(prev => {
        const updated = new Map(prev);
        updated.set(analysis_id, {
          id: analysis_id,
          progress: progress || 0,
          status: status || 'running',
          currentStep: step || 0,
          estimatedTime: estimated_time,
          error: error,
          lastUpdate: new Date().toISOString()
        });
        return updated;
      });
    });

    const unsubscribeComplete = subscribe('analysis_complete', (message) => {
      const { analysis_id, results, execution_time } = message;
      
      setActiveAnalyses(prev => {
        const updated = new Map(prev);
        if (updated.has(analysis_id)) {
          updated.set(analysis_id, {
            ...updated.get(analysis_id),
            status: 'completed',
            progress: 100,
            results,
            executionTime: execution_time
          });
        }
        return updated;
      });

      // Move to history after a delay
      setTimeout(() => {
        setActiveAnalyses(prev => {
          const updated = new Map(prev);
          const analysis = updated.get(analysis_id);
          if (analysis) {
            setProgressHistory(prevHistory => [analysis, ...prevHistory.slice(0, 9)]);
            updated.delete(analysis_id);
          }
          return updated;
        });
      }, 5000);
    });

    const unsubscribeError = subscribe('analysis_error', (message) => {
      const { analysis_id, error } = message;
      
      setActiveAnalyses(prev => {
        const updated = new Map(prev);
        if (updated.has(analysis_id)) {
          updated.set(analysis_id, {
            ...updated.get(analysis_id),
            status: 'error',
            error: error
          });
        }
        return updated;
      });
    });

    return () => {
      unsubscribeProgress();
      unsubscribeComplete();
      unsubscribeError();
    };
  }, [subscribe]);

  const startAnalysis = useCallback((analysisType, parameters) => {
    const analysisId = `${analysisType}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // Initialize progress tracking
    setActiveAnalyses(prev => {
      const updated = new Map(prev);
      updated.set(analysisId, {
        id: analysisId,
        type: analysisType,
        parameters,
        progress: 0,
        status: 'starting',
        currentStep: 0,
        startTime: new Date().toISOString()
      });
      return updated;
    });

    // Send start message via WebSocket
    sendMessage({
      type: 'start_analysis',
      analysis_id: analysisId,
      analysis_type: analysisType,
      parameters
    });

    return analysisId;
  }, [sendMessage]);

  const cancelAnalysis = useCallback((analysisId, reason = 'User cancelled') => {
    const success = sendMessage({
      type: 'cancel_analysis',
      analysis_id: analysisId,
      reason: reason
    });

    if (success) {
      setActiveAnalyses(prev => {
        const updated = new Map(prev);
        if (updated.has(analysisId)) {
          updated.set(analysisId, {
            ...updated.get(analysisId),
            status: 'cancelled',
            cancelledAt: new Date().toISOString(),
            cancellationReason: reason
          });
        }
        return updated;
      });
    }

    return success;
  }, [sendMessage]);

  const pauseAnalysis = useCallback((analysisId) => {
    if (!isConnected) {
      console.warn('Cannot pause analysis: WebSocket not connected');
      return false;
    }

    const success = sendMessage({
      type: 'pause_analysis',
      analysis_id: analysisId
    });

    if (success) {
      setActiveAnalyses(prev => {
        const updated = new Map(prev);
        if (updated.has(analysisId)) {
          updated.set(analysisId, {
            ...updated.get(analysisId),
            status: 'paused',
            pausedAt: new Date().toISOString()
          });
        }
        return updated;
      });
    }

    return success;
  }, [sendMessage, isConnected]);

  const resumeAnalysis = useCallback((analysisId) => {
    if (!isConnected) {
      console.warn('Cannot resume analysis: WebSocket not connected');
      return false;
    }

    const success = sendMessage({
      type: 'resume_analysis',
      analysis_id: analysisId
    });

    if (success) {
      setActiveAnalyses(prev => {
        const updated = new Map(prev);
        if (updated.has(analysisId)) {
          const analysis = updated.get(analysisId);
          updated.set(analysisId, {
            ...analysis,
            status: 'in-progress',
            resumedAt: new Date().toISOString(),
            pausedAt: undefined
          });
        }
        return updated;
      });
    }

    return success;
  }, [sendMessage, isConnected]);

  const getAnalysisProgress = useCallback((analysisId) => {
    return activeAnalyses.get(analysisId);
  }, [activeAnalyses]);

  const cancelAllAnalyses = useCallback(async () => {
    if (!isConnected) {
      console.warn('Cannot cancel analyses: WebSocket not connected');
      return { success: false, error: 'WebSocket not connected' };
    }

    try {
      // Call API endpoint to cancel all analyses
      const response = await fetch('/api/settings/analysis/cancel-all', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Client-ID': sessionStorage.getItem('client_id') || ''
        }
      });

      const result = await response.json();
      
      if (result.success) {
        // Update local state
        setActiveAnalyses(prev => {
          const updated = new Map();
          prev.forEach((analysis, id) => {
            updated.set(id, {
              ...analysis,
              status: 'cancelled',
              cancelledAt: new Date().toISOString(),
              cancellationReason: 'Bulk cancellation'
            });
          });
          return updated;
        });
      }

      return result;
    } catch (error) {
      console.error('Error cancelling all analyses:', error);
      return { success: false, error: error.message };
    }
  }, [isConnected]);

  const clearHistory = useCallback(() => {
    setProgressHistory([]);
  }, []);

  const getConnectionStats = useCallback(async () => {
    try {
      const response = await fetch('/api/settings/websocket/status', {
        headers: {
          'X-Client-ID': sessionStorage.getItem('client_id') || ''
        }
      });
      return await response.json();
    } catch (error) {
      console.error('Error getting connection stats:', error);
      return null;
    }
  }, []);

  return {
    isConnected,
    activeAnalyses: Array.from(activeAnalyses.values()),
    progressHistory,
    startAnalysis,
    cancelAnalysis,
    cancelAllAnalyses,
    pauseAnalysis,
    resumeAnalysis,
    getAnalysisProgress,
    clearHistory,
    getConnectionStats
  };
};

export default useWebSocket;