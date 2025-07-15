"""KDP Strategist AI Agent

An AI agent for Amazon Kindle Direct Publishing (KDP) that provides:
- Niche discovery and analysis
- Trend validation using Google Trends
- Competitor analysis using Amazon data
- Optimized listing generation
- Market stress testing

This package implements the Model Context Protocol (MCP) for seamless
integration with AI development environments.
"""

__version__ = "0.1.0"
__author__ = "KDP Strategist Team"
__description__ = "AI Agent for Amazon KDP Publishing Strategy"

from .agent import KDPStrategistAgent

__all__ = ["KDPStrategistAgent"]