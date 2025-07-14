import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  MagnifyingGlassIcon,
  ChartBarIcon,
  DocumentTextIcon,
  TrendingUpIcon,
  ShieldCheckIcon,
  ArrowRightIcon,
  EyeIcon,
  CurrencyDollarIcon,
  StarIcon
} from '@heroicons/react/24/outline';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ChartContainer from '../components/common/ChartContainer';
import { useApi } from '../App';
import { toast } from 'react-toastify';

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [recentActivity, setRecentActivity] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const { apiService } = useApi();

  useEffect(() => {
    const loadDashboardData = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        // Fetch real dashboard stats and activity from the backend
        const dashboardStats = await apiService.get('/api/dashboard/stats');
        const activityData = await apiService.get('/api/dashboard/activity');
        
        setStats(dashboardStats);
        setRecentActivity(activityData.recent_activities);
        
        toast.success('Dashboard data loaded successfully!');
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
        setError(apiService.formatError(err));
        toast.error(`Failed to load dashboard data: ${apiService.formatError(err)}`);
        
        // Fallback to empty data on error
        setStats({
          totalAnalyses: 0,
          successfulListings: 0,
          averageScore: 0,
          trendsValidated: 0
        });
        setRecentActivity([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadDashboardData();
  }, [apiService]);

  const quickActions = [
    {
      name: 'Discover Niches',
      description: 'Find profitable book niches',
      href: '/niche-discovery',
      icon: MagnifyingGlassIcon,
      color: 'bg-blue-500 hover:bg-blue-600'
    },
    {
      name: 'Analyze Competitors',
      description: 'Research competitor performance',
      href: '/competitor-analysis',
      icon: ChartBarIcon,
      color: 'bg-green-500 hover:bg-green-600'
    },
    {
      name: 'Generate Listing',
      description: 'Create optimized book listings',
      href: '/listing-generation',
      icon: DocumentTextIcon,
      color: 'bg-purple-500 hover:bg-purple-600'
    },
    {
      name: 'Validate Trends',
      description: 'Check market trend validity',
      href: '/trend-validation',
      icon: TrendingUpIcon,
      color: 'bg-orange-500 hover:bg-orange-600'
    }
  ];

  const getActivityIcon = (type) => {
    switch (type) {
      case 'niche_discovery':
        return MagnifyingGlassIcon;
      case 'competitor_analysis':
        return ChartBarIcon;
      case 'listing_generation':
        return DocumentTextIcon;
      case 'trend_validation':
        return TrendingUpIcon;
      default:
        return EyeIcon;
    }
  };

  const formatTimestamp = (timestamp) => {
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffInHours = Math.floor((now - date) / (1000 * 60 * 60));
      
      if (diffInHours < 1) {
        return 'Just now';
      } else if (diffInHours < 24) {
        return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`;
      } else {
        const diffInDays = Math.floor(diffInHours / 24);
        return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`;
      }
    } catch (error) {
      return timestamp; // Fallback to original timestamp if parsing fails
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-600 bg-green-100';
    if (score >= 60) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  // Mock chart data
  const performanceChart = {
    type: 'line',
    title: 'Analysis Performance Trend',
    data: {
      labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
      datasets: [
        {
          label: 'Average Score',
          data: [65, 72, 68, 78, 82, 85],
          borderColor: 'rgba(59, 130, 246, 1)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          fill: true
        }
      ]
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-2">
          Welcome back! Here's an overview of your KDP strategy performance.
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-8 bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error Loading Dashboard Data</h3>
              <div className="mt-2 text-sm text-red-700">
                <p>{error}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <EyeIcon className="h-8 w-8 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Total Analyses</p>
                <p className="text-2xl font-bold text-gray-900">{stats?.totalAnalyses}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <DocumentTextIcon className="h-8 w-8 text-green-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Successful Listings</p>
                <p className="text-2xl font-bold text-gray-900">{stats?.successfulListings}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <StarIcon className="h-8 w-8 text-yellow-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Average Score</p>
                <p className="text-2xl font-bold text-gray-900">{stats?.averageScore}%</p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <TrendingUpIcon className="h-8 w-8 text-purple-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Trends Validated</p>
                <p className="text-2xl font-bold text-gray-900">{stats?.trendsValidated}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Quick Actions */}
        <div className="lg:col-span-2">
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-medium text-gray-900">Quick Actions</h2>
              <p className="text-sm text-gray-600">Start your analysis with these tools</p>
            </div>
            <div className="card-body">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {quickActions.map((action) => {
                  const Icon = action.icon;
                  return (
                    <Link
                      key={action.name}
                      to={action.href}
                      className="group relative bg-white p-6 rounded-lg border border-gray-200 hover:border-gray-300 hover:shadow-md transition-all duration-200"
                    >
                      <div className="flex items-center">
                        <div className={`flex-shrink-0 p-3 rounded-lg ${action.color} transition-colors duration-200`}>
                          <Icon className="h-6 w-6 text-white" />
                        </div>
                        <div className="ml-4 flex-1">
                          <h3 className="text-sm font-medium text-gray-900 group-hover:text-primary-600">
                            {action.name}
                          </h3>
                          <p className="text-xs text-gray-500 mt-1">
                            {action.description}
                          </p>
                        </div>
                        <ArrowRightIcon className="h-4 w-4 text-gray-400 group-hover:text-primary-600 transition-colors duration-200" />
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div>
          <div className="card">
            <div className="card-header">
              <h2 className="text-lg font-medium text-gray-900">Recent Activity</h2>
            </div>
            <div className="card-body">
              <div className="space-y-4">
                {recentActivity.map((activity) => {
                  const Icon = getActivityIcon(activity.type);
                  return (
                    <div key={activity.id} className="flex items-start space-x-3">
                      <div className="flex-shrink-0">
                        <Icon className="h-5 w-5 text-gray-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {activity.title}
                        </p>
                        <p className="text-xs text-gray-500">{formatTimestamp(activity.timestamp)}</p>
                      </div>
                      <div className={`flex-shrink-0 px-2 py-1 text-xs font-medium rounded-full ${getScoreColor(activity.score)}`}>
                        {activity.score}%
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="card-footer">
              <Link
                to="/history"
                className="text-sm text-primary-600 hover:text-primary-700 font-medium"
              >
                View all activity →
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Performance Chart */}
      <div className="mt-8">
        <ChartContainer chartData={performanceChart} />
      </div>
    </div>
  );
};

export default Dashboard;