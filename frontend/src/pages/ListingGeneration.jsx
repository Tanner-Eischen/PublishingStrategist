import React, { useState } from 'react';
import { toast } from 'react-toastify';
import { useListingGeneration } from '../hooks/useApiRequest';
import LoadingSpinner from '../components/common/LoadingSpinner';
import {
  DocumentTextIcon,
  ExclamationTriangleIcon,
  ClipboardDocumentIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';

const ListingGeneration = () => {
  const [niche, setNiche] = useState('');
  const [targetAudience, setTargetAudience] = useState('');
  const [bookType, setBookType] = useState('non-fiction');
  const [tone, setTone] = useState('professional');
  const [includeKeywords, setIncludeKeywords] = useState(true);
  const { generateListing, isLoading, error, results, reset } = useListingGeneration();

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!niche.trim()) {
      toast.error('Please enter a niche');
      return;
    }

    try {
      const requestData = {
        target_audience: targetAudience.trim() || 'general audience',
        book_type: bookType,
        tone: tone,
        include_keywords: includeKeywords
      };
      
      await generateListing(niche.trim(), requestData);
    } catch (err) {
      // Error handling is done in the custom hook
      console.error('Listing generation failed:', err);
    }
  };

  const handleRetry = () => {
    if (niche.trim()) {
      handleSubmit({ preventDefault: () => {} });
    }
  };

  const copyToClipboard = (text, label) => {
    navigator.clipboard.writeText(text).then(() => {
      toast.success(`${label} copied to clipboard!`);
    }).catch(() => {
      toast.error('Failed to copy to clipboard');
    });
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-600 bg-green-100';
    if (score >= 60) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getComplianceIcon = (isCompliant) => {
    return isCompliant ? (
      <CheckCircleIcon className="h-5 w-5 text-green-500" />
    ) : (
      <XCircleIcon className="h-5 w-5 text-red-500" />
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Listing Generation</h1>
        <p className="text-gray-600 mt-2">
          Generate optimized KDP book listings with AI-powered content creation
        </p>
      </div>

      {/* Generation Form */}
      <div className="bg-white shadow rounded-lg p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label htmlFor="niche" className="block text-sm font-medium text-gray-700">
                Niche/Topic *
              </label>
              <input
                type="text"
                id="niche"
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g., productivity, mindfulness, weight loss"
                value={niche}
                onChange={(e) => setNiche(e.target.value)}
                disabled={isLoading}
                required
              />
            </div>

            <div>
              <label htmlFor="targetAudience" className="block text-sm font-medium text-gray-700">
                Target Audience
              </label>
              <input
                type="text"
                id="targetAudience"
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g., busy professionals, new parents, students"
                value={targetAudience}
                onChange={(e) => setTargetAudience(e.target.value)}
                disabled={isLoading}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label htmlFor="bookType" className="block text-sm font-medium text-gray-700">
                Book Type
              </label>
              <select
                id="bookType"
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={bookType}
                onChange={(e) => setBookType(e.target.value)}
                disabled={isLoading}
              >
                <option value="non-fiction">Non-Fiction</option>
                <option value="how-to">How-To Guide</option>
                <option value="workbook">Workbook</option>
                <option value="journal">Journal/Planner</option>
                <option value="cookbook">Cookbook</option>
                <option value="children">Children's Book</option>
              </select>
            </div>

            <div>
              <label htmlFor="tone" className="block text-sm font-medium text-gray-700">
                Tone
              </label>
              <select
                id="tone"
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={tone}
                onChange={(e) => setTone(e.target.value)}
                disabled={isLoading}
              >
                <option value="professional">Professional</option>
                <option value="friendly">Friendly</option>
                <option value="authoritative">Authoritative</option>
                <option value="conversational">Conversational</option>
                <option value="inspiring">Inspiring</option>
              </select>
            </div>

            <div className="flex items-center justify-center">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                  checked={includeKeywords}
                  onChange={(e) => setIncludeKeywords(e.target.checked)}
                  disabled={isLoading}
                />
                <span className="ml-2 text-sm text-gray-700">Include SEO Keywords</span>
              </label>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading || !niche.trim()}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <LoadingSpinner size="small" showMessage={false} />
              ) : (
                <>
                  <DocumentTextIcon className="h-5 w-5 mr-2" />
                  Generate Listing
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
          {/* Optimization Score */}
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-medium text-gray-900">Optimization Score</h2>
              <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getScoreColor(results.optimization_score)}`}>
                {Math.round(results.optimization_score)}%
              </div>
            </div>
            
            {results.seo_recommendations && results.seo_recommendations.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">SEO Recommendations:</h3>
                <ul className="text-sm text-gray-600 space-y-1">
                  {results.seo_recommendations.map((rec, index) => (
                    <li key={index} className="flex items-start">
                      <span className="text-blue-500 mr-2">•</span>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Generated Listing */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">Generated Listing</h2>
            </div>
            
            <div className="p-6 space-y-6">
              {/* Title */}
              {results.listing?.title && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-gray-700">Title</h3>
                    <button
                      onClick={() => copyToClipboard(results.listing.title, 'Title')}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      <ClipboardDocumentIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <p className="text-gray-900 font-medium">{results.listing.title}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {results.listing.title.length}/200 characters
                  </p>
                </div>
              )}

              {/* Subtitle */}
              {results.listing?.subtitle && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-gray-700">Subtitle</h3>
                    <button
                      onClick={() => copyToClipboard(results.listing.subtitle, 'Subtitle')}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      <ClipboardDocumentIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <p className="text-gray-900">{results.listing.subtitle}</p>
                </div>
              )}

              {/* Description */}
              {results.listing?.description && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-gray-700">Description</h3>
                    <button
                      onClick={() => copyToClipboard(results.listing.description, 'Description')}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      <ClipboardDocumentIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="bg-gray-50 p-4 rounded-md">
                    <p className="text-gray-900 whitespace-pre-wrap">{results.listing.description}</p>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {results.listing.description.length}/4000 characters
                  </p>
                </div>
              )}

              {/* Keywords */}
              {results.listing?.keywords && results.listing.keywords.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-gray-700">Keywords</h3>
                    <button
                      onClick={() => copyToClipboard(results.listing.keywords.join(', '), 'Keywords')}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      <ClipboardDocumentIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {results.listing.keywords.map((keyword, index) => (
                      <span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {keyword}
                      </span>
                    ))}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {results.listing.keywords.length}/7 keywords
                  </p>
                </div>
              )}

              {/* Bullet Points */}
              {results.listing?.bullet_points && results.listing.bullet_points.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-gray-700">Key Benefits</h3>
                    <button
                      onClick={() => copyToClipboard(results.listing.bullet_points.join('\n• '), 'Bullet Points')}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      <ClipboardDocumentIcon className="h-4 w-4" />
                    </button>
                  </div>
                  <ul className="space-y-2">
                    {results.listing.bullet_points.map((point, index) => (
                      <li key={index} className="flex items-start">
                        <span className="text-blue-500 mr-2">•</span>
                        <span className="text-gray-900">{point}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Categories */}
              {results.listing?.categories && results.listing.categories.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Suggested Categories</h3>
                  <div className="flex flex-wrap gap-2">
                    {results.listing.categories.map((category, index) => (
                      <span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        {category}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Compliance Check */}
          {results.compliance_check && (
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">KDP Compliance Check</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(results.compliance_check).map(([key, isCompliant]) => (
                  <div key={key} className="flex items-center">
                    {getComplianceIcon(isCompliant)}
                    <span className="ml-2 text-sm text-gray-700 capitalize">
                      {key.replace(/_/g, ' ')}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ListingGeneration;