import React, { useState, useEffect, useRef } from 'react';
import { toast } from 'react-toastify';
import { useApi } from '../App';
import { useUserPreferences } from '../hooks/useUserPreferences';
import { useAnalysisProgress } from '../hooks/useWebSocket';
import LoadingSpinner from '../components/common/LoadingSpinner';
import {
  CogIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  KeyIcon,
  ServerIcon,
  BellIcon,
  UserIcon,
  ChartBarIcon,
  ClockIcon,
  DocumentArrowUpIcon,
  DocumentArrowDownIcon,
  TrashIcon,
  ShieldCheckIcon
} from '@heroicons/react/24/outline';

const Settings = () => {
  const [settings, setSettings] = useState({
    api_key: '',
    api_endpoint: 'http://localhost:8000',
    notifications: {
      email_alerts: true,
      browser_notifications: true,
      analysis_complete: true,
      error_alerts: true
    },
    preferences: {
      default_export_format: 'csv',
      auto_save_results: true,
      theme: 'light',
      results_per_page: 20
    }
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState(null);
  const [isImporting, setIsImporting] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const fileInputRef = useRef(null);
  
  const { updateApiSettings, refreshConnection, apiSettings } = useApi();
  const { 
    preferences, 
    updatePreferences, 
    resetPreferences,
    exportPreferences,
    importPreferences,
    isLoading: prefsLoading,
    lastSaved
  } = useUserPreferences();
  const { isConnected } = useAnalysisProgress();

  useEffect(() => {
    // Load saved settings from localStorage
    const savedSettings = localStorage.getItem('kdp_strategist_settings');
    if (savedSettings) {
      try {
        const parsed = JSON.parse(savedSettings);
        setSettings(prev => ({ ...prev, ...parsed }));
      } catch (error) {
        console.error('Error loading saved settings:', error);
      }
    }
  }, []);

  const handleSave = async () => {
    setIsLoading(true);
    
    try {
      // Save to localStorage
      localStorage.setItem('kdp_strategist_settings', JSON.stringify(settings));
      
      // Update API settings
      const result = await updateApiSettings({
        api_key: settings.api_key,
        api_endpoint: settings.api_endpoint
      });
      
      if (result.success) {
        toast.success('Settings saved successfully!');
        setConnectionStatus(result.connected ? 'connected' : 'disconnected');
      } else {
        toast.error(`Failed to save settings: ${result.error}`);
        setConnectionStatus('error');
      }
    } catch (error) {
      toast.error('Failed to save settings');
      console.error('Settings save error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    setConnectionStatus(null);
    
    try {
      const isConnected = await refreshConnection();
      setConnectionStatus(isConnected ? 'connected' : 'disconnected');
      
      if (isConnected) {
        toast.success('Connection test successful!');
      } else {
        toast.error('Connection test failed');
      }
    } catch (error) {
      setConnectionStatus('error');
      toast.error('Connection test failed');
    } finally {
      setIsTesting(false);
    }
  };

  const handleReset = () => {
    setSettings({
      api_key: '',
      api_endpoint: 'http://localhost:8000',
      notifications: {
        email_alerts: true,
        browser_notifications: true,
        analysis_complete: true,
        error_alerts: true
      },
      preferences: {
        default_export_format: 'csv',
        auto_save_results: true,
        theme: 'light',
        results_per_page: 20
      }
    });
    setConnectionStatus(null);
    toast.info('Settings reset to defaults');
  };

  const handleExportPreferences = async () => {
    setIsExporting(true);
    try {
      await exportPreferences();
    } catch (error) {
      console.error('Export error:', error);
    } finally {
      setIsExporting(false);
    }
  };

  const handleImportPreferences = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setIsImporting(true);
    try {
      await importPreferences(file);
    } catch (error) {
      console.error('Import error:', error);
    } finally {
      setIsImporting(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleResetAllPreferences = () => {
    if (window.confirm('Are you sure you want to reset all preferences to defaults? This action cannot be undone.')) {
      resetPreferences();
    }
  };

  const getConnectionStatusIcon = () => {
    switch (connectionStatus) {
      case 'connected':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'disconnected':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />;
      case 'error':
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />;
      default:
        return null;
    }
  };

  const getConnectionStatusText = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'Connected';
      case 'disconnected':
        return 'Disconnected';
      case 'error':
        return 'Connection Error';
      default:
        return 'Unknown';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-2">
          Configure your KDP Strategist application preferences and API settings
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* API Configuration */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center mb-4">
            <ServerIcon className="h-5 w-5 text-gray-400 mr-2" />
            <h2 className="text-lg font-medium text-gray-900">API Configuration</h2>
          </div>
          
          <div className="space-y-4">
            <div>
              <label htmlFor="api_endpoint" className="block text-sm font-medium text-gray-700">
                API Endpoint
              </label>
              <input
                type="url"
                id="api_endpoint"
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                placeholder="http://localhost:8000"
                value={settings.api_endpoint}
                onChange={(e) => setSettings(prev => ({ ...prev, api_endpoint: e.target.value }))}
              />
            </div>

            <div>
              <label htmlFor="api_key" className="block text-sm font-medium text-gray-700">
                API Key (Optional)
              </label>
              <div className="mt-1 relative">
                <input
                  type="password"
                  id="api_key"
                  className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 pr-10"
                  placeholder="Enter your API key if required"
                  value={settings.api_key}
                  onChange={(e) => setSettings(prev => ({ ...prev, api_key: e.target.value }))}
                />
                <KeyIcon className="absolute right-3 top-2 h-5 w-5 text-gray-400" />
              </div>
            </div>

            <div className="flex items-center justify-between pt-4 border-t border-gray-200">
              <div className="flex items-center">
                {getConnectionStatusIcon()}
                <span className="ml-2 text-sm text-gray-600">
                  Status: {getConnectionStatusText()}
                </span>
              </div>
              <button
                onClick={handleTestConnection}
                disabled={isTesting}
                className="inline-flex items-center px-3 py-1 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {isTesting ? (
                  <LoadingSpinner size="small" showMessage={false} />
                ) : (
                  'Test Connection'
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Analysis Preferences */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center mb-4">
            <ChartBarIcon className="h-5 w-5 text-gray-400 mr-2" />
            <h2 className="text-lg font-medium text-gray-900">Analysis Preferences</h2>
          </div>
          
          <div className="space-y-4">
            <div>
              <label htmlFor="default_max_results" className="block text-sm font-medium text-gray-700">
                Default Max Results
              </label>
              <select
                id="default_max_results"
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={preferences.analysis?.default_max_results || 20}
                onChange={(e) => updatePreferences({
                  analysis: { default_max_results: parseInt(e.target.value) }
                })}
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>

            <div>
              <label htmlFor="preferred_export_format" className="block text-sm font-medium text-gray-700">
                Preferred Export Format
              </label>
              <select
                id="preferred_export_format"
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={preferences.analysis?.preferred_export_format || 'csv'}
                onChange={(e) => updatePreferences({
                  analysis: { preferred_export_format: e.target.value }
                })}
              >
                <option value="csv">CSV</option>
                <option value="json">JSON</option>
                <option value="xlsx">Excel</option>
              </select>
            </div>

            <div className="space-y-3 pt-4 border-t border-gray-200">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.analysis?.auto_save_results || false}
                  onChange={(e) => updatePreferences({
                    analysis: { auto_save_results: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Auto-save analysis results</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.analysis?.enable_real_time_updates || false}
                  onChange={(e) => updatePreferences({
                    analysis: { enable_real_time_updates: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Enable real-time progress updates</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.analysis?.show_progress_notifications || false}
                  onChange={(e) => updatePreferences({
                    analysis: { show_progress_notifications: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Show progress notifications</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.analysis?.auto_export_completed || false}
                  onChange={(e) => updatePreferences({
                    analysis: { auto_export_completed: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Auto-export completed analyses</span>
              </label>
            </div>
          </div>
        </div>

        {/* UI Preferences */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center mb-4">
            <UserIcon className="h-5 w-5 text-gray-400 mr-2" />
            <h2 className="text-lg font-medium text-gray-900">UI Preferences</h2>
          </div>
          
          <div className="space-y-4">
            <div>
              <label htmlFor="theme" className="block text-sm font-medium text-gray-700">
                Theme
              </label>
              <select
                id="theme"
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={preferences.ui?.theme || 'light'}
                onChange={(e) => updatePreferences({
                  ui: { theme: e.target.value }
                })}
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="auto">Auto</option>
              </select>
            </div>

            <div>
              <label htmlFor="results_per_page" className="block text-sm font-medium text-gray-700">
                Results Per Page
              </label>
              <select
                id="results_per_page"
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={preferences.ui?.results_per_page || 20}
                onChange={(e) => updatePreferences({
                  ui: { results_per_page: parseInt(e.target.value) }
                })}
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>

            <div className="space-y-3 pt-4 border-t border-gray-200">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.ui?.show_advanced_options || false}
                  onChange={(e) => updatePreferences({
                    ui: { show_advanced_options: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Show advanced options by default</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.ui?.compact_view || false}
                  onChange={(e) => updatePreferences({
                    ui: { compact_view: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Use compact view</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.ui?.enable_animations || true}
                  onChange={(e) => updatePreferences({
                    ui: { enable_animations: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Enable animations</span>
              </label>
            </div>
          </div>
        </div>

        {/* Notifications */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center mb-4">
            <BellIcon className="h-5 w-5 text-gray-400 mr-2" />
            <h2 className="text-lg font-medium text-gray-900">Notifications</h2>
          </div>
          
          <div className="space-y-4">
            <label className="flex items-center">
              <input
                type="checkbox"
                className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                checked={settings.notifications.browser_notifications}
                onChange={(e) => setSettings(prev => ({
                  ...prev,
                  notifications: { ...prev.notifications, browser_notifications: e.target.checked }
                }))}
              />
              <span className="ml-2 text-sm text-gray-700">Browser notifications</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                checked={settings.notifications.analysis_complete}
                onChange={(e) => setSettings(prev => ({
                  ...prev,
                  notifications: { ...prev.notifications, analysis_complete: e.target.checked }
                }))}
              />
              <span className="ml-2 text-sm text-gray-700">Analysis completion alerts</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                checked={settings.notifications.error_alerts}
                onChange={(e) => setSettings(prev => ({
                  ...prev,
                  notifications: { ...prev.notifications, error_alerts: e.target.checked }
                }))}
              />
              <span className="ml-2 text-sm text-gray-700">Error alerts</span>
            </label>

            <label className="flex items-center">
              <input
                type="checkbox"
                className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                checked={settings.notifications.email_alerts}
                onChange={(e) => setSettings(prev => ({
                  ...prev,
                  notifications: { ...prev.notifications, email_alerts: e.target.checked }
                }))}
              />
              <span className="ml-2 text-sm text-gray-700">Email alerts (coming soon)</span>
            </label>
          </div>
        </div>

        {/* Performance Preferences */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center mb-4">
            <ClockIcon className="h-5 w-5 text-gray-400 mr-2" />
            <h2 className="text-lg font-medium text-gray-900">Performance Preferences</h2>
          </div>
          
          <div className="space-y-4">
            <div>
              <label htmlFor="max_concurrent_analyses" className="block text-sm font-medium text-gray-700">
                Max Concurrent Analyses
              </label>
              <select
                id="max_concurrent_analyses"
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={preferences.performance?.max_concurrent_analyses || 3}
                onChange={(e) => updatePreferences({
                  performance: { max_concurrent_analyses: parseInt(e.target.value) }
                })}
              >
                <option value={1}>1</option>
                <option value={2}>2</option>
                <option value={3}>3</option>
                <option value={5}>5</option>
              </select>
            </div>

            <div>
              <label htmlFor="cache_duration" className="block text-sm font-medium text-gray-700">
                Cache Duration (hours)
              </label>
              <select
                id="cache_duration"
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={Math.floor((preferences.performance?.cache_duration || 3600) / 3600)}
                onChange={(e) => updatePreferences({
                  performance: { cache_duration: parseInt(e.target.value) * 3600 }
                })}
              >
                <option value={1}>1 hour</option>
                <option value={6}>6 hours</option>
                <option value={12}>12 hours</option>
                <option value={24}>24 hours</option>
                <option value={72}>3 days</option>
              </select>
            </div>

            <div>
              <label htmlFor="retry_attempts" className="block text-sm font-medium text-gray-700">
                Retry Attempts
              </label>
              <select
                id="retry_attempts"
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={preferences.performance?.retry_attempts || 3}
                onChange={(e) => updatePreferences({
                  performance: { retry_attempts: parseInt(e.target.value) }
                })}
              >
                <option value={1}>1</option>
                <option value={2}>2</option>
                <option value={3}>3</option>
                <option value={5}>5</option>
              </select>
            </div>

            <div className="space-y-3 pt-4 border-t border-gray-200">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.performance?.enable_caching || true}
                  onChange={(e) => updatePreferences({
                    performance: { enable_caching: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Enable caching</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.performance?.enable_background_processing || true}
                  onChange={(e) => updatePreferences({
                    performance: { enable_background_processing: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Enable background processing</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.performance?.auto_retry_failed || true}
                  onChange={(e) => updatePreferences({
                    performance: { auto_retry_failed: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Auto-retry failed requests</span>
              </label>
            </div>
          </div>
        </div>

        {/* Progress Preferences */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center mb-4">
            <ChartBarIcon className="h-5 w-5 text-gray-400 mr-2" />
            <h2 className="text-lg font-medium text-gray-900">Progress Preferences</h2>
          </div>
          
          <div className="space-y-4">
            <div>
              <label htmlFor="progress_update_interval" className="block text-sm font-medium text-gray-700">
                Progress Update Interval (ms)
              </label>
              <select
                id="progress_update_interval"
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={preferences.progress?.progress_update_interval || 1000}
                onChange={(e) => updatePreferences({
                  progress: { progress_update_interval: parseInt(e.target.value) }
                })}
              >
                <option value={500}>500ms (Fast)</option>
                <option value={1000}>1000ms (Normal)</option>
                <option value={2000}>2000ms (Slow)</option>
                <option value={5000}>5000ms (Very Slow)</option>
              </select>
            </div>

            <div className="space-y-3 pt-4 border-t border-gray-200">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.progress?.show_floating_indicator || true}
                  onChange={(e) => updatePreferences({
                    progress: { show_floating_indicator: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Show floating progress indicator</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.progress?.show_dashboard || true}
                  onChange={(e) => updatePreferences({
                    progress: { show_dashboard: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Show progress dashboard</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.progress?.show_detailed_steps || true}
                  onChange={(e) => updatePreferences({
                    progress: { show_detailed_steps: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Show detailed progress steps</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.progress?.show_time_estimates || true}
                  onChange={(e) => updatePreferences({
                    progress: { show_time_estimates: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Show time estimates</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.progress?.show_cancellation_controls || true}
                  onChange={(e) => updatePreferences({
                    progress: { show_cancellation_controls: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Show cancellation controls</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.progress?.auto_minimize_completed || true}
                  onChange={(e) => updatePreferences({
                    progress: { auto_minimize_completed: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Auto-minimize completed analyses</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.progress?.enable_progress_sounds || false}
                  onChange={(e) => updatePreferences({
                    progress: { enable_progress_sounds: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Enable progress sounds</span>
              </label>
            </div>
          </div>
        </div>

        {/* WebSocket Preferences */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center mb-4">
            <ServerIcon className="h-5 w-5 text-gray-400 mr-2" />
            <h2 className="text-lg font-medium text-gray-900">WebSocket Preferences</h2>
          </div>
          
          <div className="space-y-4">
            <div>
              <label htmlFor="reconnect_attempts" className="block text-sm font-medium text-gray-700">
                Reconnection Attempts
              </label>
              <select
                id="reconnect_attempts"
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={preferences.websocket?.reconnect_attempts || 5}
                onChange={(e) => updatePreferences({
                  websocket: { reconnect_attempts: parseInt(e.target.value) }
                })}
              >
                <option value={1}>1</option>
                <option value={3}>3</option>
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={-1}>Unlimited</option>
              </select>
            </div>

            <div>
              <label htmlFor="reconnect_delay" className="block text-sm font-medium text-gray-700">
                Reconnection Delay (seconds)
              </label>
              <select
                id="reconnect_delay"
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={Math.floor((preferences.websocket?.reconnect_delay || 3000) / 1000)}
                onChange={(e) => updatePreferences({
                  websocket: { reconnect_delay: parseInt(e.target.value) * 1000 }
                })}
              >
                <option value={1}>1 second</option>
                <option value={3}>3 seconds</option>
                <option value={5}>5 seconds</option>
                <option value={10}>10 seconds</option>
                <option value={30}>30 seconds</option>
              </select>
            </div>

            <div>
              <label htmlFor="heartbeat_interval" className="block text-sm font-medium text-gray-700">
                Heartbeat Interval (seconds)
              </label>
              <select
                id="heartbeat_interval"
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={Math.floor((preferences.websocket?.heartbeat_interval || 30000) / 1000)}
                onChange={(e) => updatePreferences({
                  websocket: { heartbeat_interval: parseInt(e.target.value) * 1000 }
                })}
              >
                <option value={10}>10 seconds</option>
                <option value={30}>30 seconds</option>
                <option value={60}>1 minute</option>
                <option value={300}>5 minutes</option>
                <option value={0}>Disabled</option>
              </select>
            </div>

            <div className="space-y-3 pt-4 border-t border-gray-200">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.websocket?.auto_reconnect || true}
                  onChange={(e) => updatePreferences({
                    websocket: { auto_reconnect: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Auto-reconnect on disconnect</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.websocket?.enable_compression || false}
                  onChange={(e) => updatePreferences({
                    websocket: { enable_compression: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Enable WebSocket compression</span>
              </label>
            </div>
          </div>
        </div>

        {/* Preferences Management */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center mb-4">
            <ShieldCheckIcon className="h-5 w-5 text-gray-400 mr-2" />
            <h2 className="text-lg font-medium text-gray-900">Preferences Management</h2>
          </div>
          
          <div className="space-y-4">
            <div className="text-sm text-gray-600 mb-4">
              Export your preferences to backup or share with others, or import previously saved preferences.
              {lastSaved && (
                <div className="mt-2 text-xs text-green-600">
                  Last saved: {new Date(lastSaved).toLocaleString()}
                </div>
              )}
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={handleExportPreferences}
                disabled={isExporting}
                className="inline-flex items-center justify-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {isExporting ? (
                  <LoadingSpinner size="small" showMessage={false} />
                ) : (
                  <>
                    <DocumentArrowDownIcon className="h-4 w-4 mr-2" />
                    Export Preferences
                  </>
                )}
              </button>

              <div className="relative">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json"
                  onChange={handleImportPreferences}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  disabled={isImporting}
                />
                <button
                  disabled={isImporting}
                  className="inline-flex items-center justify-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 w-full"
                >
                  {isImporting ? (
                    <LoadingSpinner size="small" showMessage={false} />
                  ) : (
                    <>
                      <DocumentArrowUpIcon className="h-4 w-4 mr-2" />
                      Import Preferences
                    </>
                  )}
                </button>
              </div>

              <button
                onClick={handleResetAllPreferences}
                className="inline-flex items-center justify-center px-4 py-2 border border-red-300 shadow-sm text-sm font-medium rounded-md text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                <TrashIcon className="h-4 w-4 mr-2" />
                Reset All
              </button>
            </div>

            <div className="space-y-3 pt-4 border-t border-gray-200">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.privacy?.save_search_history || true}
                  onChange={(e) => updatePreferences({
                    privacy: { save_search_history: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Save search history</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.privacy?.remember_api_settings || true}
                  onChange={(e) => updatePreferences({
                    privacy: { remember_api_settings: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Remember API settings</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={preferences.privacy?.auto_clear_sensitive_data || false}
                  onChange={(e) => updatePreferences({
                    privacy: { auto_clear_sensitive_data: e.target.checked }
                  })}
                />
                <span className="ml-2 text-sm text-gray-700">Auto-clear sensitive data on exit</span>
              </label>
            </div>
          </div>
        </div>

        {/* System Information */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center mb-4">
            <CogIcon className="h-5 w-5 text-gray-400 mr-2" />
            <h2 className="text-lg font-medium text-gray-900">System Information</h2>
          </div>
          
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Application Version:</span>
              <span className="font-medium">1.0.0</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">API Version:</span>
              <span className="font-medium">v1</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">WebSocket Status:</span>
              <span className={`font-medium ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Last Updated:</span>
              <span className="font-medium">{new Date().toLocaleDateString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Current Endpoint:</span>
              <span className="font-medium text-xs break-all">{apiSettings.api_endpoint || 'Not set'}</span>
            </div>
            {prefsLoading && (
              <div className="flex justify-between">
                <span className="text-gray-600">Preferences Status:</span>
                <span className="font-medium text-blue-600">Loading...</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex justify-end space-x-3">
        <button
          onClick={handleReset}
          className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Reset to Defaults
        </button>
        <button
          onClick={handleSave}
          disabled={isLoading}
          className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <LoadingSpinner size="small" showMessage={false} />
          ) : (
            'Save Settings'
          )}
        </button>
      </div>
    </div>
  );
};

export default Settings;