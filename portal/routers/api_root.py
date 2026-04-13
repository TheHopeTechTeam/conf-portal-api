"""
Root router.
"""
from fastapi import APIRouter, HTTPException, Request, status

from portal.config import settings
from portal.libs.contexts.request_session_context import get_request_session

from .apis.v1 import router as api_v1_router

router = APIRouter()
router.include_router(api_v1_router, prefix="/v1")


if settings.IS_DEV:

    @router.get(
        path="/internal/dev/db-pg-sleep",
        operation_id="dev_db_pg_sleep",
        include_in_schema=False,
    )
    async def dev_db_pg_sleep(seconds: int = 45):
        """
        Dev-only: runs ``SELECT pg_sleep($1)`` on the **request** DB session so you can
        reproduce ``asyncpg`` / pool behavior when the server kills the backend mid-query.

        **Prerequisites**

        - ``IS_DEV`` is true; app is running with the same middleware stack as normal
          requests so ``get_request_session()`` is non-null for this route.
        - Use whatever auth / headers your local app expects for ``/api`` routes.

        **Steps**

        1. In a first terminal, start a **long** sleep (clamped 1..300), e.g.::

               curl -v 'http://127.0.0.1:8000/api/internal/dev/db-pg-sleep?seconds=120'

           Leave it blocking until step 4.

        2. In ``psql`` (as a role that can read ``pg_stat_activity`` and call
           ``pg_terminate_backend``), find the backend PID that is running ``pg_sleep``::

               SELECT pid, usename, datname, query
               FROM pg_stat_activity
               WHERE query ILIKE '%pg_sleep%';

        3. Terminate that backend while the HTTP request is still in-flight::

               SELECT pg_terminate_backend(<pid>);

        4. Observe the API process logs: ``db_io_transient_retry``,
           ``db_connection_discard_begin``, then either success after a retry or
           ``db_io_transient_exhausted`` / HTTP 500 if the retried ``pg_sleep`` is killed
           again or retries are exhausted.

        **Note**

        Each successful retry **re-runs** the full ``pg_sleep`` from the start, so wall
        time can be much longer than ``seconds`` if the backend is terminated repeatedly.
        """
        bounded = min(max(seconds, 1), 300)
        session = get_request_session()
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No request session",
            )
        await session.fetchval("SELECT pg_sleep($1)", float(bounded))
        return {"slept_seconds": bounded}

    @router.get(
        path="/internal/dev/receive-until-disconnect",
        operation_id="dev_receive_until_disconnect",
        include_in_schema=False,
    )
    async def dev_receive_until_disconnect(request: Request):
        """
        Dev-only: keep calling ``await request.receive()`` until
        ``{"type": "http.disconnect"}`` so ``HttpDisconnectProbeMiddleware`` can log
        ``event=http_disconnect`` when you abort the client.

        Example::

            curl -N 'http://127.0.0.1:8000/api/internal/dev/receive-until-disconnect'
            # Ctrl+C curl while blocking; check server logs for http_disconnect.
        """
        while True:
            message = await request.receive()
            if message.get("type") == "http.disconnect":
                return {"ok": True, "message": "saw http.disconnect"}


@router.get(
    path="/healthz",
    operation_id="healthz"
)
async def healthz():
    """
    Healthcheck endpoint
    :return:
    """
    return {
        "message": "ok"
    }
