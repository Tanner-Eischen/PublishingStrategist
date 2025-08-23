import React, { useState } from 'react';
import { useUserPreferences } from '../../hooks/useUserPreferences';
import { toast } from 'react-toastify';
import {
  CogIcon,
  ChartBarIcon,
  BellIcon,
  ClockIcon,
  WifiIcon,
  ArrowPathIcon,
  CheckIcon
} from '@heroicons/react/24/outline';

/**
 * Comprehensive progress settings component for configuring user experience
 */
const ProgressSettings = ({ 
  isOpen = false, 
  onClose = () => {},
  showAdvanced = false 
}) => {
  const { 
    preferences, 
    updatePreferences, 
    resetPreferences,
    savePreferences 
  } = useUserPreferences();

  const [activeTab, setActiveTab] = useState('progress');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Handle preference updates with change tracking
  const handlePreferenceChange = (category, key, value) => {
    updatePreferences({
      [category]: { [key]: value }
    });
    setHasUnsavedChanges(true);
  };

  // Save all preferences
  const handleSave = async () => {
    const result = await savePreferences();
    if (result.success) {
      toast.success('Progress settings saved successfully');
      setHasUnsavedChanges(false);
    } else {
      toast.error('Failed to save settings');
    }
  };

  // Reset category preferences
  const handleResetCategory = (category) => {
    if (window.confirm(`Reset all ${category} preferences to defaults?`)) {
      resetPreferences(category);
      setHasUnsavedChanges(true);
      toast.info(`${category} preferences reset to defaults`);
    }
  };

  const tabs = [
    { id: 'progress', name: 'Progress', icon: ChartBarIcon },
    { id: 'notifications', name: 'Notifications', icon: BellIcon },
    { id: 'websocket', name: 'Connection', icon: WifiIcon },
    { id: 'performance', name: 'Performance', icon: ClockIcon }
  ];

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Backdrop */}
        <div 
          className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
          onClick={onClose}
        />

        {/* Modal */}
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
          {/* Header */}
          <div className="bg-white px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <CogIcon className="h-6 w-6 text-gray-400 mr-3" />
                <h3 className="text-lg font-medium text-gray-900">
                  Progress & User Experience Settings
                </h3>
              </div>
              <div className="flex items-center space-x-3">
                {hasUnsavedChanges && (
                  <span className="text-sm text-yellow-600 bg-yellow-50 px-2 py-1 rounded">
                    Unsaved changes
                  </span>
                )}
                <button
                  onClick={onClose}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <span className="sr-only">Close</span>
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <div className="flex">
            {/* Sidebar */}
            <div className="w-64 bg-gray-50 border-r border-gray-200">
              <nav className="p-4 space-y-2">
                {tabs.map(tab => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                        activeTab === tab.id
                          ? 'bg-blue-100 text-blue-700'
                          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                      }`}
                    >
                      <Icon className="h-5 w-5 mr-3" />
                      {tab.name}
                    </button>
                  );
                })}
              </nav>
            </div>

            {/* Content */}
            <div className="flex-1 p-6">
              {/* Progress Settings */}
              {activeTab === 'progress' && (
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <h4 className="text-lg font-medium text-gray-900">Progress Display</h4>
                    <button
                      onClick={() => handleResetCategory('progress')}
                      className="text-sm text-gray-500 hover:text-gray-700"
                    >
                      <ArrowPathIcon className="h-4 w-4 inline mr-1" />
                      Reset to defaults
                    </button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Display Options */}
                    <div className="space-y-4">
                      <h5 className="font-medium text-gray-900">Display Options</h5>
                      
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={preferences.progress?.show_floating_indicator || true}
                          onChange={(e) => handlePreferenceChange('progress', 'show_floating_indicator', e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Show floating progress indicator</span>
                      </label>

                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={preferences.progress?.show_dashboard || true}
                          onChange={(e) => handlePreferenceChange('progress', 'show_dashboard', e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Show progress dashboard</span>
                      </label>

                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={preferences.progress?.show_detailed_steps || true}
                          onChange={(e) => handlePreferenceChange('progress', 'show_detailed_steps', e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Show detailed progress steps</span>
                      </label>

                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={preferences.progress?.auto_minimize_completed || true}
                          onChange={(e) => handlePreferenceChange('progress', 'auto_minimize_completed', e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Auto-minimize completed analyses</span>
                      </label>
                    </div>

                    {/* Time and Controls */}
                    <div className="space-y-4">
                      <h5 className="font-medium text-gray-900">Time & Controls</h5>
                      
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={preferences.progress?.show_time_estimates || true}
                          onChange={(e) => handlePreferenceChange('progress', 'show_time_estimates', e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Show time estimates</span>
                      </label>

                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={preferences.progress?.show_cancellation_controls || true}
                          onChange={(e) => handlePreferenceChange('progress', 'show_cancellation_controls', e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Show cancellation controls</span>
                      </label>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Progress Update Interval
                        </label>
                        <select
                          value={preferences.progress?.progress_update_interval || 1000}
                          onChange={(e) => handlePreferenceChange('progress', 'progress_update_interval', parseInt(e.target.value))}
                          className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value={500}>500ms (Fast)</option>
                          <option value={1000}>1000ms (Normal)</option>
                          <option value={2000}>2000ms (Slow)</option>
                          <option value={5000}>5000ms (Very Slow)</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Notification Settings */}
              {activeTab === 'notifications' && (
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <h4 className="text-lg font-medium text-gray-900">Notifications</h4>
                    <button
                      onClick={() => handleResetCategory('notifications')}
                      className="text-sm text-gray-500 hover:text-gray-700"
                    >
                      <ArrowPathIcon className="h-4 w-4 inline mr-1" />
                      Reset to defaults
                    </button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Browser Notifications */}
                    <div className="space-y-4">
                      <h5 className="font-medium text-gray-900">Browser Notifications</h5>
                      
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={preferences.notifications?.browser_notifications || true}
                          onChange={(e) => handlePreferenceChange('notifications', 'browser_notifications', e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Enable browser notifications</span>
                      </label>

                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={preferences.notifications?.analysis_complete || true}
                          onChange={(e) => handlePreferenceChange('notifications', 'analysis_complete', e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Analysis completion alerts</span>
                      </label>

                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={preferences.notifications?.error_alerts || true}
                          onChange={(e) => handlePreferenceChange('notifications', 'error_alerts', e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Error alerts</span>
                      </label>

                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={preferences.notifications?.progress_updates || false}
                          onChange={(e) => handlePreferenceChange('notifications', 'progress_updates', e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Progress update notifications</span>
                      </label>
                    </div>

                    {/* Sound and Visual */}
                    <div className="space-y-4">
                      <h5 className="font-medium text-gray-900">Sound & Visual</h5>
                      
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={preferences.notifications?.sound_enabled || false}
                          onChange={(e) => handlePreferenceChange('notifications', 'sound_enabled', e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Enable notification sounds</span>
                      </label>

                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={preferences.progress?.enable_progress_sounds || false}
                          onChange={(e) => handlePreferenceChange('progress', 'enable_progress_sounds', e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Progress completion sounds</span>
                      </label>

                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={preferences.notifications?.email_alerts || false}
                          onChange={(e) => handlePreferenceChange('notifications', 'email_alerts', e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Email alerts (coming soon)</span>
                      </label>
                    </div>
                  </div>
                </div>
              )}

              {/* WebSocket Settings */}
              {activeTab === 'websocket' && (
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <h4 className="text-lg font-medium text-gray-900">WebSocket Connection</h4>
                    <button
                      onClick={() => handleResetCategory('websocket')}
                      className="text-sm text-gray-500 hover:text-gray-700"
                    >
                      <ArrowPathIcon className="h-4 w-4 inline mr-1" />
                      Reset to defaults
                    </button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Connection Settings */}
                    <div className="space-y-4">
                      <h5 className="font-medium text-gray-900">Connection Settings</h5>
                      
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={preferences.websocket?.auto_reconnect || true}
                          onChange={(e) => handlePreferenceChange('websocket', 'auto_reconnect', e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Auto-reconnect on disconnect</span>
                      </label>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Reconnect Attempts
                        </label>
                        <select
                          value={preferences.websocket?.reconnect_attempts || 5}
                          onChange={(e) => handlePreferenceChange('websocket', 'reconnect_attempts', parseInt(e.target.value))}
                          className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value={1}>1</option>
                          <option value={3}>3</option>
                          <option value={5}>5</option>
                          <option value={10}>10</option>
                          <option value={-1}>Unlimited</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Reconnect Delay (ms)
                        </label>
                        <select
                          value={preferences.websocket?.reconnect_delay || 3000}
                          onChange={(e) => handlePreferenceChange('websocket', 'reconnect_delay', parseInt(e.target.value))}
                          className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value={1000}>1 second</option>
                          <option value={3000}>3 seconds</option>
                          <option value={5000}>5 seconds</option>
                          <option value={10000}>10 seconds</option>
                        </select>
                      </div>
                    </div>

                    {/* Advanced Settings */}
                    <div className="space-y-4">
                      <h5 className="font-medium text-gray-900">Advanced Settings</h5>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Heartbeat Interval (ms)
                        </label>
                        <select
                          value={preferences.websocket?.heartbeat_interval || 30000}
                          onChange={(e) => handlePreferenceChange('websocket', 'heartbeat_interval', parseInt(e.target.value))}
                          className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value={10000}>10 seconds</option>
                          <option value={30000}>30 seconds</option>
                          <option value={60000}>1 minute</option>
                          <option value={0}>Disabled</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Connection Timeout (ms)
                        </label>
                        <select
                          value={preferences.websocket?.connection_timeout || 10000}
                          onChange={(e) => handlePreferenceChange('websocket', 'connection_timeout', parseInt(e.target.value))}
                          className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value={5000}>5 seconds</option>
                          <option value={10000}>10 seconds</option>
                          <option value={15000}>15 seconds</option>
                          <option value={30000}>30 seconds</option>
                        </select>
                      </div>

                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={preferences.websocket?.enable_compression || false}
                          onChange={(e) => handlePreferenceChange('websocket', 'enable_compression', e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Enable compression (experimental)</span>
                      </label>
                    </div>
                  </div>
                </div>
              )}

              {/* Performance Settings */}
              {activeTab === 'performance' && (
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <h4 className="text-lg font-medium text-gray-900">Performance</h4>
                    <button
                      onClick={() => handleResetCategory('performance')}
                      className="text-sm text-gray-500 hover:text-gray-700"
                    >
                      <ArrowPathIcon className="h-4 w-4 inline mr-1" />
                      Reset to defaults
                    </button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Analysis Settings */}
                    <div className="space-y-4">
                      <h5 className="font-medium text-gray-900">Analysis Settings</h5>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Max Concurrent Analyses
                        </label>
                        <select
                          value={preferences.performance?.max_concurrent_analyses || 3}
                          onChange={(e) => handlePreferenceChange('performance', 'max_concurrent_analyses', parseInt(e.target.value))}
                          className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value={1}>1</option>
                          <option value={2}>2</option>
                          <option value={3}>3</option>
                          <option value={5}>5</option>
                          <option value={10}>10</option>
                        </select>
                      </div>

                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={preferences.performance?.enable_background_processing || true}
                          onChange={(e) => handlePreferenceChange('performance', 'enable_background_processing', e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Enable background processing</span>
                      </label>

                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={preferences.performance?.auto_retry_failed || true}
                          onChange={(e) => handlePreferenceChange('performance', 'auto_retry_failed', e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Auto-retry failed requests</span>
                      </label>
                    </div>

                    {/* Caching Settings */}
                    <div className="space-y-4">
                      <h5 className="font-medium text-gray-900">Caching Settings</h5>
                      
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={preferences.performance?.enable_caching || true}
                          onChange={(e) => handlePreferenceChange('performance', 'enable_caching', e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Enable caching</span>
                      </label>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Cache Duration
                        </label>
                        <select
                          value={Math.floor((preferences.performance?.cache_duration || 3600) / 3600)}
                          onChange={(e) => handlePreferenceChange('performance', 'cache_duration', parseInt(e.target.value) * 3600)}
                          className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value={1}>1 hour</option>
                          <option value={6}>6 hours</option>
                          <option value={12}>12 hours</option>
                          <option value={24}>24 hours</option>
                          <option value={72}>3 days</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Retry Attempts
                        </label>
                        <select
                          value={preferences.performance?.retry_attempts || 3}
                          onChange={(e) => handlePreferenceChange('performance', 'retry_attempts', parseInt(e.target.value))}
                          className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value={1}>1</option>
                          <option value={2}>2</option>
                          <option value={3}>3</option>
                          <option value={5}>5</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex items-center justify-between">
            <div className="text-sm text-gray-500">
              Settings are automatically saved to your browser's local storage
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={!hasUnsavedChanges}
                className={`px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
                  hasUnsavedChanges
                    ? 'bg-blue-600 hover:bg-blue-700'
                    : 'bg-gray-400 cursor-not-allowed'
                }`}
              >
                <CheckIcon className="h-4 w-4 inline mr-1" />
                Save Settings
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProgressSettings;