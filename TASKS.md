-- Implementation Plan ---
Here's a detailed plan to create and implement the `CompetitionLvl` and `ProfitabilityTier` enums, along with other necessary class adjustments and improvements.

**Part 1: Implementation Plan for `CompetitionLvl` and `ProfitabilityTier` Enums**

**Goal:** Introduce type-safe enums for competition level and profitability tier, and integrate them consistently across the `Niche` model and API responses.

**Step 1: Define the Enums in `src/kdp_strategist/models/niche_model.py`**
*   Add the following `Enum` definitions at the top of the file, alongside `NicheCategory`:
    ```python
    # src/kdp_strategist/models/niche_model.py

    # ... existing imports ...
    from enum import Enum

    class CompetitionLevel(Enum):
        """Categorical representation of market competition."""
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"

    class ProfitabilityTier(Enum):
        """Categorical representation of niche profitability."""
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"

    class RiskLevel(Enum): # NEW: Introduce a RiskLevel enum for consistency
        """Categorical representation of niche risk."""
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        VERY_HIGH = "very_high"
    ```

**Step 2: Update the `Niche` Dataclass in `src/kdp_strategist/models/niche_model.py`**

*   **Rename Numeric Score Fields:** To avoid confusion with the new enums, rename `competition_score` to `competition_score_numeric` and `profitability_score` to `profitability_score_numeric`. These will continue to store the raw 0-100 scores.
*   **Add New Enum Fields:** Introduce `competition_level: CompetitionLevel` and `profitability_tier: ProfitabilityTier`.
*   **Add Missing Fields from Usage:** Based on how `Niche` objects are constructed in `niche_discovery.py` and `stress_testing.py`, add `primary_keyword`, `trend_analysis_data`, `competitor_analysis_data`.
*   **Standardize `analysis_date`:** Ensure the field is consistently named `analysis_date` (as it's already in `Niche` but sometimes referred to as `last_updated`).
*   **Update `__post_init__` for Auto-Assignment:** Modify `__post_init__` to automatically assign `competition_level` and `profitability_tier` based on their respective `_numeric` scores if they are initialized.
*   **Update Property Methods:** Adjust `overall_score` and `risk_level` properties to use the renamed numeric score fields and the new `RiskLevel` enum. Remove `is_profitable` as `profitability_tier` covers this.
*   **Update `to_dict` and `from_dict`:** Ensure proper serialization/deserialization of the new enum fields (to `.value` for serialization, from string back to `Enum` for deserialization) and the nested `TrendAnalysis` object.

    ```python
    # src/kdp_strategist/models/niche_model.py

    # ... existing imports including TrendAnalysis (from src.kdp_strategist.models.trend_model)

    # ... NicheCategory, CompetitionLevel, ProfitabilityTier, RiskLevel Enums ...

    @dataclass
    class Niche:
        # Core identification
        category: str # Consider making this NicheCategory if strict
        primary_keyword: str # Added: crucial for identification, used in discovery/testing
        subcategory: str = ""
        keywords: List[str] = field(default_factory=list)

        # Raw Numeric Scores (0-100 scale)
        competition_score_numeric: float = 0.0 # Renamed
        profitability_score_numeric: float = 0.0 # Renamed
        market_size_score: float = 0.0
        confidence_score: float = 0.0

        # Categorical Levels (derived from numeric scores)
        competition_level: CompetitionLevel = CompetitionLevel.MEDIUM # NEW field
        profitability_tier: ProfitabilityTier = ProfitabilityTier.MEDIUM # NEW field

        # Detailed Analysis Data (store objects or dicts for flexibility)
        trend_analysis_data: Optional[TrendAnalysis] = None # Renamed, store TrendAnalysis object
        competitor_analysis_data: Dict[str, Any] = field(default_factory=dict) # Added, matches usage
        seasonal_factors: Dict[str, float] = field(default_factory=dict)
        content_gaps: List[str] = field(default_factory=list)

        # Other relevant niche attributes
        recommended_price_range: Tuple[float, float] = (9.99, 19.99)
        top_competitors: List[str] = field(default_factory=list) # ASINs

        # Metadata
        analysis_date: datetime = field(default_factory=datetime.now)
        additional_data: Dict[str, Any] = field(default_factory=dict)

        def __post_init__(self):
            self._validate_scores()
            self._validate_keywords()
            self._validate_price_range()
            # Auto-assign categorical levels if numeric scores are provided
            if self.competition_score_numeric != 0.0:
                self.competition_level = self._determine_competition_level(self.competition_score_numeric)
            if self.profitability_score_numeric != 0.0:
                self.profitability_tier = self._determine_profitability_tier(self.profitability_score_numeric)

        # Static methods to determine enum from numeric score (can be moved outside if preferred)
        @staticmethod
        def _determine_competition_level(score: float) -> CompetitionLevel:
            if score <= 30: return CompetitionLevel.LOW
            elif score <= 60: return CompetitionLevel.MEDIUM
            else: return CompetitionLevel.HIGH

        @staticmethod
        def _determine_profitability_tier(score: float) -> ProfitabilityTier:
            if score >= 80: return ProfitabilityTier.HIGH
            elif score >= 60: return ProfitabilityTier.MEDIUM
            else: return ProfitabilityTier.LOW

        @property
        def overall_score(self) -> float:
            # Use numeric score fields
            profitability_weight = 0.4
            competition_weight = 0.3
            market_size_weight = 0.2
            confidence_weight = 0.1
            adjusted_competition = 100 - self.competition_score_numeric
            weighted_score = (
                self.profitability_score_numeric * profitability_weight +
                adjusted_competition * competition_weight +
                self.market_size_score * market_size_weight +
                self.confidence_score * confidence_weight
            )
            return round(weighted_score, 2)

        # Removed `is_profitable` property as `profitability_tier` provides this classification

        @property
        def risk_level(self) -> RiskLevel:
            """Assess risk level for this niche, returning a RiskLevel enum."""
            if (self.competition_score_numeric <= 30 and self.confidence_score >= 80 and
                self.profitability_tier == ProfitabilityTier.HIGH):
                return RiskLevel.LOW
            elif (self.competition_score_numeric <= 60 and self.confidence_score >= 60 and
                  self.profitability_tier in [ProfitabilityTier.HIGH, ProfitabilityTier.MEDIUM]):
                return RiskLevel.MEDIUM
            elif self.overall_score >= 40:
                return RiskLevel.HIGH
            else:
                return RiskLevel.VERY_HIGH

        def to_dict(self) -> Dict[str, Any]:
            data = {
                "category": self.category,
                "subcategory": self.subcategory,
                "primary_keyword": self.primary_keyword,
                "keywords": self.keywords,
                "competition_score_numeric": self.competition_score_numeric,
                "profitability_score_numeric": self.profitability_score_numeric,
                "confidence_score": self.confidence_score,
                "market_size_score": self.market_size_score,
                "competition_level": self.competition_level.value, # Serialize enum value
                "profitability_tier": self.profitability_tier.value, # Serialize enum value
                "trend_analysis_data": self.trend_analysis_data.to_dict() if self.trend_analysis_data else None, # Serialize nested dataclass
                "competitor_analysis_data": self.competitor_analysis_data,
                "seasonal_factors": self.seasonal_factors,
                "content_gaps": self.content_gaps,
                "recommended_price_range": list(self.recommended_price_range),
                "top_competitors": self.top_competitors,
                "analysis_date": self.analysis_date.isoformat(),
                "additional_data": self.additional_data,
                "overall_score": self.overall_score, # Include computed properties
                "risk_level": self.risk_level.value, # Include computed properties
            }
            return data

        @classmethod
        def from_dict(cls, data: Dict[str, Any]) -> "Niche":
            # Handle datetime, tuple conversions
            if "analysis_date" in data and isinstance(data["analysis_date"], str):
                data["analysis_date"] = datetime.fromisoformat(data["analysis_date"])
            if "recommended_price_range" in data and isinstance(data["recommended_price_range"], list):
                data["recommended_price_range"] = tuple(data["recommended_price_range"])

            # Deserialize enums
            if "competition_level" in data and isinstance(data["competition_level"], str):
                data["competition_level"] = CompetitionLevel(data["competition_level"])
            if "profitability_tier" in data and isinstance(data["profitability_tier"], str):
                data["profitability_tier"] = ProfitabilityTier(data["profitability_tier"])
            if "risk_level" in data and isinstance(data["risk_level"], str): # Deserialize if stored
                data.pop("risk_level") # This is a computed property, remove before init

            # Deserialize nested TrendAnalysis object
            if "trend_analysis_data" in data and data["trend_analysis_data"] is not None:
                data["trend_analysis_data"] = TrendAnalysis.from_dict(data["trend_analysis_data"])
            elif "trend_analysis" in data: # Handle old naming if exists
                 if data["trend_analysis"] is not None:
                    data["trend_analysis_data"] = TrendAnalysis.from_dict(data["trend_analysis"])
                 data.pop("trend_analysis") # Remove old key

            # Rename old score keys if present
            if 'competition_score' in data and 'competition_score_numeric' not in data:
                data['competition_score_numeric'] = data.pop('competition_score')
            if 'profitability_score' in data and 'profitability_score_numeric' not in data:
                data['profitability_score_numeric'] = data.pop('profitability_score')

            # Remove computed properties and old redundant fields before passing to constructor
            computed_fields = {"overall_score"}
            filtered_data = {k: v for k, v in data.items() if k not in computed_fields}
            filtered_data.pop('trend_direction', None) # Remove if it was serialized
            filtered_data.pop('estimated_monthly_searches', None) # Remove if it was serialized

            return cls(**filtered_data)
    ```

**Step 3: Update API Response Model in `api/models/responses.py`**

*   Import `CompetitionLevel` and `ProfitabilityTier` from the `niche_model.py`.
*   Modify `NicheData` within `responses.py` to use these enums for `competition_level` and add a new `profitability_tier` field. Also, `NicheData.score` should clearly map to `profitability_score_numeric`.

    ```python
    # api/models/responses.py

    # ... existing imports ...
    from typing import List, Optional, Dict, Any, Union
    from datetime import datetime
    from pydantic import BaseModel, Field

    # Import the new Enums from niche_model.py
    from src.kdp_strategist.models.niche_model import CompetitionLevel, ProfitabilityTier, RiskLevel

    class NicheData(BaseModel):
        """Model for individual niche data."""
        name: str = Field(..., description="Niche name (primary keyword)")
        # Map to profitability_score_numeric
        score: float = Field(..., description="Profitability score (0-100)")
        # Use the Enum for competition_level
        competition_level: CompetitionLevel = Field(..., description="Competition level: low, medium, high")
        # Add profitability_tier field using the Enum
        profitability_tier: ProfitabilityTier = Field(..., description="Profitability tier: low, medium, high")
        risk_level: RiskLevel = Field(..., description="Overall risk level for the niche") # Add risk_level
        search_volume: int = Field(..., description="Monthly search volume") # This will be derived
        trend_direction: str = Field(..., description="Trend direction: rising, stable, declining") # This will be derived
        keywords: List[str] = Field(default=[], description="Related keywords")
        estimated_revenue: Optional[float] = Field(None, description="Estimated monthly revenue")
        seasonality: Optional[Dict[str, float]] = Field(None, description="Seasonal patterns")
        barriers_to_entry: List[str] = Field(default=[], description="Market barriers")
    ```

**Step 4: Update `src/kdp_strategist/agent/tools/niche_discovery.py`**

*   **Import Enums:** Import `CompetitionLevel` and `ProfitabilityTier` (and `RiskLevel` if used for calculations here) from `src.kdp_strategist.models.niche_model`.
*   **Modify `_generate_niche_candidates`:**
    *   When creating `Niche` objects, pass the raw `TrendAnalysis` object to `trend_analysis_data`.
    *   Pass the raw `competition` dict to `competitor_analysis_data`.
    *   Pass the calculated numeric scores (`profitability_score_numeric`, `competition_score_numeric`). The `Niche.__post_init__` will then set the categorical enum fields.
    *   Remove `last_updated` from the `Niche` constructor call; `analysis_date` has a `default_factory`.
    ```python
    # src/kdp_strategist/agent/tools/niche_discovery.py

    # ... imports
    from src.kdp_strategist.models.niche_model import Niche, CompetitionLevel, ProfitabilityTier, RiskLevel # Add RiskLevel
    from src.kdp_strategist.models.trend_model import TrendAnalysis, TrendDirection, TrendStrength

    # ... in _generate_niche_candidates
    # ...
    niche = Niche(
        category=categories[0] if categories else "Books & Journals",
        primary_keyword=keyword,
        keywords=[keyword] + trend_analysis.related_queries[:10],
        trend_analysis_data=trend_analysis, # Pass TrendAnalysis object directly
        competitor_analysis_data=competition, # Pass competitor data as dict
        market_size_score=_estimate_market_size(trend_analysis, competition),
        seasonal_factors=trend_analysis.seasonal_patterns,
        # Calculate and assign numeric scores directly during construction
        profitability_score_numeric=NicheScorer.calculate_profitability_score({
            "trend_analysis": trend_analysis,
            "competition_data": competition,
            "market_metrics": {"estimated_search_volume": _estimate_market_size(trend_analysis, competition) * 100},
            "seasonal_patterns": trend_analysis.seasonal_patterns,
            "content_analysis": {"identified_gaps": 5}
        }),
        competition_score_numeric=NicheScorer._score_competition_level(competition) or 0.0,
        # `competition_level` and `profitability_tier` will be set in Niche's __post_init__
    )
    niche_candidates.append(niche)
    ```
*   **Modify `_score_and_rank_niches`:**
    *   This function currently assigns `niche.competition_score = CompetitionLevel.LOW` and `niche.profitability_tier = ProfitabilityTier.HIGH`. This is correct based on the *new* `Niche` model design where `competition_level` and `profitability_tier` are enum fields. The numeric scores are already calculated in `_generate_niche_candidates` or will be updated here.
    *   Ensure all score calculations use `_numeric` fields.
    *   Explicitly assign `niche.competition_level` and `niche.profitability_tier` based on the calculated numeric scores, even though `__post_init__` does it, for clarity and control within the scoring logic.
    ```python
    # src/kdp_strategist/agent/tools/niche_discovery.py

    # ... in _score_and_rank_niches
    for niche in niche_candidates:
        # Re-calculate or confirm numeric competition score
        niche.competition_score_numeric = NicheScorer._score_competition_level(niche.competitor_analysis_data) or 0.0

        # Set the categorical competition level based on numeric score
        niche.competition_level = Niche._determine_competition_level(niche.competition_score_numeric)

        # Calculate the numeric profitability score (ensure it uses the renamed fields internally)
        niche_data_for_scoring = {
            "trend_analysis": niche.trend_analysis_data,
            "competition_data": niche.competitor_analysis_data,
            "market_metrics": {"estimated_search_volume": niche.market_size_score * 100},
            "seasonal_patterns": niche.seasonal_factors,
            "content_analysis": {"identified_gaps": 5}
        }
        niche.profitability_score_numeric = NicheScorer.calculate_profitability_score(niche_data_for_scoring)

        # Set the categorical profitability tier based on numeric score
        niche.profitability_tier = Niche._determine_profitability_tier(niche.profitability_score_numeric)

        # Apply minimum score filter (using numeric score)
        if niche.profitability_score_numeric >= min_score:
            scored_niches.append(niche)

    # Sort by profitability score_numeric (descending)
    scored_niches.sort(key=lambda n: n.profitability_score_numeric, reverse=True)
    ```
*   **Modify `_generate_recommendations`:**
    *   Access `profitability_score_numeric` and `competition_level.value` for recommendations.
    ```python
    # src/kdp_strategist/agent/tools/niche_discovery.py

    # ... in _generate_recommendations
    recommendations = {
        "primary_recommendation": {
            "niche": best_niche.primary_keyword,
            "score": best_niche.profitability_score_numeric, # Use numeric score
            "reason": f"Highest profitability score with {best_niche.competition_level.value} competition" # Use enum .value
        },
        "quick_wins": [],
        "long_term_opportunities": [],
        "market_insights": {
            "avg_profitability_score": sum(n.profitability_score_numeric for n in all_scored_niches) / len(all_scored_niches),
            "competition_distribution": {
                "low": len([n for n in all_scored_niches if n.competition_level == CompetitionLevel.LOW]),
                "medium": len([n for n in all_scored_niches if n.competition_level == CompetitionLevel.MEDIUM]),
                "high": len([n for n in all_scored_niches if n.competition_level == CompetitionLevel.HIGH])
            }
        }
    }
    # ...
    for niche in top_niches[:5]:
        if niche.competition_level == CompetitionLevel.LOW and niche.profitability_score_numeric >= 60:
            # ...
    # ...
    for niche in top_niches[:10]:
        if (niche.profitability_score_numeric >= 75 and
            niche.trend_analysis_data and # Use the renamed field
            niche.trend_analysis_data.direction == TrendDirection.RISING): # Use the enum directly
            # ...
    ```

**Step 5: Update `src/kdp_strategist/agent/tools/stress_testing.py`**

*   **Import Enums:** Import `CompetitionLevel`, `ProfitabilityTier`, `RiskLevel` from `src.kdp_strategist.models.niche_model`.
*   **Modify `_create_niche_for_testing`:**
    *   Correctly initialize the `Niche` object with `primary_keyword`, `trend_analysis_data`, `competitor_analysis_data`.
    *   Populate the renamed numeric scores: `competition_score_numeric` and `profitability_score_numeric`.
    *   The `Niche.__post_init__` will handle setting the `competition_level` and `profitability_tier` enums.
    ```python
    # src/kdp_strategist/agent/tools/stress_testing.py

    # ... imports
    from src.kdp_strategist.models.niche_model import Niche, CompetitionLevel, ProfitabilityTier, RiskLevel

    async def _create_niche_for_testing(
        trends_client: TrendsClient,
        keepa_client: KeepaClient,
        cache_manager: CacheManager,
        keyword: str
    ) -> Optional[Niche]:
        # ...
        niche = Niche(
            category=f"{keyword} books",
            primary_keyword=keyword, # Now a field in Niche
            keywords=[keyword, f"{keyword} guide", f"{keyword} tips"],
            # Assign numeric scores
            competition_score_numeric=random.uniform(30, 80),
            profitability_score_numeric=random.uniform(40, 85),
            market_size_score=random.uniform(35, 75),
            confidence_score=random.uniform(50, 90),
            # Pass TrendAnalysis object and competitor_data dict directly
            trend_analysis_data=trend_analysis,
            competitor_analysis_data=competitor_data,
            recommended_price_range=(competitor_data["avg_price"] * 0.8, competitor_data["avg_price"] * 1.2),
            content_gaps=["beginner guides", "advanced techniques", "case studies"],
            seasonal_factors={"volatility": random.uniform(0.2, 0.8)},
            # `competition_level` and `profitability_tier` will be set in Niche's __post_init__
        )
        return niche
    ```
*   **Modify `StressTester.simulate_scenario` and `_calculate_stress_impact`:** Use `niche.competition_score_numeric` and `niche.profitability_score_numeric` for calculations.
*   **Modify `StressTestReport` and `StressTestingResponse` output:**
    *   The `overall_resilience` and `risk_profile` calculations should reflect the new `RiskLevel` enum.
    *   Ensure the JSON output references the correct numeric score names and enum values (`.value`).
    ```python
    # src/kdp_strategist/agent/tools/stress_testing.py

    # ... in simulate_scenario
    # Replace niche.competition_score with niche.competition_score_numeric etc.
    # ... in StressTestReport and StressTestingResponse compilation
    "baseline_niche": {
        "overall_score": niche.overall_score,
        "profitability_score": niche.profitability_score_numeric, # Use numeric
        "competition_score": niche.competition_score_numeric, # Use numeric
        "market_size_score": niche.market_size_score,
        "confidence_score": niche.confidence_score,
        "competition_level": niche.competition_level.value, # Include categorical
        "profitability_tier": niche.profitability_tier.value, # Include categorical
    },
    "stress_test_summary": {
        # ...
        "risk_profile": overall_risk_profile.value, # Use enum .value
        # ...
    }
    ```
*   **Modify `_determine_risk_profile`:** Change return type to `RiskLevel`.
    ```python
    # src/kdp_strategist/agent/tools/stress_testing.py

    def _determine_risk_profile(scenario_results: List[ScenarioResult], overall_resilience: float) -> RiskLevel:
        # ...
        if overall_resilience >= 80 and high_impact_scenarios <= 1:
            return RiskLevel.LOW
        elif overall_resilience >= 60 and high_impact_scenarios <= 3:
            return RiskLevel.MEDIUM
        elif overall_resilience >= 40:
            return RiskLevel.HIGH
        else:
            return RiskLevel.VERY_HIGH