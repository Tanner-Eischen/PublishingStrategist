# Codebase Cleanup Design Document

## Overview

This design document outlines the technical approach for cleaning up the KDP Strategist codebase by systematically removing Google Trends functionality, consolidating test files, eliminating duplicates, and improving overall code organization. The cleanup will be performed in phases to minimize risk and ensure the application remains functional throughout the process.

## Architecture

### Cleanup Strategy

The cleanup will follow a **phased approach** with dependency analysis to ensure safe removal of components:

1. **Dependency Mapping Phase**: Identify all dependencies and references
2. **Google Trends Removal Phase**: Remove all trends-related functionality
3. **Test Consolidation Phase**: Organize and consolidate test files
4. **Code Deduplication Phase**: Remove duplicate implementations
5. **Final Cleanup Phase**: Clean up remaining artifacts and documentation

### Risk Mitigation

- **Backup Strategy**: Create backup of current state before major changes
- **Incremental Testing**: Run tests after each phase to ensure functionality
- **Rollback Plan**: Maintain ability to revert changes if issues arise
- **Dependency Validation**: Verify no broken imports or missing references

## Components and Interfaces

### 1. Google Trends Removal Component

#### Files to Remove
```
src/kdp_strategist/data/trends.py
api/routers/trends_client_router.py
src/kdp_strategist/clients/simple_trends_client.py
test_*trends*.py (all trends-related test files)
docs/*trends* (all trends documentation)
```

#### Dependencies to Update
- **FastAPI Router Registration**: Remove trends router from `api/main.py`
- **Import Statements**: Update all files importing trends modules
- **Configuration**: Remove trends-related environment variables
- **MCP Configuration**: Update `kdp-strategist.mcp.json` to remove trends tools

#### Interface Changes
- Remove trends endpoints from API
- Update agent tools to exclude trends functionality
- Modify niche discovery to work without trends data

### 2. Test File Consolidation Component

#### Current Test Structure Analysis
```
Root Level Tests (40+ files):
- test_*.py files scattered in project root
- Inconsistent naming and organization
- Duplicate test functionality

Existing tests/ Directory:
- tests/unit/ (proper unit tests)
- tests/integration/ (integration tests)
- tests/e2e/ (end-to-end tests)
- tests/validation/ (validation tests)
```

#### Target Structure
```
tests/
├── unit/
│   ├── test_cache_system.py (consolidated cache tests)
│   ├── test_keepa_client.py (consolidated Keepa tests)
│   ├── test_listing_generation.py (consolidated listing tests)
│   └── test_competitor_analysis.py (consolidated competitor tests)
├── integration/
│   ├── test_api_endpoints.py (consolidated API tests)
│   ├── test_mcp_integration.py (consolidated MCP tests)
│   └── test_client_integration.py (consolidated client tests)
├── e2e/
│   └── test_user_workflows.py (consolidated workflow tests)
└── performance/
    └── test_stress_scenarios.py (consolidated stress tests)
```

#### Consolidation Strategy
- **Group by Functionality**: Merge tests testing similar components
- **Remove Duplicates**: Eliminate redundant test cases
- **Standardize Naming**: Use consistent test file naming convention
- **Update Test Runner**: Modify `pytest.ini` and test runners for new structure

### 3. Code Deduplication Component

#### Cache System Consolidation

**Current State**:
- `cache_manager.py` - Multi-tier cache implementation
- `intelligent_cache.py` - Smart caching with analytics
- `cache_analytics.py` - Cache performance monitoring
- `cache_monitor.py` - Cache health monitoring
- `unified_cache_manager.py` - Recently created unified implementation

**Target State**:
- Use `unified_cache_manager.py` as single cache implementation
- Remove redundant cache files
- Update all cache consumers to use unified interface

#### Client Code Deduplication

**Keepa Client Consolidation**:
- Keep `keepa_client.py` as primary implementation
- Remove `keepa_client_improved.py` and `keepa_fallback.py`
- Merge useful features into primary client

**HTTP Client Standardization**:
- Standardize on single HTTP client library
- Remove duplicate HTTP handling code
- Consolidate error handling patterns

### 4. Configuration Consolidation Component

#### Environment Configuration
- Consolidate duplicate `.env` handling
- Remove unused configuration parameters
- Standardize configuration validation

#### Feature Flags
- Remove trends-related feature flags
- Consolidate remaining feature flag logic
- Update feature flag documentation

## Data Models

### Cleanup Tracking Model

```python
@dataclass
class CleanupOperation:
    operation_type: str  # 'remove', 'consolidate', 'move'
    source_files: List[str]
    target_files: Optional[List[str]]
    dependencies: List[str]
    rollback_info: Dict[str, Any]
    status: str  # 'pending', 'in_progress', 'completed', 'failed'
```

### File Dependency Model

```python
@dataclass
class FileDependency:
    file_path: str
    imports: List[str]
    imported_by: List[str]
    references: List[str]
    safe_to_remove: bool
```

## Error Handling

### Cleanup Error Scenarios

1. **Import Resolution Errors**
   - Detection: Run import validation after each phase
   - Recovery: Restore removed files and update imports
   - Prevention: Comprehensive dependency analysis before removal

2. **Test Failures**
   - Detection: Run test suite after each consolidation
   - Recovery: Revert test file changes and investigate
   - Prevention: Careful test merging with conflict resolution

3. **Configuration Errors**
   - Detection: Validate configuration loading
   - Recovery: Restore original configuration files
   - Prevention: Backup configuration before changes

### Error Recovery Strategy

```python
class CleanupErrorHandler:
    def handle_import_error(self, error: ImportError, operation: CleanupOperation):
        # Restore removed files
        # Update import statements
        # Log error details
        
    def handle_test_failure(self, failures: List[str], operation: CleanupOperation):
        # Revert test changes
        # Analyze failure causes
        # Provide remediation steps
        
    def rollback_operation(self, operation: CleanupOperation):
        # Restore original state
        # Update tracking
        # Notify of rollback
```

## Testing Strategy

### Pre-Cleanup Validation

1. **Baseline Test Run**: Ensure all tests pass before cleanup
2. **Dependency Analysis**: Map all file dependencies
3. **Import Validation**: Verify all imports resolve correctly
4. **Configuration Check**: Validate all configuration loads properly

### Phase-by-Phase Testing

1. **After Google Trends Removal**:
   - Run full test suite
   - Verify no import errors
   - Test API endpoints still work
   - Validate MCP tools function correctly

2. **After Test Consolidation**:
   - Run consolidated test suite
   - Verify test coverage maintained
   - Check test execution time
   - Validate test reporting

3. **After Code Deduplication**:
   - Run integration tests
   - Verify cache system works
   - Test client functionality
   - Check performance metrics

4. **Final Validation**:
   - Full system test
   - Performance benchmarking
   - Documentation review
   - Deployment test

### Test Automation

```python
class CleanupTestRunner:
    def run_phase_tests(self, phase: str) -> TestResults:
        # Run appropriate test suite for phase
        # Collect results and metrics
        # Generate phase report
        
    def validate_imports(self) -> List[ImportError]:
        # Check all Python files for import errors
        # Return list of broken imports
        
    def check_test_coverage(self) -> CoverageReport:
        # Run coverage analysis
        # Compare with baseline
        # Report coverage changes
```

## Implementation Phases

### Phase 1: Preparation and Analysis
- Create backup of current codebase
- Run comprehensive dependency analysis
- Generate cleanup plan with file mappings
- Establish baseline metrics (test coverage, performance)

### Phase 2: Google Trends Removal
- Remove trends-related files
- Update import statements
- Remove trends API endpoints
- Update MCP configuration
- Remove trends from documentation
- Run validation tests

### Phase 3: Test File Consolidation
- Move root-level test files to tests/ directory
- Consolidate duplicate test files
- Update test runner configuration
- Validate test suite functionality
- Update CI/CD pipeline if needed

### Phase 4: Code Deduplication
- Consolidate cache system implementations
- Merge duplicate client code
- Standardize error handling
- Update configuration management
- Validate system functionality

### Phase 5: Final Cleanup
- Remove empty directories
- Clean up documentation
- Update dependency files
- Run final validation
- Generate cleanup report

## Performance Considerations

### Expected Improvements

1. **Startup Time**: Reduced imports should improve application startup
2. **Memory Usage**: Fewer loaded modules should reduce memory footprint
3. **Test Execution**: Consolidated tests should run faster
4. **Build Time**: Fewer files should reduce build and deployment time

### Metrics to Track

- Application startup time
- Memory usage at runtime
- Test suite execution time
- Code coverage percentage
- Number of files and lines of code
- Import resolution time

## Security Considerations

### Removed Attack Surface

- Elimination of Google Trends API reduces external dependencies
- Fewer test files reduce potential test data exposure
- Consolidated configuration reduces configuration drift

### Validation Requirements

- Ensure no sensitive data in removed files
- Validate configuration security after consolidation
- Check for hardcoded credentials in test files
- Verify API security after endpoint removal

## Rollback Strategy

### Backup Approach

1. **Git Branch**: Create cleanup branch for all changes
2. **File Backup**: Create timestamped backup of removed files
3. **Configuration Backup**: Save original configuration files
4. **Database Backup**: Backup any database schema if affected

### Rollback Triggers

- Critical test failures that cannot be quickly resolved
- Import errors that break core functionality
- Performance degradation beyond acceptable thresholds
- Security vulnerabilities introduced by changes

### Rollback Process

```python
class CleanupRollback:
    def rollback_to_phase(self, target_phase: str):
        # Restore files from backup
        # Revert configuration changes
        # Update import statements
        # Run validation tests
        
    def complete_rollback(self):
        # Restore entire codebase to pre-cleanup state
        # Reset all configuration
        # Validate system functionality
```

## Success Metrics

### Quantitative Metrics

- **File Count Reduction**: Target 30-40% reduction in total files
- **Code Line Reduction**: Target 20-30% reduction in total lines
- **Test Execution Time**: Target 25% improvement in test speed
- **Startup Time**: Target 15% improvement in application startup
- **Memory Usage**: Target 10% reduction in runtime memory

### Qualitative Metrics

- **Code Organization**: Improved file structure and naming
- **Maintainability**: Easier navigation and understanding
- **Test Reliability**: More stable and predictable test results
- **Documentation Quality**: Accurate and up-to-date documentation
- **Developer Experience**: Faster development and debugging

## Conclusion

This design provides a comprehensive, risk-mitigated approach to cleaning up the KDP Strategist codebase. The phased implementation ensures system stability while achieving the goals of removing Google Trends functionality, consolidating tests, and eliminating code duplication. The extensive testing and rollback strategies minimize risk while the clear success metrics provide measurable outcomes.