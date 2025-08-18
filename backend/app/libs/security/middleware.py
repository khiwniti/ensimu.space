"""
Security middleware for FastAPI application.
Implements authentication, authorization, rate limiting, and security headers.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import ipaddress

try:
    from fastapi import Request, Response, HTTPException, status
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from starlette.middleware.base import BaseHTTPMiddleware
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from .authentication import auth_manager, UserRole, Permission
from .rate_limiting import rate_limiter, RateLimitScope

logger = logging.getLogger(__name__)

class SecurityConfig:
    """Security configuration"""
    
    # CORS settings
    ALLOWED_ORIGINS = ["http://localhost:3000", "https://yourdomain.com"]
    ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    ALLOWED_HEADERS = ["*"]
    ALLOW_CREDENTIALS = True
    
    # Security headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
    }
    
    # IP whitelist/blacklist
    IP_WHITELIST: List[str] = []  # Empty means allow all
    IP_BLACKLIST: List[str] = []
    
    # Request size limits
    MAX_REQUEST_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_UPLOAD_SIZE = 50 * 1024 * 1024   # 50MB

class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware"""
    
    def __init__(self, app, config: SecurityConfig = None):
        super().__init__(app)
        self.config = config or SecurityConfig()
        self.security_bearer = HTTPBearer(auto_error=False)
        
        # Compile IP networks for faster checking
        self.ip_whitelist_networks = []
        self.ip_blacklist_networks = []
        
        for ip in self.config.IP_WHITELIST:
            try:
                self.ip_whitelist_networks.append(ipaddress.ip_network(ip, strict=False))
            except ValueError:
                logger.warning(f"Invalid IP whitelist entry: {ip}")
        
        for ip in self.config.IP_BLACKLIST:
            try:
                self.ip_blacklist_networks.append(ipaddress.ip_network(ip, strict=False))
            except ValueError:
                logger.warning(f"Invalid IP blacklist entry: {ip}")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Main middleware dispatch"""
        start_time = time.time()
        
        try:
            # 1. IP filtering
            if not await self._check_ip_access(request):
                return Response(
                    content="Access denied",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # 2. Request size validation
            if not await self._check_request_size(request):
                return Response(
                    content="Request too large",
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                )
            
            # 3. Rate limiting
            rate_limit_result = await self._check_rate_limits(request)
            if not rate_limit_result.allowed:
                response = Response(
                    content="Rate limit exceeded",
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS
                )
                # Add rate limit headers
                for header, value in rate_limit_result.to_headers().items():
                    response.headers[header] = value
                return response
            
            # 4. Authentication (for protected routes)
            auth_result = await self._authenticate_request(request)
            if auth_result.get("error") and self._is_protected_route(request):
                return Response(
                    content=auth_result["error"],
                    status_code=status.HTTP_401_UNAUTHORIZED
                )
            
            # 5. Authorization (for protected routes)
            if auth_result.get("user") and self._is_protected_route(request):
                if not await self._authorize_request(request, auth_result["user"]):
                    return Response(
                        content="Insufficient permissions",
                        status_code=status.HTTP_403_FORBIDDEN
                    )
            
            # Add user info to request state
            if auth_result.get("user"):
                request.state.user = auth_result["user"]
                request.state.authenticated = True
            else:
                request.state.authenticated = False
            
            # Process request
            response = await call_next(request)
            
            # 6. Add security headers
            self._add_security_headers(response)
            
            # 7. Add rate limit headers
            for header, value in rate_limit_result.to_headers().items():
                response.headers[header] = value
            
            # Log request
            duration = time.time() - start_time
            self._log_request(request, response, duration, auth_result.get("user"))
            
            return response
            
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            return Response(
                content="Internal server error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    async def _check_ip_access(self, request: Request) -> bool:
        """Check IP whitelist/blacklist"""
        client_ip = self._get_client_ip(request)
        
        if not client_ip:
            return True  # Allow if IP cannot be determined
        
        try:
            ip_addr = ipaddress.ip_address(client_ip)
            
            # Check blacklist first
            for network in self.ip_blacklist_networks:
                if ip_addr in network:
                    logger.warning(f"Blocked IP {client_ip} (blacklisted)")
                    return False
            
            # Check whitelist (if configured)
            if self.ip_whitelist_networks:
                for network in self.ip_whitelist_networks:
                    if ip_addr in network:
                        return True
                logger.warning(f"Blocked IP {client_ip} (not whitelisted)")
                return False
            
            return True
            
        except ValueError:
            logger.warning(f"Invalid IP address: {client_ip}")
            return True  # Allow if IP is invalid
    
    async def _check_request_size(self, request: Request) -> bool:
        """Check request size limits"""
        content_length = request.headers.get("content-length")
        
        if content_length:
            try:
                size = int(content_length)
                if size > self.config.MAX_REQUEST_SIZE:
                    logger.warning(f"Request too large: {size} bytes")
                    return False
            except ValueError:
                pass
        
        return True
    
    async def _check_rate_limits(self, request: Request):
        """Check rate limits for the request"""
        client_ip = self._get_client_ip(request)
        path = request.url.path
        
        # Determine rate limit rule based on endpoint
        rule_name = "api_general"
        identifier = client_ip
        
        if path.startswith("/api/auth/"):
            rule_name = "api_auth"
        elif path.startswith("/api/workflows/") and request.method == "POST":
            rule_name = "workflow_start"
            # Use user ID if authenticated
            if hasattr(request.state, "user") and request.state.user:
                identifier = request.state.user.get("user_id", client_ip)
        elif path.startswith("/api/files/upload"):
            rule_name = "file_upload"
            if hasattr(request.state, "user") and request.state.user:
                identifier = request.state.user.get("user_id", client_ip)
        
        return await rate_limiter.check_rate_limit(rule_name, identifier)
    
    async def _authenticate_request(self, request: Request) -> Dict[str, Any]:
        """Authenticate the request"""
        # Check for API key in headers
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return auth_manager.authenticate_api_key(api_key)
        
        # Check for JWT token
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
            token_result = auth_manager.verify_token(token)
            
            if token_result["valid"]:
                return {
                    "success": True,
                    "user": {
                        "user_id": token_result["user_id"],
                        "username": token_result["username"],
                        "role": token_result["role"]
                    }
                }
            else:
                return {
                    "success": False,
                    "error": token_result["error"]
                }
        
        # No authentication provided
        return {"success": False, "error": "No authentication provided"}
    
    async def _authorize_request(self, request: Request, user: Dict[str, Any]) -> bool:
        """Authorize the request based on user permissions"""
        path = request.url.path
        method = request.method
        user_role = UserRole(user.get("role", "viewer"))
        
        # Define endpoint permissions
        endpoint_permissions = {
            ("POST", "/api/projects/"): Permission.CREATE_PROJECT,
            ("GET", "/api/projects/"): Permission.READ_PROJECT,
            ("PUT", "/api/projects/"): Permission.UPDATE_PROJECT,
            ("DELETE", "/api/projects/"): Permission.DELETE_PROJECT,
            ("POST", "/api/workflows/"): Permission.START_WORKFLOW,
            ("DELETE", "/api/workflows/"): Permission.STOP_WORKFLOW,
            ("GET", "/api/workflows/"): Permission.VIEW_WORKFLOW,
            ("POST", "/api/files/upload"): Permission.UPLOAD_FILE,
            ("GET", "/api/files/"): Permission.DOWNLOAD_FILE,
            ("DELETE", "/api/files/"): Permission.DELETE_FILE,
            ("GET", "/api/admin/"): Permission.MANAGE_SYSTEM,
            ("GET", "/api/metrics/"): Permission.VIEW_SYSTEM_METRICS,
        }
        
        # Check specific endpoint permissions
        for (endpoint_method, endpoint_path), required_permission in endpoint_permissions.items():
            if method == endpoint_method and path.startswith(endpoint_path):
                return auth_manager.check_permission(user_role, required_permission)
        
        # Default: allow if no specific permission required
        return True
    
    def _is_protected_route(self, request: Request) -> bool:
        """Check if route requires authentication"""
        path = request.url.path
        
        # Public routes
        public_routes = [
            "/health",
            "/docs",
            "/openapi.json",
            "/api/auth/login",
            "/api/auth/register",
            "/static/",
        ]
        
        for public_route in public_routes:
            if path.startswith(public_route):
                return False
        
        # All API routes are protected by default
        return path.startswith("/api/")
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        for header, value in self.config.SECURITY_HEADERS.items():
            response.headers[header] = value
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Get client IP address from request"""
        # Check X-Forwarded-For header (for reverse proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return None
    
    def _log_request(self, request: Request, response: Response, duration: float, user: Dict[str, Any] = None):
        """Log request details"""
        client_ip = self._get_client_ip(request)
        user_info = f"user:{user.get('username', 'unknown')}" if user else "anonymous"
        
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Duration: {duration:.3f}s - "
            f"IP: {client_ip} - "
            f"User: {user_info}"
        )

class AuthenticationDependency:
    """FastAPI dependency for authentication"""
    
    def __init__(self, required: bool = True):
        self.required = required
    
    async def __call__(self, request: Request) -> Optional[Dict[str, Any]]:
        """Get authenticated user from request"""
        if hasattr(request.state, "user"):
            return request.state.user
        
        if self.required:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        return None

class PermissionDependency:
    """FastAPI dependency for permission checking"""
    
    def __init__(self, required_permission: Permission):
        self.required_permission = required_permission
    
    async def __call__(self, request: Request, user: Dict[str, Any] = None) -> bool:
        """Check if user has required permission"""
        if not user:
            user = getattr(request.state, "user", None)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user_role = UserRole(user.get("role", "viewer"))
        
        if not auth_manager.check_permission(user_role, self.required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return True

# Dependency instances
get_current_user = AuthenticationDependency(required=True)
get_current_user_optional = AuthenticationDependency(required=False)

# Permission dependencies
require_admin = PermissionDependency(Permission.MANAGE_SYSTEM)
require_project_create = PermissionDependency(Permission.CREATE_PROJECT)
require_workflow_start = PermissionDependency(Permission.START_WORKFLOW)
require_file_upload = PermissionDependency(Permission.UPLOAD_FILE)

def create_security_middleware(app, config: SecurityConfig = None):
    """Create and configure security middleware"""
    if not FASTAPI_AVAILABLE:
        logger.warning("FastAPI not available, security middleware disabled")
        return app
    
    middleware = SecurityMiddleware(app, config)
    return middleware
