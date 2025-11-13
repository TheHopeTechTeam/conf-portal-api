"""
Admin FAQ API routes
"""
import uuid
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import Depends, Query, status

from portal.container import Container
from portal.handlers import AdminFaqHandler
from portal.routers.auth_router import AuthRouter
from portal.schemas.mixins import UUIDBaseModel
from portal.serializers.mixins import DeleteBaseModel
from portal.serializers.mixins.base import BulkAction, DeleteQueryBaseModel
from portal.serializers.v1.admin.faq import (
    FaqCategoryList,
    FaqCategoryDetail,
    FaqCategoryCreate,
    FaqCategoryUpdate,
    FaqQuery,
    FaqPages,
    FaqDetail,
    FaqCreate,
    FaqUpdate,
)

router: AuthRouter = AuthRouter(is_admin=True)


@router.post(
    path="/category",
    status_code=status.HTTP_201_CREATED,
    response_model=UUIDBaseModel
)
@inject
async def create_category(
    category_data: FaqCategoryCreate,
    admin_faq_handler: AdminFaqHandler = Depends(Provide[Container.admin_faq_handler])
):
    """
    Create a FAQ category
    :param category_data:
    :param admin_faq_handler:
    :return:
    """
    return await admin_faq_handler.create_category(model=category_data)


@router.put(
    path="/category/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def update_category(
    category_id: uuid.UUID,
    category_data: FaqCategoryUpdate,
    admin_faq_handler: AdminFaqHandler = Depends(Provide[Container.admin_faq_handler])
):
    """
    Update a FAQ category
    :param category_id:
    :param category_data:
    :param admin_faq_handler:
    :return:
    """
    await admin_faq_handler.update_category(category_id=category_id, model=category_data)


@router.delete(
    path="/category/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def delete_category(
    category_id: uuid.UUID,
    model: DeleteBaseModel,
    admin_faq_handler: AdminFaqHandler = Depends(Provide[Container.admin_faq_handler])
):
    """
    Delete a FAQ category (soft by default)
    :param category_id:
    :param model:
    :param admin_faq_handler:
    :return:
    """
    await admin_faq_handler.delete_category(category_id=category_id, model=model)


@router.put(
    path="/category/restore",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def restore_categories(
    model: BulkAction,
    admin_faq_handler: AdminFaqHandler = Depends(Provide[Container.admin_faq_handler])
):
    """
    Restore soft-deleted FAQ categories
    :param model:
    :param admin_faq_handler:
    :return:
    """
    await admin_faq_handler.restore_categories(model=model)


@router.get(
    path="/pages",
    status_code=status.HTTP_200_OK,
    response_model=FaqPages
)
@inject
async def get_faq_pages(
    query_model: Annotated[FaqQuery, Query()],
    admin_faq_handler: AdminFaqHandler = Depends(Provide[Container.admin_faq_handler])
):
    """
    Get FAQ pages
    :param query_model:
    :param admin_faq_handler:
    :return:
    """
    return await admin_faq_handler.get_faq_pages(model=query_model)


@router.get(
    path="/{faq_id}",
    status_code=status.HTTP_200_OK,
    response_model=FaqDetail
)
@inject
async def get_faq(
    faq_id: uuid.UUID,
    admin_faq_handler: AdminFaqHandler = Depends(Provide[Container.admin_faq_handler])
):
    """
    Get a FAQ by ID
    :param faq_id:
    :param admin_faq_handler:
    :return:
    """
    return await admin_faq_handler.get_faq_by_id(faq_id=faq_id)


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=UUIDBaseModel
)
@inject
async def create_faq(
    faq_data: FaqCreate,
    admin_faq_handler: AdminFaqHandler = Depends(Provide[Container.admin_faq_handler])
):
    """
    Create a FAQ
    :param faq_data:
    :param admin_faq_handler:
    :return:
    """
    return await admin_faq_handler.create_faq(model=faq_data)


@router.put(
    path="/{faq_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def update_faq(
    faq_id: uuid.UUID,
    faq_data: FaqUpdate,
    admin_faq_handler: AdminFaqHandler = Depends(Provide[Container.admin_faq_handler])
):
    """
    Update a FAQ
    :param faq_id:
    :param faq_data:
    :param admin_faq_handler:
    :return:
    """
    await admin_faq_handler.update_faq(faq_id=faq_id, model=faq_data)


@router.delete(
    path="/{faq_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def delete_faq(
    faq_id: uuid.UUID,
    model: DeleteBaseModel,
    admin_faq_handler: AdminFaqHandler = Depends(Provide[Container.admin_faq_handler])
):
    """
    Delete a FAQ (soft by default)
    :param faq_id:
    :param model:
    :param admin_faq_handler:
    :return:
    """
    await admin_faq_handler.delete_faq(faq_id=faq_id, model=model)


@router.put(
    path="/restore",
    status_code=status.HTTP_204_NO_CONTENT
)
@inject
async def restore_faqs(
    model: BulkAction,
    admin_faq_handler: AdminFaqHandler = Depends(Provide[Container.admin_faq_handler])
):
    """
    Restore soft-deleted FAQs
    :param model:
    :param admin_faq_handler:
    :return:
    """
    await admin_faq_handler.restore_faqs(model=model)


@router.get(
    path="/category/list",
    status_code=status.HTTP_200_OK,
    response_model=FaqCategoryList
)
@inject
async def get_category_list(
    query_model: Annotated[DeleteQueryBaseModel, Query()],
    admin_faq_handler: AdminFaqHandler = Depends(Provide[Container.admin_faq_handler])
):
    """
    Get FAQ category list
    :param query_model:
    :param admin_faq_handler:
    :return:
    """
    return await admin_faq_handler.get_category_list(model=query_model)


@router.get(
    path="/category/{category_id}",
    status_code=status.HTTP_200_OK,
    response_model=FaqCategoryDetail
)
@inject
async def get_category(
    category_id: uuid.UUID,
    admin_faq_handler: AdminFaqHandler = Depends(Provide[Container.admin_faq_handler])
):
    """
    Get a FAQ category by ID
    :param category_id:
    :param admin_faq_handler:
    :return:
    """
    return await admin_faq_handler.get_category_by_id(category_id=category_id)
