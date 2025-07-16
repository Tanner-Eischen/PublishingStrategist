"""Test script to verify error handling infrastructure.

This script tests the custom exceptions, error handlers, logging configuration,
and health check endpoints to ensure they work correctly.
"""

import asyncio
import logging
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
from src.kdp_strategist.logging_config import configure_logging, get_logger
from src.kdp_strategist.health import get_health_checker


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


def test_logging_configuration():
    """Test logging configuration."""
    print("\nTesting logging configuration...")
    
    # Configure logging
    configure_logging()
    
    # Test logger creation
    logger = get_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    print("✓ Logger creation works correctly")
    
    # Test logging with different levels
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    print("✓ Logging with different levels works correctly")
    
    # Test structured logging with context
    logger.info("Test message with context", extra={
        "user_id": "123",
        "operation": "test",
        "duration_ms": 150.5
    })
    print("✓ Structured logging with context works correctly")


async def test_health_checks():
    """Test health check system."""
    print("\nTesting health checks...")
    
    health_checker = get_health_checker()
    
    # Test basic health check
    app_health = await health_checker.check_application_health()
    assert app_health.name == "application"
    assert app_health.status.value in ["healthy", "degraded", "unhealthy", "unknown"]
    print("✓ Application health check works correctly")
    
    # Test memory check
    memory_health = await health_checker.check_memory_usage()
    assert memory_health.name == "memory"
    assert memory_health.duration_ms > 0
    print("✓ Memory health check works correctly")
    
    # Test disk check
    disk_health = await health_checker.check_disk_space()
    assert disk_health.name == "disk"
    assert disk_health.duration_ms > 0
    print("✓ Disk health check works correctly")
    
    # Test system health check
    system_health = await health_checker.check_system_health(include_detailed=False)
    assert system_health.status.value in ["healthy", "degraded", "unhealthy", "unknown"]
    assert len(system_health.checks) >= 3  # At least app, memory, disk
    assert system_health.uptime_seconds > 0
    print("✓ System health check works correctly")
    
    # Test detailed health check
    detailed_health = await health_checker.check_system_health(include_detailed=True)
    assert len(detailed_health.checks) > len(system_health.checks)
    print("✓ Detailed health check works correctly")
    
    # Test health serialization
    health_dict = system_health.to_dict()
    assert "status" in health_dict
    assert "timestamp" in health_dict
    assert "uptime_seconds" in health_dict
    assert "checks" in health_dict
    print("✓ Health check serialization works correctly")


def test_error_context():
    """Test error context functionality."""
    print("\nTesting error context...")
    
    from src.kdp_strategist.error_handlers import ErrorContext
    
    # Test successful operation
    with ErrorContext("test_operation", user_id="123"):
        pass
    print("✓ Error context for successful operation works correctly")
    
    # Test failed operation
    try:
        with ErrorContext("failing_operation", user_id="456"):
            raise ValueError("Test error")
    except ValueError:
        pass
    print("✓ Error context for failed operation works correctly")


async def main():
    """Run all tests."""
    print("Starting error handling infrastructure tests...\n")
    
    try:
        test_custom_exceptions()
        test_logging_configuration()
        await test_health_checks()
        test_error_context()
        
        print("\n✅ All tests passed! Error handling infrastructure is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)