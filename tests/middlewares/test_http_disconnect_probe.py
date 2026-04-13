from unittest.mock import AsyncMock, patch

import pytest

from portal.middlewares.http_disconnect_probe import HttpDisconnectProbeMiddleware


@pytest.mark.asyncio
async def test_http_disconnect_probe_logs_disconnect_event():
    async def inner_app(scope, recv, send):
        await recv()

    async def upstream_receive():
        return {"type": "http.disconnect"}

    mw = HttpDisconnectProbeMiddleware(inner_app)
    scope = {"type": "http", "path": "/api/example"}
    send = AsyncMock()

    with patch("portal.middlewares.http_disconnect_probe.logger") as mock_logger:
        await mw(scope, upstream_receive, send)

    mock_logger.info.assert_called_once()
    first_arg = mock_logger.info.call_args[0][0]
    assert "event=http_disconnect" in first_arg
    assert "/api/example" in mock_logger.info.call_args[0]


@pytest.mark.asyncio
async def test_http_disconnect_probe_non_http_passthrough():
    inner = AsyncMock()
    mw = HttpDisconnectProbeMiddleware(inner)
    scope = {"type": "lifespan"}
    receive = AsyncMock()
    send = AsyncMock()
    await mw(scope, receive, send)
    inner.assert_awaited_once_with(scope, receive, send)
