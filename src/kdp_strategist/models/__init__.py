"""Data models for KDP Strategist AI Agent.

This module contains all data structures used throughout the application:
- Niche: Represents a market niche with scoring and metadata
- KDPListing: Represents an optimized book listing for KDP
- TrendAnalysis: Represents trend analysis results and forecasts

All models include validation, serialization, and utility methods.
"""

from .niche_model import Niche, NicheCategory
from .listing_model import KDPListing, ListingCategory
from .trend_model import TrendAnalysis, TrendDirection, SeasonalPattern

__all__ = [
    "Niche",
    "NicheCategory",
    "KDPListing",
    "ListingCategory",
    "TrendAnalysis",
    "TrendDirection",
    "SeasonalPattern",
]