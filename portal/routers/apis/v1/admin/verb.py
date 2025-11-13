"""
Admin verb API routes
"""

from dependency_injector.wiring import inject, Provide
from fastapi import Depends, status

from portal.container import Container
from portal.handlers import AdminVerbHandler
from portal.routers.auth_router import AuthRouter
from portal.serializers.v1.admin.verb import VerbList

router: AuthRouter = AuthRouter(is_admin=True)


@router.get(
    path="/list",
    status_code=status.HTTP_200_OK,
    response_model=VerbList
)
@inject
async def get_verb_list(
    admin_verb_handler: AdminVerbHandler = Depends(Provide[Container.admin_verb_handler])
):
    """
    Get verb list
    :param admin_verb_handler:
    :return:
    """
    return await admin_verb_handler.get_verb_list()
