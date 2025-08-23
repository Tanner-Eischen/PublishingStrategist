import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import ChartRenderer from '../ChartRenderer';
import DataTable from '../DataTable';
import ChartDashboard from '../ChartDashboard';

// Mock data for testing
const mockChartData = [
  { name: 'Category A', value: 85, competition: 'low' },
  { name: 'Category B', value: 72, competition: 'medium' },
  { name: 'Category C', value: 91, competition: 'high' }
];

const mockTableColumns = [
  { key: 'name', label: 'Name', sortable: true, filterable: true },
  { key: 'value', label: 'Value', sortable: true },
  { key: 'competition', label: 'Competition', filterable: true }
];

describe('Chart Components', () => {
  describe('ChartRenderer', () => {
    test('renders bar chart with data', () => {
      render(
        <ChartRenderer
          data={mockChartData}
          type="bar"
          library="chartjs"
        />
      );
      
      // Chart should render without errors
      expect(screen.queryByText('Loading chart...')).not.toBeInTheDocument();
    });

    test('shows loading state when no data', () => {
      render(
        <ChartRenderer
          data={[]}
          type="bar"
          library="chartjs"
        />
      );
      
      expect(screen.getByText('Loading chart...')).toBeInTheDocument();
    });

    test('supports different chart types', () => {
      const { rerender } = render(
        <ChartRenderer
          data={mockChartData}
          type="pie"
          library="recharts"
        />
      );
      
      // Should render without errors
      expect(screen.queryByText('Loading chart...')).not.toBeInTheDocument();
      
      // Test line chart
      rerender(
        <ChartRenderer
          data={mockChartData}
          type="line"
          library="recharts"
        />
      );
      
      expect(screen.queryByText('Loading chart...')).not.toBeInTheDocument();
    });
  });

  describe('DataTable', () => {
    test('renders table with data and columns', () => {
      render(
        <DataTable
          data={mockChartData}
          columns={mockTableColumns}
          title="Test Table"
        />
      );
      
      expect(screen.getByText('Test Table')).toBeInTheDocument();
      expect(screen.getByText('Category A')).toBeInTheDocument();
      expect(screen.getByText('Category B')).toBeInTheDocument();
      expect(screen.getByText('Category C')).toBeInTheDocument();
    });

    test('shows empty state when no data', () => {
      render(
        <DataTable
          data={[]}
          columns={mockTableColumns}
          emptyMessage="No data found"
        />
      );
      
      expect(screen.getByText('No data found')).toBeInTheDocument();
    });

    test('enables search functionality', () => {
      render(
        <DataTable
          data={mockChartData}
          columns={mockTableColumns}
          enableSearch={true}
        />
      );
      
      const searchInput = screen.getByPlaceholderText('Search all columns...');
      expect(searchInput).toBeInTheDocument();
      
      // Test search functionality
      fireEvent.change(searchInput, { target: { value: 'Category A' } });
      expect(screen.getByText('Category A')).toBeInTheDocument();
    });

    test('supports sorting', () => {
      render(
        <DataTable
          data={mockChartData}
          columns={mockTableColumns}
          enableSorting={true}
        />
      );
      
      // Click on sortable column header
      const nameHeader = screen.getByText('Name');
      fireEvent.click(nameHeader);
      
      // Should still show data (sorting applied)
      expect(screen.getByText('Category A')).toBeInTheDocument();
    });

    test('supports pagination', () => {
      const largeDataset = Array.from({ length: 25 }, (_, i) => ({
        name: `Category ${i + 1}`,
        value: Math.floor(Math.random() * 100),
        competition: ['low', 'medium', 'high'][i % 3]
      }));

      render(
        <DataTable
          data={largeDataset}
          columns={mockTableColumns}
          enablePagination={true}
          pageSize={10}
        />
      );
      
      // Should show pagination controls
      expect(screen.getByText('Next')).toBeInTheDocument();
      expect(screen.getByText('Previous')).toBeInTheDocument();
    });
  });

  describe('ChartDashboard', () => {
    const mockDashboardData = {
      chart1: {
        title: 'Chart 1',
        type: 'bar',
        data: mockChartData
      },
      chart2: {
        title: 'Chart 2',
        type: 'pie',
        data: mockChartData
      },
      table1: {
        title: 'Table 1',
        type: 'table',
        data: mockChartData,
        columns: mockTableColumns
      }
    };

    test('renders grid layout', () => {
      render(
        <ChartDashboard
          data={mockDashboardData}
          layout="grid"
        />
      );
      
      expect(screen.getByText('Chart 1')).toBeInTheDocument();
      expect(screen.getByText('Chart 2')).toBeInTheDocument();
      expect(screen.getByText('Table 1')).toBeInTheDocument();
    });

    test('renders tab layout', () => {
      render(
        <ChartDashboard
          data={mockDashboardData}
          layout="tabs"
        />
      );
      
      // Should show tab navigation
      expect(screen.getByText('Chart 1')).toBeInTheDocument();
      expect(screen.getByText('Chart 2')).toBeInTheDocument();
      expect(screen.getByText('Table 1')).toBeInTheDocument();
    });

    test('renders accordion layout', () => {
      render(
        <ChartDashboard
          data={mockDashboardData}
          layout="accordion"
        />
      );
      
      // Should show accordion headers
      expect(screen.getByText('Chart 1')).toBeInTheDocument();
      expect(screen.getByText('Chart 2')).toBeInTheDocument();
      expect(screen.getByText('Table 1')).toBeInTheDocument();
    });

    test('shows empty state when no data', () => {
      render(
        <ChartDashboard
          data={{}}
          layout="grid"
        />
      );
      
      expect(screen.getByText('No chart data available')).toBeInTheDocument();
    });
  });
});