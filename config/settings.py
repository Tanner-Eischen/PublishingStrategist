"""Configuration management for KDP Strategist AI Agent.

This module handles all configuration settings including:
- API keys and credentials
- Cache settings
- Rate limiting parameters
- Model configurations
- Logging settings
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class APIConfig:
    """Configuration for external API integrations."""
    keepa_api_key: Optional[str] = field(default_factory=lambda: os.getenv("KEEPA_API_KEY"))
    keepa_rate_limit: int = field(default=60)  # requests per minute
    trends_rate_limit: int = field(default=30)  # requests per minute
    request_timeout: int = field(default=30)  # seconds
    max_retries: int = field(default=3)
    retry_delay: float = field(default=1.0)  # seconds


@dataclass
class CacheConfig:
    """Configuration for data caching system."""
    cache_type: str = field(default="file")  # "file", "redis", "memory"
    cache_dir: Path = field(default_factory=lambda: Path("cache"))
    redis_url: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_URL"))
    default_ttl: int = field(default=3600)  # seconds (1 hour)
    trends_ttl: int = field(default=86400)  # seconds (24 hours)
    keepa_ttl: int = field(default=3600)  # seconds (1 hour)
    max_cache_size: int = field(default=1000)  # max items in memory cache


@dataclass
class ModelConfig:
    """Configuration for ML models and embeddings."""
    embedding_model: str = field(default="sentence-transformers/all-MiniLM-L6-v2")
    embedding_cache_size: int = field(default=10000)
    similarity_threshold: float = field(default=0.7)
    max_keywords_per_query: int = field(default=50)
    trend_analysis_window: int = field(default=365)  # days


@dataclass
class BusinessConfig:
    """Configuration for business logic and scoring."""
    min_profitability_score: float = field(default=50.0)
    max_competition_score: float = field(default=70.0)
    trend_weight: float = field(default=0.4)
    competition_weight: float = field(default=0.3)
    profitability_weight: float = field(default=0.3)
    max_niches_per_query: int = field(default=10)
    min_monthly_searches: int = field(default=1000)


@dataclass
class LoggingConfig:
    """Configuration for logging system."""
    level: str = field(default="INFO")
    format: str = field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_path: Optional[Path] = field(default=None)
    max_file_size: int = field(default=10 * 1024 * 1024)  # 10MB
    backup_count: int = field(default=5)
    enable_structured_logging: bool = field(default=True)


@dataclass
class MCPConfig:
    """Configuration for Model Context Protocol integration."""
    server_name: str = field(default="kdp-strategist")
    server_version: str = field(default="0.1.0")
    transport_type: str = field(default="stdio")  # "stdio", "sse", "websocket"
    host: str = field(default="localhost")
    port: int = field(default=8000)
    enable_cors: bool = field(default=True)
    max_request_size: int = field(default=1024 * 1024)  # 1MB


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
        if self.environment == "production" and not self.api.keepa_api_key:
            raise ValueError("KEEPA_API_KEY is required in production environment")
        
        if self.cache.cache_type == "redis" and not self.cache.redis_url:
            raise ValueError("REDIS_URL is required when using Redis cache")
        
        if self.business.trend_weight + self.business.competition_weight + self.business.profitability_weight != 1.0:
            raise ValueError("Business weights must sum to 1.0")
    
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


# Global settings instance
settings = Settings.from_env()