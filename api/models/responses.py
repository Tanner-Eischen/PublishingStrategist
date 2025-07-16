"""Response models for KDP Strategist API.

These Pydantic models define the structure of API responses
sent from the FastAPI backend to the React frontend.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field
 # Import the new Enums from niche_model.py
from src.kdp_strategist.models.niche_model import CompetitionLevel, ProfitabilityTier, RiskLevel


class ChartData(BaseModel):
    """Model for chart data visualization."""
    type: str = Field(..., description="Chart type: line, bar, pie, scatter")
    title: str = Field(..., description="Chart title")
    data: List[Dict[str, Any]] = Field(..., description="Chart data points")
    labels: Optional[List[str]] = Field(None, description="Chart labels")
    colors: Optional[List[str]] = Field(None, description="Chart colors")
    options: Optional[Dict[str, Any]] = Field(None, description="Chart options")


class AnalysisMetadata(BaseModel):
    """Metadata for analysis operations."""
    execution_time: float = Field(..., description="Execution time in seconds")
    timestamp: datetime = Field(default_factory=datetime.now, description="Analysis timestamp")
    tool_version: str = Field(default="1.0.0", description="Tool version used")
    data_sources: List[str] = Field(default=[], description="Data sources used")
    cache_hit: bool = Field(default=False, description="Whether result was cached")
    warnings: List[str] = Field(default=[], description="Analysis warnings")


class NicheData(BaseModel):
        """Model for individual niche data."""
        name: str = Field(..., description="Niche name (primary keyword)")
        # Map to profitability_score_numeric
        score: float = Field(..., description="Profitability score (0-100)")
        # Use the Enum for competition_level
        competition_level: CompetitionLevel = Field(
            ..., description="Categorical competition level"
        )
        # Add profitability_tier field using the Enum
        profitability_tier: ProfitabilityTier = Field(
            ..., description="Categorical profitability tier"
        )
        risk_level: RiskLevel = Field(..., description="Overall risk level for the niche") # Add risk_level
        search_volume: int = Field(..., description="Monthly search volume") # This will be derived
        trend_direction: str = Field(..., description="Trend direction: rising, stable, declining") # This will be derived
        keywords: List[str] = Field(default=[], description="Related keywords")
        estimated_revenue: Optional[float] = Field(None, description="Estimated monthly revenue")
        seasonality: Optional[Dict[str, float]] = Field(None, description="Seasonal patterns")
        barriers_to_entry: List[str] = Field(default=[], description="Market barriers")


class NicheDiscoveryResponse(BaseModel):
    """Response model for niche discovery."""
    status: str = Field(default="success", description="Response status")
    niches: List[NicheData] = Field(..., description="Discovered niches")
    total_analyzed: int = Field(..., description="Total niches analyzed")
    analysis_metadata: AnalysisMetadata = Field(..., description="Analysis metadata")
    charts: List[ChartData] = Field(default=[], description="Visualization data")
    export_options: List[str] = Field(default=["json", "csv"], description="Available export formats")
    recommendations: List[str] = Field(default=[], description="Strategic recommendations")


class CompetitorData(BaseModel):
    """Model for individual competitor data."""
    asin: str = Field(..., description="Amazon ASIN")
    title: str = Field(..., description="Product title")
    author: Optional[str] = Field(None, description="Author name")
    price: Optional[float] = Field(None, description="Current price")
    rank: Optional[int] = Field(None, description="Best seller rank")
    rating: Optional[float] = Field(None, description="Average rating")
    review_count: Optional[int] = Field(None, description="Number of reviews")
    publication_date: Optional[str] = Field(None, description="Publication date")
    page_count: Optional[int] = Field(None, description="Number of pages")
    categories: List[str] = Field(default=[], description="Product categories")
    keywords: List[str] = Field(default=[], description="Identified keywords")
    strengths: List[str] = Field(default=[], description="Competitive strengths")
    weaknesses: List[str] = Field(default=[], description="Competitive weaknesses")
    market_share: Optional[float] = Field(None, description="Estimated market share")


class CompetitorAnalysisResponse(BaseModel):
    """Response model for competitor analysis."""
    status: str = Field(default="success", description="Response status")
    competitors: List[CompetitorData] = Field(..., description="Competitor analysis data")
    market_overview: Dict[str, Any] = Field(..., description="Market overview statistics")
    analysis_metadata: AnalysisMetadata = Field(..., description="Analysis metadata")
    charts: List[ChartData] = Field(default=[], description="Visualization data")
    export_options: List[str] = Field(default=["json", "csv"], description="Available export formats")
    insights: List[str] = Field(default=[], description="Key insights")
    opportunities: List[str] = Field(default=[], description="Market opportunities")


class ListingData(BaseModel):
    """Model for generated listing data."""
    title: str = Field(..., description="Optimized book title")
    subtitle: Optional[str] = Field(None, description="Book subtitle")
    description: str = Field(..., description="Book description")
    keywords: List[str] = Field(..., description="Optimized keywords")
    categories: List[str] = Field(..., description="Recommended categories")
    target_price: Optional[float] = Field(None, description="Recommended price")
    bullet_points: List[str] = Field(default=[], description="Key selling points")
    author_bio: Optional[str] = Field(None, description="Suggested author bio")
    back_cover_text: Optional[str] = Field(None, description="Back cover description")
    marketing_hooks: List[str] = Field(default=[], description="Marketing angles")


class ListingGenerationResponse(BaseModel):
    """Response model for listing generation."""
    status: str = Field(default="success", description="Response status")
    listing: ListingData = Field(..., description="Generated listing data")
    optimization_score: float = Field(..., description="SEO optimization score (0-100)")
    analysis_metadata: AnalysisMetadata = Field(..., description="Analysis metadata")
    export_options: List[str] = Field(default=["json", "docx"], description="Available export formats")
    seo_recommendations: List[str] = Field(default=[], description="SEO improvement suggestions")
    compliance_check: Dict[str, bool] = Field(default={}, description="KDP compliance status")


class TrendData(BaseModel):
    """Model for trend analysis data."""
    keyword: str = Field(..., description="Analyzed keyword")
    trend_score: float = Field(..., description="Trend strength score (0-100)")
    direction: str = Field(..., description="Trend direction: rising, stable, declining")
    volatility: float = Field(..., description="Trend volatility (0-100)")
    seasonal_pattern: Optional[Dict[str, float]] = Field(None, description="Seasonal patterns")
    peak_months: List[str] = Field(default=[], description="Peak search months")
    related_queries: List[str] = Field(default=[], description="Related search queries")
    forecast: Optional[Dict[str, float]] = Field(None, description="3-month forecast")
    confidence_level: float = Field(..., description="Forecast confidence (0-100)")


class TrendValidationResponse(BaseModel):
    """Response model for trend validation."""
    status: str = Field(default="success", description="Response status")
    trends: List[TrendData] = Field(..., description="Trend analysis data")
    overall_trend_health: str = Field(..., description="Overall trend assessment")
    analysis_metadata: AnalysisMetadata = Field(..., description="Analysis metadata")
    charts: List[ChartData] = Field(default=[], description="Visualization data")
    export_options: List[str] = Field(default=["json", "csv"], description="Available export formats")
    recommendations: List[str] = Field(default=[], description="Strategic recommendations")
    risk_factors: List[str] = Field(default=[], description="Identified risk factors")


class StressTestScenario(BaseModel):
    """Model for stress test scenario results."""
    scenario: str = Field(..., description="Stress test scenario name")
    severity: str = Field(..., description="Test severity level")
    impact_score: float = Field(..., description="Impact score (0-100)")
    probability: float = Field(..., description="Scenario probability (0-100)")
    description: str = Field(..., description="Scenario description")
    potential_losses: Optional[float] = Field(None, description="Estimated potential losses")
    mitigation_strategies: List[str] = Field(default=[], description="Mitigation recommendations")
    recovery_time: Optional[str] = Field(None, description="Estimated recovery time")


class StressTestingResponse(BaseModel):
    """Response model for stress testing."""
    status: str = Field(default="success", description="Response status")
    niche: str = Field(..., description="Tested niche")
    overall_resilience: float = Field(..., description="Overall resilience score (0-100)")
    risk_level: RiskLevel = Field(..., description="Risk level: low, medium, high")
    scenarios: List[StressTestScenario] = Field(..., description="Stress test scenarios")
    analysis_metadata: AnalysisMetadata = Field(..., description="Analysis metadata")
    charts: List[ChartData] = Field(default=[], description="Visualization data")
    export_options: List[str] = Field(default=["json", "csv"], description="Available export formats")
    recommendations: List[str] = Field(default=[], description="Risk mitigation recommendations")
    contingency_plans: List[str] = Field(default=[], description="Contingency planning suggestions")


class ExportResponse(BaseModel):
    """Response model for export operations."""
    status: str = Field(default="success", description="Export status")
    download_url: str = Field(..., description="Download URL for exported file")
    filename: str = Field(..., description="Generated filename")
    file_size: int = Field(..., description="File size in bytes")
    format: str = Field(..., description="Export format")
    expires_at: datetime = Field(..., description="Download link expiration")


class ErrorResponse(BaseModel):
    """Response model for API errors."""
    status: str = Field(default="error", description="Response status")
    error_type: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(default="healthy", description="Service status")
    service: str = Field(default="kdp_strategist-api", description="Service name")
    version: str = Field(default="1.0.0", description="API version")
    timestamp: datetime = Field(default_factory=datetime.now, description="Health check timestamp")
    dependencies: Dict[str, str] = Field(default={}, description="Dependency status")
    uptime: Optional[float] = Field(None, description="Service uptime in seconds")