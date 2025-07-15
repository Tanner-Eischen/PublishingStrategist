"""KDP Strategist MCP Agent.

Main agent class that implements the Model Context Protocol (MCP) interface
for the KDP Strategist AI system. Coordinates all tools and services to provide
comprehensive publishing strategy analysis.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import (
        Tool, 
        TextContent, 
        CallToolRequest, 
        CallToolResult,
        ListToolsRequest,
        ListToolsResult
    )
except ImportError:
    raise ImportError("MCP library required. Install with: pip install mcp")

from ..data.cache_manager import CacheManager, CacheConfig
from ..data.keepa_client import KeepaClient, KeepaConfig
from ..data.trends_client import TrendsClient, TrendsConfig
from ..models.niche_model import Niche
from ..models.listing_model import KDPListing
from ..models.trend_model import TrendAnalysis
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class KDPStrategistAgent:
    """Main KDP Strategist MCP Agent.
    
    Provides AI-powered publishing strategy analysis through MCP tools:
    - find_profitable_niches: Discover profitable publishing niches
    - analyze_competitor_asin: Analyze competitor products
    - generate_kdp_listing: Create optimized KDP listings
    - validate_trend: Validate trend strength and sustainability
    - niche_stress_test: Test niche viability under various conditions
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the KDP Strategist Agent.
        
        Args:
            settings: Configuration settings. If None, loads from environment.
        """
        self.settings = settings or Settings()
        self.session_id = f"kdp_strategist_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize cache manager
        cache_config = CacheConfig(
            cache_type=self.settings.cache.cache_type,
            cache_dir=Path(self.settings.cache.cache_dir),
            redis_url=self.settings.cache.redis_url,
            default_ttl=self.settings.cache.default_ttl,
            max_cache_size=self.settings.cache.max_cache_size
        )
        self.cache_manager = CacheManager(cache_config)
        
        # Initialize API clients
        self._init_api_clients()
        
        # Tool registry
        self.tools = self._register_tools()
        
        # Statistics
        self.stats = {
            "session_start": datetime.now(),
            "tools_called": 0,
            "cache_hits": 0,
            "api_calls": 0,
            "errors": 0
        }
        
        logger.info(f"KDP Strategist Agent initialized (session: {self.session_id})")
    
    def _init_api_clients(self) -> None:
        """Initialize external API clients."""
        # Initialize Keepa client
        if self.settings.keepa.api_key:
            keepa_config = KeepaConfig(
                api_key=self.settings.keepa.api_key,
                rate_limit_per_minute=self.settings.keepa.rate_limit_per_minute,
                cache_ttl=self.settings.keepa.cache_ttl,
                enable_caching=self.settings.keepa.enable_caching
            )
            self.keepa_client = KeepaClient(keepa_config, self.cache_manager)
            logger.info("Keepa client initialized")
        else:
            self.keepa_client = None
            logger.warning("Keepa API key not provided - competitor analysis will be limited")
        
        # Initialize Trends client
        trends_config = TrendsConfig(
            geo=self.settings.trends.geo,
            language=self.settings.trends.language,
            rate_limit_delay=self.settings.trends.rate_limit_delay,
            cache_ttl=self.settings.trends.cache_ttl,
            enable_caching=self.settings.trends.enable_caching
        )
        self.trends_client = TrendsClient(trends_config, self.cache_manager)
        logger.info("Google Trends client initialized")
    
    def _register_tools(self) -> Dict[str, Tool]:
        """Register MCP tools."""
        tools = {
            "find_profitable_niches": Tool(
                name="find_profitable_niches",
                description="Discover profitable publishing niches based on market analysis, trends, and competition data.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "base_keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Base keywords to explore for niche discovery"
                        },
                        "categories": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Amazon categories to focus on (optional)"
                        },
                        "min_profitability_score": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                            "default": 60,
                            "description": "Minimum profitability score (0-100)"
                        },
                        "max_competition_level": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "default": "medium",
                            "description": "Maximum acceptable competition level"
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 50,
                            "default": 10,
                            "description": "Maximum number of niches to return"
                        }
                    },
                    "required": ["base_keywords"]
                }
            ),
            
            "analyze_competitor_asin": Tool(
                name="analyze_competitor_asin",
                description="Analyze competitor products on Amazon using ASIN to understand market positioning, pricing, and performance.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "asin": {
                            "type": "string",
                            "pattern": "^[A-Z0-9]{10}$",
                            "description": "Amazon ASIN (10-character alphanumeric code)"
                        },
                        "include_variations": {
                            "type": "boolean",
                            "default": False,
                            "description": "Include analysis of product variations"
                        },
                        "analyze_reviews": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include review sentiment analysis"
                        },
                        "historical_data": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include historical pricing and ranking data"
                        }
                    },
                    "required": ["asin"]
                }
            ),
            
            "generate_kdp_listing": Tool(
                name="generate_kdp_listing",
                description="Generate optimized KDP listing with title, description, keywords, and metadata based on niche analysis.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "niche": {
                            "type": "object",
                            "description": "Niche data from find_profitable_niches or manual input"
                        },
                        "target_audience": {
                            "type": "string",
                            "description": "Primary target audience for the book"
                        },
                        "book_type": {
                            "type": "string",
                            "enum": ["journal", "notebook", "planner", "coloring_book", "workbook", "guide", "other"],
                            "default": "journal",
                            "description": "Type of book/product"
                        },
                        "unique_angle": {
                            "type": "string",
                            "description": "Unique selling proposition or angle"
                        },
                        "price_range": {
                            "type": "object",
                            "properties": {
                                "min": {"type": "number", "minimum": 0.99},
                                "max": {"type": "number", "minimum": 0.99}
                            },
                            "description": "Target price range"
                        }
                    },
                    "required": ["niche", "target_audience"]
                }
            ),
            
            "validate_trend": Tool(
                name="validate_trend",
                description="Validate trend strength, sustainability, and seasonal patterns for keywords or niches.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Keywords to validate trends for"
                        },
                        "timeframe": {
                            "type": "string",
                            "enum": ["today 3-m", "today 12-m", "today 5-y", "all"],
                            "default": "today 12-m",
                            "description": "Time period for trend analysis"
                        },
                        "geo": {
                            "type": "string",
                            "default": "US",
                            "description": "Geographic region for analysis"
                        },
                        "include_forecast": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include 6-month trend forecast"
                        },
                        "seasonal_analysis": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include seasonal pattern analysis"
                        }
                    },
                    "required": ["keywords"]
                }
            ),
            
            "niche_stress_test": Tool(
                name="niche_stress_test",
                description="Perform comprehensive stress testing of a niche to assess viability under various market conditions.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "niche": {
                            "type": "object",
                            "description": "Niche data to stress test"
                        },
                        "test_scenarios": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["market_saturation", "trend_decline", "increased_competition", "seasonal_vulnerability", "price_pressure"]
                            },
                            "default": ["market_saturation", "trend_decline", "increased_competition"],
                            "description": "Stress test scenarios to run"
                        },
                        "severity_level": {
                            "type": "string",
                            "enum": ["mild", "moderate", "severe"],
                            "default": "moderate",
                            "description": "Severity level for stress testing"
                        },
                        "time_horizon": {
                            "type": "string",
                            "enum": ["3_months", "6_months", "12_months"],
                            "default": "6_months",
                            "description": "Time horizon for stress testing"
                        }
                    },
                    "required": ["niche"]
                }
            )
        }
        
        logger.info(f"Registered {len(tools)} MCP tools")
        return tools
    
    async def list_tools(self) -> ListToolsResult:
        """List available tools (MCP interface)."""
        return ListToolsResult(tools=list(self.tools.values()))
    
    async def call_tool(self, request: CallToolRequest) -> CallToolResult:
        """Call a tool (MCP interface)."""
        tool_name = request.params.name
        arguments = request.params.arguments or {}
        
        logger.info(f"Calling tool: {tool_name} with args: {list(arguments.keys())}")
        self.stats["tools_called"] += 1
        
        try:
            if tool_name == "find_profitable_niches":
                result = await self._find_profitable_niches(**arguments)
            elif tool_name == "analyze_competitor_asin":
                result = await self._analyze_competitor_asin(**arguments)
            elif tool_name == "generate_kdp_listing":
                result = await self._generate_kdp_listing(**arguments)
            elif tool_name == "validate_trend":
                result = await self._validate_trend(**arguments)
            elif tool_name == "niche_stress_test":
                result = await self._niche_stress_test(**arguments)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=str(result)
                    )
                ]
            )
        
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Tool {tool_name} failed: {e}")
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Error executing {tool_name}: {str(e)}"
                    )
                ],
                isError=True
            )
    
    async def _find_profitable_niches(self, base_keywords: List[str], 
                                     categories: Optional[List[str]] = None,
                                     min_profitability_score: float = 60,
                                     max_competition_level: str = "medium",
                                     limit: int = 10) -> Dict[str, Any]:
        """Find profitable niches implementation."""
        # Import here to avoid circular imports
        from .tools.niche_discovery import find_profitable_niches
        
        return await find_profitable_niches(
            trends_client=self.trends_client,
            keepa_client=self.keepa_client,
            cache_manager=self.cache_manager,
            base_keywords=base_keywords,
            categories=categories,
            min_profitability_score=min_profitability_score,
            max_competition_level=max_competition_level,
            limit=limit
        )
    
    async def _analyze_competitor_asin(self, asin: str,
                                      include_variations: bool = False,
                                      analyze_reviews: bool = True,
                                      historical_data: bool = True) -> Dict[str, Any]:
        """Analyze competitor ASIN implementation."""
        from .tools.competitor_analysis import analyze_competitor_asin
        
        return await analyze_competitor_asin(
            keepa_client=self.keepa_client,
            trends_client=self.trends_client,
            cache_manager=self.cache_manager,
            asin=asin,
            include_variations=include_variations,
            analyze_reviews=analyze_reviews,
            historical_data=historical_data
        )
    
    async def _generate_kdp_listing(self, niche: Dict[str, Any],
                                   target_audience: str,
                                   book_type: str = "journal",
                                   unique_angle: Optional[str] = None,
                                   price_range: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Generate KDP listing implementation."""
        from .tools.listing_generation import generate_kdp_listing
        
        return await generate_kdp_listing(
            trends_client=self.trends_client,
            keepa_client=self.keepa_client,
            cache_manager=self.cache_manager,
            niche=niche,
            target_audience=target_audience,
            book_type=book_type,
            unique_angle=unique_angle,
            price_range=price_range
        )
    
    async def _validate_trend(self, keywords: List[str],
                             timeframe: str = "today 12-m",
                             geo: str = "US",
                             include_forecast: bool = True,
                             seasonal_analysis: bool = True) -> Dict[str, Any]:
        """Validate trend implementation."""
        from .tools.trend_validation import validate_trend
        
        return await validate_trend(
            trends_client=self.trends_client,
            cache_manager=self.cache_manager,
            keywords=keywords,
            timeframe=timeframe,
            geo=geo,
            include_forecast=include_forecast,
            seasonal_analysis=seasonal_analysis
        )
    
    async def _niche_stress_test(self, niche: Dict[str, Any],
                                test_scenarios: List[str] = None,
                                severity_level: str = "moderate",
                                time_horizon: str = "6_months") -> Dict[str, Any]:
        """Niche stress test implementation."""
        from .tools.stress_testing import niche_stress_test
        
        if test_scenarios is None:
            test_scenarios = ["market_saturation", "trend_decline", "increased_competition"]
        
        return await niche_stress_test(
            trends_client=self.trends_client,
            keepa_client=self.keepa_client,
            cache_manager=self.cache_manager,
            niche=niche,
            test_scenarios=test_scenarios,
            severity_level=severity_level,
            time_horizon=time_horizon
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        uptime = datetime.now() - self.stats["session_start"]
        
        stats = {
            "session_id": self.session_id,
            "uptime_seconds": uptime.total_seconds(),
            "tools_called": self.stats["tools_called"],
            "cache_hits": self.stats["cache_hits"],
            "api_calls": self.stats["api_calls"],
            "errors": self.stats["errors"],
            "cache_stats": self.cache_manager.get_stats() if self.cache_manager else {},
        }
        
        if self.keepa_client:
            stats["keepa_stats"] = self.keepa_client.get_stats()
        
        if self.trends_client:
            stats["trends_stats"] = self.trends_client.get_stats()
        
        return stats
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self.cache_manager:
            self.cache_manager.cleanup_expired()
        
        logger.info(f"KDP Strategist Agent cleanup completed (session: {self.session_id})")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        asyncio.run(self.cleanup())