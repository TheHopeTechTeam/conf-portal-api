"""
Admin authentication API routes
"""
import uuid

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.params import Cookie

from portal.container import Container
from portal.handlers import AdminAuthHandler
from portal.libs.depends import check_admin_access_token
from portal.serializers.v1.admin.auth import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminTokenResponse,
    AdminInfo,
    LogoutRequest,
    LogoutResponse,
    RefreshTokenRequest,
)

router = APIRouter()


@router.post(
    path="/login",
    response_model=AdminLoginResponse,
    status_code=status.HTTP_200_OK,
)
@inject
async def admin_login(
    response: Response,
    login_data: AdminLoginRequest,
    device_id: uuid.UUID = Cookie(None, alias="device_id"),
    admin_auth_handler: AdminAuthHandler = Depends(Provide[Container.admin_auth_handler])
):
    """
    Admin login
    """
    if not device_id:
        device_id = uuid.uuid4()
    try:
        result = await admin_auth_handler.login(
            login_data=login_data,
            device_id=device_id
        )
    except Exception as e:
        raise e
    else:
        response.set_cookie(
            key="device_id",
            value=str(device_id),
            max_age=3600 * 24 * 365,  # 1 year
            httponly=True,
            secure=True,
            samesite="lax",
            path="/",
        )
        return result


@router.post(
    path="/refresh",
    response_model=AdminTokenResponse,
    status_code=status.HTTP_200_OK,
)
@inject
async def admin_refresh_token(
    refresh_data: RefreshTokenRequest,
    admin_auth_handler: AdminAuthHandler = Depends(Provide[Container.admin_auth_handler])
):
    """
    Refresh admin access token
    :param refresh_data:
    :param admin_auth_handler:
    :return:
    """
    return await admin_auth_handler.refresh_token(refresh_data)


@router.get(
    path="/me",
    response_model=AdminInfo,
    status_code=status.HTTP_200_OK,
    dependencies=[check_admin_access_token]
)
@inject
async def get_current_admin_info(
    admin_auth_handler: AdminAuthHandler = Depends(Provide[Container.admin_auth_handler])
) -> AdminInfo:
    """
    Get current admin information
    """
    return await admin_auth_handler.get_me()


@router.post(
    path="/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
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
