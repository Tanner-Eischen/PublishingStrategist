import React, { useState } from 'react';
import { toast } from 'react-toastify';
import { useCompetitorAnalysis } from '../hooks/useApiRequest';
import LoadingSpinner from '../components/common/LoadingSpinner';
import {
  ChartBarIcon,
  ExclamationTriangleIcon,
  StarIcon,
  CurrencyDollarIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';

const CompetitorAnalysis = () => {
  const [searchType, setSearchType] = useState('keyword'); // 'keyword' or 'asin'
  const [searchValue, setSearchValue] = useState('');
  const [options, setOptions] = useState({
    maxResults: 50,
    minReviews: 10,
    includePricing: true,
    includeReviews: true,
    includeKeywords: true,
    analysisDepth: 'standard'
  });
  const { analyzeCompetitors, searchCompetitors, isLoading, error, results, reset } = useCompetitorAnalysis();

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!searchValue.trim()) {
      toast.error(`Please enter a ${searchType === 'keyword' ? 'keyword' : 'ASIN'}`);
      return;
    }

    try {
      if (searchType === 'keyword') {
        await searchCompetitors(searchValue.trim(), options);
      } else {
        const asins = searchValue.split(',').map(a => a.trim()).filter(a => a);
        await analyzeCompetitors(asins, options);
      }
    } catch (err) {
      // Error handling is done in the custom hook
      console.error('Competitor analysis failed:', err);
    }
  };

  const handleRetry = () => {
    if (searchValue.trim()) {
      handleSubmit({ preventDefault: () => {} });
    }
  };

  const formatPrice = (price) => {
    return price ? `$${price.toFixed(2)}` : 'N/A';
  };

  const formatReviews = (count) => {
    if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}k`;
    }
    return count?.toString() || '0';
  };

  const getRatingColor = (rating) => {
    if (rating >= 4.5) return 'text-green-600';
    if (rating >= 4.0) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Competitor Analysis</h1>
        <p className="text-gray-600 mt-2">
          Analyze competitor performance and market positioning
        </p>
      </div>

      {/* Search Form */}
      <div className="bg-white shadow rounded-lg p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Search Type Toggle */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">Search Type</label>
            <div className="flex space-x-4">
              <label className="flex items-center">
                <input
                  type="radio"
                  name="searchType"
                  value="keyword"
                  checked={searchType === 'keyword'}
                  onChange={(e) => setSearchType(e.target.value)}
                  className="focus:ring-blue-500 h-4 w-4 text-blue-600 border-gray-300"
                />
                <span className="ml-2 text-sm text-gray-700">Search by Keyword</span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="searchType"
                  value="asin"
                  checked={searchType === 'asin'}
                  onChange={(e) => setSearchType(e.target.value)}
                  className="focus:ring-blue-500 h-4 w-4 text-blue-600 border-gray-300"
                />
                <span className="ml-2 text-sm text-gray-700">Analyze by ASIN</span>
              </label>
            </div>
          </div>

          <div>
            <label htmlFor="searchValue" className="block text-sm font-medium text-gray-700">
              {searchType === 'keyword' ? 'Keyword' : 'ASIN(s) (comma-separated)'}
            </label>
            <input
              type="text"
              id="searchValue"
              className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              placeholder={searchType === 'keyword' ? 'e.g., productivity planner' : 'e.g., B08XYZ123, B09ABC456'}
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              disabled={isLoading}
            />
          </div>

          {/* Options */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Max Results</label>
              <select
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={options.maxResults}
                onChange={(e) => setOptions({...options, maxResults: parseInt(e.target.value)})}
                disabled={isLoading}
              >
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Min Reviews</label>
              <select
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={options.minReviews}
                onChange={(e) => setOptions({...options, minReviews: parseInt(e.target.value)})}
                disabled={isLoading}
              >
                <option value={0}>Any</option>
                <option value={10}>10+</option>
                <option value={50}>50+</option>
                <option value={100}>100+</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Analysis Depth</label>
              <select
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={options.analysisDepth}
                onChange={(e) => setOptions({...options, analysisDepth: e.target.value})}
                disabled={isLoading}
              >
                <option value="basic">Basic</option>
                <option value="standard">Standard</option>
                <option value="comprehensive">Comprehensive</option>
              </select>
            </div>

            <div className="flex flex-col space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={options.includePricing}
                  onChange={(e) => setOptions({...options, includePricing: e.target.checked})}
                  disabled={isLoading}
                />
                <span className="ml-2 text-sm text-gray-700">Include Pricing</span>
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={options.includeReviews}
                  onChange={(e) => setOptions({...options, includeReviews: e.target.checked})}
                  disabled={isLoading}
                />
                <span className="ml-2 text-sm text-gray-700">Include Reviews</span>
              </label>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading || !searchValue.trim()}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <LoadingSpinner size="small" showMessage={false} />
              ) : (
                <>
                  <ChartBarIcon className="h-5 w-5 mr-2" />
                  Analyze Competitors
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-400" />
            <div className="ml-3 flex-1">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <div className="mt-2 text-sm text-red-700">
                <p>{error}</p>
              </div>
              <div className="mt-3 flex space-x-3">
                <button
                  onClick={handleRetry}
                  disabled={isLoading}
                  className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-red-700 bg-red-100 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
                >
                  <ArrowPathIcon className="h-3 w-3 mr-1" />
                  Retry
                </button>
                <button
                  onClick={reset}
                  className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-gray-700 bg-gray-100 hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
                >
                  Clear
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      {results && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Analysis Summary</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{results.competitors?.length || 0}</div>
                <div className="text-sm text-gray-500">Competitors Found</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {formatPrice(results.market_overview?.average_price)}
                </div>
                <div className="text-sm text-gray-500">Avg Price</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">
                  {results.market_overview?.average_rating?.toFixed(1) || 'N/A'}
                </div>
                <div className="text-sm text-gray-500">Avg Rating</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {formatReviews(results.market_overview?.total_reviews)}
                </div>
                <div className="text-sm text-gray-500">Total Reviews</div>
              </div>
            </div>
          </div>

          {/* Competitor Results */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">Competitor Analysis</h2>
            </div>
            <div className="divide-y divide-gray-200">
              {results.competitors?.map((competitor, index) => (
                <div key={index} className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="text-lg font-medium text-gray-900">{competitor.title}</h3>
                      <p className="text-sm text-gray-600 mt-1">ASIN: {competitor.asin}</p>
                      <p className="text-sm text-gray-600">Author: {competitor.author}</p>
                      
                      {competitor.keywords && competitor.keywords.length > 0 && (
                        <div className="mt-2">
                          <div className="flex flex-wrap gap-2">
                            {competitor.keywords.slice(0, 5).map((keyword, idx) => (
                              <span key={idx} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                {keyword}
                              </span>
                            ))}
                            {competitor.keywords.length > 5 && (
                              <span className="text-xs text-gray-500">+{competitor.keywords.length - 5} more</span>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                    
                    <div className="flex items-center space-x-6 ml-4">
                      <div className="text-center">
                        <div className="flex items-center">
                          <CurrencyDollarIcon className="h-4 w-4 text-green-600" />
                          <span className="ml-1 text-lg font-semibold text-gray-900">
                            {formatPrice(competitor.price)}
                          </span>
                        </div>
                        <div className="text-xs text-gray-500">Price</div>
                      </div>
                      
                      <div className="text-center">
                        <div className="flex items-center">
                          <StarIcon className="h-4 w-4 text-yellow-400" />
                          <span className={`ml-1 text-lg font-semibold ${getRatingColor(competitor.rating)}`}>
                            {competitor.rating?.toFixed(1) || 'N/A'}
                          </span>
                        </div>
                        <div className="text-xs text-gray-500">Rating</div>
                      </div>
                      
                      <div className="text-center">
                        <div className="text-lg font-semibold text-gray-900">
                          {formatReviews(competitor.review_count)}
                        </div>
                        <div className="text-xs text-gray-500">Reviews</div>
                      </div>
                      
                      {competitor.bsr && (
                        <div className="text-center">
                          <div className="text-lg font-semibold text-gray-900">
                            #{competitor.bsr.toLocaleString()}
                          </div>
                          <div className="text-xs text-gray-500">BSR</div>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {competitor.description && (
                    <div className="mt-4">
                      <p className="text-sm text-gray-600 line-clamp-2">{competitor.description}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CompetitorAnalysis;