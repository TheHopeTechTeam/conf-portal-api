"""
User Auth API Router
"""
from dependency_injector.wiring import inject, Provide
from fastapi import Depends
from starlette import status

from portal.config import settings
from portal.container import Container
from portal.exceptions.responses import ApiBaseException
from portal.handlers import UserAuthHandler
from portal.libs.depends import DEFAULT_RATE_LIMITERS
from portal.routers.auth_router import AuthRouter
from portal.serializers.mixins import LogoutResponse, TokenResponse, RefreshTokenRequest, LogoutRequest
from portal.serializers.v1.user import (
    UserLogin,
    UserLoginResponse,
    UserLocalLogin,
    SendSignInLinkRequest,
    SendSignInLinkResponse,
)

router: AuthRouter = AuthRouter(
    dependencies=[
        *DEFAULT_RATE_LIMITERS
    ]
)


@router.post(
    path="/send-signin-link",
    response_model=SendSignInLinkResponse,
    status_code=status.HTTP_202_ACCEPTED,
    require_auth=False,
    operation_id="user_auth_send_sign_in_link",
)
@inject
async def send_signin_link(
    model: SendSignInLinkRequest,
    user_auth_handler: UserAuthHandler = Depends(Provide[Container.user_auth_handler])
) -> SendSignInLinkResponse:
    """
    Request a login verification email. A sign-in link will be sent to the given email if the service is configured.
    Response is always the same to avoid leaking whether the email exists.
    """
    await user_auth_handler.send_signin_link(email=model.email)
    return SendSignInLinkResponse()


if settings.is_dev:
    @router.post(
        path="/local/login",
        status_code=status.HTTP_200_OK,
        include_in_schema=False,
        require_auth=False
    )
    @inject
    async def user_local_login(
        model: UserLocalLogin,
        user_auth_handler: UserAuthHandler = Depends(Provide[Container.user_auth_handler])
    ) -> UserLoginResponse:
        """

        :param model:
        :param user_auth_handler:
        :return:
        """
        return await user_auth_handler.local_login(model=model)


@router.post(
    path="/login",
    response_model=UserLoginResponse,
    status_code=status.HTTP_200_OK,
    require_auth=False,
    operation_id="user_auth_login",
)
@inject
async def user_login(
    model: UserLogin,
    user_auth_handler: UserAuthHandler = Depends(Provide[Container.user_auth_handler])
) -> UserLoginResponse:
    """
    User login
    :param model:
    :param user_auth_handler:
    :return:
    """
    return await user_auth_handler.login(model=model)


@router.post(
    path="/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    require_auth=False,
    operation_id="user_auth_refresh_token",
)
@inject
async def user_refresh_token(
    refresh_data: RefreshTokenRequest,
    user_auth_handler: UserAuthHandler = Depends(Provide[Container.user_auth_handler])
):
    """
    User refresh token
    :param refresh_data:
    :param user_auth_handler:
    :return:
    """
    return await user_auth_handler.refresh_token(refresh_data)


@router.post(
    path="/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    require_auth=False,
    operation_id="user_auth_logout",
)
@inject
async def user_logout(
    logout_data: LogoutRequest,
    user_auth_handler: UserAuthHandler = Depends(Provide[Container.user_auth_handler])
):
    """
    User logout
    :param logout_data:
    :param user_auth_handler:
    :return:
    """
    success = await user_auth_handler.logout(
        logout_data.access_token,
        logout_data.refresh_token
    )

    if not success:
        raise ApiBaseException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout"
        )

    return LogoutResponse(message="Successfully logged out")
