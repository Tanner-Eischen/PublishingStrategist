import React, { useState, useMemo } from 'react';
import { toast } from 'react-toastify';
import { useTrendValidation } from '../hooks/useApiRequest';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { DataTable, ChartDashboard } from '../components/charts';
import {
  ChartBarIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  TableCellsIcon
} from '@heroicons/react/24/outline';

const TrendValidation = () => {
  const [keywords, setKeywords] = useState('');
  const [options, setOptions] = useState({
    timeframe: '12m',
    geo: 'US',
    includeForecasts: true,
    includeSeasonal: true,
    includeCharts: true,
    analysisDepth: 'comprehensive'
  });
  const { validateTrends, isLoading, error, results, reset } = useTrendValidation();

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!keywords.trim()) {
      toast.error('Please enter at least one keyword');
      return;
    }

    try {
      const keywordList = keywords.split(',').map(k => k.trim()).filter(k => k);
      await validateTrends(keywordList, options);
    } catch (err) {
      console.error('Trend validation failed:', err);
    }
  };

  const handleRetry = () => {
    if (keywords.trim()) {
      handleSubmit({ preventDefault: () => {} });
    }
  };

  const getTrendColor = (direction) => {
    switch (direction) {
      case 'rising':
        return 'text-green-600 bg-green-100';
      case 'declining':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getHealthColor = (health) => {
    switch (health) {
      case 'excellent':
        return 'text-green-600 bg-green-100';
      case 'good':
        return 'text-blue-600 bg-blue-100';
      case 'fair':
        return 'text-yellow-600 bg-yellow-100';
      default:
        return 'text-red-600 bg-red-100';
    }
  };

  // Prepare chart data
  const chartData = useMemo(() => {
    if (!results?.trends) return null;

    const trendScores = results.trends.map(trend => ({
      name: trend.keyword,
      value: trend.trend_score,
      direction: trend.direction,
      volatility: trend.volatility || 0,
      confidence: trend.confidence_level || 0
    }));

    const directionData = results.trends.reduce((acc, trend) => {
      const direction = trend.direction || 'stable';
      acc[direction] = (acc[direction] || 0) + 1;
      return acc;
    }, {});

    return {
      trendScores: {
        title: 'Trend Scores by Keyword',
        type: 'bar',
        data: trendScores,
        chartType: 'bar'
      },
      directions: {
        title: 'Trend Direction Distribution',
        type: 'pie',
        data: Object.entries(directionData).map(([direction, count]) => ({
          name: direction.charAt(0).toUpperCase() + direction.slice(1),
          value: count
        })),
        chartType: 'pie'
      },
      volatility: {
        title: 'Volatility vs Trend Score',
        type: 'scatter',
        data: results.trends.map(trend => ({
          x: trend.volatility || 0,
          y: trend.trend_score,
          name: trend.keyword
        })),
        chartType: 'scatter'
      },
      table: {
        title: 'Detailed Trend Analysis',
        type: 'table',
        data: results.trends,
        columns: [
          { key: 'keyword', label: 'Keyword', sortable: true, filterable: true },
          { 
            key: 'direction', 
            label: 'Direction', 
            sortable: true, 
            filterable: true,
            render: (value) => (
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getTrendColor(value)}`}>
                {value}
              </span>
            )
          },
          { 
            key: 'trend_score', 
            label: 'Score', 
            sortable: true,
            render: (value) => `${Math.round(value)}`
          },
          { 
            key: 'volatility', 
            label: 'Volatility', 
            sortable: true,
            render: (value) => value ? `${Math.round(value)}%` : 'N/A'
          },
          { 
            key: 'confidence_level', 
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
        <h1 className="text-3xl font-bold text-gray-900">Trend Validation</h1>
        <p className="text-gray-600 mt-2">
          Validate market trends and analyze keyword performance over time
        </p>
      </div>

      {/* Validation Form */}
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
              placeholder="e.g., productivity, mindfulness, weight loss, fitness"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              disabled={isLoading}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Timeframe</label>
              <select
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={options.timeframe}
                onChange={(e) => setOptions({...options, timeframe: e.target.value})}
                disabled={isLoading}
              >
                <option value="3m">3 months</option>
                <option value="6m">6 months</option>
                <option value="12m">12 months</option>
                <option value="24m">24 months</option>
                <option value="5y">5 years</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Region</label>
              <select
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={options.geo}
                onChange={(e) => setOptions({...options, geo: e.target.value})}
                disabled={isLoading}
              >
                <option value="US">United States</option>
                <option value="GB">United Kingdom</option>
                <option value="CA">Canada</option>
                <option value="AU">Australia</option>
                <option value="">Worldwide</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Analysis Depth</label>
              <select
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={options.analysisDepth}
                onChange={(e) => setOptions({...options, analysisDepth: e.target.value})}
                disabled={isLoading}
              >
                <option value="basic">Basic</option>
                <option value="standard">Standard</option>
                <option value="comprehensive">Comprehensive</option>
              </select>
            </div>

            <div className="flex flex-col space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={options.includeForecasts}
                  onChange={(e) => setOptions({...options, includeForecasts: e.target.checked})}
                  disabled={isLoading}
                />
                <span className="ml-2 text-sm text-gray-700">Include Forecasts</span>
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={options.includeSeasonal}
                  onChange={(e) => setOptions({...options, includeSeasonal: e.target.checked})}
                  disabled={isLoading}
                />
                <span className="ml-2 text-sm text-gray-700">Seasonal Analysis</span>
              </label>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading || !keywords.trim()}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <LoadingSpinner size="small" showMessage={false} />
              ) : (
                <>
                  <ChartBarIcon className="h-5 w-5 mr-2" />
                  Validate Trends
                </>
              )}
            </button>
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
          {/* Overall Health */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Overall Trend Health</h2>
            <div className="flex items-center justify-center">
              <div className={`inline-flex items-center px-4 py-2 rounded-full text-lg font-medium ${getHealthColor(results.overall_trend_health)}`}>
                {results.overall_trend_health?.charAt(0).toUpperCase() + results.overall_trend_health?.slice(1)}
              </div>
            </div>
          </div>

          {/* View Mode Toggle */}
          <div className="bg-white shadow rounded-lg p-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-medium text-gray-900">Trend Analysis Results</h2>
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
              data={results.trends}
              title="Detailed Trend Analysis"
              columns={chartData.table.columns}
              enableSorting={true}
              enableFiltering={true}
              enableExport={true}
              enableSearch={true}
              pageSize={10}
            />
          )}

          {/* Recommendations */}
          {results.recommendations && results.recommendations.length > 0 && (
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Recommendations</h2>
              <ul className="space-y-2">
                {results.recommendations.map((rec, index) => (
                  <li key={index} className="flex items-start">
                    <span className="text-green-500 mr-2">✓</span>
                    <span className="text-gray-700">{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Risk Factors */}
          {results.risk_factors && results.risk_factors.length > 0 && (
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Risk Factors</h2>
              <ul className="space-y-2">
                {results.risk_factors.map((risk, index) => (
                  <li key={index} className="flex items-start">
                    <span className="text-red-500 mr-2">⚠</span>
                    <span className="text-gray-700">{risk}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TrendValidation;