/**
 * API Service for KDP Strategist Frontend
 * 
 * This module provides a centralized interface for all API calls
 * to the FastAPI backend, including error handling and request/response formatting.
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class ApiService {
  constructor() {
    this.baseURL = API_BASE_URL;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
  }

  /**
   * Make a generic API request
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: { ...this.defaultHeaders, ...options.headers },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({
          detail: `HTTP ${response.status}: ${response.statusText}`
        }));
        throw new Error(errorData.detail || 'API request failed');
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error);
      throw error;
    }
  }

  /**
   * GET request
   */
  async get(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = queryString ? `${endpoint}?${queryString}` : endpoint;
    
    return this.request(url, {
      method: 'GET',
    });
  }

  /**
   * POST request
   */
  async post(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * PUT request
   */
  async put(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  /**
   * DELETE request
   */
  async delete(endpoint) {
    return this.request(endpoint, {
      method: 'DELETE',
    });
  }

  // Health Check
  async checkHealth() {
    return this.get('/health');
  }

  // Niche Discovery APIs
  async discoverNiches(keywords, options = {}) {
    const requestData = {
      keywords: Array.isArray(keywords) ? keywords : [keywords],
      max_results: options.maxResults || 20,
      min_search_volume: options.minSearchVolume || 1000,
      max_competition: options.maxCompetition || 0.7,
      include_seasonal: options.includeSeasonal || true,
      include_charts: options.includeCharts !== false,
      ...options
    };
    
    return this.post('/api/niches/discover', requestData);
  }

  async getTrendingNiches(options = {}) {
    return this.get('/api/niches/trending', {
      timeframe: options.timeframe || '30d',
      category: options.category || 'all',
      min_growth_rate: options.minGrowthRate || 0.1
    });
  }

  // Competitor Analysis APIs
  async analyzeCompetitors(asins, options = {}) {
    const requestData = {
      asins: Array.isArray(asins) ? asins : [asins],
      include_pricing: options.includePricing !== false,
      include_reviews: options.includeReviews !== false,
      include_keywords: options.includeKeywords !== false,
      include_charts: options.includeCharts !== false,
      analysis_depth: options.analysisDepth || 'standard',
      ...options
    };
    
    return this.post('/api/competitors/analyze', requestData);
  }

  async searchCompetitors(keyword, options = {}) {
    return this.get('/api/competitors/search', {
      keyword,
      max_results: options.maxResults || 50,
      min_reviews: options.minReviews || 10,
      max_price: options.maxPrice,
      sort_by: options.sortBy || 'relevance'
    });
  }

  async getMarketOverview(niche, options = {}) {
    return this.get('/api/competitors/market-overview', {
      niche,
      timeframe: options.timeframe || '90d',
      include_forecasts: options.includeForecasts !== false
    });
  }

  // Listing Generation APIs
  async generateListing(niche, options = {}) {
    const requestData = {
      niche,
      target_keywords: options.targetKeywords || [],
      style_preferences: options.stylePreferences || {},
      compliance_level: options.complianceLevel || 'strict',
      include_seo_analysis: options.includeSeoAnalysis !== false,
      include_variations: options.includeVariations !== false,
      ...options
    };
    
    return this.post('/api/listings/generate', requestData);
  }

  async optimizeListing(listingData, options = {}) {
    const requestData = {
      current_listing: listingData,
      optimization_goals: options.optimizationGoals || ['seo', 'conversion'],
      target_keywords: options.targetKeywords || [],
      competitor_analysis: options.competitorAnalysis || false,
      ...options
    };
    
    return this.post('/api/listings/optimize', requestData);
  }

  async getListingTemplates(category = 'all') {
    return this.get('/api/listings/templates', { category });
  }

  async checkCompliance(listingData) {
    return this.post('/api/listings/compliance-check', {
      listing_data: listingData
    });
  }

  // Trend Validation APIs
  async validateTrends(keywords, options = {}) {
    const requestData = {
      keywords: Array.isArray(keywords) ? keywords : [keywords],
      timeframe: options.timeframe || '12m',
      include_forecasts: options.includeForecasts !== false,
      include_seasonal: options.includeSeasonal !== false,
      include_charts: options.includeCharts !== false,
      analysis_depth: options.analysisDepth || 'comprehensive',
      ...options
    };
    
    return this.post('/api/trends/validate', requestData);
  }

  async getTrendingKeywords(options = {}) {
    return this.get('/api/trends/trending-keywords', {
      category: options.category || 'all',
      timeframe: options.timeframe || '7d',
      min_growth_rate: options.minGrowthRate || 0.2,
      region: options.region || 'US'
    });
  }

  async forecastTrend(keyword, options = {}) {
    return this.get(`/api/trends/forecast/${encodeURIComponent(keyword)}`, {
      forecast_period: options.forecastPeriod || '6m',
      confidence_level: options.confidenceLevel || 0.8,
      include_scenarios: options.includeScenarios !== false
    });
  }

  async getSeasonalPatterns(keywords, options = {}) {
    const requestData = {
      keywords: Array.isArray(keywords) ? keywords : [keywords],
      years_back: options.yearsBack || 3,
      include_predictions: options.includePredictions !== false
    };
    
    return this.post('/api/trends/seasonal-patterns', requestData);
  }

  // Stress Testing APIs
  async runStressTest(niche, options = {}) {
    const requestData = {
      niche,
      test_scenarios: options.testScenarios || [
        'market_saturation',
        'seasonal_decline',
        'trend_reversal',
        'competition_increase'
      ],
      severity_level: options.severityLevel || 'moderate',
      include_recommendations: options.includeRecommendations !== false,
      ...options
    };
    
    return this.post('/api/stress/run', requestData);
  }

  async getAvailableScenarios() {
    return this.get('/api/stress/scenarios');
  }

  async getRiskMatrix() {
    return this.get('/api/stress/risk-matrix');
  }

  async compareNiches(niches, scenarios = null) {
    const requestData = {
      niches: Array.isArray(niches) ? niches : [niches],
      scenarios: scenarios
    };
    
    return this.post('/api/stress/compare', requestData);
  }

  // Export functionality
  async exportData(data, format = 'csv', options = {}) {
    const requestData = {
      data,
      format,
      filename: options.filename,
      include_metadata: options.includeMetadata !== false,
      ...options
    };
    
    const response = await this.request('/api/export', {
      method: 'POST',
      body: JSON.stringify(requestData),
      headers: {
        ...this.defaultHeaders,
        'Accept': format === 'pdf' ? 'application/pdf' : 'application/octet-stream'
      }
    });

    return response;
  }

  // WebSocket connection for real-time updates
  createWebSocket(onMessage, onError = null, onClose = null) {
    const wsUrl = this.baseURL.replace('http', 'ws') + '/ws';
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (onError) onError(error);
    };
    
    ws.onclose = (event) => {
      console.log('WebSocket connection closed:', event.code, event.reason);
      if (onClose) onClose(event);
    };
    
    return ws;
  }

  // Utility methods
  formatError(error) {
    if (error.response && error.response.data) {
      return error.response.data.detail || error.response.data.message || 'An error occurred';
    }
    return error.message || 'An unexpected error occurred';
  }

  isNetworkError(error) {
    return error.message.includes('fetch') || error.message.includes('Network');
  }

  // Cache management (simple in-memory cache)
  cache = new Map();
  
  getCached(key) {
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < 300000) { // 5 minutes
      return cached.data;
    }
    return null;
  }
  
  setCache(key, data) {
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    });
  }
  
  clearCache() {
    this.cache.clear();
  }
}

// Create and export a singleton instance
export const apiService = new ApiService();
export default apiService;