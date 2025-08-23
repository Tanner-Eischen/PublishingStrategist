import React, { useState } from 'react';
import AnalysisProgressManager from '../components/common/AnalysisProgressManager';
import ConnectionMonitor from '../components/common/ConnectionMonitor';
import { useUserPreferences } from '../hooks/useUserPreferences';
import { toast } from 'react-toastify';
import {
  PlayIcon,
  CogIcon,
  ChartBarIcon,
  MagnifyingGlassIcon,
  ArrowTrendingUpIcon,
  DocumentTextIcon,
  WifiIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon
} from '@heroicons/react/24/outline';

/**
 * Demo page showcasing the progress indicators and user experience features
 */
const ProgressDemo = () => {
  const [demoParameters, setDemoParameters] = useState({
    keywords: ['kindle publishing', 'self help books'],
    maxResults: 20,
    includeCompetition: true
  });

  const [showSettings, setShowSettings] = useState(false);

  const { preferences, updatePreference } = useUserPreferences();

  const analysisTypes = [
    {
      id: 'niche_discovery',
      name: 'Niche Discovery',
      description: 'Find profitable publishing niches',
      icon: MagnifyingGlassIcon,
      estimatedTime: '2-3 minutes',
      color: 'blue'
    },
    {
      id: 'competitor_analysis',
      name: 'Competitor Analysis',
      description: 'Analyze market competition',
      icon: ChartBarIcon,
      estimatedTime: '1-2 minutes',
      color: 'green'
    },
    {
      id: 'trend_validation',
      name: 'Trend Validation',
      description: 'Validate market trends',
      icon: ArrowTrendingUpIcon,
      estimatedTime: '30-60 seconds',
      color: 'purple'
    },
    {
      id: 'listing_generation',
      name: 'Listing Generation',
      description: 'Generate optimized listings',
      icon: DocumentTextIcon,
      estimatedTime: '1-2 minutes',
      color: 'orange'
    }
  ];

  const handleAnalysisComplete = (analysis) => {
    console.log('Analysis completed:', analysis);
    toast.success(`${analysis.type?.replace('_', ' ')} completed successfully!`);
  };

  const handleAnalysisError = (analysis) => {
    console.error('Analysis error:', analysis);
    toast.error(`${analysis.type?.replace('_', ' ')} failed: ${analysis.error}`);
  };

  const getColorClasses = (color) => {
    const colorMap = {
      blue: 'bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100',
      green: 'bg-green-50 border-green-200 text-green-700 hover:bg-green-100',
      purple: 'bg-purple-50 border-purple-200 text-purple-700 hover:bg-purple-100',
      orange: 'bg-orange-50 border-orange-200 text-orange-700 hover:bg-orange-100'
    };
    return colorMap[color] || colorMap.blue;
  };

  const handleStartDemoAnalysis = (analysisType, startAnalysis) => {
    const parameters = {
      ...demoParameters,
      analysisType
    };
    
    const analysisId = startAnalysis(analysisType, parameters);
    if (analysisId) {
      toast.info(`Starting ${analysisType.replace('_', ' ')} demo analysis...`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Progress & User Experience Demo</h1>
        <p className="text-gray-600 mt-2">
          Demonstration of real-time progress indicators, WebSocket connections, and user experience features
        </p>
      </div>

      {/* Analysis Progress Manager */}
      <AnalysisProgressManager
        showDashboard={preferences.progress?.show_dashboard !== false}
        showFloatingIndicator={preferences.progress?.show_floating_indicator !== false}
        onAnalysisComplete={handleAnalysisComplete}
        onAnalysisError={handleAnalysisError}
      >
        {({ startAnalysis, cancelAnalysis, cancelAllAnalyses, pauseAnalysis, resumeAnalysis, activeAnalyses, isConnected, canStartAnalysis, getConnectionStats }) => (
          <div className="space-y-6">
            {/* Connection Monitor */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <div className={`p-4 rounded-lg border ${
                  isConnected 
                    ? 'bg-green-50 border-green-200' 
                    : 'bg-red-50 border-red-200'
                }`}>
                  <div className="flex items-center">
                    {isConnected ? (
                      <>
                        <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2" />
                        <WifiIcon className="h-5 w-5 text-green-500 mr-2" />
                        <span className="text-green-800 font-medium">WebSocket Connected</span>
                        <span className="text-green-600 ml-2">Real-time updates enabled</span>
                      </>
                    ) : (
                      <>
                        <ExclamationTriangleIcon className="h-5 w-5 text-red-500 mr-2" />
                        <span className="text-red-800 font-medium">WebSocket Disconnected</span>
                        <span className="text-red-600 ml-2">Real-time updates unavailable</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
              
              <div>
                <ConnectionMonitor showDetails={true} />
              </div>
            </div>

            {/* Demo Parameters */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900">Demo Parameters</h3>
                <button
                  onClick={() => setShowSettings(!showSettings)}
                  className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  <CogIcon className="h-4 w-4 mr-2" />
                  Settings
                </button>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Keywords
                  </label>
                  <input
                    type="text"
                    value={demoParameters.keywords.join(', ')}
                    onChange={(e) => setDemoParameters(prev => ({
                      ...prev,
                      keywords: e.target.value.split(',').map(k => k.trim())
                    }))}
                    className="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Enter keywords separated by commas"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Max Results
                  </label>
                  <input
                    type="number"
                    value={demoParameters.maxResults}
                    onChange={(e) => setDemoParameters(prev => ({
                      ...prev,
                      maxResults: parseInt(e.target.value) || 20
                    }))}
                    className="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    min="1"
                    max="50"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Include Competition
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={demoParameters.includeCompetition}
                      onChange={(e) => setDemoParameters(prev => ({
                        ...prev,
                        includeCompetition: e.target.checked
                      }))}
                      className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                    />
                    <span className="ml-2 text-sm text-gray-700">Enable competition analysis</span>
                  </label>
                </div>
              </div>
            </div>

            {/* Analysis Types */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Available Analysis Types</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {analysisTypes.map((analysisType) => {
                  const IconComponent = analysisType.icon;
                  const isRunning = activeAnalyses.some(a => a.type === analysisType.id);
                  
                  return (
                    <div
                      key={analysisType.id}
                      className={`border rounded-lg p-4 transition-colors ${getColorClasses(analysisType.color)}`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center">
                          <IconComponent className="h-6 w-6 mr-3" />
                          <div>
                            <h4 className="font-medium">{analysisType.name}</h4>
                            <p className="text-sm opacity-75 mt-1">{analysisType.description}</p>
                            <div className="flex items-center mt-2 text-xs opacity-60">
                              <ClockIcon className="h-3 w-3 mr-1" />
                              <span>{analysisType.estimatedTime}</span>
                            </div>
                          </div>
                        </div>
                        
                        <button
                          onClick={() => handleStartDemoAnalysis(analysisType.id, startAnalysis)}
                          disabled={!canStartAnalysis || isRunning}
                          className={`inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                            !canStartAnalysis || isRunning
                              ? 'bg-gray-400 cursor-not-allowed'
                              : 'bg-blue-600 hover:bg-blue-700 focus:ring-blue-500'
                          }`}
                        >
                          {isRunning ? (
                            <>
                              <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white mr-2"></div>
                              Running
                            </>
                          ) : (
                            <>
                              <PlayIcon className="h-3 w-3 mr-2" />
                              Start Demo
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
              
              {!canStartAnalysis && (
                <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                  <div className="flex">
                    <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400" />
                    <div className="ml-3">
                      <p className="text-sm text-yellow-800">
                        Maximum concurrent analyses reached. Please wait for one to complete before starting another.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Active Analyses Summary */}
            {activeAnalyses.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-gray-900">
                    Active Analyses ({activeAnalyses.length})
                  </h3>
                  {activeAnalyses.length > 1 && (
                    <button
                      onClick={async () => {
                        const result = await cancelAllAnalyses();
                        if (result.success) {
                          toast.success(`Cancelled ${result.cancelled_count} analyses`);
                        } else {
                          toast.error(`Failed to cancel analyses: ${result.error}`);
                        }
                      }}
                      className="inline-flex items-center px-3 py-1 border border-red-300 text-sm leading-4 font-medium rounded-md text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                    >
                      Cancel All
                    </button>
                  )}
                </div>
                
                <div className="space-y-3">
                  {activeAnalyses.map((analysis) => (
                    <div key={analysis.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
                      <div className="flex items-center">
                        <div className="flex-shrink-0">
                          {analysis.status === 'in-progress' && (
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                          )}
                          {analysis.status === 'paused' && (
                            <div className="h-4 w-4 bg-yellow-500 rounded-full"></div>
                          )}
                        </div>
                        <div className="ml-3">
                          <p className="text-sm font-medium text-gray-900">
                            {analysis.type?.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </p>
                          <p className="text-xs text-gray-500">
                            Progress: {analysis.progress || 0}% • Status: {analysis.status}
                          </p>
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        {analysis.status === 'in-progress' && (
                          <button
                            onClick={() => pauseAnalysis(analysis.id)}
                            className="text-xs text-yellow-600 hover:text-yellow-800"
                          >
                            Pause
                          </button>
                        )}
                        {analysis.status === 'paused' && (
                          <button
                            onClick={() => resumeAnalysis(analysis.id)}
                            className="text-xs text-green-600 hover:text-green-800"
                          >
                            Resume
                          </button>
                        )}
                        <button
                          onClick={() => cancelAnalysis(analysis.id)}
                          className="text-xs text-red-600 hover:text-red-800"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Settings Panel */}
            {showSettings && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Progress & UX Settings</h3>
                
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <h4 className="text-sm font-medium text-gray-900 mb-3">Progress Display</h4>
                      <div className="space-y-2">
                        <label className="flex items-center">
                          <input
                            type="checkbox"
                            checked={preferences.progress?.show_dashboard !== false}
                            onChange={(e) => updatePreference('progress', 'show_dashboard', e.target.checked)}
                            className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                          />
                          <span className="ml-2 text-sm text-gray-700">Show progress dashboard</span>
                        </label>
                        
                        <label className="flex items-center">
                          <input
                            type="checkbox"
                            checked={preferences.progress?.show_floating_indicator !== false}
                            onChange={(e) => updatePreference('progress', 'show_floating_indicator', e.target.checked)}
                            className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                          />
                          <span className="ml-2 text-sm text-gray-700">Show floating progress indicator</span>
                        </label>
                        
                        <label className="flex items-center">
                          <input
                            type="checkbox"
                            checked={preferences.progress?.show_detailed_steps !== false}
                            onChange={(e) => updatePreference('progress', 'show_detailed_steps', e.target.checked)}
                            className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                          />
                          <span className="ml-2 text-sm text-gray-700">Show detailed progress steps</span>
                        </label>
                        
                        <label className="flex items-center">
                          <input
                            type="checkbox"
                            checked={preferences.progress?.show_time_estimates !== false}
                            onChange={(e) => updatePreference('progress', 'show_time_estimates', e.target.checked)}
                            className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                          />
                          <span className="ml-2 text-sm text-gray-700">Show time estimates</span>
                        </label>
                      </div>
                    </div>
                    
                    <div>
                      <h4 className="text-sm font-medium text-gray-900 mb-3">Notifications</h4>
                      <div className="space-y-2">
                        <label className="flex items-center">
                          <input
                            type="checkbox"
                            checked={preferences.analysis?.show_progress_notifications !== false}
                            onChange={(e) => updatePreference('analysis', 'show_progress_notifications', e.target.checked)}
                            className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                          />
                          <span className="ml-2 text-sm text-gray-700">Show progress notifications</span>
                        </label>
                        
                        <label className="flex items-center">
                          <input
                            type="checkbox"
                            checked={preferences.notifications?.browser_notifications !== false}
                            onChange={(e) => updatePreference('notifications', 'browser_notifications', e.target.checked)}
                            className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                          />
                          <span className="ml-2 text-sm text-gray-700">Enable browser notifications</span>
                        </label>
                        
                        <label className="flex items-center">
                          <input
                            type="checkbox"
                            checked={preferences.notifications?.sound_enabled === true}
                            onChange={(e) => updatePreference('notifications', 'sound_enabled', e.target.checked)}
                            className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                          />
                          <span className="ml-2 text-sm text-gray-700">Enable notification sounds</span>
                        </label>
                        
                        <label className="flex items-center">
                          <input
                            type="checkbox"
                            checked={preferences.analysis?.auto_export_completed === true}
                            onChange={(e) => updatePreference('analysis', 'auto_export_completed', e.target.checked)}
                            className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                          />
                          <span className="ml-2 text-sm text-gray-700">Auto-export completed analyses</span>
                        </label>
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 mb-3">Performance</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Max Concurrent Analyses
                        </label>
                        <input
                          type="number"
                          value={preferences.performance?.max_concurrent_analyses || 3}
                          onChange={(e) => updatePreference('performance', 'max_concurrent_analyses', parseInt(e.target.value) || 3)}
                          className="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                          min="1"
                          max="10"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Progress Update Interval (ms)
                        </label>
                        <input
                          type="number"
                          value={preferences.progress?.progress_update_interval || 1000}
                          onChange={(e) => updatePreference('progress', 'progress_update_interval', parseInt(e.target.value) || 1000)}
                          className="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                          min="100"
                          max="5000"
                          step="100"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </AnalysisProgressManager>
    </div>
  );
};

export default ProgressDemo;