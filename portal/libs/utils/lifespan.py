"""
Util functions for lifespan
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi_limiter import FastAPILimiter

from portal.config import settings
from portal.container import Container
from portal.libs.database import RedisPool
from portal.libs.events.publisher import publish_event_in_background
from portal.libs.events.types import TicketTypeSyncEvent
from portal.libs.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan
    :param app:
    """
    logger.info("Starting lifespan")

    # Register event handlers
    if hasattr(app, "container"):
        try:
            container = app.container
            event_bus = container.event_bus()
            logger.info("-" * 100)
            Container.register_event_handlers(event_bus, container)
            logger.info("Event handlers registered")
            logger.info("-" * 100)
            # Sync ticket types from ticket system on startup (fire-and-forget)
            publish_event_in_background(TicketTypeSyncEvent())
            logger.info("Ticket type sync event published on startup")
        except Exception as e:
            logger.warning("Failed to register event handlers: %s", e)

    if settings.REDIS_URL:
        try:
            redis_connection = RedisPool().create(db=1)
            await FastAPILimiter.init(
                redis=redis_connection, prefix=f"{settings.APP_NAME}_limiter"
            )
            logger.info("FastAPILimiter initialized")
        except Exception as e:
            logger.error(f"Failed to initialize FastAPILimiter: {e}")
        else:
            yield
            await FastAPILimiter.close()
            await redis_connection.close()
        finally:
            logger.info("Lifespan finished")
    else:
        yield
