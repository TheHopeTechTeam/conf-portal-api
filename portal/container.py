"""
Container
"""
from dependency_injector import containers, providers

from portal.config import settings
from portal.libs.database import RedisPool, PostgresConnection, Session
from portal.libs.database.session_proxy import SessionProxy
from portal.handlers import (
    AdminAuthHandler,
    AdminPermissionHandler,
    AdminResourceHandler,
    AdminRoleHandler,
    AdminUserHandler
)
from portal.providers.jwt_provider import JWTProvider
from portal.providers.password_provider import PasswordProvider
from portal.providers.token_blacklist_provider import TokenBlacklistProvider
from portal.providers.refresh_token_provider import RefreshTokenProvider

if settings.IS_DEV:
    from portal.handlers import DemoHandler


# pylint: disable=too-few-public-methods,c-extension-no-member
class Container(containers.DeclarativeContainer):
    """Container"""

    wiring_config = containers.WiringConfiguration(
        modules=[],
        packages=[
            "portal.handlers",
            "portal.routers"
        ],
    )

    # [App Base]
    config = providers.Configuration()
    config.from_pydantic(settings)

    # [Database]
    postgres_connection = providers.Singleton(PostgresConnection)
    # Real session factory (per-use); lifecycle is handled by middleware request context
    db_session = providers.Factory(Session, postgres_connection=postgres_connection)
    # Request-scoped session proxy that resolves to the ContextVar session
    request_session = providers.Factory(SessionProxy)

    # [Redis]
    redis_client = providers.Singleton(RedisPool)

    # [Providers]
    token_blacklist_provider = providers.Factory(
        TokenBlacklistProvider,
        redis_client=redis_client
    )

    jwt_provider = providers.Singleton(
        JWTProvider,
        token_blacklist_provider=token_blacklist_provider
    )
    password_provider = providers.Singleton(PasswordProvider)
    refresh_token_provider = providers.Factory(
        RefreshTokenProvider,
        session=db_session,
    )

    # [Handlers]
    if settings.IS_DEV:
        demo_handler = providers.Factory(
            DemoHandler,
            db_session=request_session
        )

    # [Admin]
    admin_permission_handler = providers.Factory(
        AdminPermissionHandler,
        session=request_session,
        redis_client=redis_client,
    )
    admin_resource_handler = providers.Factory(
        AdminResourceHandler,
        session=request_session,
        redis_client=redis_client,
    )
    admin_role_handler = providers.Factory(
        AdminRoleHandler,
        session=request_session,
        redis_client=redis_client,
    )
    admin_user_handler = providers.Factory(
        AdminUserHandler,
        session=request_session,
        redis_client=redis_client,
    )
    admin_auth_handler = providers.Factory(
        AdminAuthHandler,
        session=request_session,
        redis_client=redis_client,
        jwt_provider=jwt_provider,
        password_provider=password_provider,
        token_blacklist_provider=token_blacklist_provider,
        admin_permission_handler=admin_permission_handler,
        refresh_token_provider=refresh_token_provider,
        admin_role_handler=admin_role_handler,
        admin_user_handler=admin_user_handler,
    )

