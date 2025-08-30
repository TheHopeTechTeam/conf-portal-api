"""
Util functions for lifespan
"""
from contextlib import asynccontextmanager

from portal.config import settings
from fastapi import FastAPI
from fastapi_limiter import FastAPILimiter

from portal.libs.database import RedisPool
from portal.libs.logger import logger


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Lifespan
    :param _:
    """
    logger.info("Starting lifespan")
    if settings.REDIS_URL:
        try:
            redis_connection = RedisPool().create(db=1)
            await FastAPILimiter.init(
                redis=redis_connection,
                prefix=f"{settings.APP_NAME}_limiter"
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
