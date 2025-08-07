"""
Security management for PC Control MCP Server.
"""

import re
import hashlib
import secrets
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import jwt
import bcrypt

from .config import get_config, SecurityConfig
from .logger import StructuredLogger, AuditLogger
from .exceptions import (
    SecurityException, 
    AuthenticationException, 
    AuthorizationException,
    ValidationException,
    RateLimitException
)

log = StructuredLogger(__name__)


class User:
    """User representation."""
    
    def __init__(self, user_id: str, roles: Optional[List[str]] = None, 
                 metadata: Optional[Dict[str, Any]] = None):
        self.user_id = user_id
        self.roles = roles or []
        self.metadata = metadata or {}
        self.authenticated_at = datetime.now(timezone.utc)


class AuthResult:
    """Authentication result."""
    
    def __init__(self, success: bool, user: Optional[User] = None, 
                 token: Optional[str] = None, error: Optional[str] = None):
        self.success = success
        self.user = user
        self.token = token
        self.error = error


class Operation:
    """Operation representation."""
    
    def __init__(self, action: str, resource: str, 
                 details: Optional[Dict[str, Any]] = None):
        self.action = action
        self.resource = resource
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc)


class SessionManager:
    """Session management."""
    
    def __init__(self):
        self.sessions: Dict[str, User] = {}
        self.tokens: Dict[str, str] = {}  # token -> user_id
        
    def create_session(self, user: User) -> str:
        """Create a new session."""
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = user
        return session_id
    
    def get_session(self, session_id: str) -> Optional[User]:
        """Get session by ID."""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str):
        """Delete a session."""
        self.sessions.pop(session_id, None)
    
    def create_token(self, user_id: str) -> str:
        """Create authentication token."""
        token = secrets.token_urlsafe(32)
        self.tokens[token] = user_id
        return token
    
    def validate_token(self, token: str) -> Optional[str]:
        """Validate token and return user_id."""
        return self.tokens.get(token)
    
    def revoke_token(self, token: str):
        """Revoke a token."""
        self.tokens.pop(token, None)


class RateLimiter:
    """Rate limiting implementation."""
    
    def __init__(self):
        self.requests: Dict[str, List[float]] = defaultdict(list)
    
    def check_rate_limit(self, identifier: str, limit: int, 
                        window_seconds: int) -> Tuple[bool, Optional[int]]:
        """Check if rate limit is exceeded.
        
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        now = time.time()
        window_start = now - window_seconds
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > window_start
        ]
        
        # Check limit
        if len(self.requests[identifier]) >= limit:
            oldest_request = min(self.requests[identifier])
            retry_after = int(oldest_request + window_seconds - now) + 1
            return False, retry_after
        
        # Record request
        self.requests[identifier].append(now)
        return True, None


class InputValidator:
    """Input validation utilities."""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
    
    @staticmethod
    def validate_command(command: str) -> Dict[str, Any]:
        """Validate command input."""
        result = {"valid": True, "errors": []}
        
        # Check length
        if len(command) > 1000:
            result["valid"] = False
            result["errors"].append("Command too long (max 1000 characters)")
        
        # Check for dangerous patterns
        dangerous_patterns = [
            r"rm\s+-rf\s+/",
            r"format\s+[cC]:",
            r"del\s+/[fF]\s+/[sS]\s+/[qQ]",
            r"shutdown|poweroff|reboot",
            r":(){ :|:& };:",  # Fork bomb
            r"dd\s+if=/dev/zero",
            r"mkfs\.",
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command):
                result["valid"] = False
                result["errors"].append(f"Dangerous command pattern detected: {pattern}")
        
        return result
    
    @staticmethod
    def validate_path(path: str) -> Dict[str, Any]:
        """Validate file path."""
        result = {"valid": True, "errors": []}
        
        # Check length
        if len(path) > 260:  # Windows MAX_PATH
            result["valid"] = False
            result["errors"].append("Path too long (max 260 characters)")
        
        # Check for path traversal
        normalized_path = Path(path).resolve()
        if ".." in str(path):
            result["valid"] = False
            result["errors"].append("Path traversal detected")
        
        # Check for null bytes
        if "\x00" in path:
            result["valid"] = False
            result["errors"].append("Null byte in path")
        
        return result
    
    @staticmethod
    def validate_process_name(name: str) -> Dict[str, Any]:
        """Validate process name."""
        result = {"valid": True, "errors": []}
        
        # Check length
        if len(name) > 255:
            result["valid"] = False
            result["errors"].append("Process name too long (max 255 characters)")
        
        # Check allowed characters
        if not re.match(r"^[a-zA-Z0-9\-_.]+$", name):
            result["valid"] = False
            result["errors"].append("Invalid characters in process name")
        
        return result
    
    @staticmethod
    def sanitize_input(input_data: str) -> str:
        """Sanitize input data."""
        # Remove null bytes
        sanitized = input_data.replace("\x00", "")
        
        # Remove control characters (except newline, tab)
        sanitized = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", sanitized)
        
        # Trim whitespace
        sanitized = sanitized.strip()
        
        return sanitized


class SecurityManager:
    """Main security manager."""
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or get_config().config.security
        self.session_manager = SessionManager()
        self.audit_logger = AuditLogger()
        self.rate_limiter = RateLimiter()
        self.validator = InputValidator(self.config)
        self._jwt_secret = secrets.token_urlsafe(32)
    
    async def authenticate(self, credentials: Dict[str, Any]) -> AuthResult:
        """Authenticate user."""
        auth_type = self.config.authentication.type
        
        if not self.config.enabled:
            # Security disabled, allow anonymous access
            user = User("anonymous", roles=["guest"])
            return AuthResult(success=True, user=user)
        
        if auth_type == "none":
            # No authentication required
            user = User("default", roles=["user"])
            return AuthResult(success=True, user=user)
        
        elif auth_type == "basic":
            return await self._authenticate_basic(credentials)
        
        elif auth_type == "token":
            return await self._authenticate_token(credentials)
        
        else:
            raise AuthenticationException(f"Unknown authentication type: {auth_type}")
    
    async def _authenticate_basic(self, credentials: Dict[str, Any]) -> AuthResult:
        """Basic authentication."""
        username = credentials.get("username")
        password = credentials.get("password")
        
        if not username or not password:
            return AuthResult(success=False, error="Username and password required")
        
        # In a real implementation, check against database
        # For now, use hardcoded credentials
        if username == "admin" and password == "admin123":
            user = User(username, roles=["admin"])
            return AuthResult(success=True, user=user)
        
        return AuthResult(success=False, error="Invalid credentials")
    
    async def _authenticate_token(self, credentials: Dict[str, Any]) -> AuthResult:
        """Token-based authentication."""
        token = credentials.get("token")
        
        if not token:
            return AuthResult(success=False, error="Token required")
        
        try:
            # Decode JWT token
            payload = jwt.decode(token, self._jwt_secret, algorithms=["HS256"])
            user_id = payload.get("user_id")
            roles = payload.get("roles", [])
            
            user = User(user_id, roles=roles)
            return AuthResult(success=True, user=user)
        
        except jwt.ExpiredSignatureError:
            return AuthResult(success=False, error="Token expired")
        except jwt.InvalidTokenError:
            return AuthResult(success=False, error="Invalid token")
    
    def create_token(self, user: User) -> str:
        """Create JWT token for user."""
        payload = {
            "user_id": user.user_id,
            "roles": user.roles,
            "exp": datetime.now(timezone.utc) + timedelta(seconds=self.config.authentication.token_expiry),
            "iat": datetime.now(timezone.utc)
        }
        
        return jwt.encode(payload, self._jwt_secret, algorithm="HS256")
    
    async def authorize(self, user: User, operation: Operation) -> bool:
        """Check if user is authorized for operation."""
        if not self.config.enabled:
            return True
        
        # Check if user has admin role
        if "admin" in user.roles:
            return True
        
        # Check authorization rules
        for rule in self.config.authorization.__dict__.get("rules", []):
            if (rule.get("resource") == operation.resource and 
                operation.action in rule.get("actions", [])):
                
                # Check conditions
                if "conditions" in rule:
                    if not self._check_conditions(rule["conditions"], operation):
                        continue
                
                return rule.get("allow", False)
        
        # Default deny
        return False
    
    def _check_conditions(self, conditions: List[Dict], operation: Operation) -> bool:
        """Check authorization conditions."""
        for condition in conditions:
            cond_type = condition.get("type")
            cond_value = condition.get("value")
            
            if cond_type == "process_whitelist":
                process_name = operation.details.get("process_name")
                if process_name not in cond_value:
                    return False
            
            elif cond_type == "path_whitelist":
                path = operation.details.get("path")
                if not any(path.startswith(allowed) for allowed in cond_value):
                    return False
            
            elif cond_type == "safe_mode":
                if operation.details.get("safe_mode") != cond_value:
                    return False
        
        return True
    
    async def audit_operation(self, user: User, operation: Operation, 
                            result: Any, success: bool = True):
        """Audit an operation."""
        if not self.config.audit.enabled:
            return
        
        self.audit_logger.log_operation(
            user_id=user.user_id,
            action=operation.action,
            resource=operation.resource,
            result="success" if success else "failure",
            details={
                **operation.details,
                "result": str(result)[:1000]  # Limit result size
            }
        )
    
    def check_rate_limit(self, identifier: str, resource: str) -> None:
        """Check rate limit for resource."""
        # Default rate limit
        limit = 100
        window = 60
        
        # Check specific rate limits from config
        # (In real implementation, load from config)
        
        allowed, retry_after = self.rate_limiter.check_rate_limit(
            f"{identifier}:{resource}", limit, window
        )
        
        if not allowed:
            raise RateLimitException(
                f"Rate limit exceeded for {resource}",
                retry_after=retry_after
            )
    
    def validate_input(self, input_type: str, value: str) -> str:
        """Validate and sanitize input."""
        # Sanitize first
        sanitized = self.validator.sanitize_input(value)
        
        # Validate based on type
        if input_type == "command":
            result = self.validator.validate_command(sanitized)
        elif input_type == "path":
            result = self.validator.validate_path(sanitized)
        elif input_type == "process_name":
            result = self.validator.validate_process_name(sanitized)
        else:
            result = {"valid": True, "errors": []}
        
        if not result["valid"]:
            raise ValidationException(
                f"Input validation failed: {', '.join(result['errors'])}"
            )
        
        return sanitized
    
    def check_path_access(self, path: str, operation: str = "read") -> bool:
        """Check if path access is allowed."""
        path = Path(path).resolve()
        str_path = str(path)
        
        # Check blocked paths
        blocked_paths = self.config.authorization.blocked_paths
        for blocked in blocked_paths:
            if str_path.startswith(blocked):
                log.warning(f"Access denied to blocked path: {path}")
                return False
        
        # Check allowed paths (if configured)
        allowed_paths = self.config.authorization.__dict__.get("allowed_paths", [])
        if allowed_paths:
            allowed = any(str_path.startswith(allowed) for allowed in allowed_paths)
            if not allowed:
                log.warning(f"Access denied to non-allowed path: {path}")
                return False
        
        return True
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))