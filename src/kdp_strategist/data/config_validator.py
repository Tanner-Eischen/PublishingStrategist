"""
Comprehensive configuration validation for Keepa client.

This module provides validation utilities for Keepa client configuration,
including environment-specific validation, security checks, and performance
optimization recommendations.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse
import warnings

from .keepa_config import (
    KeepaConfig, RateLimitConfig, RetryConfig, CacheConfig, TimeoutConfig,
    SecurityConfig, LoggingConfig, Environment, CacheType, LogLevel
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def add_error(self, message: str):
        """Add validation error."""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add validation warning."""
        self.warnings.append(message)
    
    def add_recommendation(self, message: str):
        """Add optimization recommendation."""
        self.recommendations.append(message)
    
    def merge(self, other: 'ValidationResult'):
        """Merge another validation result."""
        if not other.is_valid:
            self.is_valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.recommendations.extend(other.recommendations)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'is_valid': self.is_valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'recommendations': self.recommendations
        }


class ConfigValidator:
    """
    Comprehensive configuration validator for Keepa client.
    
    Provides validation for all configuration aspects including:
    - Basic configuration structure and types
    - Environment-specific requirements
    - Security best practices
    - Performance optimization
    - API compliance
    """
    
    def __init__(self):
        self.api_key_pattern = re.compile(r'^[a-zA-Z0-9]{32,}$')
        self.redis_url_pattern = re.compile(r'^redis://.*$')
        
    def validate_config(self, config: KeepaConfig) -> ValidationResult:
        """
        Perform comprehensive validation of Keepa configuration.
        
        Args:
            config: KeepaConfig instance to validate
            
        Returns:
            ValidationResult with validation status and messages
        """
        result = ValidationResult(is_valid=True)
        
        # Validate core configuration
        result.merge(self._validate_core_config(config))
        
        # Validate component configurations
        result.merge(self._validate_rate_limit_config(config.rate_limit))
        result.merge(self._validate_retry_config(config.retry))
        result.merge(self._validate_cache_config(config.cache))
        result.merge(self._validate_timeout_config(config.timeout))
        result.merge(self._validate_security_config(config.security))
        result.merge(self._validate_logging_config(config.logging))
        
        # Environment-specific validation
        result.merge(self._validate_environment_specific(config))
        
        # Performance validation
        result.merge(self._validate_performance_settings(config))
        
        # Security validation
        result.merge(self._validate_security_best_practices(config))
        
        # API compliance validation
        result.merge(self._validate_api_compliance(config))
        
        return result 
   
    def _validate_core_config(self, config: KeepaConfig) -> ValidationResult:
        """Validate core configuration settings."""
        result = ValidationResult(is_valid=True)
        
        # Validate API key
        if not config.api_key:
            result.add_error("API key is required")
        elif not self.api_key_pattern.match(config.api_key):
            result.add_error("API key format is invalid (should be 32+ alphanumeric characters)")
        
        # Validate base URL
        if not config.base_url:
            result.add_error("Base URL is required")
        else:
            try:
                parsed = urlparse(config.base_url)
                if not parsed.scheme or not parsed.netloc:
                    result.add_error("Base URL must be a valid URL with scheme and host")
                elif parsed.scheme not in ['http', 'https']:
                    result.add_error("Base URL must use HTTP or HTTPS scheme")
                elif parsed.scheme == 'http' and config.environment == Environment.PRODUCTION:
                    result.add_warning("Using HTTP in production is not recommended for security")
            except Exception as e:
                result.add_error(f"Invalid base URL: {e}")
        
        # Validate user agent
        if not config.user_agent:
            result.add_error("User agent is required")
        elif len(config.user_agent) < 5:
            result.add_warning("User agent should be more descriptive")
        
        # Validate concurrent requests
        if config.max_concurrent_requests <= 0:
            result.add_error("max_concurrent_requests must be positive")
        elif config.max_concurrent_requests > 20:
            result.add_warning("High concurrent request count may trigger rate limits")
        
        # Validate connection pool size
        if config.connection_pool_size <= 0:
            result.add_error("connection_pool_size must be positive")
        elif config.connection_pool_size < config.max_concurrent_requests:
            result.add_recommendation(
                "Connection pool size should be >= max_concurrent_requests for optimal performance"
            )
        
        return result
    
    def _validate_rate_limit_config(self, config: RateLimitConfig) -> ValidationResult:
        """Validate rate limiting configuration."""
        result = ValidationResult(is_valid=True)
        
        # Validate requests per minute
        if config.max_requests_per_minute <= 0:
            result.add_error("max_requests_per_minute must be positive")
        elif config.max_requests_per_minute > 100:
            result.add_warning("Very high request rate may exceed API limits")
        
        # Validate burst capacity
        if config.burst_capacity <= 0:
            result.add_error("burst_capacity must be positive")
        elif config.burst_capacity > config.max_requests_per_minute:
            result.add_warning("burst_capacity should not exceed max_requests_per_minute")
        
        # Validate time window
        if config.time_window_seconds <= 0:
            result.add_error("time_window_seconds must be positive")
        elif config.time_window_seconds != 60:
            result.add_recommendation("Standard time window is 60 seconds for rate limiting")
        
        # Validate backoff settings
        if config.backoff_factor < 1.0:
            result.add_error("backoff_factor must be >= 1.0")
        elif config.backoff_factor > 5.0:
            result.add_warning("Very high backoff factor may cause long delays")
        
        if config.max_backoff_seconds <= 0:
            result.add_error("max_backoff_seconds must be positive")
        elif config.max_backoff_seconds > 600:
            result.add_warning("Very long max backoff may impact user experience")
        
        return result
    
    def _validate_retry_config(self, config: RetryConfig) -> ValidationResult:
        """Validate retry configuration."""
        result = ValidationResult(is_valid=True)
        
        # Validate max retries
        if config.max_retries < 0:
            result.add_error("max_retries must be non-negative")
        elif config.max_retries > 10:
            result.add_warning("Very high retry count may cause long delays")
        
        # Validate delay settings
        if config.initial_delay <= 0:
            result.add_error("initial_delay must be positive")
        
        if config.max_delay <= 0:
            result.add_error("max_delay must be positive")
        elif config.max_delay < config.initial_delay:
            result.add_error("max_delay must be >= initial_delay")
        
        # Validate exponential base
        if config.exponential_base < 1.0:
            result.add_error("exponential_base must be >= 1.0")
        elif config.exponential_base > 5.0:
            result.add_warning("Very high exponential base may cause rapid delay escalation")
        
        # Validate retry status codes
        if not config.retry_on_status_codes:
            result.add_warning("No retry status codes configured")
        else:
            invalid_codes = [code for code in config.retry_on_status_codes if code < 400 or code >= 600]
            if invalid_codes:
                result.add_error(f"Invalid HTTP status codes for retry: {invalid_codes}")
        
        return result 
   
    def _validate_cache_config(self, config: CacheConfig) -> ValidationResult:
        """Validate cache configuration."""
        result = ValidationResult(is_valid=True)
        
        # Validate cache type specific settings
        if config.cache_type == CacheType.REDIS:
            if not config.redis_url:
                result.add_error("redis_url is required when cache_type is REDIS")
            elif not self.redis_url_pattern.match(config.redis_url):
                result.add_error("Invalid Redis URL format")
        
        # Validate memory cache size
        if config.memory_cache_size <= 0:
            result.add_error("memory_cache_size must be positive")
        elif config.memory_cache_size > 10000:
            result.add_warning("Very large memory cache may consume excessive RAM")
        
        # Validate file cache path
        if config.cache_type in [CacheType.FILE, CacheType.MULTI_TIER]:
            if not config.file_cache_path:
                result.add_error("file_cache_path is required for file-based caching")
            else:
                cache_path = Path(config.file_cache_path)
                try:
                    cache_path.mkdir(parents=True, exist_ok=True)
                    if not os.access(cache_path, os.W_OK):
                        result.add_error(f"Cache directory is not writable: {config.file_cache_path}")
                except Exception as e:
                    result.add_error(f"Cannot create cache directory: {e}")
        
        # Validate TTL settings
        ttl_configs = [
            ('default_ttl_seconds', config.default_ttl_seconds),
            ('product_ttl_seconds', config.product_ttl_seconds),
            ('search_ttl_seconds', config.search_ttl_seconds),
            ('price_history_ttl_seconds', config.price_history_ttl_seconds)
        ]
        
        for name, ttl in ttl_configs:
            if ttl <= 0:
                result.add_error(f"{name} must be positive")
            elif ttl > 86400:  # 24 hours
                result.add_warning(f"{name} is very long (>24 hours), may serve stale data")
        
        # Validate cache size limit
        if config.max_cache_size_mb <= 0:
            result.add_error("max_cache_size_mb must be positive")
        elif config.max_cache_size_mb > 1000:
            result.add_warning("Very large cache size limit may consume excessive disk space")
        
        return result
    
    def _validate_timeout_config(self, config: TimeoutConfig) -> ValidationResult:
        """Validate timeout configuration."""
        result = ValidationResult(is_valid=True)
        
        # Validate individual timeouts
        if config.connect_timeout <= 0:
            result.add_error("connect_timeout must be positive")
        elif config.connect_timeout > 30:
            result.add_warning("Very long connect timeout may impact responsiveness")
        
        if config.read_timeout <= 0:
            result.add_error("read_timeout must be positive")
        elif config.read_timeout > 120:
            result.add_warning("Very long read timeout may impact responsiveness")
        
        if config.total_timeout <= 0:
            result.add_error("total_timeout must be positive")
        elif config.total_timeout > 300:
            result.add_warning("Very long total timeout may impact user experience")
        
        # Validate timeout relationships
        if config.total_timeout < max(config.connect_timeout, config.read_timeout):
            result.add_error("total_timeout must be >= max(connect_timeout, read_timeout)")
        
        if config.connect_timeout >= config.total_timeout:
            result.add_warning("connect_timeout should be less than total_timeout")
        
        return result
    
    def _validate_security_config(self, config: SecurityConfig) -> ValidationResult:
        """Validate security configuration."""
        result = ValidationResult(is_valid=True)
        
        # Validate API key configuration
        if not config.api_key_env_var and not config.api_key_file_path:
            result.add_error("Either api_key_env_var or api_key_file_path must be specified")
        
        if config.api_key_file_path:
            key_file = Path(config.api_key_file_path)
            if key_file.exists():
                # Check file permissions
                stat = key_file.stat()
                if stat.st_mode & 0o077:  # Check if group/other have any permissions
                    result.add_warning("API key file should have restrictive permissions (600)")
            else:
                result.add_warning(f"API key file does not exist: {config.api_key_file_path}")
        
        # Validate SSL settings
        if not config.validate_ssl_certificates:
            result.add_warning("SSL certificate validation is disabled - security risk")
        
        return result
    
    def _validate_logging_config(self, config) -> ValidationResult:
        """Validate logging configuration."""
        result = ValidationResult(is_valid=True)
        
        # Validate log file settings
        if config.log_file_path:
            log_file = Path(config.log_file_path)
            log_dir = log_file.parent
            
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
                if not os.access(log_dir, os.W_OK):
                    result.add_error(f"Log directory is not writable: {log_dir}")
            except Exception as e:
                result.add_error(f"Cannot create log directory: {e}")
        
        # Validate log rotation settings
        if config.max_log_file_size_mb <= 0:
            result.add_error("max_log_file_size_mb must be positive")
        elif config.max_log_file_size_mb > 1000:
            result.add_warning("Very large log file size may impact performance")
        
        if config.log_rotation_count < 0:
            result.add_error("log_rotation_count must be non-negative")
        elif config.log_rotation_count > 50:
            result.add_warning("Very high log rotation count may consume excessive disk space")
        
        # Validate log format
        if not config.log_format:
            result.add_error("log_format cannot be empty")
        elif '%(asctime)s' not in config.log_format:
            result.add_recommendation("Log format should include timestamp (%(asctime)s)")
        
        return result    

    def _validate_environment_specific(self, config: KeepaConfig) -> ValidationResult:
        """Validate environment-specific requirements."""
        result = ValidationResult(is_valid=True)
        
        if config.environment == Environment.PRODUCTION:
            # Production-specific validations
            if config.debug_mode:
                result.add_warning("Debug mode should be disabled in production")
            
            if config.mock_api_responses:
                result.add_error("Mock API responses must be disabled in production")
            
            if config.logging.log_level == LogLevel.DEBUG:
                result.add_warning("Debug logging may impact performance in production")
            
            if not config.logging.log_file_path:
                result.add_recommendation("File logging is recommended for production")
            
            if config.cache.cache_type == CacheType.MEMORY:
                result.add_recommendation("Persistent caching (file/Redis) is recommended for production")
            
            if not config.security.validate_ssl_certificates:
                result.add_error("SSL certificate validation must be enabled in production")
        
        elif config.environment == Environment.DEVELOPMENT:
            # Development-specific recommendations
            if not config.debug_mode:
                result.add_recommendation("Debug mode is helpful for development")
            
            if config.logging.log_level not in [LogLevel.DEBUG, LogLevel.INFO]:
                result.add_recommendation("Verbose logging is helpful for development")
        
        elif config.environment == Environment.TESTING:
            # Testing-specific validations
            if not config.mock_api_responses:
                result.add_recommendation("Mock API responses are recommended for testing")
            
            if config.cache.cache_type != CacheType.MEMORY:
                result.add_recommendation("Memory caching is sufficient for testing")
        
        return result
    
    def _validate_performance_settings(self, config: KeepaConfig) -> ValidationResult:
        """Validate performance-related settings."""
        result = ValidationResult(is_valid=True)
        
        # Check for performance bottlenecks
        if config.max_concurrent_requests == 1:
            result.add_recommendation("Consider increasing concurrent requests for better performance")
        
        if config.cache.cache_type == CacheType.MEMORY and config.cache.memory_cache_size < 100:
            result.add_recommendation("Increase memory cache size for better hit rates")
        
        # Check timeout vs rate limit compatibility
        requests_per_second = config.rate_limit.max_requests_per_minute / 60
        if config.timeout.total_timeout * requests_per_second > config.max_concurrent_requests:
            result.add_warning("Timeout and rate limit settings may cause request queuing")
        
        # Check cache TTL optimization
        if config.cache.search_ttl_seconds > config.cache.product_ttl_seconds:
            result.add_recommendation("Search results typically change faster than product data")
        
        return result
    
    def _validate_security_best_practices(self, config: KeepaConfig) -> ValidationResult:
        """Validate security best practices."""
        result = ValidationResult(is_valid=True)
        
        # API key security
        if config.api_key and len(config.api_key) < 32:
            result.add_warning("API key seems short - ensure it's valid")
        
        if not config.security.mask_api_key_in_logs:
            result.add_warning("API key masking in logs is recommended for security")
        
        # Cache security
        if config.cache.cache_type in [CacheType.FILE, CacheType.MULTI_TIER]:
            if not config.security.encrypt_cached_data and config.environment == Environment.PRODUCTION:
                result.add_recommendation("Consider encrypting cached data in production")
        
        # Network security
        if config.base_url.startswith('http://'):
            result.add_warning("HTTPS is recommended for API communications")
        
        return result
    
    def _validate_api_compliance(self, config: KeepaConfig) -> ValidationResult:
        """Validate Keepa API compliance."""
        result = ValidationResult(is_valid=True)
        
        # Rate limiting compliance
        if config.rate_limit.max_requests_per_minute > 100:
            result.add_error("Keepa API rate limit is typically 100 requests/minute")
        
        # Batch size compliance
        if config.enable_batch_processing:
            # These limits are enforced in the client, but validate configuration supports them
            if config.max_concurrent_requests > 5:
                result.add_warning("High concurrency may trigger Keepa rate limits")
        
        # Timeout compliance
        if config.timeout.total_timeout < 10:
            result.add_warning("Very short timeouts may cause failures with Keepa API")
        
        return result    

    def validate_environment_variables(self) -> ValidationResult:
        """Validate required environment variables."""
        result = ValidationResult(is_valid=True)
        
        # Check for API key
        if not os.getenv('KEEPA_API_KEY'):
            result.add_error("KEEPA_API_KEY environment variable is not set")
        
        # Check optional environment variables
        optional_vars = [
            'KEEPA_ENVIRONMENT',
            'KEEPA_CACHE_TYPE',
            'KEEPA_REDIS_URL',
            'KEEPA_LOG_LEVEL',
            'KEEPA_DEBUG_MODE'
        ]
        
        for var in optional_vars:
            value = os.getenv(var)
            if value:
                # Validate enum values
                if var == 'KEEPA_ENVIRONMENT':
                    try:
                        Environment(value)
                    except ValueError:
                        result.add_error(f"Invalid {var} value: {value}")
                
                elif var == 'KEEPA_CACHE_TYPE':
                    try:
                        CacheType(value)
                    except ValueError:
                        result.add_error(f"Invalid {var} value: {value}")
                
                elif var == 'KEEPA_LOG_LEVEL':
                    try:
                        LogLevel(value)
                    except ValueError:
                        result.add_error(f"Invalid {var} value: {value}")
                
                elif var == 'KEEPA_DEBUG_MODE':
                    if value.lower() not in ['true', 'false']:
                        result.add_error(f"Invalid {var} value: {value} (should be 'true' or 'false')")
        
        return result
    
    def validate_config_file(self, file_path: str) -> ValidationResult:
        """Validate configuration file format and content."""
        result = ValidationResult(is_valid=True)
        
        config_file = Path(file_path)
        
        # Check file existence and readability
        if not config_file.exists():
            result.add_error(f"Configuration file does not exist: {file_path}")
            return result
        
        if not os.access(config_file, os.R_OK):
            result.add_error(f"Configuration file is not readable: {file_path}")
            return result
        
        # Validate JSON format
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            result.add_error(f"Invalid JSON format in configuration file: {e}")
            return result
        except Exception as e:
            result.add_error(f"Error reading configuration file: {e}")
            return result
        
        # Validate configuration structure
        try:
            config = KeepaConfig.from_dict(config_data)
            result.merge(self.validate_config(config))
        except Exception as e:
            result.add_error(f"Invalid configuration structure: {e}")
        
        return result
    
    def generate_config_report(self, config: KeepaConfig) -> Dict[str, Any]:
        """Generate comprehensive configuration report."""
        validation_result = self.validate_config(config)
        
        report = {
            'validation': validation_result.to_dict(),
            'configuration_summary': {
                'environment': config.environment.value,
                'profile_name': config.profile_name,
                'api_key_configured': bool(config.api_key),
                'cache_type': config.cache.cache_type.value,
                'rate_limit_rpm': config.rate_limit.max_requests_per_minute,
                'debug_mode': config.debug_mode,
                'mock_responses': config.mock_api_responses
            },
            'security_assessment': {
                'ssl_validation': config.security.validate_ssl_certificates,
                'api_key_masked': config.security.mask_api_key_in_logs,
                'cache_encryption': config.security.encrypt_cached_data,
                'https_used': config.base_url.startswith('https://')
            },
            'performance_metrics': {
                'max_concurrent_requests': config.max_concurrent_requests,
                'connection_pool_size': config.connection_pool_size,
                'cache_ttl_seconds': config.cache.default_ttl_seconds,
                'total_timeout_seconds': config.timeout.total_timeout
            },
            'feature_flags': {
                'batch_processing': config.enable_batch_processing,
                'advanced_search': config.enable_advanced_search,
                'price_history': config.enable_price_history,
                'health_monitoring': config.enable_health_monitoring
            }
        }
        
        return report


def validate_keepa_config(config: KeepaConfig) -> ValidationResult:
    """
    Convenience function to validate Keepa configuration.
    
    Args:
        config: KeepaConfig instance to validate
        
    Returns:
        ValidationResult with validation status and messages
    """
    validator = ConfigValidator()
    return validator.validate_config(config)


def validate_config_file(file_path: str) -> ValidationResult:
    """
    Convenience function to validate configuration file.
    
    Args:
        file_path: Path to configuration file
        
    Returns:
        ValidationResult with validation status and messages
    """
    validator = ConfigValidator()
    return validator.validate_config_file(file_path)


def validate_environment() -> ValidationResult:
    """
    Convenience function to validate environment variables.
    
    Returns:
        ValidationResult with validation status and messages
    """
    validator = ConfigValidator()
    return validator.validate_environment_variables()