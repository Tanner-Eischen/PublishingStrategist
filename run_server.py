#!/usr/bin/env python3
"""
KDP Strategist FastAPI Server Launcher

This script starts the FastAPI backend server for the KDP Strategist web UI.
It handles server configuration, logging setup, and graceful shutdown.
"""

import os
import sys
import asyncio
import signal
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import uvicorn
    from api.main import app
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    print("Please install the required dependencies with: pip install -r requirements.txt")
    sys.exit(1)


def setup_logging():
    """Configure logging for the server."""
    import logging
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('kdp_strategist.log')
        ]
    )
    
    # Set specific log levels
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('uvicorn.access').setLevel(logging.INFO)
    logging.getLogger('fastapi').setLevel(logging.INFO)
    
    return logging.getLogger(__name__)


def get_server_config():
    """Get server configuration from environment variables."""
    return {
        'host': os.getenv('HOST', '0.0.0.0'),
        'port': int(os.getenv('PORT', 8000)),
        'reload': os.getenv('RELOAD', 'false').lower() == 'true',
        'workers': int(os.getenv('WORKERS', 1)),
        'log_level': os.getenv('LOG_LEVEL', 'info').lower(),
        'access_log': os.getenv('ACCESS_LOG', 'true').lower() == 'true',
    }


def print_startup_info(config):
    """Print server startup information."""
    print("\n" + "="*60)
    print("🚀 KDP Strategist FastAPI Server")
    print("="*60)
    print(f"📍 Server URL: http://{config['host']}:{config['port']}")
    print(f"📖 API Documentation: http://{config['host']}:{config['port']}/docs")
    print(f"🔧 Interactive API: http://{config['host']}:{config['port']}/redoc")
    print(f"💾 Log Level: {config['log_level'].upper()}")
    print(f"🔄 Auto-reload: {'Enabled' if config['reload'] else 'Disabled'}")
    print(f"👥 Workers: {config['workers']}")
    print("="*60)
    print("Press Ctrl+C to stop the server")
    print("="*60 + "\n")


def handle_shutdown(signum, frame):
    """Handle graceful shutdown."""
    print("\n🛑 Shutting down KDP Strategist server...")
    sys.exit(0)


def main():
    """Main entry point for the server."""
    # Setup logging
    logger = setup_logging()
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Get configuration
    config = get_server_config()
    
    # Print startup information
    print_startup_info(config)
    
    try:
        # Check if MCP agent dependencies are available
        logger.info("Checking MCP agent dependencies...")
        
        # Start the server
        logger.info(f"Starting KDP Strategist server on {config['host']}:{config['port']}")
        
        uvicorn.run(
            "api.main:app",
            host=config['host'],
            port=config['port'],
            reload=config['reload'],
            workers=config['workers'] if not config['reload'] else 1,
            log_level=config['log_level'],
            access_log=config['access_log'],
            server_header=False,
            date_header=False,
        )
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()