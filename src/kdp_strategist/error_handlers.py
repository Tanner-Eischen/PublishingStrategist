"""Global error handlers for FastAPI application.

This module provides centralized error handling for the KDP Strategist API,
including custom exception handlers and response formatting.
"""

import logging
import traceback
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .exceptions import (
    KDPStrategistError,
    ConfigurationError,
    APIClientError,
    RateLimitExceededError,
    APIAuthenticationError,
    APITimeoutError,
    DataValidationError,
    CacheError,
    DatabaseError,
    BusinessLogicError,
    ExternalServiceError,
    ErrorCode
)

logger = logging.getLogger(__name__)


def create_error_response(
    error_code: str,
    message: str,
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> JSONResponse:
    """Create standardized error response."""
    content = {
        "error": error_code,
        "message": message,
        "status_code": status_code
    }
    
    if details:
        content["details"] = details
    
    if request_id:
        content["request_id"] = request_id
    
    return JSONResponse(
        status_code=status_code,
        content=content
    )


async def kdp_strategist_exception_handler(request: Request, exc: KDPStrategistError) -> JSONResponse:
    """Handle custom KDP Strategist exceptions."""
    request_id = getattr(request.state, 'request_id', None)
    
    # Log the error with appropriate level
    if isinstance(exc, (ConfigurationError, APIAuthenticationError)):
        logger.error(f"Configuration/Auth error: {exc.message}", extra={
            "error_code": exc.error_code.value,
            "details": exc.details,
            "request_id": request_id
        })
        status_code = 500
    elif isinstance(exc, RateLimitExceededError):
        logger.warning(f"Rate limit exceeded: {exc.message}", extra={
            "error_code": exc.error_code.value,
            "details": exc.details,
            "request_id": request_id
        })
        status_code = 429
    elif isinstance(exc, DataValidationError):
        logger.warning(f"Data validation error: {exc.message}", extra={
            "error_code": exc.error_code.value,
            "details": exc.details,
            "request_id": request_id
        })
        status_code = 400
    elif isinstance(exc, APITimeoutError):
        logger.warning(f"API timeout: {exc.message}", extra={
            "error_code": exc.error_code.value,
            "details": exc.details,
            "request_id": request_id
        })
        status_code = 504
    elif isinstance(exc, ExternalServiceError):
        logger.error(f"External service error: {exc.message}", extra={
            "error_code": exc.error_code.value,
            "details": exc.details,
            "request_id": request_id
        })
        status_code = 503
    elif isinstance(exc, BusinessLogicError):
        logger.warning(f"Business logic error: {exc.message}", extra={
            "error_code": exc.error_code.value,
            "details": exc.details,
            "request_id": request_id
        })
        status_code = 422
    else:
        logger.error(f"KDP Strategist error: {exc.message}", extra={
            "error_code": exc.error_code.value,
            "details": exc.details,
            "request_id": request_id
        })
        status_code = 500
    
    return create_error_response(
        error_code=exc.error_code.value,
        message=exc.message,
        status_code=status_code,
        details=exc.details,
        request_id=request_id
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    request_id = getattr(request.state, 'request_id', None)
    
    logger.warning(f"Validation error: {exc}", extra={
        "request_id": request_id,
        "errors": exc.errors()
    })
    
    # Format validation errors for better user experience
    formatted_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        formatted_errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"]
        })
    
    return create_error_response(
        error_code=ErrorCode.DATA_VALIDATION_ERROR.value,
        message="Request validation failed",
        status_code=422,
        details={"validation_errors": formatted_errors},
        request_id=request_id
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    request_id = getattr(request.state, 'request_id', None)
    
    logger.warning(f"HTTP exception: {exc.detail}", extra={
        "status_code": exc.status_code,
        "request_id": request_id
    })
    
    return create_error_response(
        error_code="HTTP_ERROR",
        message=exc.detail,
        status_code=exc.status_code,
        request_id=request_id
    )


async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle Starlette HTTP exceptions."""
    request_id = getattr(request.state, 'request_id', None)
    
    logger.warning(f"Starlette HTTP exception: {exc.detail}", extra={
        "status_code": exc.status_code,
        "request_id": request_id
    })
    
    return create_error_response(
        error_code="HTTP_ERROR",
        message=exc.detail,
        status_code=exc.status_code,
        request_id=request_id
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions."""
    request_id = getattr(request.state, 'request_id', None)
    
    # Log the full traceback for debugging
    logger.error(f"Unhandled exception: {exc}", extra={
        "request_id": request_id,
        "traceback": traceback.format_exc()
    })
    
    # Don't expose internal error details in production
    return create_error_response(
        error_code=ErrorCode.INTERNAL_ERROR.value,
        message="An internal server error occurred. Please try again later.",
        status_code=500,
        request_id=request_id
    )


def register_error_handlers(app):
    """Register all error handlers with the FastAPI application."""
    
    # Custom exception handlers
    app.add_exception_handler(KDPStrategistError, kdp_strategist_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)
    
    # Global exception handler (catch-all)
    app.add_exception_handler(Exception, global_exception_handler)
    
    logger.info("Error handlers registered successfully")


class ErrorContext:
    """Context manager for error handling with additional context."""
    
    def __init__(self, operation: str, **context):
        self.operation = operation
        self.context = context
        self.logger = logging.getLogger(self.__class__.__module__)
    
    def __enter__(self):
        self.logger.debug(f"Starting operation: {self.operation}", extra=self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.logger.debug(f"Completed operation: {self.operation}", extra=self.context)
        else:
            self.logger.error(
                f"Operation failed: {self.operation} - {exc_val}",
                extra={**self.context, "exception_type": exc_type.__name__}
            )
        return False  # Don't suppress exceptions


def handle_api_errors(operation: str):
    """Decorator for handling API errors with context."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except KDPStrategistError:
                # Re-raise custom exceptions as-is
                raise
            except Exception as e:
                # Wrap unexpected exceptions
                logger.error(f"Unexpected error in {operation}: {e}")
                raise KDPStrategistError(
                    message=f"Operation '{operation}' failed unexpectedly",
                    error_code=ErrorCode.UNEXPECTED_ERROR,
                    details={"operation": operation},
                    cause=e
                )
        return wrapper
    return decorator