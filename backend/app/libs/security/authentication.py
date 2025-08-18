"""
Authentication and authorization system for ensimu-space.
Implements JWT-based authentication, role-based access control, and security best practices.
"""

import asyncio
import hashlib
import hmac
import logging
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

try:
    import jwt
    from passlib.context import CryptContext
    from passlib.hash import bcrypt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """User roles for access control"""
    ADMIN = "admin"
    ENGINEER = "engineer"
    ANALYST = "analyst"
    VIEWER = "viewer"
    API_USER = "api_user"

class Permission(Enum):
    """System permissions"""
    # Project permissions
    CREATE_PROJECT = "create_project"
    READ_PROJECT = "read_project"
    UPDATE_PROJECT = "update_project"
    DELETE_PROJECT = "delete_project"
    
    # Workflow permissions
    START_WORKFLOW = "start_workflow"
    STOP_WORKFLOW = "stop_workflow"
    VIEW_WORKFLOW = "view_workflow"
    MANAGE_WORKFLOW = "manage_workflow"
    
    # File permissions
    UPLOAD_FILE = "upload_file"
    DOWNLOAD_FILE = "download_file"
    DELETE_FILE = "delete_file"
    
    # Admin permissions
    MANAGE_USERS = "manage_users"
    VIEW_SYSTEM_METRICS = "view_system_metrics"
    MANAGE_SYSTEM = "manage_system"
    
    # API permissions
    API_ACCESS = "api_access"
    BULK_OPERATIONS = "bulk_operations"

@dataclass
class User:
    """User model for authentication"""
    user_id: str
    username: str
    email: str
    password_hash: str
    role: UserRole
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = None
    last_login: datetime = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    api_key: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

class SecurityConfig:
    """Security configuration"""
    
    # JWT settings
    JWT_SECRET_KEY = "your-secret-key-here"  # Should be from environment
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7
    
    # Password settings
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGITS = True
    PASSWORD_REQUIRE_SPECIAL = True
    
    # Account lockout settings
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15
    
    # Rate limiting
    RATE_LIMIT_REQUESTS = 100
    RATE_LIMIT_WINDOW_MINUTES = 15
    
    # API key settings
    API_KEY_LENGTH = 32
    API_KEY_PREFIX = "ensimu_"

class PasswordValidator:
    """Password validation utility"""
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """Validate password strength"""
        errors = []
        
        if len(password) < SecurityConfig.PASSWORD_MIN_LENGTH:
            errors.append(f"Password must be at least {SecurityConfig.PASSWORD_MIN_LENGTH} characters")
        
        if SecurityConfig.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if SecurityConfig.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if SecurityConfig.PASSWORD_REQUIRE_DIGITS and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if SecurityConfig.PASSWORD_REQUIRE_SPECIAL and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        # Check for common passwords
        common_passwords = ["password", "123456", "admin", "user", "test"]
        if password.lower() in common_passwords:
            errors.append("Password is too common")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "strength": "strong" if len(errors) == 0 else "weak"
        }

class AuthenticationManager:
    """Authentication and authorization manager"""
    
    def __init__(self):
        if not JWT_AVAILABLE:
            raise ImportError("JWT and passlib libraries required for authentication")
        
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.users: Dict[str, User] = {}  # In production, use database
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.rate_limits: Dict[str, List[datetime]] = {}
        
        # Role permissions mapping
        self.role_permissions = {
            UserRole.ADMIN: list(Permission),  # All permissions
            UserRole.ENGINEER: [
                Permission.CREATE_PROJECT, Permission.READ_PROJECT, Permission.UPDATE_PROJECT,
                Permission.START_WORKFLOW, Permission.STOP_WORKFLOW, Permission.VIEW_WORKFLOW,
                Permission.UPLOAD_FILE, Permission.DOWNLOAD_FILE, Permission.API_ACCESS
            ],
            UserRole.ANALYST: [
                Permission.READ_PROJECT, Permission.VIEW_WORKFLOW,
                Permission.DOWNLOAD_FILE, Permission.VIEW_SYSTEM_METRICS
            ],
            UserRole.VIEWER: [
                Permission.READ_PROJECT, Permission.VIEW_WORKFLOW, Permission.DOWNLOAD_FILE
            ],
            UserRole.API_USER: [
                Permission.API_ACCESS, Permission.READ_PROJECT, Permission.START_WORKFLOW
            ]
        }
    
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def generate_api_key(self) -> str:
        """Generate a secure API key"""
        random_part = secrets.token_urlsafe(SecurityConfig.API_KEY_LENGTH)
        return f"{SecurityConfig.API_KEY_PREFIX}{random_part}"
    
    def create_user(self, username: str, email: str, password: str, role: UserRole) -> Dict[str, Any]:
        """Create a new user"""
        # Validate password
        password_validation = PasswordValidator.validate_password(password)
        if not password_validation["valid"]:
            return {
                "success": False,
                "errors": password_validation["errors"]
            }
        
        # Check if user exists
        if any(u.username == username or u.email == email for u in self.users.values()):
            return {
                "success": False,
                "errors": ["Username or email already exists"]
            }
        
        # Create user
        user_id = secrets.token_urlsafe(16)
        password_hash = self.hash_password(password)
        api_key = self.generate_api_key() if role == UserRole.API_USER else None
        
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            api_key=api_key
        )
        
        self.users[user_id] = user
        
        logger.info(f"Created user {username} with role {role.value}")
        
        return {
            "success": True,
            "user_id": user_id,
            "api_key": api_key
        }
    
    def authenticate_user(self, username: str, password: str, ip_address: str = None) -> Dict[str, Any]:
        """Authenticate a user with username/password"""
        # Check rate limiting
        if ip_address and not self._check_rate_limit(ip_address):
            return {
                "success": False,
                "error": "Rate limit exceeded"
            }
        
        # Find user
        user = None
        for u in self.users.values():
            if u.username == username or u.email == username:
                user = u
                break
        
        if not user:
            return {
                "success": False,
                "error": "Invalid credentials"
            }
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            return {
                "success": False,
                "error": "Account is locked"
            }
        
        # Verify password
        if not self.verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            
            # Lock account if too many failed attempts
            if user.failed_login_attempts >= SecurityConfig.MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(minutes=SecurityConfig.LOCKOUT_DURATION_MINUTES)
                logger.warning(f"Account {username} locked due to failed login attempts")
            
            return {
                "success": False,
                "error": "Invalid credentials"
            }
        
        # Check if user is active
        if not user.is_active:
            return {
                "success": False,
                "error": "Account is disabled"
            }
        
        # Reset failed attempts and update last login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        
        # Generate tokens
        access_token = self._create_access_token(user)
        refresh_token = self._create_refresh_token(user)
        
        # Store session
        session_id = secrets.token_urlsafe(32)
        self.active_sessions[session_id] = {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role.value,
            "created_at": datetime.utcnow(),
            "ip_address": ip_address
        }
        
        logger.info(f"User {username} authenticated successfully")
        
        return {
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "session_id": session_id,
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value
            }
        }
    
    def authenticate_api_key(self, api_key: str) -> Dict[str, Any]:
        """Authenticate using API key"""
        user = None
        for u in self.users.values():
            if u.api_key == api_key:
                user = u
                break
        
        if not user or not user.is_active:
            return {
                "success": False,
                "error": "Invalid API key"
            }
        
        return {
            "success": True,
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "role": user.role.value
            }
        }
    
    def _create_access_token(self, user: User) -> str:
        """Create JWT access token"""
        payload = {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role.value,
            "exp": datetime.utcnow() + timedelta(minutes=SecurityConfig.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        return jwt.encode(payload, SecurityConfig.JWT_SECRET_KEY, algorithm=SecurityConfig.JWT_ALGORITHM)
    
    def _create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token"""
        payload = {
            "user_id": user.user_id,
            "exp": datetime.utcnow() + timedelta(days=SecurityConfig.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        return jwt.encode(payload, SecurityConfig.JWT_SECRET_KEY, algorithm=SecurityConfig.JWT_ALGORITHM)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, SecurityConfig.JWT_SECRET_KEY, algorithms=[SecurityConfig.JWT_ALGORITHM])
            
            # Check token type
            if payload.get("type") != "access":
                return {
                    "valid": False,
                    "error": "Invalid token type"
                }
            
            # Get user
            user_id = payload.get("user_id")
            if user_id not in self.users:
                return {
                    "valid": False,
                    "error": "User not found"
                }
            
            user = self.users[user_id]
            if not user.is_active:
                return {
                    "valid": False,
                    "error": "User account disabled"
                }
            
            return {
                "valid": True,
                "user_id": user_id,
                "username": payload.get("username"),
                "role": payload.get("role"),
                "payload": payload
            }
            
        except jwt.ExpiredSignatureError:
            return {
                "valid": False,
                "error": "Token expired"
            }
        except jwt.InvalidTokenError:
            return {
                "valid": False,
                "error": "Invalid token"
            }
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        try:
            payload = jwt.decode(refresh_token, SecurityConfig.JWT_SECRET_KEY, algorithms=[SecurityConfig.JWT_ALGORITHM])
            
            if payload.get("type") != "refresh":
                return {
                    "success": False,
                    "error": "Invalid token type"
                }
            
            user_id = payload.get("user_id")
            if user_id not in self.users:
                return {
                    "success": False,
                    "error": "User not found"
                }
            
            user = self.users[user_id]
            if not user.is_active:
                return {
                    "success": False,
                    "error": "User account disabled"
                }
            
            # Create new access token
            new_access_token = self._create_access_token(user)
            
            return {
                "success": True,
                "access_token": new_access_token
            }
            
        except jwt.ExpiredSignatureError:
            return {
                "success": False,
                "error": "Refresh token expired"
            }
        except jwt.InvalidTokenError:
            return {
                "success": False,
                "error": "Invalid refresh token"
            }
    
    def check_permission(self, user_role: UserRole, permission: Permission) -> bool:
        """Check if user role has specific permission"""
        return permission in self.role_permissions.get(user_role, [])
    
    def _check_rate_limit(self, identifier: str) -> bool:
        """Check rate limiting for IP address or user"""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=SecurityConfig.RATE_LIMIT_WINDOW_MINUTES)
        
        if identifier not in self.rate_limits:
            self.rate_limits[identifier] = []
        
        # Remove old requests
        self.rate_limits[identifier] = [
            req_time for req_time in self.rate_limits[identifier]
            if req_time > window_start
        ]
        
        # Check if under limit
        if len(self.rate_limits[identifier]) >= SecurityConfig.RATE_LIMIT_REQUESTS:
            return False
        
        # Add current request
        self.rate_limits[identifier].append(now)
        return True
    
    def logout_user(self, session_id: str):
        """Logout user and invalidate session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"User session {session_id} logged out")
    
    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get active sessions for a user"""
        return [
            {
                "session_id": session_id,
                "created_at": session["created_at"].isoformat(),
                "ip_address": session.get("ip_address")
            }
            for session_id, session in self.active_sessions.items()
            if session["user_id"] == user_id
        ]

# Global authentication manager
auth_manager = AuthenticationManager()

# Convenience functions
def create_user(username: str, email: str, password: str, role: UserRole):
    """Create a new user"""
    return auth_manager.create_user(username, email, password, role)

def authenticate_user(username: str, password: str, ip_address: str = None):
    """Authenticate user with credentials"""
    return auth_manager.authenticate_user(username, password, ip_address)

def authenticate_api_key(api_key: str):
    """Authenticate using API key"""
    return auth_manager.authenticate_api_key(api_key)

def verify_token(token: str):
    """Verify JWT token"""
    return auth_manager.verify_token(token)

def check_permission(user_role: UserRole, permission: Permission):
    """Check user permission"""
    return auth_manager.check_permission(user_role, permission)
