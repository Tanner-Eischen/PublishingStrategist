"""Adapter for KDPStrategistAgent to work with the API.

This adapter provides the interface expected by the API while using the real
KDPStrategistAgent implementation underneath.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Try multiple import strategies for the real agent
KDPStrategistAgent = None
Settings = None

try:
    # Try direct import from kdp-strategist directory
    import sys
    import os
    kdp_strategist_path = os.path.join(os.path.dirname(__file__), '..', '..', 'kdp-strategist')
    if kdp_strategist_path not in sys.path:
        sys.path.insert(0, kdp_strategist_path)
    
    from agent.kdp_strategist_agent import KDPStrategistAgent
    from config.settings import Settings
    logger.info("Successfully imported real KDPStrategistAgent")
except ImportError as e:
    logger.warning(f"Could not import real KDPStrategistAgent: {e}")
    # We'll handle this in the create method

class KDPStrategistAdapter:
    """Adapter to make KDPStrategistAgent compatible with API interface."""
    
    def __init__(self):
        self.agent: Optional[KDPStrategistAgent] = None
        self.initialized = False
        logger.info("KDP Strategist Adapter initialized")
    
    @classmethod
    async def create(cls):
        """Create and initialize the adapter with real agent."""
        adapter = cls()
        
        # Check if we successfully imported the real agent classes
        if KDPStrategistAgent is None or Settings is None:
            logger.error("Real KDPStrategistAgent classes not available")
            raise ImportError("Could not import real KDPStrategistAgent - falling back to mock")
        
        try:
            # Initialize the real agent
            settings = Settings()
            adapter.agent = KDPStrategistAgent(settings)
            await adapter.agent.initialize()
            adapter.initialized = True
            logger.info("Real KDP Strategist Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize real agent: {e}")
            # Fall back to mock behavior if real agent fails
            adapter.initialized = False
            raise
        return adapter
    
    async def cleanup(self):
        """Cleanup agent resources."""
        if self.agent:
            try:
                await self.agent.cleanup()
                logger.info("Real agent cleaned up")
            except Exception as e:
                logger.error(f"Error during agent cleanup: {e}")
        self.initialized = False
    
    async def discover_niches(self, keywords: List[str], **kwargs) -> Dict[str, Any]:
        """Discover niches using the real agent's find_profitable_niches tool."""
        if not self.agent or not self.initialized:
            raise RuntimeError("Agent not initialized")
        
        try:
            # Extract parameters with defaults
            categories = kwargs.get('categories')
            min_profitability_score = kwargs.get('min_profitability_score', 60)
            max_competition_level = kwargs.get('max_competition_level', 'medium')
            limit = kwargs.get('limit', 10)
            
            # Call the real agent's method
            result = await self.agent._find_profitable_niches(
                base_keywords=keywords,
                categories=categories,
                min_profitability_score=min_profitability_score,
                max_competition_level=max_competition_level,
                limit=limit
            )
            
            # Transform the result to match expected API format
            return self._transform_niches_result(result, keywords)
            
        except Exception as e:
            logger.error(f"Error in discover_niches: {e}")
            raise
    
    async def analyze_competitors(self, niche: str, **kwargs) -> Dict[str, Any]:
        """Analyze competitors using the real agent."""
        if not self.agent or not self.initialized:
            raise RuntimeError("Agent not initialized")
        
        try:
            # For now, return a basic structure since we need ASIN for real analysis
            # In a real implementation, you'd extract ASINs from the niche
            return {
                "competitors": [],
                "market_analysis": {
                    "avg_price": 0.0,
                    "avg_reviews": 0,
                    "competition_level": "unknown"
                },
                "message": "Competitor analysis requires specific ASINs. Use analyze_competitor_asin tool with specific product ASINs."
            }
            
        except Exception as e:
            logger.error(f"Error in analyze_competitors: {e}")
            raise
    
    async def generate_listing(self, niche: str, **kwargs) -> Dict[str, Any]:
        """Generate listing using the real agent."""
        if not self.agent or not self.initialized:
            raise RuntimeError("Agent not initialized")
        
        try:
            # Create a basic niche object for the real agent
            niche_data = {
                "name": niche,
                "keywords": [niche.lower()],
                "competition_level": "medium",
                "profitability_score": 70
            }
            
            target_audience = kwargs.get('target_audience', 'General audience')
            book_type = kwargs.get('book_type', 'journal')
            unique_angle = kwargs.get('unique_angle')
            price_range = kwargs.get('price_range')
            
            result = await self.agent._generate_kdp_listing(
                niche=niche_data,
                target_audience=target_audience,
                book_type=book_type,
                unique_angle=unique_angle,
                price_range=price_range
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in generate_listing: {e}")
            raise
    
    async def validate_trends(self, keywords: List[str], **kwargs) -> Dict[str, Any]:
        """Validate trends using the real agent."""
        if not self.agent or not self.initialized:
            raise RuntimeError("Agent not initialized")
        
        try:
            timeframe = kwargs.get('timeframe', 'today 12-m')
            geo = kwargs.get('geo', 'US')
            include_forecast = kwargs.get('include_forecast', True)
            seasonal_analysis = kwargs.get('seasonal_analysis', True)
            
            result = await self.agent._validate_trend(
                keywords=keywords,
                timeframe=timeframe,
                geo=geo,
                include_forecast=include_forecast,
                seasonal_analysis=seasonal_analysis
            )
            
            # Transform to expected format
            return self._transform_trends_result(result)
            
        except Exception as e:
            logger.error(f"Error in validate_trends: {e}")
            raise
    
    async def stress_test_niche(self, niche: str, **kwargs) -> Dict[str, Any]:
        """Stress test niche using the real agent."""
        if not self.agent or not self.initialized:
            raise RuntimeError("Agent not initialized")
        
        try:
            # Create a basic niche object
            niche_data = {
                "name": niche,
                "keywords": [niche.lower()],
                "competition_level": "medium",
                "profitability_score": 70
            }
            
            test_scenarios = kwargs.get('test_scenarios')
            severity_level = kwargs.get('severity_level', 'moderate')
            time_horizon = kwargs.get('time_horizon', '6_months')
            
            result = await self.agent._niche_stress_test(
                niche=niche_data,
                test_scenarios=test_scenarios,
                severity_level=severity_level,
                time_horizon=time_horizon
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in stress_test_niche: {e}")
            raise
    
    def _transform_niches_result(self, result: Dict[str, Any], keywords: List[str]) -> Dict[str, Any]:
        """Transform the real agent's niche result to match API expectations."""
        # The real agent returns a different structure, so we need to adapt it
        if 'niches' in result:
            return result
        
        # If the result doesn't have the expected structure, create it
        return {
            "niches": result.get('results', []),
            "total_found": len(result.get('results', [])),
            "search_keywords": keywords,
            "execution_time": result.get('execution_time', 0),
            "data_sources": result.get('data_sources', ["trends", "keepa"]),
            "cache_hit": result.get('cache_hit', False),
            "warnings": result.get('warnings', [])
        }
    
    def _transform_trends_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Transform the real agent's trend result to match API expectations."""
        if 'trends' in result:
            return result
        
        # Transform to expected format
        trends = []
        if 'keyword_data' in result:
            for keyword, data in result['keyword_data'].items():
                trends.append({
                    "keyword": keyword,
                    "trend_score": data.get('trend_score', 50),
                    "search_volume": data.get('search_volume', 0),
                    "competition": data.get('competition', 'medium'),
                    "forecast": data.get('forecast', 'stable')
                })
        
        return {
            "trends": trends,
            "overall_trend": result.get('overall_trend', 'neutral')
        }