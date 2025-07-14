"""KDP Strategist Tools.

This module contains the core tools for the KDP Strategist AI Agent:

- niche_discovery: Find profitable publishing niches
- competitor_analysis: Analyze competitor products and strategies
- listing_generation: Generate optimized KDP listings
- trend_validation: Validate trend strength and sustainability
- stress_testing: Test niche viability under various conditions

Each tool is designed to work independently while leveraging shared
data sources and caching for optimal performance.
"""

from .niche_discovery import find_profitable_niches
from .competitor_analysis import analyze_competitor_asin
from .listing_generation import generate_kdp_listing
from .trend_validation import validate_trend
from .stress_testing import niche_stress_test

__all__ = [
    "find_profitable_niches",
    "analyze_competitor_asin",
    "generate_kdp_listing",
    "validate_trend",
    "niche_stress_test"
]