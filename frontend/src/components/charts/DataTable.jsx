import React, { useState, useMemo, useCallback } from 'react';
import {
  ChevronUpIcon,
  ChevronDownIcon,
  ArrowDownTrayIcon,
  FunnelIcon,
  MagnifyingGlassIcon
} from '@heroicons/react/24/outline';
import { cn } from '../../lib/utils';
import ChartExport from './ChartExport';

/**
 * Interactive data table with sorting, filtering, and export capabilities
 */
const DataTable = ({
  data = [],
  columns = [],
  title,
  subtitle,
  className,
  pageSize = 10,
  enableSorting = true,
  enableFiltering = true,
  enableExport = true,
  enablePagination = true,
  enableSearch = true,
  responsive = true,
  onRowClick,
  rowClassName,
  emptyMessage = 'No data available'
}) => {
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [columnFilters, setColumnFilters] = useState({});
  const [showFilters, setShowFilters] = useState(false);

  // Auto-generate columns if not provided
  const tableColumns = useMemo(() => {
    if (columns.length > 0) return columns;
    
    if (data.length === 0) return [];
    
    const sampleRow = data[0];
    return Object.keys(sampleRow).map(key => ({
      key,
      label: key.charAt(0).toUpperCase() + key.slice(1).replace(/([A-Z])/g, ' $1'),
      sortable: true,
      filterable: true,
      render: (value) => value
    }));
  }, [columns, data]);

  // Process data with search, filters, and sorting
  const processedData = useMemo(() => {
    let result = [...data];

    // Apply search
    if (searchTerm) {
      result = result.filter(row =>
        Object.values(row).some(value =>
          String(value).toLowerCase().includes(searchTerm.toLowerCase())
        )
      );
    }

    // Apply column filters
    Object.entries(columnFilters).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== '') {
        result = result.filter(row => {
          const rowValue = row[key];
          if (typeof value === 'string') {
            return String(rowValue).toLowerCase().includes(value.toLowerCase());
          }
          return rowValue === value;
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
  }, [data, searchTerm, columnFilters, sortConfig]);

  // Pagination
  const paginatedData = useMemo(() => {
    if (!enablePagination) return processedData;
    
    const startIndex = (currentPage - 1) * pageSize;
    return processedData.slice(startIndex, startIndex + pageSize);
  }, [processedData, currentPage, pageSize, enablePagination]);

  const totalPages = Math.ceil(processedData.length / pageSize);

  // Handlers
  const handleSort = useCallback((key) => {
    if (!enableSorting) return;
    
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  }, [enableSorting]);

  const handleSearch = useCallback((term) => {
    setSearchTerm(term);
    setCurrentPage(1);
  }, []);

  const handleFilterChange = useCallback((key, value) => {
    setColumnFilters(prev => ({ ...prev, [key]: value }));
    setCurrentPage(1);
  }, []);

  const handleExport = useCallback(async (format) => {
    const exportData = {
      title: title || 'Data Table',
      subtitle,
      data: processedData,
      timestamp: new Date().toISOString()
    };

    try {
      await ChartExport.exportChart(format, exportData, null);
    } catch (error) {
      console.error('Export failed:', error);
    }
  }, [processedData, title, subtitle]);

  const clearFilters = useCallback(() => {
    setSearchTerm('');
    setColumnFilters({});
    setSortConfig({ key: null, direction: 'asc' });
    setCurrentPage(1);
  }, []);

  const getSortIcon = (columnKey) => {
    if (sortConfig.key !== columnKey) return null;
    return sortConfig.direction === 'asc' ? 
      <ChevronUpIcon className="h-4 w-4" /> : 
      <ChevronDownIcon className="h-4 w-4" />;
  };

  const hasActiveFilters = searchTerm || Object.keys(columnFilters).some(key => 
    columnFilters[key] !== null && columnFilters[key] !== undefined && columnFilters[key] !== ''
  );

  if (data.length === 0) {
    return (
      <div className={cn('bg-white rounded-lg shadow-sm border border-gray-200 p-8', className)}>
        <div className="text-center text-gray-500">
          <div className="mx-auto h-12 w-12 text-gray-400 mb-4">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <p>{emptyMessage}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('bg-white rounded-lg shadow-sm border border-gray-200', className)}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            {title && <h3 className="text-lg font-medium text-gray-900">{title}</h3>}
            {subtitle && <p className="text-sm text-gray-600 mt-1">{subtitle}</p>}
          </div>
          
          <div className="flex items-center space-x-2">
            {enableFiltering && (
              <button
                onClick={() => setShowFilters(!showFilters)}
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
            
            {enableExport && (
              <button
                onClick={() => handleExport('csv')}
                className="p-2 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100"
                title="Export Data"
              >
                <ArrowDownTrayIcon className="h-5 w-5" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Search and Filters */}
      {(enableSearch || (enableFiltering && showFilters)) && (
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200 space-y-4">
          {enableSearch && (
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                placeholder="Search all columns..."
                value={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          )}
          
          {enableFiltering && showFilters && (
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {tableColumns.filter(col => col.filterable).map(column => (
                <div key={column.key}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {column.label}
                  </label>
                  <input
                    type="text"
                    placeholder={`Filter ${column.label.toLowerCase()}...`}
                    value={columnFilters[column.key] || ''}
                    onChange={(e) => handleFilterChange(column.key, e.target.value)}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              ))}
            </div>
          )}
          
          {hasActiveFilters && (
            <div className="flex justify-between items-center pt-2">
              <span className="text-sm text-gray-600">
                Showing {processedData.length} of {data.length} items
              </span>
              <button
                onClick={clearFilters}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                Clear all filters
              </button>
            </div>
          )}
        </div>
      )}

      {/* Table */}
      <div className={cn('overflow-x-auto', responsive && 'max-w-full')}>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {tableColumns.map(column => (
                <th
                  key={column.key}
                  className={cn(
                    'px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider',
                    column.sortable && enableSorting && 'cursor-pointer hover:bg-gray-100'
                  )}
                  onClick={() => column.sortable && handleSort(column.key)}
                >
                  <div className="flex items-center space-x-1">
                    <span>{column.label}</span>
                    {column.sortable && enableSorting && getSortIcon(column.key)}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {paginatedData.map((row, index) => (
              <tr
                key={index}
                className={cn(
                  'hover:bg-gray-50',
                  onRowClick && 'cursor-pointer',
                  rowClassName && rowClassName(row, index)
                )}
                onClick={() => onRowClick && onRowClick(row, index)}
              >
                {tableColumns.map(column => (
                  <td key={column.key} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {column.render ? column.render(row[column.key], row, index) : row[column.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {enablePagination && totalPages > 1 && (
        <div className="px-6 py-4 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-700">
              Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, processedData.length)} of {processedData.length} results
            </div>
            
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              
              <div className="flex space-x-1">
                {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                  const page = i + 1;
                  return (
                    <button
                      key={page}
                      onClick={() => setCurrentPage(page)}
                      className={cn(
                        'px-3 py-1 border rounded-md text-sm font-medium',
                        currentPage === page
                          ? 'border-blue-500 bg-blue-50 text-blue-600'
                          : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                      )}
                    >
                      {page}
                    </button>
                  );
                })}
              </div>
              
              <button
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="px-3 py-1 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataTable;