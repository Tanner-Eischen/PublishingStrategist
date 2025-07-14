"""Stress testing API router.

This module provides REST API endpoints for stress testing functionality,
integrating with the existing MCP agent's stress testing tool.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from ..models.requests import StressTestingRequest
from ..models.responses import (
    StressTestingResponse,
    StressTestScenario,
    AnalysisMetadata,
    ChartData,
    ErrorResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_agent():
    """Dependency to get the MCP agent from app state."""
    from fastapi import Request
    
    def _get_agent(request: Request):
        if not hasattr(request.app.state, 'agent'):
            raise HTTPException(
                status_code=503,
                detail="MCP agent not available"
            )
        return request.app.state.agent
    
    return _get_agent


def convert_mcp_scenario_to_api(mcp_scenario: Dict[str, Any]) -> StressTestScenario:
    """Convert MCP agent stress test scenario to API response format."""
    return StressTestScenario(
        scenario=mcp_scenario.get('scenario', ''),
        severity=mcp_scenario.get('severity', 'moderate'),
        impact_score=float(mcp_scenario.get('impact_score', 0)),
        probability=float(mcp_scenario.get('probability', 0)),
        description=mcp_scenario.get('description', ''),
        potential_losses=mcp_scenario.get('potential_losses'),
        mitigation_strategies=mcp_scenario.get('mitigation_strategies', []),
        recovery_time=mcp_scenario.get('recovery_time')
    )


def calculate_overall_resilience(scenarios: List[StressTestScenario]) -> float:
    """Calculate overall resilience score based on stress test scenarios."""
    if not scenarios:
        return 0.0
    
    # Weight scenarios by probability and impact
    total_weighted_impact = 0.0
    total_weight = 0.0
    
    for scenario in scenarios:
        weight = scenario.probability / 100.0  # Convert percentage to decimal
        weighted_impact = scenario.impact_score * weight
        total_weighted_impact += weighted_impact
        total_weight += weight
    
    if total_weight == 0:
        return 50.0  # Default neutral score
    
    # Calculate resilience as inverse of weighted impact
    avg_weighted_impact = total_weighted_impact / total_weight
    resilience_score = max(0, 100 - avg_weighted_impact)
    
    return resilience_score


def determine_risk_level(resilience_score: float) -> str:
    """Determine risk level based on resilience score."""
    if resilience_score >= 75:
        return "low"
    elif resilience_score >= 50:
        return "medium"
    else:
        return "high"


def create_stress_test_charts(scenarios: List[StressTestScenario], resilience_score: float) -> List[ChartData]:
    """Create chart data for stress test visualization."""
    charts = []
    
    # Impact vs Probability scatter plot
    scenario_data = [
        {
            "x": scenario.probability,
            "y": scenario.impact_score,
            "label": scenario.scenario.replace('_', ' ').title(),
            "severity": scenario.severity
        }
        for scenario in scenarios
    ]
    
    charts.append(ChartData(
        type="scatter",
        title="Risk Matrix: Impact vs Probability",
        data=scenario_data,
        options={
            "xAxis": {"title": "Probability (%)"},
            "yAxis": {"title": "Impact Score"}
        }
    ))
    
    # Scenario impact comparison
    impact_data = [
        {"scenario": scenario.scenario.replace('_', ' ').title(), "impact": scenario.impact_score}
        for scenario in scenarios
    ]
    
    charts.append(ChartData(
        type="bar",
        title="Scenario Impact Comparison",
        data=impact_data,
        labels=[item["scenario"] for item in impact_data],
        colors=["#EF4444", "#F59E0B", "#10B981", "#3B82F6", "#8B5CF6"]
    ))
    
    # Severity distribution
    severity_counts = {}
    for scenario in scenarios:
        severity = scenario.severity
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    charts.append(ChartData(
        type="pie",
        title="Scenario Severity Distribution",
        data=[
            {"label": severity.title(), "value": count}
            for severity, count in severity_counts.items()
        ],
        colors=["#10B981", "#F59E0B", "#EF4444"]
    ))
    
    # Resilience gauge
    charts.append(ChartData(
        type="gauge",
        title="Overall Resilience Score",
        data=[{"value": resilience_score, "max": 100}],
        colors=["#EF4444" if resilience_score < 50 else "#F59E0B" if resilience_score < 75 else "#10B981"]
    ))
    
    return charts


def generate_stress_test_recommendations(scenarios: List[StressTestScenario], resilience_score: float, risk_level: str) -> List[str]:
    """Generate recommendations based on stress test results."""
    recommendations = []
    
    # Overall resilience recommendations
    if risk_level == "high":
        recommendations.append("High risk detected - implement immediate risk mitigation strategies")
        recommendations.append("Consider diversifying into multiple niches to reduce concentration risk")
    elif risk_level == "medium":
        recommendations.append("Moderate risk level - develop contingency plans for key scenarios")
        recommendations.append("Monitor market conditions closely and prepare adaptive strategies")
    else:
        recommendations.append("Low risk profile - maintain current strategy with regular monitoring")
    
    # Scenario-specific recommendations
    high_impact_scenarios = [s for s in scenarios if s.impact_score > 70]
    if high_impact_scenarios:
        recommendations.append(
            f"Focus on mitigating {len(high_impact_scenarios)} high-impact scenarios first"
        )
    
    high_probability_scenarios = [s for s in scenarios if s.probability > 60]
    if high_probability_scenarios:
        recommendations.append(
            f"Prepare for {len(high_probability_scenarios)} likely scenarios with immediate action plans"
        )
    
    # Mitigation strategy recommendations
    all_strategies = set()
    for scenario in scenarios:
        all_strategies.update(scenario.mitigation_strategies)
    
    if "diversification" in str(all_strategies).lower():
        recommendations.append("Diversification appears in multiple mitigation strategies - prioritize this approach")
    
    if "monitoring" in str(all_strategies).lower():
        recommendations.append("Enhanced monitoring recommended across multiple scenarios")
    
    return recommendations


def generate_contingency_plans(scenarios: List[StressTestScenario]) -> List[str]:
    """Generate contingency planning suggestions."""
    contingency_plans = []
    
    # Emergency response plans
    contingency_plans.append("Establish early warning indicators for each identified risk scenario")
    contingency_plans.append("Create decision trees for rapid response to market changes")
    
    # Financial contingencies
    high_loss_scenarios = [s for s in scenarios if s.potential_losses and s.potential_losses > 1000]
    if high_loss_scenarios:
        contingency_plans.append("Maintain emergency fund to cover potential losses from high-impact scenarios")
    
    # Operational contingencies
    contingency_plans.append("Develop alternative marketing channels to reduce dependency on single platforms")
    contingency_plans.append("Build relationships with multiple suppliers/partners for operational resilience")
    
    # Strategic contingencies
    contingency_plans.append("Prepare pivot strategies for entering adjacent niches if primary market declines")
    contingency_plans.append("Establish regular stress testing schedule (quarterly) to update risk assessments")
    
    return contingency_plans


@router.post("/run", response_model=StressTestingResponse)
async def run_stress_test(
    request: StressTestingRequest,
    background_tasks: BackgroundTasks,
    agent=Depends(get_agent())
):
    """Run stress test on a niche.
    
    This endpoint performs stress testing on the specified niche
    using the MCP agent's stress testing tool.
    """
    try:
        logger.info(f"Starting stress test for niche: {request.niche}")
        
        # Prepare parameters for MCP agent
        mcp_params = {
            "niche": request.niche,
            "test_scenarios": request.test_scenarios,
            "severity_level": request.severity_level,
            "include_recommendations": request.include_recommendations
        }
        
        # Call MCP agent's stress testing method
        mcp_result = await agent.stress_test_niche(
            niche=request.niche,
            test_scenarios=request.test_scenarios,
            severity_level=request.severity_level,
            include_recommendations=request.include_recommendations
        )
        
        # Convert MCP result to API format
        scenarios = [
            convert_mcp_scenario_to_api(scenario)
            for scenario in mcp_result.get('scenarios', [])
        ]
        
        # Calculate overall resilience and risk level
        overall_resilience = calculate_overall_resilience(scenarios)
        risk_level = determine_risk_level(overall_resilience)
        
        # Create visualization charts
        charts = create_stress_test_charts(scenarios, overall_resilience)
        
        # Generate recommendations and contingency plans
        recommendations = generate_stress_test_recommendations(scenarios, overall_resilience, risk_level)
        contingency_plans = generate_contingency_plans(scenarios)
        
        # Create analysis metadata
        metadata = AnalysisMetadata(
            execution_time=mcp_result.get('execution_time', 0.0),
            data_sources=mcp_result.get('data_sources', ['market_analysis', 'historical_data']),
            cache_hit=mcp_result.get('cache_hit', False),
            warnings=mcp_result.get('warnings', [])
        )
        
        response = StressTestingResponse(
            niche=request.niche,
            overall_resilience=overall_resilience,
            risk_level=risk_level,
            scenarios=scenarios,
            analysis_metadata=metadata,
            charts=charts,
            recommendations=recommendations,
            contingency_plans=contingency_plans
        )
        
        logger.info(f"Stress test completed. Resilience score: {overall_resilience:.1f}, Risk level: {risk_level}")
        return response
        
    except Exception as e:
        logger.error(f"Error in stress testing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run stress test: {str(e)}"
        )


@router.get("/scenarios")
async def get_available_scenarios():
    """Get available stress test scenarios.
    
    This endpoint returns a list of available stress test scenarios
    that can be used for testing niche resilience.
    """
    scenarios = {
        "market_saturation": {
            "name": "Market Saturation",
            "description": "Sudden increase in competitors entering the market",
            "typical_impact": "High",
            "typical_probability": "Medium",
            "indicators": ["Increased competition", "Price pressure", "Reduced market share"]
        },
        "seasonal_decline": {
            "name": "Seasonal Decline",
            "description": "Significant drop in demand during off-season periods",
            "typical_impact": "Medium",
            "typical_probability": "High",
            "indicators": ["Seasonal search patterns", "Historical sales data", "Consumer behavior"]
        },
        "trend_reversal": {
            "name": "Trend Reversal",
            "description": "Major shift in consumer preferences away from the niche",
            "typical_impact": "High",
            "typical_probability": "Low",
            "indicators": ["Declining search trends", "Social media sentiment", "Industry reports"]
        },
        "competition_increase": {
            "name": "Competition Increase",
            "description": "Entry of major players or significant marketing spend by competitors",
            "typical_impact": "Medium",
            "typical_probability": "Medium",
            "indicators": ["New product launches", "Advertising spend", "Market consolidation"]
        },
        "demand_drop": {
            "name": "Demand Drop",
            "description": "Sudden decrease in overall market demand",
            "typical_impact": "High",
            "typical_probability": "Low",
            "indicators": ["Economic indicators", "Consumer spending", "Market research"]
        },
        "keyword_shift": {
            "name": "Keyword Shift",
            "description": "Changes in how consumers search for products in the niche",
            "typical_impact": "Medium",
            "typical_probability": "Medium",
            "indicators": ["Search term evolution", "Platform algorithm changes", "User behavior"]
        }
    }
    
    return {
        "scenarios": scenarios,
        "total_available": len(scenarios),
        "usage_tips": [
            "Select scenarios most relevant to your niche",
            "Consider both high-impact and high-probability scenarios",
            "Run tests at different severity levels",
            "Update stress tests regularly as market conditions change"
        ]
    }


@router.get("/risk-matrix")
async def get_risk_matrix():
    """Get risk assessment matrix guidelines.
    
    This endpoint provides guidelines for interpreting
    risk matrix results from stress testing.
    """
    risk_matrix = {
        "probability_levels": {
            "low": {"range": "0-30%", "description": "Unlikely to occur"},
            "medium": {"range": "31-70%", "description": "Possible occurrence"},
            "high": {"range": "71-100%", "description": "Likely to occur"}
        },
        "impact_levels": {
            "low": {"range": "0-30", "description": "Minor impact on business"},
            "medium": {"range": "31-70", "description": "Moderate impact on business"},
            "high": {"range": "71-100", "description": "Severe impact on business"}
        },
        "risk_categories": {
            "low_risk": {
                "criteria": "Low probability AND low impact",
                "action": "Monitor and accept",
                "color": "green"
            },
            "medium_risk": {
                "criteria": "Medium probability OR medium impact",
                "action": "Develop mitigation plans",
                "color": "yellow"
            },
            "high_risk": {
                "criteria": "High probability AND/OR high impact",
                "action": "Immediate action required",
                "color": "red"
            }
        },
        "resilience_scoring": {
            "excellent": {"range": "80-100", "description": "Highly resilient to stress scenarios"},
            "good": {"range": "60-79", "description": "Generally resilient with some vulnerabilities"},
            "fair": {"range": "40-59", "description": "Moderate resilience, requires attention"},
            "poor": {"range": "0-39", "description": "Low resilience, high risk exposure"}
        }
    }
    
    return risk_matrix


@router.post("/compare")
async def compare_niches(
    niches: List[str],
    scenarios: List[str] = None,
    agent=Depends(get_agent())
):
    """Compare stress test results across multiple niches.
    
    This endpoint runs stress tests on multiple niches
    and provides a comparative analysis.
    """
    try:
        if len(niches) > 5:
            raise HTTPException(
                status_code=400,
                detail="Maximum 5 niches can be compared at once"
            )
        
        logger.info(f"Comparing stress tests for niches: {niches}")
        
        comparison_results = []
        
        for niche in niches:
            # Run stress test for each niche
            mcp_params = {
                "niche": niche,
                "test_scenarios": scenarios or ["market_saturation", "seasonal_decline", "trend_reversal"],
                "severity_level": "moderate",
                "include_recommendations": False  # Skip for comparison
            }
            
            try:
                mcp_result = await agent.stress_test_niche(
                    niche=niche,
                    test_scenarios=scenarios or ["market_saturation", "seasonal_decline", "trend_reversal"],
                    severity_level="moderate",
                    include_recommendations=False
                )
                
                scenarios_data = [
                    convert_mcp_scenario_to_api(scenario)
                    for scenario in mcp_result.get('scenarios', [])
                ]
                
                resilience_score = calculate_overall_resilience(scenarios_data)
                risk_level = determine_risk_level(resilience_score)
                
                comparison_results.append({
                    "niche": niche,
                    "resilience_score": resilience_score,
                    "risk_level": risk_level,
                    "scenario_count": len(scenarios_data),
                    "avg_impact": sum(s.impact_score for s in scenarios_data) / len(scenarios_data) if scenarios_data else 0,
                    "avg_probability": sum(s.probability for s in scenarios_data) / len(scenarios_data) if scenarios_data else 0
                })
                
            except Exception as e:
                logger.warning(f"Failed to test niche {niche}: {e}")
                comparison_results.append({
                    "niche": niche,
                    "resilience_score": 0,
                    "risk_level": "unknown",
                    "error": str(e)
                })
        
        # Sort by resilience score (highest first)
        comparison_results.sort(key=lambda x: x.get('resilience_score', 0), reverse=True)
        
        # Generate comparison insights
        insights = []
        if comparison_results:
            best_niche = comparison_results[0]
            worst_niche = comparison_results[-1]
            
            insights.append(f"'{best_niche['niche']}' shows highest resilience ({best_niche['resilience_score']:.1f})")
            insights.append(f"'{worst_niche['niche']}' shows lowest resilience ({worst_niche['resilience_score']:.1f})")
            
            low_risk_count = len([r for r in comparison_results if r.get('risk_level') == 'low'])
            if low_risk_count > 0:
                insights.append(f"{low_risk_count} out of {len(niches)} niches show low risk profile")
        
        return {
            "comparison_results": comparison_results,
            "insights": insights,
            "recommendation": f"Consider focusing on '{comparison_results[0]['niche']}' for lowest risk exposure" if comparison_results else "No valid results for comparison"
        }
        
    except Exception as e:
        logger.error(f"Error in niche comparison: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compare niches: {str(e)}"
        )