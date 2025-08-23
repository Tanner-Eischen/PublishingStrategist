"""Consolidated Configuration Module

This module consolidates all configuration settings from various sources:
- settings.py (APIConfig, CacheConfig)
- simple_trends_config.py (various dataclasses)
- JSON configuration files (feature flags, deployment, monitoring, incident response)
- logging.conf (logging configuration)

Provides a unified interface for all application configuration needs.
"""

import os
import json
import logging.config
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pathlib import Path


class Environment(Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class DataSource(Enum):
    """Available data sources for trend analysis."""
    AMAZON = "amazon"
    UBERSUGGEST = "ubersuggest"
    SYNTHETIC = "synthetic"
    KEEPA = "keepa"


class CacheType(Enum):
    """Available cache backend types."""
    FILE = "file"
    REDIS = "redis"
    MEMORY = "memory"
    DISABLED = "disabled"


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


def get_env_var(key: str, default: Optional[str] = None, required: bool = False) -> str:
    """Get environment variable with validation.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        required: Whether the variable is required
        
    Returns:
        Environment variable value
        
    Raises:
        ConfigurationError: If required variable is missing
    """
    value = os.getenv(key, default)
    if required and value is None:
        raise ConfigurationError(f"Required environment variable '{key}' is not set")
    return value


def load_environment_variables() -> Dict[str, str]:
    """Load all environment variables into a dictionary."""
    return dict(os.environ)


@dataclass
class APIConfig:
    """API configuration settings."""
    keepa_api_key: str = field(default_factory=lambda: get_env_var("KEEPA_API_KEY", required=True))
    amazon_api_key: str = field(default_factory=lambda: get_env_var("AMAZON_API_KEY", ""))
    ubersuggest_api_key: str = field(default_factory=lambda: get_env_var("UBERSUGGEST_API_KEY", ""))
    google_trends_api_key: str = field(default_factory=lambda: get_env_var("GOOGLE_TRENDS_API_KEY", ""))
    
    # Rate limiting
    keepa_rate_limit: int = field(default_factory=lambda: int(get_env_var("KEEPA_RATE_LIMIT", "100")))
    amazon_rate_limit: int = field(default_factory=lambda: int(get_env_var("AMAZON_RATE_LIMIT", "200")))
    ubersuggest_rate_limit: int = field(default_factory=lambda: int(get_env_var("UBERSUGGEST_RATE_LIMIT", "50")))
    
    # Timeouts
    request_timeout: int = field(default_factory=lambda: int(get_env_var("REQUEST_TIMEOUT", "30")))
    connection_timeout: int = field(default_factory=lambda: int(get_env_var("CONNECTION_TIMEOUT", "10")))
    read_timeout: int = field(default_factory=lambda: int(get_env_var("READ_TIMEOUT", "30")))
    
    # Retry settings
    max_retries: int = field(default_factory=lambda: int(get_env_var("MAX_RETRIES", "3")))
    retry_delay: float = field(default_factory=lambda: float(get_env_var("RETRY_DELAY", "1.0")))
    backoff_factor: float = field(default_factory=lambda: float(get_env_var("BACKOFF_FACTOR", "2.0")))


@dataclass
class CacheConfig:
    """Cache configuration settings."""
    cache_type: CacheType = field(default_factory=lambda: CacheType(get_env_var("CACHE_TYPE", "file")))
    cache_dir: str = field(default_factory=lambda: get_env_var("CACHE_DIR", "cache"))
    cache_ttl: int = field(default_factory=lambda: int(get_env_var("CACHE_TTL", "3600")))
    max_cache_size: int = field(default_factory=lambda: int(get_env_var("MAX_CACHE_SIZE", "1000")))
    
    # Redis settings
    redis_host: str = field(default_factory=lambda: get_env_var("REDIS_HOST", "localhost"))
    redis_port: int = field(default_factory=lambda: int(get_env_var("REDIS_PORT", "6379")))
    redis_db: int = field(default_factory=lambda: int(get_env_var("REDIS_DB", "0")))
    redis_password: Optional[str] = field(default_factory=lambda: get_env_var("REDIS_PASSWORD"))
    redis_url: Optional[str] = field(default_factory=lambda: get_env_var("REDIS_URL"))
    
    # File cache settings
    file_cache_compression: bool = field(default_factory=lambda: get_env_var("FILE_CACHE_COMPRESSION", "true").lower() == "true")
    file_cache_cleanup_interval: int = field(default_factory=lambda: int(get_env_var("FILE_CACHE_CLEANUP_INTERVAL", "3600")))


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = field(default_factory=lambda: int(get_env_var("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5")))
    recovery_timeout: int = field(default_factory=lambda: int(get_env_var("CIRCUIT_BREAKER_RECOVERY_TIMEOUT", "60")))
    expected_exception: str = field(default_factory=lambda: get_env_var("CIRCUIT_BREAKER_EXPECTED_EXCEPTION", "Exception"))


@dataclass
class MonitoringConfig:
    """Monitoring and metrics configuration."""
    enabled: bool = field(default_factory=lambda: get_env_var("MONITORING_ENABLED", "true").lower() == "true")
    metrics_interval: int = field(default_factory=lambda: int(get_env_var("METRICS_INTERVAL", "30")))
    performance_report_interval: int = field(default_factory=lambda: int(get_env_var("PERFORMANCE_REPORT_INTERVAL", "300")))
    alert_check_interval: int = field(default_factory=lambda: int(get_env_var("ALERT_CHECK_INTERVAL", "60")))
    health_check_interval: int = field(default_factory=lambda: int(get_env_var("HEALTH_CHECK_INTERVAL", "120")))
    
    # Data retention
    metrics_history_points: int = field(default_factory=lambda: int(get_env_var("METRICS_HISTORY_POINTS", "100")))
    performance_reports_count: int = field(default_factory=lambda: int(get_env_var("PERFORMANCE_REPORTS_COUNT", "288")))
    alert_history_count: int = field(default_factory=lambda: int(get_env_var("ALERT_HISTORY_COUNT", "1000")))
    log_entries_count: int = field(default_factory=lambda: int(get_env_var("LOG_ENTRIES_COUNT", "10000")))
    
    # Thresholds
    response_time_warning: int = field(default_factory=lambda: int(get_env_var("RESPONSE_TIME_WARNING", "2000")))
    response_time_critical: int = field(default_factory=lambda: int(get_env_var("RESPONSE_TIME_CRITICAL", "5000")))
    error_rate_warning: float = field(default_factory=lambda: float(get_env_var("ERROR_RATE_WARNING", "5.0")))
    error_rate_critical: float = field(default_factory=lambda: float(get_env_var("ERROR_RATE_CRITICAL", "10.0")))
    system_health_warning: int = field(default_factory=lambda: int(get_env_var("SYSTEM_HEALTH_WARNING", "70")))
    system_health_critical: int = field(default_factory=lambda: int(get_env_var("SYSTEM_HEALTH_CRITICAL", "50")))


@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: str = field(default_factory=lambda: get_env_var("LOG_LEVEL", "INFO"))
    format: str = field(default_factory=lambda: get_env_var("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    file_path: str = field(default_factory=lambda: get_env_var("LOG_FILE_PATH", "logs/kdp_strategist.log"))
    max_file_size: int = field(default_factory=lambda: int(get_env_var("LOG_MAX_FILE_SIZE", "10485760")))
    backup_count: int = field(default_factory=lambda: int(get_env_var("LOG_BACKUP_COUNT", "5")))
    enable_console: bool = field(default_factory=lambda: get_env_var("LOG_ENABLE_CONSOLE", "true").lower() == "true")
    enable_file: bool = field(default_factory=lambda: get_env_var("LOG_ENABLE_FILE", "true").lower() == "true")
    enable_structured: bool = field(default_factory=lambda: get_env_var("LOG_ENABLE_STRUCTURED", "false").lower() == "true")


@dataclass
class FeatureFlagsConfig:
    """Feature flags configuration."""
    simple_trends_percentage: float = field(default_factory=lambda: float(get_env_var("SIMPLE_TRENDS_PERCENTAGE", "100.0")))
    enable_a_b_testing: bool = field(default_factory=lambda: get_env_var("ENABLE_A_B_TESTING", "false").lower() == "true")
    a_b_split: float = field(default_factory=lambda: float(get_env_var("A_B_SPLIT", "50.0")))
    force_simple_trends: bool = field(default_factory=lambda: get_env_var("FORCE_SIMPLE_TRENDS", "false").lower() == "true")
    performance_monitoring: bool = field(default_factory=lambda: get_env_var("PERFORMANCE_MONITORING", "true").lower() == "true")


@dataclass
class NotificationConfig:
    """Notification and alerting configuration."""
    enabled: bool = field(default_factory=lambda: get_env_var("NOTIFICATIONS_ENABLED", "true").lower() == "true")
    
    # SMTP settings
    smtp_host: str = field(default_factory=lambda: get_env_var("SMTP_HOST", "smtp.gmail.com"))
    smtp_port: int = field(default_factory=lambda: int(get_env_var("SMTP_PORT", "587")))
    smtp_use_tls: bool = field(default_factory=lambda: get_env_var("SMTP_USE_TLS", "true").lower() == "true")
    smtp_username: str = field(default_factory=lambda: get_env_var("SMTP_USERNAME", ""))
    smtp_password: str = field(default_factory=lambda: get_env_var("SMTP_PASSWORD", ""))
    smtp_from: str = field(default_factory=lambda: get_env_var("SMTP_FROM", "alerts@kdpstrategist.com"))
    smtp_to: List[str] = field(default_factory=lambda: get_env_var("SMTP_TO", "admin@kdpstrategist.com").split(","))
    
    # Webhook settings
    webhook_url: Optional[str] = field(default_factory=lambda: get_env_var("WEBHOOK_URL"))
    
    # Slack settings
    slack_enabled: bool = field(default_factory=lambda: get_env_var("SLACK_ENABLED", "false").lower() == "true")
    slack_webhook_url: Optional[str] = field(default_factory=lambda: get_env_var("SLACK_WEBHOOK_URL"))
    slack_channel: str = field(default_factory=lambda: get_env_var("SLACK_CHANNEL", "#alerts"))
    
    # Escalation settings
    escalation_enabled: bool = field(default_factory=lambda: get_env_var("ESCALATION_ENABLED", "true").lower() == "true")
    auto_resolve_timeout: int = field(default_factory=lambda: int(get_env_var("AUTO_RESOLVE_TIMEOUT", "3600")))


@dataclass
class DeploymentConfig:
    """Deployment and environment configuration."""
    environment: Environment = field(default_factory=lambda: Environment(get_env_var("ENVIRONMENT", "development")))
    api_url: str = field(default_factory=lambda: get_env_var("API_URL", "http://localhost:8000"))
    database_url: str = field(default_factory=lambda: get_env_var("DATABASE_URL", "sqlite:///dev.db"))
    
    # Deployment settings
    strategy: str = field(default_factory=lambda: get_env_var("DEPLOYMENT_STRATEGY", "blue_green"))
    health_check_timeout: int = field(default_factory=lambda: int(get_env_var("HEALTH_CHECK_TIMEOUT", "300")))
    rollback_timeout: int = field(default_factory=lambda: int(get_env_var("ROLLBACK_TIMEOUT", "600")))
    backup_retention_days: int = field(default_factory=lambda: int(get_env_var("BACKUP_RETENTION_DAYS", "7")))
    deployment_timeout: int = field(default_factory=lambda: int(get_env_var("DEPLOYMENT_TIMEOUT", "1800")))


@dataclass
class ConsolidatedSettings:
    """Main configuration class that consolidates all settings."""
    api: APIConfig = field(default_factory=APIConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    feature_flags: FeatureFlagsConfig = field(default_factory=FeatureFlagsConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    deployment: DeploymentConfig = field(default_factory=DeploymentConfig)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_configuration()
        self._setup_logging()
    
    def _validate_configuration(self):
        """Validate configuration settings."""
        # Validate API keys for enabled features
        if not self.api.keepa_api_key:
            raise ConfigurationError("KEEPA_API_KEY is required")
        
        # Validate cache configuration
        if self.cache.cache_type == CacheType.REDIS:
            if not self.cache.redis_url and not self.cache.redis_host:
                raise ConfigurationError("Redis configuration is incomplete")
        
        # Validate notification configuration
        if self.notifications.enabled and self.notifications.smtp_enabled:
            if not self.notifications.smtp_username or not self.notifications.smtp_password:
                raise ConfigurationError("SMTP credentials are required when notifications are enabled")
    
    def _setup_logging(self):
        """Setup logging configuration."""
        logging_config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'simple': {
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                },
                'detailed': {
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                },
                'structured': {
                    'format': '%(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                }
            },
            'handlers': {},
            'loggers': {
                'root': {
                    'level': self.logging.level,
                    'handlers': []
                },
                'kdp_strategist': {
                    'level': self.logging.level,
                    'handlers': [],
                    'qualname': 'kdp_strategist',
                    'propagate': False
                },
                'kdp_strategist.data.keepa_client': {
                    'level': self.logging.level,
                    'handlers': [],
                    'qualname': 'kdp_strategist.data.keepa_client',
                    'propagate': False
                },
                'kdp_strategist.data.cache_manager': {
                    'level': 'DEBUG' if self.logging.level == 'DEBUG' else self.logging.level,
                    'handlers': [],
                    'qualname': 'kdp_strategist.data.cache_manager',
                    'propagate': False
                }
            }
        }
        
        # Add console handler if enabled
        if self.logging.enable_console:
            logging_config['handlers']['console'] = {
                'class': 'logging.StreamHandler',
                'level': self.logging.level,
                'formatter': 'simple',
                'stream': 'ext://sys.stdout'
            }
            for logger in logging_config['loggers'].values():
                logger['handlers'].append('console')
        
        # Add file handler if enabled
        if self.logging.enable_file:
            # Ensure log directory exists
            log_dir = Path(self.logging.file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            logging_config['handlers']['file'] = {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': self.logging.file_path,
                'mode': 'a',
                'maxBytes': self.logging.max_file_size,
                'backupCount': self.logging.backup_count
            }
            for logger in logging_config['loggers'].values():
                if 'file' not in logger['handlers']:
                    logger['handlers'].append('file')
        
        # Add structured handler if enabled
        if self.logging.enable_structured:
            logging_config['handlers']['structured'] = {
                'class': 'logging.StreamHandler',
                'level': self.logging.level,
                'formatter': 'structured',
                'stream': 'ext://sys.stdout'
            }
            for logger in logging_config['loggers'].values():
                if 'structured' not in logger['handlers']:
                    logger['handlers'].append('structured')
        
        logging.config.dictConfig(logging_config)
    
    def get_data_source_config(self, source: DataSource) -> Dict[str, Any]:
        """Get configuration for a specific data source.
        
        Args:
            source: Data source to get configuration for
            
        Returns:
            Configuration dictionary for the data source
        """
        if source == DataSource.AMAZON:
            return {
                'api_key': self.api.amazon_api_key,
                'rate_limit': self.api.amazon_rate_limit,
                'timeout': self.api.request_timeout
            }
        elif source == DataSource.UBERSUGGEST:
            return {
                'api_key': self.api.ubersuggest_api_key,
                'rate_limit': self.api.ubersuggest_rate_limit,
                'timeout': self.api.request_timeout
            }
        elif source == DataSource.KEEPA:
            return {
                'api_key': self.api.keepa_api_key,
                'rate_limit': self.api.keepa_rate_limit,
                'timeout': self.api.request_timeout
            }
        elif source == DataSource.SYNTHETIC:
            return {
                'enabled': True,
                'cache_ttl': self.cache.cache_ttl
            }
        else:
            raise ValueError(f"Unknown data source: {source}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'api': self.api.__dict__,
            'cache': self.cache.__dict__,
            'circuit_breaker': self.circuit_breaker.__dict__,
            'monitoring': self.monitoring.__dict__,
            'logging': self.logging.__dict__,
            'feature_flags': self.feature_flags.__dict__,
            'notifications': self.notifications.__dict__,
            'deployment': self.deployment.__dict__
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ConsolidatedSettings':
        """Create configuration from dictionary."""
        return cls(
            api=APIConfig(**config_dict.get('api', {})),
            cache=CacheConfig(**config_dict.get('cache', {})),
            circuit_breaker=CircuitBreakerConfig(**config_dict.get('circuit_breaker', {})),
            monitoring=MonitoringConfig(**config_dict.get('monitoring', {})),
            logging=LoggingConfig(**config_dict.get('logging', {})),
            feature_flags=FeatureFlagsConfig(**config_dict.get('feature_flags', {})),
            notifications=NotificationConfig(**config_dict.get('notifications', {})),
            deployment=DeploymentConfig(**config_dict.get('deployment', {}))
        )


# Global configuration instance
_settings: Optional[ConsolidatedSettings] = None


def get_settings() -> ConsolidatedSettings:
    """Get the global configuration instance.
    
    Returns:
        Global configuration instance
    """
    global _settings
    if _settings is None:
        _settings = ConsolidatedSettings()
    return _settings


def reload_settings() -> ConsolidatedSettings:
    """Reload the global configuration instance.
    
    Returns:
        Reloaded configuration instance
    """
    global _settings
    _settings = ConsolidatedSettings()
    return _settings


def load_config_from_file(file_path: str) -> ConsolidatedSettings:
    """Load configuration from a JSON file.
    
    Args:
        file_path: Path to the configuration file
        
    Returns:
        Configuration instance loaded from file
    """
    with open(file_path, 'r') as f:
        config_dict = json.load(f)
    return ConsolidatedSettings.from_dict(config_dict)


def save_config_to_file(settings: ConsolidatedSettings, file_path: str) -> None:
    """Save configuration to a JSON file.
    
    Args:
        settings: Configuration instance to save
        file_path: Path to save the configuration file
    """
    with open(file_path, 'w') as f:
        json.dump(settings.to_dict(), f, indent=2, default=str)