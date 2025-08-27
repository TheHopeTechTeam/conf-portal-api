"""
Fixtures for workshop handler tests.
"""
import uuid

import pytest

from portal.apps.account.models import Account
from portal.container import Container
from portal.handlers import WorkshopHandler
from portal.libs.contexts.api_context import set_api_context, APIContext


@pytest.fixture
def workshop_handler(account_id: uuid.UUID) -> WorkshopHandler:
    """
    Get workshop handler fixture.
    :param account_id:
    :return:
    """
    set_api_context(
        APIContext(
            account=Account.objects.get(id=account_id)
        )
    )
    return Container.workshop_handler()
