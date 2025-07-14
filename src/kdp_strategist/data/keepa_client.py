"""Keepa API client for Amazon product data.

Provides access to:
- Product information (BSR, price, reviews, sales)
- Historical data and trends
- Category rankings
- Competitor analysis data
- Market insights

Features:
- Rate limiting and retry logic
- Comprehensive caching
- Error handling and logging
- Data validation and transformation
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from urllib.parse import urlencode

try:
    import requests
except ImportError:
    raise ImportError("requests library required. Install with: pip install requests")

from .cache_manager import CacheManager

logger = logging.getLogger(__name__)


@dataclass
class KeepaConfig:
    """Configuration for Keepa API client."""
    api_key: str
    base_url: str = "https://api.keepa.com"
    rate_limit_per_minute: int = 100
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: int = 30
    cache_ttl: int = 3600  # 1 hour
    enable_caching: bool = True


@dataclass
class ProductData:
    """Keepa product data structure."""
    asin: str
    title: str
    brand: Optional[str] = None
    category: Optional[str] = None
    current_price: Optional[float] = None
    avg_price_30d: Optional[float] = None
    avg_price_90d: Optional[float] = None
    bsr_current: Optional[int] = None
    bsr_avg_30d: Optional[float] = None
    bsr_avg_90d: Optional[float] = None
    review_count: Optional[int] = None
    rating: Optional[float] = None
    sales_rank_drops_30d: Optional[int] = None
    sales_rank_drops_90d: Optional[int] = None
    estimated_sales_30d: Optional[int] = None
    estimated_sales_90d: Optional[int] = None
    buy_box_percentage: Optional[float] = None
    fba_fees: Optional[float] = None
    dimensions: Optional[Dict[str, float]] = None
    weight: Optional[float] = None
    package_quantity: Optional[int] = None
    variation_asins: List[str] = field(default_factory=list)
    image_urls: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    categories: List[Dict[str, Any]] = field(default_factory=list)
    last_updated: Optional[datetime] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if self.last_updated is None:
            self.last_updated = datetime.now()
    
    @property
    def is_profitable(self) -> bool:
        """Check if product appears profitable based on basic metrics."""
        if not all([self.current_price, self.bsr_current, self.review_count]):
            return False
        
        # Basic profitability heuristics
        return (
            self.current_price >= 2.99 and  # Minimum viable price
            self.bsr_current <= 100000 and  # Decent sales rank
            self.review_count >= 10  # Some market validation
        )
    
    @property
    def competition_level(self) -> str:
        """Assess competition level based on review count and BSR."""
        if not all([self.review_count, self.bsr_current]):
            return "unknown"
        
        if self.review_count > 1000 or self.bsr_current < 1000:
            return "high"
        elif self.review_count > 100 or self.bsr_current < 10000:
            return "medium"
        else:
            return "low"
    
    @property
    def estimated_monthly_revenue(self) -> Optional[float]:
        """Estimate monthly revenue based on price and sales."""
        if not all([self.current_price, self.estimated_sales_30d]):
            return None
        
        return self.current_price * self.estimated_sales_30d
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = {
            "asin": self.asin,
            "title": self.title,
            "brand": self.brand,
            "category": self.category,
            "current_price": self.current_price,
            "avg_price_30d": self.avg_price_30d,
            "avg_price_90d": self.avg_price_90d,
            "bsr_current": self.bsr_current,
            "bsr_avg_30d": self.bsr_avg_30d,
            "bsr_avg_90d": self.bsr_avg_90d,
            "review_count": self.review_count,
            "rating": self.rating,
            "sales_rank_drops_30d": self.sales_rank_drops_30d,
            "sales_rank_drops_90d": self.sales_rank_drops_90d,
            "estimated_sales_30d": self.estimated_sales_30d,
            "estimated_sales_90d": self.estimated_sales_90d,
            "buy_box_percentage": self.buy_box_percentage,
            "fba_fees": self.fba_fees,
            "dimensions": self.dimensions,
            "weight": self.weight,
            "package_quantity": self.package_quantity,
            "variation_asins": self.variation_asins,
            "image_urls": self.image_urls,
            "features": self.features,
            "categories": self.categories,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductData":
        """Create from dictionary."""
        # Handle datetime conversion
        last_updated = data.get("last_updated")
        if last_updated and isinstance(last_updated, str):
            last_updated = datetime.fromisoformat(last_updated)
        
        return cls(
            asin=data["asin"],
            title=data["title"],
            brand=data.get("brand"),
            category=data.get("category"),
            current_price=data.get("current_price"),
            avg_price_30d=data.get("avg_price_30d"),
            avg_price_90d=data.get("avg_price_90d"),
            bsr_current=data.get("bsr_current"),
            bsr_avg_30d=data.get("bsr_avg_30d"),
            bsr_avg_90d=data.get("bsr_avg_90d"),
            review_count=data.get("review_count"),
            rating=data.get("rating"),
            sales_rank_drops_30d=data.get("sales_rank_drops_30d"),
            sales_rank_drops_90d=data.get("sales_rank_drops_90d"),
            estimated_sales_30d=data.get("estimated_sales_30d"),
            estimated_sales_90d=data.get("estimated_sales_90d"),
            buy_box_percentage=data.get("buy_box_percentage"),
            fba_fees=data.get("fba_fees"),
            dimensions=data.get("dimensions"),
            weight=data.get("weight"),
            package_quantity=data.get("package_quantity"),
            variation_asins=data.get("variation_asins", []),
            image_urls=data.get("image_urls", []),
            features=data.get("features", []),
            categories=data.get("categories", []),
            last_updated=last_updated,
        )


class RateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(self, max_requests_per_minute: int):
        self.max_requests = max_requests_per_minute
        self.requests = []
        self.lock = False
    
    def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded."""
        now = time.time()
        
        # Remove requests older than 1 minute
        self.requests = [req_time for req_time in self.requests if now - req_time < 60]
        
        # Check if we need to wait
        if len(self.requests) >= self.max_requests:
            sleep_time = 60 - (now - self.requests[0]) + 0.1  # Small buffer
            if sleep_time > 0:
                logger.info(f"Rate limit reached, waiting {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
                # Clean up old requests after waiting
                now = time.time()
                self.requests = [req_time for req_time in self.requests if now - req_time < 60]
        
        # Record this request
        self.requests.append(now)


class KeepaClient:
    """Keepa API client with caching and rate limiting."""
    
    def __init__(self, config: KeepaConfig, cache_manager: Optional[CacheManager] = None):
        self.config = config
        self.cache_manager = cache_manager
        self.rate_limiter = RateLimiter(config.rate_limit_per_minute)
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            "User-Agent": "KDP-Strategist/1.0",
            "Accept": "application/json",
        })
        
        logger.info(f"Initialized Keepa client with rate limit: {config.rate_limit_per_minute}/min")
    
    def get_product(self, asin: str, force_refresh: bool = False) -> Optional[ProductData]:
        """Get product data for a single ASIN."""
        # Check cache first
        if not force_refresh and self.config.enable_caching and self.cache_manager:
            cache_key = self.cache_manager.make_key("keepa", "product", asin)
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for ASIN: {asin}")
                return ProductData.from_dict(cached_data)
        
        # Fetch from API
        try:
            self.rate_limiter.wait_if_needed()
            
            params = {
                "key": self.config.api_key,
                "domain": 1,  # Amazon.com
                "asin": asin,
                "stats": 1,  # Include statistics
                "history": 1,  # Include price history
                "rating": 1,  # Include rating info
            }
            
            url = f"{self.config.base_url}/product"
            response = self._make_request("GET", url, params=params)
            
            if not response or "products" not in response:
                logger.warning(f"No product data found for ASIN: {asin}")
                return None
            
            products = response["products"]
            if not products:
                logger.warning(f"Empty product list for ASIN: {asin}")
                return None
            
            # Parse product data
            product_data = self._parse_product_data(products[0])
            
            # Cache the result
            if self.config.enable_caching and self.cache_manager:
                cache_key = self.cache_manager.make_key("keepa", "product", asin)
                self.cache_manager.set(cache_key, product_data.to_dict(), self.config.cache_ttl)
            
            logger.info(f"Retrieved product data for ASIN: {asin}")
            return product_data
        
        except Exception as e:
            logger.error(f"Failed to get product data for ASIN {asin}: {e}")
            return None
    
    def get_products_bulk(self, asins: List[str], force_refresh: bool = False) -> Dict[str, Optional[ProductData]]:
        """Get product data for multiple ASINs efficiently."""
        results = {}
        uncached_asins = []
        
        # Check cache for each ASIN
        if not force_refresh and self.config.enable_caching and self.cache_manager:
            for asin in asins:
                cache_key = self.cache_manager.make_key("keepa", "product", asin)
                cached_data = self.cache_manager.get(cache_key)
                if cached_data:
                    results[asin] = ProductData.from_dict(cached_data)
                    logger.debug(f"Cache hit for ASIN: {asin}")
                else:
                    uncached_asins.append(asin)
        else:
            uncached_asins = asins
        
        # Fetch uncached ASINs from API
        if uncached_asins:
            try:
                self.rate_limiter.wait_if_needed()
                
                params = {
                    "key": self.config.api_key,
                    "domain": 1,  # Amazon.com
                    "asin": ",".join(uncached_asins),
                    "stats": 1,
                    "history": 1,
                    "rating": 1,
                }
                
                url = f"{self.config.base_url}/product"
                response = self._make_request("GET", url, params=params)
                
                if response and "products" in response:
                    for product_raw in response["products"]:
                        try:
                            product_data = self._parse_product_data(product_raw)
                            results[product_data.asin] = product_data
                            
                            # Cache the result
                            if self.config.enable_caching and self.cache_manager:
                                cache_key = self.cache_manager.make_key("keepa", "product", product_data.asin)
                                self.cache_manager.set(cache_key, product_data.to_dict(), self.config.cache_ttl)
                        
                        except Exception as e:
                            logger.error(f"Failed to parse product data: {e}")
                            continue
                
                logger.info(f"Retrieved bulk product data for {len(uncached_asins)} ASINs")
            
            except Exception as e:
                logger.error(f"Failed to get bulk product data: {e}")
        
        # Ensure all requested ASINs are in results (with None for failures)
        for asin in asins:
            if asin not in results:
                results[asin] = None
        
        return results
    
    def search_products(self, query: str, category: Optional[str] = None, limit: int = 50) -> List[ProductData]:
        """Search for products by keyword."""
        try:
            self.rate_limiter.wait_if_needed()
            
            params = {
                "key": self.config.api_key,
                "domain": 1,
                "type": "search",
                "term": query,
                "stats": 1,
                "history": 0,  # Don't need full history for search
                "page": 0,
                "perPage": min(limit, 100),  # API limit
            }
            
            if category:
                params["category"] = category
            
            url = f"{self.config.base_url}/search"
            response = self._make_request("GET", url, params=params)
            
            if not response or "asinList" not in response:
                logger.warning(f"No search results for query: {query}")
                return []
            
            # Get detailed product data for found ASINs
            asins = response["asinList"][:limit]
            if not asins:
                return []
            
            products_data = self.get_products_bulk(asins)
            results = [product for product in products_data.values() if product is not None]
            
            logger.info(f"Found {len(results)} products for query: {query}")
            return results
        
        except Exception as e:
            logger.error(f"Failed to search products for query '{query}': {e}")
            return []
    
    def get_category_tree(self, category_id: Optional[int] = None) -> Dict[str, Any]:
        """Get Amazon category tree."""
        cache_key = f"keepa:category_tree:{category_id or 'root'}"
        
        # Check cache
        if self.config.enable_caching and self.cache_manager:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                return cached_data
        
        try:
            self.rate_limiter.wait_if_needed()
            
            params = {
                "key": self.config.api_key,
                "domain": 1,
            }
            
            if category_id:
                params["category"] = category_id
            
            url = f"{self.config.base_url}/category"
            response = self._make_request("GET", url, params=params)
            
            if response:
                # Cache for longer since category tree doesn't change often
                if self.config.enable_caching and self.cache_manager:
                    self.cache_manager.set(cache_key, response, 86400)  # 24 hours
                
                return response
            
            return {}
        
        except Exception as e:
            logger.error(f"Failed to get category tree: {e}")
            return {}
    
    def _make_request(self, method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make HTTP request with retry logic."""
        for attempt in range(self.config.max_retries + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.config.timeout,
                    **kwargs
                )
                
                if response.status_code == 200:
                    return response.json()
                
                elif response.status_code == 429:  # Rate limited
                    if attempt < self.config.max_retries:
                        wait_time = self.config.retry_delay * (2 ** attempt)
                        logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                        time.sleep(wait_time)
                        continue
                
                elif response.status_code == 400:
                    logger.error(f"Bad request to Keepa API: {response.text}")
                    return None
                
                elif response.status_code == 401:
                    logger.error("Unauthorized - check Keepa API key")
                    return None
                
                else:
                    logger.warning(f"Keepa API returned status {response.status_code}: {response.text}")
                    if attempt < self.config.max_retries:
                        time.sleep(self.config.retry_delay)
                        continue
                
                return None
            
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1})")
                if attempt < self.config.max_retries:
                    time.sleep(self.config.retry_delay)
                    continue
            
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                if attempt < self.config.max_retries:
                    time.sleep(self.config.retry_delay)
                    continue
        
        logger.error(f"Failed to make request after {self.config.max_retries + 1} attempts")
        return None
    
    def _parse_product_data(self, raw_data: Dict[str, Any]) -> ProductData:
        """Parse raw Keepa API response into ProductData object."""
        # Extract basic info
        asin = raw_data.get("asin", "")
        title = raw_data.get("title", "")
        brand = raw_data.get("brand")
        
        # Extract pricing data
        current_price = None
        avg_price_30d = None
        avg_price_90d = None
        
        if "stats" in raw_data:
            stats = raw_data["stats"]
            current_price = stats.get("current", {}).get("AMAZON", {}).get("price")
            avg_price_30d = stats.get("avg30", {}).get("AMAZON", {}).get("price")
            avg_price_90d = stats.get("avg90", {}).get("AMAZON", {}).get("price")
        
        # Convert from Keepa price format (price * 100) to dollars
        if current_price is not None:
            current_price = current_price / 100
        if avg_price_30d is not None:
            avg_price_30d = avg_price_30d / 100
        if avg_price_90d is not None:
            avg_price_90d = avg_price_90d / 100
        
        # Extract BSR data
        bsr_current = raw_data.get("salesRankCurrent")
        bsr_avg_30d = None
        bsr_avg_90d = None
        
        if "stats" in raw_data:
            stats = raw_data["stats"]
            bsr_avg_30d = stats.get("avg30", {}).get("salesRank")
            bsr_avg_90d = stats.get("avg90", {}).get("salesRank")
        
        # Extract review data
        review_count = raw_data.get("reviewCount")
        rating = raw_data.get("rating")
        if rating is not None:
            rating = rating / 10  # Keepa uses rating * 10
        
        # Extract other metrics
        sales_rank_drops_30d = raw_data.get("salesRankDrops30")
        sales_rank_drops_90d = raw_data.get("salesRankDrops90")
        
        # Estimate sales (simplified calculation)
        estimated_sales_30d = None
        estimated_sales_90d = None
        if bsr_current and bsr_current > 0:
            # Very rough estimation based on BSR
            estimated_sales_30d = max(1, int(1000000 / bsr_current))
            estimated_sales_90d = estimated_sales_30d * 3
        
        # Extract additional data
        buy_box_percentage = raw_data.get("buyBoxPercentage")
        fba_fees = raw_data.get("fbaFees")
        if fba_fees is not None:
            fba_fees = fba_fees / 100  # Convert from cents
        
        # Extract dimensions and weight
        dimensions = None
        if "packageHeight" in raw_data:
            dimensions = {
                "height": raw_data.get("packageHeight"),
                "length": raw_data.get("packageLength"),
                "width": raw_data.get("packageWidth"),
            }
        
        weight = raw_data.get("packageWeight")
        package_quantity = raw_data.get("packageQuantity")
        
        # Extract variations and images
        variation_asins = raw_data.get("variationASINs", [])
        image_urls = raw_data.get("imagesCSV", "").split(",") if raw_data.get("imagesCSV") else []
        
        # Extract features
        features = raw_data.get("features", [])
        
        # Extract categories
        categories = []
        if "categoryTree" in raw_data:
            for cat in raw_data["categoryTree"]:
                categories.append({
                    "id": cat.get("catId"),
                    "name": cat.get("name"),
                    "parent": cat.get("parent"),
                })
        
        return ProductData(
            asin=asin,
            title=title,
            brand=brand,
            category=categories[0]["name"] if categories else None,
            current_price=current_price,
            avg_price_30d=avg_price_30d,
            avg_price_90d=avg_price_90d,
            bsr_current=bsr_current,
            bsr_avg_30d=bsr_avg_30d,
            bsr_avg_90d=bsr_avg_90d,
            review_count=review_count,
            rating=rating,
            sales_rank_drops_30d=sales_rank_drops_30d,
            sales_rank_drops_90d=sales_rank_drops_90d,
            estimated_sales_30d=estimated_sales_30d,
            estimated_sales_90d=estimated_sales_90d,
            buy_box_percentage=buy_box_percentage,
            fba_fees=fba_fees,
            dimensions=dimensions,
            weight=weight,
            package_quantity=package_quantity,
            variation_asins=variation_asins,
            image_urls=image_urls,
            features=features,
            categories=categories,
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        stats = {
            "rate_limit_per_minute": self.config.rate_limit_per_minute,
            "requests_in_last_minute": len(self.rate_limiter.requests),
            "cache_enabled": self.config.enable_caching,
        }
        
        if self.cache_manager:
            stats["cache_stats"] = self.cache_manager.get_stats()
        
        return stats
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.session.close()