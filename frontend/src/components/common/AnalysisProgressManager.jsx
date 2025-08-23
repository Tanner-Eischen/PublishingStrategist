import React, { useState, useEffect, useCallback } from 'react';
import { useAnalysisProgress } from '../../hooks/useWebSocket';
import { useUserPreferences } from '../../hooks/useUserPreferences';
import ProgressDashboard from './ProgressDashboard';
import FloatingProgressIndicator from './FloatingProgressIndicator';
import ProgressSettings from './ProgressSettings';
import { toast } from 'react-toastify';
import {
  XMarkIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ClockIcon
} from '@heroicons/react/24/outline';

/**
 * Central manager for analysis progress tracking and user experience
 * Handles multiple concurrent analyses with real-time updates
 */
const AnalysisProgressManager = ({ 
  children,
  showDashboard = true,
  showFloatingIndicator = true,
  maxConcurrentAnalyses = null,
  onAnalysisComplete = null,
  onAnalysisError = null,
  className = ''
}) => {
  const { 
    isConnected, 
    activeAnalyses, 
    progressHistory, 
    startAnalysis, 
    cancelAnalysis,
    cancelAllAnalyses,
    pauseAnalysis,
    resumeAnalysis,
    getAnalysisProgress,
    getConnectionStats
  } = useAnalysisProgress();
  
  const { 
    getPreference 
  } = useUserPreferences();

  const [notifications, setNotifications] = useState([]);
  const [showSettings, setShowSettings] = useState(false);

  // Get user preferences
  const maxConcurrent = maxConcurrentAnalyses || getPreference('performance', 'max_concurrent_analyses', 3);
  const showProgressNotifications = getPreference('analysis', 'show_progress_notifications', true);
  const autoExportCompleted = getPreference('analysis', 'auto_export_completed', false);
  const soundEnabled = getPreference('notifications', 'sound_enabled', false);

  // Helper functions
  const playNotificationSound = useCallback((type) => {
    try {
      const audio = new Audio(`/sounds/${type}.mp3`);
      audio.volume = 0.3;
      audio.play().catch(console.error);
    } catch (error) {
      console.error('Failed to play notification sound:', error);
    }
  }, []);

  const addNotification = useCallback((notification) => {
    setNotifications(prev => [notification, ...prev.slice(0, 9)]);
    
    // Auto-remove after 10 seconds
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== notification.id));
    }, 10000);
  }, []);

  const convertToCSV = (data) => {
    // Simple CSV conversion - would need enhancement for complex data
    if (data.niches) {
      const headers = ['Category', 'Keyword', 'Competition Score', 'Profitability Score', 'Market Size'];
      const rows = data.niches.map(niche => [
        niche.category || '',
        niche.primary_keyword || '',
        niche.competition_score_numeric || 0,
        niche.profitability_score_numeric || 0,
        niche.market_size_score || 0
      ]);
      return [headers, ...rows].map(row => row.join(',')).join('\n');
    }
    return JSON.stringify(data, null, 2);
  };

  const handleAutoExport = useCallback((analysis) => {
    try {
      const exportFormat = getPreference('analysis', 'preferred_export_format', 'csv');
      const dataStr = exportFormat === 'json' 
        ? JSON.stringify(analysis.results, null, 2)
        : convertToCSV(analysis.results);
      
      const dataBlob = new Blob([dataStr], { 
        type: exportFormat === 'json' ? 'application/json' : 'text/csv' 
      });
      const url = URL.createObjectURL(dataBlob);
      
      const link = document.createElement('a');
      link.href = url;
      link.download = `${analysis.type}_${analysis.id.slice(-8)}.${exportFormat}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      URL.revokeObjectURL(url);
      toast.success('Analysis results exported automatically');
    } catch (error) {
      console.error('Auto-export failed:', error);
      toast.error('Failed to auto-export results');
    }
  }, [getPreference]);

  const handleAnalysisComplete = useCallback((analysis) => {
    // Play sound if enabled
    if (soundEnabled) {
      playNotificationSound('success');
    }

    // Show toast notification
    toast.success(`${analysis.type?.replace('_', ' ')} analysis completed successfully!`);

    // Auto-export if enabled
    if (autoExportCompleted && analysis.results) {
      handleAutoExport(analysis);
    }

    // Call external callback
    if (onAnalysisComplete) {
      onAnalysisComplete(analysis);
    }

    // Add to notifications
    addNotification({
      id: `complete_${analysis.id}`,
      type: 'success',
      title: 'Analysis Complete',
      message: `${analysis.type?.replace('_', ' ')} analysis finished successfully`,
      timestamp: new Date(),
      analysisId: analysis.id
    });
  }, [soundEnabled, autoExportCompleted, onAnalysisComplete, handleAutoExport, addNotification, playNotificationSound]);

  const handleAnalysisError = useCallback((analysis) => {
    // Play sound if enabled
    if (soundEnabled) {
      playNotificationSound('error');
    }

    // Show toast notification
    toast.error(`${analysis.type?.replace('_', ' ')} analysis failed: ${analysis.error || 'Unknown error'}`);

    // Call external callback
    if (onAnalysisError) {
      onAnalysisError(analysis);
    }

    // Add to notifications
    addNotification({
      id: `error_${analysis.id}`,
      type: 'error',
      title: 'Analysis Failed',
      message: analysis.error || 'Unknown error occurred',
      timestamp: new Date(),
      analysisId: analysis.id
    });
  }, [soundEnabled, onAnalysisError, addNotification, playNotificationSound]);

  // Handle analysis completion
  useEffect(() => {
    activeAnalyses.forEach(analysis => {
      if (analysis.status === 'completed') {
        handleAnalysisComplete(analysis);
      } else if (analysis.status === 'error') {
        handleAnalysisError(analysis);
      }
    });
  }, [activeAnalyses, handleAnalysisComplete, handleAnalysisError]);

  // Handle browser notifications
  useEffect(() => {
    if (showProgressNotifications && 'Notification' in window) {
      activeAnalyses.forEach(analysis => {
        if (analysis.status === 'completed') {
          showBrowserNotification(
            'Analysis Complete',
            `${analysis.type?.replace('_', ' ')} analysis has finished successfully`,
            'success'
          );
        } else if (analysis.status === 'error') {
          showBrowserNotification(
            'Analysis Failed',
            `${analysis.type?.replace('_', ' ')} analysis encountered an error`,
            'error'
          );
        }
      });
    }
  }, [activeAnalyses, showProgressNotifications]);

  const handleStartAnalysis = useCallback((analysisType, parameters) => {
    // Check concurrent limit
    if (activeAnalyses.length >= maxConcurrent) {
      toast.warning(`Maximum ${maxConcurrent} concurrent analyses allowed. Please wait for one to complete.`);
      return null;
    }

    // Start the analysis
    const analysisId = startAnalysis(analysisType, parameters);
    
    // Show start notification
    if (showProgressNotifications) {
      toast.info(`Starting ${analysisType.replace('_', ' ')} analysis...`);
    }

    return analysisId;
  }, [activeAnalyses.length, maxConcurrent, startAnalysis, showProgressNotifications]);

  const handleCancelAnalysis = useCallback((analysisId, reason = 'User cancelled') => {
    const analysis = getAnalysisProgress(analysisId);
    if (analysis) {
      const success = cancelAnalysis(analysisId, reason);
      if (success) {
        toast.info(`${analysis.type?.replace('_', ' ')} analysis cancelled`);
        
        // Play sound if enabled
        if (soundEnabled) {
          playNotificationSound('info');
        }
      } else {
        toast.error('Failed to cancel analysis - WebSocket not connected');
      }
    }
  }, [cancelAnalysis, getAnalysisProgress, soundEnabled, playNotificationSound]);

  const handleCancelAllAnalyses = useCallback(async () => {
    if (activeAnalyses.length === 0) {
      toast.info('No active analyses to cancel');
      return;
    }

    if (window.confirm(`Cancel all ${activeAnalyses.length} active analyses?`)) {
      const result = await cancelAllAnalyses();
      
      if (result.success) {
        toast.success(`Cancelled ${result.cancelled_count} analyses`);
        
        // Play sound if enabled
        if (soundEnabled) {
          playNotificationSound('info');
        }
      } else {
        toast.error(`Failed to cancel analyses: ${result.error || 'Unknown error'}`);
      }
    }
  }, [activeAnalyses.length, cancelAllAnalyses, soundEnabled, playNotificationSound]);

  const handlePauseAnalysis = useCallback((analysisId) => {
    const analysis = getAnalysisProgress(analysisId);
    if (analysis && analysis.status === 'in-progress') {
      const success = pauseAnalysis(analysisId);
      if (success) {
        toast.info(`${analysis.type?.replace('_', ' ')} analysis paused`);
        
        // Play sound if enabled
        if (soundEnabled) {
          playNotificationSound('info');
        }
      } else {
        toast.error('Failed to pause analysis - WebSocket not connected');
      }
    }
  }, [pauseAnalysis, getAnalysisProgress, soundEnabled, playNotificationSound]);

  const handleResumeAnalysis = useCallback((analysisId) => {
    const analysis = getAnalysisProgress(analysisId);
    if (analysis && analysis.status === 'paused') {
      const success = resumeAnalysis(analysisId);
      if (success) {
        toast.info(`${analysis.type?.replace('_', ' ')} analysis resumed`);
        
        // Play sound if enabled
        if (soundEnabled) {
          playNotificationSound('info');
        }
      } else {
        toast.error('Failed to resume analysis - WebSocket not connected');
      }
    }
  }, [resumeAnalysis, getAnalysisProgress, soundEnabled, playNotificationSound]);

  const showBrowserNotification = (title, body, type = 'info') => {
    if ('Notification' in window && Notification.permission === 'granted') {
      const notification = new Notification(title, {
        body,
        icon: type === 'success' ? '/icons/success.png' : 
              type === 'error' ? '/icons/error.png' : '/icons/info.png',
        tag: `kdp-strategist-${type}`,
        requireInteraction: type === 'error'
      });

      // Auto-close after 5 seconds for non-error notifications
      if (type !== 'error') {
        setTimeout(() => notification.close(), 5000);
      }
    }
  };

  const removeNotification = (notificationId) => {
    setNotifications(prev => prev.filter(n => n.id !== notificationId));
  };





  return (
    <div className={`analysis-progress-manager ${className}`}>
      {/* Connection Status Bar */}
      {!isConnected && (
        <div className="bg-red-50 border-l-4 border-red-400 p-4 mb-4">
          <div className="flex">
            <ExclamationCircleIcon className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <p className="text-sm text-red-700">
                WebSocket connection lost. Real-time progress updates are unavailable.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      {children && typeof children === 'function' 
        ? children({
            startAnalysis: handleStartAnalysis,
            cancelAnalysis: handleCancelAnalysis,
            cancelAllAnalyses: handleCancelAllAnalyses,
            pauseAnalysis: handlePauseAnalysis,
            resumeAnalysis: handleResumeAnalysis,
            activeAnalyses,
            isConnected,
            canStartAnalysis: activeAnalyses.length < maxConcurrent,
            getConnectionStats
          })
        : children
      }

      {/* Progress Dashboard */}
      {showDashboard && (activeAnalyses.length > 0 || progressHistory.length > 0) && (
        <div className="mt-6">
          <ProgressDashboard
            showHistory={true}
            maxVisible={3}
            autoHide={false}
            onAnalysisComplete={handleAnalysisComplete}
          />
        </div>
      )}

      {/* Floating Progress Indicator */}
      {showFloatingIndicator && (
        <FloatingProgressIndicator
          position="bottom-right"
          maxVisible={3}
          autoHide={true}
          showControls={getPreference('progress', 'show_cancellation_controls', true)}
        />
      )}

      {/* Notifications */}
      {notifications.length > 0 && (
        <div className="fixed top-4 right-4 z-50 space-y-2">
          {notifications.slice(0, 3).map(notification => (
            <div
              key={notification.id}
              className={`bg-white rounded-lg shadow-lg border-l-4 p-4 max-w-sm ${
                notification.type === 'success' ? 'border-green-400' :
                notification.type === 'error' ? 'border-red-400' :
                'border-blue-400'
              }`}
            >
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  {notification.type === 'success' && (
                    <CheckCircleIcon className="h-5 w-5 text-green-400" />
                  )}
                  {notification.type === 'error' && (
                    <ExclamationCircleIcon className="h-5 w-5 text-red-400" />
                  )}
                  {notification.type === 'info' && (
                    <ClockIcon className="h-5 w-5 text-blue-400" />
                  )}
                </div>
                <div className="ml-3 flex-1">
                  <p className="text-sm font-medium text-gray-900">
                    {notification.title}
                  </p>
                  <p className="text-sm text-gray-500 mt-1">
                    {notification.message}
                  </p>
                </div>
                <button
                  onClick={() => removeNotification(notification.id)}
                  className="ml-4 text-gray-400 hover:text-gray-600"
                >
                  <XMarkIcon className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Progress Settings Modal */}
      <ProgressSettings
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        showAdvanced={true}
      />
    </div>
  );
};

export default AnalysisProgressManager;