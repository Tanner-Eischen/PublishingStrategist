/**
 * Enhanced API service with WebSocket integration and progress tracking
 */

import axios from 'axios';
import { toast } from 'react-toastify';

class ApiService {
  constructor() {
    this.baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    this.clientId = null;
    this.requestInterceptors = [];
    this.responseInterceptors = [];
    
    // Create axios instance
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  setupInterceptors() {
    // Request interceptor to add client ID
    this.client.interceptors.request.use(
      (config) => {
        if (this.clientId) {
          config.headers['X-Client-ID'] = this.clientId;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        this.handleApiError(error);
        return Promise.reject(error);
      }
    );
  }

  setClientId(clientId) {
    this.clientId = clientId;
  }

  handleApiError(error) {
    if (error.response) {
      const { status, data } = error.response;
      
      switch (status) {
        case 400:
          toast.error(data.detail || 'Invalid request');
          break;
        case 401:
          toast.error('Authentication required');
          break;
        case 403:
          toast.error('Access forbidden');
          break;
        case 404:
          toast.error('Resource not found');
          break;
        case 429:
          toast.warning('Rate limit exceeded. Please try again later.');
          break;
        case 500:
          toast.error('Server error. Please try again.');
          break;
        default:
          toast.error(data.detail || 'An error occurred');
      }
    } else if (error.request) {
      toast.error('Network error. Please check your connection.');
    } else {
      toast.error('Request failed. Please try again.');
    }
  }

  /**
   * Generic GET request method
   * @param {string} url - The URL to make the GET request to
   * @param {Object} config - Optional axios config
   * @returns {Promise<Object>} Response data
   */
  async get(url, config = {}) {
    try {
      const response = await this.client.get(url, config);
      return response.data;
    } catch (error) {
      console.error(`GET request failed for ${url}:`, error);
      throw error;
    }
  }

  /**
   * Check if an error is a network-related error
   * @param {Error} error - The error to check
   * @returns {boolean} True if it's a network error
   */
  isNetworkError(error) {
    // Check for network-related errors that should trigger retry logic
    if (error.code === 'NETWORK_ERROR' || error.code === 'ECONNREFUSED') {
      return true;
    }
    
    // Check if request was made but no response received (network timeout/connection issues)
    if (error.request && !error.response) {
      return true;
    }
    
    // Check for specific HTTP status codes that indicate temporary network issues
    if (error.response) {
      const status = error.response.status;
      // 502 Bad Gateway, 503 Service Unavailable, 504 Gateway Timeout
      return status === 502 || status === 503 || status === 504;
    }
    
    return false;
  }

  /**
   * Format error for user-friendly display
   * @param {Error} error - The error to format
   * @returns {string} Formatted error message
   */
  formatError(error) {
    if (error.response) {
      // Server responded with error status
      const status = error.response.status;
      const message = error.response.data?.message || error.response.data?.detail || error.message;
      return `Error ${status}: ${message}`;
    } else if (error.request) {
      // Request was made but no response received
      return 'Network error: Unable to connect to server';
    } else {
      // Something else happened
      return error.message || 'An unexpected error occurred';
    }
  }

  // Health check endpoints
  async healthCheck() {
    const response = await this.client.get('/api/health');
    return response.data;
  }

  async detailedHealthCheck() {
    const response = await this.client.get('/api/health/detailed');
    return response.data;
  }

  // Settings and preferences endpoints
  async getUserPreferences() {
    const response = await this.client.get('/api/settings/preferences');
    return response.data;
  }

  async updateUserPreferences(preferences) {
    const response = await this.client.put('/api/settings/preferences', preferences);
    return response.data;
  }

  async updatePreferenceCategory(category, updates) {
    const response = await this.client.patch(`/api/settings/preferences/${category}`, updates);
    return response.data;
  }

  async bulkUpdatePreferences(updates) {
    const response = await this.client.patch('/api/settings/preferences', { preferences: updates });
    return response.data;
  }

  async resetPreferences(category = null) {
    const url = category ? `/api/settings/preferences/${category}` : '/api/settings/preferences';
    const response = await this.client.delete(url);
    return response.data;
  }

  async exportPreferences() {
    const response = await this.client.get('/api/settings/preferences/export');
    return response.data;
  }

  async importPreferences(preferencesData) {
    const response = await this.client.post('/api/settings/preferences/import', preferencesData);
    return response.data;
  }

  async getWebSocketStatus() {
    const response = await this.client.get('/api/settings/websocket/status');
    return response.data;
  }

  async getSystemInfo() {
    const response = await this.client.get('/api/settings/system/info');
    return response.data;
  }

  // Niche discovery endpoints
  async discoverNiches(keywords, options = {}) {
    // Create a custom axios instance with longer timeout for niche discovery
    const nicheClient = axios.create({
      baseURL: this.baseURL,
      timeout: 120000, // 2 minutes timeout for niche discovery
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    // Add client ID header if available
    if (this.clientId) {
      nicheClient.defaults.headers['X-Client-ID'] = this.clientId;
    }
    
    try {
      const response = await nicheClient.post('/api/niches/discover', {
        base_keywords: keywords,
        ...options
      });
      return response.data;
    } catch (error) {
      // Handle timeout errors specifically
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        throw new Error('Niche discovery is taking longer than expected. This may be due to high API usage. Please try again with fewer keywords or try again later.');
      }
      throw error;
    }
  }

  async getTrendingNiches(options = {}) {
    const response = await this.client.get('/api/niches/trending', { params: options });
    return response.data;
  }

  // Trend validation endpoints
  async validateTrend(keyword, options = {}) {
    const response = await this.client.post('/api/trends/validate', {
      keywords: Array.isArray(keyword) ? keyword : [keyword],
      ...options
    });
    return response.data;
  }

  async getTrendForecast(keyword, options = {}) {
    const response = await this.client.post('/api/trends/forecast', {
      keyword,
      ...options
    });
    return response.data;
  }

  async compareTrends(keywords, options = {}) {
    const response = await this.client.post('/api/trends/compare', {
      keywords,
      ...options
    });
    return response.data;
  }

  // Competitor analysis endpoints
  async analyzeCompetitors(niche, options = {}) {
    const response = await this.client.post('/api/competitors/analyze', {
      niche,
      ...options
    });
    return response.data;
  }

  async getCompetitorDetails(asin) {
    const response = await this.client.get(`/api/competitors/${asin}`);
    return response.data;
  }

  // Listing generation endpoints
  async generateListing(niche, options = {}) {
    const response = await this.client.post('/api/listings/generate', {
      niche,
      ...options
    });
    return response.data;
  }

  async optimizeListing(listing, options = {}) {
    const response = await this.client.post('/api/listings/optimize', {
      listing,
      ...options
    });
    return response.data;
  }

  // Stress testing endpoints
  async stressTestNiche(niche, scenarios = []) {
    const response = await this.client.post('/api/stress/test', {
      niche,
      scenarios
    });
    return response.data;
  }

  // Analysis management with progress tracking
  async startAnalysisWithProgress(analysisType, parameters, onProgress = null, onComplete = null, onError = null) {
    // Generate unique analysis ID
    const analysisId = `${analysisType}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // Start the analysis via WebSocket if available
    if (window.wsConnection && window.wsConnection.readyState === WebSocket.OPEN) {
      window.wsConnection.send(JSON.stringify({
        type: 'start_analysis',
        analysis_id: analysisId,
        analysis_type: analysisType,
        parameters
      }));

      // Set up progress tracking
      if (onProgress || onComplete || onError) {
        this.setupAnalysisTracking(analysisId, onProgress, onComplete, onError);
      }

      return { analysisId, status: 'started' };
    } else {
      // Fallback to direct API call
      return await this.executeAnalysisDirectly(analysisType, parameters);
    }
  }

  setupAnalysisTracking(analysisId, onProgress, onComplete, onError) {
    const handleMessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        
        if (message.analysis_id === analysisId) {
          switch (message.type) {
            case 'analysis_progress':
              if (onProgress) {
                onProgress({
                  analysisId,
                  progress: message.progress,
                  step: message.step,
                  status: message.status,
                  estimatedTime: message.estimated_time
                });
              }
              break;
              
            case 'analysis_complete':
              if (onComplete) {
                onComplete({
                  analysisId,
                  results: message.results,
                  executionTime: message.execution_time
                });
              }
              // Remove listener
              window.wsConnection.removeEventListener('message', handleMessage);
              break;
              
            case 'analysis_error':
              if (onError) {
                onError({
                  analysisId,
                  error: message.error
                });
              }
              // Remove listener
              window.wsConnection.removeEventListener('message', handleMessage);
              break;
              
            default:
              // Handle unknown message types
              console.log('Unknown message type:', message.type);
              break;
          }
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    if (window.wsConnection) {
      window.wsConnection.addEventListener('message', handleMessage);
    }
  }

  async executeAnalysisDirectly(analysisType, parameters) {
    // Direct API calls without WebSocket progress tracking
    switch (analysisType) {
      case 'niche_discovery':
        return await this.discoverNiches(parameters.keywords, parameters);
      case 'trend_validation':
        return await this.validateTrend(parameters.keyword, parameters);
      case 'competitor_analysis':
        return await this.analyzeCompetitors(parameters.niche, parameters);
      case 'listing_generation':
        return await this.generateListing(parameters.niche, parameters);
      default:
        throw new Error(`Unknown analysis type: ${analysisType}`);
    }
  }

  async cancelAnalysis(analysisId) {
    if (window.wsConnection && window.wsConnection.readyState === WebSocket.OPEN) {
      window.wsConnection.send(JSON.stringify({
        type: 'cancel_analysis',
        analysis_id: analysisId
      }));
      return { success: true };
    }
    return { success: false, error: 'WebSocket not connected' };
  }

  async pauseAnalysis(analysisId) {
    if (window.wsConnection && window.wsConnection.readyState === WebSocket.OPEN) {
      window.wsConnection.send(JSON.stringify({
        type: 'pause_analysis',
        analysis_id: analysisId
      }));
      return { success: true };
    }
    return { success: false, error: 'WebSocket not connected' };
  }

  async resumeAnalysis(analysisId) {
    if (window.wsConnection && window.wsConnection.readyState === WebSocket.OPEN) {
      window.wsConnection.send(JSON.stringify({
        type: 'resume_analysis',
        analysis_id: analysisId
      }));
      return { success: true };
    }
    return { success: false, error: 'WebSocket not connected' };
  }

  // Utility methods
  async downloadFile(url, filename) {
    try {
      const response = await this.client.get(url, { responseType: 'blob' });
      const blob = new Blob([response.data]);
      const downloadUrl = window.URL.createObjectURL(blob);
      
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      window.URL.revokeObjectURL(downloadUrl);
      return { success: true };
    } catch (error) {
      console.error('Download failed:', error);
      return { success: false, error: error.message };
    }
  }

  async uploadFile(file, endpoint) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await this.client.post(endpoint, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  }

  // Request retry with exponential backoff
  async retryRequest(requestFn, maxRetries = 3, baseDelay = 1000) {
    let lastError;
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await requestFn();
      } catch (error) {
        lastError = error;
        
        if (attempt === maxRetries) {
          break;
        }
        
        // Don't retry on client errors (4xx)
        if (error.response && error.response.status >= 400 && error.response.status < 500) {
          break;
        }
        
        // Exponential backoff
        const delay = baseDelay * Math.pow(2, attempt);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
    
    throw lastError;
  }

  // Batch requests with concurrency control
  async batchRequests(requests, concurrency = 3) {
    const results = [];
    const executing = [];
    
    for (const request of requests) {
      const promise = request().then(result => {
        executing.splice(executing.indexOf(promise), 1);
        return result;
      });
      
      results.push(promise);
      executing.push(promise);
      
      if (executing.length >= concurrency) {
        await Promise.race(executing);
      }
    }
    
    return Promise.all(results);
  }
}

// Create singleton instance
export const apiService = new ApiService();

// Export individual methods for convenience
export const {
  healthCheck,
  detailedHealthCheck,
  getUserPreferences,
  updateUserPreferences,
  updatePreferenceCategory,
  bulkUpdatePreferences,
  resetPreferences,
  exportPreferences,
  importPreferences,
  getWebSocketStatus,
  getSystemInfo,
  discoverNiches,
  getTrendingNiches,
  validateTrend,
  getTrendForecast,
  compareTrends,
  analyzeCompetitors,
  getCompetitorDetails,
  generateListing,
  optimizeListing,
  stressTestNiche,
  startAnalysisWithProgress,
  cancelAnalysis,
  pauseAnalysis,
  resumeAnalysis,
  downloadFile,
  uploadFile
} = apiService;

export default apiService;