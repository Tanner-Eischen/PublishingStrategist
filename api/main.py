"""FastAPI application for KDP Strategist UI backend.

This module creates a FastAPI application that serves as a bridge between
the React frontend and the existing MCP agent backend.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn

# Import existing MCP agent
try:
    from src.kdp_strategist.agent.kdp_strategist_agent import KDPStrategistAgent
except ImportError:
    # Fallback for development when package is not installed
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
    from src.kdp_strategist.agent.kdp_strategist_agent import KDPStrategistAgent

# Import API routers
from .routers import niches, competitors, listings, trends, stress

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        app.state.agent = await KDPStrategistAgent.create()
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

# Include API routers
app.include_router(niches.router, prefix="/api/niches", tags=["niches"])
app.include_router(competitors.router, prefix="/api/competitors", tags=["competitors"])
app.include_router(listings.router, prefix="/api/listings", tags=["listings"])
app.include_router(trends.router, prefix="/api/trends", tags=["trends"])
app.include_router(stress.router, prefix="/api/stress", tags=["stress"])

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "kdp-strategist-api"}

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

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": "internal_error"}
    )

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