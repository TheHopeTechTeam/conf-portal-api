"""
Tests for TheHopeTicketProvider.
"""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from portal.providers.thehope_ticket_provider import TheHopeTicketProvider
from portal.schemas.thehope_ticket import (
    TheHopeTicket,
    TheHopeTicketsListResponse,
    TheHopeTicketType,
)


@pytest.fixture
def mock_thehope_ticket_service():
    return MagicMock()


@pytest.fixture
def thehope_ticket_provider(mock_thehope_ticket_service) -> TheHopeTicketProvider:
    return TheHopeTicketProvider(thehope_ticket_service=mock_thehope_ticket_service)


def _raw_tickets_list_response(docs=None, total_docs=0, page=1, total_pages=0):
    return {
        "docs": docs or [],
        "totalDocs": total_docs,
        "page": page,
        "totalPages": total_pages,
    }


def _raw_ticket(id_=None, order_id=None, type_id=None):
    return {
        "id": str(id_ or uuid4()),
        "order": str(order_id or uuid4()),
        "type": str(type_id or uuid4()),
        "isRedeemed": False,
        "isCheckedIn": False,
    }


def _raw_ticket_type(id_=None, name="一般票", price=1800):
    return {
        "id": str(id_ or uuid4()),
        "name": name,
        "price": price,
        "bundleSize": 1,
        "maxTickets": 200,
        "sold": 0,
    }


@pytest.mark.asyncio
async def test_get_ticket_types_returns_objectified_list(
    thehope_ticket_provider: TheHopeTicketProvider,
    mock_thehope_ticket_service,
):
    """get_ticket_types should return list of TheHopeTicketType from service raw response."""
    raw = {"docs": [_raw_ticket_type(), _raw_ticket_type(name="雙人套票", price=1600)]}
    mock_thehope_ticket_service.get_ticket_types = AsyncMock(return_value=raw)

    result = await thehope_ticket_provider.get_ticket_types()

    assert len(result) == 2
    assert all(isinstance(t, TheHopeTicketType) for t in result)
    assert result[0].name == "一般票"
    assert result[1].name == "雙人套票"
    mock_thehope_ticket_service.get_ticket_types.assert_called_once()


@pytest.mark.asyncio
async def test_get_tickets_by_email_returns_objectified_response(
    thehope_ticket_provider: TheHopeTicketProvider,
    mock_thehope_ticket_service,
):
    """get_tickets_by_email should return TheHopeTicketsListResponse when service returns data."""
    raw = _raw_tickets_list_response(docs=[_raw_ticket()], total_docs=1)
    mock_thehope_ticket_service.get_ticket_by_email = AsyncMock(return_value=raw)

    result = await thehope_ticket_provider.get_ticket_by_email("user@example.com")

    assert result is not None
    assert isinstance(result, TheHopeTicketsListResponse)
    assert len(result.docs) == 1
    assert result.total_docs == 1
    mock_thehope_ticket_service.get_ticket_by_email.assert_called_once_with("user@example.com")


@pytest.mark.asyncio
async def test_get_tickets_by_email_returns_none_when_service_returns_none(
    thehope_ticket_provider: TheHopeTicketProvider,
    mock_thehope_ticket_service,
):
    """get_tickets_by_email should return None when service returns None."""
    mock_thehope_ticket_service.get_ticket_by_email = AsyncMock(return_value=None)

    result = await thehope_ticket_provider.get_ticket_by_email("user@example.com")

    assert result is None


@pytest.mark.asyncio
async def test_get_ticket_list_by_email_returns_first_ticket(
    thehope_ticket_provider: TheHopeTicketProvider,
    mock_thehope_ticket_service,
):
    """get_ticket_list_by_email should return first ticket (docs[0]) when response has docs."""
    ticket_id = uuid4()
    raw = _raw_tickets_list_response(docs=[_raw_ticket(id_=ticket_id)], total_docs=1)
    mock_thehope_ticket_service.get_ticket_by_email = AsyncMock(return_value=raw)

    result = await thehope_ticket_provider.get_ticket_by_email("user@example.com")

    assert result is not None
    assert isinstance(result, TheHopeTicket)
    assert result.id == ticket_id


@pytest.mark.asyncio
async def test_get_ticket_list_by_email_returns_none_when_no_tickets(
    thehope_ticket_provider: TheHopeTicketProvider,
    mock_thehope_ticket_service,
):
    """get_ticket_list_by_email should return None when get_tickets_by_email returns None."""
    mock_thehope_ticket_service.get_ticket_by_email = AsyncMock(return_value=None)

    result = await thehope_ticket_provider.get_ticket_by_email("user@example.com")

    assert result is None


@pytest.mark.asyncio
async def test_check_in_ticket_calls_service_and_does_not_raise(
    thehope_ticket_provider: TheHopeTicketProvider,
    mock_thehope_ticket_service,
):
    """check_in_ticket should call service and not raise on success."""
    ticket_id = uuid4()
    mock_thehope_ticket_service.check_in_ticket = AsyncMock(return_value=None)

    await thehope_ticket_provider.check_in_ticket(ticket_id)

    mock_thehope_ticket_service.check_in_ticket.assert_called_once_with(ticket_id)


@pytest.mark.asyncio
async def test_check_in_ticket_swallows_exception_and_logs(
    thehope_ticket_provider: TheHopeTicketProvider,
    mock_thehope_ticket_service,
    mocker,
):
    """check_in_ticket should not re-raise when service raises; error is logged."""
    ticket_id = uuid4()
    mock_thehope_ticket_service.check_in_ticket = AsyncMock(
        side_effect=ConnectionError("connection failed")
    )
    mock_logger = mocker.patch("portal.providers.thehope_ticket_provider.logger")

    await thehope_ticket_provider.check_in_ticket(ticket_id)

    mock_logger.error.assert_called_once()
    assert "Failed to check in ticket" in mock_logger.error.call_args[0][0]
    assert str(ticket_id) in mock_logger.error.call_args[0][0]
