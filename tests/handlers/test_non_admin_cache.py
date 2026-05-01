"""
Tests for non-admin handler cache behavior.
"""
from datetime import date, datetime, UTC
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from portal.handlers.conference import ConferenceHandler
from portal.handlers.faq import FAQHandler
from portal.handlers.notification import NotificationHandler
from portal.handlers.workshop import WorkshopHandler
from portal.serializers.v1.conference import ConferenceBase, ConferenceList
from portal.serializers.v1.faq import FaqCategoryBase
from portal.serializers.v1.notification import UserNotificationItem, UserNotificationList


class _QueryChain:
    def __init__(self, fetch_result):
        self._fetch_result = fetch_result

    def where(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    async def fetch(self, *args, **kwargs):
        return self._fetch_result


@pytest.mark.asyncio
async def test_conference_get_conferences_should_return_cached_result():
    conference = ConferenceBase(
        id=uuid4(),
        title="Conf 2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
    )
    cached_payload = ConferenceList(conferences=[conference]).model_dump_json()
    session = MagicMock()
    redis_instance = MagicMock()
    redis_instance.get = AsyncMock(return_value=cached_payload)
    redis_client = MagicMock()
    redis_client.create.return_value = redis_instance

    handler = ConferenceHandler(
        session=session,
        redis_client=redis_client,
        file_handler=MagicMock(),
    )

    result = await handler.get_conferences()

    assert len(result.conferences) == 1
    assert result.conferences[0].title == "Conf 2026"
    session.select.assert_not_called()


@pytest.mark.asyncio
async def test_faq_get_faq_categories_should_fallback_when_cache_read_fails():
    session = MagicMock()
    expected_rows = [
        FaqCategoryBase(id=uuid4(), name="General", description="General questions"),
    ]
    session.select.return_value = _QueryChain(fetch_result=expected_rows)

    redis_instance = MagicMock()
    redis_instance.get = AsyncMock(side_effect=Exception("redis-down"))
    redis_instance.set = AsyncMock(return_value=True)
    redis_client = MagicMock()
    redis_client.create.return_value = redis_instance

    handler = FAQHandler(session=session, redis_client=redis_client)

    result = await handler.get_faq_categories()

    assert len(result.categories) == 1
    assert result.categories[0].name == "General"
    session.select.assert_called_once()


@pytest.mark.asyncio
async def test_workshop_invalidate_related_caches_should_delete_all_expected_keys():
    session = MagicMock()
    redis_instance = MagicMock()
    redis_instance.delete = AsyncMock(return_value=1)
    redis_client = MagicMock()
    redis_client.create.return_value = redis_instance
    handler = WorkshopHandler(
        session=session,
        redis_client=redis_client,
        file_handler=MagicMock(),
    )
    user_id = uuid4()
    handler._user_ctx = SimpleNamespace(user_id=user_id)
    workshop_id = uuid4()

    await handler._invalidate_workshop_related_caches(workshop_id=workshop_id)

    assert redis_instance.delete.await_count == 4


@pytest.mark.asyncio
async def test_notification_get_notifications_should_return_cached_result():
    item = UserNotificationItem(
        id=uuid4(),
        title="Hello",
        message="World",
        url=None,
        is_read=False,
        created_at=datetime.now(UTC),
    )
    cached_payload = UserNotificationList(items=[item]).model_dump_json()
    session = MagicMock()
    redis_instance = MagicMock()
    redis_instance.get = AsyncMock(return_value=cached_payload)
    redis_client = MagicMock()
    redis_client.create.return_value = redis_instance

    handler = NotificationHandler(session=session, redis_client=redis_client)
    handler._require_user_id = MagicMock(return_value=uuid4())

    result = await handler.get_notifications()

    assert len(result.items) == 1
    assert result.items[0].title == "Hello"
    session.select.assert_not_called()
