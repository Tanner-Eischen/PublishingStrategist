"""Enhanced Keepa product data models based on official API specification.

This module provides comprehensive data models for Keepa API responses with:
- Full field coverage from official API specification
- Data validation and constraint checking
- Calculated fields (profitability score, competition level)
- Data quality scoring based on completeness and accuracy
- Serialization and deserialization methods
- Model conversion utilities for different output formats
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import statistics
from decimal import Decimal

logger = logging.getLogger(__name__)


class PriceType(Enum):
    """Enumeration of price types in Keepa API."""
    AMAZON = "amazon"
    NEW = "new"
    USED = "used"
    SALES_RANK = "sales_rank"
    RATING = "rating"
    BUY_BOX = "buy_box"
    COUNT_NEW = "count_new"
    COUNT_USED = "count_used"
    COUNT_REFURB = "count_refurb"
    COUNT_COLLECTIBLE = "count_collectible"


class CompetitionLevel(Enum):
    """Competition level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class TrendDirection(Enum):
    """Price trend direction."""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    UNKNOWN = "unknown"


@dataclass
class ProductDimensions:
    """Product physical dimensions."""
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    unit_length: str = "inches"
    unit_weight: str = "pounds"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def get_volume(self) -> Optional[float]:
        """Calculate volume if all dimensions are available."""
        if all([self.length, self.width, self.height]):
            return self.length * self.width * self.height
        return None
    
    def is_complete(self) -> bool:
        """Check if all dimension data is available."""
        return all([
            self.length is not None,
            self.width is not None,
            self.height is not None,
            self.weight is not None
        ])


@dataclass
class CategoryNode:
    """Category hierarchy node with full tree information."""
    id: Optional[int]
    name: str
    parent_id: Optional[int] = None
    level: int = 0
    path: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def get_full_path(self) -> str:
        """Get full category path as string."""
        if self.path:
            return " > ".join(self.path)
        return self.name


@dataclass
class CategoryHierarchy:
    """Complete category hierarchy information."""
    nodes: List[CategoryNode] = field(default_factory=list)
    primary_category: Optional[CategoryNode] = None
    all_category_names: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "primary_category": self.primary_category.to_dict() if self.primary_category else None,
            "all_category_names": self.all_category_names
        }
    
    def get_primary_path(self) -> str:
        """Get primary category path."""
        if self.primary_category:
            return self.primary_category.get_full_path()
        return ""
    
    def get_depth(self) -> int:
        """Get maximum category depth."""
        if not self.nodes:
            return 0
        return max(node.level for node in self.nodes)


@dataclass
class PricePoint:
    """Individual price history data point."""
    timestamp: datetime
    price: float
    price_type: PriceType = PriceType.AMAZON
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "price": self.price,
            "price_type": self.price_type.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PricePoint':
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            price=data["price"],
            price_type=PriceType(data.get("price_type", "amazon"))
        )


@dataclass
class PriceStatistics:
    """Price trend analysis and statistics."""
    current_price: Optional[float] = None
    average_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0
    price_volatility: float = 0.0
    trend_direction: TrendDirection = TrendDirection.UNKNOWN
    trend_strength: float = 0.0  # 0.0 to 1.0
    price_drops_count: int = 0
    price_increases_count: int = 0
    days_analyzed: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["trend_direction"] = self.trend_direction.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PriceStatistics':
        """Create from dictionary."""
        data = data.copy()
        if "trend_direction" in data:
            data["trend_direction"] = TrendDirection(data["trend_direction"])
        return cls(**data)


@dataclass
class SalesEstimate:
    """Sales estimation data with confidence metrics."""
    daily_sales: float = 0.0
    monthly_sales: float = 0.0
    yearly_sales: float = 0.0
    confidence_score: float = 0.0  # 0.0 to 1.0
    estimation_method: str = "bsr_based"
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["last_updated"] = self.last_updated.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SalesEstimate':
        """Create from dictionary."""
        data = data.copy()
        if "last_updated" in data:
            data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        return cls(**data)


@dataclass
class VariationData:
    """Product variation information."""
    parent_asin: Optional[str] = None
    variation_asins: List[str] = field(default_factory=list)
    variation_attributes: Dict[str, List[str]] = field(default_factory=dict)
    is_parent: bool = False
    is_child: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def get_variation_count(self) -> int:
        """Get total number of variations."""
        return len(self.variation_asins)


@dataclass
class MarketplaceData:
    """Marketplace and seller information."""
    buy_box_winner: Optional[str] = None
    buy_box_price: Optional[float] = None
    buy_box_percentage: Optional[float] = None
    fba_fees: Optional[float] = None
    seller_count: int = 0
    new_offer_count: int = 0
    used_offer_count: int = 0
    refurb_offer_count: int = 0
    collectible_offer_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def get_total_offers(self) -> int:
        """Get total number of offers across all conditions."""
        return (self.new_offer_count + self.used_offer_count + 
                self.refurb_offer_count + self.collectible_offer_count)


@dataclass
class ReviewData:
    """Review and rating information."""
    review_count: int = 0
    rating: Optional[float] = None
    rating_distribution: Dict[int, int] = field(default_factory=dict)
    review_velocity: Optional[float] = None  # reviews per day
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def get_weighted_rating(self) -> Optional[float]:
        """Calculate weighted average rating from distribution."""
        if not self.rating_distribution:
            return self.rating
        
        total_reviews = sum(self.rating_distribution.values())
        if total_reviews == 0:
            return self.rating
        
        weighted_sum = sum(rating * count for rating, count in self.rating_distribution.items())
        return weighted_sum / total_reviews
    
    def get_review_quality_score(self) -> float:
        """Calculate review quality score based on count and rating."""
        if not self.rating or self.review_count == 0:
            return 0.0
        
        # Base score from rating (0-5 scale normalized to 0-1)
        rating_score = self.rating / 5.0
        
        # Review count factor (logarithmic scaling)
        import math
        count_factor = min(1.0, math.log10(self.review_count + 1) / 3.0)  # log10(1000) ≈ 3
        
        return rating_score * count_factor


@dataclass
class DataQualityMetrics:
    """Data quality and completeness metrics."""
    completeness_score: float = 0.0  # 0.0 to 1.0
    accuracy_score: float = 0.0      # 0.0 to 1.0
    freshness_score: float = 0.0     # 0.0 to 1.0
    overall_score: float = 0.0       # 0.0 to 1.0
    missing_fields: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    last_validated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["last_validated"] = self.last_validated.isoformat()
        return data
    
    def calculate_overall_score(self) -> float:
        """Calculate overall data quality score."""
        scores = [self.completeness_score, self.accuracy_score, self.freshness_score]
        valid_scores = [s for s in scores if s > 0]
        
        if not valid_scores:
            return 0.0
        
        self.overall_score = sum(valid_scores) / len(valid_scores)
        return self.overall_score


@dataclass
class EnhancedProductData:
    """Comprehensive product data model based on Keepa API specification.
    
    This model includes all fields from the official Keepa API specification
    plus calculated fields and data quality metrics.
    """
    
    # Basic Product Information (Required)
    asin: str
    title: str
    
    # Basic Product Information (Optional)
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    part_number: Optional[str] = None
    product_group: Optional[str] = None
    binding: Optional[str] = None
    description: Optional[str] = None
    
    # Pricing Information
    current_price: Optional[float] = None
    avg_price_30d: Optional[float] = None
    avg_price_90d: Optional[float] = None
    lowest_price_30d: Optional[float] = None
    highest_price_30d: Optional[float] = None
    price_drops_30d: int = 0
    
    # Sales Rank Information
    bsr_current: Optional[int] = None
    bsr_avg_30d: Optional[float] = None
    bsr_avg_90d: Optional[float] = None
    bsr_drops_30d: int = 0
    bsr_category: Optional[str] = None
    
    # Review Information
    review_data: ReviewData = field(default_factory=ReviewData)
    
    # Category Information
    category_hierarchy: CategoryHierarchy = field(default_factory=CategoryHierarchy)
    
    # Product Details
    images: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    dimensions: Optional[ProductDimensions] = None
    package_quantity: int = 1
    
    # Variations and Related Products
    variation_data: VariationData = field(default_factory=VariationData)
    
    # Sales Estimates
    sales_estimate: SalesEstimate = field(default_factory=SalesEstimate)
    
    # Marketplace Information
    marketplace_data: MarketplaceData = field(default_factory=MarketplaceData)
    
    # Price Statistics
    price_statistics: Optional[PriceStatistics] = None
    
    # Data Quality and Metadata
    data_quality: DataQualityMetrics = field(default_factory=DataQualityMetrics)
    last_updated: datetime = field(default_factory=datetime.now)
    api_response_time: Optional[float] = None
    cache_hit: bool = False
    
    # Debug and Raw Data
    raw_stats_current: List[Any] = field(default_factory=list)
    raw_stats_avg: List[Any] = field(default_factory=list)
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ProductData to dictionary with proper serialization."""
        data = {
            # Basic information
            "asin": self.asin,
            "title": self.title,
            "brand": self.brand,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "part_number": self.part_number,
            "product_group": self.product_group,
            "binding": self.binding,
            "description": self.description,
            
            # Pricing
            "current_price": self.current_price,
            "avg_price_30d": self.avg_price_30d,
            "avg_price_90d": self.avg_price_90d,
            "lowest_price_30d": self.lowest_price_30d,
            "highest_price_30d": self.highest_price_30d,
            "price_drops_30d": self.price_drops_30d,
            
            # Sales rank
            "bsr_current": self.bsr_current,
            "bsr_avg_30d": self.bsr_avg_30d,
            "bsr_avg_90d": self.bsr_avg_90d,
            "bsr_drops_30d": self.bsr_drops_30d,
            "bsr_category": self.bsr_category,
            
            # Complex objects
            "review_data": self.review_data.to_dict(),
            "category_hierarchy": self.category_hierarchy.to_dict(),
            "images": self.images,
            "features": self.features,
            "dimensions": self.dimensions.to_dict() if self.dimensions else None,
            "package_quantity": self.package_quantity,
            "variation_data": self.variation_data.to_dict(),
            "sales_estimate": self.sales_estimate.to_dict(),
            "marketplace_data": self.marketplace_data.to_dict(),
            "price_statistics": self.price_statistics.to_dict() if self.price_statistics else None,
            "data_quality": self.data_quality.to_dict(),
            
            # Metadata
            "last_updated": self.last_updated.isoformat(),
            "api_response_time": self.api_response_time,
            "cache_hit": self.cache_hit,
            "raw_stats_current": self.raw_stats_current,
            "raw_stats_avg": self.raw_stats_avg,
            "additional_data": self.additional_data
        }
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnhancedProductData':
        """Create EnhancedProductData from dictionary."""
        # Handle nested objects
        review_data = ReviewData(**data.get("review_data", {}))
        
        category_data = data.get("category_hierarchy", {})
        category_hierarchy = CategoryHierarchy(
            nodes=[CategoryNode(**node) for node in category_data.get("nodes", [])],
            primary_category=CategoryNode(**category_data["primary_category"]) if category_data.get("primary_category") else None,
            all_category_names=category_data.get("all_category_names", [])
        )
        
        dimensions = None
        if data.get("dimensions"):
            dimensions = ProductDimensions(**data["dimensions"])
        
        variation_data = VariationData(**data.get("variation_data", {}))
        sales_estimate = SalesEstimate.from_dict(data.get("sales_estimate", {}))
        marketplace_data = MarketplaceData(**data.get("marketplace_data", {}))
        
        price_statistics = None
        if data.get("price_statistics"):
            price_statistics = PriceStatistics.from_dict(data["price_statistics"])
        
        data_quality = DataQualityMetrics(**data.get("data_quality", {}))
        if "last_validated" in data.get("data_quality", {}):
            data_quality.last_validated = datetime.fromisoformat(data["data_quality"]["last_validated"])
        
        # Handle datetime
        last_updated = datetime.now()
        if "last_updated" in data:
            last_updated = datetime.fromisoformat(data["last_updated"])
        
        return cls(
            asin=data["asin"],
            title=data["title"],
            brand=data.get("brand"),
            manufacturer=data.get("manufacturer"),
            model=data.get("model"),
            part_number=data.get("part_number"),
            product_group=data.get("product_group"),
            binding=data.get("binding"),
            description=data.get("description"),
            current_price=data.get("current_price"),
            avg_price_30d=data.get("avg_price_30d"),
            avg_price_90d=data.get("avg_price_90d"),
            lowest_price_30d=data.get("lowest_price_30d"),
            highest_price_30d=data.get("highest_price_30d"),
            price_drops_30d=data.get("price_drops_30d", 0),
            bsr_current=data.get("bsr_current"),
            bsr_avg_30d=data.get("bsr_avg_30d"),
            bsr_avg_90d=data.get("bsr_avg_90d"),
            bsr_drops_30d=data.get("bsr_drops_30d", 0),
            bsr_category=data.get("bsr_category"),
            review_data=review_data,
            category_hierarchy=category_hierarchy,
            images=data.get("images", []),
            features=data.get("features", []),
            dimensions=dimensions,
            package_quantity=data.get("package_quantity", 1),
            variation_data=variation_data,
            sales_estimate=sales_estimate,
            marketplace_data=marketplace_data,
            price_statistics=price_statistics,
            data_quality=data_quality,
            last_updated=last_updated,
            api_response_time=data.get("api_response_time"),
            cache_hit=data.get("cache_hit", False),
            raw_stats_current=data.get("raw_stats_current", []),
            raw_stats_avg=data.get("raw_stats_avg", []),
            additional_data=data.get("additional_data", {})
        )
    
    def to_json(self, indent: Optional[int] = None) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'EnhancedProductData':
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def get_category_path(self) -> str:
        """Get category path as a readable string."""
        return self.category_hierarchy.get_primary_path()
    
    def calculate_profitability_score(self) -> float:
        """Calculate profitability score based on multiple factors.
        
        Returns:
            Score from 0.0 to 10.0 based on various profitability indicators
        """
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
        if self.review_data.review_count >= 100:
            score += 2.0
        elif self.review_data.review_count >= 50:
            score += 1.0
        
        # Rating factor (higher rating = quality product)
        if self.review_data.rating and self.review_data.rating >= 4.0:
            score += 1.0
        
        # Sales estimate factor
        if self.sales_estimate.monthly_sales >= 100:
            score += 2.0
        elif self.sales_estimate.monthly_sales >= 50:
            score += 1.0
        
        # Competition factor (fewer sellers = less competition)
        if self.marketplace_data.seller_count <= 5:
            score += 1.0
        elif self.marketplace_data.seller_count <= 20:
            score += 0.5
        
        return min(10.0, score)  # Cap at 10.0
    
    def get_competition_level(self) -> CompetitionLevel:
        """Determine competition level based on review count, BSR, and seller count."""
        if not self.review_data.review_count or not self.bsr_current:
            return CompetitionLevel.UNKNOWN
        
        # High competition indicators
        high_competition_factors = 0
        if self.review_data.review_count > 500:
            high_competition_factors += 1
        if self.bsr_current < 10000:
            high_competition_factors += 1
        if self.marketplace_data.seller_count > 50:
            high_competition_factors += 1
        
        # Medium competition indicators
        medium_competition_factors = 0
        if 100 < self.review_data.review_count <= 500:
            medium_competition_factors += 1
        if 10000 <= self.bsr_current < 50000:
            medium_competition_factors += 1
        if 10 < self.marketplace_data.seller_count <= 50:
            medium_competition_factors += 1
        
        if high_competition_factors >= 2:
            return CompetitionLevel.HIGH
        elif medium_competition_factors >= 2 or high_competition_factors >= 1:
            return CompetitionLevel.MEDIUM
        else:
            return CompetitionLevel.LOW
    
    def calculate_data_quality_score(self) -> float:
        """Calculate comprehensive data quality score."""
        # Count required fields
        required_fields = ["asin", "title"]
        important_fields = [
            "current_price", "bsr_current", "review_data.review_count",
            "review_data.rating", "category_hierarchy.primary_category"
        ]
        optional_fields = [
            "brand", "manufacturer", "description", "images", "features",
            "dimensions", "sales_estimate.monthly_sales"
        ]
        
        # Calculate completeness score
        required_complete = all(getattr(self, field, None) is not None for field in required_fields)
        if not required_complete:
            self.data_quality.completeness_score = 0.0
        else:
            important_complete = 0
            for field in important_fields:
                if "." in field:
                    obj_name, attr_name = field.split(".", 1)
                    obj = getattr(self, obj_name, None)
                    if obj and getattr(obj, attr_name, None) is not None:
                        important_complete += 1
                else:
                    if getattr(self, field, None) is not None:
                        important_complete += 1
            
            optional_complete = 0
            for field in optional_fields:
                if "." in field:
                    obj_name, attr_name = field.split(".", 1)
                    obj = getattr(self, obj_name, None)
                    if obj and getattr(obj, attr_name, None) is not None:
                        optional_complete += 1
                else:
                    value = getattr(self, field, None)
                    if value is not None and (not isinstance(value, list) or len(value) > 0):
                        optional_complete += 1
            
            # Weighted completeness score
            important_weight = 0.6
            optional_weight = 0.4
            
            important_score = important_complete / len(important_fields)
            optional_score = optional_complete / len(optional_fields)
            
            self.data_quality.completeness_score = (
                important_score * important_weight + 
                optional_score * optional_weight
            )
        
        # Calculate accuracy score (based on validation errors)
        total_validations = len(required_fields) + len(important_fields) + len(optional_fields)
        error_count = len(self.data_quality.validation_errors)
        self.data_quality.accuracy_score = max(0.0, 1.0 - (error_count / total_validations))
        
        # Calculate freshness score (based on last_updated)
        hours_since_update = (datetime.now() - self.last_updated).total_seconds() / 3600
        if hours_since_update <= 1:
            self.data_quality.freshness_score = 1.0
        elif hours_since_update <= 24:
            self.data_quality.freshness_score = 0.8
        elif hours_since_update <= 168:  # 1 week
            self.data_quality.freshness_score = 0.6
        else:
            self.data_quality.freshness_score = 0.3
        
        # Calculate overall score
        return self.data_quality.calculate_overall_score()
    
    def validate_constraints(self) -> List[str]:
        """Validate data constraints and return list of errors."""
        errors = []
        
        # Basic validation
        if not self.asin or len(self.asin) != 10:
            errors.append("ASIN must be exactly 10 characters")
        
        if not self.title or len(self.title.strip()) == 0:
            errors.append("Title cannot be empty")
        
        # Price validation
        if self.current_price is not None and self.current_price < 0:
            errors.append("Current price cannot be negative")
        
        if self.avg_price_30d is not None and self.avg_price_30d < 0:
            errors.append("Average price cannot be negative")
        
        # BSR validation
        if self.bsr_current is not None and self.bsr_current <= 0:
            errors.append("BSR must be positive")
        
        # Review validation
        if self.review_data.rating is not None and (self.review_data.rating < 0 or self.review_data.rating > 5):
            errors.append("Rating must be between 0 and 5")
        
        if self.review_data.review_count < 0:
            errors.append("Review count cannot be negative")
        
        # Sales estimate validation
        if self.sales_estimate.monthly_sales < 0:
            errors.append("Monthly sales cannot be negative")
        
        if self.sales_estimate.confidence_score < 0 or self.sales_estimate.confidence_score > 1:
            errors.append("Confidence score must be between 0 and 1")
        
        # Update validation errors in data quality
        self.data_quality.validation_errors = errors
        
        return errors
    
    def to_legacy_format(self) -> Dict[str, Any]:
        """Convert to legacy ProductData format for backward compatibility."""
        return {
            "asin": self.asin,
            "title": self.title,
            "brand": self.brand,
            "manufacturer": self.manufacturer,
            "product_group": self.product_group,
            "description": self.description,
            "current_price": self.current_price,
            "avg_price_30d": self.avg_price_30d,
            "avg_price_90d": self.avg_price_90d,
            "lowest_price_30d": self.lowest_price_30d,
            "highest_price_30d": self.highest_price_30d,
            "bsr_current": self.bsr_current,
            "bsr_avg_30d": self.bsr_avg_30d,
            "bsr_avg_90d": self.bsr_avg_90d,
            "review_count": self.review_data.review_count,
            "rating": self.review_data.rating,
            "primary_category": self.category_hierarchy.get_primary_path(),
            "category_hierarchy": [node.to_dict() for node in self.category_hierarchy.nodes],
            "all_categories": self.category_hierarchy.all_category_names,
            "images": self.images,
            "features": self.features,
            "dimensions": self.dimensions.to_dict() if self.dimensions else None,
            "weight": self.dimensions.weight if self.dimensions else None,
            "estimated_sales_30d": int(self.sales_estimate.monthly_sales),
            "estimated_sales_90d": int(self.sales_estimate.monthly_sales * 3),
            "monthly_sold": int(self.sales_estimate.monthly_sales),
            "buy_box_percentage": self.marketplace_data.buy_box_percentage,
            "fba_fees": self.marketplace_data.fba_fees,
            "package_quantity": self.package_quantity,
            "variation_asins": self.variation_data.variation_asins,
            "last_updated": self.last_updated,
            "data_quality_score": self.data_quality.overall_score,
            "validation_errors": self.data_quality.validation_errors,
            "raw_stats_current": self.raw_stats_current,
            "raw_stats_avg": self.raw_stats_avg,
            "additional_data": self.additional_data
        }
    
    def to_csv_row(self) -> Dict[str, Any]:
        """Convert to flat dictionary suitable for CSV export."""
        return {
            "asin": self.asin,
            "title": self.title,
            "brand": self.brand or "",
            "manufacturer": self.manufacturer or "",
            "current_price": self.current_price or 0,
            "bsr_current": self.bsr_current or 0,
            "review_count": self.review_data.review_count,
            "rating": self.review_data.rating or 0,
            "monthly_sales": self.sales_estimate.monthly_sales,
            "profitability_score": self.calculate_profitability_score(),
            "competition_level": self.get_competition_level().value,
            "category_path": self.get_category_path(),
            "seller_count": self.marketplace_data.seller_count,
            "data_quality_score": self.data_quality.overall_score,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class PriceHistoryData:
    """Complete price history data for a product."""
    asin: str
    price_points: List[PricePoint]
    price_type: PriceType
    time_period_days: int
    data_points: int
    statistics: PriceStatistics
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization."""
        return {
            "asin": self.asin,
            "price_points": [point.to_dict() for point in self.price_points],
            "price_type": self.price_type.value,
            "time_period_days": self.time_period_days,
            "data_points": self.data_points,
            "statistics": self.statistics.to_dict(),
            "last_updated": self.last_updated.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PriceHistoryData':
        """Create from dictionary."""
        return cls(
            asin=data["asin"],
            price_points=[PricePoint.from_dict(point) for point in data["price_points"]],
            price_type=PriceType(data["price_type"]),
            time_period_days=data["time_period_days"],
            data_points=data["data_points"],
            statistics=PriceStatistics.from_dict(data["statistics"]),
            last_updated=datetime.fromisoformat(data["last_updated"])
        )
    
    def get_price_trend(self) -> Tuple[TrendDirection, float]:
        """Analyze price trend and return direction and strength."""
        if len(self.price_points) < 2:
            return TrendDirection.UNKNOWN, 0.0
        
        # Calculate linear regression slope
        prices = [point.price for point in self.price_points]
        n = len(prices)
        x_values = list(range(n))
        
        # Calculate slope using least squares
        x_mean = sum(x_values) / n
        y_mean = sum(prices) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, prices))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            return TrendDirection.STABLE, 0.0
        
        slope = numerator / denominator
        
        # Determine trend direction and strength
        price_range = max(prices) - min(prices)
        if price_range == 0:
            return TrendDirection.STABLE, 0.0
        
        # Normalize slope by price range to get strength (0-1)
        strength = min(1.0, abs(slope * n) / price_range)
        
        if abs(slope) < 0.01:  # Very small slope
            return TrendDirection.STABLE, strength
        elif slope > 0:
            return TrendDirection.UP, strength
        else:
            return TrendDirection.DOWN, strength


# Utility functions for model conversion and validation

def validate_product_data(product: EnhancedProductData) -> Tuple[bool, List[str]]:
    """Validate product data and return validation result.
    
    Args:
        product: Product data to validate
        
    Returns:
        Tuple of (is_valid, error_list)
    """
    errors = product.validate_constraints()
    product.calculate_data_quality_score()
    
    return len(errors) == 0, errors


def convert_legacy_to_enhanced(legacy_data: Dict[str, Any]) -> EnhancedProductData:
    """Convert legacy ProductData format to EnhancedProductData.
    
    Args:
        legacy_data: Dictionary in legacy format
        
    Returns:
        EnhancedProductData object
    """
    # Create review data
    review_data = ReviewData(
        review_count=legacy_data.get("review_count", 0),
        rating=legacy_data.get("rating")
    )
    
    # Create category hierarchy
    category_hierarchy = CategoryHierarchy(
        all_category_names=legacy_data.get("all_categories", [])
    )
    
    if legacy_data.get("primary_category"):
        category_hierarchy.primary_category = CategoryNode(
            id=None,
            name=legacy_data["primary_category"]
        )
    
    # Create dimensions
    dimensions = None
    if legacy_data.get("dimensions") or legacy_data.get("weight"):
        dim_data = legacy_data.get("dimensions", {})
        dimensions = ProductDimensions(
            length=dim_data.get("length"),
            width=dim_data.get("width"),
            height=dim_data.get("height"),
            weight=legacy_data.get("weight")
        )
    
    # Create variation data
    variation_data = VariationData(
        variation_asins=legacy_data.get("variation_asins", [])
    )
    
    # Create sales estimate
    sales_estimate = SalesEstimate(
        monthly_sales=legacy_data.get("monthly_sold", 0),
        daily_sales=legacy_data.get("monthly_sold", 0) / 30.0
    )
    
    # Create marketplace data
    marketplace_data = MarketplaceData(
        buy_box_percentage=legacy_data.get("buy_box_percentage"),
        fba_fees=legacy_data.get("fba_fees")
    )
    
    # Create data quality metrics
    data_quality = DataQualityMetrics(
        overall_score=legacy_data.get("data_quality_score", 0.0),
        validation_errors=legacy_data.get("validation_errors", [])
    )
    
    # Handle datetime
    last_updated = legacy_data.get("last_updated")
    if isinstance(last_updated, str):
        last_updated = datetime.fromisoformat(last_updated)
    elif not isinstance(last_updated, datetime):
        last_updated = datetime.now()
    
    return EnhancedProductData(
        asin=legacy_data["asin"],
        title=legacy_data["title"],
        brand=legacy_data.get("brand"),
        manufacturer=legacy_data.get("manufacturer"),
        product_group=legacy_data.get("product_group"),
        description=legacy_data.get("description"),
        current_price=legacy_data.get("current_price"),
        avg_price_30d=legacy_data.get("avg_price_30d"),
        avg_price_90d=legacy_data.get("avg_price_90d"),
        lowest_price_30d=legacy_data.get("lowest_price_30d"),
        highest_price_30d=legacy_data.get("highest_price_30d"),
        bsr_current=legacy_data.get("bsr_current"),
        bsr_avg_30d=legacy_data.get("bsr_avg_30d"),
        bsr_avg_90d=legacy_data.get("bsr_avg_90d"),
        review_data=review_data,
        category_hierarchy=category_hierarchy,
        images=legacy_data.get("images", []),
        features=legacy_data.get("features", []),
        dimensions=dimensions,
        package_quantity=legacy_data.get("package_quantity", 1),
        variation_data=variation_data,
        sales_estimate=sales_estimate,
        marketplace_data=marketplace_data,
        data_quality=data_quality,
        last_updated=last_updated,
        raw_stats_current=legacy_data.get("raw_stats_current", []),
        raw_stats_avg=legacy_data.get("raw_stats_avg", []),
        additional_data=legacy_data.get("additional_data", {})
    )


def create_mock_product_data(asin: str, **kwargs) -> EnhancedProductData:
    """Create mock product data for testing purposes.
    
    Args:
        asin: Product ASIN
        **kwargs: Override values for specific fields
        
    Returns:
        EnhancedProductData with realistic mock values
    """
    import random
    
    # Generate realistic mock data
    mock_data = {
        "asin": asin,
        "title": kwargs.get("title", f"Sample Product {asin}"),
        "brand": kwargs.get("brand", "Sample Brand"),
        "current_price": kwargs.get("current_price", round(random.uniform(10, 100), 2)),
        "bsr_current": kwargs.get("bsr_current", random.randint(1000, 100000)),
        "review_data": ReviewData(
            review_count=kwargs.get("review_count", random.randint(10, 1000)),
            rating=kwargs.get("rating", round(random.uniform(3.0, 5.0), 1))
        ),
        "sales_estimate": SalesEstimate(
            monthly_sales=kwargs.get("monthly_sales", random.randint(10, 500))
        ),
        "marketplace_data": MarketplaceData(
            seller_count=kwargs.get("seller_count", random.randint(1, 50))
        )
    }
    
    # Override with any provided kwargs
    mock_data.update(kwargs)
    
    # Create the product
    product = EnhancedProductData(**mock_data)
    product.calculate_data_quality_score()
    
    return product