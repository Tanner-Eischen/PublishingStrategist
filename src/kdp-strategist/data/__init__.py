"""Data layer for KDP Strategist AI Agent.

This module provides data access and caching functionality including:
- Cache management for API responses
- Keepa API client for Amazon product data
- Google Trends client for trend analysis
- Rate limiting and retry logic
- Data validation and transformation
"""

from .cache_manager import CacheManager, CacheConfig
from .keepa_client import KeepaClient
from .trends_client import TrendsClient

__all__ = [
    "CacheManager",
    "CacheConfig", 
    "KeepaClient",
    "TrendsClient",
]