"""Simple authentication system to replace databutton auth."""

from typing import Optional, List
from fastapi import HTTPException, Depends, Request


class AuthenticatedUser:
    """Simple user model."""
    def __init__(self, user_id: str, email: Optional[str] = None, username: Optional[str] = None, roles: Optional[List[str]] = None):
        self.user_id = user_id
        self.email = email
        self.username = username
        self.roles = roles or ["user"]


class AuthConfig:
    """Simple auth configuration."""
    def __init__(self, **kwargs):
        self.config = kwargs


async def get_authorized_user(request: Request) -> Optional[AuthenticatedUser]:
    """Simple auth dependency - for now, returns a default user."""
    # For development, return a default user
    # In production, implement proper authentication
    return AuthenticatedUser(
        user_id="default_user", 
        email="user@example.com",
        username="default_user",
        roles=["user", "admin"]
    )


async def get_current_user_optional(request: Request) -> Optional[AuthenticatedUser]:
    """Optional auth dependency."""
    try:
        return await get_authorized_user(request)
    except:
        return None


async def get_current_user(request: Request) -> AuthenticatedUser:
    """Required auth dependency."""
    user = await get_authorized_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user