import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  Database,
  Download,
  Eye,
  Play,
  RefreshCw,
  Server,
  Square,
  TrendingDown,
  TrendingUp,
  Zap
} from 'lucide-react';

interface Metric {
  name: string;
  value: number;
  unit: string;
  trend: 'up' | 'down' | 'stable';
  status: 'good' | 'warning' | 'critical';
  description: string;
  chart_type: string;
  historical_data: Array<{ timestamp: string; value: number }>;
}

interface Alert {
  id: string;
  title: string;
  message: string;
  severity: 'info' | 'warning' | 'critical';
  timestamp: string;
  component: string;
  resolved: boolean;
  resolution_time?: string;
}

interface SystemHealth {
  overall_health_score: number;
  component_health: Record<string, { status: string; last_check: string }>;
  active_alerts: Alert[];
  system_metrics: Record<string, Metric>;
  last_updated: string;
}

interface PerformanceReport {
  period: string;
  start_time: string;
  end_time: string;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  avg_response_time: number;
  p95_response_time: number;
  p99_response_time: number;
  error_rate: number;
  cache_hit_rate: number;
  throughput_per_minute: number;
  top_errors: Array<{ error: string; count: number }>;
  slowest_endpoints: Array<{ endpoint: string; avg_time: number }>;
}

interface LogAnalysis {
  start_time: string;
  end_time: string;
  total_entries: number;
  entries_by_level: Record<string, number>;
  entries_by_component: Record<string, number>;
  error_patterns: Array<{ pattern: string; description: string; count: number; severity: string }>;
  performance_metrics: Record<string, number>;
  anomalies: Array<{ type: string; description: string; severity: string }>;
  recommendations: string[];
}

const ProductionMonitoringDashboard: React.FC = () => {
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [performanceReports, setPerformanceReports] = useState<PerformanceReport[]>([]);
  const [logAnalysis, setLogAnalysis] = useState<LogAnalysis | null>(null);
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedMetric, setSelectedMetric] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(30); // seconds

  const fetchSystemHealth = useCallback(async () => {
    try {
      const response = await fetch('/api/monitoring/health');
      const data = await response.json();
      setSystemHealth(data);
    } catch (error) {
      console.error('Failed to fetch system health:', error);
    }
  }, []);

  const fetchPerformanceReports = useCallback(async () => {
    try {
      const response = await fetch('/api/monitoring/performance?hours=24&limit=48');
      const data = await response.json();
      setPerformanceReports(data);
    } catch (error) {
      console.error('Failed to fetch performance reports:', error);
    }
  }, []);

  const fetchLogAnalysis = useCallback(async () => {
    try {
      const response = await fetch('/api/monitoring/logs/analysis?hours=24');
      const data = await response.json();
      setLogAnalysis(data);
    } catch (error) {
      console.error('Failed to fetch log analysis:', error);
    }
  }, []);

  const checkMonitoringStatus = useCallback(async () => {
    try {
      const response = await fetch('/api/monitoring/status');
      const data = await response.json();
      setIsMonitoring(data.dashboard_active && data.log_monitoring_active && data.incident_response_active);
    } catch (error) {
      console.error('Failed to check monitoring status:', error);
    }
  }, []);

  const fetchAllData = useCallback(async () => {
    setLoading(true);
    await Promise.all([
      fetchSystemHealth(),
      fetchPerformanceReports(),
      fetchLogAnalysis(),
      checkMonitoringStatus()
    ]);
    setLoading(false);
  }, [fetchSystemHealth, fetchPerformanceReports, fetchLogAnalysis, checkMonitoringStatus]);

  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(fetchAllData, refreshInterval * 1000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval, fetchAllData]);

  const toggleMonitoring = async () => {
    try {
      const endpoint = isMonitoring ? 'stop' : 'start';
      await fetch(`/api/monitoring/${endpoint}`, { method: 'POST' });
      setIsMonitoring(!isMonitoring);
    } catch (error) {
      console.error('Failed to toggle monitoring:', error);
    }
  };

  const createTestAlert = async () => {
    try {
      await fetch('/api/monitoring/test/alert?severity=warning&component=test', { method: 'POST' });
      alert('Test alert created!');
      fetchSystemHealth();
    } catch (error) {
      console.error('Failed to create test alert:', error);
    }
  };

  const resolveAlert = async (alertId: string) => {
    try {
      await fetch(`/api/monitoring/alerts/${alertId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolution_note: 'Manually resolved from dashboard' })
      });
      fetchSystemHealth();
    } catch (error) {
      console.error('Failed to resolve alert:', error);
    }
  };

  const exportDashboardData = async () => {
    try {
      const response = await fetch('/api/monitoring/dashboard/export?hours=24');
      const data = await response.json();
      
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `monitoring-data-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export dashboard data:', error);
    }
  };

  const getHealthScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    if (score >= 40) return 'text-orange-600';
    return 'text-red-600';
  };

  const getMetricStatusColor = (status: string) => {
    switch (status) {
      case 'good': return 'text-green-600 bg-green-100';
      case 'warning': return 'text-yellow-600 bg-yellow-100';
      case 'critical': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up': return <TrendingUp className="w-4 h-4 text-green-600" />;
      case 'down': return <TrendingDown className="w-4 h-4 text-red-600" />;
      default: return <Activity className="w-4 h-4 text-gray-600" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-600 bg-red-100';
      case 'warning': return 'text-yellow-600 bg-yellow-100';
      case 'info': return 'text-blue-600 bg-blue-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Production Monitoring</h1>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700">Auto Refresh:</label>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Number(e.target.value))}
              className="px-2 py-1 border border-gray-300 rounded text-sm"
              disabled={!autoRefresh}
            >
              <option value={10}>10s</option>
              <option value={30}>30s</option>
              <option value={60}>1m</option>
              <option value={300}>5m</option>
            </select>
          </div>
          
          <button
            onClick={exportDashboardData}
            className="flex items-center px-3 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
          >
            <Download className="w-4 h-4 mr-2" />
            Export
          </button>
          
          <button
            onClick={createTestAlert}
            className="flex items-center px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <AlertTriangle className="w-4 h-4 mr-2" />
            Test Alert
          </button>
          
          <button
            onClick={toggleMonitoring}
            className={`flex items-center px-4 py-2 rounded-lg ${
              isMonitoring 
                ? 'bg-red-600 hover:bg-red-700 text-white' 
                : 'bg-green-600 hover:bg-green-700 text-white'
            }`}
          >
            {isMonitoring ? (
              <>
                <Square className="w-4 h-4 mr-2" />
                Stop Monitoring
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2" />
                Start Monitoring
              </>
            )}
          </button>
        </div>
      </div>

      {/* System Health Overview */}
      {systemHealth && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">System Health</h3>
                <p className={`text-3xl font-bold ${getHealthScoreColor(systemHealth.overall_health_score)}`}>
                  {systemHealth.overall_health_score.toFixed(1)}%
                </p>
              </div>
              <Server className="w-8 h-8 text-gray-400" />
            </div>
          </div>
          
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Active Alerts</h3>
                <p className="text-3xl font-bold text-red-600">
                  {systemHealth.active_alerts.length}
                </p>
              </div>
              <AlertTriangle className="w-8 h-8 text-gray-400" />
            </div>
          </div>
          
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Response Time</h3>
                <p className="text-3xl font-bold text-blue-600">
                  {systemHealth.system_metrics.response_time?.value.toFixed(0) || 0}ms
                </p>
              </div>
              <Clock className="w-8 h-8 text-gray-400" />
            </div>
          </div>
          
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Cache Hit Rate</h3>
                <p className="text-3xl font-bold text-green-600">
                  {systemHealth.system_metrics.cache_hit_rate?.value.toFixed(1) || 0}%
                </p>
              </div>
              <Database className="w-8 h-8 text-gray-400" />
            </div>
          </div>
        </div>
      )}

      {/* Monitoring Status */}
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className={`w-3 h-3 rounded-full mr-3 ${
              isMonitoring ? 'bg-green-500' : 'bg-red-500'
            }`} />
            <span className="font-medium">
              Monitoring Status: {isMonitoring ? 'Active' : 'Inactive'}
            </span>
            {systemHealth && (
              <span className="ml-4 text-sm text-gray-500">
                Last updated: {new Date(systemHealth.last_updated).toLocaleString()}
              </span>
            )}
          </div>
          <button
            onClick={fetchAllData}
            className="text-gray-500 hover:text-gray-700"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Active Alerts */}
      {systemHealth && systemHealth.active_alerts.length > 0 && (
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">Active Alerts</h2>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {systemHealth.active_alerts.map((alert) => (
                <div key={alert.id} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getSeverityColor(alert.severity)}`}>
                        {alert.severity}
                      </span>
                      <h3 className="text-lg font-medium text-gray-900">{alert.title}</h3>
                    </div>
                    <p className="text-gray-600 mt-1">{alert.message}</p>
                    <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
                      <span>Component: {alert.component}</span>
                      <span>Time: {new Date(alert.timestamp).toLocaleString()}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => resolveAlert(alert.id)}
                    className="ml-4 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                  >
                    Resolve
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* System Metrics */}
      {systemHealth && (
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">System Metrics</h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {Object.entries(systemHealth.system_metrics).map(([key, metric]) => (
                <div key={key} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-gray-900">{metric.name}</h3>
                    <div className="flex items-center space-x-2">
                      {getTrendIcon(metric.trend)}
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getMetricStatusColor(metric.status)}`}>
                        {metric.status}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-baseline space-x-2">
                    <span className="text-2xl font-bold text-gray-900">
                      {metric.value.toFixed(metric.unit === '%' ? 1 : 0)}
                    </span>
                    <span className="text-sm text-gray-500">{metric.unit}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{metric.description}</p>
                  <button
                    onClick={() => setSelectedMetric(selectedMetric === key ? null : key)}
                    className="mt-2 text-xs text-blue-600 hover:text-blue-800"
                  >
                    {selectedMetric === key ? 'Hide' : 'Show'} History
                  </button>
                  
                  {selectedMetric === key && metric.historical_data.length > 0 && (
                    <div className="mt-4 p-3 bg-gray-50 rounded">
                      <h4 className="text-xs font-medium text-gray-700 mb-2">Recent History</h4>
                      <div className="space-y-1">
                        {metric.historical_data.slice(-5).map((point, index) => (
                          <div key={index} className="flex justify-between text-xs">
                            <span className="text-gray-500">
                              {new Date(point.timestamp).toLocaleTimeString()}
                            </span>
                            <span className="font-medium">
                              {point.value.toFixed(metric.unit === '%' ? 1 : 0)} {metric.unit}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Performance Reports */}
      {performanceReports.length > 0 && (
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">Performance Reports (Last 24h)</h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
              {performanceReports.slice(0, 1).map((report, index) => (
                <React.Fragment key={index}>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">{report.total_requests}</div>
                    <div className="text-sm text-gray-500">Total Requests</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">{report.avg_response_time.toFixed(0)}ms</div>
                    <div className="text-sm text-gray-500">Avg Response Time</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-red-600">{report.error_rate.toFixed(1)}%</div>
                    <div className="text-sm text-gray-500">Error Rate</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-purple-600">{report.throughput_per_minute.toFixed(1)}</div>
                    <div className="text-sm text-gray-500">Req/Min</div>
                  </div>
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Log Analysis */}
      {logAnalysis && (
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">Log Analysis (Last 24h)</h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Log Levels */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">Log Levels</h3>
                <div className="space-y-2">
                  {Object.entries(logAnalysis.entries_by_level).map(([level, count]) => (
                    <div key={level} className="flex justify-between">
                      <span className="text-sm text-gray-600">{level}</span>
                      <span className="text-sm font-medium">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Error Patterns */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">Error Patterns</h3>
                <div className="space-y-2">
                  {logAnalysis.error_patterns.slice(0, 5).map((pattern, index) => (
                    <div key={index} className="text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600 truncate">{pattern.pattern}</span>
                        <span className="font-medium">{pattern.count}</span>
                      </div>
                      <span className={`inline-flex px-1 py-0.5 text-xs rounded ${getSeverityColor(pattern.severity)}`}>
                        {pattern.severity}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Recommendations */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">Recommendations</h3>
                <div className="space-y-2">
                  {logAnalysis.recommendations.slice(0, 3).map((recommendation, index) => (
                    <div key={index} className="text-sm text-gray-600 p-2 bg-blue-50 rounded">
                      {recommendation}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProductionMonitoringDashboard;