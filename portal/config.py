"""
Configuration
"""
import os
from typing import Optional, Any, Type, Tuple

from dotenv import load_dotenv
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, EnvSettingsSource, PydanticBaseSettingsSource

from portal.libs.shared import Converter

load_dotenv()


class CustomSource(EnvSettingsSource):

    def prepare_field_value(
        self,
        field_name: str,
        field: FieldInfo,
        value: Any,
        value_is_complex: bool
    ) -> Any:
        """
        Prepare field value for custom source.
        :param field_name:
        :param field:
        :param value:
        :param value_is_complex:
        :return:
        """
        if field.annotation is bool:
            return Converter.to_bool(value, default=field.default or False)
        if field.annotation is list[str]:
            return [v for v in value.split(',')]
        return value


class Configuration(BaseSettings):
    """
    Configuration
    """

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (CustomSource(settings_cls),)

    # [App Base]
    APP_NAME: str = "conf-portal-api"
    ENV: str = os.getenv(key="ENV", default="dev").lower()
    DEBUG: bool = os.getenv(key="DEBUG", default=False)
    IS_PROD: bool = ENV == "prod"
    IS_DEV: bool = ENV not in ["prod", "stg"]
    APP_FQDN: str = os.getenv(key="APP_FQDN", default="localhost")
    BASE_URL: str = f"https://{APP_FQDN}" if not IS_DEV else f"http://{APP_FQDN}"  # noqa

    # [FastAPI]
    HOST: str = os.getenv(key="HOST", default="127.0.0.1")
    PORT: int = os.getenv(key="PORT", default=8000)

    # [CORS]
    CORS_ALLOWED_ORIGINS: list[str] = os.getenv(key="CORS_ALLOWED_ORIGINS", default="*").split()
    CORS_ALLOW_ORIGINS_REGEX: Optional[str] = os.getenv(key="CORS_ALLOW_ORIGINS_REGEX")

    # [Redis]
    REDIS_URL: Optional[str] = os.getenv(key="REDIS_URL")

    # [Database]
    DATABASE_HOST: str = os.getenv(key="DATABASE_HOST", default="localhost")
    DATABASE_USER: str = os.getenv(key="DATABASE_USER", default="postgres")
    DATABASE_PASSWORD: str = os.getenv(key="DATABASE_PASSWORD", default="")
    DATABASE_PORT: str = os.getenv(key="DATABASE_PORT", default="5432")
    DATABASE_NAME: str = os.getenv(key="DATABASE_NAME", default="postgres")
    DATABASE_SCHEMA: str = os.getenv(key="DATABASE_SCHEMA", default="public")
    DATABASE_CONNECTION_POOL_MAX_SIZE: int = os.getenv("DATABASE_CONNECTION_POOL_MAX_SIZE", 10)
    DATABASE_APPLICATION_NAME: str = APP_NAME
    DATABASE_POOL: bool = os.getenv("DATABASE_POOL", True)
    SQL_ECHO: bool = os.getenv("SQL_ECHO", False)
    SQLALCHEMY_DATABASE_URI: str = f'postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}'
    ASYNC_DATABASE_URL: str = f'postgresql+asyncpg://{DATABASE_USER}:{DATABASE_PASSWORD}@' \
                              f'{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}'

    # [Sentry]
    SENTRY_URL: Optional[str] = os.getenv(key="SENTRY_URL")


settings: Configuration = Configuration()
