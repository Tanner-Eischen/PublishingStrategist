#!/usr/bin/env python3
"""Test configuration validation with invalid values."""

import os
from config.settings import Settings, ConfigurationError

# Test 1: Invalid environment
print("=== Test 1: Invalid Environment ===")
os.environ['ENVIRONMENT'] = 'invalid_env'
try:
    settings = Settings.from_env()
    print("ERROR: Should have failed with invalid environment")
except ConfigurationError as e:
    print(f"✓ Correctly caught invalid environment: {e}")

# Test 2: Invalid cache type
print("\n=== Test 2: Invalid Cache Type ===")
os.environ['ENVIRONMENT'] = 'development'
os.environ['CACHE_TYPE'] = 'invalid_cache'
try:
    settings = Settings.from_env()
    print("ERROR: Should have failed with invalid cache type")
except ConfigurationError as e:
    print(f"✓ Correctly caught invalid cache type: {e}")

# Test 3: Invalid business weights
print("\n=== Test 3: Invalid Business Weights ===")
os.environ['CACHE_TYPE'] = 'file'
os.environ['TREND_WEIGHT'] = '0.5'
os.environ['COMPETITION_WEIGHT'] = '0.5'
os.environ['PROFITABILITY_WEIGHT'] = '0.5'  # Sum = 1.5, should fail
try:
    settings = Settings.from_env()
    print("ERROR: Should have failed with invalid weights")
except ConfigurationError as e:
    print(f"✓ Correctly caught invalid weights: {e}")

# Test 4: Production without API key
print("\n=== Test 4: Production Without API Key ===")
os.environ['ENVIRONMENT'] = 'production'
os.environ['TREND_WEIGHT'] = '0.4'
os.environ['COMPETITION_WEIGHT'] = '0.3'
os.environ['PROFITABILITY_WEIGHT'] = '0.3'
# Don't set KEEPA_API_KEY
try:
    settings = Settings.from_env()
    print("ERROR: Should have failed without API key in production")
except ConfigurationError as e:
    print(f"✓ Correctly caught missing API key in production: {e}")

print("\n=== All validation tests completed ===")