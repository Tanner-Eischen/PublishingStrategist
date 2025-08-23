"""
Comprehensive configuration management for Keepa client.

This module provides a robust configuration system with environment-specific profiles,
validation, secure API key handling, and runtime updates for non-critical settings.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import warnings
from datetime import timedelta

logger = logging.getLogger(__name__)


class CacheType(Enum):
    """Supported cache types."""
    MEMORY = "memory"
    FILE = "file"
    REDIS = "redis"
    MULTI_TIER = "multi_tier"


class LogLevel(Enum):
    """Supported log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Environment(Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    max_requests_per_minute: int = 60
    burst_capacity: int = 10
    time_window_seconds: int = 60
    backoff_factor: float = 2.0
    max_backoff_seconds: int = 300
    jitter: bool = True
    
    def __post_init__(self):
        """Validate rate limit configuration."""
        if self.max_requests_per_minute <= 0:
            raise ValueError("max_requests_per_minute must be positive")
        if self.burst_capacity <= 0:
            raise ValueError("burst_capacity must be positive")
        if self.time_window_seconds <= 0:
            raise ValueError("time_window_seconds must be positive")
        if self.backoff_factor < 1.0:
            raise ValueError("backoff_factor must be >= 1.0")
        if self.max_backoff_seconds <= 0:
            raise ValueError("max_backoff_seconds must be positive")


@dataclass
class RetryConfig:
    """Retry configuration for failed requests."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_status_codes: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])
    
    def __post_init__(self):
        """Validate retry configuration."""
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.initial_delay <= 0:
            raise ValueError("initial_delay must be positive")
        if self.max_delay <= 0:
            raise ValueError("max_delay must be positive")
        if self.exponential_base < 1.0:
            raise ValueError("exponential_base must be >= 1.0")


@dataclass
class CacheConfig:
    """Caching configuration."""
    cache_type: CacheType = CacheType.FILE
    memory_cache_size: int = 1000
    file_cache_path: str = "./cache"
    redis_url: Optional[str] = None
    default_ttl_seconds: int = 3600
    product_ttl_seconds: int = 1800
    search_ttl_seconds: int = 900
    price_history_ttl_seconds: int = 7200
    enable_compression: bool = True
    max_cache_size_mb: int = 500
    
    def __post_init__(self):
        """Validate cache configuration."""
        if self.memory_cache_size <= 0:
            raise ValueError("memory_cache_size must be positive")
        if self.default_ttl_seconds <= 0:
            raise ValueError("default_ttl_seconds must be positive")
        if self.max_cache_size_mb <= 0:
            raise ValueError("max_cache_size_mb must be positive")
        
        # Validate Redis URL if provided
        if self.cache_type == CacheType.REDIS and not self.redis_url:
            raise ValueError("redis_url is required when cache_type is REDIS")


@dataclass
class TimeoutConfig:
    """Timeout configuration for API requests."""
    connect_timeout: float = 10.0
    read_timeout: float = 30.0
    total_timeout: float = 60.0
    
    def __post_init__(self):
        """Validate timeout configuration."""
        if self.connect_timeout <= 0:
            raise ValueError("connect_timeout must be positive")
        if self.read_timeout <= 0:
            raise ValueError("read_timeout must be positive")
        if self.total_timeout <= 0:
            raise ValueError("total_timeout must be positive")
        if self.total_timeout < max(self.connect_timeout, self.read_timeout):
            raise ValueError("total_timeout must be >= max(connect_timeout, read_timeout)")


@dataclass
class SecurityConfig:
    """Security configuration for API key handling."""
    api_key_env_var: str = "KEEPA_API_KEY"
    api_key_file_path: Optional[str] = None
    encrypt_cached_data: bool = False
    mask_api_key_in_logs: bool = True
    validate_ssl_certificates: bool = True
    api_key_rotation_enabled: bool = False
    api_key_rotation_interval_hours: int = 24
    secure_key_storage: bool = True
    key_derivation_iterations: int = 100000
    
    def __post_init__(self):
        """Validate security configuration."""
        if not self.api_key_env_var and not self.api_key_file_path:
            raise ValueError("Either api_key_env_var or api_key_file_path must be specified")
        
        if self.api_key_rotation_interval_hours <= 0:
            raise ValueError("api_key_rotation_interval_hours must be positive")
        
        if self.key_derivation_iterations < 10000:
            raise ValueError("key_derivation_iterations must be at least 10000 for security")


@dataclass
class LoggingConfig:
    """Logging configuration."""
    log_level: LogLevel = LogLevel.INFO
    log_file_path: Optional[str] = None
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_requests: bool = True
    log_responses: bool = False
    log_cache_operations: bool = False
    max_log_file_size_mb: int = 100
    log_rotation_count: int = 5
    
    def __post_init__(self):
        """Validate logging configuration."""
        if self.max_log_file_size_mb <= 0:
            raise ValueError("max_log_file_size_mb must be positive")
        if self.log_rotation_count < 0:
            raise ValueError("log_rotation_count must be non-negative")


@dataclass
class KeepaConfig:
    """
    Comprehensive configuration for Keepa client.
    
    This class provides a centralized configuration system with validation,
    environment-specific profiles, and secure API key handling.
    """
    
    # Core API settings
    api_key: Optional[str] = None
    base_url: str = "https://api.keepa.com"
    user_agent: str = "KDP-Strategist/1.0"
    
    # Environment and profile
    environment: Environment = Environment.DEVELOPMENT
    profile_name: str = "default"
    
    # Component configurations
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Feature flags
    enable_batch_processing: bool = True
    enable_advanced_search: bool = True
    enable_price_history: bool = True
    enable_health_monitoring: bool = True
    
    # Performance settings
    max_concurrent_requests: int = 5
    connection_pool_size: int = 10
    enable_request_compression: bool = True
    
    # Development settings
    debug_mode: bool = False
    mock_api_responses: bool = False
    validate_responses: bool = True
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        self._validate_configuration()
        self._load_api_key()
        self._setup_logging()
    
    def _validate_configuration(self):
        """Validate the complete configuration."""
        # Validate core settings
        if not self.base_url:
            raise ValueError("base_url cannot be empty")
        
        if not self.user_agent:
            raise ValueError("user_agent cannot be empty")
        
        if self.max_concurrent_requests <= 0:
            raise ValueError("max_concurrent_requests must be positive")
        
        if self.connection_pool_size <= 0:
            raise ValueError("connection_pool_size must be positive")
        
        # Environment-specific validations
        if self.environment == Environment.PRODUCTION:
            if self.debug_mode:
                warnings.warn("Debug mode is enabled in production environment")
            if self.mock_api_responses:
                raise ValueError("Mock API responses cannot be enabled in production")
    
    def _load_api_key(self):
        """Load API key from environment or file."""
        if self.api_key:
            return  # Already set
        
        # Try environment variable first
        if self.security.api_key_env_var:
            self.api_key = os.getenv(self.security.api_key_env_var)
        
        # Try file if environment variable not found
        if not self.api_key and self.security.api_key_file_path:
            try:
                with open(self.security.api_key_file_path, 'r') as f:
                    self.api_key = f.read().strip()
            except FileNotFoundError:
                logger.warning(f"API key file not found: {self.security.api_key_file_path}")
            except Exception as e:
                logger.error(f"Error reading API key file: {e}")
        
        if not self.api_key:
            raise ValueError(
                f"API key not found. Set {self.security.api_key_env_var} environment variable "
                f"or provide api_key_file_path"
            )
    
    def _setup_logging(self):
        """Setup logging based on configuration."""
        logging.basicConfig(
            level=getattr(logging, self.logging.log_level.value),
            format=self.logging.log_format
        )
        
        if self.logging.log_file_path:
            from logging.handlers import RotatingFileHandler
            handler = RotatingFileHandler(
                self.logging.log_file_path,
                maxBytes=self.logging.max_log_file_size_mb * 1024 * 1024,
                backupCount=self.logging.log_rotation_count
            )
            handler.setFormatter(logging.Formatter(self.logging.log_format))
            logging.getLogger().addHandler(handler)
    
    def get_masked_api_key(self) -> str:
        """Get masked API key for logging purposes."""
        if not self.api_key:
            return "NOT_SET"
        
        if self.security.mask_api_key_in_logs:
            return f"{self.api_key[:4]}...{self.api_key[-4:]}" if len(self.api_key) > 8 else "***"
        
        return self.api_key
    
    def store_api_key_securely(self, api_key: str, key_file_path: Optional[str] = None) -> bool:
        """
        Store API key securely with encryption.
        
        Args:
            api_key: The API key to store
            key_file_path: Optional path to store the key file
            
        Returns:
            True if key was stored successfully, False otherwise
        """
        if not self.security.secure_key_storage:
            logger.warning("Secure key storage is disabled")
            return False
        
        try:
            import base64
            import hashlib
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            
            # Generate a salt for key derivation
            salt = os.urandom(16)
            
            # Derive encryption key from a master password (in production, this should come from a secure source)
            master_password = os.getenv('KEEPA_MASTER_PASSWORD', 'default_master_password').encode()
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=self.security.key_derivation_iterations,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password))
            
            # Encrypt the API key
            fernet = Fernet(key)
            encrypted_key = fernet.encrypt(api_key.encode())
            
            # Store encrypted key and salt
            key_data = {
                'encrypted_key': base64.b64encode(encrypted_key).decode(),
                'salt': base64.b64encode(salt).decode(),
                'iterations': self.security.key_derivation_iterations
            }
            
            storage_path = key_file_path or self.security.api_key_file_path or '.keepa_key'
            with open(storage_path, 'w') as f:
                json.dump(key_data, f)
            
            # Set restrictive permissions
            os.chmod(storage_path, 0o600)
            
            logger.info(f"API key stored securely at {storage_path}")
            return True
            
        except ImportError:
            logger.error("cryptography library not available for secure key storage")
            return False
        except Exception as e:
            logger.error(f"Failed to store API key securely: {e}")
            return False
    
    def load_api_key_securely(self, key_file_path: Optional[str] = None) -> Optional[str]:
        """
        Load API key from secure storage.
        
        Args:
            key_file_path: Optional path to the key file
            
        Returns:
            Decrypted API key or None if loading failed
        """
        if not self.security.secure_key_storage:
            return None
        
        try:
            import base64
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            
            storage_path = key_file_path or self.security.api_key_file_path or '.keepa_key'
            
            if not os.path.exists(storage_path):
                logger.warning(f"Secure key file not found: {storage_path}")
                return None
            
            # Load encrypted key data
            with open(storage_path, 'r') as f:
                key_data = json.load(f)
            
            # Derive decryption key
            master_password = os.getenv('KEEPA_MASTER_PASSWORD', 'default_master_password').encode()
            salt = base64.b64decode(key_data['salt'])
            iterations = key_data.get('iterations', self.security.key_derivation_iterations)
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=iterations,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password))
            
            # Decrypt the API key
            fernet = Fernet(key)
            encrypted_key = base64.b64decode(key_data['encrypted_key'])
            decrypted_key = fernet.decrypt(encrypted_key).decode()
            
            return decrypted_key
            
        except ImportError:
            logger.error("cryptography library not available for secure key loading")
            return None
        except Exception as e:
            logger.error(f"Failed to load API key securely: {e}")
            return None
    
    def rotate_api_key(self, new_api_key: str) -> bool:
        """
        Rotate the API key with validation and secure storage.
        
        Args:
            new_api_key: The new API key to use
            
        Returns:
            True if rotation was successful, False otherwise
        """
        if not self.security.api_key_rotation_enabled:
            logger.warning("API key rotation is disabled")
            return False
        
        try:
            # Validate new API key format
            if len(new_api_key) < 32:
                logger.error("New API key is too short")
                return False
            
            # Store old key for rollback
            old_key = self.api_key
            
            # Update to new key
            self.api_key = new_api_key
            
            # Store securely if enabled
            if self.security.secure_key_storage:
                if not self.store_api_key_securely(new_api_key):
                    # Rollback on storage failure
                    self.api_key = old_key
                    return False
            
            logger.info("API key rotated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate API key: {e}")
            return False
    
    def update_runtime_setting(self, setting_path: str, value: Any) -> bool:
        """
        Update non-critical settings at runtime.
        
        Args:
            setting_path: Dot-separated path to setting (e.g., 'cache.default_ttl_seconds')
            value: New value for the setting
            
        Returns:
            True if setting was updated, False if setting is not updatable at runtime
        """
        # Define which settings can be updated at runtime
        updatable_settings = {
            'cache.default_ttl_seconds',
            'cache.product_ttl_seconds',
            'cache.search_ttl_seconds',
            'cache.price_history_ttl_seconds',
            'cache.enable_compression',
            'logging.log_level',
            'logging.log_requests',
            'logging.log_responses',
            'logging.log_cache_operations',
            'rate_limit.max_requests_per_minute',
            'rate_limit.burst_capacity',
            'rate_limit.jitter',
            'retry.max_retries',
            'retry.initial_delay',
            'retry.jitter',
            'timeout.read_timeout',
            'timeout.total_timeout',
            'debug_mode',
            'validate_responses',
            'max_concurrent_requests',
            'enable_request_compression'
        }
        
        if setting_path not in updatable_settings:
            logger.warning(f"Setting '{setting_path}' is not updatable at runtime")
            return False
        
        try:
            # Navigate to the setting and update it
            parts = setting_path.split('.')
            obj = self
            
            for part in parts[:-1]:
                obj = getattr(obj, part)
            
            # Validate the new value
            old_value = getattr(obj, parts[-1])
            
            # Type validation based on old value type
            if isinstance(old_value, bool) and not isinstance(value, bool):
                if isinstance(value, str):
                    value = value.lower() in ('true', '1', 'yes', 'on')
                else:
                    raise ValueError(f"Expected boolean value, got {type(value)}")
            elif isinstance(old_value, int) and not isinstance(value, int):
                value = int(value)
            elif isinstance(old_value, float) and not isinstance(value, (int, float)):
                value = float(value)
            elif isinstance(old_value, LogLevel) and isinstance(value, str):
                value = LogLevel(value.upper())
            
            setattr(obj, parts[-1], value)
            
            # Re-validate the configuration section
            if parts[0] in ['rate_limit', 'retry', 'cache', 'timeout', 'security', 'logging']:
                getattr(self, parts[0]).__post_init__()
            
            logger.info(f"Updated runtime setting '{setting_path}': {old_value} -> {value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update runtime setting '{setting_path}': {e}")
            # Restore old value
            try:
                setattr(obj, parts[-1], old_value)
            except:
                pass
            return False
    
    def get_runtime_updatable_settings(self) -> Dict[str, Any]:
        """
        Get all settings that can be updated at runtime with their current values.
        
        Returns:
            Dictionary mapping setting paths to current values
        """
        updatable_settings = {
            'cache.default_ttl_seconds': self.cache.default_ttl_seconds,
            'cache.product_ttl_seconds': self.cache.product_ttl_seconds,
            'cache.search_ttl_seconds': self.cache.search_ttl_seconds,
            'cache.price_history_ttl_seconds': self.cache.price_history_ttl_seconds,
            'cache.enable_compression': self.cache.enable_compression,
            'logging.log_level': self.logging.log_level.value,
            'logging.log_requests': self.logging.log_requests,
            'logging.log_responses': self.logging.log_responses,
            'logging.log_cache_operations': self.logging.log_cache_operations,
            'rate_limit.max_requests_per_minute': self.rate_limit.max_requests_per_minute,
            'rate_limit.burst_capacity': self.rate_limit.burst_capacity,
            'rate_limit.jitter': self.rate_limit.jitter,
            'retry.max_retries': self.retry.max_retries,
            'retry.initial_delay': self.retry.initial_delay,
            'retry.jitter': self.retry.jitter,
            'timeout.read_timeout': self.timeout.read_timeout,
            'timeout.total_timeout': self.timeout.total_timeout,
            'debug_mode': self.debug_mode,
            'validate_responses': self.validate_responses,
            'max_concurrent_requests': self.max_concurrent_requests,
            'enable_request_compression': self.enable_request_compression
        }
        
        return updatable_settings
    
    def batch_update_runtime_settings(self, settings: Dict[str, Any]) -> Dict[str, bool]:
        """
        Update multiple runtime settings in a single operation.
        
        Args:
            settings: Dictionary mapping setting paths to new values
            
        Returns:
            Dictionary mapping setting paths to success status
        """
        results = {}
        
        for setting_path, value in settings.items():
            results[setting_path] = self.update_runtime_setting(setting_path, value)
        
        return results
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        config_dict = asdict(self)
        
        # Mask sensitive information
        if self.security.mask_api_key_in_logs and config_dict.get('api_key'):
            config_dict['api_key'] = self.get_masked_api_key()
        
        return config_dict
    
    def save_to_file(self, file_path: str, include_sensitive: bool = False):
        """
        Save configuration to JSON file.
        
        Args:
            file_path: Path to save configuration file
            include_sensitive: Whether to include sensitive data like API keys
        """
        config_dict = self.to_dict()
        
        if not include_sensitive:
            config_dict.pop('api_key', None)
        
        with open(file_path, 'w') as f:
            json.dump(config_dict, f, indent=2, default=str)
        
        logger.info(f"Configuration saved to {file_path}")
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'KeepaConfig':
        """Create configuration from dictionary."""
        # Convert nested dictionaries to dataclass instances
        if 'rate_limit' in config_dict:
            config_dict['rate_limit'] = RateLimitConfig(**config_dict['rate_limit'])
        
        if 'retry' in config_dict:
            config_dict['retry'] = RetryConfig(**config_dict['retry'])
        
        if 'cache' in config_dict:
            config_dict['cache'] = CacheConfig(**config_dict['cache'])
        
        if 'timeout' in config_dict:
            config_dict['timeout'] = TimeoutConfig(**config_dict['timeout'])
        
        if 'security' in config_dict:
            config_dict['security'] = SecurityConfig(**config_dict['security'])
        
        if 'logging' in config_dict:
            config_dict['logging'] = LoggingConfig(**config_dict['logging'])
        
        # Convert enum strings back to enums
        if 'environment' in config_dict and isinstance(config_dict['environment'], str):
            config_dict['environment'] = Environment(config_dict['environment'])
        
        if 'cache' in config_dict and 'cache_type' in config_dict['cache']:
            if isinstance(config_dict['cache'].cache_type, str):
                config_dict['cache'].cache_type = CacheType(config_dict['cache'].cache_type)
        
        if 'logging' in config_dict and 'log_level' in config_dict['logging']:
            if isinstance(config_dict['logging'].log_level, str):
                config_dict['logging'].log_level = LogLevel(config_dict['logging'].log_level)
        
        return cls(**config_dict)
    
    @classmethod
    def from_file(cls, file_path: str) -> 'KeepaConfig':
        """Load configuration from JSON file."""
        with open(file_path, 'r') as f:
            config_dict = json.load(f)
        
        return cls.from_dict(config_dict)
    
    def validate(self) -> List[str]:
        """
        Validate the complete configuration and return list of issues.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        issues = []
        
        try:
            self._validate_configuration()
        except ValueError as e:
            issues.append(str(e))
        
        # Validate component configurations
        for component_name in ['rate_limit', 'retry', 'cache', 'timeout', 'security', 'logging']:
            try:
                component = getattr(self, component_name)
                component.__post_init__()
            except ValueError as e:
                issues.append(f"{component_name}: {e}")
        
        return issues


class ConfigurationManager:
    """
    Manages configuration profiles and environment-specific settings.
    """
    
    def __init__(self, config_dir: str = "./config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self._profiles: Dict[str, KeepaConfig] = {}
        self._current_profile: Optional[str] = None
    
    def create_profile(self, profile_name: str, config: KeepaConfig):
        """Create or update a configuration profile."""
        config.profile_name = profile_name
        self._profiles[profile_name] = config
        
        # Save to file
        profile_file = self.config_dir / f"{profile_name}.json"
        config.save_to_file(str(profile_file))
        
        logger.info(f"Created configuration profile: {profile_name}")
    
    def load_profile(self, profile_name: str) -> KeepaConfig:
        """Load a configuration profile."""
        if profile_name in self._profiles:
            return self._profiles[profile_name]
        
        # Try to load from file
        profile_file = self.config_dir / f"{profile_name}.json"
        if profile_file.exists():
            config = KeepaConfig.from_file(str(profile_file))
            self._profiles[profile_name] = config
            return config
        
        raise ValueError(f"Configuration profile '{profile_name}' not found")
    
    def set_active_profile(self, profile_name: str):
        """Set the active configuration profile."""
        if profile_name not in self._profiles:
            self.load_profile(profile_name)
        
        self._current_profile = profile_name
        logger.info(f"Set active configuration profile: {profile_name}")
    
    def get_active_config(self) -> KeepaConfig:
        """Get the currently active configuration."""
        if not self._current_profile:
            raise ValueError("No active configuration profile set")
        
        return self._profiles[self._current_profile]
    
    def list_profiles(self) -> List[str]:
        """List all available configuration profiles."""
        # Get profiles from memory and files
        file_profiles = [
            f.stem for f in self.config_dir.glob("*.json")
            if f.is_file()
        ]
        
        all_profiles = set(self._profiles.keys()) | set(file_profiles)
        return sorted(all_profiles)
    
    def delete_profile(self, profile_name: str):
        """Delete a configuration profile."""
        # Remove from memory
        self._profiles.pop(profile_name, None)
        
        # Remove file
        profile_file = self.config_dir / f"{profile_name}.json"
        if profile_file.exists():
            profile_file.unlink()
        
        # Clear active profile if it was deleted
        if self._current_profile == profile_name:
            self._current_profile = None
        
        logger.info(f"Deleted configuration profile: {profile_name}")
    
    def create_environment_profiles(self):
        """Create default profiles for different environments."""
        # Development profile
        dev_config = KeepaConfig(
            environment=Environment.DEVELOPMENT,
            debug_mode=True,
            mock_api_responses=False,
            rate_limit=RateLimitConfig(max_requests_per_minute=30),
            cache=CacheConfig(cache_type=CacheType.FILE, default_ttl_seconds=1800),
            logging=LoggingConfig(log_level=LogLevel.DEBUG, log_requests=True)
        )
        self.create_profile("development", dev_config)
        
        # Testing profile
        test_config = KeepaConfig(
            environment=Environment.TESTING,
            debug_mode=True,
            mock_api_responses=True,
            rate_limit=RateLimitConfig(max_requests_per_minute=10),
            cache=CacheConfig(cache_type=CacheType.MEMORY, default_ttl_seconds=300),
            logging=LoggingConfig(log_level=LogLevel.DEBUG)
        )
        self.create_profile("testing", test_config)
        
        # Staging profile
        staging_config = KeepaConfig(
            environment=Environment.STAGING,
            debug_mode=False,
            mock_api_responses=False,
            rate_limit=RateLimitConfig(max_requests_per_minute=45, burst_capacity=15),
            cache=CacheConfig(
                cache_type=CacheType.REDIS,
                redis_url="redis://localhost:6379/1",
                default_ttl_seconds=2700
            ),
            logging=LoggingConfig(
                log_level=LogLevel.INFO,
                log_file_path="./logs/keepa_client_staging.log",
                log_requests=True
            ),
            security=SecurityConfig(
                encrypt_cached_data=True,
                validate_ssl_certificates=True,
                secure_key_storage=True
            )
        )
        self.create_profile("staging", staging_config)
        
        # Production profile
        prod_config = KeepaConfig(
            environment=Environment.PRODUCTION,
            debug_mode=False,
            mock_api_responses=False,
            rate_limit=RateLimitConfig(max_requests_per_minute=60, burst_capacity=20),
            cache=CacheConfig(
                cache_type=CacheType.REDIS,
                redis_url="redis://localhost:6379/0",
                default_ttl_seconds=3600
            ),
            logging=LoggingConfig(
                log_level=LogLevel.INFO,
                log_file_path="./logs/keepa_client.log",
                log_requests=False
            ),
            security=SecurityConfig(
                encrypt_cached_data=True,
                validate_ssl_certificates=True,
                secure_key_storage=True,
                api_key_rotation_enabled=True
            )
        )
        self.create_profile("production", prod_config)
        
        logger.info("Created default environment profiles")
    
    def clone_profile(self, source_profile: str, target_profile: str, modifications: Optional[Dict[str, Any]] = None) -> KeepaConfig:
        """
        Clone an existing profile with optional modifications.
        
        Args:
            source_profile: Name of the profile to clone
            target_profile: Name for the new profile
            modifications: Optional dictionary of modifications to apply
            
        Returns:
            The new configuration
        """
        source_config = self.load_profile(source_profile)
        
        # Create a deep copy
        config_dict = source_config.to_dict()
        
        # Apply modifications if provided
        if modifications:
            self._apply_modifications(config_dict, modifications)
        
        # Create new config from modified dictionary
        new_config = KeepaConfig.from_dict(config_dict)
        new_config.profile_name = target_profile
        
        # Save the new profile
        self.create_profile(target_profile, new_config)
        
        return new_config
    
    def _apply_modifications(self, config_dict: Dict[str, Any], modifications: Dict[str, Any]):
        """Apply modifications to configuration dictionary."""
        for key, value in modifications.items():
            if '.' in key:
                # Handle nested keys like 'cache.default_ttl_seconds'
                parts = key.split('.')
                current = config_dict
                
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                current[parts[-1]] = value
            else:
                config_dict[key] = value
    
    def export_profile(self, profile_name: str, export_path: str, include_sensitive: bool = False):
        """
        Export a profile to a file with optional sensitive data.
        
        Args:
            profile_name: Name of the profile to export
            export_path: Path to export the profile to
            include_sensitive: Whether to include sensitive data like API keys
        """
        config = self.load_profile(profile_name)
        config.save_to_file(export_path, include_sensitive=include_sensitive)
        logger.info(f"Exported profile '{profile_name}' to {export_path}")
    
    def import_profile(self, profile_name: str, import_path: str) -> KeepaConfig:
        """
        Import a profile from a file.
        
        Args:
            profile_name: Name for the imported profile
            import_path: Path to import the profile from
            
        Returns:
            The imported configuration
        """
        config = KeepaConfig.from_file(import_path)
        config.profile_name = profile_name
        self.create_profile(profile_name, config)
        logger.info(f"Imported profile '{profile_name}' from {import_path}")
        return config
    
    def validate_all_profiles(self) -> Dict[str, Any]:
        """
        Validate all available profiles.
        
        Returns:
            Dictionary mapping profile names to validation results
        """
        from .config_validator import ConfigValidator
        
        validator = ConfigValidator()
        results = {}
        
        for profile_name in self.list_profiles():
            try:
                config = self.load_profile(profile_name)
                # Set a dummy API key for validation if not present
                if not config.api_key:
                    config.api_key = "dummy_key_for_validation_only_1234567890"
                
                validation_result = validator.validate_config(config)
                results[profile_name] = validation_result.to_dict()
            except Exception as e:
                results[profile_name] = {
                    'is_valid': False,
                    'errors': [f"Failed to load or validate profile: {e}"],
                    'warnings': [],
                    'recommendations': []
                }
        
        return results


def get_default_config() -> KeepaConfig:
    """Get default configuration for development."""
    return KeepaConfig(
        environment=Environment.DEVELOPMENT,
        debug_mode=True,
        rate_limit=RateLimitConfig(max_requests_per_minute=30),
        cache=CacheConfig(cache_type=CacheType.FILE),
        logging=LoggingConfig(log_level=LogLevel.INFO)
    )


def load_config_from_env() -> KeepaConfig:
    """Load configuration from environment variables."""
    config = KeepaConfig()
    
    # Override with environment variables if present
    if os.getenv('KEEPA_DEBUG_MODE'):
        config.debug_mode = os.getenv('KEEPA_DEBUG_MODE').lower() == 'true'
    
    if os.getenv('KEEPA_ENVIRONMENT'):
        config.environment = Environment(os.getenv('KEEPA_ENVIRONMENT'))
    
    if os.getenv('KEEPA_CACHE_TYPE'):
        config.cache.cache_type = CacheType(os.getenv('KEEPA_CACHE_TYPE'))
    
    if os.getenv('KEEPA_REDIS_URL'):
        config.cache.redis_url = os.getenv('KEEPA_REDIS_URL')
    
    if os.getenv('KEEPA_LOG_LEVEL'):
        config.logging.log_level = LogLevel(os.getenv('KEEPA_LOG_LEVEL'))
    
    if os.getenv('KEEPA_MAX_REQUESTS_PER_MINUTE'):
        config.rate_limit.max_requests_per_minute = int(os.getenv('KEEPA_MAX_REQUESTS_PER_MINUTE'))
    
    return config