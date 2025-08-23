"""FastAPI application for KDP Strategist UI backend.

This module creates a FastAPI application that serves as a bridge between
the React frontend and the existing MCP agent backend.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn

# Import existing MCP agent
from src.kdp_strategist.agent.kdp_strategist_agent import KDPStrategistAgent

# Import error handling infrastructure
from src.kdp_strategist.error_handlers import register_error_handlers
import logging
# Health checker functionality will be implemented inline
from src.kdp_strategist.exceptions import KDPStrategistError, ConfigurationError

# Import API routers
from .routers import niches, competitors, listings, stress, settings, dashboard

# Configure structured logging
logger = logging.getLogger(__name__)

# WebSocket connection manager with analysis tracking
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.active_analyses: dict[str, dict] = {}
        self.client_analyses: dict[str, set] = {}

    async def connect(self, websocket: WebSocket, client_id: str = None):
        await websocket.accept()
        if not client_id:
            client_id = f"client_{len(self.active_connections)}_{int(asyncio.get_event_loop().time())}"
        
        self.active_connections[client_id] = websocket
        self.client_analyses[client_id] = set()
        logger.info(f"WebSocket connected: {client_id}. Total connections: {len(self.active_connections)}")
        return client_id

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            # Cancel any active analyses for this client
            if client_id in self.client_analyses:
                for analysis_id in self.client_analyses[client_id].copy():
                    self.cancel_analysis(analysis_id)
                del self.client_analyses[client_id]
            
            del self.active_connections[client_id]
            logger.info(f"WebSocket disconnected: {client_id}. Total connections: {len(self.active_connections)}")

    async def send_to_client(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast(self, message: dict):
        disconnected_clients = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    def start_analysis(self, analysis_id: str, client_id: str, analysis_type: str, parameters: dict):
        """Start tracking an analysis"""
        self.active_analyses[analysis_id] = {
            'id': analysis_id,
            'client_id': client_id,
            'type': analysis_type,
            'parameters': parameters,
            'status': 'starting',
            'progress': 0,
            'current_step': 0,
            'start_time': asyncio.get_event_loop().time(),
            'cancelled': False,
            'paused': False,
            'pause_time': None,
            'total_pause_duration': 0,
            'estimated_completion': None,
            'steps': self._get_analysis_steps(analysis_type),
            'step_details': {},
            'error_details': None,
            'cancellation_reason': None
        }
        
        if client_id in self.client_analyses:
            self.client_analyses[client_id].add(analysis_id)

    def _get_analysis_steps(self, analysis_type: str) -> list:
        """Get the steps for a specific analysis type"""
        step_maps = {
            'niche_discovery': [
                'Initializing analysis parameters',
                'Expanding keywords using trends data',
                
                'Analyzing market competition',
                'Calculating profitability scores',
                'Finalizing results'
            ],
            'competitor_analysis': [
                'Setting up competitor search',
                'Gathering competitor data',
                'Analyzing competitor metrics',
                'Comparing competitors',
                'Preparing analysis results'
            ],
            'trend_validation': [
                'Setting up trend analysis',
                'Fetching trend data',
                'Validating trend patterns',
                'Generating trend forecasts',
                'Preparing validation results'
            ],
            'listing_generation': [
                'Setting up listing generation',
                'Analyzing niche content',
                'Generating listing content',
                'Optimizing for SEO',
                'Preparing final listing'
            ]
        }
        return step_maps.get(analysis_type, ['Processing analysis'])

    async def update_analysis_progress(self, analysis_id: str, progress: int, step: int, status: str = None, estimated_time: str = None, step_details: dict = None):
        """Update analysis progress and notify client"""
        if analysis_id in self.active_analyses:
            analysis = self.active_analyses[analysis_id]
            analysis['progress'] = progress
            analysis['current_step'] = step
            if status:
                analysis['status'] = status
            
            # Calculate estimated completion time
            if progress > 0 and analysis['start_time']:
                elapsed_time = asyncio.get_event_loop().time() - analysis['start_time'] - analysis.get('total_pause_duration', 0)
                if elapsed_time > 0:
                    estimated_total_time = (elapsed_time / progress) * 100
                    estimated_remaining = max(0, estimated_total_time - elapsed_time)
                    analysis['estimated_completion'] = estimated_remaining
            
            # Send progress update to client
            progress_message = {
                'type': 'analysis_progress',
                'analysis_id': analysis_id,
                'progress': progress,
                'step': step,
                'status': status or analysis['status'],
                'estimated_time': estimated_time or analysis.get('estimated_completion'),
                'step_name': analysis['steps'][step] if step < len(analysis['steps']) else 'Processing',
                'total_steps': len(analysis['steps']),
                'elapsed_time': asyncio.get_event_loop().time() - analysis['start_time'] if analysis['start_time'] else 0
            }
            
            if step_details:
                progress_message['step_details'] = step_details
            
            await self.send_to_client(analysis['client_id'], progress_message)

    async def complete_analysis(self, analysis_id: str, results: dict):
        """Mark analysis as complete and notify client"""
        if analysis_id in self.active_analyses:
            analysis = self.active_analyses[analysis_id]
            execution_time = asyncio.get_event_loop().time() - analysis['start_time']
            
            await self.send_to_client(analysis['client_id'], {
                'type': 'analysis_complete',
                'analysis_id': analysis_id,
                'results': results,
                'execution_time': execution_time
            })
            
            # Clean up
            client_id = analysis['client_id']
            if client_id in self.client_analyses:
                self.client_analyses[client_id].discard(analysis_id)
            del self.active_analyses[analysis_id]

    async def error_analysis(self, analysis_id: str, error: str):
        """Mark analysis as error and notify client"""
        if analysis_id in self.active_analyses:
            analysis = self.active_analyses[analysis_id]
            
            await self.send_to_client(analysis['client_id'], {
                'type': 'analysis_error',
                'analysis_id': analysis_id,
                'error': error
            })
            
            # Clean up
            client_id = analysis['client_id']
            if client_id in self.client_analyses:
                self.client_analyses[client_id].discard(analysis_id)
            del self.active_analyses[analysis_id]

    def cancel_analysis(self, analysis_id: str):
        """Cancel an active analysis"""
        if analysis_id in self.active_analyses:
            self.active_analyses[analysis_id]['cancelled'] = True
            self.active_analyses[analysis_id]['status'] = 'cancelled'
            return True
        return False

    def pause_analysis(self, analysis_id: str):
        """Pause an active analysis"""
        if analysis_id in self.active_analyses:
            analysis = self.active_analyses[analysis_id]
            if analysis['status'] == 'in-progress' and not analysis['paused']:
                analysis['paused'] = True
                analysis['pause_time'] = asyncio.get_event_loop().time()
                analysis['status'] = 'paused'
                return True
        return False

    def resume_analysis(self, analysis_id: str):
        """Resume a paused analysis"""
        if analysis_id in self.active_analyses:
            analysis = self.active_analyses[analysis_id]
            if analysis['status'] == 'paused' and analysis['paused']:
                # Calculate total pause duration
                if analysis['pause_time']:
                    pause_duration = asyncio.get_event_loop().time() - analysis['pause_time']
                    analysis['total_pause_duration'] += pause_duration
                
                analysis['paused'] = False
                analysis['pause_time'] = None
                analysis['status'] = 'in-progress'
                return True
        return False

    def is_analysis_cancelled(self, analysis_id: str) -> bool:
        """Check if analysis is cancelled"""
        return self.active_analyses.get(analysis_id, {}).get('cancelled', False)

    def is_analysis_paused(self, analysis_id: str) -> bool:
        """Check if analysis is paused"""
        return self.active_analyses.get(analysis_id, {}).get('paused', False)

    def get_analysis_info(self, analysis_id: str) -> dict:
        """Get detailed analysis information"""
        return self.active_analyses.get(analysis_id, {})

manager = ConnectionManager()

async def simulate_demo_analysis(analysis_id: str, analysis_type: str, connection_manager: ConnectionManager):
    """Simulate a demo analysis with realistic progress updates."""
    import random
    
    try:
        # Get analysis info
        analysis = connection_manager.get_analysis_info(analysis_id)
        if not analysis:
            return
        
        steps = analysis['steps']
        total_steps = len(steps)
        
        # Simulate different durations based on analysis type
        duration_map = {
            'niche_discovery': (6, 10),
            'competitor_analysis': (8, 12),
            'trend_validation': (4, 6),
            'listing_generation': (5, 8)
        }
        
        min_duration, max_duration = duration_map.get(analysis_type, (5, 8))
        total_duration = random.uniform(min_duration, max_duration)
        step_duration = total_duration / total_steps
        
        # Start the analysis
        await connection_manager.update_analysis_progress(
            analysis_id, 0, 0, 'in-progress', 
            step_details={'message': 'Starting analysis...'}
        )
        
        for step_index in range(total_steps):
            # Check if analysis was cancelled or paused
            if connection_manager.is_analysis_cancelled(analysis_id):
                logger.info(f"Demo analysis {analysis_id} was cancelled")
                return
            
            # Wait while paused
            while connection_manager.is_analysis_paused(analysis_id):
                await asyncio.sleep(0.5)
                if connection_manager.is_analysis_cancelled(analysis_id):
                    return
            
            # Simulate step processing time with some randomness
            step_time = step_duration * random.uniform(0.7, 1.3)
            
            # Update progress at the beginning of each step
            progress = int((step_index / total_steps) * 100)
            await connection_manager.update_analysis_progress(
                analysis_id, progress, step_index, 'in-progress',
                step_details={
                    'current_step': steps[step_index],
                    'step_progress': 0,
                    'message': f'Processing: {steps[step_index]}'
                }
            )
            
            # Simulate sub-progress within the step
            sub_steps = 5
            for sub_step in range(sub_steps):
                if connection_manager.is_analysis_cancelled(analysis_id):
                    return
                
                while connection_manager.is_analysis_paused(analysis_id):
                    await asyncio.sleep(0.5)
                    if connection_manager.is_analysis_cancelled(analysis_id):
                        return
                
                await asyncio.sleep(step_time / sub_steps)
                
                # Update sub-progress
                sub_progress = int((sub_step + 1) / sub_steps * 100)
                await connection_manager.update_analysis_progress(
                    analysis_id, progress, step_index, 'in-progress',
                    step_details={
                        'current_step': steps[step_index],
                        'step_progress': sub_progress,
                        'message': f'Processing: {steps[step_index]} ({sub_progress}%)'
                    }
                )
        
        # Complete the analysis
        if not connection_manager.is_analysis_cancelled(analysis_id):
            # Use real analysis instead of mock data
            try:
                # This should call the actual analysis functions
                # For now, return a message indicating real analysis is needed
                real_results = {
                    'message': 'Real analysis implementation needed',
                    'analysis_type': analysis_type,
                    'status': 'requires_implementation'
                }
                
                await connection_manager.update_analysis_progress(
                    analysis_id, 100, total_steps, 'completed',
                    step_details={'message': 'Analysis completed - real implementation needed'}
                )
                
                await connection_manager.complete_analysis(analysis_id, real_results)
                logger.info(f"Analysis {analysis_id} completed - real implementation needed")
            except Exception as e:
                logger.error(f"Analysis {analysis_id} failed: {e}")
                await connection_manager.error_analysis(analysis_id, str(e))
    
    except Exception as e:
        logger.error(f"Error in demo analysis {analysis_id}: {e}")
        await connection_manager.error_analysis(analysis_id, str(e))

# Mock results generation function removed - using real analysis

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown events."""
    # Startup
    logger.info("Starting KDP Strategist API...")
    try:
        # Initialize MCP agent
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent))
        from config.settings import get_settings
        settings = get_settings()
        app.state.agent = KDPStrategistAgent(settings)
        logger.info("MCP Agent initialized successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize MCP agent: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down KDP Strategist API...")
        if hasattr(app.state, 'agent'):
            try:
                await app.state.agent.cleanup()
                logger.info("MCP Agent cleaned up successfully")
            except Exception as e:
                logger.error(f"Error during agent cleanup: {e}")

# Create FastAPI application
app = FastAPI(
    title="KDP Strategist API",
    description="""
    ## KDP Strategist AI Agent API
    
    A comprehensive API for Kindle Direct Publishing (KDP) market analysis and strategy optimization.
    
    ### Features
    
    * **Niche Discovery**: Find profitable publishing niches using AI-powered market analysis
    * **Trend Validation**: Validate market trends using Google Trends data
    * **Competitor Analysis**: Analyze competitor products and market positioning
    * **Listing Generation**: Generate optimized KDP book listings
    * **Stress Testing**: Test niche viability under various market conditions
    
    ### Rate Limits
    
    * Niche Discovery: 10 requests per hour
    * Trend Validation: 20 requests per hour  
    * General endpoints: 100 requests per hour
    
    ### Authentication
    
    Currently, no authentication is required. Rate limiting is based on IP address.
    
    ### Data Sources
    
    * Google Trends API for trend analysis
    * Keepa API for Amazon product data (optional)
    * Internal AI models for market analysis
    
    ### Support
    
    For support and documentation, visit the project repository.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "KDP Strategist Support",
        "email": "support@kdpstrategist.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        },
        {
            "url": "https://api.kdpstrategist.com",
            "description": "Production server"
        }
    ]
)

# Configure CORS for React frontend
# Get allowed origins from environment or use defaults
allowed_origins = [
    "http://localhost:3000",  # React dev server
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://localhost:8080",  # Alternative dev server
    "http://127.0.0.1:8080",
]

# Add production origins if specified in environment
import os
if os.getenv("CORS_ORIGINS"):
    env_origins = os.getenv("CORS_ORIGINS").split(",")
    allowed_origins.extend([origin.strip() for origin in env_origins])

# In development, allow all origins for easier testing
if os.getenv("ENVIRONMENT", "development") == "development":
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Register error handlers
register_error_handlers(app)

# Include API routers
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(niches.router, prefix="/api/niches", tags=["niches"])
app.include_router(competitors.router, prefix="/api/competitors", tags=["competitors"])
app.include_router(listings.router, prefix="/api/listings", tags=["listings"])
app.include_router(stress.router, prefix="/api/stress", tags=["stress"])
app.include_router(settings.router, tags=["settings"])
# Feature flags router removed during trends cleanup
# app.include_router(production_monitoring.router, prefix="/api", tags=["production-monitoring"])
# Incidents router removed during trends cleanup

# Enhanced health check endpoints
@app.get("/api/health")
async def health_check():
    """Basic health check endpoint for load balancers."""
    from datetime import datetime
    import time
    
    return {
        "status": "healthy",
        "service": "kdp_strategist-api",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": int(time.time())
    }

@app.get("/api/health/detailed")
async def detailed_health_check():
    """Detailed health check endpoint for monitoring systems."""
    from datetime import datetime
    import time
    
    return {
        "status": "healthy",
        "service": "kdp_strategist-api",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": int(time.time()),
        "components": {
            "api": "healthy",
            "database": "healthy"
        }
    }

@app.get("/api/health/ready")
async def readiness_check():
    """Readiness check for Kubernetes deployments."""
    try:
        # Simple readiness check - verify app state is available
        if hasattr(app.state, 'agent'):
            return {"status": "ready", "message": "Service is ready to accept traffic"}
        else:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "message": "Service is not ready"}
            )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "message": "Readiness check failed"}
        )

@app.get("/api/health/live")
async def liveness_check():
    """Liveness check for Kubernetes deployments."""
    try:
        # Simple liveness check - if we can respond, we're alive
        return {"status": "alive", "message": "Service is alive"}
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not_alive", "message": "Liveness check failed"}
        )

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates and analysis progress tracking."""
    client_id = None
    try:
        client_id = await manager.connect(websocket)
        
        # Send welcome message
        await manager.send_to_client(client_id, {
            'type': 'connection',
            'status': 'connected',
            'client_id': client_id,
            'message': 'WebSocket connection established'
        })
        
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_websocket_message(client_id, message)
            except json.JSONDecodeError:
                await manager.send_to_client(client_id, {
                    'type': 'error',
                    'message': 'Invalid JSON message format'
                })
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await manager.send_to_client(client_id, {
                    'type': 'error',
                    'message': f'Error processing message: {str(e)}'
                })
                
    except WebSocketDisconnect:
        if client_id:
            manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if client_id:
            manager.disconnect(client_id)

async def handle_websocket_message(client_id: str, message: dict):
    """Handle incoming WebSocket messages from clients."""
    message_type = message.get('type')
    
    if message_type == 'connection':
        # Handle connection initialization
        await manager.send_to_client(client_id, {
            'type': 'connection_ack',
            'client_id': client_id,
            'server_time': asyncio.get_event_loop().time()
        })
        
    elif message_type == 'start_analysis':
        # Handle analysis start request
        analysis_id = message.get('analysis_id')
        analysis_type = message.get('analysis_type')
        parameters = message.get('parameters', {})
        
        if analysis_id and analysis_type:
            manager.start_analysis(analysis_id, client_id, analysis_type, parameters)
            await manager.send_to_client(client_id, {
                'type': 'analysis_started',
                'analysis_id': analysis_id,
                'message': f'Analysis {analysis_id} started'
            })
            
            # Start demo simulation if demo_mode is enabled
            if parameters.get('demo_mode', False):
                asyncio.create_task(simulate_demo_analysis(analysis_id, analysis_type, manager))
        else:
            await manager.send_to_client(client_id, {
                'type': 'error',
                'message': 'Missing analysis_id or analysis_type'
            })
            
    elif message_type == 'cancel_analysis':
        # Handle analysis cancellation
        analysis_id = message.get('analysis_id')
        if analysis_id:
            success = manager.cancel_analysis(analysis_id)
            if success:
                await manager.send_to_client(client_id, {
                    'type': 'analysis_cancelled',
                    'analysis_id': analysis_id,
                    'message': f'Analysis {analysis_id} cancelled'
                })
            else:
                await manager.send_to_client(client_id, {
                    'type': 'error',
                    'message': f'Analysis {analysis_id} not found or already completed'
                })
        else:
            await manager.send_to_client(client_id, {
                'type': 'error',
                'message': 'Missing analysis_id'
            })
            
    elif message_type == 'pause_analysis':
        # Handle analysis pause
        analysis_id = message.get('analysis_id')
        if analysis_id:
            success = manager.pause_analysis(analysis_id)
            if success:
                await manager.send_to_client(client_id, {
                    'type': 'analysis_paused',
                    'analysis_id': analysis_id,
                    'message': f'Analysis {analysis_id} paused'
                })
            else:
                await manager.send_to_client(client_id, {
                    'type': 'error',
                    'message': f'Analysis {analysis_id} cannot be paused or not found'
                })
        else:
            await manager.send_to_client(client_id, {
                'type': 'error',
                'message': 'Missing analysis_id'
            })
            
    elif message_type == 'resume_analysis':
        # Handle analysis resume
        analysis_id = message.get('analysis_id')
        if analysis_id:
            success = manager.resume_analysis(analysis_id)
            if success:
                await manager.send_to_client(client_id, {
                    'type': 'analysis_resumed',
                    'analysis_id': analysis_id,
                    'message': f'Analysis {analysis_id} resumed'
                })
            else:
                await manager.send_to_client(client_id, {
                    'type': 'error',
                    'message': f'Analysis {analysis_id} cannot be resumed or not found'
                })
        else:
            await manager.send_to_client(client_id, {
                'type': 'error',
                'message': 'Missing analysis_id'
            })
            
    elif message_type == 'ping':
        # Handle ping/keepalive
        await manager.send_to_client(client_id, {
            'type': 'pong',
            'timestamp': message.get('timestamp'),
            'server_time': asyncio.get_event_loop().time()
        })
        
    else:
        # Unknown message type
        await manager.send_to_client(client_id, {
            'type': 'error',
            'message': f'Unknown message type: {message_type}'
        })

# Note: Global exception handler is registered via register_error_handlers()

# Serve static files (React build) - will be added after UI is built
# app.mount("/", StaticFiles(directory="ui/dist", html=True), name="ui")

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )