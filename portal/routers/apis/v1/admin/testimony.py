"""
Admin testimony API routes
"""
import uuid
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import Depends, Query, status

from portal.container import Container
from portal.handlers import AdminTestimonyHandler
from portal.routers.auth_router import AuthRouter
from portal.serializers.v1.admin.testimony import (
    TestimonyQuery,
    TestimonyPages,
    TestimonyDetail,
)

router: AuthRouter = AuthRouter(is_admin=True)


@router.get(
    path="/pages",
    status_code=status.HTTP_200_OK,
    response_model=TestimonyPages
)
@inject
async def get_testimony_pages(
    query_model: Annotated[TestimonyQuery, Query()],
    admin_testimony_handler: AdminTestimonyHandler = Depends(Provide[Container.admin_testimony_handler])
):
    return await admin_testimony_handler.get_testimony_pages(model=query_model)


@router.get(
    path="/{testimony_id}",
    status_code=status.HTTP_200_OK,
    response_model=TestimonyDetail
)
@inject
async def get_testimony(
    testimony_id: uuid.UUID,
    admin_testimony_handler: AdminTestimonyHandler = Depends(Provide[Container.admin_testimony_handler])
):
    return await admin_testimony_handler.get_testimony_by_id(testimony_id=str(testimony_id))
