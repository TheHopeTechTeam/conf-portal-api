"""
main application
"""

from collections import defaultdict
from urllib.parse import urlparse

import firebase_admin
import sentry_sdk
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exception_handlers import http_exception_handler
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from firebase_admin import credentials
from sentry_sdk.integrations.asyncpg import AsyncPGIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.tracing import Span
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse

from portal.config import settings
from portal.container import Container
from portal.exceptions.responses import ApiBaseException
from portal.libs.consts.base import SECURITY_SCHEMES
from portal.libs.contexts.request_session_context import get_request_session
from portal.libs.database.asyncpg_transient_errors import is_transient_asyncpg_connection_error
from portal.libs.database.transient_db_http_response import (
    safe_rollback_session,
    transient_db_503_content,
)
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.logger import logger
from portal.libs.events.publisher import set_global_container
from portal.libs.utils.lifespan import lifespan
from portal.middlewares import (
    AuthMiddleware,
    CoreRequestMiddleware,
    HttpDisconnectProbeMiddleware,
)
from portal.routers import admin_router, api_router

__all__ = ["app"]


def setup_tracing():
    """
    Setup tracing
    :return:
    """
    if not settings.SENTRY_URL:
        return

    def before_send_transaction(event, hint):
        request = (event or {}).get("request") or {}
        url = request.get("url")
        if not url:
            return event

        path = urlparse(url).path or ""
        if not path:
            return event

        event["transaction"] = path.strip()
        event.setdefault("transaction_info", {})["source"] = "url"
        return event

    sentry_sdk.init(
        dsn=settings.SENTRY_URL,
        release=settings.APP_VERSION,
        integrations=[
            AsyncPGIntegration(),
            FastApiIntegration(),
            HttpxIntegration(),
            RedisIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        environment=settings.ENV.upper(),
        enable_tracing=True,
        before_send_transaction=before_send_transaction,
        enable_logs=True,
    )


def register_router(application: FastAPI) -> None:
    """
    register router
    :param application:
    :return:
    """
    application.include_router(api_router, prefix="/api")


def register_middleware(application: FastAPI) -> None:
    """
    register middleware
    Middleware order (from outer to inner, executed in reverse order):
    1. HttpDisconnectProbeMiddleware - Log http.disconnect on receive (outermost)
    2. CORSMiddleware - Handle CORS
    3. CoreRequestMiddleware - Setup request context and database session
    4. AuthMiddleware - Verify token and set UserContext (innermost, executed first)

    Note: AuthMiddleware executes after CoreRequestMiddleware to ensure database session is available.
    Both authentication (token verification) and authorization (permission checking) are handled in AuthMiddleware.
    No dependency injection is used for auth logic.
    :param application:
    :return:
    """
    # Last add_middleware wraps outermost on the request path (receive first).
    application.add_middleware(AuthMiddleware)
    application.add_middleware(CoreRequestMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_origin_regex=settings.CORS_ALLOW_ORIGINS_REGEX,
    )
    application.add_middleware(HttpDisconnectProbeMiddleware)


def init_firebase():
    """
    init firebase
    :return:
    """
    credential = credentials.Certificate(settings.GOOGLE_FIREBASE_CERTIFICATE)
    firebase_admin.initialize_app(
        credential=credential,
    )


def register_exception_handler(application: FastAPI) -> None:
    """
    register exception handler
    :param application:
    :return:
    """
    @application.exception_handler(HTTPException)
    @distributed_trace(inject_span=True)
    async def root_http_exception_handler(request, exc: HTTPException, *, _span: Span = None):
        """

        :param request:
        :param exc:
        :param _span:
        :return:
        """
        session = get_request_session()
        if session is not None:
            await session.rollback()
        try:
            _span.set_data("internal.exc_detail", exc.detail)
            _span.set_data("internal.endpoint", str(request.url))
        except Exception:
            pass
        return await http_exception_handler(request, exc)


    @application.exception_handler(ApiBaseException)
    @distributed_trace(inject_span=True)
    async def root_api_exception_handler(
        request, exc: ApiBaseException, *, _span: Span = None
    ):
        """

        :param request:
        :param exc:
        :param _span:
        :return:
        """
        session = get_request_session()
        if session is not None:
            await session.rollback()
        content = defaultdict()
        content["detail"] = exc.detail
        if settings.is_dev:
            content["debug_detail"] = exc.debug_detail
            content["url"] = str(request.url)
        try:
            _span.set_data("internal.exc_detail", exc.detail)
            _span.set_data("internal.exc_dev_info", exc.debug_detail)
            _span.set_data("internal.endpoint", str(request.url))
        except Exception:
            pass
        return JSONResponse(content=content, status_code=exc.status_code)


    @application.exception_handler(Exception)
    @distributed_trace(inject_span=True)
    async def exception_handler(request: Request, exc, *, _span: Span = None):
        """

        :param request:
        :param exc:
        :param _span:
        :return:
        """
        if is_transient_asyncpg_connection_error(exc):
            await safe_rollback_session(get_request_session())
            content = transient_db_503_content(request, exc)
            try:
                _span.set_data("internal.exc_detail", content["detail"])
                _span.set_data("internal.exc_dev_info", content.get("debug_detail"))
                _span.set_data("internal.endpoint", str(request.url))
            except Exception:
                pass
            return JSONResponse(
                content=content, status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        content = defaultdict()
        content["detail"] = {"message": "Internal Server Error", "url": str(request.url)}
        if settings.is_dev:
            content["debug_detail"] = f"{exc.__class__.__name__}: {exc}"
        try:
            _span.set_data("internal.exc_detail", content["detail"])
            _span.set_data("internal.exc_dev_info", content["debug_detail"])
            _span.set_data("internal.endpoint", str(request.url))
        except Exception:
            pass
        return JSONResponse(
            content=content, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



def get_admin_application(container: Container) -> FastAPI:
    """
    get admin application
    :param container: Container instance from main application
    """
    admin_application = FastAPI(
        lifespan=lifespan,
        openapi_url="/api/openapi.json" if settings.is_dev else None,
        docs_url="/docs" if settings.is_dev else None,
        redoc_url="/redoc" if settings.is_dev else None,
    )
    admin_application.container = container
    register_middleware(application=admin_application)
    admin_application.include_router(admin_router, prefix="/api/v1")
    register_exception_handler(application=admin_application)

    return admin_application


def get_application() -> FastAPI:
    """
    get application
    """
    setup_tracing()
    application = FastAPI(
        lifespan=lifespan,
        openapi_url="/api/openapi.json",
    )

    # set container
    container = Container()
    application.container = container
    # Set global container for event publisher
    set_global_container(container)

    # init firebase
    try:
        init_firebase()
    except Exception as e:
        logger.error(f"Error initializing firebase: {e}")

    register_middleware(application=application)
    register_router(application=application)

    admin_app = get_admin_application(container=container)
    application.mount("/admin", admin_app)

    def custom_openapi():
        if not application.openapi_schema:
            openapi_schema = get_openapi(
                title=settings.APP_NAME.replace("-", " ").title().replace("Api", "API"),
                version=settings.APP_VERSION,
                summary="Conferences Portal API",
                description="API documentation for Conferences Portal",
                routes=application.routes,
            )
            component = openapi_schema.get("components", {})
            component["securitySchemes"] = SECURITY_SCHEMES
            openapi_schema["components"] = component
            application.openapi_schema = openapi_schema
        return application.openapi_schema

    application.openapi = custom_openapi

    register_exception_handler(application=application)

    return application


app = get_application()


@app.get("/")
async def root():
    """
    Root path redirects to /docs in development environment
    """
    if settings.is_dev:
        return RedirectResponse(url="/docs")
    return {"message": "Welcome to Conferences Portal API"}


# @app.exception_handler(InvalidAuthorizationToken)
# def on_invalid_token(
#     request: Request,
#     exc: InvalidAuthorizationToken
# ):
#     """
#
#     :param request:
#     :param exc:
#     :return:
#     """
#     return JSONResponse(
#         content={"detail": str(exc)},
#         status_code=status.HTTP_401_UNAUTHORIZED
#     )
