#!/usr/bin/env python3
"""MCP Server entry point for KDP Strategist AI Agent.

This module provides a proper MCP server implementation that can be used
with MCP-compatible clients and AI assistants.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Sequence

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool,
        TextContent,
        CallToolRequest,
        CallToolResult,
        ListToolsRequest,
        ListToolsResult,
    )
except ImportError:
    raise ImportError("MCP library required. Install with: pip install mcp")

from config.settings import get_settings
from .agent.kdp_strategist_agent import KDPStrategistAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KDPStrategistMCPServer:
    """MCP Server wrapper for KDP Strategist Agent."""
    
    def __init__(self):
        """Initialize the MCP server."""
        self.server = Server("kdp-strategist")
        self.agent = None
        
        # Register MCP handlers
        self.server.list_tools = self.list_tools
        self.server.call_tool = self.call_tool
    
    async def initialize(self) -> None:
        """Initialize the KDP Strategist agent."""
        try:
            settings = get_settings()
            self.agent = KDPStrategistAgent(settings)
            logger.info("KDP Strategist MCP Server initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize KDP Strategist agent: {e}")
            raise
    
    async def list_tools(self) -> ListToolsResult:
        """List available tools."""
        if not self.agent:
            await self.initialize()
        
        return await self.agent.list_tools()
    
    async def call_tool(self, request: CallToolRequest) -> CallToolResult:
        """Call a tool."""
        if not self.agent:
            await self.initialize()
        
        return await self.agent.call_tool(request)
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self.agent:
            await self.agent.cleanup()
        logger.info("KDP Strategist MCP Server cleanup completed")


async def main() -> None:
    """Main entry point for the MCP server."""
    try:
        # Create and initialize the server
        mcp_server = KDPStrategistMCPServer()
        await mcp_server.initialize()
        
        logger.info("Starting KDP Strategist MCP Server...")
        logger.info("Available tools:")
        
        # List available tools for logging
        tools_result = await mcp_server.list_tools()
        for tool in tools_result.tools:
            logger.info(f"  - {tool.name}: {tool.description}")
        
        # Run the server
        async with stdio_server() as (read_stream, write_stream):
            await mcp_server.server.run(
                read_stream,
                write_stream,
                mcp_server.initialize
            )
    
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        if 'mcp_server' in locals():
            await mcp_server.cleanup()


if __name__ == "__main__":
    # Handle Windows event loop policy
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("MCP Server interrupted by user")
    except Exception as e:
        logger.error(f"MCP Server failed: {e}")
        sys.exit(1)