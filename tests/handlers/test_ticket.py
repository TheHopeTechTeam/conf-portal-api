"""
Test ticket handler
"""
import os
import uuid

import pytest

from portal.handlers import TicketHandler


@pytest.mark.asyncio
async def test_get_user_ticket_by_email(ticket_handler: TicketHandler):
    """

    :param ticket_handler:
    :return:
    """
    email = os.environ.get("TEST_EMAIL")
    assert email
    result = await ticket_handler.get_user_ticket_by_email(email=email)


@pytest.mark.asyncio
async def test__get_workshop_registration_status(ticket_handler: TicketHandler):
    """

    :param ticket_handler:
    :return:
    """
    user_id = os.environ.get("TEST_USER_ID")
    assert user_id
    user_id = uuid.UUID(user_id)
    result = await ticket_handler._get_workshop_registration_status(user_id=user_id)
    print(result)
