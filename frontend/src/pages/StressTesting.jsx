import React, { useState } from 'react';
import { toast } from 'react-toastify';
import { useApi } from '../App';
import LoadingSpinner from '../components/common/LoadingSpinner';
import {
  ExclamationTriangleIcon,
  ShieldExclamationIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon
} from '@heroicons/react/24/outline';

const StressTesting = () => {
  const [niche, setNiche] = useState('');
  const [scenarios, setScenarios] = useState([
    'market_saturation',
    'seasonal_decline',
    'trend_reversal',
    'competition_increase'
  ]);
  const [severityLevel, setSeverityLevel] = useState('moderate');
  const [includeRecommendations, setIncludeRecommendations] = useState(true);
  const [results, setResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const { apiService } = useApi();

  const availableScenarios = [
    { id: 'market_saturation', label: 'Market Saturation', description: 'Test resilience against market oversaturation' },
    { id: 'seasonal_decline', label: 'Seasonal Decline', description: 'Analyze impact of seasonal downturns' },
    { id: 'trend_reversal', label: 'Trend Reversal', description: 'Evaluate response to trend reversals' },
    { id: 'competition_increase', label: 'Competition Increase', description: 'Test against increased competition' },
    { id: 'economic_downturn', label: 'Economic Downturn', description: 'Assess impact of economic recession' },
    { id: 'platform_changes', label: 'Platform Changes', description: 'Evaluate response to platform algorithm changes' }
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!niche.trim()) {
      toast.error('Please enter a niche');
      return;
    }

    if (scenarios.length === 0) {
      toast.error('Please select at least one test scenario');
      return;
    }

    setIsLoading(true);
    setError(null);
    setResults(null);

    try {
      const requestData = {
        niche: niche.trim(),
        test_scenarios: scenarios,
        severity_level: severityLevel,
        include_recommendations: includeRecommendations
      };
      
      const response = await apiService.runStressTest(niche.trim(), requestData);
      
      setResults(response);
      toast.success('Stress test completed successfully!');
    } catch (err) {
      const errorMessage = apiService.formatError(err);
      setError(errorMessage);
      toast.error(`Stress test failed: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetry = () => {
    if (niche.trim()) {
      handleSubmit({ preventDefault: () => {} });
    }
  };

  const handleScenarioToggle = (scenarioId) => {
    setScenarios(prev => 
      prev.includes(scenarioId)
        ? prev.filter(id => id !== scenarioId)
        : [...prev, scenarioId]
    );
  };

  const getRiskColor = (level) => {
    switch (level?.toLowerCase()) {
      case 'low':
        return 'text-green-600 bg-green-100';
      case 'medium':
        return 'text-yellow-600 bg-yellow-100';
      case 'high':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getResilienceIcon = (score) => {
    if (score >= 70) return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
    if (score >= 40) return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />;
    return <XCircleIcon className="h-5 w-5 text-red-500" />;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Stress Testing</h1>
        <p className="text-gray-600 mt-2">
          Test niche resilience under various market stress scenarios
        </p>
      </div>

      {/* Test Configuration Form */}
      <div className="bg-white shadow rounded-lg p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="niche" className="block text-sm font-medium text-gray-700">
              Niche to Test *
            </label>
            <input
              type="text"
              id="niche"
              className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-red-500 focus:border-red-500"
              placeholder="e.g., productivity journals, mindfulness books"
              value={niche}
              onChange={(e) => setNiche(e.target.value)}
              disabled={isLoading}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Test Scenarios *
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {availableScenarios.map((scenario) => (
                <label key={scenario.id} className="flex items-start">
                  <input
                    type="checkbox"
                    className="mt-1 rounded border-gray-300 text-red-600 shadow-sm focus:border-red-300 focus:ring focus:ring-red-200 focus:ring-opacity-50"
                    checked={scenarios.includes(scenario.id)}
                    onChange={() => handleScenarioToggle(scenario.id)}
                    disabled={isLoading}
                  />
                  <div className="ml-3">
                    <span className="text-sm font-medium text-gray-700">{scenario.label}</span>
                    <p className="text-xs text-gray-500">{scenario.description}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700">Severity Level</label>
              <select
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-red-500 focus:border-red-500"
                value={severityLevel}
                onChange={(e) => setSeverityLevel(e.target.value)}
                disabled={isLoading}
              >
                <option value="mild">Mild</option>
                <option value="moderate">Moderate</option>
                <option value="severe">Severe</option>
                <option value="extreme">Extreme</option>
              </select>
            </div>

            <div className="flex items-center justify-center">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-red-600 shadow-sm focus:border-red-300 focus:ring focus:ring-red-200 focus:ring-opacity-50"
                  checked={includeRecommendations}
                  onChange={(e) => setIncludeRecommendations(e.target.checked)}
                  disabled={isLoading}
                />
                <span className="ml-2 text-sm text-gray-700">Include Mitigation Recommendations</span>
              </label>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading || !niche.trim() || scenarios.length === 0}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <LoadingSpinner size="small" showMessage={false} />
              ) : (
                <>
                  <ShieldExclamationIcon className="h-5 w-5 mr-2" />
                  Run Stress Test
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
                  onClick={() => setError(null)}
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
          {/* Overall Resilience Score */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Overall Resilience Score</h2>
            <div className="flex items-center justify-center">
              <div className="flex items-center">
                {getResilienceIcon(results.overall_score)}
                <span className="ml-2 text-3xl font-bold text-gray-900">
                  {Math.round(results.overall_score || 0)}%
                </span>
              </div>
            </div>
            <p className="text-center text-gray-600 mt-2">
              {results.overall_score >= 70 ? 'Highly Resilient' :
               results.overall_score >= 40 ? 'Moderately Resilient' : 'Low Resilience'}
            </p>
          </div>

          {/* Scenario Results */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">Scenario Test Results</h2>
            </div>
            <div className="divide-y divide-gray-200">
              {results.scenario_results?.map((scenario, index) => (
                <div key={index} className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="text-lg font-medium text-gray-900">{scenario.name}</h3>
                      <p className="text-sm text-gray-600 mt-1">{scenario.description}</p>
                      
                      <div className="mt-3 flex items-center space-x-4">
                        <div className="flex items-center">
                          {getResilienceIcon(scenario.resilience_score)}
                          <span className="ml-1 text-lg font-semibold">
                            {Math.round(scenario.resilience_score)}%
                          </span>
                        </div>
                        
                        <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getRiskColor(scenario.risk_level)}`}>
                          {scenario.risk_level} Risk
                        </div>
                        
                        {scenario.impact_score && (
                          <div className="text-sm text-gray-600">
                            Impact: {Math.round(scenario.impact_score)}%
                          </div>
                        )}
                      </div>
                      
                      {scenario.key_vulnerabilities && scenario.key_vulnerabilities.length > 0 && (
                        <div className="mt-4">
                          <h4 className="text-sm font-medium text-gray-700">Key Vulnerabilities:</h4>
                          <ul className="mt-2 text-sm text-gray-600 list-disc list-inside">
                            {scenario.key_vulnerabilities.map((vulnerability, idx) => (
                              <li key={idx}>{vulnerability}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recommendations */}
          {results.recommendations && results.recommendations.length > 0 && (
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Mitigation Recommendations</h2>
              <div className="space-y-4">
                {results.recommendations.map((rec, index) => (
                  <div key={index} className="border-l-4 border-blue-400 pl-4">
                    <h3 className="text-sm font-medium text-gray-900">{rec.title}</h3>
                    <p className="text-sm text-gray-600 mt-1">{rec.description}</p>
                    {rec.priority && (
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium mt-2 ${
                        rec.priority === 'high' ? 'bg-red-100 text-red-800' :
                        rec.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-green-100 text-green-800'
                      }`}>
                        {rec.priority} priority
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Risk Matrix */}
          {results.risk_matrix && (
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Risk Assessment Matrix</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-600">{results.risk_matrix.high_risk || 0}</div>
                  <div className="text-sm text-gray-500">High Risk Factors</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-yellow-600">{results.risk_matrix.medium_risk || 0}</div>
                  <div className="text-sm text-gray-500">Medium Risk Factors</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">{results.risk_matrix.low_risk || 0}</div>
                  <div className="text-sm text-gray-500">Low Risk Factors</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default StressTesting;