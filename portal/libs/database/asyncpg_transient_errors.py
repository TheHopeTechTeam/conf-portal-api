"""
Detect transient asyncpg / connection errors for retries and HTTP mapping.
"""

import asyncpg


def _iter_exception_chain(exc: BaseException):
    seen: set[int] = set()
    pending = [exc]
    while pending:
        current = pending.pop()
        ident = id(current)
        if ident in seen:
            continue
        seen.add(ident)
        yield current
        if current.__cause__ is not None:
            pending.append(current.__cause__)
        if current.__context__ is not None and current.__context__ is not current.__cause__:
            pending.append(current.__context__)


def is_transient_asyncpg_connection_error(exc: BaseException) -> bool:
    """
    Return True if exc or its cause/context chain indicates a transient DB connection issue.
    """
    transient_types = (
        asyncpg.exceptions.ConnectionDoesNotExistError,
        asyncpg.exceptions.InterfaceError,
        asyncpg.exceptions.PostgresConnectionError,
        asyncpg.exceptions.TooManyConnectionsError,
        ConnectionResetError,
        BrokenPipeError,
    )
    for link in _iter_exception_chain(exc):
        if isinstance(link, transient_types):
            return True
        msg = (str(link) or "").lower()
        if "closed" in msg and "middle" in msg and "operation" in msg:
            return True
        if "connection" in msg and "lost" in msg:
            return True
    return False
