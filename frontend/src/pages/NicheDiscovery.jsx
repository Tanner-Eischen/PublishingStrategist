import React, { useState, useMemo, useEffect } from 'react';
import { toast } from 'react-toastify';
import { useNicheDiscovery } from '../hooks/useApiRequest';
import { useAnalysisProgress } from '../hooks/useWebSocket';
import { useAnalysisPreferences } from '../hooks/useUserPreferences';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ProgressDashboard from '../components/common/ProgressDashboard';
import { DataTable, ChartDashboard } from '../components/charts';
import {
  MagnifyingGlassIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  ChartBarIcon,
  TableCellsIcon,
  StopIcon,
  CogIcon
} from '@heroicons/react/24/outline';

const NicheDiscovery = () => {
  const [keywords, setKeywords] = useState('');
  const [options, setOptions] = useState({
    maxResults: 20,
    minSearchVolume: 1000,
    maxCompetition: 0.7,
    includeSeasonal: true,
    includeCharts: true
  });
  const [currentAnalysisId, setCurrentAnalysisId] = useState(null);
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
  
  const { discoverNiches, isLoading, error, results, reset } = useNicheDiscovery();
  const { 
    isConnected, 
    startAnalysis, 
    cancelAnalysis, 
    activeAnalyses 
  } = useAnalysisProgress();
  const { 
    analysisPreferences, 
    getAnalysisDefaults, 
    updateAnalysisPreference 
  } = useAnalysisPreferences();

  // Initialize options from user preferences
  useEffect(() => {
    const defaults = getAnalysisDefaults();
    setOptions(prev => ({
      ...prev,
      maxResults: defaults.maxResults,
      includeCharts: true // Always include charts for visualization
    }));
  }, [getAnalysisDefaults]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!keywords.trim()) {
      toast.error('Please enter at least one keyword');
      return;
    }

    try {
      const keywordList = keywords.split(',').map(k => k.trim()).filter(k => k);
      
      // Start WebSocket progress tracking if connected
      if (isConnected && analysisPreferences.enable_real_time_updates) {
        const analysisId = startAnalysis('niche_discovery', {
          keywords: keywordList,
          ...options
        });
        setCurrentAnalysisId(analysisId);
        
        // Show progress notification
        if (analysisPreferences.show_progress_notifications) {
          toast.info('Analysis started - tracking progress in real-time');
        }
      }
      
      await discoverNiches(keywordList, options);
    } catch (err) {
      // Error handling is done in the custom hook
      console.error('Niche discovery failed:', err);
    } finally {
      setCurrentAnalysisId(null);
    }
  };

  const handleCancel = () => {
    if (currentAnalysisId) {
      cancelAnalysis(currentAnalysisId);
      setCurrentAnalysisId(null);
      toast.info('Analysis cancelled');
    }
  };

  const handleAnalysisComplete = (analysis) => {
    if (analysisPreferences.auto_save_results && analysis.results) {
      // Auto-save results to localStorage
      const savedResults = JSON.parse(localStorage.getItem('kdp_strategist_saved_analyses') || '[]');
      savedResults.unshift({
        id: analysis.id,
        type: analysis.type,
        timestamp: new Date().toISOString(),
        results: analysis.results,
        parameters: analysis.parameters
      });
      
      // Keep only last 50 analyses
      localStorage.setItem('kdp_strategist_saved_analyses', JSON.stringify(savedResults.slice(0, 50)));
    }
    
    if (analysisPreferences.show_progress_notifications) {
      toast.success(`Analysis completed! Found ${analysis.results?.niches?.length || 0} niches`);
    }
  };

  const handleRetry = () => {
    if (keywords.trim()) {
      handleSubmit({ preventDefault: () => {} });
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-600 bg-green-100';
    if (score >= 60) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getCompetitionLevel = (level) => {
    const levels = {
      low: { color: 'text-green-600 bg-green-100', text: 'Low' },
      medium: { color: 'text-yellow-600 bg-yellow-100', text: 'Medium' },
      high: { color: 'text-red-600 bg-red-100', text: 'High' }
    };
    return levels[level] || levels.medium;
  };

  // Prepare chart data
  const chartData = useMemo(() => {
    if (!results?.niches) return null;

    const profitabilityData = results.niches.map(niche => ({
      name: niche.category,
      value: niche.profitability_score_numeric,
      competition: niche.competition_level,
      keywords: niche.keywords?.length || 0
    }));

    const competitionData = results.niches.reduce((acc, niche) => {
      const level = niche.competition_level;
      acc[level] = (acc[level] || 0) + 1;
      return acc;
    }, {});

    return {
      profitability: {
        title: 'Profitability Scores',
        type: 'bar',
        data: profitabilityData,
        chartType: 'bar'
      },
      competition: {
        title: 'Competition Distribution',
        type: 'pie',
        data: Object.entries(competitionData).map(([level, count]) => ({
          name: level.charAt(0).toUpperCase() + level.slice(1),
          value: count
        })),
        chartType: 'pie'
      },
      table: {
        title: 'Detailed Niche Analysis',
        type: 'table',
        data: results.niches,
        columns: [
          { key: 'category', label: 'Category', sortable: true },
          { key: 'primary_keyword', label: 'Primary Keyword', sortable: true },
          { 
            key: 'profitability_score_numeric', 
            label: 'Profitability', 
            sortable: true,
            render: (value) => `${Math.round(value)}%`
          },
          { key: 'competition_level', label: 'Competition', sortable: true },
          { 
            key: 'confidence_score', 
            label: 'Confidence', 
            sortable: true,
            render: (value) => value ? `${Math.round(value)}%` : 'N/A'
          }
        ]
      }
    };
  }, [results]);

  const [viewMode, setViewMode] = useState('charts'); // 'charts' or 'table'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Niche Discovery</h1>
        <p className="text-gray-600 mt-2">
          Discover profitable publishing niches using AI-powered market analysis
        </p>
      </div>

      {/* Progress Dashboard */}
      {(activeAnalyses.length > 0 || analysisPreferences.enable_real_time_updates) && (
        <ProgressDashboard
          onAnalysisComplete={handleAnalysisComplete}
          showHistory={true}
          maxVisible={2}
          autoHide={false}
        />
      )}

      {/* Search Form */}
      <div className="bg-white shadow rounded-lg p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="keywords" className="block text-sm font-medium text-gray-700">
              Keywords (comma-separated)
            </label>
            <textarea
              id="keywords"
              rows={3}
              className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              placeholder="e.g., self-help, productivity, mindfulness, weight loss"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              disabled={isLoading}
            />
          </div>

          {/* Options */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Max Results</label>
              <select
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={options.maxResults}
                onChange={(e) => setOptions({...options, maxResults: parseInt(e.target.value)})}
                disabled={isLoading}
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Min Search Volume</label>
              <select
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={options.minSearchVolume}
                onChange={(e) => setOptions({...options, minSearchVolume: parseInt(e.target.value)})}
                disabled={isLoading}
              >
                <option value={500}>500+</option>
                <option value={1000}>1,000+</option>
                <option value={5000}>5,000+</option>
                <option value={10000}>10,000+</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Max Competition</label>
              <select
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={options.maxCompetition}
                onChange={(e) => setOptions({...options, maxCompetition: parseFloat(e.target.value)})}
                disabled={isLoading}
              >
                <option value={0.3}>Low (0.3)</option>
                <option value={0.5}>Medium (0.5)</option>
                <option value={0.7}>High (0.7)</option>
                <option value={1.0}>Any (1.0)</option>
              </select>
            </div>

            <div className="flex items-center space-x-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={options.includeSeasonal}
                  onChange={(e) => setOptions({...options, includeSeasonal: e.target.checked})}
                  disabled={isLoading}
                />
                <span className="ml-2 text-sm text-gray-700">Include Seasonal</span>
              </label>
            </div>
          </div>

          {/* Advanced Options Toggle */}
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
              className="inline-flex items-center text-sm text-gray-600 hover:text-gray-800"
            >
              <CogIcon className="h-4 w-4 mr-1" />
              {showAdvancedOptions ? 'Hide' : 'Show'} Advanced Options
            </button>
            
            {/* WebSocket connection status */}
            <div className="flex items-center space-x-2 text-xs text-gray-500">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span>Real-time updates {isConnected ? 'enabled' : 'disabled'}</span>
            </div>
          </div>

          {/* Advanced Options */}
          {showAdvancedOptions && (
            <div className="bg-gray-50 p-4 rounded-md space-y-4">
              <h4 className="text-sm font-medium text-gray-900">Analysis Preferences</h4>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                    checked={analysisPreferences.enable_real_time_updates}
                    onChange={(e) => updateAnalysisPreference('enable_real_time_updates', e.target.checked)}
                  />
                  <span className="ml-2 text-sm text-gray-700">Enable real-time progress updates</span>
                </label>

                <label className="flex items-center">
                  <input
                    type="checkbox"
                    className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                    checked={analysisPreferences.auto_save_results}
                    onChange={(e) => updateAnalysisPreference('auto_save_results', e.target.checked)}
                  />
                  <span className="ml-2 text-sm text-gray-700">Auto-save analysis results</span>
                </label>

                <label className="flex items-center">
                  <input
                    type="checkbox"
                    className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                    checked={analysisPreferences.show_progress_notifications}
                    onChange={(e) => updateAnalysisPreference('show_progress_notifications', e.target.checked)}
                  />
                  <span className="ml-2 text-sm text-gray-700">Show progress notifications</span>
                </label>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Export Format</label>
                  <select
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    value={analysisPreferences.preferred_export_format}
                    onChange={(e) => updateAnalysisPreference('preferred_export_format', e.target.value)}
                  >
                    <option value="csv">CSV</option>
                    <option value="json">JSON</option>
                    <option value="xlsx">Excel</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          <div className="flex space-x-3">
            <button
              type="submit"
              disabled={isLoading || !keywords.trim()}
              className="flex-1 flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <LoadingSpinner size="small" showMessage={false} />
              ) : (
                <>
                  <MagnifyingGlassIcon className="h-5 w-5 mr-2" />
                  Discover Niches
                </>
              )}
            </button>

            {/* Cancel button for active analysis */}
            {currentAnalysisId && isLoading && (
              <button
                type="button"
                onClick={handleCancel}
                className="px-4 py-2 border border-red-300 rounded-md shadow-sm text-sm font-medium text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                <StopIcon className="h-5 w-5" />
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-400" />
            <div className="ml-3 flex-1">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <div className="mt-2 text-sm text-red-700">
                <p>{error}</p>
              </div>
              <div className="mt-3 flex space-x-3">
                <button
                  onClick={handleRetry}
                  disabled={isLoading}
                  className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-red-700 bg-red-100 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
                >
                  <ArrowPathIcon className="h-3 w-3 mr-1" />
                  Retry
                </button>
                <button
                  onClick={reset}
                  className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-gray-700 bg-gray-100 hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
                >
                  Clear
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      {results && chartData && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Analysis Summary</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{results.niches?.length || 0}</div>
                <div className="text-sm text-gray-500">Niches Found</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {results.niches?.filter(n => n.profitability_score_numeric >= 70).length || 0}
                </div>
                <div className="text-sm text-gray-500">High Potential</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">
                  {results.niches?.filter(n => n.competition_level === 'low').length || 0}
                </div>
                <div className="text-sm text-gray-500">Low Competition</div>
              </div>
            </div>
          </div>

          {/* View Mode Toggle */}
          <div className="bg-white shadow rounded-lg p-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-medium text-gray-900">Niche Analysis Results</h2>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setViewMode('charts')}
                  className={`inline-flex items-center px-3 py-2 rounded-md text-sm font-medium ${
                    viewMode === 'charts'
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <ChartBarIcon className="h-4 w-4 mr-2" />
                  Charts
                </button>
                <button
                  onClick={() => setViewMode('table')}
                  className={`inline-flex items-center px-3 py-2 rounded-md text-sm font-medium ${
                    viewMode === 'table'
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <TableCellsIcon className="h-4 w-4 mr-2" />
                  Table
                </button>
              </div>
            </div>
          </div>

          {/* Chart/Table Content */}
          {viewMode === 'charts' ? (
            <ChartDashboard
              data={chartData}
              layout="grid"
              responsive={true}
              enableExport={true}
            />
          ) : (
            <DataTable
              data={results.niches}
              title="Detailed Niche Analysis"
              columns={[
                { key: 'category', label: 'Category', sortable: true, filterable: true },
                { key: 'primary_keyword', label: 'Primary Keyword', sortable: true, filterable: true },
                { 
                  key: 'profitability_score_numeric', 
                  label: 'Profitability', 
                  sortable: true,
                  render: (value) => (
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getScoreColor(value)}`}>
                      {Math.round(value)}%
                    </span>
                  )
                },
                { 
                  key: 'competition_level', 
                  label: 'Competition', 
                  sortable: true, 
                  filterable: true,
                  render: (value) => (
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getCompetitionLevel(value).color}`}>
                      {getCompetitionLevel(value).text}
                    </span>
                  )
                },
                { 
                  key: 'confidence_score', 
                  label: 'Confidence', 
                  sortable: true,
                  render: (value) => value ? `${Math.round(value)}%` : 'N/A'
                },
                {
                  key: 'keywords',
                  label: 'Keywords',
                  render: (value) => value ? `${value.length} keywords` : 'N/A'
                }
              ]}
              enableSorting={true}
              enableFiltering={true}
              enableExport={true}
              enableSearch={true}
              pageSize={10}
            />
          )}
        </div>
      )}
    </div>
  );
};

export default NicheDiscovery;