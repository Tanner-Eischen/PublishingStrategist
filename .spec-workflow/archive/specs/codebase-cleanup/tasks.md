# Codebase Cleanup Tasks

## Phase 1: Preparation and Analysis

- [x] 1.1 Create backup branch for cleanup work
  - File: Git repository
  - Create new branch 'codebase-cleanup' from main
  - Ensure all current work is committed
  - Purpose: Enable rollback if issues arise
  - _Requirements: Risk mitigation strategy_

- [x] 1.2 Run baseline test suite
  - File: pytest.ini, tests/
  - Execute full test suite and record results
  - Document current test coverage metrics
  - Purpose: Establish baseline for comparison
  - _Requirements: Pre-cleanup validation_

- [x] 1.3 Generate dependency analysis report
  - File: Create dependency_analysis.json
  - Map all file imports and dependencies
  - Identify circular dependencies
  - Purpose: Understand code relationships before cleanup
  - _Requirements: Dependency mapping phase_

- [x] 1.4 Analyze Google Trends file dependencies
  - File: src/kdp_strategist/data/trends.py, api/routers/trends_client_router.py
  - Map all files that import trends modules
  - Identify trends-related configuration
  - Purpose: Plan safe removal of trends functionality
  - _Requirements: 1.1, 1.2_

- [x] 1.5 Catalog root-level test files
  - File: Root directory test_*.py files
  - List all 40+ root-level test files
  - Categorize by functionality (unit, integration, e2e)
  - Purpose: Plan test consolidation strategy
  - _Requirements: 2.1, 2.2_

- [x] 1.6 Identify duplicate cache implementations
  - File: cache_manager.py, intelligent_cache.py, unified_cache_manager.py
  - Compare cache system implementations
  - Document feature differences
  - Purpose: Plan cache consolidation
  - _Requirements: 3.1_

- [x] 1.7 Document current application metrics
  - File: Create baseline_metrics.json
  - Record startup time, memory usage, test execution time
  - Count total files and lines of code
  - Purpose: Measure cleanup impact
  - _Requirements: Performance requirements_

## Phase 2: Google Trends Complete Removal

- [x] 2.1 Remove core trends files
  - File: src/kdp_strategist/data/trends.py
  - Delete trends data processing module
  - Purpose: Eliminate trends functionality
  - _Requirements: 1.2.1_

- [x] 2.2 Remove trends client router
  - File: api/routers/trends_client_router.py
  - Delete trends API router
  - Purpose: Remove trends endpoints
  - _Requirements: 1.2.1_

- [x] 2.3 Remove simple trends client
  - File: src/kdp_strategist/clients/simple_trends_client.py
  - Delete trends client implementation
  - Purpose: Eliminate trends client code
  - _Requirements: 1.2.1_

- [x] 2.4 Remove trends-related test files
  - File: test_*trends*.py files
  - Delete all trends test files from root
  - Remove trends tests from tests/ directory
  - Purpose: Clean up trends testing code
  - _Requirements: 1.2.1, 2.2.1_

- [x] 2.5 Update FastAPI main router
  - File: api/main.py
  - Remove trends router registration
  - Update router imports
  - Purpose: Remove trends from API
  - _Requirements: 1.2.3_

- [x] 2.6 Update MCP configuration
  - File: kdp-strategist.mcp.json
  - Remove trends-related tools
  - Update tool descriptions
  - Purpose: Remove trends from MCP interface
  - _Requirements: 1.1.1_

- [x] 2.7 Clean trends from requirements.txt
  - File: requirements.txt
  - Remove pytrends dependency
  - Remove other trends-related packages
  - Purpose: Eliminate trends dependencies
  - _Requirements: 6.1.1_

- [-] 2.8 Update import statements
  - File: Multiple files importing trends modules
  - Remove all trends imports
  - Update affected function signatures
  - Purpose: Fix broken imports after trends removal
  - _Requirements: 1.1.2, 1.2.2_

- [x] 2.9 Remove trends configuration
  - File: config/settings.py, .env.example
  - Remove trends API keys and settings
  - Clean environment variable references
  - Purpose: Eliminate trends configuration
  - _Requirements: 1.1.3_

- [x] 2.10 Update documentation
  - File: README.md, docs/
  - Remove all Google Trends references
  - Update feature lists
  - Purpose: Clean documentation of trends references
  - _Requirements: 1.1.4, 5.1.1_

- [x] 2.11 Validate trends removal
  - File: Entire codebase
  - Search for remaining trends references
  - Run import validation
  - Purpose: Ensure complete trends removal
  - _Requirements: 1.1.1_

## Phase 3: Test File Consolidation

- [x] 3.1 Analyze root-level test files
  - File: All test_*.py files in root
  - Categorize tests by type and functionality
  - Identify duplicate test cases
  - Purpose: Plan consolidation strategy
  - _Requirements: 2.1.3, 2.2.2_

- [x] 3.2 Create consolidated cache tests
  - File: tests/unit/test_cache_system.py
  - Merge test_enhanced_cache_demo.py and related cache tests
  - Consolidate cache testing functionality
  - Purpose: Unified cache testing
  - _Requirements: 2.1.2, 2.2.2_

- [x] 3.3 Create consolidated Keepa tests
  - File: tests/unit/test_keepa_client.py
  - Merge test_keepa_*.py files
  - Consolidate Keepa API testing
  - Purpose: Unified Keepa testing
  - _Requirements: 2.1.2, 2.2.2_

- [x] 3.4 Create consolidated listing tests
  - File: tests/unit/test_listing_generation.py
  - Merge test_listing_generation_*.py files
  - Consolidate listing functionality tests
  - Purpose: Unified listing testing
  - _Requirements: 2.1.2, 2.2.2_

- [x] 3.5 Create consolidated competitor tests
  - File: tests/unit/test_competitor_analysis.py
  - Merge test_competitor_*.py files
  - Consolidate competitor analysis tests
  - Purpose: Unified competitor testing
  - _Requirements: 2.1.2, 2.2.2_

- [x] 3.6 Create consolidated API tests
  - File: tests/integration/test_api_endpoints.py
  - Merge test_fastapi_endpoints.py and related API tests
  - Consolidate endpoint testing
  - Purpose: Unified API testing
  - _Requirements: 2.1.2, 2.2.2_

- [x] 3.7 Create consolidated MCP tests
  - File: tests/integration/test_mcp_integration.py
  - Merge test_mcp_*.py files
  - Consolidate MCP functionality tests
  - Purpose: Unified MCP testing
  - _Requirements: 2.1.2, 2.2.2_

- [x] 3.8 Create consolidated stress tests
  - File: tests/performance/test_stress_scenarios.py
  - Merge test_stress_testing_*.py files
  - Consolidate performance testing
  - Purpose: Unified performance testing
  - _Requirements: 2.1.2, 2.2.2_

- [x] 3.9 Delete root-level test files
  - File: test_agent_trend_validation.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.10 Delete root-level test files
  - File: test_amazon_suggestions.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.11 Delete root-level test files
  - File: test_backend.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.12 Delete root-level test files
  - File: test_basic_configuration_setup.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.13 Delete root-level test files
  - File: test_competitor_analysis_tool.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.14 Delete root-level test files
  - File: test_competitor_api.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.15 Delete root-level test files
  - File: test_comprehensive_endpoints.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.16 Delete root-level test files
  - File: test_config_improvements.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.17 Delete root-level test files
  - File: test_config_validator_import.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.18 Delete root-level test files
  - File: test_enhanced_cache_demo.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.19 Delete root-level test files
  - File: test_enhanced_keepa_parsing.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.20 Delete root-level test files
  - File: test_fastapi_endpoints.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.21 Delete root-level test files
  - File: test_keepa_config_import.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.22 Delete root-level test files
  - File: test_keepa_error_handling.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.23 Delete root-level test files
  - File: test_keepa_simple.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.24 Delete root-level test files
  - File: test_keepa_token.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.25 Delete root-level test files
  - File: test_listing_generation_mcp.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.26 Delete root-level test files
  - File: test_listing_generation_tool.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.27 Delete root-level test files
  - File: test_mcp_fetch_direct.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.28 Delete root-level test files
  - File: test_mcp_fetch_server.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.29 Delete root-level test files
  - File: test_minimal_validator.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.30 Delete root-level test files
  - File: test_mock_data_reality.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.31 Delete root-level test files
  - File: test_niche_discovery_basic.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.32 Delete root-level test files
  - File: test_price_history_integration.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.33 Delete root-level test files
  - File: test_rate_limiting_compliance.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.34 Delete root-level test files
  - File: test_real_competitor_analysis.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.35 Delete root-level test files
  - File: test_server_integration.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.36 Delete root-level test files
  - File: test_stress_testing_fastapi.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.37 Delete root-level test files
  - File: test_stress_testing_mcp.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.38 Delete root-level test files
  - File: test_stress_testing_tool.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.39 Delete root-level test files
  - File: test_tool_endpoints.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.40 Delete root-level test files
  - File: test_validation_only.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.41 Delete root-level test files
  - File: test_validation_simple.py
  - Remove after consolidation
  - Purpose: Clean up root directory
  - _Requirements: 2.1.1_

- [x] 3.42 Update test runner configuration
  - File: pytest.ini
  - Update test discovery paths
  - Configure new test structure
  - Purpose: Support consolidated test structure
  - _Requirements: 2.2.3_

- [x] 3.43 Validate consolidated test suite
  - File: tests/
  - Run full test suite
  - Verify all tests pass
  - Purpose: Ensure test consolidation success
  - _Requirements: 2.2.3_

## Phase 4: Code Deduplication

- [x] 4.1 Consolidate cache system
  - File: src/kdp_strategist/utils/unified_cache_manager.py
  - Use unified cache as primary implementation
  - Update all cache consumers
  - Purpose: Single cache system
  - _Requirements: 3.1.1, 3.1.3_

- [x] 4.2 Remove redundant cache files
  - File: cache_manager.py, intelligent_cache.py
  - Delete duplicate cache implementations
  - Preserve useful features in unified cache
  - Purpose: Eliminate cache duplication
  - _Requirements: 3.1.2_

- [x] 4.3 Consolidate Keepa clients
  - File: src/kdp_strategist/clients/keepa_client.py
  - Merge features from improved and fallback clients
  - Remove duplicate client files
  - Purpose: Single Keepa client implementation
  - _Requirements: 3.2.1_

- [x] 4.4 Remove duplicate Keepa files
  - File: keepa_client_improved.py, keepa_fallback.py
  - Delete redundant Keepa implementations
  - Update imports to use primary client
  - Purpose: Eliminate Keepa duplication
  - _Requirements: 3.2.1_

- [x] 4.5 Standardize HTTP client usage
  - File: Multiple files with HTTP requests
  - Use consistent HTTP client library
  - Remove duplicate HTTP handling
  - Purpose: Consistent HTTP implementation
  - _Requirements: 3.2.2_

- [x] 4.6 Consolidate error handling
  - File: src/kdp_strategist/exceptions.py
  - Standardize error handling patterns
  - Remove duplicate error classes
  - Purpose: Consistent error handling
  - _Requirements: 3.2.3_

- [x] 4.7 Consolidate configuration files
  - File: config/settings.py
  - Merge duplicate configuration logic
  - Remove redundant config files
  - Purpose: Single configuration system
  - _Requirements: 4.2.1_

- [-] 4.8 Validate deduplication
  - File: Entire codebase
  - Run tests after deduplication
  - Verify functionality preserved
  - Purpose: Ensure deduplication success
  - _Requirements: 3.1, 3.2_

## Phase 5: Final Cleanup and Optimization

- [x] 5.1 Organize remaining files
  - File: Root directory files
  - Move utility scripts to appropriate directories
  - Remove temporary files
  - Purpose: Clean file organization
  - _Requirements: 4.1.1, 4.1.3_

- [ ] 5.2 Clean up documentation
  - File: docs/, README.md
  - Update documentation to reflect changes
  - Remove outdated information
  - Purpose: Accurate documentation
  - _Requirements: 5.1.2, 5.1.3_

- [ ] 5.3 Update dependency files
  - File: requirements.txt, setup.py
  - Remove unused dependencies
  - Update package versions
  - Purpose: Clean dependency management
  - _Requirements: 6.1.2, 6.1.3_

- [ ] 5.4 Clean configuration files
  - File: config/, .env.example
  - Remove unused configuration parameters
  - Update configuration documentation
  - Purpose: Clean configuration
  - _Requirements: 4.2.3_

- [ ] 5.5 Remove debug and utility files
  - File: debug_*.py, diagnose_*.py
  - Remove temporary debugging files
  - Keep essential utility scripts
  - Purpose: Clean development files
  - _Requirements: 4.1.1_

- [ ] 5.6 Update import statements
  - File: All Python files
  - Remove unused imports
  - Organize imports per PEP 8
  - Purpose: Clean import structure
  - _Requirements: 6.2.1, 6.2.2_

- [ ] 5.7 Clean code comments
  - File: All source files
  - Remove outdated comments
  - Update comments to reflect current code
  - Purpose: Accurate code documentation
  - _Requirements: 5.2.1, 5.2.2_

- [ ] 5.8 Remove empty directories
  - File: Project directory structure
  - Delete empty directories
  - Ensure clean directory structure
  - Purpose: Clean directory organization
  - _Requirements: 4.1.3_

- [ ] 5.9 Final validation
  - File: Entire codebase
  - Run complete test suite
  - Verify application starts correctly
  - Purpose: Ensure cleanup success
  - _Requirements: Success criteria_

- [ ] 5.10 Generate cleanup report
  - File: Create cleanup_report.md
  - Document files removed and changes made
  - Report performance improvements
  - Purpose: Document cleanup results
  - _Requirements: Success metrics_

## Success Criteria

### Quantitative Targets
- 30-40% reduction in total files
- 20-30% reduction in total lines of code
- 25% improvement in test execution time
- 15% improvement in application startup time
- 10% reduction in runtime memory usage

### Qualitative Targets
- Zero Google Trends references
- All tests passing
- No broken imports
- Improved code organization
- Consistent coding patterns

### Risk Mitigation
- Backup branch available for rollback
- Incremental testing after each phase
- Dependency validation before removal
- Configuration backup and validation

### Implementation Notes
- Estimated time: 2-3 days
- Dependencies: Must complete phases in order
- Testing: Run tests after each phase
- Rollback: Available via backup branch