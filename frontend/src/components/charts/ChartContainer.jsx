import React, { useState, useRef, useCallback, useMemo } from 'react';
import { 
  ArrowDownTrayIcon, 
  FunnelIcon, 
  ArrowsUpDownIcon,
  EyeIcon,
  EyeSlashIcon
} from '@heroicons/react/24/outline';
import { toast } from 'react-toastify';
import { cn } from '../../lib/utils';
import ChartRenderer from './ChartRenderer';
import ChartFilters from './ChartFilters';
import ChartExport from './ChartExport';

/**
 * Container component that wraps charts with filtering, sorting, and export functionality
 */
const ChartContainer = ({
  data,
  chartType = 'bar',
  title,
  subtitle,
  className,
  height = 400,
  responsive = true,
  enableFiltering = true,
  enableSorting = true,
  enableExport = true,
  enableToggleView = true,
  filterOptions = {},
  sortOptions = {},
  exportOptions = {},
  onDataChange,
  children,
  ...chartProps
}) => {
  const [filteredData, setFilteredData] = useState(data);
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [activeFilters, setActiveFilters] = useState({});
  const [showFilters, setShowFilters] = useState(false);
  const [showChart, setShowChart] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const chartRef = useRef(null);

  // Memoized processed data
  const processedData = useMemo(() => {
    if (!data || !Array.isArray(data)) return [];
    
    let result = [...data];
    
    // Apply filters
    Object.entries(activeFilters).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== '') {
        result = result.filter(item => {
          const itemValue = item[key];
          if (typeof value === 'string') {
            return itemValue?.toString().toLowerCase().includes(value.toLowerCase());
          } else if (typeof value === 'number') {
            return itemValue >= value;
          } else if (Array.isArray(value)) {
            return value.includes(itemValue);
          }
          return itemValue === value;
        });
      }
    });
    
    // Apply sorting
    if (sortConfig.key) {
      result.sort((a, b) => {
        const aVal = a[sortConfig.key];
        const bVal = b[sortConfig.key];
        
        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    
    return result;
  }, [data, activeFilters, sortConfig]);

  // Update filtered data when processed data changes
  React.useEffect(() => {
    setFilteredData(processedData);
    if (onDataChange) {
      onDataChange(processedData);
    }
  }, [processedData, onDataChange]);

  const handleSort = useCallback((key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  }, []);

  const handleFilterChange = useCallback((filters) => {
    setActiveFilters(filters);
  }, []);

  const handleExport = useCallback(async (format, options = {}) => {
    setIsExporting(true);
    try {
      const exportData = {
        title,
        subtitle,
        data: filteredData,
        chartType,
        timestamp: new Date().toISOString(),
        ...options
      };

      // Use ChartExport utility
      const success = await ChartExport.exportChart(format, exportData, chartRef.current);
      
      if (success) {
        toast.success(`Chart exported as ${format.toUpperCase()}`);
      } else {
        toast.error('Export failed');
      }
    } catch (error) {
      console.error('Export error:', error);
      toast.error('Export failed: ' + error.message);
    } finally {
      setIsExporting(false);
    }
  }, [filteredData, chartType, title, subtitle]);

  const toggleFilters = useCallback(() => {
    setShowFilters(prev => !prev);
  }, []);

  const toggleChart = useCallback(() => {
    setShowChart(prev => !prev);
  }, []);

  const clearFilters = useCallback(() => {
    setActiveFilters({});
    setSortConfig({ key: null, direction: 'asc' });
  }, []);

  const hasActiveFilters = Object.keys(activeFilters).some(key => 
    activeFilters[key] !== null && activeFilters[key] !== undefined && activeFilters[key] !== ''
  );

  return (
    <div className={cn('bg-white rounded-lg shadow-sm border border-gray-200', className)}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            {title && (
              <h3 className="text-lg font-medium text-gray-900">{title}</h3>
            )}
            {subtitle && (
              <p className="text-sm text-gray-600 mt-1">{subtitle}</p>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            {/* Toggle Chart View */}
            {enableToggleView && (
              <button
                onClick={toggleChart}
                className="p-2 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100"
                title={showChart ? 'Hide Chart' : 'Show Chart'}
              >
                {showChart ? (
                  <EyeSlashIcon className="h-5 w-5" />
                ) : (
                  <EyeIcon className="h-5 w-5" />
                )}
              </button>
            )}
            
            {/* Filters Toggle */}
            {enableFiltering && (
              <button
                onClick={toggleFilters}
                className={cn(
                  'p-2 rounded-md hover:bg-gray-100',
                  showFilters || hasActiveFilters 
                    ? 'text-blue-600 bg-blue-50' 
                    : 'text-gray-400 hover:text-gray-600'
                )}
                title="Toggle Filters"
              >
                <FunnelIcon className="h-5 w-5" />
              </button>
            )}
            
            {/* Sort */}
            {enableSorting && (
              <button
                onClick={() => handleSort('value')}
                className={cn(
                  'p-2 rounded-md hover:bg-gray-100',
                  sortConfig.key ? 'text-blue-600 bg-blue-50' : 'text-gray-400 hover:text-gray-600'
                )}
                title="Sort Data"
              >
                <ArrowsUpDownIcon className="h-5 w-5" />
              </button>
            )}
            
            {/* Export */}
            {enableExport && (
              <div className="relative">
                <button
                  onClick={() => handleExport('png')}
                  disabled={isExporting}
                  className="p-2 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100 disabled:opacity-50"
                  title="Export Chart"
                >
                  <ArrowDownTrayIcon className="h-5 w-5" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Filters Panel */}
      {enableFiltering && showFilters && (
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <ChartFilters
            data={data}
            filters={activeFilters}
            onFiltersChange={handleFilterChange}
            options={filterOptions}
            onClear={clearFilters}
          />
        </div>
      )}

      {/* Chart Content */}
      <div className="p-6">
        {showChart ? (
          <div ref={chartRef} className={responsive ? 'w-full' : ''}>
            <ChartRenderer
              data={filteredData}
              type={chartType}
              height={height}
              responsive={responsive}
              {...chartProps}
            />
          </div>
        ) : (
          <div className="flex items-center justify-center h-64 text-gray-500">
            <div className="text-center">
              <EyeSlashIcon className="h-12 w-12 mx-auto mb-2" />
              <p>Chart is hidden</p>
            </div>
          </div>
        )}
        
        {/* Custom children content */}
        {children}
      </div>

      {/* Data Summary */}
      <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-600">
        <div className="flex items-center justify-between">
          <span>
            Showing {filteredData?.length || 0} of {data?.length || 0} items
            {hasActiveFilters && (
              <span className="ml-2 text-blue-600">(filtered)</span>
            )}
          </span>
          
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-blue-600 hover:text-blue-800 text-sm"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChartContainer;