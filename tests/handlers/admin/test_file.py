"""
Tests for AdminFileHandler batch signed URL loading.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from portal.handlers.admin.file import AdminFileHandler
from portal.schemas.file import SignedUrlFileByResourceRow


def _file_handler_with_session(session: MagicMock) -> AdminFileHandler:
    redis_pool = MagicMock()
    redis_pool.create = MagicMock(return_value=AsyncMock())
    return AdminFileHandler(session=session, redis_client=redis_pool)


@pytest.mark.asyncio
async def test_get_signed_urls_by_resource_ids_empty_collection():
    """
    Empty or all-falsy resource_ids should return {} without querying.
    """
    session = MagicMock()
    handler = _file_handler_with_session(session)
    assert await handler.get_signed_urls_by_resource_ids([]) == {}
    session.select.assert_not_called()


@pytest.mark.asyncio
async def test_get_signed_url_by_resource_id_delegates_to_batch(mocker: MockerFixture):
    """
    Single-resource helper should call batch with a one-element collection.
    """
    session = MagicMock()
    handler = _file_handler_with_session(session)
    rid = uuid.uuid4()
    mock_batch = mocker.patch.object(
        handler,
        "get_signed_urls_by_resource_ids",
        new_callable=AsyncMock,
        return_value={rid: ["https://example.com/a"]},
    )
    out = await handler.get_signed_url_by_resource_id(rid)
    assert out == ["https://example.com/a"]
    mock_batch.assert_awaited_once_with([rid])


@pytest.mark.asyncio
async def test_get_signed_urls_by_resource_ids_groups_by_resource(mocker: MockerFixture):
    """
    Rows for the same resource_id should produce one list of signed URLs in order.
    """
    rid_a = uuid.uuid4()
    rid_b = uuid.uuid4()
    row_a1 = SignedUrlFileByResourceRow(
        resource_id=rid_a,
        id=uuid.uuid4(),
        original_name="1.png",
        key="k1",
        storage="s3",
        bucket="b",
        region="us-east-1",
    )
    row_a2 = SignedUrlFileByResourceRow(
        resource_id=rid_a,
        id=uuid.uuid4(),
        original_name="2.png",
        key="k2",
        storage="s3",
        bucket="b",
        region="us-east-1",
    )
    row_b = SignedUrlFileByResourceRow(
        resource_id=rid_b,
        id=uuid.uuid4(),
        original_name="b.png",
        key="kb",
        storage="s3",
        bucket="b",
        region="us-east-1",
    )
    session = MagicMock()
    chain = MagicMock()
    session.select = MagicMock(return_value=chain)
    chain.outerjoin.return_value = chain
    chain.where.return_value = chain
    chain.order_by.return_value = chain
    chain.fetch = AsyncMock(return_value=[row_a1, row_a2, row_b])
    handler = _file_handler_with_session(session)
    mocker.patch.object(handler, "get_signed_url", new_callable=AsyncMock, side_effect=["u1", "u2", "u3"])
    result = await handler.get_signed_urls_by_resource_ids([rid_a, rid_b])
    assert result[rid_a] == ["u1", "u2"]
    assert result[rid_b] == ["u3"]
    assert handler.get_signed_url.await_count == 3
