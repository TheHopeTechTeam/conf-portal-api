"""
Demo API Router
"""
import uuid
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import Depends, Query
from starlette import status

from portal.container import Container
from portal.handlers import DemoHandler
from portal.routers.auth_router import AuthRouter
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import GenericQueryBaseModel, DeleteBaseModel
from portal.serializers.mixins.base import BulkAction
from portal.serializers.v1.demo import DemoPages, DemoList, DemoCreate, DemoUpdate

router: AuthRouter = AuthRouter(require_auth=False)


@router.get(
    path="/pages",
    status_code=status.HTTP_200_OK,
    response_model=DemoPages
)
@inject
async def demo_pages(
    query_model: Annotated[GenericQueryBaseModel, Query()],
    demo_handler: DemoHandler = Depends(Provide[Container.demo_handler])
) -> DemoPages:
    """
    Demo pages
    :param query_model:
    :param demo_handler:
    :return:
    """
    return await demo_handler.get_pages(model=query_model)


@router.get(
    path="/list",
    status_code=status.HTTP_200_OK,
    response_model=DemoList
)
@inject
async def demo_list(
    demo_handler: DemoHandler = Depends(Provide[Container.demo_handler])
) -> DemoList:
    """
    Demo list
    :param demo_handler:
    :return:
    """
    return await demo_handler.get_list()


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=UUIDBaseModel
)
@inject
async def create_demo(
    demo_data: DemoCreate,
    demo_handler: DemoHandler = Depends(Provide[Container.demo_handler])
) -> UUIDBaseModel:
    """
    Create a demo
    :param demo_data:
    :param demo_handler:
    :return:
    """
    return await demo_handler.create_demo(model=demo_data)


@router.delete(
    path="/{demo_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def delete_demo(
    demo_id: uuid.UUID,
    model: DeleteBaseModel,
    demo_handler: DemoHandler = Depends(Provide[Container.demo_handler])
) -> None:
    """
    Delete a demo
    :param demo_id:
    :param model:
    :param demo_handler:
    :return:
    """
    await demo_handler.delete_demo(demo_id=demo_id, model=model)


@router.put(
    path="/restore",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def restore_demo(
    model: BulkAction,
    demo_handler: DemoHandler = Depends(Provide[Container.demo_handler])
) -> None:
    """

    :param model:
    :param demo_handler:
    :return:
    """
    await demo_handler.restore_demo(model=model)


@router.put(
    path="/{demo_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def update_demo(
    demo_id: uuid.UUID,
    demo_data: DemoUpdate,
    demo_handler: DemoHandler = Depends(Provide[Container.demo_handler])
) -> None:
    """
    Update a demo
    :param demo_id:
    :param demo_data:
    :param demo_handler:
    :return:
    """
    await demo_handler.update_demo(demo_id=demo_id, model=demo_data)
