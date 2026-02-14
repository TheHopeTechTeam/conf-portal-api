"""
Tests for TheHopeTicketService.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from portal.services.thehope_ticket import TheHopeTicketService


def test_build_url_with_path_without_leading_slash(mocker: MockerFixture):
    """_build_url should prefix path with / when path does not start with /."""
    mocker.patch("portal.services.thehope_ticket.settings", THEHOPE_TICKET_SYSTEM_URL="https://ticket.example.com", THEHOPE_TICKET_SYSTEM_API_KEY="key")
    service = TheHopeTicketService()
    result = service._build_url(path="tickets", version="v1")
    assert result == "https://ticket.example.com/api/v1/tickets"


def test_build_url_with_path_with_leading_slash(mocker: MockerFixture):
    """_build_url should use path as-is when path starts with /."""
    mocker.patch("portal.services.thehope_ticket.settings", THEHOPE_TICKET_SYSTEM_URL="https://ticket.example.com/", THEHOPE_TICKET_SYSTEM_API_KEY="key")
    service = TheHopeTicketService()
    result = service._build_url(path="/tickets", version="v1")
    assert result == "https://ticket.example.com/api/v1/tickets"


def test_build_url_with_custom_version(mocker: MockerFixture):
    """_build_url should use given version segment."""
    mocker.patch("portal.services.thehope_ticket.settings", THEHOPE_TICKET_SYSTEM_URL="https://ticket.example.com", THEHOPE_TICKET_SYSTEM_API_KEY="key")
    service = TheHopeTicketService()
    result = service._build_url(path="tickets", version="v2")
    assert "v2/tickets" in result
    assert result == "https://ticket.example.com/api/v2/tickets"


@pytest.mark.asyncio
async def test_get_ticket_by_email_returns_json_response(thehope_ticket_service: TheHopeTicketService, mocker: MockerFixture):
    """get_ticket_by_email should return parsed JSON from the tickets API."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"docs": [], "totalDocs": 0, "page": 1, "totalPages": 0}
    mock_client = MagicMock()
    mock_client.create.return_value.add_headers.return_value.add_query.return_value.aget = AsyncMock(
        return_value=mock_response
    )
    mocker.patch("portal.services.thehope_ticket.http_client", mock_client)

    result = await thehope_ticket_service.get_ticket_by_email("user@example.com")

    assert result == {"docs": [], "totalDocs": 0, "page": 1, "totalPages": 0}
    mock_client.create.assert_called_once()
    call_url = mock_client.create.call_args[0][0]
    assert "tickets" in call_url
    mock_client.create.return_value.add_headers.assert_called_once_with(thehope_ticket_service._headers)
    mock_client.create.return_value.add_headers.return_value.add_query.assert_called_once()
    call_params = mock_client.create.return_value.add_headers.return_value.add_query.call_args[0][0]
    assert call_params["trash"] is False
    assert call_params["where[user.email][equals]"] == "user@example.com"


@pytest.mark.asyncio
async def test_get_ticket_by_email_propagates_exception(thehope_ticket_service: TheHopeTicketService, mocker: MockerFixture):
    """get_ticket_by_email should re-raise when the HTTP client raises."""
    mock_client = MagicMock()
    mock_client.create.return_value.add_headers.return_value.add_query.return_value.aget = AsyncMock(
        side_effect=ConnectionError("connection failed")
    )
    mocker.patch("portal.services.thehope_ticket.http_client", mock_client)

    with pytest.raises(ConnectionError, match="connection failed"):
        await thehope_ticket_service.get_ticket_by_email("user@example.com")
