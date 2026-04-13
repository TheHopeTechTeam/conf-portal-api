from fastapi import FastAPI
from fastapi.testclient import TestClient

from portal.main import register_exception_handler


def test_register_exception_handler_transient_db_returns_503():
    app = FastAPI()

    @app.get("/boom")
    async def boom():
        raise ConnectionResetError(54, "Connection reset")

    register_exception_handler(application=app)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")
    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "db_transient"
    assert body["detail"]["message"] == "Service Unavailable"


def test_register_exception_handler_non_transient_returns_500():
    app = FastAPI()

    @app.get("/boom")
    async def boom():
        raise ValueError("syntax error")

    register_exception_handler(application=app)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")
    assert response.status_code == 500
    body = response.json()
    assert body.get("code") != "db_transient"
    assert body["detail"]["message"] == "Internal Server Error"
