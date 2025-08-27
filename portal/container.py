"""
Container
"""
from dependency_injector import containers, providers

from portal.config import settings
from portal.handlers import (
    AccountHandler,
    ConferenceHandler,
    EventInfoHandler,
    FAQHandler,
    FCMDeviceHandler,
    FeedbackHandler,
    FileHandler,
    TestimonyHandler,
    WorkshopHandler,
)
from portal.libs.database import RedisPool, PostgresConnection, Session

if settings.IS_DEV:
    from portal.handlers import DemoHandler


# pylint: disable=too-few-public-methods,c-extension-no-member
class Container(containers.DeclarativeContainer):
    """Container"""

    wiring_config = containers.WiringConfiguration(
        modules=[],
        packages=["portal.handlers", "portal.routers"],
    )

    # [App Base]
    config = providers.Configuration()
    config.from_pydantic(settings)

    # [Database]
    redis_pool = providers.Singleton(RedisPool)
    postgres_connection = providers.Singleton(PostgresConnection)
    db_session = providers.Factory(Session, postgres_connection=postgres_connection)

    # [Handlers]
    if settings.IS_DEV:
        demo_handler = providers.Factory(
            DemoHandler,
            db_session=db_session
        )

    # [handlers]
    file_handler = providers.Factory(FileHandler)
    account_handler = providers.Factory(AccountHandler)
    conference_handler = providers.Factory(
        ConferenceHandler,
        file_handler=file_handler
    )
    event_info_handler = providers.Factory(EventInfoHandler)
    faq_handler = providers.Factory(FAQHandler)
    fcm_device_handler = providers.Factory(FCMDeviceHandler)
    feedback_handler = providers.Factory(FeedbackHandler)
    testimony_handler = providers.Factory(TestimonyHandler)
    workshop_handler = providers.Factory(
        WorkshopHandler,
        file_handler=file_handler
    )
