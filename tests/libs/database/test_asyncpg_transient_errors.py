import asyncpg.exceptions

from portal.libs.database.asyncpg_transient_errors import is_transient_asyncpg_connection_error


def test_is_transient_asyncpg_connection_error_types():
    assert is_transient_asyncpg_connection_error(
        asyncpg.exceptions.ConnectionDoesNotExistError("connection was closed")
    )
    assert is_transient_asyncpg_connection_error(ConnectionResetError(54, "Connection reset"))


def test_is_transient_asyncpg_connection_error_message_fallback():
    class CustomExc(Exception):
        pass

    assert is_transient_asyncpg_connection_error(
        CustomExc("connection was closed in the middle of operation")
    )
    assert not is_transient_asyncpg_connection_error(ValueError("syntax error"))


def test_is_transient_asyncpg_connection_error_follows_cause_chain():
    root = asyncpg.exceptions.ConnectionDoesNotExistError("connection was closed")
    wrapper = RuntimeError("sentry or outer")
    wrapper.__cause__ = root
    assert is_transient_asyncpg_connection_error(wrapper)
