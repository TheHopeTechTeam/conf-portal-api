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
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse

from portal.config import settings
from portal.container import Container
from portal.exceptions.responses import ApiBaseException
from portal.libs.contexts.request_session_context import get_request_session
from portal.libs.logger import logger
from portal.libs.utils.lifespan import lifespan
from portal.middlewares import CoreRequestMiddleware
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
    :param application:
    :return:
    """
    application.add_middleware(CoreRequestMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_origin_regex=settings.CORS_ALLOW_ORIGINS_REGEX
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
        title=settings.APP_NAME.replace("-", " ").title().replace("Api", "API"),
        version=settings.APP_VERSION,
        summary="Conferences Portal API",
        description="API documentation for Conferences Portal",
    )

    # set container
    application.container = Container()

    # init firebase
    try:
        init_firebase()
    except Exception as e:
        logger.error(f"Error initializing firebase: {e}")
    register_middleware(application=application)
    register_router(application=application)

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
async def root_http_exception_handler(request, exc: HTTPException):
    """

    :param request:
    :param exc:
    :return:
    """
    session = get_request_session()
    if session is not None:
        await session.rollback()
    return await http_exception_handler(request, exc)


@app.exception_handler(ApiBaseException)
async def root_api_exception_handler(request, exc: ApiBaseException):
    """

    :param request:
    :param exc:
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
    return JSONResponse(
        content=content,
        status_code=exc.status_code
    )


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc):
    """

    :param request:
    :param exc:
    :return:
    """
    content = defaultdict()
    content["detail"] = {
        "message": "Internal Server Error",
        "url": str(request.url)
    }
    if settings.is_dev:
        content["debug_detail"] = f"{exc.__class__.__name__}: {exc}"
    return JSONResponse(
        content=content,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
