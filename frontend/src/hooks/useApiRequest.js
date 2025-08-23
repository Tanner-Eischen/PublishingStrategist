import { useState, useCallback } from 'react';
import { toast } from 'react-toastify';
import { useApi } from '../App';

/**
 * Custom hook for handling API requests with loading states, error handling, and retry logic
 */
export const useApiRequest = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const { apiService } = useApi();

  const execute = useCallback(async (apiCall, options = {}) => {
    const {
      onSuccess,
      onError,
      showSuccessToast = true,
      showErrorToast = true,
      successMessage,
      errorMessage,
      retryCount = 0,
      maxRetries = 2
    } = options;

    setIsLoading(true);
    setError(null);

    try {
      const result = await apiCall();
      setData(result);
      
      if (onSuccess) {
        onSuccess(result);
      }
      
      if (showSuccessToast && successMessage) {
        toast.success(successMessage);
      }
      
      return result;
    } catch (err) {
      const formattedError = apiService.formatError(err);
      setError(formattedError);
      
      // Retry logic for network errors
      if (apiService.isNetworkError(err) && retryCount < maxRetries) {
        console.log(`Retrying API call (attempt ${retryCount + 1}/${maxRetries})`);
        await new Promise(resolve => setTimeout(resolve, 1000 * (retryCount + 1)));
        return execute(apiCall, { ...options, retryCount: retryCount + 1 });
      }
      
      if (onError) {
        onError(formattedError, err);
      }
      
      if (showErrorToast) {
        const message = errorMessage || `Request failed: ${formattedError}`;
        toast.error(message);
      }
      
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [apiService]);

  const reset = useCallback(() => {
    setIsLoading(false);
    setError(null);
    setData(null);
  }, []);

  return {
    isLoading,
    error,
    data,
    execute,
    reset
  };
};

/**
 * Hook specifically for niche discovery requests
 */
export const useNicheDiscovery = () => {
  const { execute, isLoading, error, data, reset } = useApiRequest();
  const { apiService } = useApi();

  const discoverNiches = useCallback(async (keywords, options = {}) => {
    return execute(
      () => apiService.discoverNiches(keywords, options),
      {
        successMessage: `Found ${data?.niches?.length || 0} potential niches!`,
        errorMessage: 'Niche discovery failed',
        ...options
      }
    );
  }, [execute, apiService, data]);

  return {
    discoverNiches,
    isLoading,
    error,
    results: data,
    reset
  };
};

/**
 * Hook specifically for competitor analysis requests
 */
export const useCompetitorAnalysis = () => {
  const { execute, isLoading, error, data, reset } = useApiRequest();
  const { apiService } = useApi();

  const analyzeCompetitors = useCallback(async (asins, options = {}) => {
    return execute(
      () => apiService.analyzeCompetitors(asins, options),
      {
        successMessage: `Analysis complete! Found ${data?.competitors?.length || 0} competitors`,
        errorMessage: 'Competitor analysis failed',
        ...options
      }
    );
  }, [execute, apiService, data]);

  const searchCompetitors = useCallback(async (keyword, options = {}) => {
    return execute(
      () => apiService.searchCompetitors(keyword, options),
      {
        successMessage: `Found competitors for "${keyword}"`,
        errorMessage: 'Competitor search failed',
        ...options
      }
    );
  }, [execute, apiService]);

  return {
    analyzeCompetitors,
    searchCompetitors,
    isLoading,
    error,
    results: data,
    reset
  };
};

/**
 * Hook specifically for listing generation requests
 */
export const useListingGeneration = () => {
  const { execute, isLoading, error, data, reset } = useApiRequest();
  const { apiService } = useApi();

  const generateListing = useCallback(async (niche, options = {}) => {
    return execute(
      () => apiService.generateListing(niche, options),
      {
        successMessage: 'Listing generated successfully!',
        errorMessage: 'Listing generation failed',
        ...options
      }
    );
  }, [execute, apiService]);

  const optimizeListing = useCallback(async (listingData, options = {}) => {
    return execute(
      () => apiService.optimizeListing(listingData, options),
      {
        successMessage: 'Listing optimized successfully!',
        errorMessage: 'Listing optimization failed',
        ...options
      }
    );
  }, [execute, apiService]);

  return {
    generateListing,
    optimizeListing,
    isLoading,
    error,
    results: data,
    reset
  };
};

/**
 * Hook specifically for trend validation requests
 */
export const useTrendValidation = () => {
  const { execute, isLoading, error, data, reset } = useApiRequest();
  const { apiService } = useApi();

  const validateTrends = useCallback(async (keywords, options = {}) => {
    return execute(
      () => apiService.validateTrends(keywords, options),
      {
        successMessage: `Trend validation completed for ${keywords.length} keywords`,
        errorMessage: 'Trend validation failed',
        ...options
      }
    );
  }, [execute, apiService]);

  const getTrendingKeywords = useCallback(async (options = {}) => {
    return execute(
      () => apiService.getTrendingKeywords(options),
      {
        successMessage: 'Retrieved trending keywords',
        errorMessage: 'Failed to get trending keywords',
        showSuccessToast: false,
        ...options
      }
    );
  }, [execute, apiService]);

  return {
    validateTrends,
    getTrendingKeywords,
    isLoading,
    error,
    results: data,
    reset
  };
};

export default useApiRequest;