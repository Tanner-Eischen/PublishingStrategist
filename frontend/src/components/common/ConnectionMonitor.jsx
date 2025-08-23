import React, { useState, useEffect, useCallback } from 'react';
import { useAnalysisProgress } from '../../hooks/useWebSocket';
import {
  WifiIcon,
  SignalIcon,
  ClockIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';

/**
 * Connection monitoring component that displays WebSocket status and statistics
 */
const ConnectionMonitor = ({ 
  className = '',
  showDetails = false,
  refreshInterval = 5000 
}) => {
  const { isConnected, getConnectionStats } = useAnalysisProgress();
  const [stats, setStats] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Fetch connection statistics
  const fetchStats = useCallback(async () => {
    if (!getConnectionStats) return;
    
    setIsRefreshing(true);
    try {
      const newStats = await getConnectionStats();
      if (newStats) {
        setStats(newStats);
        setLastUpdate(new Date());
      }
    } catch (error) {
      console.error('Error fetching connection stats:', error);
    } finally {
      setIsRefreshing(false);
    }
  }, [getConnectionStats]);

  // Auto-refresh stats
  useEffect(() => {
    if (isConnected && refreshInterval > 0) {
      fetchStats(); // Initial fetch
      
      const interval = setInterval(fetchStats, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [isConnected, refreshInterval, fetchStats]);

  const getConnectionStatusColor = () => {
    if (!isConnected) return 'text-red-600 bg-red-50 border-red-200';
    if (stats?.active_analyses > 0) return 'text-blue-600 bg-blue-50 border-blue-200';
    return 'text-green-600 bg-green-50 border-green-200';
  };

  const getConnectionStatusIcon = () => {
    if (!isConnected) return <ExclamationTriangleIcon className="h-4 w-4" />;
    if (stats?.active_analyses > 0) return <ChartBarIcon className="h-4 w-4" />;
    return <CheckCircleIcon className="h-4 w-4" />;
  };

  const getConnectionStatusText = () => {
    if (!isConnected) return 'Disconnected';
    if (stats?.active_analyses > 0) return `${stats.active_analyses} Active`;
    return 'Connected';
  };



  if (!showDetails) {
    // Compact view
    return (
      <div className={`inline-flex items-center space-x-2 ${className}`}>
        <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${getConnectionStatusColor()}`}>
          {getConnectionStatusIcon()}
          <span className="ml-1">{getConnectionStatusText()}</span>
        </div>
        
        {isConnected && stats && (
          <div className="text-xs text-gray-500">
            {stats.total_connections} connections
          </div>
        )}
      </div>
    );
  }

  // Detailed view
  return (
    <div className={`bg-white rounded-lg border shadow-sm ${className}`}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <WifiIcon className="h-5 w-5 text-gray-400" />
            <h3 className="text-sm font-medium text-gray-900">Connection Status</h3>
          </div>
          
          <button
            onClick={fetchStats}
            disabled={isRefreshing}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
            title="Refresh statistics"
          >
            <ArrowPathIcon className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Status */}
      <div className="p-4 space-y-4">
        <div className={`flex items-center justify-between p-3 rounded-md border ${getConnectionStatusColor()}`}>
          <div className="flex items-center space-x-2">
            {getConnectionStatusIcon()}
            <span className="font-medium">{getConnectionStatusText()}</span>
          </div>
          
          {isConnected && (
            <div className="flex items-center space-x-1 text-sm">
              <SignalIcon className="h-4 w-4" />
              <span>Real-time</span>
            </div>
          )}
        </div>

        {/* Statistics */}
        {isConnected && stats && (
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">
                {stats.total_connections}
              </div>
              <div className="text-xs text-gray-500">Total Connections</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">
                {stats.active_analyses}
              </div>
              <div className="text-xs text-gray-500">Active Analyses</div>
            </div>
          </div>
        )}

        {/* Analysis Statistics */}
        {stats?.analysis_statistics && (
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-gray-900">Analysis Breakdown</h4>
            
            {/* By Status */}
            {Object.keys(stats.analysis_statistics.by_status).length > 0 && (
              <div>
                <div className="text-xs text-gray-500 mb-2">By Status</div>
                <div className="space-y-1">
                  {Object.entries(stats.analysis_statistics.by_status).map(([status, count]) => (
                    <div key={status} className="flex justify-between text-sm">
                      <span className="capitalize">{status.replace('_', ' ')}</span>
                      <span className="font-medium">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* By Type */}
            {Object.keys(stats.analysis_statistics.by_type).length > 0 && (
              <div>
                <div className="text-xs text-gray-500 mb-2">By Type</div>
                <div className="space-y-1">
                  {Object.entries(stats.analysis_statistics.by_type).map(([type, count]) => (
                    <div key={type} className="flex justify-between text-sm">
                      <span className="capitalize">{type.replace('_', ' ')}</span>
                      <span className="font-medium">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Client Analyses */}
        {stats?.analysis_statistics?.client_analyses?.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-gray-900">Your Analyses</h4>
            <div className="space-y-1">
              {stats.analysis_statistics.client_analyses.map((analysis) => (
                <div key={analysis.id} className="flex items-center justify-between text-sm p-2 bg-gray-50 rounded">
                  <div>
                    <span className="font-medium capitalize">
                      {analysis.type?.replace('_', ' ')}
                    </span>
                    <span className="text-gray-500 ml-2">
                      {analysis.progress}%
                    </span>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    analysis.status === 'in-progress' ? 'bg-blue-100 text-blue-800' :
                    analysis.status === 'completed' ? 'bg-green-100 text-green-800' :
                    analysis.status === 'paused' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {analysis.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Last Update */}
        {lastUpdate && (
          <div className="flex items-center justify-center text-xs text-gray-500 pt-2 border-t border-gray-100">
            <ClockIcon className="h-3 w-3 mr-1" />
            <span>Updated {lastUpdate.toLocaleTimeString()}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default ConnectionMonitor;