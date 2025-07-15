#!/usr/bin/env python3
"""Basic Usage Example for KDP Strategist AI Agent.

This example demonstrates how to use the KDP Strategist AI Agent
programmatically to discover profitable niches, analyze competitors,
generate listings, validate trends, and perform stress testing.

Usage:
    python examples/basic_usage.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

from config.settings import load_settings
from agent.kdp_strategist_agent import KDPStrategistAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demonstrate_niche_discovery(agent: KDPStrategistAgent):
    """Demonstrate niche discovery functionality."""
    print("\n" + "="*60)
    print("🔍 NICHE DISCOVERY DEMONSTRATION")
    print("="*60)
    
    try:
        # Example: Find profitable niches in the cooking space
        result = await agent.discover_niches("find_profitable_niches", {
            "base_keywords": ["healthy cooking", "meal prep", "quick recipes"],
            "max_niches": 3,
            "min_profitability": 60,
            "include_seasonal": True
        })
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return
        
        discovered_niches = result.get("discovered_niches", {})
        analysis_metadata = result.get("analysis_metadata", {})
        
        print(f"✅ Found {len(discovered_niches)} profitable niches")
        print(f"📊 Analysis completed in {analysis_metadata.get('processing_time_seconds', 'N/A')} seconds")
        
        for i, (keyword, niche_data) in enumerate(discovered_niches.items(), 1):
            print(f"\n{i}. {keyword.title()}")
            print(f"   Overall Score: {niche_data.get('overall_score', 'N/A')}/100")
            print(f"   Profitability: {niche_data.get('profitability_score', 'N/A')}/100")
            print(f"   Competition: {niche_data.get('competition_score', 'N/A')}/100")
            print(f"   Market Size: {niche_data.get('market_size_score', 'N/A')}/100")
            
            related_keywords = niche_data.get('related_keywords', [])
            if related_keywords:
                print(f"   Related Keywords: {', '.join(related_keywords[:3])}")
    
    except Exception as e:
        logger.error(f"Error in niche discovery demonstration: {e}")
        print(f"❌ Error: {e}")


async def demonstrate_competitor_analysis(agent: KDPStrategistAgent):
    """Demonstrate competitor analysis functionality."""
    print("\n" + "="*60)
    print("📊 COMPETITOR ANALYSIS DEMONSTRATION")
    print("="*60)
    
    try:
        # Example: Analyze a competitor ASIN (using a sample ASIN)
        result = await agent.analyze_competitors("analyze_competitor_asin", {
            "asin": "B08EXAMPLE123",  # Sample ASIN
            "include_market_analysis": True,
            "analyze_pricing_history": True
        })
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return
        
        competitor_metrics = result.get("competitor_metrics", {})
        market_analysis = result.get("market_analysis", {})
        
        print("✅ Competitor Analysis Completed")
        print(f"📈 Sales Rank: {competitor_metrics.get('sales_rank', 'N/A')}")
        print(f"💰 Current Price: ${competitor_metrics.get('current_price', 'N/A')}")
        print(f"⭐ Rating: {competitor_metrics.get('rating', 'N/A')}/5")
        print(f"📝 Review Count: {competitor_metrics.get('review_count', 'N/A')}")
        
        if market_analysis:
            print(f"\n🏪 Market Analysis:")
            print(f"   Total Competitors: {market_analysis.get('total_competitors', 'N/A')}")
            print(f"   Average Price: ${market_analysis.get('average_price', 'N/A')}")
            print(f"   Market Saturation: {market_analysis.get('saturation_level', 'N/A')}")
    
    except Exception as e:
        logger.error(f"Error in competitor analysis demonstration: {e}")
        print(f"❌ Error: {e}")


async def demonstrate_listing_generation(agent: KDPStrategistAgent):
    """Demonstrate KDP listing generation functionality."""
    print("\n" + "="*60)
    print("📝 LISTING GENERATION DEMONSTRATION")
    print("="*60)
    
    try:
        # Example: Generate a KDP listing for a cookbook
        result = await agent.generate_listing("generate_kdp_listing", {
            "niche_keyword": "healthy meal prep",
            "target_audience": "busy professionals and health-conscious individuals",
            "book_type": "cookbook",
            "include_keywords": True,
            "include_categories": True
        })
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return
        
        generated_listing = result.get("generated_listing", {})
        optimization_suggestions = result.get("optimization_suggestions", [])
        
        print("✅ KDP Listing Generated Successfully")
        print(f"\n📖 Title: {generated_listing.get('title', 'N/A')}")
        print(f"\n📄 Description:")
        description = generated_listing.get('description', 'N/A')
        print(f"   {description[:200]}{'...' if len(description) > 200 else ''}")
        
        keywords = generated_listing.get('keywords', [])
        if keywords:
            print(f"\n🔍 Keywords: {', '.join(keywords[:5])}")
        
        categories = generated_listing.get('categories', [])
        if categories:
            print(f"\n📂 Categories: {', '.join(categories[:3])}")
        
        pricing = generated_listing.get('pricing_recommendation', {})
        if pricing:
            print(f"\n💰 Pricing Recommendation: ${pricing.get('recommended_price', 'N/A')}")
        
        if optimization_suggestions:
            print(f"\n💡 Optimization Suggestions:")
            for i, suggestion in enumerate(optimization_suggestions[:3], 1):
                print(f"   {i}. {suggestion}")
    
    except Exception as e:
        logger.error(f"Error in listing generation demonstration: {e}")
        print(f"❌ Error: {e}")


async def demonstrate_trend_validation(agent: KDPStrategistAgent):
    """Demonstrate trend validation functionality."""
    print("\n" + "="*60)
    print("📈 TREND VALIDATION DEMONSTRATION")
    print("="*60)
    
    try:
        # Example: Validate trend for "intermittent fasting"
        result = await agent.validate_trendsl("validate_trend", {
            "keyword": "intermittent fasting",
            "timeframe": "today 12-m",
            "include_forecasts": True,
            "include_seasonality": True
        })
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return
        
        validation_result = result.get("validation_result", {})
        trend_analysis = result.get("trend_analysis", {})
        forecasts = result.get("forecasts", [])
        seasonal_analysis = result.get("seasonal_analysis", {})
        
        print("✅ Trend Validation Completed")
        print(f"\n🎯 Validation Result:")
        print(f"   Valid Trend: {'✅ Yes' if validation_result.get('is_valid') else '❌ No'}")
        print(f"   Overall Score: {validation_result.get('overall_score', 'N/A')}/100")
        
        print(f"\n📊 Current Trend Analysis:")
        print(f"   Trend Score: {trend_analysis.get('current_score', 'N/A')}/100")
        print(f"   Direction: {trend_analysis.get('direction', 'N/A')}")
        print(f"   Strength: {trend_analysis.get('strength', 'N/A')}")
        print(f"   Confidence: {trend_analysis.get('confidence', 'N/A')}")
        
        if forecasts:
            print(f"\n🔮 Forecasts:")
            for forecast in forecasts[:3]:
                timeframe = forecast.get('timeframe', 'N/A')
                predicted_score = forecast.get('predicted_score', 'N/A')
                direction = forecast.get('direction', 'N/A')
                print(f"   {timeframe}: {predicted_score}/100 ({direction})")
        
        if seasonal_analysis and seasonal_analysis.get('has_seasonality'):
            print(f"\n🌟 Seasonality Detected:")
            peak_months = seasonal_analysis.get('peak_months', [])
            if peak_months:
                month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                peak_names = [month_names[m-1] for m in peak_months if 1 <= m <= 12]
                print(f"   Peak Months: {', '.join(peak_names)}")
    
    except Exception as e:
        logger.error(f"Error in trend validation demonstration: {e}")
        print(f"❌ Error: {e}")


async def demonstrate_stress_testing(agent: KDPStrategistAgent):
    """Demonstrate stress testing functionality."""
    print("\n" + "="*60)
    print("🧪 STRESS TESTING DEMONSTRATION")
    print("="*60)
    
    try:
        # Example: Stress test the "keto recipes" niche
        result = await agent.stress_test_niche("niche_stress_test", {
            "niche_keyword": "keto recipes",
            "include_all_scenarios": True
        })
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return
        
        stress_test_summary = result.get("stress_test_summary", {})
        scenario_results = result.get("scenario_results", [])
        risk_analysis = result.get("risk_analysis", {})
        recommendations = result.get("recommendations", {})
        
        print("✅ Stress Test Completed")
        print(f"\n🛡️ Overall Resilience: {stress_test_summary.get('overall_resilience', 'N/A')}/100")
        print(f"⚠️ Risk Profile: {stress_test_summary.get('risk_profile', 'N/A')}")
        print(f"🧪 Scenarios Tested: {stress_test_summary.get('scenarios_tested', 'N/A')}")
        
        if scenario_results:
            print(f"\n📋 Top Risk Scenarios:")
            # Sort by impact percentage and show top 3
            sorted_scenarios = sorted(
                scenario_results, 
                key=lambda x: x.get('impact_percentage', 0), 
                reverse=True
            )
            
            for i, scenario in enumerate(sorted_scenarios[:3], 1):
                scenario_name = scenario.get('scenario', 'N/A').replace('_', ' ').title()
                impact = scenario.get('impact_percentage', 'N/A')
                survival = scenario.get('survival_probability', 'N/A')
                print(f"   {i}. {scenario_name}: {impact}% impact, {survival} survival rate")
        
        critical_vulnerabilities = risk_analysis.get('critical_vulnerabilities', [])
        if critical_vulnerabilities:
            print(f"\n⚠️ Critical Vulnerabilities:")
            for i, vulnerability in enumerate(critical_vulnerabilities[:3], 1):
                print(f"   {i}. {vulnerability}")
        
        immediate_actions = recommendations.get('immediate_actions', [])
        if immediate_actions:
            print(f"\n🚀 Immediate Actions:")
            for i, action in enumerate(immediate_actions[:3], 1):
                print(f"   {i}. {action}")
    
    except Exception as e:
        logger.error(f"Error in stress testing demonstration: {e}")
        print(f"❌ Error: {e}")


async def main():
    """Main demonstration function."""
    print("🚀 KDP Strategist AI Agent - Basic Usage Demonstration")
    print("This example shows how to use the KDP Strategist programmatically.")
    print("\nNote: This demonstration uses simulated data for API calls.")
    print("In production, ensure you have valid API keys configured.")
    
    try:
        # Load configuration
        settings = load_settings()
        
        # Initialize the agent
        print("\n🔧 Initializing KDP Strategist Agent...")
        agent = KDPStrategistAgent(settings)
        await agent.initialize()
        
        print("✅ Agent initialized successfully!")
        print(f"🛠️ Available tools: {', '.join(await agent.list_tools())}")
        
        # Run demonstrations
        await demonstrate_niche_discovery(agent)
        await demonstrate_competitor_analysis(agent)
        await demonstrate_listing_generation(agent)
        await demonstrate_trend_validation(agent)
        await demonstrate_stress_testing(agent)
        
        print("\n" + "="*60)
        print("🎉 DEMONSTRATION COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\n💡 Next Steps:")
        print("   1. Configure your API keys in the .env file")
        print("   2. Run the agent in interactive mode: kdp_strategist --interactive")
        print("   3. Integrate the agent into your publishing workflow")
        print("   4. Explore advanced features and customization options")
        
        # Cleanup
        await agent.cleanup()
        
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        print(f"\n❌ Demonstration failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Ensure all dependencies are installed: pip install -r requirements.txt")
        print("   2. Check your configuration in the .env file")
        print("   3. Verify your Python environment and version (3.8+)")
        print("   4. Check the logs for detailed error information")


if __name__ == "__main__":
    # Handle Windows event loop policy
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Demonstration interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n💥 Fatal error: {e}")