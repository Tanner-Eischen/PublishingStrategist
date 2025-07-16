"""Simple test script to verify error handling infrastructure.

This script tests the custom exceptions and basic functionality without
requiring full configuration setup.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.kdp_strategist.exceptions import (
    KDPStrategistError,
    ConfigurationError,
    APIClientError,
    RateLimitExceededError,
    DataValidationError,
    ErrorCode
)


def test_custom_exceptions():
    """Test custom exception classes."""
    print("Testing custom exceptions...")
    
    # Test base exception
    try:
        raise KDPStrategistError(
            message="Test error",
            error_code=ErrorCode.INTERNAL_ERROR,
            details={"test": "data"}
        )
    except KDPStrategistError as e:
        assert e.message == "Test error"
        assert e.error_code == ErrorCode.INTERNAL_ERROR
        assert e.details == {"test": "data"}
        print("✓ Base KDPStrategistError works correctly")
    
    # Test configuration error
    try:
        raise ConfigurationError(
            message="Missing configuration",
            missing_keys=["API_KEY"],
            invalid_values={"timeout": -1}
        )
    except ConfigurationError as e:
        assert e.error_code == ErrorCode.CONFIGURATION_ERROR
        assert "API_KEY" in e.details["missing_keys"]
        print("✓ ConfigurationError works correctly")
    
    # Test rate limit error
    try:
        raise RateLimitExceededError(
            service_name="test_api",
            retry_after=60
        )
    except RateLimitExceededError as e:
        assert e.error_code == ErrorCode.RATE_LIMIT_EXCEEDED
        assert e.retry_after == 60
        print("✓ RateLimitExceededError works correctly")
    
    # Test error serialization
    error = DataValidationError(
        message="Invalid field",
        field_name="email",
        field_value="invalid-email"
    )
    error_dict = error.to_dict()
    assert error_dict["error"] == ErrorCode.DATA_VALIDATION_ERROR.value
    assert error_dict["message"] == "Invalid field"
    assert error_dict["details"]["field_name"] == "email"
    print("✓ Error serialization works correctly")


def test_error_codes():
    """Test error code enumeration."""
    print("\nTesting error codes...")
    
    # Test that all error codes are accessible
    assert ErrorCode.CONFIGURATION_ERROR.value == "CONFIGURATION_ERROR"
    assert ErrorCode.API_CLIENT_ERROR.value == "API_CLIENT_ERROR"
    assert ErrorCode.RATE_LIMIT_EXCEEDED.value == "RATE_LIMIT_EXCEEDED"
    assert ErrorCode.DATA_VALIDATION_ERROR.value == "DATA_VALIDATION_ERROR"
    print("✓ Error codes work correctly")


def test_exception_chaining():
    """Test exception chaining with cause."""
    print("\nTesting exception chaining...")
    
    original_error = ValueError("Original error")
    
    try:
        raise KDPStrategistError(
            message="Wrapped error",
            error_code=ErrorCode.INTERNAL_ERROR,
            cause=original_error
        )
    except KDPStrategistError as e:
        assert e.cause == original_error
        assert str(e.cause) == "Original error"
        print("✓ Exception chaining works correctly")


def test_api_client_errors():
    """Test API client specific errors."""
    print("\nTesting API client errors...")
    
    # Test API client error
    api_error = APIClientError(
        message="API request failed",
        service_name="test_service",
        status_code=500,
        response_data={"error": "Internal server error"}
    )
    
    assert api_error.details["service"] == "test_service"
    assert api_error.details["status_code"] == 500
    assert api_error.details["response_data"]["error"] == "Internal server error"
    print("✓ API client error works correctly")
    
    # Test rate limit error with retry after
    rate_limit_error = RateLimitExceededError(
        service_name="keepa",
        retry_after=120,
        quota_type="tokens"
    )
    
    assert rate_limit_error.retry_after == 120
    assert rate_limit_error.details["quota_type"] == "tokens"
    print("✓ Rate limit error with retry after works correctly")


def main():
    """Run all tests."""
    print("Starting basic error handling tests...\n")
    
    try:
        test_custom_exceptions()
        test_error_codes()
        test_exception_chaining()
        test_api_client_errors()
        
        print("\n✅ All basic tests passed! Error handling infrastructure is working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)