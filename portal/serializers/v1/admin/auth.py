"""
Admin authentication serializers
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class AdminLoginRequest(BaseModel):
    """Admin login request"""
    email: EmailStr = Field(..., description="Admin email")
    password: str = Field(..., description="Admin password")


class AdminTokenResponse(BaseModel):
    """Admin token response"""
    access_token: str = Field(..., description="Access token")
    refresh_token: str = Field(..., description="Refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration (seconds)")


class AdminInfo(BaseModel):
    """Admin info"""
    id: UUID = Field(..., description="Admin ID")
    email: str = Field(..., description="Admin email")
    display_name: str = Field(..., description="Display name")
    roles: List[str] = Field(default=[], description="Admin roles")
    permissions: List[str] = Field(default=[], description="Admin permissions")
    last_login_at: Optional[datetime] = Field(None, description="Last login time")


class AdminLoginResponse(BaseModel):
    """Admin login response"""
    admin: AdminInfo = Field(..., description="Admin info")
    tokens: AdminTokenResponse = Field(..., description="Auth tokens")


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str = Field(..., description="Refresh token")


class ChangePasswordRequest(BaseModel):
    """Change password request"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=6, description="New password")


class ForgotPasswordRequest(BaseModel):
    """Forgot password request"""
    email: EmailStr = Field(..., description="User email")


class ResetPasswordRequest(BaseModel):
    """Reset password request"""
    token: str = Field(..., description="Reset password token")
    new_password: str = Field(..., min_length=6, description="New password")


class LogoutRequest(BaseModel):
    """Logout request"""
    access_token: str = Field(..., description="Access token to blacklist")
    refresh_token: Optional[str] = Field(None, description="Refresh token to blacklist")


class LogoutResponse(BaseModel):
    """Logout response"""
    message: str = Field(..., description="Logout message")
