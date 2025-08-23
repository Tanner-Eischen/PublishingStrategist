import React, { useState, useEffect } from 'react';
import { 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  Eye, 
  RefreshCw,
  Play,
  Square,
  Bell
} from 'lucide-react';

interface Incident {
  id: string;
  title: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'open' | 'investigating' | 'resolving' | 'resolved' | 'closed';
  created_at: string;
  updated_at: string;
  resolved_at?: string;
  tags: string[];
  metadata: Record<string, any>;
  actions_taken: string[];
}

interface IncidentSummary {
  total: number;
  by_status: Record<string, number>;
  by_severity: Record<string, number>;
  recent: Array<{
    id: string;
    title: string;
    severity: string;
    status: string;
    created_at: string;
  }>;
}

const IncidentDashboard: React.FC = () => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [summary, setSummary] = useState<IncidentSummary | null>(null);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ status: '', severity: '' });

  useEffect(() => {
    fetchIncidents();
    fetchSummary();
    checkMonitoringStatus();
  }, [filter]);

  const fetchIncidents = async () => {
    try {
      const params = new URLSearchParams();
      if (filter.status) params.append('status', filter.status);
      if (filter.severity) params.append('severity', filter.severity);
      
      const response = await fetch(`/api/incidents?${params}`);
      const data = await response.json();
      setIncidents(data);
    } catch (error) {
      console.error('Failed to fetch incidents:', error);
    }
  };

  const fetchSummary = async () => {
    try {
      const response = await fetch('/api/incidents/summary/overview');
      const data = await response.json();
      setSummary(data);
    } catch (error) {
      console.error('Failed to fetch summary:', error);
    } finally {
      setLoading(false);
    }
  };

  const checkMonitoringStatus = async () => {
    try {
      const response = await fetch('/api/incidents/monitoring/status');
      const data = await response.json();
      setIsMonitoring(data.is_running);
    } catch (error) {
      console.error('Failed to check monitoring status:', error);
    }
  };

  const toggleMonitoring = async () => {
    try {
      const endpoint = isMonitoring ? 'stop' : 'start';
      await fetch(`/api/incidents/monitoring/${endpoint}`, { method: 'POST' });
      setIsMonitoring(!isMonitoring);
    } catch (error) {
      console.error('Failed to toggle monitoring:', error);
    }
  };

  const testNotification = async () => {
    try {
      await fetch('/api/incidents/test/notification', { method: 'POST' });
      alert('Test notification sent!');
      fetchIncidents();
      fetchSummary();
    } catch (error) {
      console.error('Failed to send test notification:', error);
    }
  };

  const resolveIncident = async (incidentId: string, note: string) => {
    try {
      await fetch(`/api/incidents/${incidentId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolution_note: note })
      });
      fetchIncidents();
      fetchSummary();
      setSelectedIncident(null);
    } catch (error) {
      console.error('Failed to resolve incident:', error);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-600 bg-red-100';
      case 'high': return 'text-orange-600 bg-orange-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      case 'low': return 'text-blue-600 bg-blue-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open': return 'text-red-600 bg-red-100';
      case 'investigating': return 'text-yellow-600 bg-yellow-100';
      case 'resolving': return 'text-blue-600 bg-blue-100';
      case 'resolved': return 'text-green-600 bg-green-100';
      case 'closed': return 'text-gray-600 bg-gray-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'open': return <AlertTriangle className="w-4 h-4" />;
      case 'investigating': return <Eye className="w-4 h-4" />;
      case 'resolving': return <RefreshCw className="w-4 h-4" />;
      case 'resolved': return <CheckCircle className="w-4 h-4" />;
      case 'closed': return <CheckCircle className="w-4 h-4" />;
      default: return <Clock className="w-4 h-4" />;
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
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Incident Dashboard</h1>
        <div className="flex space-x-4">
          <button
            onClick={testNotification}
            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Bell className="w-4 h-4 mr-2" />
            Test Notification
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

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Total Incidents</h3>
            <p className="text-3xl font-bold text-blue-600">{summary.total}</p>
          </div>
          
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Open</h3>
            <p className="text-3xl font-bold text-red-600">
              {summary.by_status.open || 0}
            </p>
          </div>
          
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Investigating</h3>
            <p className="text-3xl font-bold text-yellow-600">
              {summary.by_status.investigating || 0}
            </p>
          </div>
          
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Resolved (24h)</h3>
            <p className="text-3xl font-bold text-green-600">
              {summary.recent.filter(i => i.status === 'resolved').length}
            </p>
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
          </div>
          <button
            onClick={checkMonitoringStatus}
            className="text-gray-500 hover:text-gray-700"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <div className="flex space-x-4">
          <select
            value={filter.status}
            onChange={(e) => setFilter({ ...filter, status: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-md"
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="investigating">Investigating</option>
            <option value="resolving">Resolving</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
          
          <select
            value={filter.severity}
            onChange={(e) => setFilter({ ...filter, severity: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-md"
          >
            <option value="">All Severities</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
          
          <button
            onClick={() => setFilter({ status: '', severity: '' })}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
          >
            Clear Filters
          </button>
        </div>
      </div>

      {/* Incidents Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Incident
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Severity
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {incidents.map((incident) => (
              <tr key={incident.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div>
                    <div className="text-sm font-medium text-gray-900">
                      {incident.title}
                    </div>
                    <div className="text-sm text-gray-500">
                      {incident.id}
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getSeverityColor(incident.severity)}`}>
                    {incident.severity}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex items-center px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(incident.status)}`}>
                    {getStatusIcon(incident.status)}
                    <span className="ml-1">{incident.status}</span>
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {new Date(incident.created_at).toLocaleString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button
                    onClick={() => setSelectedIncident(incident)}
                    className="text-blue-600 hover:text-blue-900 mr-4"
                  >
                    View
                  </button>
                  {incident.status !== 'resolved' && incident.status !== 'closed' && (
                    <button
                      onClick={() => {
                        const note = prompt('Enter resolution note:');
                        if (note) resolveIncident(incident.id, note);
                      }}
                      className="text-green-600 hover:text-green-900"
                    >
                      Resolve
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Incident Detail Modal */}
      {selectedIncident && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold text-gray-900">
                Incident Details
              </h3>
              <button
                onClick={() => setSelectedIncident(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">ID</label>
                <p className="text-sm text-gray-900">{selectedIncident.id}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Title</label>
                <p className="text-sm text-gray-900">{selectedIncident.title}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Description</label>
                <p className="text-sm text-gray-900">{selectedIncident.description}</p>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Severity</label>
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getSeverityColor(selectedIncident.severity)}`}>
                    {selectedIncident.severity}
                  </span>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Status</label>
                  <span className={`inline-flex items-center px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(selectedIncident.status)}`}>
                    {getStatusIcon(selectedIncident.status)}
                    <span className="ml-1">{selectedIncident.status}</span>
                  </span>
                </div>
              </div>
              
              {selectedIncident.tags.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">Tags</label>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {selectedIncident.tags.map((tag, index) => (
                      <span key={index} className="px-2 py-1 bg-gray-100 text-gray-800 text-xs rounded">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {selectedIncident.actions_taken.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">Actions Taken</label>
                  <ul className="mt-1 text-sm text-gray-900 list-disc list-inside">
                    {selectedIncident.actions_taken.map((action, index) => (
                      <li key={index}>{action}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              <div className="grid grid-cols-2 gap-4 text-sm text-gray-500">
                <div>
                  <label className="block font-medium">Created</label>
                  <p>{new Date(selectedIncident.created_at).toLocaleString()}</p>
                </div>
                <div>
                  <label className="block font-medium">Updated</label>
                  <p>{new Date(selectedIncident.updated_at).toLocaleString()}</p>
                </div>
              </div>
              
              {selectedIncident.resolved_at && (
                <div className="text-sm text-gray-500">
                  <label className="block font-medium">Resolved</label>
                  <p>{new Date(selectedIncident.resolved_at).toLocaleString()}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IncidentDashboard;