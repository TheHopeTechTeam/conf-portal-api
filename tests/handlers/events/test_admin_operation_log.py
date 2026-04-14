"""
Tests for admin operation log event handler and AdminLogHandler wiring.
"""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from portal.handlers.admin.log import AdminLogHandler
from portal.handlers.events.admin_operation_log import AdminOperationLogEventHandler
from portal.libs.consts.enums import OperationType
from portal.libs.contexts.request_context import (
    RequestContext,
    reset_request_context,
    set_request_context,
)
from portal.libs.contexts.user_context import UserContext, set_user_context, reset_user_context
from portal.libs.events.types import AdminOperationLogEvent
from portal.models import PortalLog
from portal.models.mixins.context import SYSTEM_USER_ID


@pytest.mark.asyncio
async def test_admin_operation_log_event_handler_inserts_portal_log():
    record_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    insert_chain = MagicMock()
    insert_chain.values.return_value = insert_chain
    insert_chain.execute = AsyncMock()
    session = MagicMock()
    session.insert.return_value = insert_chain

    handler = AdminOperationLogEventHandler(session=session)
    event = AdminOperationLogEvent(
        operation_type=OperationType.UPDATE,
        record_id=record_id,
        operation_code="portal_user",
        old_data={"name": "a"},
        new_data={"name": "b"},
        changed_fields=[{"field": "name", "old": "a", "new": "b"}],
        ip_address="203.0.113.1",
        user_agent="pytest",
        created_by="admin_user",
        created_by_id=actor_id,
    )
    await handler.handle(event=event)

    session.insert.assert_called_once_with(PortalLog)
    insert_chain.values.assert_called_once()
    kwargs = insert_chain.values.call_args.kwargs
    assert kwargs["operation_type"] == OperationType.UPDATE.value
    assert kwargs["record_id"] == record_id
    assert kwargs["operation_code"] == "portal_user"
    assert json.loads(kwargs["old_data"]) == {"name": "a"}
    assert json.loads(kwargs["new_data"]) == {"name": "b"}
    assert json.loads(kwargs["changed_fields"]) == [{"field": "name", "old": "a", "new": "b"}]
    assert kwargs["ip_address"] == "203.0.113.1"
    assert kwargs["user_agent"] == "pytest"
    assert kwargs["created_by"] == "admin_user"
    assert kwargs["created_by_id"] == actor_id
    insert_chain.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_operation_log_event_handler_resolves_actor_from_user_context():
    user_id = uuid.uuid4()
    token = set_user_context(
        UserContext(user_id=user_id, username="ctx_user", is_admin=True)
    )
    try:
        insert_chain = MagicMock()
        insert_chain.values.return_value = insert_chain
        insert_chain.execute = AsyncMock()
        session = MagicMock()
        session.insert.return_value = insert_chain

        handler = AdminOperationLogEventHandler(session=session)
        event = AdminOperationLogEvent(operation_type=OperationType.LOGIN)
        await handler.handle(event=event)

        kwargs = insert_chain.values.call_args.kwargs
        assert kwargs["created_by"] == "ctx_user"
        assert kwargs["created_by_id"] == user_id
    finally:
        reset_user_context(token)


@pytest.mark.asyncio
async def test_admin_operation_log_event_handler_fallback_actor_when_no_context():
    insert_chain = MagicMock()
    insert_chain.values.return_value = insert_chain
    insert_chain.execute = AsyncMock()
    session = MagicMock()
    session.insert.return_value = insert_chain

    handler = AdminOperationLogEventHandler(session=session)
    event = AdminOperationLogEvent(operation_type=OperationType.OTHER)
    await handler.handle(event=event)

    kwargs = insert_chain.values.call_args.kwargs
    assert kwargs["created_by"] == "system"
    assert kwargs["created_by_id"] == SYSTEM_USER_ID


@pytest.mark.asyncio
async def test_admin_log_handler_create_log_publishes_event():
    user_id = uuid.uuid4()
    user_token = set_user_context(
        UserContext(user_id=user_id, username="publisher", is_admin=True)
    )
    req_token = set_request_context(
        RequestContext(ip="198.51.100.2", user_agent="Mozilla/test")
    )
    try:
        with patch("portal.handlers.admin.log.publish_event_in_background") as publish_mock:
            log_handler = AdminLogHandler()
            rid = uuid.uuid4()
            log_handler.create_log(
                OperationType.DELETE,
                record_id=rid,
                operation_code="portal_role",
            )
            publish_mock.assert_called_once()
            event = publish_mock.call_args.kwargs["event"]
            assert isinstance(event, AdminOperationLogEvent)
            assert event.operation_type == OperationType.DELETE
            assert event.record_id == rid
            assert event.operation_code == "portal_role"
            assert event.ip_address == "198.51.100.2"
            assert event.user_agent == "Mozilla/test"
            assert event.created_by == "publisher"
            assert event.created_by_id == user_id
    finally:
        reset_request_context(req_token)
        reset_user_context(user_token)


@pytest.mark.asyncio
async def test_admin_log_handler_create_log_autofills_changed_fields():
    user_token = set_user_context(
        UserContext(user_id=uuid.uuid4(), username="u", is_admin=True)
    )
    try:
        with patch("portal.handlers.admin.log.publish_event_in_background") as publish_mock:
            log_handler = AdminLogHandler()
            log_handler.create_log(
                OperationType.UPDATE,
                old_data={"name": "a", "keep": 1},
                new_data={"name": "b", "keep": 1},
            )
            event = publish_mock.call_args.kwargs["event"]
            assert event.old_data == {"name": "a", "keep": 1}
            assert event.new_data == {"name": "b", "keep": 1}
            assert event.changed_fields == [
                {"field": "name", "old": "a", "new": "b"},
            ]
    finally:
        reset_user_context(user_token)


@pytest.mark.asyncio
async def test_admin_log_handler_create_log_respects_explicit_changed_fields():
    user_token = set_user_context(
        UserContext(user_id=uuid.uuid4(), username="u", is_admin=True)
    )
    try:
        with patch("portal.handlers.admin.log.publish_event_in_background") as publish_mock:
            log_handler = AdminLogHandler()
            explicit = [{"field": "name", "old": "x", "new": "y"}]
            log_handler.create_log(
                OperationType.UPDATE,
                old_data={"name": "a"},
                new_data={"name": "b"},
                changed_fields=explicit,
            )
            event = publish_mock.call_args.kwargs["event"]
            assert event.old_data == {"name": "a"}
            assert event.new_data == {"name": "b"}
            assert event.changed_fields == explicit
    finally:
        reset_user_context(user_token)


@pytest.mark.asyncio
async def test_admin_log_handler_create_log_falls_back_when_normalize_raises():
    user_token = set_user_context(
        UserContext(user_id=uuid.uuid4(), username="u", is_admin=True)
    )
    try:
        with patch("portal.handlers.admin.log.publish_event_in_background") as publish_mock:
            with patch(
                "portal.handlers.admin.log.normalize_for_audit_json",
                side_effect=RuntimeError("normalize failed"),
            ):
                log_handler = AdminLogHandler()
                log_handler.create_log(
                    OperationType.UPDATE,
                    old_data={"name": "a"},
                    new_data={"name": "b"},
                )
            event = publish_mock.call_args.kwargs["event"]
            assert event.old_data == {"name": "a"}
            assert event.new_data == {"name": "b"}
            assert event.changed_fields is None
    finally:
        reset_user_context(user_token)


@pytest.mark.asyncio
async def test_admin_log_handler_create_log_swallows_outer_failure():
    user_token = set_user_context(
        UserContext(user_id=uuid.uuid4(), username="u", is_admin=True)
    )
    try:
        with patch(
            "portal.handlers.admin.log.publish_event_in_background",
            side_effect=RuntimeError("publish failed"),
        ):
            log_handler = AdminLogHandler()
            log_handler.create_log(OperationType.OTHER)
    finally:
        reset_user_context(user_token)
