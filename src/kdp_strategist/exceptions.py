"""Consolidated error handling classes for KDP Strategist.

This module provides a unified error handling system with structured error responses,
retry logic, and comprehensive error categorization for all KDP Strategist components.
"""

from typing import Optional, Dict, Any, List, Union, Callable
from enum import Enum
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import logging
import time
import random
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class RequestContext:
    """Context information for API requests to aid in error handling and debugging."""
    endpoint: str
    method: str = "GET"
    params: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    attempt: int = 1
    max_attempts: int = 3
    start_time: Optional[datetime] = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()
    
    def get_duration(self) -> float:
        """Get request duration in seconds."""
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0


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
    """Base exception class for all KDP Strategist errors with enhanced functionality."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[Union[ErrorCode, str]] = None,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
        context: Optional[RequestContext] = None,
        fallback_data: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        self.message = message
        self.error_code = error_code or ErrorCode.INTERNAL_ERROR
        self.details = details or {}
        self.suggestions = suggestions or []
        self.context = context
        self.fallback_data = fallback_data
        self.cause = cause
        self.timestamp = datetime.now()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to structured dictionary for API responses."""
        error_dict = {
            "error": {
                "type": self.__class__.__name__,
                "message": self.message,
                "code": self.error_code.value if hasattr(self.error_code, 'value') else str(self.error_code),
                "details": self.details,
                "suggestions": self.suggestions,
                "timestamp": self.timestamp.isoformat(),
                "cause": str(self.cause) if self.cause else None
            }
        }
        
        # Add context information if available
        if self.context:
            error_dict["error"]["context"] = {
                "endpoint": self.context.endpoint,
                "method": self.context.method,
                "attempt": self.context.attempt,
                "max_attempts": self.context.max_attempts,
                "duration_seconds": self.context.get_duration()
            }
        
        # Add fallback data if available
        if self.fallback_data:
            error_dict["fallback_data"] = self.fallback_data
        
        return error_dict


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


# Backward compatibility alias
APIError = APIClientError


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
        
        # Create details for the parent class
        additional_details = {"quota_type": quota_type}
        if retry_after:
            additional_details["retry_after"] = retry_after
        
        super().__init__(
            message=message,
            service_name=service_name,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            cause=cause
        )
        
        # Merge additional details with parent details
        self.details.update(additional_details)
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
    """Raised when external service calls fail."""
    
    def __init__(
        self, 
        message: str, 
        service_name: str,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        self.service_name = service_name
        service_details = details or {}
        service_details["service_name"] = service_name
        
        super().__init__(
            message=message,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            details=service_details,
            **kwargs
        )


# Keepa-Specific Error Classes

class KeepaAPIError(APIClientError):
    """Base class for Keepa API specific errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
        keepa_error_code: Optional[str] = None,
        **kwargs
    ):
        # Extract details and suggestions to avoid conflicts
        existing_details = kwargs.pop("details", {})
        existing_suggestions = kwargs.pop("suggestions", [])
        
        # Prepare Keepa-specific details
        keepa_details = {
            "api_name": "keepa",
            "status_code": status_code,
            "response_text": response_text[:500] if response_text else None,
            "keepa_error_code": keepa_error_code
        }
        
        # Merge details
        existing_details.update(keepa_details)
        
        # Prepare suggestions
        if not existing_suggestions:
            existing_suggestions = self._get_keepa_error_suggestions(status_code, keepa_error_code)
        
        super().__init__(
            message=message,
            service_name="keepa",
            error_code=ErrorCode.API_CLIENT_ERROR if not error_code else error_code,
            status_code=status_code,
            response_data=existing_details,
            cause=kwargs.get("cause")
        )
        
        # Override details and suggestions after parent initialization
        self.details = existing_details
        self.suggestions = existing_suggestions
    
    def _get_keepa_error_suggestions(self, status_code: Optional[int], keepa_error_code: Optional[str]) -> List[str]:
        """Get Keepa-specific error suggestions."""
        suggestions = []
        
        if status_code == 400:
            suggestions.extend([
                "Check request parameters format",
                "Verify ASIN format (10 characters, alphanumeric)",
                "Ensure domain parameter is valid (0-10)",
                "Check that required parameters are included"
            ])
        elif status_code == 401:
            suggestions.extend([
                "Verify Keepa API key is correct and active",
                "Check if API key has sufficient permissions",
                "Ensure API key is not expired",
                "Contact Keepa support if key should be valid"
            ])
        elif status_code == 402:
            suggestions.extend([
                "Insufficient Keepa API tokens remaining",
                "Check your Keepa account token balance",
                "Consider upgrading your Keepa plan",
                "Wait for token reset if on free plan"
            ])
        elif status_code == 429:
            suggestions.extend([
                "Keepa rate limit exceeded",
                "Implement exponential backoff retry logic",
                "Reduce request frequency",
                "Use cached data when available",
                "Consider upgrading to higher rate limit plan"
            ])
        elif status_code == 503:
            suggestions.extend([
                "Keepa service temporarily unavailable",
                "Try again in a few minutes",
                "Check Keepa status page for service issues",
                "Use cached data as fallback"
            ])
        elif keepa_error_code:
            if "ASIN" in keepa_error_code.upper():
                suggestions.extend([
                    "Verify ASIN format and validity",
                    "Check if product exists on Amazon",
                    "Try with a different ASIN"
                ])
            elif "DOMAIN" in keepa_error_code.upper():
                suggestions.extend([
                    "Check domain parameter (0=US, 1=UK, 2=DE, etc.)",
                    "Ensure domain matches the marketplace"
                ])
        
        if not suggestions:
            suggestions.extend([
                "Check Keepa API documentation for parameter requirements",
                "Verify network connectivity",
                "Try again with different parameters"
            ])
        
        return suggestions


class KeepaRateLimitError(KeepaAPIError):
    """Keepa API rate limit exceeded error with retry information."""
    
    def __init__(
        self,
        retry_after: Optional[int] = None,
        current_usage: Optional[int] = None,
        limit: Optional[int] = None,
        **kwargs
    ):
        self.retry_after = retry_after or 60  # Default 1 minute
        self.current_usage = current_usage
        self.limit = limit
        
        message = "Keepa API rate limit exceeded"
        if current_usage and limit:
            message += f": {current_usage}/{limit} requests"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        
        # Prepare details without conflicting with parent class
        rate_limit_details = {
            "retry_after_seconds": self.retry_after,
            "current_usage": current_usage,
            "rate_limit": limit,
            "reset_time": (datetime.now() + timedelta(seconds=self.retry_after)).isoformat()
        }
        
        # Merge with any existing details
        existing_details = kwargs.pop("details", {})
        existing_details.update(rate_limit_details)
        
        suggestions = [
            f"Wait {self.retry_after} seconds before retrying",
            "Implement exponential backoff with jitter",
            "Use cached data if available",
            "Consider reducing request frequency",
            "Upgrade to higher rate limit plan if needed"
        ]
        
        super().__init__(
            message=message,
            error_code="KEEPA_RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=existing_details,
            suggestions=suggestions,
            **kwargs
        )


class KeepaAuthenticationError(KeepaAPIError):
    """Keepa API authentication/authorization error."""
    
    def __init__(self, message: Optional[str] = None, **kwargs):
        message = message or "Keepa API authentication failed"
        
        # Extract suggestions to avoid conflicts
        existing_suggestions = kwargs.pop("suggestions", [])
        suggestions = [
            "Verify Keepa API key is correct",
            "Check if API key is active and not expired",
            "Ensure API key has required permissions",
            "Check environment variable KEEPA_API_KEY",
            "Contact Keepa support if key should be valid"
        ]
        suggestions.extend(existing_suggestions)
        
        super().__init__(
            message=message,
            error_code="KEEPA_AUTHENTICATION_FAILED",
            status_code=401,
            suggestions=suggestions,
            **kwargs
        )


class KeepaTimeoutError(KeepaAPIError):
    """Keepa API request timeout error with retry logic."""
    
    def __init__(
        self,
        timeout_duration: float,
        operation: str = "API request",
        **kwargs
    ):
        self.timeout_duration = timeout_duration
        self.operation = operation
        
        message = f"Keepa {operation} timed out after {timeout_duration} seconds"
        
        # Prepare details without conflicting with parent class
        timeout_details = {
            "timeout_duration": timeout_duration,
            "operation": operation,
            "timeout_type": "request_timeout"
        }
        
        # Merge with any existing details
        existing_details = kwargs.pop("details", {})
        existing_details.update(timeout_details)
        
        # Extract suggestions to avoid conflicts
        existing_suggestions = kwargs.pop("suggestions", [])
        suggestions = [
            "Retry the request with exponential backoff",
            f"Consider increasing timeout from {timeout_duration}s",
            "Check network connectivity",
            "Use cached data if available",
            "Try with smaller batch sizes if applicable"
        ]
        suggestions.extend(existing_suggestions)
        
        super().__init__(
            message=message,
            error_code="KEEPA_TIMEOUT_ERROR",
            details=existing_details,
            suggestions=suggestions,
            **kwargs
        )


class KeepaDataParsingError(KeepaAPIError):
    """Keepa API response data parsing error."""
    
    def __init__(
        self,
        field: str,
        raw_value: Any,
        expected_type: str,
        asin: Optional[str] = None,
        **kwargs
    ):
        self.field = field
        self.raw_value = raw_value
        self.expected_type = expected_type
        self.asin = asin
        
        message = f"Failed to parse Keepa field '{field}'"
        if asin:
            message += f" for ASIN '{asin}'"
        message += f": expected {expected_type}, got {type(raw_value).__name__}"
        
        # Prepare details without conflicting with parent class
        parsing_details = {
            "field": field,
            "raw_value": str(raw_value)[:200] if raw_value is not None else None,
            "raw_value_type": type(raw_value).__name__,
            "expected_type": expected_type,
            "asin": asin
        }
        
        # Merge with any existing details
        existing_details = kwargs.pop("details", {})
        existing_details.update(parsing_details)
        
        # Extract suggestions to avoid conflicts
        existing_suggestions = kwargs.pop("suggestions", [])
        suggestions = [
            "Check Keepa API response format",
            "Verify field exists in response",
            "Handle missing or null values gracefully",
            "Use fallback parsing logic",
            "Report parsing issue if data format changed"
        ]
        suggestions.extend(existing_suggestions)
        
        super().__init__(
            message=message,
            error_code="KEEPA_DATA_PARSING_ERROR",
            details=existing_details,
            suggestions=suggestions,
            **kwargs
        )


class KeepaServiceUnavailableError(KeepaAPIError):
    """Keepa service unavailable error with fallback suggestions."""
    
    def __init__(self, message=None, **kwargs):
        if message is None:
            message = "Keepa API service is temporarily unavailable"
        
        # Extract suggestions to avoid conflicts
        existing_suggestions = kwargs.pop("suggestions", [])
        suggestions = [
            "Use cached data if available",
            "Retry with exponential backoff",
            "Check Keepa status page for service issues",
            "Implement circuit breaker pattern",
            "Try again in a few minutes"
        ]
        suggestions.extend(existing_suggestions)
        
        super().__init__(
            message=message,
            error_code="KEEPA_SERVICE_UNAVAILABLE",
            status_code=503,
            suggestions=suggestions,
            **kwargs
        )


# Additional Error Classes

class ValidationError(KDPStrategistError):
    """Error for parameter validation failures."""
    
    def __init__(
        self,
        message: str,
        parameter: Optional[str] = None,
        value: Optional[Any] = None,
        expected_type: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        details.update({
            "parameter": parameter,
            "provided_value": str(value) if value is not None else None,
            "expected_type": expected_type
        })
        
        suggestions = kwargs.get("suggestions", [])
        if not suggestions:
            suggestions = self._get_validation_suggestions(parameter, expected_type)
        
        super().__init__(
            message=message,
            error_code=ErrorCode.DATA_VALIDATION_ERROR,
            details=details,
            suggestions=suggestions,
            **kwargs
        )
    
    def _get_validation_suggestions(self, parameter: Optional[str], expected_type: Optional[str]) -> List[str]:
        """Get suggestions for validation errors."""
        suggestions = []
        
        if parameter:
            suggestions.append(f"Check the '{parameter}' parameter")
        
        if expected_type:
            suggestions.append(f"Ensure value is of type: {expected_type}")
        
        suggestions.append("Refer to tool documentation for valid parameter formats")
        return suggestions


class ToolExecutionError(KDPStrategistError):
    """Error for tool execution failures."""
    
    def __init__(
        self,
        message: str,
        tool_name: str,
        operation: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        details.update({
            "tool_name": tool_name,
            "operation": operation
        })
        
        suggestions = kwargs.get("suggestions", [])
        if not suggestions:
            suggestions = [
                f"Check {tool_name} tool requirements",
                "Verify input parameters are correct",
                "Try again with different parameters"
            ]
        
        super().__init__(
            message=message,
            error_code=f"TOOL_ERROR_{tool_name.upper()}",
            details=details,
            suggestions=suggestions,
            **kwargs
        )


# Utility Functions

def create_error_response(
    error: Union[KDPStrategistError, Exception],
    tool_name: Optional[str] = None,
    fallback_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a structured error response from an exception.
    
    Args:
        error: The exception to convert
        tool_name: Name of the tool that failed (optional)
        fallback_data: Any fallback data to include (optional)
    
    Returns:
        Structured error response dictionary
    """
    if isinstance(error, KDPStrategistError):
        response = error.to_dict()
    else:
        # Handle generic exceptions
        response = {
            "error": {
                "type": "UnexpectedError",
                "message": str(error),
                "code": "UNEXPECTED_ERROR",
                "details": {
                    "exception_type": type(error).__name__
                },
                "suggestions": [
                    "This is an unexpected error",
                    "Please try again or contact support if the issue persists"
                ],
                "timestamp": datetime.now().isoformat()
            }
        }
    
    # Add tool context if provided
    if tool_name:
        response["error"]["details"]["tool_name"] = tool_name
    
    # Add fallback data if available
    if fallback_data:
        response["fallback_data"] = fallback_data
        response["error"]["details"]["has_fallback_data"] = True
    
    return response


def handle_api_error(
    error: Exception,
    operation: str = "API call",
    context: Optional[RequestContext] = None
) -> Dict[str, Any]:
    """Handle API errors with structured response.
    
    Args:
        error: The exception that occurred
        operation: Description of the operation that failed
        context: Request context information
    
    Returns:
        Structured error response
    """
    if isinstance(error, APIClientError):
        api_error = error
    else:
        # Convert generic exception to APIClientError
        api_error = APIClientError(
            message=f"{operation} failed: {str(error)}",
            service_name="unknown",
            context=context
        )
    
    return create_error_response(api_error)


def handle_validation_error(
    message: str,
    parameter: Optional[str] = None,
    value: Optional[Any] = None,
    expected_type: Optional[str] = None
) -> Dict[str, Any]:
    """Handle validation errors with structured response.
    
    Args:
        message: Error message
        parameter: Name of the invalid parameter
        value: The invalid value provided
        expected_type: Expected type or format
    
    Returns:
        Structured error response
    """
    validation_error = ValidationError(
        message=message,
        parameter=parameter,
        value=value,
        expected_type=expected_type
    )
    
    return create_error_response(validation_error)


def create_error_response_with_fallback(
    error: Exception,
    tool_name: Optional[str] = None,
    fallback_data: Optional[Dict[str, Any]] = None,
    context: Optional[RequestContext] = None
) -> Dict[str, Any]:
    """Create a structured error response with fallback data support.
    
    Args:
        error: The exception that occurred
        tool_name: Name of the tool that failed (optional)
        fallback_data: Any fallback data to include (optional)
        context: Request context information (optional)
    
    Returns:
        Structured error response dictionary with fallback data
    """
    if isinstance(error, KDPStrategistError):
        response = error.to_dict()
    else:
        # Handle generic exceptions
        response = {
            "error": {
                "type": "UnexpectedError",
                "message": str(error),
                "code": "UNEXPECTED_ERROR",
                "details": {
                    "exception_type": type(error).__name__
                },
                "suggestions": [
                    "This is an unexpected error",
                    "Please try again or contact support if the issue persists"
                ],
                "timestamp": datetime.now().isoformat()
            }
        }
    
    # Add tool context if provided
    if tool_name:
        response["error"]["details"]["tool_name"] = tool_name
    
    # Add request context if provided
    if context:
        response["error"]["context"] = {
            "endpoint": context.endpoint,
            "method": context.method,
            "attempt": context.attempt,
            "duration_seconds": context.get_duration()
        }
    
    # Add fallback data if available
    if fallback_data:
        response["fallback_data"] = fallback_data
        response["error"]["details"]["has_fallback_data"] = True
    
    return response


def handle_keepa_api_error(
    error: Exception,
    operation: str = "Keepa API call",
    context: Optional[RequestContext] = None,
    fallback_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Handle Keepa API errors with appropriate error response and fallback data.
    
    Args:
        error: The exception that occurred
        operation: Description of the operation that failed
        context: Request context information
        fallback_data: Any fallback data to include
    
    Returns:
        Structured error response with fallback data
    """
    # Create appropriate Keepa error if not already one
    if not isinstance(error, KeepaAPIError):
        if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
            # HTTP error with response
            keepa_error = KeepaAPIError(
                message=f"Keepa {operation} failed: {str(error)}",
                status_code=error.response.status_code,
                response_text=getattr(error.response, 'text', None),
                context=context,
                fallback_data=fallback_data
            )
        else:
            # Generic error
            keepa_error = KeepaAPIError(
                message=f"Keepa {operation} failed: {str(error)}",
                context=context,
                fallback_data=fallback_data
            )
    else:
        keepa_error = error
        # Add fallback data if not already present
        if fallback_data and not keepa_error.fallback_data:
            keepa_error.fallback_data = fallback_data
    
    return create_error_response_with_fallback(
        keepa_error,
        tool_name="keepa_client",
        context=context
    )


class KeepaErrorHandler:
    """Comprehensive error handler for Keepa API operations."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def handle_http_error(self, response, context: Optional[RequestContext] = None) -> KeepaAPIError:
        """Handle HTTP errors from Keepa API."""
        status_code = response.status_code
        response_text = getattr(response, 'text', '')
        
        # Extract error code from response headers or body
        error_code = self._extract_error_code(response)
        
        # Create appropriate error based on status code
        if status_code == 429:
            retry_after = self._extract_retry_after(response)
            return KeepaRateLimitError(
                retry_after=retry_after,
                context=context,
                status_code=status_code,
                response_text=response_text
            )
        elif status_code == 401:
            return KeepaAuthenticationError(
                context=context,
                status_code=status_code,
                response_text=response_text
            )
        elif status_code >= 500:
            return KeepaServiceUnavailableError(
                context=context,
                status_code=status_code,
                response_text=response_text
            )
        else:
            return KeepaAPIError(
                message=f"Keepa API request failed with status {status_code}",
                status_code=status_code,
                response_text=response_text,
                context=context
            )
    
    def handle_timeout_error(self, timeout_duration: float, context: Optional[RequestContext] = None) -> KeepaTimeoutError:
        """Handle timeout errors."""
        return KeepaTimeoutError(
            timeout_duration=timeout_duration,
            context=context
        )
    
    def handle_parsing_error(
        self,
        field: str,
        raw_value: Any,
        expected_type: str,
        context: Optional[RequestContext] = None
    ) -> KeepaDataParsingError:
        """Handle data parsing errors."""
        return KeepaDataParsingError(
            field=field,
            raw_value=raw_value,
            expected_type=expected_type,
            context=context
        )
    
    def _extract_error_code(self, response) -> Optional[str]:
        """Extract error code from response."""
        # Try to get from headers first
        if hasattr(response, 'headers'):
            error_code = response.headers.get('X-Error-Code')
            if error_code:
                return error_code
        
        # Try to parse from response body
        try:
            if hasattr(response, 'json'):
                data = response.json()
                return data.get('error', {}).get('code')
        except Exception:
            pass
        
        return None
    
    def _extract_retry_after(self, response) -> Optional[int]:
        """Extract retry-after value from response."""
        if hasattr(response, 'headers'):
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                try:
                    return int(retry_after)
                except ValueError:
                    pass
        return None


class RetryHandler:
    """Handles retry logic with exponential backoff and jitter."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.logger = logging.getLogger(__name__)
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if an operation should be retried."""
        if attempt >= self.max_retries:
            return False
        
        # Retry on specific error types
        if isinstance(error, (KeepaTimeoutError, KeepaServiceUnavailableError)):
            return True
        
        if isinstance(error, KeepaRateLimitError):
            return True
        
        return False
    
    def get_delay(self, attempt: int, retry_after: Optional[int] = None) -> float:
        """Calculate delay before next retry."""
        if retry_after:
            # Use server-specified delay
            delay = float(retry_after)
        else:
            # Calculate exponential backoff
            delay = self.base_delay * (self.exponential_base ** attempt)
        
        # Apply maximum delay limit
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
        
        # Ensure minimum delay
        delay = max(0.1, delay)
        
        return delay


class CircuitBreaker:
    """Circuit breaker pattern implementation for Keepa API resilience."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = KeepaAPIError
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.logger = logging.getLogger(__name__)
    
    async def call(self, operation, *args, **kwargs):
        """Execute operation through circuit breaker."""
        
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                self.logger.info("Circuit breaker transitioning to HALF_OPEN state")
            else:
                raise KeepaServiceUnavailableError(
                    details={"circuit_breaker_state": "OPEN"},
                    fallback_data=kwargs.get("fallback_data")
                )
        
        try:
            result = await operation(*args, **kwargs)
            self._on_success()
            return result
        
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        
        return (datetime.now() - self.last_failure_time).total_seconds() > self.recovery_timeout
    
    def _on_success(self):
        """Handle successful operation."""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.logger.info("Circuit breaker reset to CLOSED state")
        
        self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures. "
                f"Will retry after {self.recovery_timeout} seconds"
            )


class KeepaErrorLogger:
    """Comprehensive error logging for Keepa API operations."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def log_api_request(
        self,
        context: RequestContext,
        response_time: Optional[float] = None,
        response_size: Optional[int] = None,
        success: bool = True
    ):
        """Log API request details."""
        
        log_data = {
            "endpoint": context.endpoint,
            "method": context.method,
            "attempt": context.attempt,
            "success": success,
            "response_time_ms": round(response_time * 1000, 2) if response_time else None,
            "response_size_bytes": response_size
        }
        
        # Add sanitized parameters (remove sensitive data)
        if context.params:
            sanitized_params = self._sanitize_params(context.params)
            log_data["params"] = sanitized_params
        
        if success:
            self.logger.info(f"Keepa API request successful", extra=log_data)
        else:
            self.logger.error(f"Keepa API request failed", extra=log_data)
    
    def log_error_with_context(
        self,
        error: KeepaAPIError,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        """Log error with comprehensive context information."""
        
        log_data = {
            "error_type": type(error).__name__,
            "error_code": error.error_code,
            "error_message": error.message,
            "timestamp": error.timestamp.isoformat()
        }
        
        # Add context information
        if error.context:
            log_data.update({
                "endpoint": error.context.endpoint,
                "method": error.context.method,
                "attempt": error.context.attempt,
                "max_attempts": error.context.max_attempts,
                "duration_seconds": error.context.get_duration()
            })
        
        # Add error details
        if error.details:
            log_data["details"] = error.details
        
        # Add additional context
        if additional_context:
            log_data["additional_context"] = additional_context
        
        # Add fallback data availability
        log_data["has_fallback_data"] = error.fallback_data is not None
        
        self.logger.error("Keepa API error occurred", extra=log_data)
    
    def log_rate_limit_status(
        self,
        current_usage: int,
        limit: int,
        reset_time: Optional[datetime] = None
    ):
        """Log rate limit status for monitoring."""
        
        usage_percentage = (current_usage / limit) * 100 if limit > 0 else 0
        
        log_data = {
            "current_usage": current_usage,
            "rate_limit": limit,
            "usage_percentage": round(usage_percentage, 1),
            "reset_time": reset_time.isoformat() if reset_time else None
        }
        
        if usage_percentage >= 90:
            self.logger.warning("Keepa API rate limit nearly exceeded", extra=log_data)
        elif usage_percentage >= 75:
            self.logger.info("Keepa API rate limit usage high", extra=log_data)
        else:
            self.logger.debug("Keepa API rate limit status", extra=log_data)
    
    def log_cache_operation(
        self,
        operation: str,
        cache_key: str,
        hit: bool = False,
        size: Optional[int] = None
    ):
        """Log cache operations for performance monitoring."""
        
        log_data = {
            "cache_operation": operation,
            "cache_key": cache_key[:100],  # Truncate long keys
            "cache_hit": hit,
            "data_size_bytes": size
        }
        
        if hit:
            self.logger.debug("Cache hit", extra=log_data)
        else:
            self.logger.debug("Cache miss", extra=log_data)
    
    def log_batch_operation(
        self,
        total_items: int,
        successful_items: int,
        failed_items: int,
        cached_items: int,
        duration: float
    ):
        """Log batch operation summary."""
        
        success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
        cache_hit_rate = (cached_items / total_items) * 100 if total_items > 0 else 0
        
        log_data = {
            "batch_total_items": total_items,
            "batch_successful": successful_items,
            "batch_failed": failed_items,
            "batch_cached": cached_items,
            "batch_success_rate": round(success_rate, 1),
            "batch_cache_hit_rate": round(cache_hit_rate, 1),
            "batch_duration_seconds": round(duration, 2)
        }
        
        if success_rate >= 95:
            self.logger.info("Batch operation completed successfully", extra=log_data)
        elif success_rate >= 80:
            self.logger.warning("Batch operation completed with some failures", extra=log_data)
        else:
            self.logger.error("Batch operation had high failure rate", extra=log_data)
    
    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from parameters for logging."""
        sanitized = params.copy()
        
        # Remove or mask sensitive fields
        sensitive_fields = ["key", "api_key", "token", "password"]
        
        for field in sensitive_fields:
            if field in sanitized:
                if isinstance(sanitized[field], str) and len(sanitized[field]) > 8:
                    # Show first 4 and last 4 characters
                    sanitized[field] = f"{sanitized[field][:4]}...{sanitized[field][-4:]}"
                else:
                    sanitized[field] = "***"
        
        return sanitized