"""
Custom exceptions for PC Control MCP Server.
"""

from typing import Optional, Dict, Any


class PCControlException(Exception):
    """Base exception for all PC Control MCP Server errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class SecurityException(PCControlException):
    """Raised when a security violation occurs."""
    pass


class AuthenticationException(SecurityException):
    """Raised when authentication fails."""
    pass


class AuthorizationException(SecurityException):
    """Raised when authorization fails."""
    pass


class ValidationException(PCControlException):
    """Raised when input validation fails."""
    pass


class ConfigurationException(PCControlException):
    """Raised when configuration is invalid or missing."""
    pass


class SystemException(PCControlException):
    """Raised when system operations fail."""
    pass


class ProcessException(SystemException):
    """Raised when process operations fail."""
    pass


class FileOperationException(SystemException):
    """Raised when file operations fail."""
    pass


class NetworkException(SystemException):
    """Raised when network operations fail."""
    pass


class ServiceException(SystemException):
    """Raised when service operations fail."""
    pass


class RegistryException(SystemException):
    """Raised when registry operations fail (Windows only)."""
    pass


class AutomationException(PCControlException):
    """Raised when GUI automation operations fail."""
    pass


class MonitoringException(PCControlException):
    """Raised when monitoring operations fail."""
    pass


class RateLimitException(PCControlException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class TimeoutException(PCControlException):
    """Raised when an operation times out."""
    pass


class ResourceLimitException(PCControlException):
    """Raised when resource limits are exceeded."""
    pass