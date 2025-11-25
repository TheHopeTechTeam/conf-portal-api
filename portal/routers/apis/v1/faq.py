"""
FAQs API router
"""
import uuid

from dependency_injector.wiring import Provide, inject
from fastapi import Depends
from starlette import status

from portal.container import Container
from portal.handlers import FAQHandler
from portal.libs.depends import DEFAULT_RATE_LIMITERS
from portal.routers.auth_router import AuthRouter
from portal.serializers.v1.faq import FaqCategoryBase, FaqCategoryList, FaqBase, FaqList

router: AuthRouter = AuthRouter(
    require_auth=False,
    dependencies=[
        *DEFAULT_RATE_LIMITERS
    ]
)


@router.get(
    path="/categories",
    status_code=status.HTTP_200_OK,
    response_model=FaqCategoryList,
    operation_id="get_faq_categories",
)
@inject
async def get_faq_categories(
    faq_handler: FAQHandler = Depends(Provide[Container.faq_handler]),
) -> FaqCategoryList:
    """
    Get FAQ categories
    """
    return await faq_handler.get_faq_categories()


@router.get(
    path="/category/{category_id}",
    status_code=status.HTTP_200_OK,
    response_model=FaqCategoryBase,
    operation_id="get_faq_category_by_id",
)
@inject
async def get_category_by_id(
    category_id: uuid.UUID,
    faq_handler: FAQHandler = Depends(Provide[Container.faq_handler]),
) -> FaqCategoryBase:
    """
    Get category by ID
    """
    return await faq_handler.get_category_by_id(category_id)


@router.get(
    path="/{faq_id}",
    status_code=status.HTTP_200_OK,
    response_model=FaqBase,
    operation_id="get_faq_by_id",
)
@inject
async def get_faq_by_id(
    faq_id: uuid.UUID,
    faq_handler: FAQHandler = Depends(Provide[Container.faq_handler]),
) -> FaqBase:
    """
    Get FAQ by ID
    """
    return await faq_handler.get_faq_by_id(faq_id)


@router.get(
    path="/category/{category_id}/list",
    status_code=status.HTTP_200_OK,
    response_model=FaqList,
    operation_id="get_faqs_by_category_id",
)
@inject
async def get_faqs_by_category_id(
    category_id: uuid.UUID,
    faq_handler: FAQHandler = Depends(Provide[Container.faq_handler]),
) -> FaqList:
    """
    Get FAQs by category
    """
    return await faq_handler.get_faqs_by_category(category_id)
