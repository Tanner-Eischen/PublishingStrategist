import React, { useState, useEffect } from 'react';
import { 
  CheckCircleIcon, 
  ClockIcon, 
  ExclamationCircleIcon,
  XMarkIcon,
  PlayIcon,
  PauseIcon,
  StopIcon
} from '@heroicons/react/24/outline';

const ProgressIndicator = ({ 
  steps, 
  currentStep, 
  status = 'in-progress', // 'in-progress', 'completed', 'error', 'cancelled', 'paused'
  showEstimatedTime = true,
  estimatedTimeRemaining = null,
  onCancel = null,
  onPause = null,
  onResume = null,
  analysisId = null,
  showControls = true,
  realTimeUpdates = false,
  executionTime = null,
  error = null
}) => {
  const [elapsedTime, setElapsedTime] = useState(0);
  const [startTime] = useState(Date.now());

  // Update elapsed time for real-time updates
  useEffect(() => {
    if (realTimeUpdates && status === 'in-progress') {
      const interval = setInterval(() => {
        setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
      }, 1000);
      
      return () => clearInterval(interval);
    }
  }, [realTimeUpdates, status, startTime]);

  const getStepStatus = (stepIndex) => {
    if (stepIndex < currentStep) return 'completed';
    if (stepIndex === currentStep) return status;
    return 'pending';
  };

  const getStepIcon = (stepStatus) => {
    switch (stepStatus) {
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'in-progress':
        return (
          <div className="h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        );
      case 'paused':
        return <PauseIcon className="h-5 w-5 text-yellow-500" />;
      case 'cancelled':
        return <XMarkIcon className="h-5 w-5 text-gray-500" />;
      case 'error':
        return <ExclamationCircleIcon className="h-5 w-5 text-red-500" />;
      default:
        return <ClockIcon className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStepColor = (stepStatus) => {
    switch (stepStatus) {
      case 'completed':
        return 'text-green-600 border-green-300 bg-green-50';
      case 'in-progress':
        return 'text-blue-600 border-blue-300 bg-blue-50';
      case 'paused':
        return 'text-yellow-600 border-yellow-300 bg-yellow-50';
      case 'cancelled':
        return 'text-gray-600 border-gray-300 bg-gray-50';
      case 'error':
        return 'text-red-600 border-red-300 bg-red-50';
      default:
        return 'text-gray-500 border-gray-300 bg-gray-50';
    }
  };

  const getStatusMessage = () => {
    switch (status) {
      case 'completed':
        return `Analysis completed${executionTime ? ` in ${formatTime(executionTime)}` : ''}`;
      case 'error':
        return `Analysis failed${error ? `: ${error}` : ''}`;
      case 'cancelled':
        return 'Analysis cancelled by user';
      case 'paused':
        return 'Analysis paused';
      case 'in-progress':
        return 'Analysis in progress...';
      default:
        return 'Preparing analysis...';
    }
  };

  const formatTime = (seconds) => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const getProgressPercentage = () => {
    if (status === 'completed') return 100;
    if (status === 'error' || status === 'cancelled') return 0;
    return Math.round((currentStep / steps.length) * 100);
  };

  const getProgressBarColor = () => {
    switch (status) {
      case 'completed':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      case 'cancelled':
        return 'bg-gray-500';
      case 'paused':
        return 'bg-yellow-500';
      default:
        return 'bg-blue-500';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      {/* Header with controls */}
      <div className="mb-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">Analysis Progress</h3>
            <p className="text-sm text-gray-600 mt-1">{getStatusMessage()}</p>
          </div>
          
          {/* Control buttons */}
          {showControls && (status === 'in-progress' || status === 'paused') && (
            <div className="flex items-center space-x-2">
              {status === 'in-progress' && onPause && (
                <button
                  onClick={() => onPause(analysisId)}
                  className="inline-flex items-center px-2 py-1 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  title="Pause analysis"
                >
                  <PauseIcon className="h-3 w-3" />
                </button>
              )}
              
              {status === 'paused' && onResume && (
                <button
                  onClick={() => onResume(analysisId)}
                  className="inline-flex items-center px-2 py-1 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  title="Resume analysis"
                >
                  <PlayIcon className="h-3 w-3" />
                </button>
              )}
              
              {onCancel && (
                <button
                  onClick={() => onCancel(analysisId)}
                  className="inline-flex items-center px-2 py-1 border border-red-300 shadow-sm text-xs font-medium rounded text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                  title="Cancel analysis"
                >
                  <StopIcon className="h-3 w-3" />
                </button>
              )}
            </div>
          )}
        </div>
        
        {/* Time information */}
        <div className="flex items-center justify-between text-sm text-gray-500 mt-2">
          <div className="flex items-center space-x-4">
            {realTimeUpdates && (
              <span>Elapsed: {formatTime(elapsedTime)}</span>
            )}
            {showEstimatedTime && estimatedTimeRemaining && (
              <span>Remaining: {estimatedTimeRemaining}</span>
            )}
          </div>
          {analysisId && (
            <span className="text-xs font-mono">ID: {analysisId.slice(-8)}</span>
          )}
        </div>
      </div>

      {/* Steps */}
      <div className="space-y-4">
        {steps.map((step, index) => {
          const stepStatus = getStepStatus(index);
          return (
            <div key={index} className="flex items-center">
              <div className={`flex items-center justify-center w-8 h-8 rounded-full border-2 ${getStepColor(stepStatus)}`}>
                {getStepIcon(stepStatus)}
              </div>
              <div className="ml-4 flex-1">
                <div className="flex items-center justify-between">
                  <p className={`text-sm font-medium ${
                    stepStatus === 'completed' ? 'text-green-900' :
                    stepStatus === 'in-progress' ? 'text-blue-900' :
                    stepStatus === 'paused' ? 'text-yellow-900' :
                    stepStatus === 'cancelled' ? 'text-gray-900' :
                    stepStatus === 'error' ? 'text-red-900' :
                    'text-gray-500'
                  }`}>
                    {step.title}
                  </p>
                  {step.duration && stepStatus === 'completed' && (
                    <span className="text-xs text-gray-500">
                      {step.duration}
                    </span>
                  )}
                </div>
                {step.description && (
                  <p className="text-xs text-gray-600 mt-1">
                    {step.description}
                  </p>
                )}
                {stepStatus === 'error' && step.error && (
                  <p className="text-xs text-red-600 mt-1">
                    Error: {step.error}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Enhanced Progress Bar */}
      <div className="mt-6">
        <div className="flex justify-between text-sm text-gray-600 mb-2">
          <span>Progress</span>
          <span>{getProgressPercentage()}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className={`h-2 rounded-full transition-all duration-300 ${getProgressBarColor()}`}
            style={{ width: `${getProgressPercentage()}%` }}
          />
        </div>
      </div>

      {/* Error details */}
      {status === 'error' && error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <div className="flex">
            <ExclamationCircleIcon className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <h4 className="text-sm font-medium text-red-800">Analysis Error</h4>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProgressIndicator;