"""Mock KDP Strategist Agent for development and testing.

This is a mock implementation that provides hardcoded responses for development,
testing, CI/CD, demo mode, and as a fallback when the real MCP agent is unavailable.
It implements the same interface as the real KDPStrategistAgent but returns
predefined data instead of making actual API calls.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class MockKDPStrategistAgent:
    """Mock KDP Strategist Agent for development and testing purposes."""
    
    def __init__(self):
        self.initialized = False
        logger.info("Mock KDP Strategist Agent initialized")
    
    @classmethod
    async def create(cls):
        """Create and initialize the mock agent."""
        agent = cls()
        agent.initialized = True
        return agent
    
    async def cleanup(self):
        """Cleanup agent resources."""
        self.initialized = False
        logger.info("Mock agent cleaned up")
    
    # Mock methods for niche discovery
    async def discover_niches(self, keywords: List[str], **kwargs) -> Dict[str, Any]:
        """Mock niche discovery with hardcoded data."""
        return {
            "niches": [
                {
                    "name": "Self-Help Books",
                    "keywords": ["motivation", "productivity", "success"],
                    "competition_level": "medium",
                    "profitability_score": 85.5,
                    "search_volume": 15000,
                    "trend_direction": "rising",
                    "estimated_revenue": 2500,
                    "seasonality": {"jan": 1.0, "feb": 1.0, "mar": 1.0, "apr": 1.0, "may": 1.0, "jun": 1.0, "jul": 1.0, "aug": 1.0, "sep": 1.0, "oct": 1.0, "nov": 1.0, "dec": 1.0},
                    "barriers_to_entry": ["Content quality", "Marketing budget"]
                },
                {
                    "name": "Cooking Guides",
                    "keywords": ["recipes", "cooking", "kitchen"],
                    "competition_level": "high",
                    "profitability_score": 72.3,
                    "search_volume": 25000,
                    "trend_direction": "stable",
                    "estimated_revenue": 1800,
                    "seasonality": {"jan": 0.8, "feb": 0.9, "mar": 1.1, "apr": 1.2, "may": 1.3, "jun": 1.1, "jul": 0.9, "aug": 0.8, "sep": 1.0, "oct": 1.1, "nov": 1.4, "dec": 1.5},
                    "barriers_to_entry": ["High competition", "Recipe originality"]
                }
            ],
            "total_found": 2,
            "search_keywords": keywords,
            "execution_time": 2.5,
            "data_sources": ["keepa", "google_trends"],
            "cache_hit": False,
            "warnings": []
        }
    
    # Mock methods for competitor analysis
    async def analyze_competitors(self, niche: str, **kwargs) -> Dict[str, Any]:
        """Mock competitor analysis with hardcoded data."""
        return {
            "competitors": [
                {
                    "title": "The Ultimate Guide to Success",
                    "author": "John Doe",
                    "price": 9.99,
                    "rank": 1500,
                    "reviews": 245,
                    "rating": 4.5
                }
            ],
            "market_analysis": {
                "avg_price": 8.99,
                "avg_reviews": 150,
                "competition_level": "medium"
            }
        }
    
    # Mock methods for listing generation
    async def generate_listing(self, niche: str, **kwargs) -> Dict[str, Any]:
        """Mock listing generation with hardcoded data."""
        return {
            "title": f"Master {niche}: A Complete Guide",
            "description": f"Discover the secrets of {niche} with this comprehensive guide.",
            "keywords": [niche.lower(), "guide", "tips", "strategies"],
            "categories": ["Self-Help", "Business"],
            "seo_score": 85
        }
    
    # Mock methods for trend validation
    async def validate_trends(self, keywords: List[str], **kwargs) -> Dict[str, Any]:
        """Mock trend validation with hardcoded data."""
        return {
            "trends": [
                {
                    "keyword": keyword,
                    "trend_score": 75,
                    "search_volume": 10000,
                    "competition": "medium",
                    "forecast": "rising"
                }
                for keyword in keywords
            ],
            "overall_trend": "positive"
        }
    
    # Mock methods for stress testing
    async def stress_test_niche(self, niche: str, **kwargs) -> Dict[str, Any]:
        """Mock stress testing with hardcoded data."""
        return {
            "niche": niche,
            "stress_score": 70,
            "risk_factors": [
                "High competition",
                "Seasonal demand"
            ],
            "recommendations": [
                "Focus on long-tail keywords",
                "Consider sub-niches"
            ],
            "scenarios": {
                "best_case": {"revenue": 5000, "probability": 0.2},
                "worst_case": {"revenue": 500, "probability": 0.1},
                "most_likely": {"revenue": 2000, "probability": 0.7}
            }
        }