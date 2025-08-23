/**
 * Test runner script for frontend tests
 * 
 * This script runs the React Testing Library tests for the frontend components
 * and generates a test report.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Configuration
const config = {
  testCommand: 'npm test -- --watchAll=false --coverage',
  testReportDir: 'test-reports',
  coverageThreshold: 80,
  visualRegressionDir: 'visual-regression-tests'
};

// Create test report directory if it doesn't exist
if (!fs.existsSync(config.testReportDir)) {
  fs.mkdirSync(config.testReportDir, { recursive: true });
}

// Create visual regression directory if it doesn't exist
if (!fs.existsSync(config.visualRegressionDir)) {
  fs.mkdirSync(config.visualRegressionDir, { recursive: true });
}

// Run the tests
console.log('Running frontend tests...');

try {
  // Run Jest tests
  execSync(config.testCommand, { stdio: 'inherit' });
  
  // Check if coverage report exists
  const coverageReportPath = path.join('coverage', 'coverage-summary.json');
  if (fs.existsSync(coverageReportPath)) {
    const coverageReport = JSON.parse(fs.readFileSync(coverageReportPath, 'utf8'));
    const totalCoverage = coverageReport.total.statements.pct;
    
    console.log(`\nTest coverage: ${totalCoverage}%`);
    
    if (totalCoverage < config.coverageThreshold) {
      console.warn(`⚠️ Warning: Coverage is below threshold of ${config.coverageThreshold}%`);
    } else {
      console.log(`✅ Coverage meets threshold of ${config.coverageThreshold}%`);
    }
    
    // Copy coverage report to test reports directory
    fs.copyFileSync(
      coverageReportPath,
      path.join(config.testReportDir, 'coverage-summary.json')
    );
  }
  
  console.log('\n✅ All frontend tests passed!');
} catch (error) {
  console.error('\n❌ Frontend tests failed!');
  process.exit(1);
}