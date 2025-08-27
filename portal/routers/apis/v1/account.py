"""
Account API Router
"""
import uuid

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Request, Response, Depends
from starlette import status

from portal.container import Container
from portal.handlers import AccountHandler
from portal.libs.depends import (
    check_access_token,
)
from portal.route_classes import LogRoute
from portal.serializers.v1.account import AccountLogin, AccountDetail, AccountUpdate, LoginResponse

router = APIRouter(
    route_class=LogRoute
)


@router.post(
    path="/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK
)
@inject
async def login(
    model: AccountLogin,
    account_handler: AccountHandler = Depends(Provide[Container.account_handler]),
) -> LoginResponse:
    """
    Login
    """
    return await account_handler.login(model=model)


@router.get(
    path="/{account_id}",
    response_model=AccountDetail,
    status_code=status.HTTP_200_OK,
    dependencies=[check_access_token],
    description="For getting an account personal information"
)
@inject
async def get_account(
    request: Request,
    response: Response,
    account_id: uuid.UUID,
    account_handler: AccountHandler = Depends(Provide[Container.account_handler]),
) -> AccountDetail:
    """
    Get an account
    """
    return await account_handler.get_account(account_id=account_id)


@router.put(
    path="/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[check_access_token],
    description="For updating an account personal information"
)
@inject
async def update_account(
    request: Request,
    response: Response,
    account_id: uuid.UUID,
    model: AccountUpdate,
    account_handler: AccountHandler = Depends(Provide[Container.account_handler]),
) -> None:
    """
    Update an account
    """
    await account_handler.update_account(account_id=account_id, model=model)


@router.delete(
    path="/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[check_access_token],
    description="For deleting an account"
)
@inject
async def delete_account(
    request: Request,
    response: Response,
    account_id: uuid.UUID,
    account_handler: AccountHandler = Depends(Provide[Container.account_handler]),
) -> None:
    """
    Delete an account
    """
    await account_handler.delete_account(account_id=account_id)
