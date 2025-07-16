"""FastAPI application for KDP Strategist UI backend.

This module creates a FastAPI application that serves as a bridge between
the React frontend and the existing MCP agent backend.
"""

import asyncio
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
from src.kdp_strategist.logging_config import configure_logging, get_logger
from src.kdp_strategist.health import get_health_checker
from src.kdp_strategist.exceptions import KDPStrategistError, ConfigurationError

# Import API routers
from .routers import niches, competitors, listings, trends, stress

# Configure structured logging
configure_logging()
logger = get_logger(__name__)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                self.disconnect(connection)

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown events."""
    # Startup
    logger.info("Starting KDP Strategist API...")
    try:
        # Initialize MCP agent
        from config.settings import Settings
        settings = Settings.from_env()
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
    description="Web API for KDP Strategist AI Agent",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register error handlers
register_error_handlers(app)

# Include API routers
app.include_router(niches.router, prefix="/api/niches", tags=["niches"])
app.include_router(competitors.router, prefix="/api/competitors", tags=["competitors"])
app.include_router(listings.router, prefix="/api/listings", tags=["listings"])
app.include_router(trends.router, prefix="/api/trends", tags=["trends"])
app.include_router(stress.router, prefix="/api/stress", tags=["stress"])

# Enhanced health check endpoints
@app.get("/api/health")
async def health_check():
    """Basic health check endpoint for load balancers."""
    health_checker = get_health_checker()
    system_health = await health_checker.check_system_health(include_detailed=False)
    
    return {
        "status": system_health.status.value,
        "service": "kdp_strategist-api",
        "timestamp": system_health.timestamp.isoformat(),
        "uptime_seconds": system_health.uptime_seconds
    }

@app.get("/api/health/detailed")
async def detailed_health_check():
    """Detailed health check endpoint for monitoring systems."""
    health_checker = get_health_checker()
    system_health = await health_checker.check_system_health(include_detailed=True)
    
    return system_health.to_dict()

@app.get("/api/health/ready")
async def readiness_check():
    """Readiness check for Kubernetes deployments."""
    try:
        health_checker = get_health_checker()
        system_health = await health_checker.check_system_health(include_detailed=False)
        
        if system_health.status.value in ["healthy", "degraded"]:
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
        # Simple check to ensure the application is responsive
        health_checker = get_health_checker()
        app_health = await health_checker.check_application_health()
        
        if app_health.status.value != "unhealthy":
            return {"status": "alive", "message": "Service is alive"}
        else:
            return JSONResponse(
                status_code=503,
                content={"status": "not_alive", "message": "Service is not responding"}
            )
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not_alive", "message": "Liveness check failed"}
        )

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for now - can be enhanced for real-time analysis updates
            await manager.send_personal_message(f"Message received: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

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