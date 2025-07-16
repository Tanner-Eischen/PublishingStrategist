"""Test script to debug configuration validation issues."""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def test_config_validation():
    """Test configuration validation with current environment."""
    print("Testing configuration validation...")
    
    # Print current environment variables
    print("\nCurrent environment variables:")
    config_vars = [
        'CACHE_TYPE', 'ENVIRONMENT', 'DEBUG', 'LOG_LEVEL',
        'TREND_WEIGHT', 'COMPETITION_WEIGHT', 'PROFITABILITY_WEIGHT'
    ]
    
    for var in config_vars:
        value = os.getenv(var, 'NOT_SET')
        print(f"  {var} = {value}")
    
    # Try to create settings
    try:
        from config.settings import Settings
        settings = Settings.from_env()
        print("\n✓ Configuration validation passed!")
        
        # Print some key settings
        print(f"  Cache type: {settings.cache.cache_type}")
        print(f"  Environment: {settings.environment}")
        print(f"  Debug: {settings.debug}")
        print(f"  Log level: {settings.logging.level}")
        
        # Check weights sum
        weights_sum = (settings.business.trend_weight + 
                      settings.business.competition_weight + 
                      settings.business.profitability_weight)
        print(f"  Business weights sum: {weights_sum}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Configuration validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_config_validation()
    sys.exit(0 if success else 1)