"""Configuration management for KDP Strategist AI Agent.

This module handles all configuration settings including:
- API keys and credentials
- Cache settings
- Rate limiting parameters
- Model configurations
- Logging settings
- Environment-specific configurations
"""

import os
import sys
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

try:
    from dotenv import load_dotenv
    # Load .env file from project root
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables must be set manually.")


class Environment(Enum):
    """Supported environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing required values."""
    pass


@dataclass
class APIConfig:
    """Configuration for external API integrations."""
    keepa_api_key: Optional[str] = field(default_factory=lambda: os.getenv("KEEPA_API_KEY"))
    keepa_rate_limit: int = field(default_factory=lambda: int(os.getenv("KEEPA_RATE_LIMIT", "60")))
    trends_rate_limit: int = field(default_factory=lambda: int(os.getenv("TRENDS_RATE_LIMIT", "30")))
    request_timeout: int = field(default_factory=lambda: int(os.getenv("API_REQUEST_TIMEOUT", "30")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("API_MAX_RETRIES", "3")))
    retry_delay: float = field(default_factory=lambda: float(os.getenv("API_RETRY_DELAY", "1.0")))


@dataclass
class CacheConfig:
    """Configuration for data caching system."""
    cache_type: str = field(default_factory=lambda: os.getenv("CACHE_TYPE", "file"))
    cache_dir: Path = field(default_factory=lambda: Path(os.getenv("CACHE_DIR", "cache")))
    redis_url: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_URL"))
    redis_host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    redis_port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    redis_db: int = field(default_factory=lambda: int(os.getenv("REDIS_DB", "0")))
    redis_password: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_PASSWORD"))
    default_ttl: int = field(default_factory=lambda: int(os.getenv("CACHE_TTL", "3600")))
    trends_ttl: int = field(default_factory=lambda: int(os.getenv("TRENDS_CACHE_TTL", "86400")))
    keepa_ttl: int = field(default_factory=lambda: int(os.getenv("KEEPA_CACHE_TTL", "3600")))
    max_cache_size: int = field(default_factory=lambda: int(os.getenv("CACHE_MAX_SIZE", "1000")))


@dataclass
class ModelConfig:
    """Configuration for ML models and embeddings."""
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    embedding_cache_size: int = field(default_factory=lambda: int(os.getenv("EMBEDDING_CACHE_SIZE", "10000")))
    similarity_threshold: float = field(default_factory=lambda: float(os.getenv("SIMILARITY_THRESHOLD", "0.7")))
    max_keywords_per_query: int = field(default_factory=lambda: int(os.getenv("MAX_KEYWORDS_PER_QUERY", "50")))
    trend_analysis_window: int = field(default_factory=lambda: int(os.getenv("TREND_ANALYSIS_WINDOW", "365")))


@dataclass
class BusinessConfig:
    """Configuration for business logic and scoring."""
    min_profitability_score: float = field(default_factory=lambda: float(os.getenv("MIN_PROFITABILITY_SCORE", "50.0")))
    max_competition_score: float = field(default_factory=lambda: float(os.getenv("MAX_COMPETITION_SCORE", "70.0")))
    trend_weight: float = field(default_factory=lambda: float(os.getenv("TREND_WEIGHT", "0.4")))
    competition_weight: float = field(default_factory=lambda: float(os.getenv("COMPETITION_WEIGHT", "0.3")))
    profitability_weight: float = field(default_factory=lambda: float(os.getenv("PROFITABILITY_WEIGHT", "0.3")))
    max_niches_per_query: int = field(default_factory=lambda: int(os.getenv("MAX_NICHES_PER_QUERY", "10")))
    min_monthly_searches: int = field(default_factory=lambda: int(os.getenv("MIN_MONTHLY_SEARCHES", "1000")))


@dataclass
class LoggingConfig:
    """Configuration for logging system."""
    level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    format: str = field(default_factory=lambda: os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    file_path: Optional[Path] = field(default_factory=lambda: Path(os.getenv("LOG_FILE")) if os.getenv("LOG_FILE") else None)
    max_file_size: int = field(default_factory=lambda: int(os.getenv("LOG_MAX_FILE_SIZE", str(10 * 1024 * 1024))))
    backup_count: int = field(default_factory=lambda: int(os.getenv("LOG_BACKUP_COUNT", "5")))
    enable_structured_logging: bool = field(default_factory=lambda: os.getenv("LOG_STRUCTURED", "true").lower() == "true")


@dataclass
class MCPConfig:
    """Configuration for Model Context Protocol integration."""
    server_name: str = field(default_factory=lambda: os.getenv("MCP_SERVER_NAME", "kdp_strategist"))
    server_version: str = field(default_factory=lambda: os.getenv("MCP_SERVER_VERSION", "0.1.0"))
    transport_type: str = field(default_factory=lambda: os.getenv("MCP_TRANSPORT_TYPE", "stdio"))
    host: str = field(default_factory=lambda: os.getenv("MCP_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("MCP_PORT", "8000")))
    enable_cors: bool = field(default_factory=lambda: os.getenv("MCP_ENABLE_CORS", "true").lower() == "true")
    max_request_size: int = field(default_factory=lambda: int(os.getenv("MCP_MAX_REQUEST_SIZE", str(1024 * 1024))))


@dataclass
class Settings:
    """Main configuration class containing all settings."""
    api: APIConfig = field(default_factory=APIConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    models: ModelConfig = field(default_factory=ModelConfig)
    business: BusinessConfig = field(default_factory=BusinessConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    
    # Environment settings
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_config()
        self._setup_directories()
    
    def _validate_config(self) -> None:
        """Validate configuration settings."""
        errors = []
        
        # Environment validation
        try:
            Environment(self.environment)
        except ValueError:
            errors.append(f"Invalid environment '{self.environment}'. Must be one of: {', '.join([e.value for e in Environment])}")
        
        # API configuration validation
        if self.environment == Environment.PRODUCTION.value and not self.api.keepa_api_key:
            errors.append("KEEPA_API_KEY is required in production environment. Get your API key from https://keepa.com/#!api")
        
        if self.api.keepa_rate_limit <= 0:
            errors.append("KEEPA_RATE_LIMIT must be greater than 0")
        
        if self.api.trends_rate_limit <= 0:
            errors.append("TRENDS_RATE_LIMIT must be greater than 0")
        
        if self.api.request_timeout <= 0:
            errors.append("API_REQUEST_TIMEOUT must be greater than 0")
        
        # Cache configuration validation
        valid_cache_types = ["file", "redis", "memory"]
        if self.cache.cache_type not in valid_cache_types:
            errors.append(f"CACHE_TYPE must be one of: {', '.join(valid_cache_types)}")
        
        if self.cache.cache_type == "redis":
            if not self.cache.redis_url and not (self.cache.redis_host and self.cache.redis_port):
                errors.append("Redis cache requires either REDIS_URL or REDIS_HOST/REDIS_PORT configuration")
        
        if self.cache.default_ttl <= 0:
            errors.append("CACHE_TTL must be greater than 0")
        
        # Business logic validation
        weights_sum = self.business.trend_weight + self.business.competition_weight + self.business.profitability_weight
        if abs(weights_sum - 1.0) > 0.001:  # Allow for floating point precision
            errors.append(f"Business weights must sum to 1.0 (current sum: {weights_sum:.3f})")
        
        if not (0 <= self.business.min_profitability_score <= 100):
            errors.append("MIN_PROFITABILITY_SCORE must be between 0 and 100")
        
        if not (0 <= self.business.max_competition_score <= 100):
            errors.append("MAX_COMPETITION_SCORE must be between 0 and 100")
        
        # Model configuration validation
        if self.models.similarity_threshold < 0 or self.models.similarity_threshold > 1:
            errors.append("SIMILARITY_THRESHOLD must be between 0 and 1")
        
        if self.models.max_keywords_per_query <= 0:
            errors.append("MAX_KEYWORDS_PER_QUERY must be greater than 0")
        
        # Logging configuration validation
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.logging.level.upper() not in valid_log_levels:
            errors.append(f"LOG_LEVEL must be one of: {', '.join(valid_log_levels)}")
        
        # MCP configuration validation
        valid_transport_types = ["stdio", "sse", "websocket"]
        if self.mcp.transport_type not in valid_transport_types:
            errors.append(f"MCP_TRANSPORT_TYPE must be one of: {', '.join(valid_transport_types)}")
        
        if not (1 <= self.mcp.port <= 65535):
            errors.append("MCP_PORT must be between 1 and 65535")
        
        # Raise configuration error if any validation failed
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ConfigurationError(error_message)
    
    def _setup_directories(self) -> None:
        """Create necessary directories."""
        if self.cache.cache_type == "file":
            self.cache.cache_dir.mkdir(parents=True, exist_ok=True)
        
        if self.logging.file_path:
            self.logging.file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            "api": self.api.__dict__,
            "cache": {**self.cache.__dict__, "cache_dir": str(self.cache.cache_dir)},
            "models": self.models.__dict__,
            "business": self.business.__dict__,
            "logging": {**self.logging.__dict__, "file_path": str(self.logging.file_path) if self.logging.file_path else None},
            "mcp": self.mcp.__dict__,
            "environment": self.environment,
            "debug": self.debug,
        }
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""
        return cls()
    
    @classmethod
    def from_file(cls, config_path: Path) -> "Settings":
        """Load settings from configuration file."""
        import yaml
        
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
        
        # Create settings with loaded data
        # This is a simplified implementation - in practice, you'd want
        # more sophisticated config file parsing
        return cls()
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get information about the current environment configuration."""
        return {
            "environment": self.environment,
            "debug": self.debug,
            "cache_type": self.cache.cache_type,
            "has_keepa_key": bool(self.api.keepa_api_key),
            "log_level": self.logging.level,
            "mcp_transport": self.mcp.transport_type,
        }
    
    def validate_required_for_environment(self) -> List[str]:
        """Validate required settings for current environment and return missing items."""
        missing = []
        
        if self.environment == Environment.PRODUCTION.value:
            if not self.api.keepa_api_key:
                missing.append("KEEPA_API_KEY")
        
        if self.cache.cache_type == "redis":
            if not self.cache.redis_url and not (self.cache.redis_host and self.cache.redis_port):
                missing.append("REDIS_URL or REDIS_HOST/REDIS_PORT")
        
        return missing


# Global settings instance - create explicitly when needed
# settings = Settings.from_env()