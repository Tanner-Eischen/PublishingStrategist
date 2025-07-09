"""KDP Strategist AI Agent - MCP Integration.

This module provides the MCP (Model Context Protocol) agent implementation
for the KDP Strategist, enabling AI-powered publishing strategy analysis.

Core Components:
- KDPStrategistAgent: Main MCP agent class
- Tool implementations for niche discovery, competitor analysis, etc.
- Integration with external APIs (Keepa, Google Trends)
- Caching and performance optimization
"""

from .kdp_strategist_agent import KDPStrategistAgent
from .tools import (
    find_profitable_niches,
    analyze_competitor_asin,
    generate_kdp_listing,
    validate_trend,
    niche_stress_test
)

__all__ = [
    "KDPStrategistAgent",
    "find_profitable_niches",
    "analyze_competitor_asin", 
    "generate_kdp_listing",
    "validate_trend",
    "niche_stress_test"
]