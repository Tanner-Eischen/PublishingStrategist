# Application Startup Fix - Design Document

## Introduction

This design document outlines the technical solution for resolving critical startup issues in the KDP Strategist application. The solution addresses dependency management, Python path configuration, service orchestration, and error handling to ensure both the FastAPI backend and React frontend can start and operate reliably.

## Architecture Overview

### Current State Analysis

Based on codebase analysis, the application has:
- **Backend**: FastAPI server with uvicorn, located in `scripts/run_server.py`
- **Frontend**: React application with Create React App in `frontend/` directory
- **Dependencies**: Python packages in `requirements.txt`, Node.js packages in `frontend/package.json`
- **Issues**: Missing MCP dependencies, Python path problems, import errors

### Target Architecture

```
KDP Strategist Application
├── Dependency Management Layer
│   ├── Python Environment Setup
│   ├── MCP Dependencies Installation
│   └── Node.js Dependencies Resolution
├── Configuration Layer
│   ├── Environment Variables
│   ├── Python Path Configuration
│   └── Service Discovery
├── Service Layer
│   ├── Backend API Server (FastAPI)
│   ├── Frontend Development Server (React)
│   └── Health Check Endpoints
└── Orchestration Layer
    ├── Startup Scripts
    ├── Error Handling
    └── Service Monitoring
```

## Component Design

### 1. Dependency Management System

#### 1.1 Python Dependencies Handler

**Purpose**: Ensure all Python packages including MCP are properly installed

**Location**: `scripts/setup_dependencies.py`

**Key Functions**:
- `install_python_dependencies()`: Install requirements.txt packages
- `install_mcp_dependencies()`: Install MCP packages separately
- `verify_dependencies()`: Check all imports work correctly
- `handle_dependency_conflicts()`: Resolve version conflicts

**Implementation Strategy**:
```python
def install_python_dependencies():
    """Install Python dependencies with proper error handling"""
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        install_mcp_dependencies()
        verify_dependencies()
    except subprocess.CalledProcessError as e:
        handle_installation_error(e)

def install_mcp_dependencies():
    """Install MCP dependencies separately to avoid conflicts"""
    mcp_packages = ["mcp", "mcp-server-stdio"]
    for package in mcp_packages:
        subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)
```

#### 1.2 Frontend Dependencies Handler

**Purpose**: Ensure Node.js packages are properly installed and compatible

**Location**: `scripts/setup_frontend.py`

**Key Functions**:
- `install_node_dependencies()`: Run npm install with error handling
- `verify_frontend_build()`: Test compilation without starting server
- `handle_node_conflicts()`: Resolve package conflicts

### 2. Configuration Management System

#### 2.1 Environment Configuration

**Purpose**: Manage environment variables and configuration files

**Location**: `config/environment_manager.py`

**Key Functions**:
- `load_environment_config()`: Load .env files with fallbacks
- `validate_configuration()`: Ensure required settings are present
- `setup_python_path()`: Configure PYTHONPATH for module imports

**Implementation Strategy**:
```python
def setup_python_path():
    """Configure Python path to resolve import issues"""
    project_root = Path(__file__).parent.parent
    paths_to_add = [
        str(project_root),
        str(project_root / "src"),
        str(project_root / "api")
    ]
    
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
```

#### 2.2 Service Configuration

**Purpose**: Configure backend and frontend services for proper communication

**Location**: `config/service_config.py`

**Key Functions**:
- `get_backend_config()`: Return FastAPI server configuration
- `get_frontend_config()`: Return React development server configuration
- `setup_cors_config()`: Configure CORS for frontend-backend communication

### 3. Service Management System

#### 3.1 Backend Service Manager

**Purpose**: Start and manage the FastAPI backend server

**Location**: `scripts/backend_manager.py`

**Key Functions**:
- `start_backend_server()`: Launch FastAPI with proper configuration
- `check_backend_health()`: Verify server is responding
- `handle_backend_errors()`: Process and report startup errors

**Implementation Strategy**:
```python
def start_backend_server():
    """Start FastAPI backend with comprehensive error handling"""
    try:
        setup_python_path()
        verify_dependencies()
        
        import uvicorn
        from api.main import app
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except ImportError as e:
        handle_import_error(e)
    except Exception as e:
        handle_startup_error(e)
```

#### 3.2 Frontend Service Manager

**Purpose**: Start and manage the React development server

**Location**: `scripts/frontend_manager.py`

**Key Functions**:
- `start_frontend_server()`: Launch React development server
- `check_frontend_health()`: Verify frontend is accessible
- `handle_frontend_errors()`: Process compilation and runtime errors

### 4. Health Check System

#### 4.1 Service Health Monitor

**Purpose**: Monitor the health of both backend and frontend services

**Location**: `api/routers/health.py` (enhanced)

**Key Functions**:
- `check_backend_health()`: Verify API endpoints are responding
- `check_frontend_health()`: Verify frontend is accessible
- `check_dependencies()`: Verify all required packages are available
- `get_system_status()`: Return comprehensive system health report

**Implementation Strategy**:
```python
@router.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "backend": check_backend_health(),
            "frontend": check_frontend_health(),
            "dependencies": check_dependencies()
        }
    }
    
    if any(service["status"] != "healthy" for service in health_status["services"].values()):
        health_status["status"] = "unhealthy"
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status
```

### 5. Error Handling System

#### 5.1 Startup Error Handler

**Purpose**: Provide clear, actionable error messages for startup failures

**Location**: `src/kdp_strategist/startup_error_handler.py`

**Key Functions**:
- `handle_import_error()`: Process and explain import failures
- `handle_dependency_error()`: Guide users through dependency installation
- `handle_configuration_error()`: Help resolve configuration issues
- `generate_diagnostic_report()`: Create detailed error reports

**Implementation Strategy**:
```python
def handle_import_error(error: ImportError):
    """Provide specific guidance for import errors"""
    module_name = str(error).split("'")[1] if "'" in str(error) else "unknown"
    
    error_guidance = {
        "api": "Run: python -m pip install -e . to install the project in development mode",
        "mcp": "Run: python -m pip install mcp mcp-server-stdio",
        "uvicorn": "Run: python -m pip install -r requirements.txt"
    }
    
    guidance = error_guidance.get(module_name, f"Install missing module: pip install {module_name}")
    
    print(f"\n❌ Import Error: {error}")
    print(f"💡 Solution: {guidance}")
    print(f"📋 Full diagnostic: Run 'python scripts/diagnose_startup.py'\n")
```

### 6. Orchestration System

#### 6.1 Master Startup Script

**Purpose**: Coordinate the entire application startup process

**Location**: `scripts/start_application.py`

**Key Functions**:
- `start_full_application()`: Start both backend and frontend
- `start_backend_only()`: Start only the backend service
- `start_frontend_only()`: Start only the frontend service
- `run_diagnostics()`: Check system readiness before starting

**Implementation Strategy**:
```python
def start_full_application():
    """Start the complete KDP Strategist application"""
    print("🚀 Starting KDP Strategist Application...")
    
    # Phase 1: Diagnostics
    print("📋 Running pre-startup diagnostics...")
    if not run_diagnostics():
        print("❌ Diagnostics failed. Please resolve issues before starting.")
        return False
    
    # Phase 2: Dependencies
    print("📦 Verifying dependencies...")
    if not verify_all_dependencies():
        print("📦 Installing missing dependencies...")
        install_all_dependencies()
    
    # Phase 3: Backend
    print("🔧 Starting backend server...")
    backend_process = start_backend_async()
    
    # Phase 4: Frontend
    print("🎨 Starting frontend server...")
    frontend_process = start_frontend_async()
    
    # Phase 5: Health Check
    print("🏥 Performing health checks...")
    if wait_for_services_ready():
        print("✅ Application started successfully!")
        print("🌐 Backend: http://localhost:8000")
        print("🎨 Frontend: http://localhost:3000")
        return True
    else:
        print("❌ Services failed to start properly.")
        cleanup_processes([backend_process, frontend_process])
        return False
```

## Data Models

### Service Status Model

```python
from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime

class ServiceStatus(BaseModel):
    name: str
    status: str  # "healthy", "unhealthy", "starting", "stopped"
    url: Optional[str]
    last_check: datetime
    error_message: Optional[str]
    dependencies: Dict[str, bool]

class SystemHealth(BaseModel):
    overall_status: str
    services: Dict[str, ServiceStatus]
    timestamp: datetime
    diagnostics: Dict[str, str]
```

### Configuration Model

```python
class ApplicationConfig(BaseModel):
    backend_host: str = "localhost"
    backend_port: int = 8000
    frontend_host: str = "localhost"
    frontend_port: int = 3000
    debug_mode: bool = True
    cors_origins: List[str] = ["http://localhost:3000"]
    python_path: List[str]
    environment: str = "development"
```

## API Endpoints

### Health Check Endpoints

```python
# GET /api/health - Comprehensive health check
# GET /api/health/backend - Backend-specific health
# GET /api/health/frontend - Frontend connectivity check
# GET /api/health/dependencies - Dependency verification
# GET /api/diagnostics - Detailed system diagnostics
```

### Configuration Endpoints

```python
# GET /api/config - Current application configuration
# POST /api/config/reload - Reload configuration from files
# GET /api/config/environment - Environment variable status
```

## Error Handling Strategy

### Error Categories

1. **Dependency Errors**: Missing packages, version conflicts
2. **Configuration Errors**: Invalid settings, missing environment variables
3. **Network Errors**: Port conflicts, CORS issues
4. **Import Errors**: Python path issues, missing modules
5. **Service Errors**: Server startup failures, health check failures

### Error Response Format

```python
class StartupError(BaseModel):
    error_type: str
    error_message: str
    suggested_solution: str
    diagnostic_command: Optional[str]
    documentation_link: Optional[str]
```

## Testing Strategy

### Unit Tests

- Test each component in isolation
- Mock external dependencies
- Verify error handling paths
- Test configuration loading

### Integration Tests

- Test full startup sequence
- Verify service communication
- Test health check endpoints
- Validate error recovery

### End-to-End Tests

- Test complete application startup
- Verify frontend-backend integration
- Test user workflows
- Performance and reliability testing

## Security Considerations

### Environment Security

- Store sensitive configuration in environment variables
- Validate all configuration inputs
- Use secure defaults for production
- Implement proper CORS policies

### Dependency Security

- Pin dependency versions in requirements.txt
- Regularly update dependencies for security patches
- Scan for known vulnerabilities
- Use virtual environments for isolation

## Performance Considerations

### Startup Performance

- Parallel dependency installation where possible
- Lazy loading of non-critical components
- Efficient health check intervals
- Optimized import paths

### Runtime Performance

- Efficient error handling without performance impact
- Minimal overhead for health checks
- Optimized configuration loading
- Proper resource cleanup

## Monitoring and Observability

### Logging Strategy

- Structured logging for startup events
- Error tracking with context
- Performance metrics collection
- Debug logging for troubleshooting

### Metrics Collection

- Startup time metrics
- Service health metrics
- Error rate tracking
- Dependency check performance

## Implementation Plan

### Phase 1: Foundation (Priority: High)

1. Create dependency management system
2. Implement Python path configuration
3. Build basic error handling
4. Create diagnostic tools

### Phase 2: Service Management (Priority: High)

1. Enhance backend startup script
2. Improve frontend startup process
3. Implement health check system
4. Add service orchestration

### Phase 3: Integration (Priority: Medium)

1. Create master startup script
2. Implement comprehensive error handling
3. Add configuration management
4. Build monitoring capabilities

### Phase 4: Enhancement (Priority: Low)

1. Add advanced diagnostics
2. Implement performance monitoring
3. Create automated recovery
4. Add development tools

## Success Metrics

- **Startup Success Rate**: >95% successful startups
- **Startup Time**: <30 seconds for full application
- **Error Resolution Time**: <5 minutes with clear guidance
- **Health Check Response**: <2 seconds
- **Zero Silent Failures**: All errors must be reported clearly

## Rollback Strategy

- Maintain backup of current startup scripts
- Implement feature flags for new startup components
- Create rollback scripts for quick recovery
- Document manual startup procedures as fallback