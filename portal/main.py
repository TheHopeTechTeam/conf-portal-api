"""
main application
"""

from collections import defaultdict

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
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.logger import logger
from portal.libs.events.publisher import set_global_container
from portal.libs.utils.lifespan import lifespan
from portal.middlewares import CoreRequestMiddleware, AuthMiddleware
from portal.routers import api_router

__all__ = ["app"]


def setup_tracing():
    """
    Setup tracing
    :return:
    """
    if not settings.SENTRY_URL:
        return
    sentry_sdk.init(
        dsn=settings.SENTRY_URL,
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
    1. CORSMiddleware - Handle CORS (outermost, executed last)
    2. CoreRequestMiddleware - Setup request context and database session
    3. AuthMiddleware - Verify token and set UserContext (innermost, executed first)

    Note: AuthMiddleware executes after CoreRequestMiddleware to ensure database session is available.
    Both authentication (token verification) and authorization (permission checking) are handled in AuthMiddleware.
    No dependency injection is used for auth logic.
    :param application:
    :return:
    """
    # CORS middleware should be outermost (added first, executed last)
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


def init_firebase():
    """
    init firebase
    :return:
    """
    credential = credentials.Certificate(settings.GOOGLE_FIREBASE_CERTIFICATE)
    firebase_admin.initialize_app(
        credential=credential,
        # options={
        #     "storageBucket": settings.FIREBASE_STORAGE_BUCKET
        # }
    )


def get_application() -> FastAPI:
    """
    get application
    """
    setup_tracing()
    application = FastAPI(
        lifespan=lifespan,
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


@app.exception_handler(HTTPException)
@distributed_trace(inject_span=True)
async def root_http_exception_handler(request, exc: HTTPException, _span: Span = None):
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


@app.exception_handler(ApiBaseException)
@distributed_trace(inject_span=True)
async def root_api_exception_handler(
    request, exc: ApiBaseException, _span: Span = None
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


@app.exception_handler(Exception)
@distributed_trace(inject_span=True)
async def exception_handler(request: Request, exc, _span: Span = None):
    """

    :param request:
    :param exc:
    :param _span:
    :return:
    """
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
