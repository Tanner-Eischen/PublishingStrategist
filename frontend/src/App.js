import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

// Components
import Navbar from './components/layout/Navbar';
import Sidebar from './components/layout/Sidebar';
import LoadingSpinner from './components/common/LoadingSpinner';
import ErrorBoundary from './components/common/ErrorBoundary';
import { cn } from './lib/utils';

// Pages
import Dashboard from './pages/Dashboard';
import NicheDiscovery from './pages/NicheDiscovery';
import CompetitorAnalysis from './pages/CompetitorAnalysis';
import ListingGeneration from './pages/ListingGeneration';
import TrendValidation from './pages/TrendValidation';
import StressTesting from './pages/StressTesting';
import Settings from './pages/Settings';

// Services
import { apiService } from './services/api';

// Styles
import './App.css';

// Create API Context
const ApiContext = createContext({
  apiService: null,
  updateApiSettings: () => {},
  isConnected: false,
  refreshConnection: () => {}
});

// Custom hook to use API context
export const useApi = () => {
  const context = useContext(ApiContext);
  if (!context) {
    throw new Error('useApi must be used within an ApiProvider');
  }
  return context;
};

function App() {
  const [isLoading, setIsLoading] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [currentUser, setCurrentUser] = useState(null);
  const [apiSettings, setApiSettings] = useState({ api_key: '', api_endpoint: '' });

  useEffect(() => {
    // Initialize the application
    initializeApp();
  }, []);

  const initializeApp = async () => {
    try {
      setIsLoading(true);
      
      // Load and apply saved API settings
      const savedSettings = localStorage.getItem('kdp_strategist_settings');
      if (savedSettings) {
        try {
          const parsed = JSON.parse(savedSettings);
          const newApiSettings = {
            api_key: parsed.api_key || '',
            api_endpoint: parsed.api_endpoint || ''
          };
          setApiSettings(newApiSettings);
          
          if (parsed.api_key) {
            apiService.setApiKey(parsed.api_key);
          }
          if (parsed.api_endpoint) {
            apiService.setBaseUrl(parsed.api_endpoint);
          }
        } catch (error) {
          console.error('Error loading saved settings:', error);
        }
      }
      
      // Check API health
      const healthCheck = await apiService.checkHealth();
      setIsConnected(healthCheck.status === 'healthy');
      
      // Initialize user session (if needed)
      // For now, we'll use a default user
      setCurrentUser({
        id: 'default',
        name: 'KDP Strategist User',
        preferences: {
          theme: 'light',
          defaultExportFormat: 'csv'
        }
      });
      
    } catch (error) {
      console.error('Failed to initialize app:', error);
      setIsConnected(false);
    } finally {
      setIsLoading(false);
    }
  };

  // Function to update API settings from Settings component
  const updateApiSettings = async (newSettings) => {
    try {
      const { api_key, api_endpoint } = newSettings;
      
      // Update local state
      setApiSettings({ api_key, api_endpoint });
      
      // Apply to apiService
      if (api_key) {
        apiService.setApiKey(api_key);
      } else {
        apiService.setApiKey(null);
      }
      
      if (api_endpoint) {
        apiService.setBaseUrl(api_endpoint);
      }
      
      // Test connection
      const healthCheck = await apiService.checkHealth();
      setIsConnected(healthCheck.status === 'healthy');
      
      return { success: true, connected: healthCheck.status === 'healthy' };
    } catch (error) {
      console.error('Error updating API settings:', error);
      setIsConnected(false);
      return { success: false, error: error.message };
    }
  };

  // Function to refresh connection
  const refreshConnection = async () => {
    try {
      const healthCheck = await apiService.checkHealth();
      setIsConnected(healthCheck.status === 'healthy');
      return healthCheck.status === 'healthy';
    } catch (error) {
      console.error('Connection refresh failed:', error);
      setIsConnected(false);
      return false;
    }
  };

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <LoadingSpinner size="large" message="Initializing KDP Strategist..." />
      </div>
    );
  }

  if (!isConnected) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="mb-4">
            <svg className="mx-auto h-12 w-12 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h3 className="mt-2 text-sm font-medium text-gray-900">Connection Failed</h3>
          <p className="mt-1 text-sm text-gray-500">
            Unable to connect to the KDP Strategist API. Please ensure the backend server is running.
          </p>
          <div className="mt-6">
            <button
              onClick={initializeApp}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Retry Connection
            </button>
          </div>
        </div>
      </div>
    );
  }

  // API Context value
  const apiContextValue = {
    apiService,
    updateApiSettings,
    isConnected,
    refreshConnection,
    apiSettings
  };

  return (
    <ErrorBoundary>
      <ApiContext.Provider value={apiContextValue}>
        <Router>
          <div className="flex min-h-screen bg-gray-50">
            <Sidebar isOpen={sidebarOpen} toggleSidebar={toggleSidebar} />
            <div className={cn("flex flex-col flex-1 transition-all duration-300 ease-in-out", sidebarOpen ? 'ml-64' : 'ml-0')}>
              <Navbar toggleSidebar={toggleSidebar} isSidebarOpen={sidebarOpen} />
              <main className="flex-1 p-6 overflow-auto">
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/niche-discovery" element={<NicheDiscovery />} />
                  <Route path="/competitor-analysis" element={<CompetitorAnalysis />} />
                  <Route path="/listing-generation" element={<ListingGeneration />} />
                  <Route path="/trend-validation" element={<TrendValidation />} />
                  <Route path="/stress-testing" element={<StressTesting />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </main>
            </div>
          </div>
          <ToastContainer position="bottom-right" autoClose={5000} hideProgressBar={false} newestOnTop={false} closeOnClick rtl={false} pauseOnFocusLoss draggable pauseOnHover />
        </Router>
      </ApiContext.Provider>
    </ErrorBoundary>
  );
}

export default App;