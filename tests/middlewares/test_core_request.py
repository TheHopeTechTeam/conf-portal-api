from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from portal.middlewares.core_request import CoreRequestMiddleware


class _FakeContainer:
    def __init__(self, db_session):
        self._db_session = db_session

    def db_session(self):
        return self._db_session


def _session_with_async_mocks():
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def client_for_status():
    def _make(status_code: int):
        session = _session_with_async_mocks()
        app = FastAPI()
        app.container = _FakeContainer(session)
        app.add_middleware(CoreRequestMiddleware)

        @app.get("/t")
        async def handler():
            return JSONResponse(content={}, status_code=status_code)

        test_client = TestClient(app, raise_server_exceptions=False)
        return test_client, session

    return _make


def test_core_request_middleware_503_calls_rollback_not_commit(client_for_status):
    client, session = client_for_status(503)
    response = client.get("/t")
    assert response.status_code == 503
    session.commit.assert_not_called()
    session.rollback.assert_called_once()
    session.close.assert_called_once()


def test_core_request_middleware_200_calls_commit(client_for_status):
    client, session = client_for_status(200)
    response = client.get("/t")
    assert response.status_code == 200
    session.commit.assert_called_once()
    session.rollback.assert_not_called()
    session.close.assert_called_once()


def test_core_request_middleware_422_calls_rollback(client_for_status):
    client, session = client_for_status(422)
    response = client.get("/t")
    assert response.status_code == 422
    session.commit.assert_not_called()
    session.rollback.assert_called_once()
    session.close.assert_called_once()


def test_core_request_middleware_transient_exception_returns_503_without_app_handler():
    """
    When call_next raises before FastAPI exception_handler runs (e.g. BaseHTTPMiddleware
    ordering), CoreRequestMiddleware must still return 503 for transient DB errors.
    """
    session = _session_with_async_mocks()
    app = FastAPI()
    app.container = _FakeContainer(session)
    app.add_middleware(CoreRequestMiddleware)

    @app.get("/boom")
    async def handler():
        raise ConnectionResetError(54, "Connection reset")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")
    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "db_transient"
    session.commit.assert_not_called()
    session.rollback.assert_called_once()
    session.close.assert_called_once()
