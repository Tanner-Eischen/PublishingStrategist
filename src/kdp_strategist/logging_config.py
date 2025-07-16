"""Structured logging configuration for KDP Strategist application.

This module provides centralized logging configuration with support for
structured logging, multiple handlers, and environment-specific settings.
"""

import logging
import logging.config
import logging.handlers
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum

from config.settings import LoggingConfig


class LogLevel(Enum):
    """Supported log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None
            }
        
        # Add extra fields if enabled
        if self.include_extra:
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in {
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'lineno', 'funcName', 'created',
                    'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'getMessage', 'exc_info',
                    'exc_text', 'stack_info'
                }:
                    extra_fields[key] = value
            
            if extra_fields:
                log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry, default=str)


class ContextFilter(logging.Filter):
    """Filter to add contextual information to log records."""
    
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.context = context or {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context information to log record."""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


class LoggingManager:
    """Centralized logging configuration manager."""
    
    def __init__(self, config: LoggingConfig):
        self.config = config
        self.is_configured = False
        self._loggers: Dict[str, logging.Logger] = {}
    
    def configure_logging(self) -> None:
        """Configure logging based on settings."""
        if self.is_configured:
            return
        
        # Create logs directory if file logging is enabled
        if self.config.file_path:
            self.config.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.level.upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Add console handler
        console_handler = self._create_console_handler()
        root_logger.addHandler(console_handler)
        
        # Add file handler if configured
        if self.config.file_path:
            file_handler = self._create_file_handler()
            root_logger.addHandler(file_handler)
        
        # Configure specific loggers
        self._configure_application_loggers()
        
        # Suppress noisy third-party loggers
        self._configure_third_party_loggers()
        
        self.is_configured = True
        logging.info("Logging configuration completed")
    
    def _create_console_handler(self) -> logging.Handler:
        """Create console handler with appropriate formatter."""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, self.config.level.upper()))
        
        if self.config.enable_structured_logging:
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter(
                fmt=self.config.format,
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        handler.setFormatter(formatter)
        return handler
    
    def _create_file_handler(self) -> logging.Handler:
        """Create rotating file handler."""
        handler = logging.handlers.RotatingFileHandler(
            filename=self.config.file_path,
            maxBytes=self.config.max_file_size,
            backupCount=self.config.backup_count,
            encoding='utf-8'
        )
        handler.setLevel(logging.DEBUG)  # File handler captures all levels
        
        # Use detailed formatter for file logging
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        return handler
    
    def _configure_application_loggers(self) -> None:
        """Configure application-specific loggers."""
        app_loggers = [
            'kdp_strategist',
            'kdp_strategist.agent',
            'kdp_strategist.data',
            'kdp_strategist.models',
            'kdp_strategist.utils',
            'api'
        ]
        
        for logger_name in app_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(getattr(logging, self.config.level.upper()))
            # Don't propagate to avoid duplicate messages
            logger.propagate = False
            
            # Add the same handlers as root logger
            for handler in logging.getLogger().handlers:
                logger.addHandler(handler)
            
            self._loggers[logger_name] = logger
    
    def _configure_third_party_loggers(self) -> None:
        """Configure third-party library loggers to reduce noise."""
        # Suppress noisy loggers
        noisy_loggers = [
            'urllib3.connectionpool',
            'requests.packages.urllib3',
            'asyncio',
            'aiohttp.access'
        ]
        
        for logger_name in noisy_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.WARNING)
        
        # Set specific levels for important third-party loggers
        logging.getLogger('uvicorn').setLevel(logging.INFO)
        logging.getLogger('fastapi').setLevel(logging.INFO)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a configured logger by name."""
        if not self.is_configured:
            self.configure_logging()
        
        if name not in self._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(getattr(logging, self.config.level.upper()))
            self._loggers[name] = logger
        
        return self._loggers[name]
    
    def add_context_filter(self, logger_name: str, context: Dict[str, Any]) -> None:
        """Add context filter to a specific logger."""
        logger = self.get_logger(logger_name)
        context_filter = ContextFilter(context)
        logger.addFilter(context_filter)
    
    def log_performance_metrics(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        **kwargs
    ) -> None:
        """Log performance metrics in a structured format."""
        logger = self.get_logger('kdp_strategist.performance')
        
        metrics = {
            "operation": operation,
            "duration_ms": duration_ms,
            "success": success,
            **kwargs
        }
        
        if success:
            logger.info(f"Operation completed: {operation}", extra=metrics)
        else:
            logger.warning(f"Operation failed: {operation}", extra=metrics)
    
    def log_api_request(
        self,
        method: str,
        url: str,
        status_code: int,
        duration_ms: float,
        request_id: Optional[str] = None
    ) -> None:
        """Log API request in a structured format."""
        logger = self.get_logger('kdp_strategist.api')
        
        request_info = {
            "method": method,
            "url": url,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "request_id": request_id
        }
        
        if 200 <= status_code < 400:
            logger.info(f"API request: {method} {url}", extra=request_info)
        elif 400 <= status_code < 500:
            logger.warning(f"API client error: {method} {url}", extra=request_info)
        else:
            logger.error(f"API server error: {method} {url}", extra=request_info)


# Global logging manager instance
_logging_manager: Optional[LoggingManager] = None


def get_logging_manager(config: Optional[LoggingConfig] = None) -> LoggingManager:
    """Get the global logging manager instance."""
    global _logging_manager
    
    if _logging_manager is None:
        if config is None:
            from config.settings import Settings
            settings = Settings.from_env()
            config = settings.logging
        
        _logging_manager = LoggingManager(config)
        _logging_manager.configure_logging()
    
    return _logging_manager


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger by name."""
    manager = get_logging_manager()
    return manager.get_logger(name)


def configure_logging(config: Optional[LoggingConfig] = None) -> None:
    """Configure logging for the application."""
    manager = get_logging_manager(config)
    manager.configure_logging()


# Convenience function for structured logging
def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    **context
) -> None:
    """Log message with additional context."""
    log_func = getattr(logger, level.lower())
    log_func(message, extra=context)