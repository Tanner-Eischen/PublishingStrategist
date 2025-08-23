import React, { useState, useMemo } from 'react';
import { cn } from '../../lib/utils';
import ChartContainer from './ChartContainer';
import DataTable from './DataTable';

/**
 * Responsive dashboard component for displaying multiple charts
 */
const ChartDashboard = ({
  data = {},
  layout = 'grid', // 'grid', 'tabs', 'accordion'
  responsive = true,
  className,
  onChartClick,
  enableExport = true
}) => {
  const [activeTab, setActiveTab] = useState(0);
  const [expandedSections, setExpandedSections] = useState(new Set([0]));

  // Process dashboard data
  const dashboardItems = useMemo(() => {
    if (Array.isArray(data)) return data;
    
    return Object.entries(data).map(([key, value]) => ({
      id: key,
      title: key.charAt(0).toUpperCase() + key.slice(1).replace(/([A-Z])/g, ' $1'),
      ...value
    }));
  }, [data]);

  const toggleSection = (index) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedSections(newExpanded);
  };

  if (dashboardItems.length === 0) {
    return (
      <div className={cn('text-center py-12 text-gray-500', className)}>
        <p>No chart data available</p>
      </div>
    );
  }

  // Grid Layout
  if (layout === 'grid') {
    return (
      <div className={cn(
        'grid gap-6',
        responsive && 'grid-cols-1 lg:grid-cols-2 xl:grid-cols-3',
        className
      )}>
        {dashboardItems.map((item, index) => (
          <div key={item.id || index} className="min-h-0">
            {item.type === 'table' ? (
              <DataTable
                {...item}
                enableExport={enableExport}
                onClick={() => onChartClick?.(item, index)}
              />
            ) : (
              <ChartContainer
                {...item}
                enableExport={enableExport}
                onClick={() => onChartClick?.(item, index)}
              />
            )}
          </div>
        ))}
      </div>
    );
  }

  // Tab Layout
  if (layout === 'tabs') {
    return (
      <div className={cn('bg-white rounded-lg shadow-sm border', className)}>
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6">
            {dashboardItems.map((item, index) => (
              <button
                key={item.id || index}
                onClick={() => setActiveTab(index)}
                className={cn(
                  'py-4 px-1 border-b-2 font-medium text-sm whitespace-nowrap',
                  activeTab === index
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                )}
              >
                {item.title}
              </button>
            ))}
          </nav>
        </div>
        
        <div className="p-6">
          {dashboardItems[activeTab] && (
            dashboardItems[activeTab].type === 'table' ? (
              <DataTable
                {...dashboardItems[activeTab]}
                enableExport={enableExport}
              />
            ) : (
              <ChartContainer
                {...dashboardItems[activeTab]}
                enableExport={enableExport}
              />
            )
          )}
        </div>
      </div>
    );
  }

  // Accordion Layout
  if (layout === 'accordion') {
    return (
      <div className={cn('space-y-4', className)}>
        {dashboardItems.map((item, index) => (
          <div key={item.id || index} className="bg-white rounded-lg shadow-sm border">
            <button
              onClick={() => toggleSection(index)}
              className="w-full px-6 py-4 text-left border-b border-gray-200 hover:bg-gray-50"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-gray-900">{item.title}</h3>
                <svg
                  className={cn(
                    'h-5 w-5 text-gray-500 transition-transform',
                    expandedSections.has(index) && 'rotate-180'
                  )}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </button>
            
            {expandedSections.has(index) && (
              <div className="p-6">
                {item.type === 'table' ? (
                  <DataTable
                    {...item}
                    enableExport={enableExport}
                  />
                ) : (
                  <ChartContainer
                    {...item}
                    enableExport={enableExport}
                  />
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    );
  }

  return null;
};

export default ChartDashboard;