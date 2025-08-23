"""
Error handlers for FastAPI application.
"""
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .exceptions import (
    KDPStrategistError, APIClientError, DataValidationError,
    ConfigurationError, RateLimitExceededError
)

logger = logging.getLogger(__name__)


async def kdp_strategist_exception_handler(request: Request, exc: KDPStrategistError) -> JSONResponse:
    """Handle base KDP Strategist exceptions."""
    logger.error(f"KDP Strategist error: {str(exc)} - URL: {request.url}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": str(exc),
            "details": "An internal error occurred while processing your request."
        }
    )


async def api_client_exception_handler(request: Request, exc: APIClientError) -> JSONResponse:
    """Handle API client exceptions."""
    logger.error(f"API client error in {exc.service}: {exc.message} - URL: {request.url}")
    
    # Map to appropriate HTTP status codes
    status_code = 502  # Bad Gateway by default
    if hasattr(exc, 'status_code') and exc.status_code:
        if exc.status_code == 401:
            status_code = 401  # Unauthorized
        elif exc.status_code == 403:
            status_code = 403  # Forbidden
        elif exc.status_code == 429:
            status_code = 429  # Too Many Requests
        elif 400 <= exc.status_code < 500:
            status_code = 400  # Bad Request
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": "api_error",
            "service": exc.service,
            "message": exc.message,
            "details": f"External API error from {exc.service}"
        }
    )


async def validation_exception_handler(request: Request, exc: DataValidationError) -> JSONResponse:
    """Handle data validation exceptions."""
    logger.warning(f"Validation error in {exc.field}: {exc.message} - URL: {request.url}")
    
    content = {
        "error": "validation_error",
        "field": exc.field,
        "message": exc.message,
        "details": "The provided data failed validation."
    }
    
    if hasattr(exc, 'value') and exc.value is not None:
        content["invalid_value"] = exc.value
    
    return JSONResponse(
        status_code=400,
        content=content
    )


async def configuration_exception_handler(request: Request, exc: ConfigurationError) -> JSONResponse:
    """Handle configuration exceptions."""
    logger.error(f"Configuration error in {exc.setting}: {exc.message} - URL: {request.url}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "configuration_error",
            "setting": exc.setting,
            "message": exc.message,
            "details": "A configuration error occurred. Please check your settings."
        }
    )


async def rate_limit_exception_handler(request: Request, exc: RateLimitExceededError) -> JSONResponse:
    """Handle rate limit exceptions."""
    logger.warning(f"Rate limit exceeded for {exc.service}: {exc.message} - URL: {request.url}")
    
    headers = {}
    if hasattr(exc, 'retry_after') and exc.retry_after:
        headers["Retry-After"] = str(exc.retry_after)
    
    return JSONResponse(
        status_code=429,
        headers=headers,
        content={
            "error": "rate_limit_exceeded",
            "service": exc.service,
            "message": exc.message,
            "retry_after": getattr(exc, 'retry_after', None),
            "details": f"Rate limit exceeded for {exc.service}. Please try again later."
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    logger.warning(f"HTTP {exc.status_code} error: {exc.detail} - URL: {request.url}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "status_code": exc.status_code,
            "message": exc.detail,
            "details": "An HTTP error occurred."
        }
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI validation errors."""
    logger.warning(f"Request validation error: {exc.errors()} - URL: {request.url}")
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Request validation failed",
            "details": exc.errors(),
            "body": exc.body
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)} - URL: {request.url}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "details": "Please try again later or contact support if the problem persists."
        }
    )


def register_error_handlers(app):
    """Register all error handlers with the FastAPI app."""
    # Custom exception handlers
    app.add_exception_handler(KDPStrategistError, kdp_strategist_exception_handler)
    app.add_exception_handler(APIClientError, api_client_exception_handler)
    app.add_exception_handler(DataValidationError, validation_exception_handler)
    app.add_exception_handler(ConfigurationError, configuration_exception_handler)
    app.add_exception_handler(RateLimitExceededError, rate_limit_exception_handler)
    
    # FastAPI built-in exception handlers
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    
    # General exception handler (catch-all)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Error handlers registered successfully")