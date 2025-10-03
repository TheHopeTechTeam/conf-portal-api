"""
Test admin role handler
"""
import pytest

from portal.handlers import AdminRoleHandler
from portal.serializers.mixins import GenericQueryBaseModel


@pytest.mark.asyncio
async def test_get_role_pages(admin_role_handler: AdminRoleHandler):
    """

    :param admin_role_handler:
    :return:
    """
    model = GenericQueryBaseModel()
    item = await admin_role_handler.get_role_pages(model=model)
