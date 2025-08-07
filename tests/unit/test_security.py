"""
Unit tests for security module.
"""

import pytest
from src.core import SecurityManager, User, Operation, ValidationException
from src.core.config import SecurityConfig


class TestSecurityManager:
    """Test SecurityManager class."""
    
    @pytest.fixture
    def security_manager(self):
        """Create SecurityManager instance."""
        config = SecurityConfig()
        return SecurityManager(config)
    
    @pytest.fixture
    def test_user(self):
        """Create test user."""
        return User("test_user", roles=["user"])
    
    @pytest.fixture
    def admin_user(self):
        """Create admin user."""
        return User("admin", roles=["admin"])
    
    def test_validate_command_success(self, security_manager):
        """Test successful command validation."""
        command = "ls -la"
        result = security_manager.validate_input("command", command)
        assert result == command
    
    def test_validate_command_dangerous(self, security_manager):
        """Test dangerous command validation."""
        with pytest.raises(ValidationException):
            security_manager.validate_input("command", "rm -rf /")
    
    def test_validate_path_success(self, security_manager):
        """Test successful path validation."""
        path = "/home/user/test.txt"
        result = security_manager.validate_input("path", path)
        assert result == path
    
    def test_validate_path_traversal(self, security_manager):
        """Test path traversal validation."""
        with pytest.raises(ValidationException):
            security_manager.validate_input("path", "/home/../../../etc/passwd")
    
    def test_check_path_access_allowed(self, security_manager):
        """Test allowed path access."""
        result = security_manager.check_path_access("/home/user/documents", "read")
        assert result is True
    
    def test_check_path_access_blocked(self, security_manager):
        """Test blocked path access."""
        result = security_manager.check_path_access("/etc/passwd", "write")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_authenticate_no_security(self, security_manager):
        """Test authentication with security disabled."""
        security_manager.config.enabled = False
        result = await security_manager.authenticate({})
        assert result.success is True
        assert result.user.user_id == "anonymous"
    
    @pytest.mark.asyncio
    async def test_authorize_admin(self, security_manager, admin_user):
        """Test admin authorization."""
        operation = Operation("delete", "process", {"pid": 1234})
        result = await security_manager.authorize(admin_user, operation)
        assert result is True
    
    def test_hash_password(self, security_manager):
        """Test password hashing."""
        password = "test_password123"
        hashed = security_manager.hash_password(password)
        assert hashed != password
        assert security_manager.verify_password(password, hashed) is True
    
    def test_sanitize_input(self, security_manager):
        """Test input sanitization."""
        dirty_input = "test\x00data\x07with\x1fcontrol\x7fchars"
        clean = security_manager.validator.sanitize_input(dirty_input)
        assert "\x00" not in clean
        assert "\x07" not in clean
        assert "\x1f" not in clean
        assert "\x7f" not in clean