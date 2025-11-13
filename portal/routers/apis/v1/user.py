"""
Account API Router
"""
import uuid

from dependency_injector.wiring import inject, Provide
from fastapi import Request, Response, Depends
from starlette import status

from portal.container import Container
from portal.handlers import UserHandler
from portal.libs.depends import DEFAULT_RATE_LIMITERS
from portal.routers.auth_router import AuthRouter
from portal.serializers.v1.user import UserDetail, UserUpdate

router: AuthRouter = AuthRouter(
    dependencies=[
        *DEFAULT_RATE_LIMITERS
    ]
)


@router.get(
    path="/{user_id}",
    response_model=UserDetail,
    status_code=status.HTTP_200_OK,
    description="For getting an account personal information"
)
@inject
async def get_account(
    request: Request,
    response: Response,
    user_id: uuid.UUID,
    user_handler: UserHandler = Depends(Provide[Container.user_handler]),
) -> UserDetail:
    """
    Get an account
    """
    return await user_handler.get_user(user_id=user_id)


@router.put(
    path="/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="For updating an account personal information"
)
@inject
async def update_account(
    request: Request,
    response: Response,
    user_id: uuid.UUID,
    model: UserUpdate,
    user_handler: UserHandler = Depends(Provide[Container.user_handler]),
) -> None:
    """
    Update an account
    """
    await user_handler.update_user(user_id=user_id, model=model)


@router.delete(
    path="/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="For deleting an account"
)
@inject
async def delete_account(
    request: Request,
    response: Response,
    user_id: uuid.UUID,
    user_handler: UserHandler = Depends(Provide[Container.user_handler]),
) -> None:
    """
    Delete an account
    """
    await user_handler.delete_user(user_id=user_id)
