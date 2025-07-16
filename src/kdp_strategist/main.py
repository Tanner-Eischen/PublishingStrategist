#!/usr/bin/env python3
"""Main entry point for the KDP Strategist AI Agent.

This module provides the main entry point for running the KDP Strategist
MCP (Model Context Protocol) agent. It handles:
- Agent initialization and configuration
- MCP server setup and connection
- Tool registration and management
- Error handling and logging
- Graceful shutdown procedures

Usage:
    python -m kdp_strategist.main
    
Or as a console script (after installation):
    kdp-_trategist
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional
import argparse

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from config.settings import Settings
from .agent.kdp_strategist_agent import KDPStrategistAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('kdp_strategist.log')
    ]
)

logger = logging.getLogger(__name__)


class KDPStrategistServer:
    """Main server class for the KDP Strategist MCP agent."""
    
    def __init__(self, settings: Settings):
        """Initialize the server with configuration settings."""
        self.settings = settings
        self.agent: Optional[KDPStrategistAgent] = None
        self.running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    async def start(self) -> None:
        """Start the KDP Strategist MCP agent server."""
        try:
            logger.info("Starting KDP Strategist AI Agent...")
            
            # Initialize the agent
            self.agent = KDPStrategistAgent(self.settings)
            await self.agent.initialize()
            
            logger.info("KDP Strategist Agent initialized successfully")
            logger.info(f"Available tools: {', '.join(await self.agent.list_tools())}")
            
            # Start the main server loop
            self.running = True
            await self._run_server_loop()
            
        except Exception as e:
            logger.error(f"Failed to start KDP Strategist Agent: {e}")
            raise
        finally:
            await self._cleanup()
    
    async def _run_server_loop(self) -> None:
        """Main server loop for handling MCP requests."""
        logger.info("KDP Strategist Agent is ready and waiting for requests...")
        logger.info("Press Ctrl+C to stop the agent")
        
        try:
            while self.running:
                # In a real MCP implementation, this would handle incoming requests
                # For now, we'll just keep the agent alive and ready
                await asyncio.sleep(1)
                
                # Optionally, perform periodic maintenance tasks
                if hasattr(self.agent, 'perform_maintenance'):
                    await self.agent.perform_maintenance()
        
        except asyncio.CancelledError:
            logger.info("Server loop cancelled")
        except Exception as e:
            logger.error(f"Error in server loop: {e}")
            raise
    
    async def _cleanup(self) -> None:
        """Cleanup resources before shutdown."""
        logger.info("Cleaning up resources...")
        
        if self.agent:
            try:
                await self.agent.cleanup()
                logger.info("Agent cleanup completed")
            except Exception as e:
                logger.error(f"Error during agent cleanup: {e}")
        
        logger.info("KDP Strategist Agent shutdown complete")


async def run_interactive_mode(agent: KDPStrategistAgent) -> None:
    """Run the agent in interactive mode for testing and development."""
    logger.info("Starting interactive mode...")
    logger.info("Type 'help' for available commands, 'quit' to exit")
    
    available_tools = await agent.list_tools()
    
    while True:
        try:
            user_input = input("\nKDP Strategist> ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            elif user_input.lower() == 'help':
                print("\nAvailable commands:")
                print("  help - Show this help message")
                print("  tools - List available tools")
                print("  test <tool_name> - Test a specific tool")
                print("  quit - Exit interactive mode")
                print("\nAvailable tools:")
                for tool in available_tools:
                    print(f"  - {tool}")
            elif user_input.lower() == 'tools':
                print("\nAvailable tools:")
                for tool in available_tools:
                    print(f"  - {tool}")
            elif user_input.lower().startswith('test '):
                tool_name = user_input[5:].strip()
                if tool_name in available_tools:
                    await _test_tool(agent, tool_name)
                else:
                    print(f"Unknown tool: {tool_name}")
            elif user_input:
                print("Unknown command. Type 'help' for available commands.")
        
        except KeyboardInterrupt:
            break
        except EOFError:
            break
        except Exception as e:
            logger.error(f"Error in interactive mode: {e}")
            print(f"Error: {e}")
    
    logger.info("Exiting interactive mode")


async def _test_tool(agent: KDPStrategistAgent, tool_name: str) -> None:
    """Test a specific tool with sample data."""
    print(f"\nTesting tool: {tool_name}")
    
    try:
        # Sample test parameters for each tool
        test_params = {
            "find_profitable_niches": {
                "base_keywords": ["cooking", "fitness"],
                "max_niches": 3,
                "min_profitability": 60
            },
            "analyze_competitor_asin": {
                "asin": "B08EXAMPLE",
                "include_market_analysis": True
            },
            "generate_kdp_listing": {
                "niche_keyword": "healthy cooking",
                "target_audience": "health-conscious adults",
                "book_type": "cookbook"
            },
            "validate_trend": {
                "keyword": "meal prep",
                "timeframe": "today 12-m",
                "include_forecasts": True
            },
            "niche_stress_test": {
                "niche_keyword": "keto recipes",
                "include_all_scenarios": True
            }
        }
        
        if tool_name in test_params:
            print(f"Running with test parameters: {test_params[tool_name]}")
            result = await agent.call_tool(tool_name, test_params[tool_name])
            
            if "error" in result:
                print(f"Tool returned error: {result['error']}")
            else:
                print("Tool executed successfully!")
                # Print a summary of the result
                if tool_name == "find_profitable_niches":
                    niches = result.get("discovered_niches", {})
                    print(f"Found {len(niches)} profitable niches")
                elif tool_name == "analyze_competitor_asin":
                    metrics = result.get("competitor_metrics", {})
                    print(f"Competitor analysis completed. Sales rank: {metrics.get('sales_rank', 'N/A')}")
                elif tool_name == "generate_kdp_listing":
                    listing = result.get("generated_listing", {})
                    print(f"Generated listing with title: {listing.get('title', 'N/A')[:50]}...")
                elif tool_name == "validate_trend":
                    validation = result.get("validation_result", {})
                    print(f"Trend validation: {validation.get('is_valid', False)}")
                elif tool_name == "niche_stress_test":
                    summary = result.get("stress_test_summary", {})
                    print(f"Stress test completed. Overall resilience: {summary.get('overall_resilience', 'N/A')}")
        else:
            print(f"No test parameters defined for tool: {tool_name}")
    
    except Exception as e:
        logger.error(f"Error testing tool {tool_name}: {e}")
        print(f"Error testing tool: {e}")


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="KDP Strategist AI Agent - MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Start the MCP server
  %(prog)s --interactive      # Run in interactive mode
  %(prog)s --config custom.env # Use custom config file
  %(prog)s --log-level DEBUG  # Enable debug logging
"""
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode for testing"
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to configuration file (default: .env)"
    )
    
    parser.add_argument(
        "--log-level", "-l",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="KDP Strategist AI Agent v1.0.0"
    )
    
    return parser.parse_args()


async def main() -> None:
    """Main entry point for the KDP Strategist AI Agent."""
    args = parse_arguments()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        settings = Settings.from_env()
        
        # Validate critical settings
        if not settings.api.keepa_api_key and settings.environment != "development":
            logger.warning("Keepa API key not configured. Some features may not work.")
        
        logger.info(f"Configuration loaded. Environment: {settings.environment}")
        
        if args.interactive:
            # Run in interactive mode
            logger.info("Starting in interactive mode...")
            agent = KDPStrategistAgent(settings)
            await agent.initialize()
            
            try:
                await run_interactive_mode(agent)
            finally:
                await agent.cleanup()
        else:
            # Run as MCP server
            server = KDPStrategistServer(settings)
            await server.start()
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Handle Windows event loop policy
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)