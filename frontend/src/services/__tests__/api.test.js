import axios from 'axios';
import { apiService } from '../api';

// Mock axios
jest.mock('axios', () => ({
  create: jest.fn(() => ({
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() }
    }
  }))
}));

// Mock toast notifications
jest.mock('react-toastify', () => ({
  toast: {
    error: jest.fn(),
    warning: jest.fn(),
    success: jest.fn(),
    info: jest.fn()
  }
}));

describe('API Service', () => {
  let mockAxios;
  
  beforeEach(() => {
    jest.clearAllMocks();
    mockAxios = axios.create();
  });
  
  test('discoverNiches calls the correct endpoint with parameters', async () => {
    const mockResponse = { data: { niches: [], total_analyzed: 0 } };
    mockAxios.post.mockResolvedValueOnce(mockResponse);
    
    const keywords = ['productivity', 'journal'];
    const options = { max_niches: 5, target_audience: 'professionals' };
    
    await apiService.discoverNiches(keywords, options);
    
    expect(mockAxios.post).toHaveBeenCalledWith('/api/niches/discover', {
      base_keywords: keywords,
      max_niches: 5,
      target_audience: 'professionals'
    });
  });
  
  test('validateTrend calls the correct endpoint with parameters', async () => {
    const mockResponse = { data: { trend_data: {}, related_keywords: [] } };
    mockAxios.post.mockResolvedValueOnce(mockResponse);
    
    const keyword = 'productivity journal';
    const options = { timeframe: '12m', include_forecast: true };
    
    await apiService.validateTrend(keyword, options);
    
    expect(mockAxios.post).toHaveBeenCalledWith('/api/trends/validate', {
      keywords: [keyword],
      timeframe: '12m',
      include_forecast: true
    });
  });
  
  test('analyzeCompetitors calls the correct endpoint with parameters', async () => {
    const mockResponse = { data: { competitors: [], market_analysis: {} } };
    mockAxios.post.mockResolvedValueOnce(mockResponse);
    
    const niche = 'productivity journal';
    const options = { max_competitors: 10 };
    
    await apiService.analyzeCompetitors(niche, options);
    
    expect(mockAxios.post).toHaveBeenCalledWith('/api/competitors/analyze', {
      niche: 'productivity journal',
      max_competitors: 10
    });
  });
  
  test('generateListing calls the correct endpoint with parameters', async () => {
    const mockResponse = { data: { listing: {}, optimization_suggestions: [] } };
    mockAxios.post.mockResolvedValueOnce(mockResponse);
    
    const niche = 'productivity journal';
    const options = { target_audience: 'professionals', book_type: 'journal' };
    
    await apiService.generateListing(niche, options);
    
    expect(mockAxios.post).toHaveBeenCalledWith('/api/listings/generate', {
      niche: 'productivity journal',
      target_audience: 'professionals',
      book_type: 'journal'
    });
  });
  
  test('handles API errors correctly', async () => {
    const errorResponse = {
      response: {
        status: 429,
        data: { detail: 'Rate limit exceeded' }
      }
    };
    mockAxios.post.mockRejectedValueOnce(errorResponse);
    
    await expect(apiService.discoverNiches(['test'])).rejects.toEqual(errorResponse);
    
    expect(require('react-toastify').toast.warning).toHaveBeenCalledWith('Rate limit exceeded. Please try again later.');
  });
  
  test('handles network errors correctly', async () => {
    const networkError = { request: {}, message: 'Network Error' };
    mockAxios.post.mockRejectedValueOnce(networkError);
    
    await expect(apiService.discoverNiches(['test'])).rejects.toEqual(networkError);
    
    expect(require('react-toastify').toast.error).toHaveBeenCalledWith('Network error. Please check your connection.');
  });
  
  test('startAnalysisWithProgress uses WebSocket when available', async () => {
    // Mock WebSocket
    global.WebSocket = {
      OPEN: 1
    };
    
    window.wsConnection = {
      readyState: 1,
      send: jest.fn()
    };
    
    const analysisType = 'niche_discovery';
    const parameters = { base_keywords: ['test'] };
    const onProgress = jest.fn();
    const onComplete = jest.fn();
    
    const result = await apiService.startAnalysisWithProgress(
      analysisType,
      parameters,
      onProgress,
      onComplete
    );
    
    expect(result.status).toBe('started');
    expect(window.wsConnection.send).toHaveBeenCalledWith(
      expect.stringContaining('"type":"start_analysis"')
    );
    
    // Clean up
    delete window.wsConnection;
    delete global.WebSocket;
  });
  
  test('startAnalysisWithProgress falls back to direct API call when WebSocket unavailable', async () => {
    // Mock direct API call
    const mockResponse = { niches: [], total_analyzed: 0 };
    apiService.executeAnalysisDirectly = jest.fn().mockResolvedValueOnce(mockResponse);
    
    // Ensure WebSocket is not available
    window.wsConnection = undefined;
    
    const analysisType = 'niche_discovery';
    const parameters = { base_keywords: ['test'] };
    
    await apiService.startAnalysisWithProgress(analysisType, parameters);
    
    expect(apiService.executeAnalysisDirectly).toHaveBeenCalledWith(
      analysisType,
      parameters
    );
  });
});