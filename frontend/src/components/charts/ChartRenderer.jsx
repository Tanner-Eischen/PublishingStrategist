import React, { useMemo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  RadialLinearScale,
  Filler
} from 'chart.js';
import { Line, Bar, Pie, Doughnut, Scatter, Radar, PolarArea } from 'react-chartjs-2';
import {
  LineChart,
  BarChart,
  PieChart,
  AreaChart,
  ScatterChart,
  RadarChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend as RechartsLegend,
  ResponsiveContainer,
  Cell,
  Area,
  Line as RechartsLine,
  Bar as RechartsBar
} from 'recharts';
import { transformChartData } from '../../utils/chartUtils';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  RadialLinearScale,
  Filler
);

/**
 * Universal chart renderer that supports both Chart.js and Recharts
 */
const ChartRenderer = ({
  data,
  type = 'bar',
  library = 'chartjs', // 'chartjs' or 'recharts'
  height = 400,
  responsive = true,
  options = {},
  colors = [],
  animate = true,
  showGrid = true,
  showLegend = true,
  showTooltip = true,
  ...props
}) => {
  // Transform data for the appropriate library
  const chartData = useMemo(() => {
    if (!data || !Array.isArray(data)) return null;
    
    if (library === 'recharts') {
      // Transform for Recharts format
      return data.map((item, index) => ({
        name: item.name || item.label || item.x || `Item ${index + 1}`,
        value: item.value || item.y || item.score || 0,
        ...item
      }));
    } else {
      // Transform for Chart.js format
      return transformChartData({
        type,
        data,
        colors
      });
    }
  }, [data, type, library, colors]);

  // Default colors for charts
  const defaultColors = [
    '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
    '#EC4899', '#06B6D4', '#22C55E', '#F97316', '#6366F1'
  ];

  const chartColors = colors.length > 0 ? colors : defaultColors;

  // Chart.js options
  const chartJsOptions = useMemo(() => ({
    responsive: responsive,
    maintainAspectRatio: false,
    animation: animate ? {} : false,
    plugins: {
      legend: {
        display: showLegend,
        position: 'top',
      },
      tooltip: {
        enabled: showTooltip,
      },
    },
    scales: type !== 'pie' && type !== 'doughnut' && type !== 'radar' && type !== 'polarArea' ? {
      x: {
        grid: {
          display: showGrid,
        },
      },
      y: {
        grid: {
          display: showGrid,
        },
        beginAtZero: true,
      },
    } : {},
    ...options
  }), [responsive, animate, showLegend, showTooltip, showGrid, type, options]);

  if (!chartData) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-2"></div>
          <p>Loading chart...</p>
        </div>
      </div>
    );
  }

  // Render Chart.js charts
  if (library === 'chartjs') {
    const containerStyle = {
      height: responsive ? height : 'auto',
      width: '100%'
    };

    switch (type.toLowerCase()) {
      case 'line':
        return (
          <div style={containerStyle}>
            <Line data={chartData} options={chartJsOptions} {...props} />
          </div>
        );
      
      case 'bar':
        return (
          <div style={containerStyle}>
            <Bar data={chartData} options={chartJsOptions} {...props} />
          </div>
        );
      
      case 'pie':
        return (
          <div style={containerStyle}>
            <Pie data={chartData} options={chartJsOptions} {...props} />
          </div>
        );
      
      case 'doughnut':
        return (
          <div style={containerStyle}>
            <Doughnut data={chartData} options={chartJsOptions} {...props} />
          </div>
        );
      
      case 'scatter':
        return (
          <div style={containerStyle}>
            <Scatter data={chartData} options={chartJsOptions} {...props} />
          </div>
        );
      
      case 'radar':
        return (
          <div style={containerStyle}>
            <Radar data={chartData} options={chartJsOptions} {...props} />
          </div>
        );
      
      case 'polararea':
        return (
          <div style={containerStyle}>
            <PolarArea data={chartData} options={chartJsOptions} {...props} />
          </div>
        );
      
      default:
        return (
          <div style={containerStyle}>
            <Bar data={chartData} options={chartJsOptions} {...props} />
          </div>
        );
    }
  }

  // Render Recharts charts
  if (library === 'recharts') {
    const ResponsiveWrapper = ({ children }) => (
      responsive ? (
        <ResponsiveContainer width="100%" height={height}>
          {children}
        </ResponsiveContainer>
      ) : (
        <div style={{ width: '100%', height }}>
          {children}
        </div>
      )
    );

    switch (type.toLowerCase()) {
      case 'line':
        return (
          <ResponsiveWrapper>
            <LineChart data={chartData} {...props}>
              {showGrid && <CartesianGrid strokeDasharray="3 3" />}
              <XAxis dataKey="name" />
              <YAxis />
              {showTooltip && <RechartsTooltip />}
              {showLegend && <RechartsLegend />}
              <RechartsLine 
                type="monotone" 
                dataKey="value" 
                stroke={chartColors[0]} 
                strokeWidth={2}
                dot={{ fill: chartColors[0] }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveWrapper>
        );
      
      case 'bar':
        return (
          <ResponsiveWrapper>
            <BarChart data={chartData} {...props}>
              {showGrid && <CartesianGrid strokeDasharray="3 3" />}
              <XAxis dataKey="name" />
              <YAxis />
              {showTooltip && <RechartsTooltip />}
              {showLegend && <RechartsLegend />}
              <RechartsBar dataKey="value">
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={chartColors[index % chartColors.length]} />
                ))}
              </RechartsBar>
            </BarChart>
          </ResponsiveWrapper>
        );
      
      case 'pie':
        return (
          <ResponsiveWrapper>
            <PieChart {...props}>
              {showTooltip && <RechartsTooltip />}
              {showLegend && <RechartsLegend />}
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                outerRadius={Math.min(height * 0.3, 120)}
                fill="#8884d8"
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={chartColors[index % chartColors.length]} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveWrapper>
        );
      
      case 'area':
        return (
          <ResponsiveWrapper>
            <AreaChart data={chartData} {...props}>
              {showGrid && <CartesianGrid strokeDasharray="3 3" />}
              <XAxis dataKey="name" />
              <YAxis />
              {showTooltip && <RechartsTooltip />}
              {showLegend && <RechartsLegend />}
              <Area 
                type="monotone" 
                dataKey="value" 
                stroke={chartColors[0]} 
                fill={chartColors[0]}
                fillOpacity={0.3}
              />
            </AreaChart>
          </ResponsiveWrapper>
        );
      
      case 'scatter':
        return (
          <ResponsiveWrapper>
            <ScatterChart data={chartData} {...props}>
              {showGrid && <CartesianGrid strokeDasharray="3 3" />}
              <XAxis dataKey="x" type="number" />
              <YAxis dataKey="y" type="number" />
              {showTooltip && <RechartsTooltip />}
              {showLegend && <RechartsLegend />}
              <Scatter dataKey="value" fill={chartColors[0]} />
            </ScatterChart>
          </ResponsiveWrapper>
        );
      
      case 'radar':
        return (
          <ResponsiveWrapper>
            <RadarChart data={chartData} {...props}>
              {showTooltip && <RechartsTooltip />}
              {showLegend && <RechartsLegend />}
              <Radar
                name="Value"
                dataKey="value"
                stroke={chartColors[0]}
                fill={chartColors[0]}
                fillOpacity={0.3}
              />
            </RadarChart>
          </ResponsiveWrapper>
        );
      
      default:
        return (
          <ResponsiveWrapper>
            <BarChart data={chartData} {...props}>
              {showGrid && <CartesianGrid strokeDasharray="3 3" />}
              <XAxis dataKey="name" />
              <YAxis />
              {showTooltip && <RechartsTooltip />}
              {showLegend && <RechartsLegend />}
              <RechartsBar dataKey="value">
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={chartColors[index % chartColors.length]} />
                ))}
              </RechartsBar>
            </BarChart>
          </ResponsiveWrapper>
        );
    }
  }

  return (
    <div className="flex items-center justify-center h-64 text-gray-500">
      <p>Unsupported chart library: {library}</p>
    </div>
  );
};

export default ChartRenderer;