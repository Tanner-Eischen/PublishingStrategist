import React from 'react';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

/**
 * Chart export utilities for various formats
 */
class ChartExport {
  /**
   * Export chart to various formats
   * @param {string} format - Export format (png, jpg, pdf, csv, json)
   * @param {Object} data - Chart data and metadata
   * @param {HTMLElement} chartElement - Chart DOM element
   * @returns {Promise<boolean>} Success status
   */
  static async exportChart(format, data, chartElement) {
    try {
      switch (format.toLowerCase()) {
        case 'png':
          return await this.exportAsPNG(chartElement, data);
        case 'jpg':
        case 'jpeg':
          return await this.exportAsJPG(chartElement, data);
        case 'pdf':
          return await this.exportAsPDF(chartElement, data);
        case 'csv':
          return this.exportAsCSV(data);
        case 'json':
          return this.exportAsJSON(data);
        case 'svg':
          return await this.exportAsSVG(chartElement, data);
        default:
          throw new Error(`Unsupported export format: ${format}`);
      }
    } catch (error) {
      console.error('Export failed:', error);
      return false;
    }
  }

  /**
   * Export chart as PNG image
   */
  static async exportAsPNG(element, data) {
    if (!element) throw new Error('Chart element not found');

    const canvas = await html2canvas(element, {
      backgroundColor: '#ffffff',
      scale: 2,
      logging: false,
      useCORS: true
    });

    const link = document.createElement('a');
    link.download = `${this.generateFilename(data, 'png')}`;
    link.href = canvas.toDataURL('image/png');
    link.click();

    return true;
  }

  /**
   * Export chart as JPG image
   */
  static async exportAsJPG(element, data) {
    if (!element) throw new Error('Chart element not found');

    const canvas = await html2canvas(element, {
      backgroundColor: '#ffffff',
      scale: 2,
      logging: false,
      useCORS: true
    });

    const link = document.createElement('a');
    link.download = `${this.generateFilename(data, 'jpg')}`;
    link.href = canvas.toDataURL('image/jpeg', 0.9);
    link.click();

    return true;
  }

  /**
   * Export chart as PDF
   */
  static async exportAsPDF(element, data) {
    if (!element) throw new Error('Chart element not found');

    const canvas = await html2canvas(element, {
      backgroundColor: '#ffffff',
      scale: 2,
      logging: false,
      useCORS: true
    });

    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF({
      orientation: canvas.width > canvas.height ? 'landscape' : 'portrait',
      unit: 'mm',
      format: 'a4'
    });

    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = pdf.internal.pageSize.getHeight();
    const imgWidth = canvas.width;
    const imgHeight = canvas.height;
    const ratio = Math.min(pdfWidth / imgWidth, pdfHeight / imgHeight);
    const imgX = (pdfWidth - imgWidth * ratio) / 2;
    const imgY = 30;

    // Add title
    if (data.title) {
      pdf.setFontSize(16);
      pdf.text(data.title, pdfWidth / 2, 20, { align: 'center' });
    }

    // Add chart
    pdf.addImage(imgData, 'PNG', imgX, imgY, imgWidth * ratio, imgHeight * ratio);

    // Add metadata
    let yPos = imgY + (imgHeight * ratio) + 20;
    pdf.setFontSize(10);
    
    if (data.subtitle) {
      pdf.text(`Subtitle: ${data.subtitle}`, 20, yPos);
      yPos += 10;
    }
    
    pdf.text(`Generated: ${new Date().toLocaleString()}`, 20, yPos);
    yPos += 10;
    
    if (data.data && data.data.length) {
      pdf.text(`Data Points: ${data.data.length}`, 20, yPos);
    }

    pdf.save(`${this.generateFilename(data, 'pdf')}`);
    return true;
  }

  /**
   * Export data as CSV
   */
  static exportAsCSV(data) {
    if (!data.data || !Array.isArray(data.data)) {
      throw new Error('No data available for CSV export');
    }

    const csvData = data.data;
    const headers = Object.keys(csvData[0] || {});
    
    let csvContent = headers.join(',') + '\n';
    
    csvData.forEach(row => {
      const values = headers.map(header => {
        const value = row[header];
        // Escape commas and quotes in CSV
        if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return value;
      });
      csvContent += values.join(',') + '\n';
    });

    // Add metadata as comments
    if (data.title) {
      csvContent = `# ${data.title}\n` + csvContent;
    }
    if (data.subtitle) {
      csvContent = `# ${data.subtitle}\n` + csvContent;
    }
    csvContent = `# Generated: ${new Date().toISOString()}\n` + csvContent;

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${this.generateFilename(data, 'csv')}`;
    link.click();

    return true;
  }

  /**
   * Export data as JSON
   */
  static exportAsJSON(data) {
    const exportData = {
      metadata: {
        title: data.title,
        subtitle: data.subtitle,
        chartType: data.chartType,
        exportedAt: new Date().toISOString(),
        dataPoints: data.data?.length || 0
      },
      data: data.data || []
    };

    const jsonString = JSON.stringify(exportData, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${this.generateFilename(data, 'json')}`;
    link.click();

    return true;
  }

  /**
   * Export chart as SVG (if supported by the chart library)
   */
  static async exportAsSVG(element, data) {
    // Try to find SVG element within the chart
    const svgElement = element.querySelector('svg');
    
    if (!svgElement) {
      // Fallback to PNG if no SVG found
      return await this.exportAsPNG(element, data);
    }

    const svgData = new XMLSerializer().serializeToString(svgElement);
    const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(svgBlob);
    link.download = `${this.generateFilename(data, 'svg')}`;
    link.click();

    return true;
  }

  /**
   * Generate filename for export
   */
  static generateFilename(data, extension) {
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:.]/g, '-');
    const title = data.title ? data.title.replace(/[^a-zA-Z0-9]/g, '_') : 'chart';
    return `${title}_${timestamp}.${extension}`;
  }

  /**
   * Get available export formats
   */
  static getAvailableFormats() {
    return [
      { value: 'png', label: 'PNG Image', icon: '🖼️' },
      { value: 'jpg', label: 'JPG Image', icon: '📷' },
      { value: 'pdf', label: 'PDF Document', icon: '📄' },
      { value: 'svg', label: 'SVG Vector', icon: '🎨' },
      { value: 'csv', label: 'CSV Data', icon: '📊' },
      { value: 'json', label: 'JSON Data', icon: '📋' }
    ];
  }

  /**
   * Batch export multiple formats
   */
  static async batchExport(formats, data, chartElement) {
    const results = {};
    
    for (const format of formats) {
      try {
        results[format] = await this.exportChart(format, data, chartElement);
      } catch (error) {
        console.error(`Failed to export as ${format}:`, error);
        results[format] = false;
      }
    }
    
    return results;
  }
}

// Export dropdown component
export const ExportDropdown = ({ 
  onExport, 
  disabled = false, 
  formats = ChartExport.getAvailableFormats(),
  className = ''
}) => {
  const [isOpen, setIsOpen] = React.useState(false);

  const handleExport = (format) => {
    onExport(format);
    setIsOpen(false);
  };

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
      >
        Export
        <svg className="ml-2 -mr-0.5 h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
      </button>

      {isOpen && (
        <div className="origin-top-right absolute right-0 mt-2 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-50">
          <div className="py-1">
            {formats.map((format) => (
              <button
                key={format.value}
                onClick={() => handleExport(format.value)}
                className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
              >
                <span className="mr-3">{format.icon}</span>
                {format.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ChartExport;