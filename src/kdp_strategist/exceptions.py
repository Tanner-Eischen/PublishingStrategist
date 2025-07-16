"""Custom exception classes for KDP Strategist application.

This module defines custom exception classes for different error types
to provide better error handling and debugging capabilities.
"""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorCode(Enum):
    """Standard error codes for the application."""
    # Configuration errors
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    MISSING_API_KEY = "MISSING_API_KEY"
    INVALID_ENVIRONMENT = "INVALID_ENVIRONMENT"
    
    # API client errors
    API_CLIENT_ERROR = "API_CLIENT_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    API_AUTHENTICATION_ERROR = "API_AUTHENTICATION_ERROR"
    API_TIMEOUT_ERROR = "API_TIMEOUT_ERROR"
    API_QUOTA_EXCEEDED = "API_QUOTA_EXCEEDED"
    
    # Data validation errors
    DATA_VALIDATION_ERROR = "DATA_VALIDATION_ERROR"
    INVALID_INPUT_FORMAT = "INVALID_INPUT_FORMAT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    
    # Cache errors
    CACHE_ERROR = "CACHE_ERROR"
    CACHE_CONNECTION_ERROR = "CACHE_CONNECTION_ERROR"
    CACHE_SERIALIZATION_ERROR = "CACHE_SERIALIZATION_ERROR"
    
    # Database errors
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_QUERY_ERROR = "DATABASE_QUERY_ERROR"
    
    # Business logic errors
    BUSINESS_LOGIC_ERROR = "BUSINESS_LOGIC_ERROR"
    INSUFFICIENT_DATA_ERROR = "INSUFFICIENT_DATA_ERROR"
    ANALYSIS_FAILED_ERROR = "ANALYSIS_FAILED_ERROR"
    
    # External service errors
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    NETWORK_ERROR = "NETWORK_ERROR"
    
    # Internal errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"


class KDPStrategistError(Exception):
    """Base exception class for KDP Strategist application."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.cause = cause
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.error_code.value,
            "message": self.message,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None
        }


class ConfigurationError(KDPStrategistError):
    """Raised when configuration is invalid or missing required values."""
    
    def __init__(
        self,
        message: str,
        missing_keys: Optional[list] = None,
        invalid_values: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = {}
        if missing_keys:
            details["missing_keys"] = missing_keys
        if invalid_values:
            details["invalid_values"] = invalid_values
        
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFIGURATION_ERROR,
            details=details,
            cause=cause
        )


class APIClientError(KDPStrategistError):
    """Base class for external API client errors."""
    
    def __init__(
        self,
        message: str,
        service_name: str,
        error_code: ErrorCode = ErrorCode.API_CLIENT_ERROR,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = {"service": service_name}
        if status_code:
            details["status_code"] = status_code
        if response_data:
            details["response_data"] = response_data
        
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            cause=cause
        )


class RateLimitExceededError(APIClientError):
    """Raised when API rate limit is exceeded."""
    
    def __init__(
        self,
        service_name: str,
        retry_after: Optional[int] = None,
        quota_type: str = "requests",
        cause: Optional[Exception] = None
    ):
        message = f"Rate limit exceeded for {service_name}"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        
        details = {"quota_type": quota_type}
        if retry_after:
            details["retry_after"] = retry_after
        
        super().__init__(
            message=message,
            service_name=service_name,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            cause=cause
        )
        self.retry_after = retry_after


class APIAuthenticationError(APIClientError):
    """Raised when API authentication fails."""
    
    def __init__(
        self,
        service_name: str,
        auth_type: str = "api_key",
        cause: Optional[Exception] = None
    ):
        message = f"Authentication failed for {service_name} using {auth_type}"
        
        super().__init__(
            message=message,
            service_name=service_name,
            error_code=ErrorCode.API_AUTHENTICATION_ERROR,
            cause=cause
        )


class APITimeoutError(APIClientError):
    """Raised when API request times out."""
    
    def __init__(
        self,
        service_name: str,
        timeout_seconds: int,
        operation: str = "request",
        cause: Optional[Exception] = None
    ):
        message = f"{service_name} {operation} timed out after {timeout_seconds} seconds"
        
        details = {"timeout_seconds": timeout_seconds, "operation": operation}
        
        super().__init__(
            message=message,
            service_name=service_name,
            error_code=ErrorCode.API_TIMEOUT_ERROR,
            details=details,
            cause=cause
        )


class DataValidationError(KDPStrategistError):
    """Raised when data validation fails."""
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        validation_rules: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = {}
        if field_name:
            details["field_name"] = field_name
        if field_value is not None:
            details["field_value"] = str(field_value)
        if validation_rules:
            details["validation_rules"] = validation_rules
        
        super().__init__(
            message=message,
            error_code=ErrorCode.DATA_VALIDATION_ERROR,
            details=details,
            cause=cause
        )


class CacheError(KDPStrategistError):
    """Base class for cache-related errors."""
    
    def __init__(
        self,
        message: str,
        cache_type: str,
        operation: str,
        cache_key: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        details = {
            "cache_type": cache_type,
            "operation": operation
        }
        if cache_key:
            details["cache_key"] = cache_key
        
        super().__init__(
            message=message,
            error_code=ErrorCode.CACHE_ERROR,
            details=details,
            cause=cause
        )


class DatabaseError(KDPStrategistError):
    """Base class for database-related errors."""
    
    def __init__(
        self,
        message: str,
        operation: str,
        table_name: Optional[str] = None,
        query: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        details = {"operation": operation}
        if table_name:
            details["table_name"] = table_name
        if query:
            details["query"] = query
        
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_ERROR,
            details=details,
            cause=cause
        )


class BusinessLogicError(KDPStrategistError):
    """Raised when business logic validation fails."""
    
    def __init__(
        self,
        message: str,
        operation: str,
        input_data: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = {"operation": operation}
        if input_data:
            details["input_data"] = input_data
        
        super().__init__(
            message=message,
            error_code=ErrorCode.BUSINESS_LOGIC_ERROR,
            details=details,
            cause=cause
        )


class ExternalServiceError(KDPStrategistError):
    """Raised when external service is unavailable or fails."""
    
    def __init__(
        self,
        message: str,
        service_name: str,
        service_url: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        details = {"service_name": service_name}
        if service_url:
            details["service_url"] = service_url
        
        super().__init__(
            message=message,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            details=details,
            cause=cause
        )