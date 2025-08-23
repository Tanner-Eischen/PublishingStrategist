import React, { useState, useCallback, useMemo } from 'react';
import { XMarkIcon, FunnelIcon } from '@heroicons/react/24/outline';
import { cn } from '../../lib/utils';

/**
 * Chart filtering component with dynamic filter generation
 */
const ChartFilters = ({
  data = [],
  filters = {},
  onFiltersChange,
  options = {},
  onClear,
  className
}) => {
  const [localFilters, setLocalFilters] = useState(filters);

  // Generate filter options from data
  const filterOptions = useMemo(() => {
    if (!data || !Array.isArray(data) || data.length === 0) return {};

    const options = {};
    const sampleItem = data[0];

    Object.keys(sampleItem).forEach(key => {
      const values = data.map(item => item[key]).filter(val => val !== null && val !== undefined);
      const uniqueValues = [...new Set(values)];
      
      if (uniqueValues.length > 1 && uniqueValues.length <= 20) {
        // Categorical filter for small unique value sets
        options[key] = {
          type: 'select',
          label: key.charAt(0).toUpperCase() + key.slice(1).replace(/([A-Z])/g, ' $1'),
          options: uniqueValues.map(val => ({ value: val, label: String(val) }))
        };
      } else if (typeof uniqueValues[0] === 'number') {
        // Range filter for numeric values
        const min = Math.min(...uniqueValues);
        const max = Math.max(...uniqueValues);
        options[key] = {
          type: 'range',
          label: key.charAt(0).toUpperCase() + key.slice(1).replace(/([A-Z])/g, ' $1'),
          min,
          max,
          step: (max - min) / 100
        };
      } else if (typeof uniqueValues[0] === 'string') {
        // Text search filter for strings
        options[key] = {
          type: 'text',
          label: key.charAt(0).toUpperCase() + key.slice(1).replace(/([A-Z])/g, ' $1')
        };
      }
    });

    return options;
  }, [data]);

  const handleFilterChange = useCallback((key, value) => {
    const newFilters = { ...localFilters, [key]: value };
    setLocalFilters(newFilters);
    onFiltersChange?.(newFilters);
  }, [localFilters, onFiltersChange]);

  const handleClearFilter = useCallback((key) => {
    const newFilters = { ...localFilters };
    delete newFilters[key];
    setLocalFilters(newFilters);
    onFiltersChange?.(newFilters);
  }, [localFilters, onFiltersChange]);

  const handleClearAll = useCallback(() => {
    setLocalFilters({});
    onFiltersChange?.({});
    onClear?.();
  }, [onFiltersChange, onClear]);

  const activeFilterCount = Object.keys(localFilters).filter(key => 
    localFilters[key] !== null && localFilters[key] !== undefined && localFilters[key] !== ''
  ).length;

  if (Object.keys(filterOptions).length === 0) {
    return (
      <div className={cn('text-center py-4 text-gray-500', className)}>
        <FunnelIcon className="h-8 w-8 mx-auto mb-2" />
        <p>No filterable data available</p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <FunnelIcon className="h-5 w-5 text-gray-600" />
          <h4 className="text-sm font-medium text-gray-900">Filters</h4>
          {activeFilterCount > 0 && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
              {activeFilterCount} active
            </span>
          )}
        </div>
        
        {activeFilterCount > 0 && (
          <button
            onClick={handleClearAll}
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Filter Controls */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Object.entries(filterOptions).map(([key, config]) => (
          <div key={key} className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              {config.label}
            </label>
            
            {config.type === 'select' && (
              <div className="relative">
                <select
                  value={localFilters[key] || ''}
                  onChange={(e) => handleFilterChange(key, e.target.value || null)}
                  className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
                >
                  <option value="">All</option>
                  {config.options.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                {localFilters[key] && (
                  <button
                    onClick={() => handleClearFilter(key)}
                    className="absolute inset-y-0 right-8 flex items-center pr-2"
                  >
                    <XMarkIcon className="h-4 w-4 text-gray-400 hover:text-gray-600" />
                  </button>
                )}
              </div>
            )}
            
            {config.type === 'range' && (
              <div className="space-y-2">
                <input
                  type="range"
                  min={config.min}
                  max={config.max}
                  step={config.step}
                  value={localFilters[key] || config.min}
                  onChange={(e) => handleFilterChange(key, parseFloat(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>{config.min}</span>
                  <span className="font-medium">
                    {localFilters[key] ? localFilters[key].toFixed(1) : config.min}
                  </span>
                  <span>{config.max}</span>
                </div>
                {localFilters[key] && (
                  <button
                    onClick={() => handleClearFilter(key)}
                    className="text-xs text-gray-600 hover:text-gray-900"
                  >
                    Reset
                  </button>
                )}
              </div>
            )}
            
            {config.type === 'text' && (
              <div className="relative">
                <input
                  type="text"
                  value={localFilters[key] || ''}
                  onChange={(e) => handleFilterChange(key, e.target.value || null)}
                  placeholder={`Search ${config.label.toLowerCase()}...`}
                  className="block w-full pl-3 pr-10 py-2 border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                />
                {localFilters[key] && (
                  <button
                    onClick={() => handleClearFilter(key)}
                    className="absolute inset-y-0 right-0 flex items-center pr-3"
                  >
                    <XMarkIcon className="h-4 w-4 text-gray-400 hover:text-gray-600" />
                  </button>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Active Filters Display */}
      {activeFilterCount > 0 && (
        <div className="pt-4 border-t border-gray-200">
          <div className="flex flex-wrap gap-2">
            {Object.entries(localFilters)
              .filter(([_, value]) => value !== null && value !== undefined && value !== '')
              .map(([key, value]) => (
                <span
                  key={key}
                  className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                >
                  {filterOptions[key]?.label}: {String(value)}
                  <button
                    onClick={() => handleClearFilter(key)}
                    className="ml-2 inline-flex items-center justify-center w-4 h-4 rounded-full hover:bg-blue-200"
                  >
                    <XMarkIcon className="h-3 w-3" />
                  </button>
                </span>
              ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ChartFilters;