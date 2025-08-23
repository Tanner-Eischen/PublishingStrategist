import React, { useState, useEffect, useCallback } from 'react';
import { useAnalysisProgress } from '../../hooks/useWebSocket';
import { useUserPreferences } from '../../hooks/useUserPreferences';
import {
  ChartBarIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  PlayIcon,
  PauseIcon,
  StopIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationCircleIcon
} from '@heroicons/react/24/outline';

/**
 * Floating progress indicator that shows active analyses in a compact overlay
 */
const FloatingProgressIndicator = ({ 
  position = 'bottom-right',
  maxVisible = 3,
  autoHide = true,
  showControls = true
}) => {
  const { 
    isConnected, 
    activeAnalyses, 
    cancelAnalysis,
    pauseAnalysis,
    resumeAnalysis
  } = useAnalysisProgress();
  
  const { getPreference } = useUserPreferences();
  const [isMinimized, setIsMinimized] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [position2, setPosition2] = useState({ x: 0, y: 0 });
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Auto-hide when no active analyses
  const shouldShow = !autoHide || activeAnalyses.length > 0;
  const showFloatingIndicator = getPreference('progress', 'show_floating_indicator', true);

  // Get position classes
  const getPositionClasses = () => {
    const base = 'fixed z-50';
    switch (position) {
      case 'top-right':
        return `${base} top-4 right-4`;
      case 'top-left':
        return `${base} top-4 left-4`;
      case 'bottom-left':
        return `${base} bottom-4 left-4`;
      case 'bottom-right':
      default:
        return `${base} bottom-4 right-4`;
    }
  };

  // Handle drag functionality
  const handleMouseDown = (e) => {
    if (e.target.closest('.control-button')) return; // Don't drag when clicking controls
    
    setIsDragging(true);
    setDragStart({
      x: e.clientX - position2.x,
      y: e.clientY - position2.y
    });
  };

  const handleMouseMove = useCallback((e) => {
    if (!isDragging) return;
    
    setPosition2({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    });
  }, [isDragging, dragStart]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-3 w-3 text-green-500" />;
      case 'error':
        return <ExclamationCircleIcon className="h-3 w-3 text-red-500" />;
      case 'paused':
        return <PauseIcon className="h-3 w-3 text-yellow-500" />;
      case 'in-progress':
      default:
        return <ClockIcon className="h-3 w-3 text-blue-500" />;
    }
  };

  const getProgressColor = (status) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      case 'paused':
        return 'bg-yellow-500';
      case 'in-progress':
      default:
        return 'bg-blue-500';
    }
  };

  const formatAnalysisType = (type) => {
    return type?.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Analysis';
  };

  const formatTime = (seconds) => {
    if (!seconds) return '';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  };

  if (!shouldShow || !showFloatingIndicator || activeAnalyses.length === 0) {
    return null;
  }

  const visibleAnalyses = activeAnalyses.slice(0, maxVisible);
  const hiddenCount = Math.max(0, activeAnalyses.length - maxVisible);

  return (
    <div 
      className={`${getPositionClasses()} max-w-sm select-none`}
      style={isDragging ? { 
        transform: `translate(${position2.x}px, ${position2.y}px)`,
        position: 'fixed',
        top: 0,
        left: 0,
        right: 'auto',
        bottom: 'auto'
      } : {}}
    >
      <div 
        className={`bg-white rounded-lg shadow-lg border transition-all duration-200 ${
          isDragging ? 'cursor-grabbing shadow-xl' : 'cursor-grab'
        }`}
        onMouseDown={handleMouseDown}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-gray-200">
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-red-500'
            }`} />
            <ChartBarIcon className="h-4 w-4 text-blue-500" />
            <span className="text-sm font-medium text-gray-900">
              {activeAnalyses.length} Active
            </span>
          </div>
          
          <div className="flex items-center space-x-1">
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="control-button p-1 text-gray-400 hover:text-gray-600 rounded"
              title={isMinimized ? 'Expand' : 'Minimize'}
            >
              {isMinimized ? (
                <ChevronUpIcon className="h-3 w-3" />
              ) : (
                <ChevronDownIcon className="h-3 w-3" />
              )}
            </button>
          </div>
        </div>

        {/* Analysis list */}
        {!isMinimized && (
          <div className="p-3 space-y-3 max-h-80 overflow-y-auto">
            {visibleAnalyses.map(analysis => (
              <div key={analysis.id} className="space-y-2">
                {/* Analysis header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 flex-1 min-w-0">
                    {getStatusIcon(analysis.status)}
                    <span className="text-xs font-medium text-gray-900 truncate">
                      {formatAnalysisType(analysis.type)}
                    </span>
                    <span className="text-xs text-gray-500">
                      {analysis.progress || 0}%
                    </span>
                  </div>
                  
                  {/* Controls */}
                  {showControls && (
                    <div className="flex items-center space-x-1 ml-2">
                      {analysis.status === 'in-progress' && (
                        <button
                          onClick={() => pauseAnalysis(analysis.id)}
                          className="control-button p-1 text-gray-400 hover:text-yellow-600 rounded"
                          title="Pause"
                        >
                          <PauseIcon className="h-3 w-3" />
                        </button>
                      )}
                      
                      {analysis.status === 'paused' && (
                        <button
                          onClick={() => resumeAnalysis(analysis.id)}
                          className="control-button p-1 text-gray-400 hover:text-green-600 rounded"
                          title="Resume"
                        >
                          <PlayIcon className="h-3 w-3" />
                        </button>
                      )}
                      
                      <button
                        onClick={() => cancelAnalysis(analysis.id)}
                        className="control-button p-1 text-gray-400 hover:text-red-600 rounded"
                        title="Cancel"
                      >
                        <StopIcon className="h-3 w-3" />
                      </button>
                    </div>
                  )}
                </div>

                {/* Progress bar */}
                <div className="w-full bg-gray-200 rounded-full h-1.5">
                  <div 
                    className={`h-1.5 rounded-full transition-all duration-300 ${getProgressColor(analysis.status)}`}
                    style={{ width: `${analysis.progress || 0}%` }}
                  />
                </div>

                {/* Time info */}
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>
                    {analysis.currentStep ? `Step ${analysis.currentStep + 1}` : 'Starting...'}
                  </span>
                  {analysis.estimatedTime && (
                    <span>
                      ~{formatTime(analysis.estimatedTime)} left
                    </span>
                  )}
                </div>

                {/* Status message */}
                {analysis.status === 'paused' && analysis.pausedAt && (
                  <div className="text-xs text-yellow-600 bg-yellow-50 px-2 py-1 rounded">
                    Paused at {new Date(analysis.pausedAt).toLocaleTimeString()}
                  </div>
                )}
                
                {analysis.error && (
                  <div className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
                    Error: {analysis.error}
                  </div>
                )}
              </div>
            ))}

            {/* Hidden count indicator */}
            {hiddenCount > 0 && (
              <div className="text-xs text-gray-500 text-center py-2 border-t border-gray-100">
                +{hiddenCount} more analysis{hiddenCount > 1 ? 'es' : ''}
              </div>
            )}

            {/* Connection status */}
            {!isConnected && (
              <div className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded text-center">
                WebSocket disconnected - updates may be delayed
              </div>
            )}
          </div>
        )}

        {/* Minimized view */}
        {isMinimized && (
          <div className="p-2">
            <div className="flex items-center justify-center space-x-2">
              {visibleAnalyses.slice(0, 3).map((analysis, index) => (
                <div key={analysis.id} className="flex items-center space-x-1">
                  <div className={`w-2 h-2 rounded-full ${getProgressColor(analysis.status)}`} />
                  <span className="text-xs text-gray-600">
                    {analysis.progress || 0}%
                  </span>
                </div>
              ))}
              {hiddenCount > 0 && (
                <span className="text-xs text-gray-500">+{hiddenCount}</span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default FloatingProgressIndicator;