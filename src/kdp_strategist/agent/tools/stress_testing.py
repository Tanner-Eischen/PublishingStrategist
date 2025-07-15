"""Stress Testing Tool.

Performs comprehensive stress testing of niches to assess:
- Market resilience under various scenarios
- Competition pressure tolerance
- Economic downturn impact
- Seasonal volatility effects
- Platform algorithm changes
- Consumer behavior shifts

The tool simulates multiple stress scenarios including:
- Market saturation scenarios
- Economic recession impacts
- Competitive flooding
- Seasonal demand crashes
- Platform policy changes
- Consumer trend shifts
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from statistics import mean, stdev
import random
import math

from ...data.cache_manager import CacheManager
from ...data.trends_client import TrendsClient
from ...data.keepa_client import KeepaClient
from ...models.niche_model import Niche, CompetitionLevel, ProfitabilityTier, RiskLevel
from ...models.trend_model import TrendAnalysis
from .niche_discovery import NicheScorer
from .trend_validation import TrendValidator

logger = logging.getLogger(__name__)


class StressScenario(Enum):
    """Types of stress test scenarios."""
    MARKET_SATURATION = "market_saturation"
    ECONOMIC_DOWNTURN = "economic_downturn"
    COMPETITIVE_FLOODING = "competitive_flooding"
    SEASONAL_CRASH = "seasonal_crash"
    PLATFORM_CHANGES = "platform_changes"
    TREND_REVERSAL = "trend_reversal"
    CONSUMER_SHIFT = "consumer_shift"
    SUPPLY_CHAIN_DISRUPTION = "supply_chain_disruption"


@dataclass
class StressTestParameters:
    """Parameters for stress test scenarios."""
    scenario: StressScenario
    severity: float  # 0.1 (mild) to 1.0 (severe)
    duration_months: int  # How long the stress lasts
    recovery_months: int  # How long to recover
    probability: float  # Likelihood of scenario occurring
    description: str


@dataclass
class ScenarioResult:
    """Result of a single stress test scenario."""
    scenario: StressScenario
    parameters: StressTestParameters
    initial_score: float
    stressed_score: float
    recovery_score: float
    impact_percentage: float
    resilience_score: float
    survival_probability: float
    key_vulnerabilities: List[str]
    mitigation_strategies: List[str]


@dataclass
class StressTestReport:
    """Comprehensive stress test report."""
    niche_keyword: str
    baseline_niche: Niche
    scenario_results: List[ScenarioResult]
    overall_resilience: float
    risk_profile: str
    critical_vulnerabilities: List[str]
    recommended_mitigations: List[str]
    confidence_level: float
    test_timestamp: datetime


class StressTester:
    """Core stress testing engine."""
    
    # Stress test scenarios with default parameters
    DEFAULT_SCENARIOS = {
        StressScenario.MARKET_SATURATION: StressTestParameters(
            scenario=StressScenario.MARKET_SATURATION,
            severity=0.7,
            duration_months=6,
            recovery_months=12,
            probability=0.3,
            description="Market becomes oversaturated with competitors"
        ),
        StressScenario.ECONOMIC_DOWNTURN: StressTestParameters(
            scenario=StressScenario.ECONOMIC_DOWNTURN,
            severity=0.6,
            duration_months=8,
            recovery_months=18,
            probability=0.2,
            description="Economic recession reduces consumer spending"
        ),
        StressScenario.COMPETITIVE_FLOODING: StressTestParameters(
            scenario=StressScenario.COMPETITIVE_FLOODING,
            severity=0.8,
            duration_months=4,
            recovery_months=8,
            probability=0.4,
            description="Sudden influx of new competitors"
        ),
        StressScenario.SEASONAL_CRASH: StressTestParameters(
            scenario=StressScenario.SEASONAL_CRASH,
            severity=0.9,
            duration_months=3,
            recovery_months=6,
            probability=0.5,
            description="Severe seasonal demand drop"
        ),
        StressScenario.PLATFORM_CHANGES: StressTestParameters(
            scenario=StressScenario.PLATFORM_CHANGES,
            severity=0.5,
            duration_months=3,
            recovery_months=9,
            probability=0.3,
            description="Amazon algorithm or policy changes"
        ),
        StressScenario.TREND_REVERSAL: StressTestParameters(
            scenario=StressScenario.TREND_REVERSAL,
            severity=0.8,
            duration_months=12,
            recovery_months=24,
            probability=0.25,
            description="Major trend reversal or consumer preference shift"
        ),
        StressScenario.CONSUMER_SHIFT: StressTestParameters(
            scenario=StressScenario.CONSUMER_SHIFT,
            severity=0.6,
            duration_months=9,
            recovery_months=15,
            probability=0.35,
            description="Consumer behavior and preferences change"
        ),
        StressScenario.SUPPLY_CHAIN_DISRUPTION: StressTestParameters(
            scenario=StressScenario.SUPPLY_CHAIN_DISRUPTION,
            severity=0.4,
            duration_months=2,
            recovery_months=4,
            probability=0.15,
            description="Supply chain or production disruptions"
        )
    }
    
    @classmethod
    def simulate_scenario(
        cls,
        niche: Niche,
        scenario_params: StressTestParameters,
        trend_analysis: Optional[TrendAnalysis] = None
    ) -> ScenarioResult:
        """Simulate a single stress test scenario."""
        initial_score = niche.overall_score
        
        # Calculate stress impact based on scenario type and niche characteristics
        stress_impact = cls._calculate_stress_impact(
            niche, scenario_params, trend_analysis
        )
        
        # Apply stress to niche score
        stressed_score = initial_score * (1 - stress_impact)
        stressed_score = max(0, stressed_score)
        
        # Calculate recovery score
        recovery_factor = cls._calculate_recovery_factor(
            niche, scenario_params, stress_impact
        )
        recovery_score = stressed_score + (initial_score - stressed_score) * recovery_factor
        recovery_score = min(initial_score, recovery_score)
        
        # Calculate impact percentage
        impact_percentage = (initial_score - stressed_score) / initial_score * 100
        
        # Calculate resilience score (how well it maintains performance)
        resilience_score = (stressed_score / initial_score) * 100
        
        # Calculate survival probability
        survival_probability = cls._calculate_survival_probability(
            stressed_score, recovery_score, scenario_params
        )
        
        # Identify vulnerabilities
        vulnerabilities = cls._identify_vulnerabilities(
            niche, scenario_params, stress_impact
        )
        
        # Generate mitigation strategies
        mitigations = cls._generate_mitigation_strategies(
            niche, scenario_params, vulnerabilities
        )
        
        return ScenarioResult(
            scenario=scenario_params.scenario,
            parameters=scenario_params,
            initial_score=round(initial_score, 1),
            stressed_score=round(stressed_score, 1),
            recovery_score=round(recovery_score, 1),
            impact_percentage=round(impact_percentage, 1),
            resilience_score=round(resilience_score, 1),
            survival_probability=round(survival_probability, 2),
            key_vulnerabilities=vulnerabilities,
            mitigation_strategies=mitigations
        )
    
    @classmethod
    def _calculate_stress_impact(
        cls,
        niche: Niche,
        scenario_params: StressTestParameters,
        trend_analysis: Optional[TrendAnalysis] = None
    ) -> float:
        """Calculate the impact of stress on the niche."""
        base_impact = scenario_params.severity * 0.5  # Base 50% max impact
        
        # Scenario-specific impact calculations
        if scenario_params.scenario == StressScenario.MARKET_SATURATION:
            # Higher competition score = more vulnerable to saturation
            competition_factor = niche.competition_score_numeric / 100
            base_impact *= (1 + competition_factor)
        
        elif scenario_params.scenario == StressScenario.ECONOMIC_DOWNTURN:
            # Higher price points more vulnerable to economic stress
            if niche.price_range:
                avg_price = (niche.price_range[0] + niche.price_range[1]) / 2
                price_factor = min(1.0, avg_price / 50)  # Normalize around $50
                base_impact *= (1 + price_factor * 0.5)
        
        elif scenario_params.scenario == StressScenario.COMPETITIVE_FLOODING:
            # Lower competition score = more vulnerable to new competitors
            competition_vulnerability = (100 - niche.competition_score_numeric) / 100
            base_impact *= (1 + competition_vulnerability * 0.8)
        
        elif scenario_params.scenario == StressScenario.SEASONAL_CRASH:
            # Higher seasonal factors = more vulnerable
            seasonal_factor = 0.5  # Default moderate seasonality
            if niche.seasonal_factors:
                seasonal_factor = niche.seasonal_factors.get("volatility", 0.5)
            base_impact *= (1 + seasonal_factor)
        
        elif scenario_params.scenario == StressScenario.TREND_REVERSAL:
            # Trend-dependent niches more vulnerable
            if trend_analysis:
                trend_dependency = trend_analysis.trend_score / 100
                base_impact *= (1 + trend_dependency * 0.7)
        
        elif scenario_params.scenario == StressScenario.CONSUMER_SHIFT:
            # Niche-specific consumer dependency
            market_size_factor = (100 - niche.market_size_score) / 100
            base_impact *= (1 + market_size_factor * 0.6)
        
        # Apply duration factor (longer stress = more impact)
        duration_factor = min(1.5, scenario_params.duration_months / 12)
        base_impact *= duration_factor
        
        return min(0.95, base_impact)  # Cap at 95% impact
    
    @classmethod
    def _calculate_recovery_factor(
        cls,
        niche: Niche,
        scenario_params: StressTestParameters,
        stress_impact: float
    ) -> float:
        """Calculate how well the niche recovers from stress."""
        base_recovery = 0.7  # Base 70% recovery
        
        # Higher profitability = better recovery
        profitability_factor = niche.profitability_score / 100
        base_recovery += profitability_factor * 0.2
        
        # Lower competition = easier recovery
        competition_factor = (100 - niche.competition_score_numreic) / 100
        base_recovery += competition_factor * 0.15
        
        # Market size helps recovery
        market_factor = niche.market_size_score / 100
        base_recovery += market_factor * 0.1
        
        # Recovery time factor (longer recovery time = better eventual recovery)
        time_factor = min(1.2, scenario_params.recovery_months / 12)
        base_recovery *= time_factor
        
        # Severe stress reduces recovery potential
        stress_factor = 1 - (stress_impact * 0.3)
        base_recovery *= stress_factor
        
        return min(1.0, max(0.1, base_recovery))
    
    @classmethod
    def _calculate_survival_probability(
        cls,
        stressed_score: float,
        recovery_score: float,
        scenario_params: StressTestParameters
    ) -> float:
        """Calculate probability of surviving the stress scenario."""
        # Base survival on stressed score
        if stressed_score >= 60:
            base_survival = 0.95
        elif stressed_score >= 40:
            base_survival = 0.8
        elif stressed_score >= 20:
            base_survival = 0.6
        elif stressed_score >= 10:
            base_survival = 0.3
        else:
            base_survival = 0.1
        
        # Factor in recovery potential
        recovery_factor = recovery_score / 100
        base_survival += recovery_factor * 0.2
        
        # Factor in scenario severity and duration
        severity_penalty = scenario_params.severity * 0.15
        duration_penalty = min(0.2, scenario_params.duration_months / 24)
        
        final_survival = base_survival - severity_penalty - duration_penalty
        
        return min(1.0, max(0.05, final_survival))
    
    @classmethod
    def _identify_vulnerabilities(
        cls,
        niche: Niche,
        scenario_params: StressTestParameters,
        stress_impact: float
    ) -> List[str]:
        """Identify key vulnerabilities exposed by the stress test."""
        vulnerabilities = []
        
        # High stress impact indicates vulnerability
        if stress_impact > 0.7:
            vulnerabilities.append(f"High vulnerability to {scenario_params.scenario.value}")
        
        # Scenario-specific vulnerabilities
        if scenario_params.scenario == StressScenario.MARKET_SATURATION:
            if niche.competition_score_numeric > 70:
                vulnerabilities.append("Already high competition makes saturation more likely")
            if niche.market_size_score < 40:
                vulnerabilities.append("Small market size limits growth potential")
        
        elif scenario_params.scenario == StressScenario.ECONOMIC_DOWNTURN:
            if niche.price_range and niche.price_range[1] > 30:
                vulnerabilities.append("Higher price point vulnerable to economic stress")
            if "luxury" in niche.category.lower() or "premium" in niche.category.lower():
                vulnerabilities.append("Luxury/premium positioning vulnerable in downturns")
        
        elif scenario_params.scenario == StressScenario.COMPETITIVE_FLOODING:
            if niche.competition_score_numeric < 50:
                vulnerabilities.append("Low competition barriers allow easy entry")
            if not niche.content_gaps:
                vulnerabilities.append("Limited content differentiation opportunities")
        
        elif scenario_params.scenario == StressScenario.SEASONAL_CRASH:
            if niche.seasonal_factors and niche.seasonal_factors.get("volatility", 0) > 0.6:
                vulnerabilities.append("High seasonal volatility increases crash risk")
        
        # General vulnerabilities
        if niche.confidence_score < 60:
            vulnerabilities.append("Low confidence in niche data increases uncertainty")
        
        if niche.profitability_score < 50:
            vulnerabilities.append("Low profitability reduces stress resilience")
        
        return vulnerabilities
    
    @classmethod
    def _generate_mitigation_strategies(
        cls,
        niche: Niche,
        scenario_params: StressTestParameters,
        vulnerabilities: List[str]
    ) -> List[str]:
        """Generate mitigation strategies for identified vulnerabilities."""
        strategies = []
        
        # Scenario-specific strategies
        if scenario_params.scenario == StressScenario.MARKET_SATURATION:
            strategies.extend([
                "Develop unique content angles to differentiate from competitors",
                "Focus on sub-niches with less competition",
                "Build strong brand recognition early"
            ])
        
        elif scenario_params.scenario == StressScenario.ECONOMIC_DOWNTURN:
            strategies.extend([
                "Consider lower-priced product options",
                "Emphasize value proposition and practical benefits",
                "Diversify into recession-resistant sub-topics"
            ])
        
        elif scenario_params.scenario == StressScenario.COMPETITIVE_FLOODING:
            strategies.extend([
                "Establish first-mover advantage quickly",
                "Create high-quality content that's hard to replicate",
                "Build customer loyalty through superior value"
            ])
        
        elif scenario_params.scenario == StressScenario.SEASONAL_CRASH:
            strategies.extend([
                "Develop year-round content strategy",
                "Create evergreen content to smooth seasonal variations",
                "Plan inventory and marketing around seasonal patterns"
            ])
        
        elif scenario_params.scenario == StressScenario.PLATFORM_CHANGES:
            strategies.extend([
                "Diversify across multiple platforms",
                "Stay updated on platform policy changes",
                "Build direct customer relationships"
            ])
        
        elif scenario_params.scenario == StressScenario.TREND_REVERSAL:
            strategies.extend([
                "Monitor trend indicators closely",
                "Prepare pivot strategies for related niches",
                "Build adaptable content frameworks"
            ])
        
        # General mitigation strategies
        if niche.profitability_score < 60:
            strategies.append("Focus on improving profit margins through premium positioning")
        
        if niche.market_size_score < 50:
            strategies.append("Expand target market through related keywords and topics")
        
        if niche.competition_score > 70:
            strategies.append("Identify and exploit competitor weaknesses")
        
        return strategies[:5]  # Limit to top 5 strategies


async def niche_stress_test(
    trends_client: TrendsClient,
    keepa_client: KeepaClient,
    cache_manager: CacheManager,
    niche_keyword: str,
    custom_scenarios: Optional[List[StressTestParameters]] = None,
    include_all_scenarios: bool = True
) -> Dict[str, Any]:
    """Perform comprehensive stress testing on a niche.
    
    Args:
        trends_client: Google Trends client
        keepa_client: Keepa API client
        cache_manager: Cache manager
        niche_keyword: Primary keyword for the niche
        custom_scenarios: Custom stress test scenarios
        include_all_scenarios: Whether to test all default scenarios
    
    Returns:
        Dictionary containing comprehensive stress test results
    """
    logger.info(f"Starting stress test for niche: {niche_keyword}")
    
    try:
        # First, we need to create/retrieve the niche data
        niche = await _create_niche_for_testing(
            trends_client, keepa_client, cache_manager, niche_keyword
        )
        
        if not niche:
            return {
                "error": "Unable to create niche data for stress testing",
                "niche_keyword": niche_keyword,
                "test_timestamp": datetime.now().isoformat()
            }
        
        # Get trend analysis for enhanced testing
        trend_analysis = None
        try:
            trend_analysis = await trends_client.get_trend_analysis(niche_keyword)
        except Exception as e:
            logger.warning(f"Could not get trend analysis: {e}")
        
        # Determine scenarios to test
        scenarios_to_test = []
        
        if include_all_scenarios:
            scenarios_to_test.extend(StressTester.DEFAULT_SCENARIOS.values())
        
        if custom_scenarios:
            scenarios_to_test.extend(custom_scenarios)
        
        if not scenarios_to_test:
            scenarios_to_test = list(StressTester.DEFAULT_SCENARIOS.values())
        
        # Run stress tests for each scenario
        scenario_results = []
        for scenario_params in scenarios_to_test:
            try:
                result = StressTester.simulate_scenario(
                    niche, scenario_params, trend_analysis
                )
                scenario_results.append(result)
                logger.debug(f"Completed stress test for scenario: {scenario_params.scenario.value}")
            except Exception as e:
                logger.error(f"Failed stress test for scenario {scenario_params.scenario.value}: {e}")
        
        # Calculate overall resilience
        overall_resilience = _calculate_overall_resilience(scenario_results)
        
        # Determine risk profile
        overall_risk_profile = _determine_risk_profile(scenario_results, overall_resilience)
        
        # Identify critical vulnerabilities
        critical_vulnerabilities = _identify_critical_vulnerabilities(scenario_results)
        
        # Generate recommended mitigations
        recommended_mitigations = _generate_recommended_mitigations(
            scenario_results, critical_vulnerabilities
        )
        
        # Calculate confidence level
        confidence_level = _calculate_test_confidence(
            niche, trend_analysis, len(scenario_results)
        )
        
        # Create comprehensive report
        stress_test_report = StressTestReport(
            niche_keyword=niche_keyword,
            baseline_niche=niche,
            scenario_results=scenario_results,
            overall_resilience=overall_resilience,
            risk_profile=overall_risk_profile,
            critical_vulnerabilities=critical_vulnerabilities,
            recommended_mitigations=recommended_mitigations,
            confidence_level=confidence_level,
            test_timestamp=datetime.now()
        )
        
        # Compile final result
        result = {
            "stress_test_summary": {
                "niche_keyword": niche_keyword,
                "overall_resilience": overall_resilience,
                "risk_profile": overall_risk_profile.value, # Use enum .value
                "scenarios_tested": len(scenario_results),
                "confidence_level": confidence_level
            },
            "baseline_niche": {
                "overall_score": niche.overall_score,
                "profitability_score": niche.profitability_score_numeric, # Use numeric
                "competition_score": niche.competition_score_numeric, # Use numeric
                "market_size_score": niche.market_size_score,
                "confidence_score": niche.confidence_score,
                "competition_level": niche.competition_level.value, # Include categorical
                "profitability_tier": niche.profitability_tier.value, # Include categorical
    },
            "scenario_results": [
                {
                    "scenario": result.scenario.value,
                    "severity": result.parameters.severity,
                    "probability": result.parameters.probability,
                    "initial_score": result.initial_score,
                    "stressed_score": result.stressed_score,
                    "recovery_score": result.recovery_score,
                    "impact_percentage": result.impact_percentage,
                    "resilience_score": result.resilience_score,
                    "survival_probability": result.survival_probability,
                    "key_vulnerabilities": result.key_vulnerabilities,
                    "mitigation_strategies": result.mitigation_strategies,
                    "description": result.parameters.description
                }
                for result in scenario_results
            ],
            "risk_analysis": {
                "critical_vulnerabilities": critical_vulnerabilities,
                "highest_risk_scenarios": _get_highest_risk_scenarios(scenario_results),
                "lowest_resilience_scenarios": _get_lowest_resilience_scenarios(scenario_results),
                "survival_analysis": _analyze_survival_probabilities(scenario_results)
            },
            "recommendations": {
                "immediate_actions": recommended_mitigations[:3],
                "strategic_mitigations": recommended_mitigations[3:],
                "monitoring_priorities": _get_monitoring_priorities(scenario_results),
                "contingency_planning": _get_contingency_recommendations(scenario_results)
            },
            "test_metadata": {
                "test_timestamp": stress_test_report.test_timestamp.isoformat(),
                "confidence_level": confidence_level,
                "data_quality": {
                    "has_trend_data": trend_analysis is not None,
                    "niche_data_completeness": _assess_niche_data_completeness(niche)
                }
            }
        }
        
        logger.info(f"Stress test completed for niche: {niche_keyword}")
        return result
    
    except Exception as e:
        logger.error(f"Stress test failed for {niche_keyword}: {e}")
        return {
            "error": str(e),
            "niche_keyword": niche_keyword,
            "test_timestamp": datetime.now().isoformat()
        }


async def _create_niche_for_testing(
    trends_client: TrendsClient,
    keepa_client: KeepaClient,
    cache_manager: CacheManager,
    keyword: str
) -> Optional[Niche]:
    """Create a niche object for stress testing."""
    try:
        # Get trend analysis
        trend_analysis = await trends_client.get_trend_analysis(keyword)
        
        # Simulate competitor analysis (in real implementation, this would use actual data)
        competitor_data = {
            "total_competitors": random.randint(50, 500),
            "avg_price": random.uniform(10, 50),
            "top_competitor_sales": random.randint(100, 1000)
        }
        
        # Calculate scores using NicheScorer
        scorer = NicheScorer()
        
        # Create basic niche structure
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
        
        
        
    except Exception as e:
        logger.error(f"Failed to create niche for testing: {e}")
        return None


def _calculate_overall_resilience(scenario_results: List[ScenarioResult]) -> float:
    """Calculate overall resilience score across all scenarios."""
    if not scenario_results:
        return 0.0
    
    # Weight by scenario probability
    weighted_resilience = 0.0
    total_weight = 0.0
    
    for result in scenario_results:
        weight = result.parameters.probability
        weighted_resilience += result.resilience_score * weight
        total_weight += weight
    
    if total_weight == 0:
        return mean([r.resilience_score for r in scenario_results])
    
    return round(weighted_resilience / total_weight, 1)


def _determine_risk_profile(scenario_results: List[ScenarioResult], overall_resilience: float) -> RiskLevel:
    """Determine overall risk profile."""
    # Count high-impact scenarios
    high_impact_scenarios = len([r for r in scenario_results if r.impact_percentage > 50])
    low_survival_scenarios = len([r for r in scenario_results if r.survival_probability < 0.7])
    
    if overall_resilience >= 80 and high_impact_scenarios <= 1:
            return RiskLevel.LOW
    elif overall_resilience >= 60 and high_impact_scenarios <= 3:
            return RiskLevel.MEDIUM
    elif overall_resilience >= 40:
            return RiskLevel.HIGH
    else:
            return RiskLevel.VERY_HIGH


def _identify_critical_vulnerabilities(scenario_results: List[ScenarioResult]) -> List[str]:
    """Identify the most critical vulnerabilities across all scenarios."""
    vulnerability_counts = {}
    
    # Count vulnerability mentions across scenarios
    for result in scenario_results:
        for vulnerability in result.key_vulnerabilities:
            vulnerability_counts[vulnerability] = vulnerability_counts.get(vulnerability, 0) + 1
    
    # Also include vulnerabilities from high-impact scenarios
    critical_vulnerabilities = []
    
    for result in scenario_results:
        if result.impact_percentage > 60 or result.survival_probability < 0.6:
            critical_vulnerabilities.extend(result.key_vulnerabilities)
    
    # Get most common vulnerabilities
    common_vulnerabilities = [
        vuln for vuln, count in vulnerability_counts.items() 
        if count >= 2
    ]
    
    # Combine and deduplicate
    all_critical = list(set(critical_vulnerabilities + common_vulnerabilities))
    
    return all_critical[:5]  # Return top 5


def _generate_recommended_mitigations(
    scenario_results: List[ScenarioResult],
    critical_vulnerabilities: List[str]
) -> List[str]:
    """Generate prioritized mitigation recommendations."""
    mitigation_counts = {}
    
    # Count mitigation strategy mentions
    for result in scenario_results:
        for mitigation in result.mitigation_strategies:
            weight = result.parameters.probability * (result.impact_percentage / 100)
            mitigation_counts[mitigation] = mitigation_counts.get(mitigation, 0) + weight
    
    # Sort by weighted importance
    sorted_mitigations = sorted(
        mitigation_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    return [mitigation for mitigation, _ in sorted_mitigations[:8]]


def _calculate_test_confidence(
    niche: Niche,
    trend_analysis: Optional[TrendAnalysis],
    scenarios_tested: int
) -> float:
    """Calculate confidence level in the stress test results."""
    base_confidence = 0.7
    
    # Factor in niche data quality
    base_confidence += (niche.confidence_score / 100) * 0.2
    
    # Factor in trend data availability
    if trend_analysis:
        base_confidence += trend_analysis.confidence_level * 0.15
    
    # Factor in number of scenarios tested
    scenario_factor = min(1.0, scenarios_tested / 8) * 0.15
    base_confidence += scenario_factor
    
    return round(min(1.0, base_confidence), 2)


def _get_highest_risk_scenarios(scenario_results: List[ScenarioResult]) -> List[Dict[str, Any]]:
    """Get scenarios with highest risk (impact * probability)."""
    risk_scenarios = []
    
    for result in scenario_results:
        risk_score = (result.impact_percentage / 100) * result.parameters.probability
        risk_scenarios.append({
            "scenario": result.scenario.value,
            "risk_score": round(risk_score, 3),
            "impact_percentage": result.impact_percentage,
            "probability": result.parameters.probability
        })
    
    return sorted(risk_scenarios, key=lambda x: x["risk_score"], reverse=True)[:3]


def _get_lowest_resilience_scenarios(scenario_results: List[ScenarioResult]) -> List[Dict[str, Any]]:
    """Get scenarios with lowest resilience scores."""
    resilience_scenarios = [
        {
            "scenario": result.scenario.value,
            "resilience_score": result.resilience_score,
            "survival_probability": result.survival_probability
        }
        for result in scenario_results
    ]
    
    return sorted(resilience_scenarios, key=lambda x: x["resilience_score"])[:3]


def _analyze_survival_probabilities(scenario_results: List[ScenarioResult]) -> Dict[str, Any]:
    """Analyze survival probabilities across scenarios."""
    survival_probs = [r.survival_probability for r in scenario_results]
    
    return {
        "average_survival_probability": round(mean(survival_probs), 3),
        "worst_case_survival": round(min(survival_probs), 3),
        "best_case_survival": round(max(survival_probs), 3),
        "scenarios_below_70_percent": len([p for p in survival_probs if p < 0.7]),
        "scenarios_below_50_percent": len([p for p in survival_probs if p < 0.5])
    }


def _get_monitoring_priorities(scenario_results: List[ScenarioResult]) -> List[str]:
    """Get monitoring priorities based on stress test results."""
    priorities = []
    
    # High-probability, high-impact scenarios need monitoring
    for result in scenario_results:
        if result.parameters.probability > 0.3 and result.impact_percentage > 40:
            priorities.append(f"Monitor indicators for {result.scenario.value}")
    
    # General monitoring recommendations
    priorities.extend([
        "Track competitor entry rates",
        "Monitor trend strength and direction",
        "Watch for seasonal pattern changes",
        "Track platform policy updates"
    ])
    
    return priorities[:5]


def _get_contingency_recommendations(scenario_results: List[ScenarioResult]) -> List[str]:
    """Get contingency planning recommendations."""
    recommendations = [
        "Develop pivot strategies for related niches",
        "Maintain diversified content portfolio",
        "Build emergency fund for market downturns",
        "Create rapid response protocols for competitive threats",
        "Establish alternative revenue streams"
    ]
    
    # Add scenario-specific contingencies
    high_risk_scenarios = [r for r in scenario_results if r.impact_percentage > 60]
    
    if any(r.scenario == StressScenario.TREND_REVERSAL for r in high_risk_scenarios):
        recommendations.append("Prepare trend reversal detection and response plan")
    
    if any(r.scenario == StressScenario.COMPETITIVE_FLOODING for r in high_risk_scenarios):
        recommendations.append("Develop competitive differentiation strategies")
    
    return recommendations[:6]


def _assess_niche_data_completeness(niche: Niche) -> float:
    """Assess completeness of niche data for testing."""
    completeness_score = 0.0
    total_factors = 8
    
    if niche.primary_keyword:
        completeness_score += 1
    if niche.related_keywords:
        completeness_score += 1
    if niche.competition_score > 0:
        completeness_score += 1
    if niche.profitability_score > 0:
        completeness_score += 1
    if niche.market_size_score > 0:
        completeness_score += 1
    if niche.trend_analysis:
        completeness_score += 1
    if niche.competitor_data:
        completeness_score += 1
    if niche.price_range:
        completeness_score += 1
    
    return round(completeness_score / total_factors, 2)