import { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';

/**
 * Hook for managing user preferences with localStorage persistence
 */
export const useUserPreferences = () => {
  const [preferences, setPreferences] = useState({
    // Analysis preferences
    analysis: {
      auto_save_results: true,
      show_progress_notifications: true,
      default_max_results: 20,
      enable_real_time_updates: true,
      auto_export_completed: false,
      preferred_export_format: 'csv'
    },
    
    // UI preferences
    ui: {
      theme: 'light',
      results_per_page: 20,
      show_advanced_options: false,
      compact_view: false,
      enable_animations: true,
      sidebar_collapsed: false
    },
    
    // Notification preferences
    notifications: {
      browser_notifications: true,
      analysis_complete: true,
      error_alerts: true,
      progress_updates: false,
      sound_enabled: false,
      email_alerts: false
    },
    
    // Progress and WebSocket preferences
    progress: {
      show_floating_indicator: true,
      show_dashboard: true,
      auto_minimize_completed: true,
      show_detailed_steps: true,
      enable_progress_sounds: false,
      progress_update_interval: 1000, // milliseconds
      show_time_estimates: true,
      show_cancellation_controls: true
    },
    
    // WebSocket preferences
    websocket: {
      auto_reconnect: true,
      reconnect_attempts: 5,
      reconnect_delay: 3000,
      heartbeat_interval: 30000,
      connection_timeout: 10000,
      enable_compression: false,
      fallback_to_polling: true,
      max_reconnect_delay: 30000,
      exponential_backoff: true
    },
    
    // Performance preferences
    performance: {
      enable_caching: true,
      cache_duration: 3600, // 1 hour in seconds
      max_concurrent_analyses: 3,
      enable_background_processing: true,
      auto_retry_failed: true,
      retry_attempts: 3
    },
    
    // Privacy preferences
    privacy: {
      save_search_history: true,
      share_usage_analytics: false,
      remember_api_settings: true,
      auto_clear_sensitive_data: false
    }
  });

  const [isLoading, setIsLoading] = useState(true);
  const [lastSaved, setLastSaved] = useState(null);

  // Helper function to apply theme
  const applyTheme = useCallback((theme) => {
    const root = document.documentElement;
    
    if (theme === 'dark') {
      root.classList.add('dark');
    } else if (theme === 'light') {
      root.classList.remove('dark');
    } else if (theme === 'auto') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (prefersDark) {
        root.classList.add('dark');
      } else {
        root.classList.remove('dark');
      }
    }
  }, []);

  const loadPreferences = useCallback(() => {
    try {
      const saved = localStorage.getItem('kdp_strategist_preferences');
      if (saved) {
        const parsed = JSON.parse(saved);
        setPreferences(prev => ({
          ...prev,
          ...parsed,
          // Ensure nested objects are properly merged
          analysis: { ...prev.analysis, ...(parsed.analysis || {}) },
          ui: { ...prev.ui, ...(parsed.ui || {}) },
          notifications: { ...prev.notifications, ...(parsed.notifications || {}) },
          progress: { ...prev.progress, ...(parsed.progress || {}) },
          websocket: { ...prev.websocket, ...(parsed.websocket || {}) },
          performance: { ...prev.performance, ...(parsed.performance || {}) },
          privacy: { ...prev.privacy, ...(parsed.privacy || {}) }
        }));
      }
    } catch (error) {
      console.error('Error loading preferences:', error);
      toast.error('Failed to load user preferences');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Load preferences from localStorage on mount
  useEffect(() => {
    loadPreferences();
  }, [loadPreferences]);

  const savePreferences = useCallback(async (newPreferences = null) => {
    try {
      const toSave = newPreferences || preferences;
      localStorage.setItem('kdp_strategist_preferences', JSON.stringify(toSave));
      setLastSaved(new Date().toISOString());
      
      // Apply theme immediately if changed
      if (toSave.ui?.theme) {
        applyTheme(toSave.ui.theme);
      }
      
      // Request notification permission if enabled
      if (toSave.notifications?.browser_notifications && 'Notification' in window) {
        if (Notification.permission === 'default') {
          await Notification.requestPermission();
        }
      }
      
      return { success: true };
    } catch (error) {
      console.error('Error saving preferences:', error);
      toast.error('Failed to save preferences');
      return { success: false, error: error.message };
    }
  }, [preferences, applyTheme]);

  const updatePreference = useCallback((category, key, value) => {
    setPreferences(prev => {
      const updated = {
        ...prev,
        [category]: {
          ...prev[category],
          [key]: value
        }
      };
      
      // Auto-save after update
      setTimeout(() => savePreferences(updated), 100);
      
      return updated;
    });
  }, [savePreferences]);

  const updatePreferences = useCallback((updates) => {
    setPreferences(prev => {
      const updated = { ...prev };
      
      Object.entries(updates).forEach(([category, categoryUpdates]) => {
        if (typeof categoryUpdates === 'object' && categoryUpdates !== null) {
          updated[category] = {
            ...prev[category],
            ...categoryUpdates
          };
        }
      });
      
      // Auto-save after update
      setTimeout(() => savePreferences(updated), 100);
      
      return updated;
    });
  }, [savePreferences]);

  const resetPreferences = useCallback((category = null) => {
    const defaultPrefs = {
      analysis: {
        auto_save_results: true,
        show_progress_notifications: true,
        default_max_results: 20,
        enable_real_time_updates: true,
        auto_export_completed: false,
        preferred_export_format: 'csv'
      },
      ui: {
        theme: 'light',
        results_per_page: 20,
        show_advanced_options: false,
        compact_view: false,
        enable_animations: true,
        sidebar_collapsed: false
      },
      notifications: {
        browser_notifications: true,
        analysis_complete: true,
        error_alerts: true,
        progress_updates: false,
        sound_enabled: false,
        email_alerts: false
      },
      progress: {
        show_floating_indicator: true,
        show_dashboard: true,
        auto_minimize_completed: true,
        show_detailed_steps: true,
        enable_progress_sounds: false,
        progress_update_interval: 1000,
        show_time_estimates: true,
        show_cancellation_controls: true
      },
      websocket: {
        auto_reconnect: true,
        reconnect_attempts: 5,
        reconnect_delay: 3000,
        heartbeat_interval: 30000,
        connection_timeout: 10000,
        enable_compression: false
      },
      performance: {
        enable_caching: true,
        cache_duration: 3600,
        max_concurrent_analyses: 3,
        enable_background_processing: true,
        auto_retry_failed: true,
        retry_attempts: 3
      },
      privacy: {
        save_search_history: true,
        share_usage_analytics: false,
        remember_api_settings: true,
        auto_clear_sensitive_data: false
      }
    };

    if (category) {
      setPreferences(prev => ({
        ...prev,
        [category]: defaultPrefs[category]
      }));
    } else {
      setPreferences(defaultPrefs);
    }
    
    savePreferences(category ? { ...preferences, [category]: defaultPrefs[category] } : defaultPrefs);
    toast.success(category ? `${category} preferences reset` : 'All preferences reset to defaults');
  }, [preferences, savePreferences]);

  const exportPreferences = useCallback(() => {
    try {
      const dataStr = JSON.stringify(preferences, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      
      const link = document.createElement('a');
      link.href = url;
      link.download = `kdp-strategist-preferences-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      URL.revokeObjectURL(url);
      toast.success('Preferences exported successfully');
    } catch (error) {
      console.error('Error exporting preferences:', error);
      toast.error('Failed to export preferences');
    }
  }, [preferences]);

  const importPreferences = useCallback((file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = (e) => {
        try {
          const imported = JSON.parse(e.target.result);
          
          // Validate structure
          const requiredCategories = ['analysis', 'ui', 'notifications', 'performance', 'privacy'];
          const hasValidStructure = requiredCategories.every(cat => 
            imported[cat] && typeof imported[cat] === 'object'
          );
          
          if (!hasValidStructure) {
            throw new Error('Invalid preferences file structure');
          }
          
          setPreferences(imported);
          savePreferences(imported);
          toast.success('Preferences imported successfully');
          resolve(imported);
        } catch (error) {
          console.error('Error importing preferences:', error);
          toast.error('Failed to import preferences: Invalid file format');
          reject(error);
        }
      };
      
      reader.onerror = () => {
        const error = new Error('Failed to read preferences file');
        toast.error('Failed to read preferences file');
        reject(error);
      };
      
      reader.readAsText(file);
    });
  }, [savePreferences]);

  const getPreference = useCallback((category, key, defaultValue = null) => {
    return preferences[category]?.[key] ?? defaultValue;
  }, [preferences]);

  const hasPreference = useCallback((category, key) => {
    return preferences[category]?.[key] !== undefined;
  }, [preferences]);

  // Apply theme on preferences change
  useEffect(() => {
    if (preferences.ui?.theme) {
      applyTheme(preferences.ui.theme);
    }
  }, [preferences.ui?.theme, applyTheme]);

  // Set up auto-save interval for preferences
  useEffect(() => {
    const interval = setInterval(() => {
      if (lastSaved) {
        const timeSinceLastSave = Date.now() - new Date(lastSaved).getTime();
        if (timeSinceLastSave > 300000) { // 5 minutes
          savePreferences();
        }
      }
    }, 60000); // Check every minute

    return () => clearInterval(interval);
  }, [lastSaved, savePreferences]);

  return {
    preferences,
    isLoading,
    lastSaved,
    updatePreference,
    updatePreferences,
    savePreferences,
    resetPreferences,
    exportPreferences,
    importPreferences,
    getPreference,
    hasPreference,
    loadPreferences
  };
};

/**
 * Hook for managing analysis session preferences
 */
export const useAnalysisPreferences = () => {
  const { preferences, updatePreference, getPreference } = useUserPreferences();

  const getAnalysisDefaults = useCallback(() => ({
    maxResults: getPreference('analysis', 'default_max_results', 20),
    autoSave: getPreference('analysis', 'auto_save_results', true),
    realTimeUpdates: getPreference('analysis', 'enable_real_time_updates', true),
    exportFormat: getPreference('analysis', 'preferred_export_format', 'csv'),
    showNotifications: getPreference('analysis', 'show_progress_notifications', true)
  }), [getPreference]);

  const updateAnalysisPreference = useCallback((key, value) => {
    updatePreference('analysis', key, value);
  }, [updatePreference]);

  return {
    analysisPreferences: preferences.analysis,
    getAnalysisDefaults,
    updateAnalysisPreference
  };
};

export default useUserPreferences;