"""
main application
"""
from collections import defaultdict

import firebase_admin
import sentry_sdk
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse
from firebase_admin import credentials
from sentry_sdk.integrations.asyncpg import AsyncPGIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse

from fixtures import db_session
from portal.config import settings
from portal.container import Container
from portal.libs.database import Session
from portal.libs.utils.lifespan import lifespan
from portal.middlewares import DatabaseSessionMiddleware, RequestContextMiddleware
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
            DjangoIntegration(),
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
    # RequestContextMiddleware should come early to make contexts available to subsequent layers
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(DatabaseSessionMiddleware)
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
    application = FastAPI(lifespan=lifespan)
    # set route class
    # application.router.route_class = LogRouting
    # set container
    application.container = Container()

    # init firebase
    try:
        init_firebase()
    except Exception as e:
        print(f"Firebase init error: {e}")
    register_middleware(application=application)
    register_router(application=application)

    return application


app = get_application()


@app.get("/")
async def root():
    """
    Root path redirects to /docs in development environment
    """
    if settings.IS_DEV:
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
    container: Container = request.app.container
    db_session: Session = container.db_session()
    await db_session.rollback()
    return await http_exception_handler(request, exc)


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
    if settings.DEBUG:
        content["debug_detail"] = f"{exc.__class__.__name__}: {exc}"
    return JSONResponse(
        content=content,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
