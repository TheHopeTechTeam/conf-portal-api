"""
Fixtures for all services.
"""
import pytest

from portal.container import Container
from portal.services.thehope_ticket import TheHopeTicketService


@pytest.fixture
def thehope_ticket_service(container: Container) -> TheHopeTicketService:
    return container.thehope_ticket_service()
