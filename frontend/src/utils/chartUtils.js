/**
 * Utility functions for transforming API chart data to Chart.js format
 */

/**
 * Transform API chart data to Chart.js compatible format
 * @param {Object} apiChartData - Chart data from API
 * @returns {Object} Chart.js compatible data structure
 */
export function transformChartData(apiChartData) {
  if (!apiChartData || !apiChartData.data) {
    return {
      labels: [],
      datasets: []
    };
  }

  const { type, data, labels, colors = [] } = apiChartData;
  
  // Default colors if none provided
  const defaultColors = [
    'rgba(59, 130, 246, 0.8)',   // blue
    'rgba(16, 185, 129, 0.8)',   // green
    'rgba(245, 158, 11, 0.8)',   // yellow
    'rgba(239, 68, 68, 0.8)',    // red
    'rgba(139, 92, 246, 0.8)',   // purple
    'rgba(236, 72, 153, 0.8)',   // pink
    'rgba(6, 182, 212, 0.8)',    // cyan
    'rgba(34, 197, 94, 0.8)'     // emerald
  ];

  const borderColors = [
    'rgba(59, 130, 246, 1)',
    'rgba(16, 185, 129, 1)',
    'rgba(245, 158, 11, 1)',
    'rgba(239, 68, 68, 1)',
    'rgba(139, 92, 246, 1)',
    'rgba(236, 72, 153, 1)',
    'rgba(6, 182, 212, 1)',
    'rgba(34, 197, 94, 1)'
  ];

  switch (type.toLowerCase()) {
    case 'bar':
      return transformBarChartData(data, labels, colors, defaultColors, borderColors);
    
    case 'line':
      return transformLineChartData(data, labels, colors, defaultColors, borderColors);
    
    case 'pie':
    case 'doughnut':
      return transformPieChartData(data, colors, defaultColors);
    
    case 'scatter':
      return transformScatterChartData(data, colors, defaultColors, borderColors);
    
    default:
      console.warn(`Unsupported chart type: ${type}`);
      return {
        labels: [],
        datasets: []
      };
  }
}

/**
 * Transform data for bar charts
 */
function transformBarChartData(data, labels, colors, defaultColors, borderColors) {
  const chartLabels = labels || data.map(item => item.name || item.label || item.x);
  const values = data.map(item => item.score || item.value || item.y);
  
  return {
    labels: chartLabels,
    datasets: [{
      label: 'Values',
      data: values,
      backgroundColor: colors.length > 0 ? colors : defaultColors,
      borderColor: borderColors,
      borderWidth: 1
    }]
  };
}

/**
 * Transform data for line charts
 */
function transformLineChartData(data, labels, colors, defaultColors, borderColors) {
  const chartLabels = labels || data.map(item => item.name || item.label || item.x);
  const values = data.map(item => item.score || item.value || item.y);
  
  return {
    labels: chartLabels,
    datasets: [{
      label: 'Values',
      data: values,
      backgroundColor: (colors && colors.length > 0) ? colors[0] : defaultColors[0],
      borderColor: (colors && colors.length > 0) ? colors[0] : borderColors[0],
      borderWidth: 2,
      fill: false,
      tension: 0.4
    }]
  };
}

/**
 * Transform data for pie/doughnut charts
 */
function transformPieChartData(data, colors, defaultColors) {
  const chartLabels = data.map(item => item.label || item.name);
  const values = data.map(item => item.value || item.score);
  
  return {
    labels: chartLabels,
    datasets: [{
      data: values,
      backgroundColor: colors.length > 0 ? colors : defaultColors.slice(0, data.length),
      borderWidth: 1,
      borderColor: '#ffffff'
    }]
  };
}

/**
 * Transform data for scatter charts
 */
function transformScatterChartData(data, colors, defaultColors, borderColors) {
  const scatterData = data.map(item => ({
    x: item.x,
    y: item.y,
    label: item.label
  }));
  
  return {
    datasets: [{
      label: 'Data Points',
      data: scatterData,
      backgroundColor: (colors && colors.length > 0) ? colors[0] : defaultColors[0],
      borderColor: (colors && colors.length > 0) ? colors[0] : borderColors[0],
      borderWidth: 1
    }]
  };
}

/**
 * Validate chart data structure
 * @param {Object} chartData - Chart data to validate
 * @returns {boolean} True if valid
 */
export function validateChartData(chartData) {
  if (!chartData) return false;
  if (!chartData.type) return false;
  if (!chartData.data || !Array.isArray(chartData.data)) return false;
  if (chartData.data.length === 0) return false;
  
  return true;
}