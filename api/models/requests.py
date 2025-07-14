"""Request models for KDP Strategist API.

These Pydantic models define the structure of incoming API requests
from the React frontend to the FastAPI backend.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class NicheDiscoveryRequest(BaseModel):
    """Request model for niche discovery endpoint."""
    base_keywords: List[str] = Field(
        ..., 
        description="List of base keywords to analyze",
        min_items=1,
        max_items=10
    )
    max_niches: int = Field(
        default=5,
        description="Maximum number of niches to return",
        ge=1,
        le=20
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional filters for niche discovery"
    )
    
    @validator('base_keywords')
    def validate_keywords(cls, v):
        if not v:
            raise ValueError('At least one keyword is required')
        # Clean and validate keywords
        cleaned = [kw.strip().lower() for kw in v if kw.strip()]
        if not cleaned:
            raise ValueError('Keywords cannot be empty after cleaning')
        return cleaned


class CompetitorAnalysisRequest(BaseModel):
    """Request model for competitor analysis endpoint."""
    asins: List[str] = Field(
        ...,
        description="List of Amazon ASINs to analyze",
        min_items=1,
        max_items=20
    )
    analysis_depth: str = Field(
        default="standard",
        description="Depth of analysis: basic, standard, or detailed"
    )
    include_trends: bool = Field(
        default=True,
        description="Whether to include trend analysis"
    )
    
    @validator('asins')
    def validate_asins(cls, v):
        # Basic ASIN validation (10 characters, alphanumeric)
        cleaned_asins = []
        for asin in v:
            asin = asin.strip().upper()
            if len(asin) != 10:
                raise ValueError(f'ASIN {asin} must be exactly 10 characters')
            if not asin.isalnum():
                raise ValueError(f'ASIN {asin} must be alphanumeric')
            cleaned_asins.append(asin)
        return cleaned_asins
    
    @validator('analysis_depth')
    def validate_analysis_depth(cls, v):
        if v not in ['basic', 'standard', 'detailed']:
            raise ValueError('Analysis depth must be basic, standard, or detailed')
        return v


class ListingGenerationRequest(BaseModel):
    """Request model for listing generation endpoint."""
    niche: str = Field(
        ...,
        description="Target niche for listing generation",
        min_length=3,
        max_length=100
    )
    target_audience: Optional[str] = Field(
        default=None,
        description="Specific target audience",
        max_length=200
    )
    book_type: str = Field(
        default="paperback",
        description="Type of book: paperback, ebook, or hardcover"
    )
    include_keywords: bool = Field(
        default=True,
        description="Whether to include keyword optimization"
    )
    tone: str = Field(
        default="professional",
        description="Tone for the listing: professional, casual, or creative"
    )
    
    @validator('book_type')
    def validate_book_type(cls, v):
        if v not in ['paperback', 'ebook', 'hardcover']:
            raise ValueError('Book type must be paperback, ebook, or hardcover')
        return v
    
    @validator('tone')
    def validate_tone(cls, v):
        if v not in ['professional', 'casual', 'creative']:
            raise ValueError('Tone must be professional, casual, or creative')
        return v


class TrendValidationRequest(BaseModel):
    """Request model for trend validation endpoint."""
    keywords: List[str] = Field(
        ...,
        description="Keywords to validate trends for",
        min_items=1,
        max_items=15
    )
    timeframe: str = Field(
        default="12m",
        description="Timeframe for trend analysis: 1m, 3m, 6m, 12m, or 24m"
    )
    geo: str = Field(
        default="US",
        description="Geographic region for trend analysis"
    )
    include_seasonality: bool = Field(
        default=True,
        description="Whether to include seasonality analysis"
    )
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        if v not in ['1m', '3m', '6m', '12m', '24m']:
            raise ValueError('Timeframe must be 1m, 3m, 6m, 12m, or 24m')
        return v
    
    @validator('keywords')
    def validate_keywords(cls, v):
        cleaned = [kw.strip().lower() for kw in v if kw.strip()]
        if not cleaned:
            raise ValueError('At least one valid keyword is required')
        return cleaned


class StressTestingRequest(BaseModel):
    """Request model for stress testing endpoint."""
    niche: str = Field(
        ...,
        description="Niche to stress test",
        min_length=3,
        max_length=100
    )
    test_scenarios: List[str] = Field(
        default=["market_saturation", "seasonal_decline", "trend_reversal"],
        description="List of stress test scenarios to run"
    )
    severity_level: str = Field(
        default="moderate",
        description="Severity level: mild, moderate, or severe"
    )
    include_recommendations: bool = Field(
        default=True,
        description="Whether to include mitigation recommendations"
    )
    
    @validator('severity_level')
    def validate_severity_level(cls, v):
        if v not in ['mild', 'moderate', 'severe']:
            raise ValueError('Severity level must be mild, moderate, or severe')
        return v
    
    @validator('test_scenarios')
    def validate_test_scenarios(cls, v):
        valid_scenarios = [
            "market_saturation", "seasonal_decline", "trend_reversal",
            "competition_increase", "demand_drop", "keyword_shift"
        ]
        for scenario in v:
            if scenario not in valid_scenarios:
                raise ValueError(f'Invalid scenario: {scenario}. Must be one of {valid_scenarios}')
        return v


class ExportRequest(BaseModel):
    """Request model for export functionality."""
    data_type: str = Field(
        ...,
        description="Type of data to export: niche, competitor, listing, trend, or stress"
    )
    format: str = Field(
        ...,
        description="Export format: json, csv, or docx"
    )
    data: Dict[str, Any] = Field(
        ...,
        description="Data to export"
    )
    filename: Optional[str] = Field(
        default=None,
        description="Custom filename for export"
    )
    
    @validator('data_type')
    def validate_data_type(cls, v):
        if v not in ['niche', 'competitor', 'listing', 'trend', 'stress']:
            raise ValueError('Data type must be niche, competitor, listing, trend, or stress')
        return v
    
    @validator('format')
    def validate_format(cls, v):
        if v not in ['json', 'csv', 'docx']:
            raise ValueError('Format must be json, csv, or docx')
        return v