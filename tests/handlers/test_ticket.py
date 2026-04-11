"""
Test ticket handler
"""
import os

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
