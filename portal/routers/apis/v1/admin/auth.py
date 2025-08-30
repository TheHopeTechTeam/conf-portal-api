"""
Admin authentication API routes
"""
from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends, HTTPException, status

from portal.container import Container
from portal.handlers import AdminAuthHandler
from portal.serializers.v1.admin.auth import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminTokenResponse,
    AdminInfo,
    LogoutRequest,
    LogoutResponse,
)

router = APIRouter()


@router.post("/login", response_model=AdminLoginResponse)
@inject
async def admin_login(
    login_data: AdminLoginRequest,
    admin_auth_handler: AdminAuthHandler = Depends(Provide[Container.admin_auth_handler])
):
    """
    Admin login
    """
    return await admin_auth_handler.login(login_data)


@router.post("/refresh", response_model=AdminTokenResponse)
@inject
async def admin_refresh_token(
    refresh_data: dict,
    admin_auth_handler: AdminAuthHandler = Depends(Provide[Container.admin_auth_handler])
):
    """
    Refresh admin access token
    """
    return await admin_auth_handler.refresh_token(refresh_data["refresh_token"])


@router.get("/me", response_model=AdminInfo)
@inject
async def get_current_admin_info(
    admin_auth_handler: AdminAuthHandler = Depends(Provide[Container.admin_auth_handler])
):
    """
    Get current admin information
    """


@router.post(
    "/logout",
    response_model=LogoutResponse
)
@inject
async def admin_logout(
    logout_data: LogoutRequest,
    admin_auth_handler: AdminAuthHandler = Depends(Provide[Container.admin_auth_handler])
):
    """
    Admin logout
    """
    success = await admin_auth_handler.logout(
        logout_data.access_token,
        logout_data.refresh_token
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout"
        )

    return LogoutResponse(message="Successfully logged out")
