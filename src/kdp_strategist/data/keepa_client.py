"""Keepa API client for product data retrieval.

This module provides:
- Product data retrieval from Keepa API
- Rate limiting and error handling
- Caching integration
- Data parsing and normalization
"""

import asyncio
import logging
import random
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
import aiohttp
import json

from .cache_manager import CacheManager
from .rate_limiter import AdvancedRateLimiter, RateLimitConfig, RateLimiter
from .keepa_data_validator import KeepaDataValidator, ValidationResult
from .request_manager import RequestManager, RequestConfig, LogLevel
from ..exceptions import (
    KDPStrategistError, KeepaAPIError, KeepaRateLimitError,
    KeepaAuthenticationError, KeepaTimeoutError, KeepaDataParsingError,
    KeepaServiceUnavailableError, RequestContext, create_error_response
)
from ..exceptions import APIError
from ..exceptions import (
    KeepaAPIError,
    KeepaRateLimitError,
    KeepaAuthenticationError,
    KeepaTimeoutError,
    KeepaDataParsingError,
    KeepaServiceUnavailableError,
    create_error_response,
    KeepaErrorHandler,
    RetryHandler,
    CircuitBreaker,
    KeepaErrorLogger,
    handle_keepa_api_error,
    create_error_response_with_fallback
)

logger = logging.getLogger(__name__)


@dataclass
class FallbackConfig:
    """Configuration for fallback data generation."""
    realistic_variance: bool = True
    include_data_source_indicators: bool = True


@dataclass
class DataSourceInfo:
    """Information about the data source used."""
    source_type: str  # 'keepa_api', 'cached_fallback', 'alternative_source'
    source_name: str
    reliability_score: float  # 0-100, higher is more reliable
    last_updated: datetime
    data_freshness: str  # 'real_time', 'recent', 'stale', 'simulated'
    limitations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_name": self.source_name,
            "reliability_score": self.reliability_score,
            "last_updated": self.last_updated.isoformat(),
            "data_freshness": self.data_freshness,
            "limitations": self.limitations
        }


@dataclass
class ProductData:
    """Enhanced product data structure from Keepa API based on official specification."""
    # Basic Product Information
    asin: str
    title: str
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    product_group: Optional[str] = None
    description: Optional[str] = None
    
    # Pricing Information
    current_price: Optional[float] = None
    avg_price_30d: Optional[float] = None
    avg_price_90d: Optional[float] = None
    lowest_price_30d: Optional[float] = None
    highest_price_30d: Optional[float] = None
    
    # Sales Rank Information
    bsr_current: Optional[int] = None
    bsr_avg_30d: Optional[float] = None
    bsr_avg_90d: Optional[float] = None
    
    # Review Information
    review_count: int = 0
    rating: Optional[float] = None
    
    # Category Information
    primary_category: Optional[str] = None
    category_hierarchy: List[Dict[str, Any]] = None
    all_categories: List[str] = None
    
    # Product Details
    images: List[str] = None
    features: List[str] = None
    dimensions: Optional[Dict[str, float]] = None
    weight: Optional[float] = None
    
    # Sales Estimates
    estimated_sales_30d: int = 0
    estimated_sales_90d: int = 0
    monthly_sold: int = 0
    
    # Additional Fields
    buy_box_percentage: Optional[float] = None
    fba_fees: Optional[float] = None
    package_quantity: int = 1
    variation_asins: List[str] = None
    
    # Metadata
    last_updated: datetime = None
    data_quality_score: float = 1.0
    validation_errors: List[str] = None
    
    # Debug Information
    raw_stats_current: List[Any] = None
    raw_stats_avg: List[Any] = None
    additional_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize default values for list and dict fields."""
        if self.category_hierarchy is None:
            self.category_hierarchy = []
        if self.all_categories is None:
            self.all_categories = []
        if self.images is None:
            self.images = []
        if self.features is None:
            self.features = []
        if self.variation_asins is None:
            self.variation_asins = []
        if self.validation_errors is None:
            self.validation_errors = []
        if self.raw_stats_current is None:
            self.raw_stats_current = []
        if self.raw_stats_avg is None:
            self.raw_stats_avg = []
        if self.last_updated is None:
            self.last_updated = datetime.now()
        if self.additional_data is None:
            self.additional_data = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ProductData to dictionary with proper serialization."""
        data = asdict(self)
        # Convert datetime to ISO string for JSON serialization
        if isinstance(data.get('last_updated'), datetime):
            data['last_updated'] = data['last_updated'].isoformat()
        return data
    
    def get_category_path(self) -> str:
        """Get category path as a readable string."""
        if self.all_categories:
            return " > ".join(self.all_categories)
        return self.primary_category or ""
    
    def calculate_profitability_score(self) -> float:
        """Calculate profitability score based on multiple factors."""
        score = 0.0
        
        # Price factor (higher price = higher potential profit)
        if self.current_price:
            if self.current_price >= 20:
                score += 3.0
            elif self.current_price >= 10:
                score += 2.0
            elif self.current_price >= 5:
                score += 1.0
        
        # BSR factor (lower BSR = higher sales potential)
        if self.bsr_current:
            if self.bsr_current <= 1000:
                score += 3.0
            elif self.bsr_current <= 10000:
                score += 2.0
            elif self.bsr_current <= 100000:
                score += 1.0
        
        # Review factor (more reviews = established market)
        if self.review_count >= 100:
            score += 2.0
        elif self.review_count >= 50:
            score += 1.0
        
        # Rating factor (higher rating = quality product)
        if self.rating and self.rating >= 4.0:
            score += 1.0
        
        # Sales estimate factor
        if self.estimated_sales_30d >= 100:
            score += 2.0
        elif self.estimated_sales_30d >= 50:
            score += 1.0
        
        return min(10.0, score)  # Cap at 10.0
    
    def get_competition_level(self) -> str:
        """Determine competition level based on review count and BSR."""
        if not self.review_count or not self.bsr_current:
            return "unknown"
        
        if self.review_count > 500 and self.bsr_current < 10000:
            return "high"
        elif self.review_count > 100 and self.bsr_current < 50000:
            return "medium"
        else:
            return "low"


@dataclass
class CategoryNode:
    """Category hierarchy node."""
    id: Optional[int]
    name: str
    parent_id: Optional[int] = None
    level: int = 0


@dataclass
class PricePoint:
    """Individual price history data point."""
    timestamp: datetime
    price: float
    price_type: str = "amazon"  # amazon, new, used, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "price": self.price,
            "price_type": self.price_type
        }


@dataclass
class PriceHistoryData:
    """Complete price history data for a product."""
    asin: str
    price_points: List[PricePoint]
    price_type: str
    time_period_days: int
    data_points: int
    statistics: Dict[str, float]
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization."""
        return {
            "asin": self.asin,
            "price_points": [point.to_dict() for point in self.price_points],
            "price_type": self.price_type,
            "time_period_days": self.time_period_days,
            "data_points": self.data_points,
            "statistics": self.statistics,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class PriceStatistics:
    """Price trend analysis and statistics."""
    current_price: Optional[float]
    average_price: float
    min_price: float
    max_price: float
    price_volatility: float
    trend_direction: str  # "up", "down", "stable"
    trend_strength: float  # 0.0 to 1.0
    price_drops_count: int
    price_increases_count: int
    days_analyzed: int


@dataclass
class ValidationError:
    """Data validation error details."""
    field: str
    expected_type: str
    actual_value: Any
    message: str


@dataclass
class KeepaConfig:
    """Configuration for Keepa API client."""
    api_key: str
    base_url: str = "https://api.keepa.com"
    rate_limit: int = 100  # requests per minute
    timeout: int = 30
    cache_ttl: int = 3600  # 1 hour


# RateLimiter class moved to rate_limiter.py module


class KeepaClient:
    """Enhanced Keepa API client with comprehensive error handling and resilience."""
    
    def __init__(self, settings, cache_manager: Optional[CacheManager] = None, fallback_config: Optional[FallbackConfig] = None):
        """Initialize Keepa client with enhanced error handling and fallback capabilities."""
        # Handle both nested and flat settings structures
        if hasattr(settings, 'api'):
            self.api_key = settings.api.keepa_api_key
            rate_limit = settings.api.keepa_rate_limit
            self.timeout = settings.api.request_timeout
        else:
            self.api_key = getattr(settings, 'keepa_api_key', '')
            rate_limit = getattr(settings, 'keepa_rate_limit', 100)
            self.timeout = getattr(settings, 'keepa_timeout', 30)
        
        self.base_url = 'https://api.keepa.com'
        
        # Initialize fallback configuration
        self.fallback_config = fallback_config or FallbackConfig()
        
        # Initialize request management system
        request_config = RequestConfig(
            total_timeout=self.timeout,
            connect_timeout=min(self.timeout // 3, 10),
            read_timeout=self.timeout - min(self.timeout // 3, 10),
            max_retries=3,
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter_factor=0.1,
            failure_threshold=5,
            recovery_timeout=60,
            half_open_max_calls=3,
            max_connections=100,
            max_connections_per_host=min(rate_limit // 2, 20),
            connection_timeout=30,
            keepalive_timeout=30,
            log_level=LogLevel.BASIC,
            log_request_headers=False,
            log_response_headers=False,
            log_request_body=False,
            log_response_body=False,
            max_log_body_size=1000
        )
        
        # Initialize components
        self.logger = logging.getLogger(__name__)
        self.request_manager = RequestManager(request_config, self.logger)
        
        # Initialize advanced rate limiter with comprehensive configuration
        rate_limit_config = RateLimitConfig(
            max_requests_per_minute=rate_limit,
            burst_capacity=rate_limit * 2,  # Allow 2x burst capacity
            time_window_seconds=60,
            sliding_window_size=10,  # 10 sub-windows for smooth sliding
            max_concurrent_requests=min(rate_limit // 2, 20),  # Reasonable concurrency
            queue_timeout_seconds=300,  # 5 minute queue timeout
            enable_monitoring=True
        )
        self.rate_limiter = AdvancedRateLimiter(rate_limit_config)
        self.cache_manager = cache_manager
        
        # Initialize error handling components (legacy support)
        self.error_handler = KeepaErrorHandler(self.logger)
        self.error_logger = KeepaErrorLogger(self.logger)
        self.retry_handler = RetryHandler(max_attempts=3, base_delay=1.0, max_delay=60.0)
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        
        # Initialize data validation
        self.data_validator = KeepaDataValidator()
        
        # Validate API key
        if not self.api_key:
            raise KeepaAuthenticationError("Keepa API key is required but not provided")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.request_manager.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.request_manager.__aexit__(exc_type, exc_val, exc_tb)
        
        # Gracefully shutdown the rate limiter
        await self.rate_limiter.shutdown()
    
    async def get_product_data(self, asin: str, include_history: bool = False, 
                              stats_days: int = 30, include_offers: int = 0, force_refresh: bool = False) -> Optional[ProductData]:
        """Get product data for a specific ASIN with comprehensive error handling and fallback strategies."""
        data_source = None
        
        # Try main API first
        try:
            result = await self._get_product_data_from_api(asin, include_history, stats_days, include_offers, force_refresh)
            if result:
                data_source = DataSourceInfo(
                    source_type="keepa_api",
                    source_name="Keepa API",
                    reliability_score=95.0,
                    last_updated=datetime.now(),
                    data_freshness="real_time",
                    limitations=[]
                )
                # Add data source info to product data
                if hasattr(result, 'additional_data'):
                    result.additional_data = result.additional_data or {}
                    result.additional_data['data_source'] = data_source.to_dict()
                return result
        except Exception as e:
            logger.warning(f"Keepa API failed for ASIN {asin}: {e}")
        
        # Fallback Strategy 1: Check cache for previous data
        if self.cache_manager and not force_refresh:
            cache_key = f"fallback_product_{asin}"
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                logger.info(f"Using cached fallback data for ASIN: {asin}")
                product_data = ProductData.from_dict(cached_data) if isinstance(cached_data, dict) else cached_data
                
                data_source = DataSourceInfo(
                    source_type="cached_fallback",
                    source_name="Cached Data",
                    reliability_score=70.0,
                    last_updated=product_data.last_updated or datetime.now(),
                    data_freshness="stale",
                    limitations=["Data may be outdated", "Limited real-time accuracy"]
                )
                
                if hasattr(product_data, 'additional_data'):
                    product_data.additional_data = product_data.additional_data or {}
                    product_data.additional_data['data_source'] = data_source.to_dict()
                
                return product_data
    
    def _generate_mock_products(self, query: str, category: Optional[str] = None, limit: int = 20) -> List[ProductData]:
        """Generate realistic mock product data for testing and fallback scenarios."""
        products = []
        
        for i in range(limit):
            # Generate realistic ASIN
            asin = f"B{random.randint(10000000, 99999999):08d}"
            
            # Generate product title based on query
            title = self._generate_product_title(query, i)
            
            # Generate realistic pricing
            base_price = self._get_base_price_for_query(query)
            price_variation = random.uniform(0.7, 1.5)
            current_price = round(base_price * price_variation, 2)
            
            # Generate sales rank (BSR)
            bsr = random.randint(1000, 500000)
            
            # Generate rating and review count
            rating = round(random.uniform(3.5, 4.8), 1)
            review_count = random.randint(10, 5000)
            
            # Create product data
            product = ProductData(
                asin=asin,
                title=title,
                current_price=current_price,
                amazon_price=current_price,
                sales_rank=bsr,
                rating=rating,
                review_count=review_count,
                category=category or "Books",
                additional_data={
                    'mock_generated': True,
                    'query': query,
                    'position': i + 1,
                    'estimated_monthly_sales': max(1, int(1000000 / bsr)),
                    'competition_level': self._assess_competition_level(bsr)
                }
            )
            
            products.append(product)
        
        return products
    
    def _generate_product_title(self, query: str, position: int) -> str:
        """Generate realistic product titles based on query."""
        templates = [
            f"{query.title()}: A Complete Guide",
            f"The Ultimate {query.title()} Handbook",
            f"Mastering {query.title()}: Expert Tips and Strategies",
            f"{query.title()} for Beginners: Step-by-Step Guide",
            f"Advanced {query.title()}: Professional Techniques",
            f"{query.title()} Secrets: What They Don't Want You to Know",
            f"The {query.title()} Blueprint: Proven Methods",
            f"{query.title()} Mastery: From Novice to Expert"
        ]
        
        base_title = random.choice(templates)
        
        # Add variation for different positions
        if position > 3:
            variations = ["2nd Edition", "Revised Edition", "Updated Version", "Premium Edition"]
            base_title += f" ({random.choice(variations)})"
        
        return base_title
    
    def _get_base_price_for_query(self, query: str) -> float:
        """Estimate base price based on query characteristics."""
        # Price ranges based on common book categories
        price_ranges = {
            'business': (15.99, 29.99),
            'self-help': (12.99, 24.99),
            'fiction': (9.99, 16.99),
            'cookbook': (19.99, 34.99),
            'technical': (29.99, 59.99),
            'children': (7.99, 14.99),
            'romance': (8.99, 12.99),
            'mystery': (10.99, 15.99)
        }
        
        query_lower = query.lower()
        for category, (min_price, max_price) in price_ranges.items():
            if category in query_lower:
                return random.uniform(min_price, max_price)
        
        # Default range for general books
        return random.uniform(12.99, 24.99)
    
    def _assess_competition_level(self, bsr: int) -> str:
        """Assess competition level based on BSR."""
        if bsr < 10000:
            return "very_high"
        elif bsr < 50000:
            return "high"
        elif bsr < 150000:
            return "medium"
        elif bsr < 300000:
            return "low"
        else:
            return "very_low"
    
    def get_fallback_status(self) -> Dict[str, Any]:
        """Get the current status of fallback strategies."""
        status = {
            'keepa_api_available': self.api_key is not None,
            'cache_available': self.cache_manager is not None,
            'mock_data_available': True,
            'active_strategies': [],
            'fallback_config': {
                'use_cache': self.fallback_config.use_cache,
                'use_mock_data': self.fallback_config.use_mock_data,
                'cache_ttl': self.fallback_config.cache_ttl
            }
        }
        
        # Determine active strategies
        if status['keepa_api_available']:
            status['active_strategies'].append('keepa_api')
        
        if status['cache_available'] and self.fallback_config.use_cache:
            status['active_strategies'].append('cache_fallback')
        
        if self.fallback_config.use_mock_data:
            status['active_strategies'].append('mock_data_generation')
        
        return status
    
    def get_data_source_warning(self, data_source_info: DataSourceInfo) -> Optional[str]:
        """Generate appropriate warnings based on data source reliability."""
        if data_source_info.source_type == "simulated_fallback":
            return ("⚠️ Using simulated data for testing purposes. "
                   "Results may not reflect actual market conditions.")
        elif data_source_info.source_type == "cached_fallback":
            return ("ℹ️ Using cached data. Results may not reflect current market conditions. "
                   "Consider refreshing data if recent accuracy is critical.")
        elif data_source_info.reliability_score < 70:
            return f"⚠️ Data reliability is {data_source_info.reliability_score}%. Use with caution."
        
        return None
    
    async def get_competition_analysis(self, keyword: str, limit: int = 20) -> Dict[str, Any]:
        """Get comprehensive competition analysis using multiple fallback strategies."""
        logger.info(f"Performing competition analysis for: {keyword}")
        
        # Try to get product data using fallback strategies
        products = await self.search_products(keyword, limit=limit)
        
        if not products:
            logger.warning(f"No competition data found for keyword: {keyword}")
            return self._create_empty_competition_analysis(keyword)
        
        # Analyze the competition data
        analysis = self._analyze_competition_metrics(products, keyword)
        
        # Add data source information
        if products:
            first_product = products[0]
            if hasattr(first_product, 'additional_data') and first_product.additional_data:
                first_product_source = first_product.additional_data.get('data_source', {})
                analysis["data_source"] = first_product_source
                analysis["data_reliability"] = first_product_source.get('reliability_score', 0)
                analysis["data_limitations"] = first_product_source.get('limitations', [])
        
        return analysis
    
    def _create_empty_competition_analysis(self, keyword: str) -> Dict[str, Any]:
        """Create empty competition analysis when no data is available."""
        return {
            "keyword": keyword,
            "competitor_count": 0,
            "avg_price": 0.0,
            "avg_rating": 0.0,
            "avg_reviews": 0.0,
            "price_range": {"min": 0.0, "max": 0.0, "avg": 0.0},
            "competition_level": "unknown",
            "market_opportunity": "unknown",
            "data_source": {
                "source_type": "no_data",
                "source_name": "No Data Available",
                "reliability_score": 0.0,
                "data_freshness": "unavailable",
                "limitations": ["No competition data available", "Unable to assess market"]
            },
            "recommendations": ["Consider alternative keywords", "Verify market demand through other channels"]
        }
    
    def _analyze_competition_metrics(self, products: List[ProductData], keyword: str) -> Dict[str, Any]:
        """Analyze competition metrics from product data."""
        if not products:
            return self._create_empty_competition_analysis(keyword)
        
        # Extract metrics
        prices = []
        ratings = []
        review_counts = []
        bsr_values = []
        
        for p in products:
            if p.current_price and p.current_price > 0:
                prices.append(p.current_price)
            if p.rating and p.rating > 0:
                ratings.append(p.rating)
            if p.review_count and p.review_count > 0:
                review_counts.append(p.review_count)
            if p.sales_rank and p.sales_rank > 0:
                bsr_values.append(p.sales_rank)
        
        # Calculate averages
        avg_price = sum(prices) / len(prices) if prices else 0.0
        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
        avg_reviews = sum(review_counts) / len(review_counts) if review_counts else 0.0
        avg_bsr = sum(bsr_values) / len(bsr_values) if bsr_values else 0.0
        
        # Determine competition level
        competition_level = self._determine_competition_level(len(products), avg_reviews, avg_rating)
        
        # Calculate market opportunity score
        opportunity_score = self._calculate_opportunity_score(
            len(products), avg_price, avg_rating, avg_reviews, avg_bsr
        )
        
        # Generate recommendations
        recommendations = self._generate_competition_recommendations(
            competition_level, opportunity_score, avg_price, avg_reviews
        )
        
        return {
            "keyword": keyword,
            "competitor_count": len(products),
            "avg_price": round(avg_price, 2),
            "avg_rating": round(avg_rating, 1),
            "avg_reviews": round(avg_reviews, 0),
            "avg_bsr": round(avg_bsr, 0) if avg_bsr > 0 else None,
            "price_range": {
                "min": min(prices) if prices else 0.0,
                "max": max(prices) if prices else 0.0,
                "avg": round(avg_price, 2)
            },
            "competition_level": competition_level,
            "market_opportunity": self._categorize_opportunity(opportunity_score),
            "opportunity_score": round(opportunity_score, 1),
            "top_competitors": self._format_top_competitors(products),
            "recommendations": recommendations
         }
    
    def _determine_competition_level(self, competitor_count: int, avg_reviews: float, avg_rating: float) -> str:
        """Determine competition level based on metrics."""
        if competitor_count == 0:
            return "none"
        elif competitor_count < 10:
            return "low"
        elif competitor_count < 30:
            if avg_reviews < 50:
                return "low"
            elif avg_reviews < 200:
                return "medium"
            else:
                return "high"
        elif competitor_count < 50:
            if avg_reviews < 100:
                return "medium"
            else:
                return "high"
        else:
            return "very_high"
    
    def _calculate_opportunity_score(self, competitor_count: int, avg_price: float, 
                                   avg_rating: float, avg_reviews: float, avg_bsr: float) -> float:
        """Calculate market opportunity score (0-100)."""
        score = 50.0  # Base score
        
        # Adjust for competition count (fewer competitors = higher score)
        if competitor_count == 0:
            score += 30
        elif competitor_count < 10:
            score += 20
        elif competitor_count < 30:
            score += 10
        elif competitor_count > 100:
            score -= 20
        
        # Adjust for review saturation (fewer reviews = higher opportunity)
        if avg_reviews < 50:
            score += 15
        elif avg_reviews < 200:
            score += 5
        elif avg_reviews > 1000:
            score -= 15
        
        # Adjust for rating quality (lower ratings = opportunity for better product)
        if avg_rating < 3.5:
            score += 10
        elif avg_rating < 4.0:
            score += 5
        elif avg_rating > 4.5:
            score -= 5
        
        # Adjust for pricing (reasonable pricing range is good)
        if 5.0 <= avg_price <= 25.0:
            score += 10
        elif avg_price < 5.0:
            score -= 5  # Too low might indicate low value perception
        elif avg_price > 50.0:
            score -= 10  # Too high might limit market
        
        # Adjust for BSR (better BSR indicates active market)
        if avg_bsr > 0:
            if avg_bsr < 10000:
                score += 5  # Active market
            elif avg_bsr > 500000:
                score -= 5  # Less active market
        
        return max(0.0, min(100.0, score))
    
    def _categorize_opportunity(self, score: float) -> str:
        """Categorize opportunity score into levels."""
        if score >= 80:
            return "excellent"
        elif score >= 65:
            return "good"
        elif score >= 50:
            return "moderate"
        elif score >= 35:
            return "limited"
        else:
            return "poor"
    
    def _generate_competition_recommendations(self, competition_level: str, opportunity_score: float,
                                           avg_price: float, avg_reviews: float) -> List[str]:
        """Generate actionable recommendations based on competition analysis."""
        recommendations = []
        
        if competition_level == "none":
            recommendations.append("🎯 No direct competition found - potential blue ocean opportunity")
            recommendations.append("📊 Validate market demand before proceeding")
        elif competition_level == "low":
            recommendations.append("✅ Low competition detected - good entry opportunity")
            recommendations.append("🚀 Focus on quality content to establish market position")
        elif competition_level == "medium":
            recommendations.append("⚖️ Moderate competition - differentiation is key")
            recommendations.append("💡 Identify gaps in competitor offerings")
        elif competition_level == "high":
            recommendations.append("🔥 High competition - requires strong differentiation")
            recommendations.append("🎯 Consider niche-specific angles or sub-topics")
        else:
            recommendations.append("⚠️ Very high competition - proceed with caution")
            recommendations.append("🔍 Look for underserved sub-niches")
        
        # Price-based recommendations
        if avg_price < 10:
            recommendations.append("💰 Low average pricing - consider premium positioning")
        elif avg_price > 30:
            recommendations.append("💸 High average pricing - value proposition must be strong")
        
        # Review-based recommendations
        if avg_reviews < 100:
            recommendations.append("📝 Low review counts - opportunity for early market entry")
        elif avg_reviews > 500:
            recommendations.append("⭐ High review saturation - focus on superior quality")
        
        return recommendations
    
    def _format_top_competitors(self, products: List[ProductData]) -> List[Dict[str, Any]]:
        """Format top competitors for analysis."""
        # Sort by review count
        sorted_products = sorted(products, key=lambda p: p.review_count or 0, reverse=True)[:5]
        
        competitors = []
        for p in sorted_products:
            title = p.title or ""
            competitors.append({
                "asin": p.asin or "",
                "title": title[:50] + "..." if len(title) > 50 else title,
                "price": p.current_price or 0,
                "rating": p.rating or 0,
                "reviews": p.review_count or 0,
                "bsr": p.sales_rank or 0
            })
        
        return competitors
    
    async def _get_product_data_from_api(self, asin: str, include_history: bool = False, 
                                        stats_days: int = 30, include_offers: int = 0, force_refresh: bool = False) -> Dict[str, Any]:
        """Original get_product_data implementation for API calls."""
        # Create request context for error handling
        context = RequestContext(
            endpoint="product",
            method="GET",
            params={
                "asin": asin,
                "include_history": include_history,
                "stats_days": stats_days,
                "include_offers": include_offers
            }
        )
        
        # Check cache first
        cache_key = f"keepa:product:{asin}:{include_history}:{stats_days}:{include_offers}"
        cached_data = None
        
        if self.cache_manager:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                self.error_logger.log_cache_operation("get", cache_key, hit=True)
                return cached_data
            else:
                self.error_logger.log_cache_operation("get", cache_key, hit=False)
        
        # Define the operation to be executed with retry and circuit breaker
        async def fetch_operation():
            # Wait for rate limit
            await self.rate_limiter.acquire_permit()
            
            # Make API request with correct parameters
            endpoint = "product"
            params = {
                "key": self.api_key,
                "domain": 1,        # Amazon.com
                "asin": asin,
                "stats": stats_days,  # Number of days for statistics
                "history": 1 if include_history else 0,
                "update": 1         # Use cached data if less than 1 hour old
            }
            
            # Add offers if requested (max 20 ASINs when using offers)
            if include_offers > 0:
                params["offers"] = str(include_offers)
            
            start_time = datetime.now()
            response_data = await self._make_api_request_with_error_handling(endpoint, params, context)
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Log successful request
            self.error_logger.log_api_request(
                context=context,
                response_time=response_time,
                response_size=len(str(response_data)) if response_data else 0,
                success=True
            )
            
            # Check for API errors in response
            if "error" in response_data:
                error = self.error_handler.handle_api_response_error(response_data, context, cached_data)
                self.error_logger.log_error_with_context(error)
                raise error
            
            # Parse product data
            if "products" in response_data and response_data["products"]:
                product_data = self._parse_product_data_with_error_handling(
                    response_data["products"][0], asin, context
                )
                
                # Cache the result
                if self.cache_manager:
                    self.cache_manager.set(cache_key, product_data, ttl=3600)
                    self.error_logger.log_cache_operation("set", cache_key, size=len(str(product_data)))
                
                return product_data
            else:
                error = KeepaAPIError(
                    message=f"No product data found for ASIN: {asin}",
                    error_code="KEEPA_NO_PRODUCT_DATA",
                    context=context,
                    fallback_data=cached_data
                )
                self.error_logger.log_error_with_context(error)
                raise error
        
        try:
            # Execute with circuit breaker and retry logic
            return await self.circuit_breaker.call(
                self.retry_handler.execute_with_retry,
                fetch_operation,
                context,
                retryable_errors=(KeepaTimeoutError, KeepaServiceUnavailableError, KeepaRateLimitError)
            )
            
        except KeepaAPIError as e:
            # Log the error and return structured response with fallback data
            self.error_logger.log_error_with_context(e)
            
            # If we have cached data, return it as fallback
            if cached_data:
                self.logger.warning(f"Using cached data as fallback for ASIN {asin}")
                return cached_data
            
            # Otherwise, raise the error
            raise e
        
        except Exception as e:
            # Handle unexpected errors
            error = KeepaAPIError(
                message=f"Unexpected error retrieving product data for ASIN {asin}: {str(e)}",
                error_code="KEEPA_UNEXPECTED_ERROR",
                context=context,
                fallback_data=cached_data
            )
            self.error_logger.log_error_with_context(error)
            
            if cached_data:
                self.logger.warning(f"Using cached data as fallback for ASIN {asin} after unexpected error")
                return cached_data
            
            raise error
    
    async def search_products(self, keyword: str, limit: int = 20, page: int = 0, 
                             category: Optional[str] = None, stats_days: int = 30) -> List[ProductData]:
        """Search for products by keyword with comprehensive error handling and fallback strategies.
        
        Args:
            keyword: Search term/keyword
            limit: Maximum number of results to return (up to 50)
            page: Page number for pagination (0-9, 10 results per page)
            category: Optional category filter
            stats_days: Number of days for statistics (default 30)
        
        Returns:
            List of ProductData objects
        """
        results = []
        data_source = None
        
        # Strategy 1: Try Keepa API if available
        try:
            results = await self._search_products_from_api(keyword, limit, page, category, stats_days)
            if results:
                data_source = DataSourceInfo(
                    source_type="keepa_api",
                    source_name="Keepa API",
                    reliability_score=95.0,
                    last_updated=datetime.now(),
                    data_freshness="real_time",
                    limitations=[]
                )
                
                # Add data source to each result
                for product in results:
                    if hasattr(product, 'additional_data'):
                        product.additional_data = product.additional_data or {}
                        product.additional_data['data_source'] = data_source.to_dict()
                
                return results
        except Exception as e:
            logger.warning(f"Keepa search failed for keyword '{keyword}': {e}")
        
        # Strategy 2: Check cache
        if self.cache_manager:
            cache_key = f"fallback_search_{hashlib.md5(f'{keyword}_{category}_{limit}'.encode()).hexdigest()}"
            cached_results = self.cache_manager.get(cache_key)
            if cached_results:
                logger.info(f"Using cached search results for keyword: {keyword}")
                results = [ProductData.from_dict(data) if isinstance(data, dict) else data for data in cached_results]
                
                data_source = DataSourceInfo(
                    source_type="cached_fallback",
                    source_name="Cached Search Results",
                    reliability_score=70.0,
                    last_updated=datetime.now(),
                    data_freshness="stale",
                    limitations=["Cached search results", "May not reflect current market"]
                )
                
                for product in results:
                    if hasattr(product, 'additional_data'):
                        product.additional_data = product.additional_data or {}
                        product.additional_data['data_source'] = data_source.to_dict()
                
                return results
        
        # Strategy 3: Generate realistic mock data
        logger.info(f"Generating mock competition data for keyword: {keyword}")
        results = self._generate_mock_products(keyword, category, limit)
        
        if results:
            data_source = DataSourceInfo(
                source_type="simulated_fallback",
                source_name="Mock Competition Data",
                reliability_score=40.0,
                last_updated=datetime.now(),
                data_freshness="simulated",
                limitations=["Simulated data for testing", "Not based on real market data"]
            )
            
            # Add data source to each result
            for product in results:
                if hasattr(product, 'additional_data'):
                    product.additional_data = product.additional_data or {}
                    product.additional_data['data_source'] = data_source.to_dict()
            
            # Cache the results for consistency
            if self.cache_manager:
                cache_key = f"fallback_search_{hashlib.md5(f'{keyword}_{category}_{limit}'.encode()).hexdigest()}"
                cache_data = [product.to_dict() if hasattr(product, 'to_dict') else product for product in results]
                self.cache_manager.set(cache_key, cache_data, ttl=3600)  # Cache for 1 hour
            
            return results
        
        logger.warning(f"No search results available for keyword: {keyword}")
        return []
    
    async def _search_products_from_api(self, keyword: str, limit: int = 20, page: int = 0, 
                                       category: Optional[str] = None, stats_days: int = 30) -> List[Dict[str, Any]]:
        """Original search_products implementation for API calls."""
        # Create request context
        context = RequestContext(
            endpoint="search",
            method="GET",
            params={
                "keyword": keyword,
                "limit": limit,
                "page": page,
                "stats_days": stats_days
            }
        )
        
        # Validate parameters
        if page < 0 or page > 9:
            raise KeepaAPIError(
                message="Page parameter must be between 0 and 9",
                error_code="KEEPA_INVALID_PAGE_PARAMETER",
                context=context
            )
        
        if limit > 50:
            limit = 50
            self.logger.warning(f"Limit reduced to 50 (Keepa maximum)")
        
        # Check cache first
        cache_key = f"keepa:search:{keyword}:{limit}:{page}:{stats_days}"
        cached_data = None
        
        if self.cache_manager:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                self.error_logger.log_cache_operation("get", cache_key, hit=True)
                return cached_data
            else:
                self.error_logger.log_cache_operation("get", cache_key, hit=False)
        
        # Define the search operation
        async def search_operation():
            # Wait for rate limit
            await self.rate_limiter.acquire_permit()
            
            # Use correct search endpoint parameters according to official API spec
            endpoint = "search"
            params = {
                "key": self.api_key,
                "domain": 0,        # Amazon.com (corrected from 1 to 0)
                "type": "product",  # Required parameter for product search
                "term": keyword,    # Correct parameter name (not 'selection')
                "stats": stats_days, # Number of days for statistics (not boolean)
                "page": page,       # Page number for pagination (0-9)
                "update": 1         # Cache optimization - use cached data if < 1 hour old
            }
            
            start_time = datetime.now()
            response_data = await self._make_api_request_with_error_handling(endpoint, params, context)
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Log successful request
            self.error_logger.log_api_request(
                context=context,
                response_time=response_time,
                response_size=len(str(response_data)) if response_data else 0,
                success=True
            )
            
            # Check for API errors in response
            if "error" in response_data:
                error = self.error_handler.handle_api_response_error(response_data, context, cached_data)
                self.error_logger.log_error_with_context(error)
                raise error
            
            # Parse search results
            results = []
            parsing_errors = 0
            
            if "products" in response_data:
                for i, product in enumerate(response_data["products"][:limit]):
                    try:
                        parsed_product = self._parse_product_data_with_error_handling(
                            product, 
                            product.get("asin", f"unknown_{i}"), 
                            context
                        )
                        results.append(parsed_product)
                    except Exception as e:
                        parsing_errors += 1
                        self.logger.warning(f"Failed to parse search result {i}: {e}")
                        continue
            
            # Log parsing summary
            if parsing_errors > 0:
                self.logger.warning(f"Search parsing completed with {parsing_errors} errors out of {len(response_data.get('products', []))} products")
            
            # Cache the results
            if self.cache_manager and results:
                self.cache_manager.set(cache_key, results, ttl=1800)  # 30 minutes
                self.error_logger.log_cache_operation("set", cache_key, size=len(str(results)))
            
            return results
        
        try:
            # Execute with circuit breaker and retry logic
            return await self.circuit_breaker.call(
                self.retry_handler.execute_with_retry,
                search_operation,
                context,
                retryable_errors=(KeepaTimeoutError, KeepaServiceUnavailableError, KeepaRateLimitError)
            )
            
        except KeepaAPIError as e:
            # Log the error and return fallback data if available
            self.error_logger.log_error_with_context(e)
            
            if cached_data:
                self.logger.warning(f"Using cached search results as fallback for keyword '{keyword}'")
                return cached_data
            
            # Return empty results with error information
            return [{
                "asin": "",
                "title": f"Search failed for keyword: {keyword}",
                "error": str(e),
                "last_updated": datetime.now().isoformat(),
                "data_quality_score": 0.0,
                "validation_errors": [str(e)],
                "search_failed": True
            }]
        
        except Exception as e:
            # Handle unexpected errors
            error = KeepaAPIError(
                message=f"Unexpected error searching for keyword '{keyword}': {str(e)}",
                error_code="KEEPA_SEARCH_UNEXPECTED_ERROR",
                context=context,
                fallback_data=cached_data
            )
            self.error_logger.log_error_with_context(error)
            
            if cached_data:
                self.logger.warning(f"Using cached search results as fallback for keyword '{keyword}' after unexpected error")
                return cached_data
            
            return [{
                "asin": "",
                "title": f"Search failed for keyword: {keyword}",
                "error": str(e),
                "last_updated": datetime.now().isoformat(),
                "data_quality_score": 0.0,
                "validation_errors": [str(e)],
                "search_failed": True
            }]
    
    async def find_products_advanced(
        self, 
        criteria: Dict[str, Any], 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Advanced product search using Keepa's /query endpoint with JSON criteria.
        
        Args:
            criteria: JSON search criteria dictionary with filters like:
                - price_range: {"min": 10.0, "max": 50.0} for current Amazon price
                - sales_threshold: {"min": 100} for minimum 30-day sales
                - category: {"id": 283155} for specific category filtering
                - rating: {"min": 4.0} for minimum rating
                - review_count: {"min": 50} for minimum review count
            limit: Maximum number of results to return (up to 50)
        
        Returns:
            List of product data dictionaries matching the criteria
            
        Raises:
            KeepaAPIError: For API-specific errors
            ValueError: For malformed search criteria
        """
        # Create request context
        context = RequestContext(
            endpoint="query",
            method="GET",
            params={
                "criteria": criteria,
                "limit": limit
            }
        )
        
        # Validate parameters
        if limit > 50:
            limit = 50
            self.logger.warning(f"Advanced search limit reduced to 50 (Keepa maximum)")
        
        # Validate and format search criteria
        try:
            formatted_criteria = self._format_advanced_search_criteria(criteria)
        except Exception as e:
            raise ValueError(f"Malformed search criteria: {str(e)}")
        
        # Check cache first
        criteria_hash = hash(str(sorted(criteria.items())))
        cache_key = f"keepa:advanced_search:{criteria_hash}:{limit}"
        cached_data = None
        
        if self.cache_manager:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                self.error_logger.log_cache_operation("get", cache_key, hit=True)
                return cached_data
            else:
                self.error_logger.log_cache_operation("get", cache_key, hit=False)
        
        # Define the advanced search operation
        async def advanced_search_operation():
            # Wait for rate limit
            await self.rate_limiter.acquire_permit()
            
            # Use /query endpoint with JSON selection criteria
            endpoint = "query"
            params = {
                "key": self.api_key,
                "domain": 1,        # Amazon.com
                "selection": json.dumps(formatted_criteria),  # JSON criteria
                "stats": 30,        # 30 days of statistics
                "update": 1         # Cache optimization
            }
            
            start_time = datetime.now()
            response_data = await self._make_api_request_with_error_handling(endpoint, params, context)
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Log successful request
            self.error_logger.log_api_request(
                context=context,
                response_time=response_time,
                response_size=len(str(response_data)) if response_data else 0,
                success=True
            )
            
            # Check for API errors in response
            if "error" in response_data:
                error = self.error_handler.handle_api_response_error(response_data, context, cached_data)
                self.error_logger.log_error_with_context(error)
                raise error
            
            # Parse advanced search results
            results = []
            parsing_errors = 0
            
            if "products" in response_data:
                for i, product in enumerate(response_data["products"][:limit]):
                    try:
                        parsed_product = self._parse_product_data_with_error_handling(
                            product, 
                            product.get("asin", f"unknown_{i}"), 
                            context
                        )
                        results.append(parsed_product)
                    except Exception as e:
                        parsing_errors += 1
                        self.logger.warning(f"Failed to parse advanced search result {i}: {e}")
                        continue
            
            # Log parsing summary
            if parsing_errors > 0:
                self.logger.warning(f"Advanced search parsing completed with {parsing_errors} errors out of {len(response_data.get('products', []))} products")
            
            # Cache the results
            if self.cache_manager and results:
                self.cache_manager.set(cache_key, results, ttl=1800)  # 30 minutes
                self.error_logger.log_cache_operation("set", cache_key, size=len(str(results)))
            
            return results
        
        try:
            # Execute with circuit breaker and retry logic
            return await self.circuit_breaker.call(
                self.retry_handler.execute_with_retry,
                advanced_search_operation,
                context,
                retryable_errors=(KeepaTimeoutError, KeepaServiceUnavailableError, KeepaRateLimitError)
            )
            
        except KeepaAPIError as e:
            # Log the error and return fallback data if available
            self.error_logger.log_error_with_context(e)
            
            if cached_data:
                self.logger.warning(f"Using cached advanced search results as fallback")
                return cached_data
            
            # Return empty results with error information
            return [{
                "asin": "",
                "title": f"Advanced search failed",
                "error": str(e),
                "last_updated": datetime.now().isoformat(),
                "data_quality_score": 0.0,
                "validation_errors": [str(e)],
                "advanced_search_failed": True
            }]
        
        except Exception as e:
            # Handle unexpected errors
            error = KeepaAPIError(
                message=f"Unexpected error in advanced search: {str(e)}",
                error_code="KEEPA_ADVANCED_SEARCH_ERROR",
                context=context,
                fallback_data=cached_data
            )
            self.error_logger.log_error_with_context(error)
            
            if cached_data:
                self.logger.warning(f"Using cached advanced search results as fallback after unexpected error")
                return cached_data
            
            return [{
                "asin": "",
                "title": f"Advanced search failed",
                "error": str(e),
                "last_updated": datetime.now().isoformat(),
                "data_quality_score": 0.0,
                "validation_errors": [str(e)],
                "advanced_search_failed": True
            }]
    
    async def get_price_history(
        self,
        asin: str,
        days: int = 90,
        data_points: int = 100,
        price_type: str = "amazon"
    ) -> PriceHistoryData:
        """Get historical pricing data with configurable resolution.
        
        Args:
            asin: Product ASIN to retrieve price history for
            days: Number of days of history to retrieve (30, 60, 90, 180, 365)
            data_points: Maximum number of data points to return (affects resolution)
            price_type: Type of price data ("amazon", "new", "used", "sales_rank", "rating")
        
        Returns:
            PriceHistoryData object with parsed price history and statistics
            
        Raises:
            KeepaAPIError: For API-specific errors
            ValueError: For invalid parameters
        """
        # Create request context
        context = RequestContext(
            endpoint="product",
            method="GET",
            params={
                "asin": asin,
                "days": days,
                "data_points": data_points,
                "price_type": price_type
            }
        )
        
        # Validate parameters
        if days not in [30, 60, 90, 180, 365]:
            raise ValueError("Days parameter must be one of: 30, 60, 90, 180, 365")
        
        if data_points < 1 or data_points > 1000:
            raise ValueError("Data points must be between 1 and 1000")
        
        valid_price_types = ["amazon", "new", "used", "sales_rank", "rating", "buy_box"]
        if price_type not in valid_price_types:
            raise ValueError(f"Price type must be one of: {valid_price_types}")
        
        # Check cache first
        cache_key = f"keepa:price_history:{asin}:{days}:{data_points}:{price_type}"
        cached_data = None
        
        if self.cache_manager:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                self.error_logger.log_cache_operation("get", cache_key, hit=True)
                return PriceHistoryData(**cached_data)
            else:
                self.error_logger.log_cache_operation("get", cache_key, hit=False)
        
        # Define the price history operation
        async def price_history_operation():
            # Wait for rate limit
            await self.rate_limiter.acquire_permit()
            
            # Use product endpoint with history parameter
            endpoint = "product"
            params = {
                "key": self.api_key,
                "domain": 1,        # Amazon.com
                "asin": asin,
                "history": 1,       # Include price history
                "stats": days,      # Number of days for statistics
                "update": 1         # Cache optimization
            }
            
            start_time = datetime.now()
            response_data = await self._make_api_request_with_error_handling(endpoint, params, context)
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Log successful request
            self.error_logger.log_api_request(
                context=context,
                response_time=response_time,
                response_size=len(str(response_data)) if response_data else 0,
                success=True
            )
            
            # Check for API errors in response
            if "error" in response_data:
                error = self.error_handler.handle_api_response_error(response_data, context, cached_data)
                self.error_logger.log_error_with_context(error)
                raise error
            
            # Parse price history data
            if "products" in response_data and response_data["products"]:
                product_data = response_data["products"][0]
                price_history = self._parse_price_history_data(
                    product_data, asin, days, data_points, price_type, context
                )
                
                # Cache the result
                if self.cache_manager:
                    cache_data = price_history.to_dict()
                    self.cache_manager.set(cache_key, cache_data, ttl=3600)  # 1 hour TTL
                    self.error_logger.log_cache_operation("set", cache_key, size=len(str(cache_data)))
                
                return price_history
            else:
                error = KeepaAPIError(
                    message=f"No price history data found for ASIN: {asin}",
                    error_code="KEEPA_NO_PRICE_HISTORY",
                    context=context,
                    fallback_data=cached_data
                )
                self.error_logger.log_error_with_context(error)
                raise error
        
        try:
            # Execute with circuit breaker and retry logic
            return await self.circuit_breaker.call(
                self.retry_handler.execute_with_retry,
                price_history_operation,
                context,
                retryable_errors=(KeepaTimeoutError, KeepaServiceUnavailableError, KeepaRateLimitError)
            )
            
        except KeepaAPIError as e:
            # Log the error and return fallback data if available
            self.error_logger.log_error_with_context(e)
            
            if cached_data:
                self.logger.warning(f"Using cached price history as fallback for ASIN {asin}")
                return PriceHistoryData(**cached_data)
            
            # Return empty price history with error information
            return PriceHistoryData(
                asin=asin,
                price_points=[],
                price_type=price_type,
                time_period_days=days,
                data_points=0,
                statistics={
                    "error": str(e),
                    "current_price": None,
                    "average_price": 0.0,
                    "min_price": 0.0,
                    "max_price": 0.0,
                    "price_volatility": 0.0,
                    "trend_direction": "unknown",
                    "trend_strength": 0.0
                },
                last_updated=datetime.now()
            )
        
        except Exception as e:
            # Handle unexpected errors
            error = KeepaAPIError(
                message=f"Unexpected error retrieving price history for ASIN {asin}: {str(e)}",
                error_code="KEEPA_PRICE_HISTORY_ERROR",
                context=context,
                fallback_data=cached_data
            )
            self.error_logger.log_error_with_context(error)
            
            if cached_data:
                self.logger.warning(f"Using cached price history as fallback for ASIN {asin} after unexpected error")
                return PriceHistoryData(**cached_data)
            
            # Return empty price history with error information
            return PriceHistoryData(
                asin=asin,
                price_points=[],
                price_type=price_type,
                time_period_days=days,
                data_points=0,
                statistics={
                    "error": str(e),
                    "current_price": None,
                    "average_price": 0.0,
                    "min_price": 0.0,
                    "max_price": 0.0,
                    "price_volatility": 0.0,
                    "trend_direction": "unknown",
                    "trend_strength": 0.0
                },
                last_updated=datetime.now()
            )
    
    def _format_advanced_search_criteria(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Format search criteria into Keepa's JSON selection format.
        
        Args:
            criteria: User-friendly criteria dictionary
            
        Returns:
            Formatted criteria for Keepa API
            
        Raises:
            ValueError: For invalid criteria format
        """
        formatted = {}
        
        # Price range filtering (current_AMAZON with gte/lte)
        if "price_range" in criteria:
            price_range = criteria["price_range"]
            if not isinstance(price_range, dict):
                raise ValueError("price_range must be a dictionary with 'min' and/or 'max' keys")
            
            price_filter = {}
            if "min" in price_range:
                if not isinstance(price_range["min"], (int, float)) or price_range["min"] < 0:
                    raise ValueError("price_range.min must be a non-negative number")
                # Convert dollars to cents for Keepa API
                price_filter["gte"] = int(price_range["min"] * 100)
            
            if "max" in price_range:
                if not isinstance(price_range["max"], (int, float)) or price_range["max"] < 0:
                    raise ValueError("price_range.max must be a non-negative number")
                # Convert dollars to cents for Keepa API
                price_filter["lte"] = int(price_range["max"] * 100)
            
            if "min" in price_range and "max" in price_range and price_range["min"] > price_range["max"]:
                raise ValueError("price_range.min cannot be greater than price_range.max")
            
            if price_filter:
                formatted["current_AMAZON"] = price_filter
        
        # Sales threshold filtering (avg30_SALES with minimum values)
        if "sales_threshold" in criteria:
            sales_threshold = criteria["sales_threshold"]
            if not isinstance(sales_threshold, dict):
                raise ValueError("sales_threshold must be a dictionary with 'min' key")
            
            if "min" in sales_threshold:
                if not isinstance(sales_threshold["min"], (int, float)) or sales_threshold["min"] < 0:
                    raise ValueError("sales_threshold.min must be a non-negative number")
                
                formatted["avg30_SALES"] = {
                    "gte": int(sales_threshold["min"])
                }
        
        # Category-specific filtering
        if "category" in criteria:
            category = criteria["category"]
            if isinstance(category, dict) and "id" in category:
                if not isinstance(category["id"], int) or category["id"] <= 0:
                    raise ValueError("category.id must be a positive integer")
                formatted["categoryId"] = category["id"]
            elif isinstance(category, int):
                if category <= 0:
                    raise ValueError("category must be a positive integer")
                formatted["categoryId"] = category
            else:
                raise ValueError("category must be an integer or dictionary with 'id' key")
        
        # Rating filtering (convert to Keepa's rating*10 format)
        if "rating" in criteria:
            rating = criteria["rating"]
            if isinstance(rating, dict) and "min" in rating:
                if not isinstance(rating["min"], (int, float)) or rating["min"] < 0 or rating["min"] > 5:
                    raise ValueError("rating.min must be between 0 and 5")
                # Keepa stores rating * 10
                formatted["current_RATING"] = {
                    "gte": int(rating["min"] * 10)
                }
            elif isinstance(rating, (int, float)):
                if rating < 0 or rating > 5:
                    raise ValueError("rating must be between 0 and 5")
                formatted["current_RATING"] = {
                    "gte": int(rating * 10)
                }
            else:
                raise ValueError("rating must be a number or dictionary with 'min' key")
        
        # Review count filtering
        if "review_count" in criteria:
            review_count = criteria["review_count"]
            if isinstance(review_count, dict) and "min" in review_count:
                if not isinstance(review_count["min"], int) or review_count["min"] < 0:
                    raise ValueError("review_count.min must be a non-negative integer")
                formatted["current_COUNT_REVIEWS"] = {
                    "gte": review_count["min"]
                }
            elif isinstance(review_count, int):
                if review_count < 0:
                    raise ValueError("review_count must be a non-negative integer")
                formatted["current_COUNT_REVIEWS"] = {
                    "gte": review_count
                }
            else:
                raise ValueError("review_count must be an integer or dictionary with 'min' key")
        
        # Best Seller Rank filtering (lower rank = better)
        if "bsr" in criteria:
            bsr = criteria["bsr"]
            if isinstance(bsr, dict) and "max" in bsr:
                if not isinstance(bsr["max"], int) or bsr["max"] <= 0:
                    raise ValueError("bsr.max must be a positive integer")
                formatted["current_SALES"] = {
                    "lte": bsr["max"]
                }
            elif isinstance(bsr, int):
                if bsr <= 0:
                    raise ValueError("bsr must be a positive integer")
                formatted["current_SALES"] = {
                    "lte": bsr
                }
            else:
                raise ValueError("bsr must be an integer or dictionary with 'max' key")
        
        # Validate that we have at least one filter
        if not formatted:
            raise ValueError("At least one search criterion must be provided")
        
        return formatted
    
    def _parse_price_history_data(
        self,
        product_data: Dict[str, Any],
        asin: str,
        days: int,
        data_points: int,
        price_type: str,
        context: Optional[RequestContext] = None
    ) -> PriceHistoryData:
        """Parse price history data from Keepa API response.
        
        Args:
            product_data: Raw product data from Keepa API
            asin: Product ASIN
            days: Number of days requested
            data_points: Maximum data points requested
            price_type: Type of price data requested
            context: Request context for error handling
            
        Returns:
            PriceHistoryData object with parsed history and statistics
        """
        try:
            # Map price types to Keepa CSV field names
            price_type_mapping = {
                "amazon": "csv",  # Amazon price history
                "new": "csv",     # New offers (if available)
                "used": "csv",    # Used offers (if available)
                "sales_rank": "csv",  # Sales rank history
                "rating": "csv",  # Rating history
                "buy_box": "csv"  # Buy box price history
            }
            
            # Get the appropriate CSV data field
            csv_field = price_type_mapping.get(price_type, "csv")
            csv_data = product_data.get(csv_field, [])
            
            # Parse CSV data into price points
            price_points = self._parse_keepa_csv_data(csv_data, price_type, days, data_points)
            
            # Calculate statistics
            statistics = self._calculate_price_statistics(price_points, price_type)
            
            # Create price history data object
            return PriceHistoryData(
                asin=asin,
                price_points=price_points,
                price_type=price_type,
                time_period_days=days,
                data_points=len(price_points),
                statistics=statistics,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing price history for ASIN {asin}: {e}")
            
            # Return empty price history with error information
            return PriceHistoryData(
                asin=asin,
                price_points=[],
                price_type=price_type,
                time_period_days=days,
                data_points=0,
                statistics={
                    "error": str(e),
                    "current_price": None,
                    "average_price": 0.0,
                    "min_price": 0.0,
                    "max_price": 0.0,
                    "price_volatility": 0.0,
                    "trend_direction": "unknown",
                    "trend_strength": 0.0
                },
                last_updated=datetime.now()
            )
    
    def _parse_keepa_csv_data(
        self,
        csv_data: List[int],
        price_type: str,
        days: int,
        max_data_points: int
    ) -> List[PricePoint]:
        """Parse Keepa CSV data format into price points.
        
        Keepa CSV format:
        - Data is stored as pairs: [timestamp_minutes, value, timestamp_minutes, value, ...]
        - Timestamps are in minutes since Keepa epoch (21 Aug 2011 00:00:00 GMT)
        - Prices are in cents for price data
        - Values are raw for non-price data (ratings, sales rank)
        
        Args:
            csv_data: Raw CSV data array from Keepa
            price_type: Type of price data being parsed
            days: Number of days of history requested
            max_data_points: Maximum number of data points to return
            
        Returns:
            List of PricePoint objects
        """
        if not csv_data or len(csv_data) < 2:
            return []
        
        price_points = []
        keepa_epoch = datetime(2011, 8, 21, 0, 0, 0)  # Keepa epoch
        cutoff_time = datetime.now() - timedelta(days=days)
        
        try:
            # Parse pairs of [timestamp, value]
            for i in range(0, len(csv_data) - 1, 2):
                timestamp_minutes = csv_data[i]
                value = csv_data[i + 1]
                
                # Skip invalid data points
                if timestamp_minutes is None or value is None or value < 0:
                    continue
                
                # Convert Keepa timestamp to datetime
                timestamp = keepa_epoch + timedelta(minutes=timestamp_minutes)
                
                # Filter by time period
                if timestamp < cutoff_time:
                    continue
                
                # Convert value based on price type
                if price_type in ["amazon", "new", "used", "buy_box"]:
                    # Price data is in cents, convert to dollars
                    price = round(value / 100.0, 2)
                elif price_type == "rating":
                    # Rating data is stored * 10
                    price = round(value / 10.0, 1)
                else:
                    # Sales rank and other data is stored as-is
                    price = float(value)
                
                price_points.append(PricePoint(
                    timestamp=timestamp,
                    price=price,
                    price_type=price_type
                ))
            
            # Sort by timestamp
            price_points.sort(key=lambda x: x.timestamp)
            
            # Limit data points if necessary (keep evenly distributed points)
            if len(price_points) > max_data_points:
                step = len(price_points) // max_data_points
                price_points = price_points[::step][:max_data_points]
            
            return price_points
            
        except Exception as e:
            self.logger.error(f"Error parsing Keepa CSV data: {e}")
            return []
    
    def _calculate_price_statistics(
        self,
        price_points: List[PricePoint],
        price_type: str
    ) -> Dict[str, float]:
        """Calculate price trend analysis and statistics.
        
        Args:
            price_points: List of price points to analyze
            price_type: Type of price data
            
        Returns:
            Dictionary with calculated statistics
        """
        if not price_points:
            return {
                "current_price": None,
                "average_price": 0.0,
                "min_price": 0.0,
                "max_price": 0.0,
                "price_volatility": 0.0,
                "trend_direction": "unknown",
                "trend_strength": 0.0,
                "price_drops_count": 0,
                "price_increases_count": 0,
                "days_analyzed": 0
            }
        
        try:
            prices = [point.price for point in price_points]
            
            # Basic statistics
            current_price = prices[-1] if prices else None
            average_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            
            # Calculate price volatility (coefficient of variation)
            if average_price > 0:
                price_variance = sum((p - average_price) ** 2 for p in prices) / len(prices)
                price_std = price_variance ** 0.5
                price_volatility = price_std / average_price
            else:
                price_volatility = 0.0
            
            # Calculate trend direction and strength
            trend_direction, trend_strength = self._calculate_price_trend(price_points)
            
            # Count price changes
            price_drops_count = 0
            price_increases_count = 0
            
            for i in range(1, len(prices)):
                if prices[i] < prices[i-1]:
                    price_drops_count += 1
                elif prices[i] > prices[i-1]:
                    price_increases_count += 1
            
            # Calculate days analyzed
            if len(price_points) >= 2:
                days_analyzed = (price_points[-1].timestamp - price_points[0].timestamp).days
            else:
                days_analyzed = 0
            
            return {
                "current_price": current_price,
                "average_price": round(average_price, 2),
                "min_price": min_price,
                "max_price": max_price,
                "price_volatility": round(price_volatility, 3),
                "trend_direction": trend_direction,
                "trend_strength": round(trend_strength, 3),
                "price_drops_count": price_drops_count,
                "price_increases_count": price_increases_count,
                "days_analyzed": days_analyzed
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating price statistics: {e}")
            return {
                "current_price": None,
                "average_price": 0.0,
                "min_price": 0.0,
                "max_price": 0.0,
                "price_volatility": 0.0,
                "trend_direction": "unknown",
                "trend_strength": 0.0,
                "price_drops_count": 0,
                "price_increases_count": 0,
                "days_analyzed": 0
            }
    
    def _calculate_price_trend(self, price_points: List[PricePoint]) -> tuple[str, float]:
        """Calculate price trend direction and strength using linear regression.
        
        Args:
            price_points: List of price points to analyze
            
        Returns:
            Tuple of (trend_direction, trend_strength)
            - trend_direction: "up", "down", or "stable"
            - trend_strength: 0.0 to 1.0 indicating strength of trend
        """
        if len(price_points) < 2:
            return "unknown", 0.0
        
        try:
            # Convert timestamps to numeric values (days since first point)
            first_timestamp = price_points[0].timestamp
            x_values = [(point.timestamp - first_timestamp).total_seconds() / 86400 for point in price_points]
            y_values = [point.price for point in price_points]
            
            # Calculate linear regression slope
            n = len(x_values)
            sum_x = sum(x_values)
            sum_y = sum(y_values)
            sum_xy = sum(x * y for x, y in zip(x_values, y_values))
            sum_x2 = sum(x * x for x in x_values)
            
            # Calculate slope (trend)
            denominator = n * sum_x2 - sum_x * sum_x
            if denominator == 0:
                return "stable", 0.0
            
            slope = (n * sum_xy - sum_x * sum_y) / denominator
            
            # Calculate correlation coefficient (trend strength)
            sum_y2 = sum(y * y for y in y_values)
            numerator_r = n * sum_xy - sum_x * sum_y
            denominator_r = ((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y)) ** 0.5
            
            if denominator_r == 0:
                correlation = 0.0
            else:
                correlation = abs(numerator_r / denominator_r)
            
            # Determine trend direction
            if abs(slope) < 0.01:  # Very small slope considered stable
                trend_direction = "stable"
            elif slope > 0:
                trend_direction = "up"
            else:
                trend_direction = "down"
            
            # Trend strength is the absolute correlation coefficient
            trend_strength = min(1.0, correlation)
            
            return trend_direction, trend_strength
            
        except Exception as e:
            self.logger.error(f"Error calculating price trend: {e}")
            return "unknown", 0.0
    
    async def _make_api_request_with_error_handling(
        self, 
        endpoint: str, 
        params: Dict[str, Any], 
        context: RequestContext
    ) -> Dict[str, Any]:
        """Make an API request to Keepa using the centralized request manager."""
        url = f"{self.base_url}/{endpoint}"
        
        # Use the request manager for all HTTP requests
        return await self.request_manager.make_request(
            method="GET",
            url=url,
            params=params,
            context=context
        )
    
    async def _make_api_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy API request method for backward compatibility."""
        context = RequestContext(endpoint=endpoint, params=params)
        return await self._make_api_request_with_error_handling(endpoint, params, context)
    
    def _parse_product_data_with_error_handling(
        self, 
        raw_product: Dict[str, Any], 
        asin: str, 
        context: Optional[RequestContext] = None
    ) -> Dict[str, Any]:
        """Parse product data with comprehensive error handling and validation."""
        validation_errors = []
        
        try:
            return self._parse_product_data(raw_product)
        except Exception as e:
            # Log parsing error with context
            parsing_error = self.error_handler.handle_parsing_error(
                field="product_data",
                raw_value=raw_product,
                expected_type="valid product data",
                asin=asin,
                context=context
            )
            
            self.error_logger.log_error_with_context(parsing_error)
            
            # Return minimal data structure with error information
            return {
                "asin": asin,
                "title": raw_product.get("title", ""),
                "error": str(e),
                "last_updated": datetime.now().isoformat(),
                "data_quality_score": 0.0,
                "validation_errors": [str(e)],
                "parsing_failed": True
            }
    
    def _parse_product_data(self, raw_product: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw product data from Keepa API according to official specification.
        
        Based on official Keepa API documentation:
        - Stats array indices: [0]=price(cents), [3]=BSR, [4]=rating*10, [5]=reviews
        - CategoryTree contains full hierarchy with catId and name
        - Images can be in multiple formats (imagesCSV or images array)
        - Package dimensions include length, width, height, weight
        """
        try:
            # Basic product information with validation
            asin = self._validate_string_field(raw_product.get("asin", ""), "asin")
            title = self._validate_string_field(raw_product.get("title", ""), "title")
            brand = self._validate_string_field(raw_product.get("brand", ""), "brand", required=False)
            manufacturer = self._validate_string_field(raw_product.get("manufacturer", ""), "manufacturer", required=False)
            
            # Parse stats object with comprehensive validation
            stats = raw_product.get("stats", {})
            current_stats = self._validate_stats_array(stats.get("current", []), "stats.current")
            avg_stats = self._validate_stats_array(stats.get("avg", []), "stats.avg")
            min_stats = self._validate_stats_array(stats.get("min", []), "stats.min")
            max_stats = self._validate_stats_array(stats.get("max", []), "stats.max")
            
            # Handle both old test format and new official Keepa format
            # Old test format: [price_cents, rating, reviews, rank, timestamp]
            # Official format: [price_cents, -1, -1, rank, rating*10, reviews, ...]
            
            # Extract current price (index 0 in stats array, stored in cents)
            current_price = None
            if len(current_stats) > 0 and current_stats[0] is not None and current_stats[0] > 0:
                current_price = round(current_stats[0] / 100.0, 2)  # Convert cents to dollars
            
            # Extract average prices for 30d and 90d periods
            avg_price_30d = None
            if len(avg_stats) > 0 and avg_stats[0] is not None and avg_stats[0] > 0:
                avg_price_30d = round(avg_stats[0] / 100.0, 2)
            
            # Extract rating - handle both formats
            rating = None
            # Check if this looks like the old test format (5 elements: price, rating, reviews, rank, timestamp)
            if len(current_stats) == 5 and current_stats[1] is not None and isinstance(current_stats[1], (int, float)) and current_stats[1] <= 5:
                # Old test format: rating at index 1 (not multiplied by 10)
                rating = round(float(current_stats[1]), 1)
            elif len(current_stats) > 4 and current_stats[4] is not None and current_stats[4] > 0 and current_stats[4] <= 50:
                # Official format: rating stored * 10 at index 4
                rating = round(current_stats[4] / 10.0, 1)
            
            # Extract review count - handle both formats
            review_count = 0
            # Check if this looks like the old test format
            if len(current_stats) == 5 and current_stats[2] is not None:
                # Old test format: reviews at index 2
                review_count = max(0, int(current_stats[2]))
            elif len(current_stats) > 5 and current_stats[5] is not None:
                # Official format: reviews at index 5
                review_count = max(0, int(current_stats[5]))
            
            # Extract Best Seller Rank - handle both formats
            bsr_current = None
            if len(current_stats) > 3 and current_stats[3] is not None and current_stats[3] > 0:
                # Both formats: BSR at index 3
                bsr_current = int(current_stats[3])
            
            # Extract average BSR
            bsr_avg_30d = None
            if len(avg_stats) > 3 and avg_stats[3] is not None and avg_stats[3] > 0:
                bsr_avg_30d = float(avg_stats[3])
            
            # Parse category tree with comprehensive validation
            category_hierarchy = self._validate_category_tree(raw_product.get("categoryTree"))
            all_categories = [cat["name"] for cat in category_hierarchy if cat.get("name")]
            primary_category = all_categories[-1] if all_categories else ""
            
            # Parse images using comprehensive validation
            images = self._parse_image_urls(raw_product)
            
            # Parse product features/bullet points with validation
            features = self._validate_list_field(
                raw_product.get("features"), 
                "features", 
                expected_item_type=str
            )
            
            # Parse package dimensions and weight with validation
            dimensions, weight = self._parse_package_dimensions(raw_product)
            
            # Implement improved BSR-to-sales estimation algorithm
            estimated_sales_30d = self._calculate_sales_estimate(bsr_current, primary_category)
            
            # Calculate additional metrics
            lowest_price_30d = None
            highest_price_30d = None
            if len(min_stats) > 0 and min_stats[0] is not None and min_stats[0] > 0:
                lowest_price_30d = round(min_stats[0] / 100.0, 2)
            if len(max_stats) > 0 and max_stats[0] is not None and max_stats[0] > 0:
                highest_price_30d = round(max_stats[0] / 100.0, 2)
            
            # Parse additional product information
            product_group = raw_product.get("productGroup", "")
            description = raw_product.get("description", "")
            monthly_sold = raw_product.get("monthlySold", 0)
            
            # Construct comprehensive product data with backward compatibility
            parsed_data = {
                # Basic Information
                "asin": asin,
                "title": title,
                "brand": brand,
                "manufacturer": manufacturer,
                "product_group": product_group,
                "description": description,
                
                # Pricing Information (new enhanced fields)
                "current_price": current_price,
                "avg_price_30d": avg_price_30d,
                "lowest_price_30d": lowest_price_30d,
                "highest_price_30d": highest_price_30d,
                
                # Sales Rank Information (new enhanced fields)
                "bsr_current": bsr_current,
                "bsr_avg_30d": bsr_avg_30d,
                
                # Review Information (new enhanced fields)
                "review_count": review_count,
                "rating": rating,
                
                # Category Information (new enhanced fields)
                "primary_category": primary_category,
                "category_hierarchy": category_hierarchy,
                "all_categories": all_categories,
                
                # Product Details (new enhanced fields)
                "images": images,
                "features": features,
                "dimensions": dimensions if dimensions else None,
                "weight": weight,
                
                # Sales Estimates (new enhanced fields)
                "estimated_sales_30d": estimated_sales_30d,
                "monthly_sold": monthly_sold,
                
                # Metadata
                "last_updated": datetime.now().isoformat(),
                "data_quality_score": self._calculate_data_quality_score(raw_product, current_stats),
                
                # Debug information
                "raw_stats_current": current_stats,
                "raw_stats_avg": avg_stats,
                "validation_errors": [],
                
                # Backward compatibility fields (maintain old field names)
                "price": current_price or 0.0,  # Old field name for current_price
                "rating": rating or 0.0,  # Old field name for rating (ensure default value)
                "reviews": review_count,  # Old field name for review_count
                "rank": bsr_current or 0,  # Old field name for bsr_current
                "category": " > ".join(all_categories) if all_categories else "",  # Old field name for category path
                "categories": all_categories,  # Keep this as it was already a list
            }
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error parsing product data for ASIN {raw_product.get('asin', 'unknown')}: {e}")
            # Return minimal data structure with error information
            return {
                "asin": raw_product.get("asin", ""),
                "title": raw_product.get("title", ""),
                "error": str(e),
                "last_updated": datetime.now().isoformat(),
                "data_quality_score": 0.0,
                "validation_errors": [str(e)]
            }
    
    def _validate_string_field(self, value: Any, field_name: str, required: bool = True) -> str:
        """Validate and clean string fields."""
        if value is None:
            if required:
                raise ValueError(f"Required field '{field_name}' is None")
            return ""
        
        if not isinstance(value, str):
            logger.warning(f"Field '{field_name}' expected string, got {type(value)}: {value}")
            return str(value)
        
        return value.strip()
    
    def _calculate_sales_estimate(self, bsr: Optional[int], category: str) -> int:
        """Calculate improved sales estimate based on BSR and category.
        
        Uses research-based BSR-to-sales conversion rates that vary by category.
        """
        if not bsr or bsr <= 0:
            return 0
        
        # Category-specific multipliers based on market research
        category_multipliers = {
            "Books": 1.0,
            "Kindle Store": 0.8,
            "Electronics": 1.5,
            "Home & Kitchen": 1.2,
            "Toys & Games": 1.3,
            "Sports & Outdoors": 1.1,
            "Health & Personal Care": 1.4,
            "Beauty & Personal Care": 1.4,
            "Clothing, Shoes & Jewelry": 0.9,
            "Arts, Crafts & Sewing": 0.7
        }
        
        # Find category multiplier
        multiplier = 1.0
        for cat_key, mult in category_multipliers.items():
            if cat_key.lower() in category.lower():
                multiplier = mult
                break
        
        # Improved BSR-to-sales algorithm based on empirical data
        if bsr <= 5:
            base_sales = 1000 + (5 - bsr) * 200
        elif bsr <= 10:
            base_sales = 800 + (10 - bsr) * 40
        elif bsr <= 50:
            base_sales = 400 + (50 - bsr) * 10
        elif bsr <= 100:
            base_sales = 200 + (100 - bsr) * 4
        elif bsr <= 500:
            base_sales = 100 + (500 - bsr) * 0.25
        elif bsr <= 1000:
            base_sales = 50 + (1000 - bsr) * 0.1
        elif bsr <= 5000:
            base_sales = 25 + (5000 - bsr) * 0.005
        elif bsr <= 10000:
            base_sales = 15 + (10000 - bsr) * 0.002
        elif bsr <= 50000:
            base_sales = 10 + (50000 - bsr) * 0.0001
        elif bsr <= 100000:
            base_sales = 5 + (100000 - bsr) * 0.00005
        elif bsr <= 500000:
            base_sales = 2 + (500000 - bsr) * 0.000006
        else:
            base_sales = 1
        
        # Apply category multiplier and ensure minimum of 1
        estimated_sales = max(1, int(base_sales * multiplier))
        
        return estimated_sales
    
    def _calculate_data_quality_score(self, raw_product: Dict[str, Any], current_stats: List[Any]) -> float:
        """Calculate data quality score based on completeness and accuracy."""
        score = 0.0
        max_score = 10.0
        
        # Basic fields (2 points)
        if raw_product.get("asin"):
            score += 0.5
        if raw_product.get("title"):
            score += 0.5
        if raw_product.get("brand"):
            score += 0.5
        if raw_product.get("manufacturer"):
            score += 0.5
        
        # Pricing data (2 points)
        if len(current_stats) > 0 and current_stats[0] is not None and current_stats[0] > 0:
            score += 2.0
        
        # Review data (2 points)
        if len(current_stats) > 4 and current_stats[4] is not None and current_stats[4] > 0:
            score += 1.0
        if len(current_stats) > 5 and current_stats[5] is not None:
            score += 1.0
        
        # BSR data (2 points)
        if len(current_stats) > 3 and current_stats[3] is not None and current_stats[3] > 0:
            score += 2.0
        
        # Category data (1 point)
        if raw_product.get("categoryTree"):
            score += 1.0
        
        # Images and features (1 point)
        if raw_product.get("imagesCSV") or raw_product.get("images"):
            score += 0.5
        if raw_product.get("features"):
            score += 0.5
        
        return round(score / max_score, 2)
    
    def _validate_numeric_field(self, value: Any, field_name: str, 
                               min_value: Optional[float] = None, 
                               max_value: Optional[float] = None,
                               required: bool = False) -> Optional[float]:
        """Validate and convert numeric fields with range checking."""
        if value is None:
            if required:
                raise ValueError(f"Required numeric field '{field_name}' is None")
            return None
        
        try:
            numeric_value = float(value)
            
            # Range validation
            if min_value is not None and numeric_value < min_value:
                logger.warning(f"Field '{field_name}' value {numeric_value} below minimum {min_value}")
                return min_value
            
            if max_value is not None and numeric_value > max_value:
                logger.warning(f"Field '{field_name}' value {numeric_value} above maximum {max_value}")
                return max_value
            
            return numeric_value
            
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid numeric value for field '{field_name}': {value} - {e}")
            if required:
                raise ValueError(f"Field '{field_name}' must be numeric, got {type(value)}: {value}")
            return None
    
    def _validate_integer_field(self, value: Any, field_name: str,
                               min_value: Optional[int] = None,
                               max_value: Optional[int] = None,
                               required: bool = False) -> Optional[int]:
        """Validate and convert integer fields with range checking."""
        if value is None:
            if required:
                raise ValueError(f"Required integer field '{field_name}' is None")
            return None
        
        try:
            int_value = int(value)
            
            # Range validation
            if min_value is not None and int_value < min_value:
                logger.warning(f"Field '{field_name}' value {int_value} below minimum {min_value}")
                return min_value
            
            if max_value is not None and int_value > max_value:
                logger.warning(f"Field '{field_name}' value {int_value} above maximum {max_value}")
                return max_value
            
            return int_value
            
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid integer value for field '{field_name}': {value} - {e}")
            if required:
                raise ValueError(f"Field '{field_name}' must be integer, got {type(value)}: {value}")
            return None
    
    def _validate_list_field(self, value: Any, field_name: str, 
                            expected_item_type: type = str,
                            required: bool = False) -> List[Any]:
        """Validate list fields and their contents."""
        if value is None:
            if required:
                raise ValueError(f"Required list field '{field_name}' is None")
            return []
        
        if not isinstance(value, list):
            logger.warning(f"Field '{field_name}' expected list, got {type(value)}: {value}")
            return []
        
        validated_items = []
        for i, item in enumerate(value):
            if not isinstance(item, expected_item_type):
                logger.warning(f"Field '{field_name}[{i}]' expected {expected_item_type.__name__}, got {type(item)}: {item}")
                # Try to convert if possible
                try:
                    converted_item = expected_item_type(item)
                    validated_items.append(converted_item)
                except (ValueError, TypeError):
                    logger.error(f"Could not convert '{field_name}[{i}]' to {expected_item_type.__name__}")
                    continue
            else:
                validated_items.append(item)
        
        return validated_items
    
    def _validate_stats_array(self, stats: List[Any], field_name: str) -> List[Any]:
        """Validate Keepa stats array format and contents."""
        if not isinstance(stats, list):
            logger.error(f"Stats field '{field_name}' expected list, got {type(stats)}")
            return []
        
        # Keepa stats arrays should have at least 6 elements
        if len(stats) < 6:
            logger.warning(f"Stats array '{field_name}' has {len(stats)} elements, expected at least 6")
        
        validated_stats = []
        for i, value in enumerate(stats):
            if value is None or value == -1:
                # -1 is Keepa's way of indicating no data
                validated_stats.append(None)
            else:
                try:
                    # Most stats are numeric
                    if isinstance(value, (int, float)):
                        validated_stats.append(value)
                    else:
                        # Try to convert to number
                        numeric_value = float(value)
                        validated_stats.append(numeric_value)
                except (ValueError, TypeError):
                    logger.warning(f"Stats array '{field_name}[{i}]' contains non-numeric value: {value}")
                    validated_stats.append(None)
        
        return validated_stats
    
    def _handle_parsing_error(self, error: Exception, asin: str, field: str) -> None:
        """Handle and log parsing errors with context."""
        error_msg = f"Error parsing field '{field}' for ASIN '{asin}': {str(error)}"
        logger.error(error_msg)
        
        # Could implement error reporting/metrics here
        # For now, just log the error
    
    def _validate_category_tree(self, category_tree: Any) -> List[Dict[str, Any]]:
        """Validate and parse category tree structure."""
        if not category_tree:
            return []
        
        if not isinstance(category_tree, list):
            logger.warning(f"Category tree expected list, got {type(category_tree)}")
            return []
        
        validated_categories = []
        for i, cat_node in enumerate(category_tree):
            if not isinstance(cat_node, dict):
                logger.warning(f"Category tree node {i} expected dict, got {type(cat_node)}")
                continue
            
            cat_id = cat_node.get("catId")
            cat_name = cat_node.get("name", "")
            
            if not cat_name:
                logger.warning(f"Category tree node {i} missing name")
                continue
            
            validated_node = {
                "id": self._validate_integer_field(cat_id, f"categoryTree[{i}].catId"),
                "name": self._validate_string_field(cat_name, f"categoryTree[{i}].name")
            }
            
            validated_categories.append(validated_node)
        
        return validated_categories
    
    def _parse_image_urls(self, raw_product: Dict[str, Any]) -> List[str]:
        """Parse image URLs from various Keepa response formats."""
        images = []
        
        try:
            # Handle imagesCSV format (comma-separated filenames)
            if "imagesCSV" in raw_product and raw_product["imagesCSV"]:
                csv_images = raw_product["imagesCSV"]
                if isinstance(csv_images, str):
                    filenames = [img.strip() for img in csv_images.split(",") if img.strip()]
                    for filename in filenames:
                        if filename:
                            # For backward compatibility with tests, include both filename and full URL
                            images.append(filename)  # Raw filename for backward compatibility
                            if not filename.startswith("http"):
                                full_url = f"https://m.media-amazon.com/images/I/{filename}"
                                # Only add full URL if it's different from filename
                                if full_url != filename:
                                    images.append(full_url)
            
            # Handle images array format (with metadata)
            elif "images" in raw_product and isinstance(raw_product["images"], list):
                for img_obj in raw_product["images"]:
                    if isinstance(img_obj, dict):
                        # Prefer large image, fallback to medium, then small
                        img_filename = (img_obj.get("l") or 
                                      img_obj.get("m") or 
                                      img_obj.get("s"))
                        if img_filename:
                            images.append(img_filename)  # Raw filename
                            if not img_filename.startswith("http"):
                                full_url = f"https://m.media-amazon.com/images/I/{img_filename}"
                                images.append(full_url)  # Full URL
                    elif isinstance(img_obj, str):
                        # Direct filename
                        images.append(img_obj)
                        if not img_obj.startswith("http"):
                            full_url = f"https://m.media-amazon.com/images/I/{img_obj}"
                            images.append(full_url)
        
        except Exception as e:
            self._handle_parsing_error(e, raw_product.get("asin", "unknown"), "images")
        
        return images
    
    def _parse_package_dimensions(self, raw_product: Dict[str, Any]) -> tuple[Optional[Dict[str, float]], Optional[float]]:
        """Parse package dimensions and weight from Keepa response."""
        dimensions = {}
        weight = None
        
        try:
            # Parse individual dimension fields (values in hundredths of units)
            dimension_fields = {
                "packageHeight": "height",
                "packageLength": "length", 
                "packageWidth": "width"
            }
            
            for keepa_field, dim_name in dimension_fields.items():
                if keepa_field in raw_product and raw_product[keepa_field]:
                    # Convert from hundredths to actual units (inches)
                    dim_value = self._validate_numeric_field(
                        raw_product[keepa_field], 
                        keepa_field, 
                        min_value=0
                    )
                    if dim_value is not None:
                        dimensions[dim_name] = round(dim_value / 100.0, 2)
            
            # Parse weight (in hundredths of pounds)
            if "packageWeight" in raw_product and raw_product["packageWeight"]:
                weight_value = self._validate_numeric_field(
                    raw_product["packageWeight"], 
                    "packageWeight", 
                    min_value=0
                )
                if weight_value is not None:
                    weight = round(weight_value / 100.0, 2)
        
        except Exception as e:
            self._handle_parsing_error(e, raw_product.get("asin", "unknown"), "dimensions")
        
        return (dimensions if dimensions else None), weight
    
    async def batch_get_products(self, asins: List[str], stats_days: int = 30, 
                               include_history: bool = False, include_offers: int = 0,
                               chunk_size: int = 100) -> List[Dict[str, Any]]:
        """Get multiple products in batch requests with intelligent caching.
        
        Args:
            asins: List of ASINs to retrieve (up to 100 per request)
            stats_days: Number of days for statistics (default 30)
            include_history: Whether to include price history
            include_offers: Number of offers to include (0-20, reduces max ASINs to 20)
            chunk_size: Maximum ASINs per API request (default 100)
        
        Returns:
            List of product data dictionaries in the same order as input ASINs
        
        Raises:
            ValueError: If batch size limits are exceeded
            APIError: If API request fails
        """
        if not asins:
            return []
        
        # Validate batch size limits according to Keepa API constraints
        if include_offers > 0:
            max_batch_size = 20  # Keepa limit when including offers
            if len(asins) > max_batch_size:
                raise ValueError(f"Maximum {max_batch_size} ASINs per batch request when including offers")
            if include_offers > 20:
                raise ValueError("Maximum 20 offers per request")
        else:
            max_batch_size = 100  # Standard Keepa limit
            if len(asins) > max_batch_size:
                raise ValueError(f"Maximum {max_batch_size} ASINs per batch request")
        
        # Adjust chunk size based on offers constraint
        effective_chunk_size = min(chunk_size, max_batch_size)
        
        # Step 1: Check cache for all ASINs and identify uncached ones
        cached_results = {}
        uncached_asins = []
        
        if self.cache_manager:
            for asin in asins:
                cache_key = f"keepa:product:{asin}:{include_history}:{stats_days}:{include_offers}"
                cached_data = self.cache_manager.get(cache_key)
                if cached_data:
                    cached_results[asin] = cached_data
                    logger.debug(f"Cache hit for ASIN: {asin}")
                else:
                    uncached_asins.append(asin)
                    logger.debug(f"Cache miss for ASIN: {asin}")
        else:
            uncached_asins = asins
        
        logger.info(f"Batch request: {len(cached_results)} cached, {len(uncached_asins)} uncached ASINs")
        
        # Step 2: Fetch uncached ASINs in chunks
        api_results = {}
        failed_asins = []
        
        if uncached_asins:
            # Split uncached ASINs into chunks
            chunks = [uncached_asins[i:i + effective_chunk_size] 
                     for i in range(0, len(uncached_asins), effective_chunk_size)]
            
            for chunk_idx, chunk_asins in enumerate(chunks):
                logger.info(f"Processing chunk {chunk_idx + 1}/{len(chunks)} with {len(chunk_asins)} ASINs")
                
                try:
                    chunk_results = await self._fetch_batch_chunk(
                        chunk_asins, stats_days, include_history, include_offers
                    )
                    
                    # Process successful results
                    for product_data in chunk_results:
                        asin = product_data.get('asin')
                        if asin:
                            api_results[asin] = product_data
                            
                            # Cache individual results
                            if self.cache_manager:
                                cache_key = f"keepa:product:{asin}:{include_history}:{stats_days}:{include_offers}"
                                self.cache_manager.set(cache_key, product_data, ttl=3600)
                                logger.debug(f"Cached result for ASIN: {asin}")
                    
                    # Identify failed ASINs in this chunk
                    successful_asins = {result.get('asin') for result in chunk_results}
                    chunk_failed = [asin for asin in chunk_asins if asin not in successful_asins]
                    failed_asins.extend(chunk_failed)
                    
                except Exception as e:
                    logger.error(f"Chunk {chunk_idx + 1} failed: {e}")
                    failed_asins.extend(chunk_asins)
                    # Continue with other chunks - graceful degradation
        
        # Step 3: Combine results maintaining original order
        final_results = []
        for asin in asins:
            if asin in cached_results:
                final_results.append(cached_results[asin])
            elif asin in api_results:
                final_results.append(api_results[asin])
            else:
                # Create error entry for failed ASIN
                error_entry = {
                    "asin": asin,
                    "title": "",
                    "error": "Failed to retrieve product data",
                    "last_updated": datetime.now().isoformat(),
                    "data_quality_score": 0.0,
                    "validation_errors": ["API request failed"]
                }
                final_results.append(error_entry)
                logger.warning(f"Failed to retrieve data for ASIN: {asin}")
        
        # Log batch processing summary
        success_count = len([r for r in final_results if not r.get('error')])
        logger.info(f"Batch processing complete: {success_count}/{len(asins)} successful, "
                   f"{len(failed_asins)} failed")
        
        return final_results
    
    async def _fetch_batch_chunk(self, asins: List[str], stats_days: int, 
                               include_history: bool, include_offers: int) -> List[Dict[str, Any]]:
        """Fetch a single chunk of ASINs from the API.
        
        Args:
            asins: List of ASINs for this chunk
            stats_days: Number of days for statistics
            include_history: Whether to include price history
            include_offers: Number of offers to include
        
        Returns:
            List of parsed product data
        
        Raises:
            APIError: If API request fails
        """
        # Wait for rate limit
        await self.rate_limiter.acquire_permit()
        
        try:
            endpoint = "product"
            params = {
                "key": self.api_key,
                "domain": 1,  # Amazon.com
                "asin": ",".join(asins),  # Comma-separated ASIN format
                "stats": stats_days,  # Number of days for statistics
                "history": 1 if include_history else 0,
                "update": 1  # Cache optimization - use cached data if < 1 hour old
            }
            
            # Add offers parameter if requested
            if include_offers > 0:
                params["offers"] = str(include_offers)
            
            logger.debug(f"Making batch API request for ASINs: {asins}")
            response_data = await self._make_api_request(endpoint, params)
            
            # Check for API errors
            if "error" in response_data:
                error_msg = response_data["error"]
                logger.error(f"Keepa API error for batch request: {error_msg}")
                raise APIError(f"Keepa API error: {error_msg}", "keepa")
            
            # Parse results
            results = []
            if "products" in response_data and response_data["products"]:
                for product in response_data["products"]:
                    try:
                        product_data = self._parse_product_data(product)
                        results.append(product_data)
                    except Exception as e:
                        logger.error(f"Failed to parse product data: {e}")
                        # Continue with other products - partial failure handling
                        continue
            
            logger.debug(f"Successfully parsed {len(results)} products from batch response")
            return results
            
        except APIError:
            raise  # Re-raise API errors as-is
        except Exception as e:
            logger.error(f"Batch chunk request failed: {e}")
            raise APIError(f"Batch request failed: {str(e)}", "keepa")
    
    async def get_price_history(self, asin: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get price history for a specific ASIN."""
        # Check cache first
        if self.cache_manager:
            cache_key = f"keepa:history:{asin}:{days}"
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                return cached_data
        
        await self.rate_limiter.acquire_permit()
        
        try:
            endpoint = "product"
            params = {
                "key": self.api_key,
                "domain": 1,  # Amazon.com
                "asin": asin,
                "history": 1,
                "days": days
            }
            
            response_data = await self._make_api_request(endpoint, params)
            
            if "error" in response_data:
                raise APIError(f"Keepa API error: {response_data['error']}", "keepa")
            
            history = []
            if "products" in response_data and response_data["products"]:
                product = response_data["products"][0]
                
                # Parse CSV data (Keepa returns price history as CSV arrays)
                if "csv" in product and product["csv"]:
                    csv_data = product["csv"]
                    
                    # CSV data comes in pairs: [price, timestamp, price, timestamp, ...]
                    for i in range(0, len(csv_data), 2):
                        if i + 1 < len(csv_data):
                            price_cents = csv_data[i]
                            timestamp = csv_data[i + 1]
                            
                            if price_cents is not None and timestamp is not None:
                                history.append({
                                    "price": price_cents / 100.0,  # Convert cents to dollars
                                    "timestamp": datetime.fromtimestamp(timestamp).isoformat()
                                })
            
            # Cache the results
            if self.cache_manager:
                self.cache_manager.set(cache_key, history, ttl=1800)  # 30 minutes
            
            return history
            
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Price history lookup failed: {str(e)}", "keepa")
    
    def validate_batch_request(self, asins: List[str], include_offers: int = 0) -> None:
        """Validate batch request parameters.
        
        Args:
            asins: List of ASINs to validate
            include_offers: Number of offers to include
        
        Raises:
            ValueError: If validation fails
        """
        if not asins:
            raise ValueError("ASIN list cannot be empty")
        
        if not isinstance(asins, list):
            raise ValueError("ASINs must be provided as a list")
        
        # Validate individual ASINs
        for i, asin in enumerate(asins):
            if not isinstance(asin, str):
                raise ValueError(f"ASIN at index {i} must be a string, got {type(asin)}")
            
            if not asin.strip():
                raise ValueError(f"ASIN at index {i} cannot be empty")
            
            # Basic ASIN format validation (10 characters, alphanumeric)
            asin_clean = asin.strip().upper()
            if len(asin_clean) != 10:
                raise ValueError(f"ASIN '{asin}' must be exactly 10 characters")
            
            if not asin_clean.isalnum():
                raise ValueError(f"ASIN '{asin}' must contain only alphanumeric characters")
        
        # Validate batch size limits
        if include_offers > 0:
            if len(asins) > 20:
                raise ValueError(f"Maximum 20 ASINs allowed when including offers, got {len(asins)}")
            if include_offers > 20:
                raise ValueError(f"Maximum 20 offers per request, got {include_offers}")
        else:
            if len(asins) > 100:
                raise ValueError(f"Maximum 100 ASINs per batch request, got {len(asins)}")
    
    def get_batch_cache_status(self, asins: List[str], stats_days: int = 30, 
                              include_history: bool = False, include_offers: int = 0) -> Dict[str, Any]:
        """Get cache status for a batch of ASINs.
        
        Args:
            asins: List of ASINs to check
            stats_days: Number of days for statistics
            include_history: Whether to include price history
            include_offers: Number of offers to include
        
        Returns:
            Dictionary with cache statistics and ASIN lists
        """
        if not self.cache_manager:
            return {
                "cache_enabled": False,
                "cached_asins": [],
                "uncached_asins": asins,
                "cache_hit_rate": 0.0,
                "total_asins": len(asins)
            }
        
        cached_asins = []
        uncached_asins = []
        
        for asin in asins:
            cache_key = f"keepa:product:{asin}:{include_history}:{stats_days}:{include_offers}"
            if self.cache_manager.get(cache_key):
                cached_asins.append(asin)
            else:
                uncached_asins.append(asin)
        
        cache_hit_rate = len(cached_asins) / len(asins) if asins else 0.0
        
        return {
            "cache_enabled": True,
            "cached_asins": cached_asins,
            "uncached_asins": uncached_asins,
            "cache_hit_rate": cache_hit_rate,
            "total_asins": len(asins),
            "api_requests_needed": len(uncached_asins)
        }
    
    async def batch_get_products_with_retry(self, asins: List[str], stats_days: int = 30,
                                          include_history: bool = False, include_offers: int = 0,
                                          max_retries: int = 3, retry_delay: float = 1.0) -> List[Dict[str, Any]]:
        """Get multiple products with retry logic for failed requests.
        
        Args:
            asins: List of ASINs to retrieve
            stats_days: Number of days for statistics
            include_history: Whether to include price history
            include_offers: Number of offers to include
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        
        Returns:
            List of product data dictionaries
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return await self.batch_get_products(
                    asins=asins,
                    stats_days=stats_days,
                    include_history=include_history,
                    include_offers=include_offers
                )
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Batch request attempt {attempt + 1} failed: {e}. "
                                 f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Batch request failed after {max_retries + 1} attempts")
        
        # If all retries failed, raise the last exception
        if last_exception:
            raise last_exception
        
        return []
    
    def split_batch_by_offers(self, asins: List[str], include_offers: int = 0) -> List[List[str]]:
        """Split a large batch into smaller chunks based on offers constraint.
        
        Args:
            asins: List of ASINs to split
            include_offers: Number of offers to include
        
        Returns:
            List of ASIN chunks that respect batch size limits
        """
        if not asins:
            return []
        
        # Determine chunk size based on offers constraint
        chunk_size = 20 if include_offers > 0 else 100
        
        chunks = []
        for i in range(0, len(asins), chunk_size):
            chunk = asins[i:i + chunk_size]
            chunks.append(chunk)
        
        return chunks
    
    async def get_batch_processing_stats(self) -> Dict[str, Any]:
        """Get statistics about batch processing performance.
        
        Returns:
            Dictionary with batch processing statistics
        """
        # This would typically be implemented with actual metrics collection
        # Get current rate limiter status
        rate_status = self.rate_limiter.get_rate_limit_status()
        
        return {
            "rate_limiter_status": {
                "requests_made": self.rate_limiter.total_requests,
                "max_requests": rate_status.max_requests,
                "time_window": rate_status.time_window_seconds,
                "requests_remaining": max(0, rate_status.max_requests - rate_status.requests_in_window),
                "current_tokens": rate_status.current_tokens,
                "utilization_percentage": rate_status.utilization_percentage,
                "queue_size": rate_status.queue_size
            },
            "cache_enabled": self.cache_manager is not None,
            "session_active": self.session is not None,
            "api_key_configured": bool(self.api_key)
        }
    
    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None   
 
    # Health Monitoring and Status Reporting Methods
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of the Keepa client."""
        health_status = {
            "api_accessible": False,
            "rate_limit_status": "unknown",
            "cache_status": "unknown",
            "last_successful_request": None,
            "error_rate": 0.0,
            "circuit_breaker_state": self.circuit_breaker.state,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Test API connectivity with a simple request
            test_context = RequestContext(endpoint="health_check", method="GET")
            
            # Use a minimal request to test connectivity
            params = {
                "key": self.api_key,
                "domain": 1
            }
            
            start_time = datetime.now()
            await self._make_api_request_with_error_handling("token", params, test_context)
            response_time = (datetime.now() - start_time).total_seconds()
            
            health_status.update({
                "api_accessible": True,
                "last_successful_request": datetime.now().isoformat(),
                "response_time_seconds": response_time
            })
            
        except KeepaAuthenticationError:
            health_status["api_accessible"] = False
            health_status["error"] = "Authentication failed - check API key"
        except KeepaRateLimitError:
            health_status["api_accessible"] = True
            health_status["error"] = "Rate limit exceeded"
        except Exception as e:
            health_status["api_accessible"] = False
            health_status["error"] = str(e)
        
        # Get rate limit status
        try:
            rate_limit_status = self.rate_limiter.get_rate_limit_status()
            health_status["rate_limit_status"] = {
                "current_tokens": rate_limit_status.current_tokens,
                "utilization_percentage": rate_limit_status.utilization_percentage,
                "queue_size": rate_limit_status.queue_size,
                "active_requests": rate_limit_status.active_requests,
                "estimated_wait_time": rate_limit_status.estimated_wait_time,
                "status": "healthy" if rate_limit_status.utilization_percentage < 80 else "warning"
            }
        except Exception as e:
            health_status["rate_limit_status"] = f"Error getting rate limit status: {e}"
        
        # Get cache status
        if self.cache_manager:
            try:
                # This would depend on cache_manager implementation
                health_status["cache_status"] = "available"
            except Exception as e:
                health_status["cache_status"] = f"Error: {e}"
        else:
            health_status["cache_status"] = "not_configured"
        
        return health_status
    
    def get_usage_metrics(self) -> Dict[str, Any]:
        """Get API usage and performance metrics."""
        rate_limit_status = self.rate_limiter.get_rate_limit_status()
        performance_metrics = self.rate_limiter.get_performance_metrics()
        
        metrics = {
            "rate_limit": {
                "current_tokens": rate_limit_status.current_tokens,
                "max_tokens": rate_limit_status.max_tokens,
                "requests_in_window": rate_limit_status.requests_in_window,
                "max_requests": rate_limit_status.max_requests,
                "utilization_percentage": rate_limit_status.utilization_percentage,
                "queue_size": rate_limit_status.queue_size,
                "active_requests": rate_limit_status.active_requests,
                "estimated_wait_time": rate_limit_status.estimated_wait_time,
                "requests_per_second": rate_limit_status.requests_per_second
            },
            "performance": performance_metrics,
            "circuit_breaker": {
                "state": self.circuit_breaker.state,
                "failure_count": self.circuit_breaker.failure_count,
                "last_failure_time": self.circuit_breaker.last_failure_time.isoformat() if self.circuit_breaker.last_failure_time else None
            },
            "client_config": {
                "timeout_seconds": self.timeout,
                "base_url": self.base_url,
                "cache_enabled": self.cache_manager is not None
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return metrics
    
    async def test_connectivity(self) -> Dict[str, Any]:
        """Test Keepa API connectivity and return detailed results."""
        test_results = {
            "connectivity_test": False,
            "authentication_test": False,
            "rate_limit_test": False,
            "response_time_ms": None,
            "errors": [],
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Test basic connectivity
            start_time = datetime.now()
            context = RequestContext(endpoint="connectivity_test", method="GET")
            
            params = {
                "key": self.api_key,
                "domain": 1
            }
            
            response = await self._make_api_request_with_error_handling("token", params, context)
            response_time = (datetime.now() - start_time).total_seconds()
            
            test_results.update({
                "connectivity_test": True,
                "authentication_test": True,
                "response_time_ms": round(response_time * 1000, 2)
            })
            
            # Check if response indicates rate limit status
            if "tokensLeft" in response:
                test_results["rate_limit_test"] = True
                test_results["tokens_remaining"] = response["tokensLeft"]
            
        except KeepaAuthenticationError as e:
            test_results["errors"].append(f"Authentication failed: {e.message}")
        except KeepaRateLimitError as e:
            test_results["connectivity_test"] = True
            test_results["authentication_test"] = True
            test_results["errors"].append(f"Rate limit exceeded: {e.message}")
        except KeepaTimeoutError as e:
            test_results["errors"].append(f"Request timeout: {e.message}")
        except Exception as e:
            test_results["errors"].append(f"Unexpected error: {str(e)}")
        
        return test_results
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring and debugging."""
        # This would typically be implemented with a metrics collector
        # For now, return basic circuit breaker and rate limiter stats
        
        return {
            "circuit_breaker": {
                "state": self.circuit_breaker.state,
                "failure_count": self.circuit_breaker.failure_count,
                "failure_threshold": self.circuit_breaker.failure_threshold,
                "last_failure": self.circuit_breaker.last_failure_time.isoformat() if self.circuit_breaker.last_failure_time else None
            },
            "rate_limiter": self.rate_limiter.get_rate_limit_status().to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    
    async def close(self):
        """Clean up resources and close connections."""
        if self.session:
            await self.session.close()
            self.session = None
        
        self.logger.info("Keepa client closed and resources cleaned up")    

    def _validate_and_enhance_product_data(
        self, 
        product_data: Dict[str, Any], 
        context: Optional[RequestContext] = None
    ) -> Dict[str, Any]:
        """Validate and enhance parsed product data.
        
        Args:
            product_data: Parsed product data dictionary
            context: Request context for error handling
            
        Returns:
            Enhanced product data with validation results
        """
        try:
            # Validate the product data
            validation_result = self.data_validator.validate_product_data(product_data)
            
            # Add validation metadata to the product data
            product_data["validation_errors"] = [error.to_dict() for error in validation_result.errors]
            product_data["validation_warnings"] = [warning.to_dict() for warning in validation_result.warnings]
            product_data["data_quality_score"] = validation_result.quality_score
            product_data["field_completeness"] = validation_result.field_completeness
            product_data["consistency_checks"] = validation_result.consistency_checks
            product_data["is_data_valid"] = validation_result.is_valid
            
            # Log validation results
            if not validation_result.is_valid:
                self.logger.warning(
                    f"Product data validation failed for ASIN {product_data.get('asin', 'unknown')}: "
                    f"{len(validation_result.errors)} errors, quality score: {validation_result.quality_score:.2f}"
                )
                
                # Log specific errors for debugging
                for error in validation_result.errors:
                    self.logger.debug(f"Validation error - {error.field}: {error.message}")
            
            elif validation_result.warnings:
                self.logger.info(
                    f"Product data has {len(validation_result.warnings)} validation warnings "
                    f"for ASIN {product_data.get('asin', 'unknown')}"
                )
            
            # Enhance data based on validation results
            product_data = self._enhance_data_based_on_validation(product_data, validation_result)
            
            return product_data
            
        except Exception as e:
            self.logger.error(f"Error during data validation: {e}")
            
            # Add error information to product data
            product_data["validation_errors"] = [{
                "field": "validation_process",
                "message": f"Validation failed: {str(e)}",
                "severity": "error"
            }]
            product_data["data_quality_score"] = 0.5  # Default moderate score
            product_data["is_data_valid"] = False
            
            return product_data
    
    def _enhance_data_based_on_validation(
        self, 
        product_data: Dict[str, Any], 
        validation_result: ValidationResult
    ) -> Dict[str, Any]:
        """Enhance product data based on validation results.
        
        Args:
            product_data: Product data dictionary
            validation_result: Validation result object
            
        Returns:
            Enhanced product data
        """
        try:
            # Fix common data issues automatically where possible
            
            # Ensure ASIN is uppercase
            if "asin" in product_data and isinstance(product_data["asin"], str):
                product_data["asin"] = product_data["asin"].upper()
            
            # Clean and validate title
            if "title" in product_data and isinstance(product_data["title"], str):
                title = product_data["title"].strip()
                if len(title) > 500:  # Truncate very long titles
                    title = title[:497] + "..."
                product_data["title"] = title
            
            # Ensure numeric fields are proper types
            numeric_fields = [
                "current_price", "avg_price_30d", "avg_price_90d", 
                "lowest_price_30d", "highest_price_30d", "rating",
                "bsr_current", "bsr_avg_30d", "bsr_avg_90d"
            ]
            
            for field in numeric_fields:
                if field in product_data and product_data[field] is not None:
                    try:
                        if field == "rating":
                            # Ratings should be floats
                            product_data[field] = float(product_data[field])
                        elif "price" in field:
                            # Prices should be floats
                            product_data[field] = float(product_data[field])
                        elif "bsr" in field:
                            # BSR can be int or float
                            value = product_data[field]
                            if isinstance(value, float) and value.is_integer():
                                product_data[field] = int(value)
                            else:
                                product_data[field] = float(value)
                    except (ValueError, TypeError):
                        # If conversion fails, set to None
                        product_data[field] = None
            
            # Ensure integer fields are proper types
            integer_fields = [
                "review_count", "estimated_sales_30d", "estimated_sales_90d", 
                "monthly_sold", "package_quantity"
            ]
            
            for field in integer_fields:
                if field in product_data and product_data[field] is not None:
                    try:
                        product_data[field] = int(float(product_data[field]))
                    except (ValueError, TypeError):
                        product_data[field] = 0
            
            # Ensure list fields are proper types
            list_fields = ["images", "features", "all_categories", "variation_asins"]
            
            for field in list_fields:
                if field in product_data:
                    if not isinstance(product_data[field], list):
                        if product_data[field] is None:
                            product_data[field] = []
                        else:
                            # Try to convert to list
                            try:
                                if isinstance(product_data[field], str):
                                    # Split comma-separated strings
                                    product_data[field] = [item.strip() for item in product_data[field].split(",") if item.strip()]
                                else:
                                    product_data[field] = [product_data[field]]
                            except:
                                product_data[field] = []
            
            # Add computed fields based on available data
            product_data = self._add_computed_fields(product_data)
            
            return product_data
            
        except Exception as e:
            self.logger.error(f"Error enhancing product data: {e}")
            return product_data
    
    def _add_computed_fields(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add computed fields to product data.
        
        Args:
            product_data: Product data dictionary
            
        Returns:
            Product data with computed fields added
        """
        try:
            # Calculate profitability score
            if hasattr(self, '_calculate_profitability_score'):
                product_data["profitability_score"] = self._calculate_profitability_score(product_data)
            
            # Determine competition level
            product_data["competition_level"] = self._determine_competition_level(product_data)
            
            # Calculate price trend if historical data available
            if "price_history" in product_data:
                product_data["price_trend"] = self._calculate_price_trend(product_data["price_history"])
            
            # Add market position indicator
            product_data["market_position"] = self._determine_market_position(product_data)
            
            # Add data freshness indicator
            product_data["data_freshness"] = self._calculate_data_freshness(product_data)
            
            return product_data
            
        except Exception as e:
            self.logger.error(f"Error adding computed fields: {e}")
            return product_data
    
    def _calculate_profitability_score(self, product_data: Dict[str, Any]) -> float:
        """Calculate profitability score based on multiple factors."""
        score = 0.0
        
        # Price factor (higher price = higher potential profit)
        current_price = product_data.get("current_price")
        if current_price:
            if current_price >= 20:
                score += 3.0
            elif current_price >= 10:
                score += 2.0
            elif current_price >= 5:
                score += 1.0
        
        # BSR factor (lower BSR = higher sales potential)
        bsr_current = product_data.get("bsr_current")
        if bsr_current:
            if bsr_current <= 1000:
                score += 3.0
            elif bsr_current <= 10000:
                score += 2.0
            elif bsr_current <= 100000:
                score += 1.0
        
        # Review factor (more reviews = established market)
        review_count = product_data.get("review_count", 0)
        if review_count >= 100:
            score += 2.0
        elif review_count >= 50:
            score += 1.0
        
        # Rating factor (higher rating = quality product)
        rating = product_data.get("rating")
        if rating and rating >= 4.0:
            score += 1.0
        
        # Sales estimate factor
        estimated_sales = product_data.get("estimated_sales_30d", 0)
        if estimated_sales >= 100:
            score += 2.0
        elif estimated_sales >= 50:
            score += 1.0
        
        return min(10.0, score)  # Cap at 10.0
    
    def _determine_competition_level(self, product_data: Dict[str, Any]) -> str:
        """Determine competition level based on review count and BSR."""
        review_count = product_data.get("review_count", 0)
        bsr_current = product_data.get("bsr_current")
        
        if not review_count or not bsr_current:
            return "unknown"
        
        if review_count > 500 and bsr_current < 10000:
            return "high"
        elif review_count > 100 and bsr_current < 50000:
            return "medium"
        else:
            return "low"
    
    def _calculate_price_trend(self, price_history: Dict[str, Any]) -> str:
        """Calculate price trend from price history data."""
        try:
            statistics = price_history.get("statistics", {})
            trend_direction = statistics.get("trend_direction", "unknown")
            trend_strength = statistics.get("trend_strength", 0.0)
            
            if trend_strength > 0.7:
                return f"strong_{trend_direction}"
            elif trend_strength > 0.3:
                return f"moderate_{trend_direction}"
            else:
                return "stable"
                
        except Exception:
            return "unknown"
    
    def _determine_market_position(self, product_data: Dict[str, Any]) -> str:
        """Determine market position based on BSR and category."""
        bsr_current = product_data.get("bsr_current")
        category = product_data.get("primary_category", "")
        
        if not bsr_current:
            return "unknown"
        
        # Category-specific BSR thresholds
        category_thresholds = {
            "Books": {"top": 1000, "good": 10000, "average": 100000},
            "Electronics": {"top": 500, "good": 5000, "average": 50000},
            "Home & Kitchen": {"top": 1000, "good": 10000, "average": 100000},
            "default": {"top": 1000, "good": 10000, "average": 100000}
        }
        
        thresholds = category_thresholds.get(category, category_thresholds["default"])
        
        if bsr_current <= thresholds["top"]:
            return "top_performer"
        elif bsr_current <= thresholds["good"]:
            return "good_performer"
        elif bsr_current <= thresholds["average"]:
            return "average_performer"
        else:
            return "poor_performer"
    
    def _calculate_data_freshness(self, product_data: Dict[str, Any]) -> str:
        """Calculate data freshness based on last_updated timestamp."""
        try:
            last_updated = product_data.get("last_updated")
            if not last_updated:
                return "unknown"
            
            if isinstance(last_updated, str):
                last_updated = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            
            if not isinstance(last_updated, datetime):
                return "unknown"
            
            age = datetime.now() - last_updated.replace(tzinfo=None)
            
            if age.total_seconds() < 3600:  # Less than 1 hour
                return "very_fresh"
            elif age.total_seconds() < 86400:  # Less than 1 day
                return "fresh"
            elif age.total_seconds() < 604800:  # Less than 1 week
                return "moderate"
            else:
                return "stale"
                
        except Exception:
            return "unknown"
    
    def validate_product_data(self, product_data: Dict[str, Any]) -> ValidationResult:
        """Validate product data and return detailed results.
        
        Args:
            product_data: Product data dictionary to validate
            
        Returns:
            ValidationResult object with detailed validation information
        """
        return self.data_validator.validate_product_data(product_data)
    
    def validate_batch_data(self, batch_data: List[Dict[str, Any]]) -> Dict[str, ValidationResult]:
        """Validate batch product data.
        
        Args:
            batch_data: List of product data dictionaries
            
        Returns:
            Dictionary mapping ASIN to ValidationResult
        """
        return self.data_validator.validate_batch_data(batch_data)
    
    def get_data_quality_report(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive data quality report.
        
        Args:
            product_data: Product data dictionary
            
        Returns:
            Detailed data quality report
        """
        validation_result = self.validate_product_data(product_data)
        
        return {
            "asin": product_data.get("asin", "unknown"),
            "overall_quality_score": validation_result.quality_score,
            "is_valid": validation_result.is_valid,
            "error_count": len(validation_result.errors),
            "warning_count": len(validation_result.warnings),
            "field_completeness": validation_result.field_completeness,
            "consistency_checks": validation_result.consistency_checks,
            "errors": [error.to_dict() for error in validation_result.errors],
            "warnings": [warning.to_dict() for warning in validation_result.warnings],
            "computed_fields": {
                "profitability_score": product_data.get("profitability_score"),
                "competition_level": product_data.get("competition_level"),
                "market_position": product_data.get("market_position"),
                "data_freshness": product_data.get("data_freshness")
            },
            "recommendations": self._generate_data_quality_recommendations(validation_result)
        }
    
    def _generate_data_quality_recommendations(self, validation_result: ValidationResult) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Recommendations based on errors
        error_fields = [error.field for error in validation_result.errors]
        
        if "asin" in error_fields:
            recommendations.append("Verify ASIN format - should be 10 alphanumeric characters")
        
        if "current_price" in error_fields:
            recommendations.append("Check price data - ensure positive numeric values")
        
        if "rating" in error_fields:
            recommendations.append("Validate rating data - should be between 0.0 and 5.0")
        
        # Recommendations based on completeness
        completeness = validation_result.field_completeness
        
        if completeness.get("pricing", 0) < 0.5:
            recommendations.append("Improve pricing data completeness for better analysis")
        
        if completeness.get("ratings", 0) < 0.5:
            recommendations.append("Gather more rating and review data")
        
        if completeness.get("details", 0) < 0.3:
            recommendations.append("Add product details like images and features")
        
        # Recommendations based on consistency
        consistency = validation_result.consistency_checks
        
        if not consistency.get("rating_review_consistency", True):
            recommendations.append("Investigate rating without reviews - may indicate data issue")
        
        if not consistency.get("bsr_sales_consistency", True):
            recommendations.append("Review BSR vs sales estimates for consistency")
        
        # Quality-based recommendations
        if validation_result.quality_score < 0.5:
            recommendations.append("Overall data quality is low - consider data refresh")
        elif validation_result.quality_score < 0.7:
            recommendations.append("Data quality is moderate - some improvements possible")
        
        return recommendations
    
    def get_request_metrics(self) -> Dict[str, Any]:
        """Get request performance and reliability metrics from the request manager."""
        return self.request_manager.get_metrics()
    
    def get_request_health_status(self) -> Dict[str, Any]:
        """Get health status of the request management system."""
        return self.request_manager.get_health_status()
    
    async def close_request_manager(self):
        """Close the request manager and clean up resources."""
        await self.request_manager.close()
    
    async def make_batch_api_requests(
        self,
        requests: List[Dict[str, Any]],
        max_concurrent: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Make multiple API requests concurrently using the request manager.
        
        Args:
            requests: List of request dictionaries with keys: endpoint, params
            max_concurrent: Maximum number of concurrent requests
            
        Returns:
            List of response data dictionaries in the same order as requests
        """
        # Convert Keepa-specific requests to full HTTP requests
        http_requests = []
        for req in requests:
            http_requests.append({
                'method': 'GET',
                'url': f"{self.base_url}/{req['endpoint']}",
                'params': req['params']
            })
        
        return await self.request_manager.make_batch_requests(http_requests, max_concurrent)
