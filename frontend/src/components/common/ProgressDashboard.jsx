import React, { useState, useEffect } from 'react';
import { useAnalysisProgress } from '../../hooks/useWebSocket';
import { useUserPreferences } from '../../hooks/useUserPreferences';
import ProgressIndicator from './ProgressIndicator';
import { toast } from 'react-toastify';
import {
  ChevronUpIcon,
  ChevronDownIcon,
  TrashIcon,
  EyeIcon,
  EyeSlashIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';

const ProgressDashboard = ({ 
  className = '',
  showHistory = true,
  maxVisible = 3,
  autoHide = true,
  onAnalysisComplete = null
}) => {
  const { 
    isConnected, 
    activeAnalyses, 
    progressHistory, 
    cancelAnalysis,
    cancelAllAnalyses,
    pauseAnalysis,
    resumeAnalysis,
    clearHistory 
  } = useAnalysisProgress();
  
  const { getPreference } = useUserPreferences();
  const [isExpanded, setIsExpanded] = useState(false);
  const [isVisible, setIsVisible] = useState(true);
  const [filter, setFilter] = useState('all'); // 'all', 'active', 'completed', 'error'

  // Auto-hide when no active analyses and autoHide is enabled
  useEffect(() => {
    if (autoHide && activeAnalyses.length === 0 && progressHistory.length === 0) {
      setIsVisible(false);
    } else if (activeAnalyses.length > 0) {
      setIsVisible(true);
    }
  }, [activeAnalyses.length, progressHistory.length, autoHide]);

  // Handle analysis completion callbacks
  useEffect(() => {
    activeAnalyses.forEach(analysis => {
      if (analysis.status === 'completed' && onAnalysisComplete) {
        onAnalysisComplete(analysis);
      }
    });
  }, [activeAnalyses, onAnalysisComplete]);

  const getAnalysisSteps = (analysisType) => {
    const stepMaps = {
      niche_discovery: [
        { title: 'Initializing', description: 'Setting up analysis parameters' },
        { title: 'Keyword Expansion', description: 'Expanding keywords using trends data' },
        { title: 'Trend Analysis', description: 'Analyzing Google Trends data' },
        { title: 'Competition Analysis', description: 'Analyzing market competition' },
        { title: 'Scoring', description: 'Calculating profitability scores' },
        { title: 'Finalizing', description: 'Preparing results' }
      ],
      competitor_analysis: [
        { title: 'Initializing', description: 'Setting up competitor search' },
        { title: 'Data Collection', description: 'Gathering competitor data' },
        { title: 'Analysis', description: 'Analyzing competitor metrics' },
        { title: 'Comparison', description: 'Comparing competitors' },
        { title: 'Finalizing', description: 'Preparing analysis results' }
      ],
      trend_validation: [
        { title: 'Initializing', description: 'Setting up trend analysis' },
        { title: 'Data Retrieval', description: 'Fetching trend data' },
        { title: 'Validation', description: 'Validating trend patterns' },
        { title: 'Forecasting', description: 'Generating trend forecasts' },
        { title: 'Finalizing', description: 'Preparing validation results' }
      ],
      listing_generation: [
        { title: 'Initializing', description: 'Setting up listing generation' },
        { title: 'Content Analysis', description: 'Analyzing niche content' },
        { title: 'Generation', description: 'Generating listing content' },
        { title: 'Optimization', description: 'Optimizing for SEO' },
        { title: 'Finalizing', description: 'Preparing final listing' }
      ]
    };

    return stepMaps[analysisType] || [
      { title: 'Processing', description: 'Analysis in progress' }
    ];
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-4 w-4 text-green-500" />;
      case 'error':
        return <ExclamationCircleIcon className="h-4 w-4 text-red-500" />;
      case 'cancelled':
        return <XMarkIcon className="h-4 w-4 text-gray-500" />;
      default:
        return <ClockIcon className="h-4 w-4 text-blue-500" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'error':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'cancelled':
        return 'text-gray-600 bg-gray-50 border-gray-200';
      case 'paused':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      default:
        return 'text-blue-600 bg-blue-50 border-blue-200';
    }
  };

  const filteredHistory = progressHistory.filter(analysis => {
    if (filter === 'all') return true;
    if (filter === 'active') return ['in-progress', 'paused'].includes(analysis.status);
    if (filter === 'completed') return analysis.status === 'completed';
    if (filter === 'error') return analysis.status === 'error';
    return true;
  });

  const allAnalyses = [...activeAnalyses, ...filteredHistory];
  const visibleAnalyses = isExpanded ? allAnalyses : allAnalyses.slice(0, maxVisible);

  if (!isVisible && activeAnalyses.length === 0) {
    return null;
  }

  return (
    <div className={`bg-white rounded-lg shadow-sm border ${className}`}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <h3 className="text-sm font-medium text-gray-900">
              Analysis Progress
            </h3>
            
            {/* Connection status */}
            <div className="flex items-center space-x-1">
              <div className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`} />
              <span className="text-xs text-gray-500">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>

            {/* Active count */}
            {activeAnalyses.length > 0 && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                {activeAnalyses.length} active
              </span>
            )}
          </div>

          <div className="flex items-center space-x-2">
            {/* Filter dropdown */}
            {(activeAnalyses.length > 0 || progressHistory.length > 0) && (
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="text-xs border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">All</option>
                <option value="active">Active</option>
                <option value="completed">Completed</option>
                <option value="error">Errors</option>
              </select>
            )}

            {/* Bulk operations */}
            {activeAnalyses.length > 1 && (
              <button
                onClick={async () => {
                  if (window.confirm(`Cancel all ${activeAnalyses.length} active analyses?`)) {
                    const result = await cancelAllAnalyses();
                    if (result.success) {
                      toast.success(`Cancelled ${result.cancelled_count} analyses`);
                    } else {
                      toast.error(`Failed to cancel analyses: ${result.error}`);
                    }
                  }
                }}
                className="text-xs text-red-500 hover:text-red-700"
                title="Cancel all analyses"
              >
                Cancel All
              </button>
            )}

            {/* Clear history */}
            {progressHistory.length > 0 && (
              <button
                onClick={clearHistory}
                className="text-xs text-gray-500 hover:text-gray-700"
                title="Clear history"
              >
                <TrashIcon className="h-4 w-4" />
              </button>
            )}

            {/* Expand/collapse */}
            {allAnalyses.length > maxVisible && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="text-xs text-gray-500 hover:text-gray-700"
              >
                {isExpanded ? (
                  <ChevronUpIcon className="h-4 w-4" />
                ) : (
                  <ChevronDownIcon className="h-4 w-4" />
                )}
              </button>
            )}

            {/* Hide/show toggle */}
            <button
              onClick={() => setIsVisible(!isVisible)}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              {isVisible ? (
                <EyeSlashIcon className="h-4 w-4" />
              ) : (
                <EyeIcon className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Analysis list */}
      {isVisible && (
        <div className="divide-y divide-gray-200">
          {visibleAnalyses.length === 0 ? (
            <div className="px-4 py-6 text-center text-sm text-gray-500">
              No analyses to display
            </div>
          ) : (
            visibleAnalyses.map((analysis) => (
              <div key={analysis.id} className="p-4">
                {/* Analysis header */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    {getStatusIcon(analysis.status)}
                    <span className="text-sm font-medium text-gray-900">
                      {analysis.type?.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Analysis'}
                    </span>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(analysis.status)}`}>
                      {analysis.status}
                    </span>
                  </div>
                  
                  <div className="flex items-center space-x-2 text-xs text-gray-500">
                    {analysis.startTime && (
                      <span>
                        Started: {new Date(analysis.startTime).toLocaleTimeString()}
                      </span>
                    )}
                    {analysis.executionTime && (
                      <span>
                        Duration: {Math.round(analysis.executionTime)}s
                      </span>
                    )}
                  </div>
                </div>

                {/* Progress indicator for active analyses */}
                {['in-progress', 'paused'].includes(analysis.status) && (
                  <ProgressIndicator
                    steps={getAnalysisSteps(analysis.type)}
                    currentStep={analysis.currentStep || 0}
                    status={analysis.status}
                    analysisId={analysis.id}
                    onCancel={cancelAnalysis}
                    onPause={pauseAnalysis}
                    onResume={resumeAnalysis}
                    showEstimatedTime={getPreference('progress', 'show_time_estimates', true)}
                    estimatedTimeRemaining={analysis.estimatedTime}
                    realTimeUpdates={getPreference('analysis', 'enable_real_time_updates', true)}
                    showControls={getPreference('progress', 'show_cancellation_controls', true)}
                    error={analysis.error}
                  />
                )}

                {/* Completed analysis summary */}
                {analysis.status === 'completed' && analysis.results && (
                  <div className="bg-green-50 border border-green-200 rounded-md p-3">
                    <div className="flex items-center justify-between">
                      <div className="text-sm text-green-800">
                        Analysis completed successfully
                      </div>
                      <div className="text-xs text-green-600">
                        {analysis.results.niches?.length || analysis.results.competitors?.length || 0} results
                      </div>
                    </div>
                  </div>
                )}

                {/* Error analysis summary */}
                {analysis.status === 'error' && (
                  <div className="bg-red-50 border border-red-200 rounded-md p-3">
                    <div className="text-sm text-red-800">
                      Analysis failed: {analysis.error || 'Unknown error'}
                    </div>
                  </div>
                )}

                {/* Parameters summary */}
                {analysis.parameters && (
                  <div className="mt-2 text-xs text-gray-500">
                    <details className="cursor-pointer">
                      <summary className="hover:text-gray-700">Parameters</summary>
                      <pre className="mt-1 text-xs bg-gray-50 p-2 rounded overflow-x-auto">
                        {JSON.stringify(analysis.parameters, null, 2)}
                      </pre>
                    </details>
                  </div>
                )}
              </div>
            ))
          )}

          {/* Show more indicator */}
          {!isExpanded && allAnalyses.length > maxVisible && (
            <div className="px-4 py-2 text-center">
              <button
                onClick={() => setIsExpanded(true)}
                className="text-xs text-blue-600 hover:text-blue-800"
              >
                Show {allAnalyses.length - maxVisible} more analyses
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ProgressDashboard;