"""
The Hope Ticket Service
"""
from typing import Optional
from urllib.parse import urljoin
from uuid import UUID

from httpx import HTTPStatusError
from sentry_sdk.tracing import Span

from portal.config import settings
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.http_client import http_client


class TheHopeTicketService:
    """The Hope Ticket Service"""

    def __init__(self):
        self._base_url = f"{settings.THEHOPE_TICKET_SYSTEM_URL}/api/"
        self._headers = {"x-external-service-token": settings.THEHOPE_TICKET_SYSTEM_API_KEY}

    def _build_url(self, path: str, version: str = "v1") -> str:
        """
        Build URL for API call
        :param path:
        :param version:
        :return:
        """
        return urljoin(self._base_url, f"{version}/{path}")

    @distributed_trace(inject_span=True)
    async def get_ticket_types(self, _span: Span) -> dict:
        """

        :param _span:
        :return:
        """
        url = self._build_url(path="/ticketTypes")
        try:
            resp = await (
                http_client.create(url)
                .add_headers(self._headers)
                .aget()
            )
            resp.raise_for_status()
            return resp.json()
        except HTTPStatusError as e:
            _span.set_data("error.status_code", e.response.status_code)
            _span.set_data("error.message", e.response.text)
            raise e

    @distributed_trace(inject_span=True)
    async def get_ticket_by_id(self, ticket_id: UUID, _span: Span) -> Optional[dict]:
        """
        Get ticket by id.
        :param ticket_id:
        :param _span:
        :return:
        """
        url = self._build_url(path=f"/tickets/{ticket_id}")
        try:
            resp = await (
                http_client.create(url)
                .add_headers(self._headers)
                .aget()
            )
            resp.raise_for_status()
            data = resp.json()
            return (data.get("doc") if isinstance(data, dict) and "doc" in data else data)
        except HTTPStatusError as e:
            _span.set_data("error.status_code", e.response.status_code)
            _span.set_data("error.message", e.response.text)
            if e.response.status_code == 404:
                return None
            raise e
        except Exception as e:
            _span.set_data("error.message", str(e))
            return None

    @distributed_trace(inject_span=True)
    async def get_ticket_list_by_email(self, user_email: str, _span: Span) -> Optional[dict]:
        """
        Get ticket by user email
        :param user_email:
        :param _span:
        :return:
        """
        url = self._build_url(path="/tickets")
        params = {
            "trash": False,
            "where[user.email][equals]": user_email
        }
        try:
            resp = await (
                http_client.create(url)
                .add_headers(self._headers)
                .add_query(params)
                .aget()
            )
            resp.raise_for_status()
            return resp.json()
        except HTTPStatusError as e:
            _span.set_data("error.status_code", e.response.status_code)
            _span.set_data("error.message", e.response.text)
            return None
        except Exception as e:
            _span.set_data("error.message", str(e))
            return None

    @distributed_trace(inject_span=True)
    async def check_in_ticket(self, ticket_id: UUID, _span: Span) -> dict:
        """
        Update ticket check-in status
        :param ticket_id:
        :param _span:
        :return:
        """
        url = self._build_url(path=f"/tickets/{ticket_id}")
        data = {"isCheckedIn": True}
        try:
            resp = await (
                http_client.create(url)
                .add_headers(self._headers)
                .add_json(data)
                .retry(3)
                .apatch()
            )
            resp.raise_for_status()
            return resp.json()
        except HTTPStatusError as e:
            _span.set_data("error.status_code", e.response.status_code)
            _span.set_data("error.message", e.response.text)
            raise e
        except Exception as e:
            _span.set_data("error.message", str(e))
            raise e
