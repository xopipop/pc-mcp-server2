"""
Logging configuration and utilities for PC Control MCP Server.
"""

import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime
import traceback

from loguru import logger
import yaml

from .exceptions import ConfigurationException


class LoggerConfig:
    """Logger configuration management."""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        self.config_path = config_path
        self.config = self._load_config()
        self._setup_logger()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load logger configuration from file or use defaults."""
        if self.config_path and Path(self.config_path).exists():
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        
        # Default configuration
        return {
            'server': {
                'log_level': 'INFO',
                'log_format': '{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}'
            }
        }
    
    def _setup_logger(self):
        """Configure loguru logger."""
        # Remove default handler
        logger.remove()
        
        # Get log level from config
        log_level = self.config.get('server', {}).get('log_level', 'INFO')
        log_format = self.config.get('server', {}).get('log_format', 
            '{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}')
        
        # Console handler
        logger.add(
            sys.stderr,
            format=log_format,
            level=log_level,
            colorize=True,
            backtrace=True,
            diagnose=True
        )
        
        # File handler
        log_dir = Path.home() / '.pc_control_mcp' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_dir / 'pc_control_{time:YYYY-MM-DD}.log',
            rotation='1 day',
            retention='30 days',
            format=log_format,
            level=log_level,
            backtrace=True,
            diagnose=True,
            compression='zip'
        )
        
        # Audit log handler
        if self.config.get('security', {}).get('audit', {}).get('enabled', True):
            logger.add(
                log_dir / 'audit_{time:YYYY-MM-DD}.log',
                rotation='1 day',
                retention='30 days',
                format='{time:YYYY-MM-DD HH:mm:ss} | AUDIT | {message}',
                level='INFO',
                filter=lambda record: 'audit' in record['extra'],
                compression='zip'
            )


class AuditLogger:
    """Specialized audit logger for security events."""
    
    def __init__(self):
        self.logger = logger.bind(audit=True)
    
    def log_operation(self, 
                     user_id: Optional[str],
                     action: str,
                     resource: str,
                     result: str,
                     details: Optional[Dict[str, Any]] = None,
                     ip_address: Optional[str] = None,
                     user_agent: Optional[str] = None):
        """Log an auditable operation."""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id or 'anonymous',
            'action': action,
            'resource': resource,
            'result': result,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'details': details or {}
        }
        
        # Mask sensitive data
        audit_entry = self._mask_sensitive_data(audit_entry)
        
        self.logger.info(f"AUDIT: {json.dumps(audit_entry)}")
    
    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data in audit logs."""
        sensitive_fields = ['password', 'token', 'api_key', 'secret', 'credential']
        
        def mask_dict(d: Dict[str, Any]) -> Dict[str, Any]:
            masked = {}
            for key, value in d.items():
                if any(field in key.lower() for field in sensitive_fields):
                    masked[key] = '***MASKED***'
                elif isinstance(value, dict):
                    masked[key] = mask_dict(value)
                elif isinstance(value, list):
                    masked[key] = [mask_dict(item) if isinstance(item, dict) else item for item in value]
                else:
                    masked[key] = value
            return masked
        
        return mask_dict(data)


class StructuredLogger:
    """Structured logging wrapper for consistent log format."""
    
    def __init__(self, name: str):
        self.logger = logger.bind(name=name)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured data."""
        self.logger.debug(message, **self._prepare_extra(kwargs))
    
    def info(self, message: str, **kwargs):
        """Log info message with structured data."""
        self.logger.info(message, **self._prepare_extra(kwargs))
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data."""
        self.logger.warning(message, **self._prepare_extra(kwargs))
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log error message with structured data."""
        extra = self._prepare_extra(kwargs)
        if exception:
            extra['exception_type'] = type(exception).__name__
            extra['exception_message'] = str(exception)
            extra['traceback'] = traceback.format_exc()
        self.logger.error(message, **extra)
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log critical message with structured data."""
        extra = self._prepare_extra(kwargs)
        if exception:
            extra['exception_type'] = type(exception).__name__
            extra['exception_message'] = str(exception)
            extra['traceback'] = traceback.format_exc()
        self.logger.critical(message, **extra)
    
    def _prepare_extra(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare extra data for logging."""
        return {k: v for k, v in data.items() if v is not None}


# Initialize default logger
def setup_logging(config_path: Optional[Union[str, Path]] = None):
    """Setup logging configuration."""
    LoggerConfig(config_path)


# Create module logger
log = StructuredLogger(__name__)