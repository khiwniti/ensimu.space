"""
Hello API router for basic health and connectivity testing.
"""

from fastapi import APIRouter, Depends
from datetime import datetime
from typing import Dict, Any

from app.simple_auth import get_current_user_optional, AuthenticatedUser

router = APIRouter(prefix="/hello", tags=["hello"])

@router.get("/")
async def hello_world() -> Dict[str, Any]:
    """Simple hello world endpoint for basic connectivity testing"""
    return {
        "message": "Hello from EnsumuSpace CAE Preprocessing API!",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "operational",
        "version": "1.0.0"
    }

@router.get("/authenticated")
async def hello_authenticated(
    current_user: AuthenticatedUser = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """Hello endpoint that shows authentication status"""
    if current_user:
        return {
            "message": f"Hello {current_user.username or current_user.user_id}!",
            "authenticated": True,
            "user_id": current_user.user_id,
            "roles": current_user.roles,
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        return {
            "message": "Hello anonymous user!",
            "authenticated": False,
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for the hello service"""
    return {
        "service": "hello",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "api": "operational",
            "routes": "loaded"
        }
    }