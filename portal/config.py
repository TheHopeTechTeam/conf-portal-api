"""
Configuration
"""
import json
import logging
import os
from pathlib import PosixPath, Path
from typing import Optional, Any, Type, Tuple

from dotenv import load_dotenv
from google.oauth2 import service_account
from pydantic import field_validator, model_validator
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
    REDIS_DB: int = int(os.getenv(key="REDIS_DB", default="0"))

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

    # [JWT]
    JWT_SECRET_KEY: str = os.getenv(key="JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv(key="JWT_ACCESS_TOKEN_EXPIRE_MINUTES", default="60"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv(key="REFRESH_TOKEN_EXPIRE_DAYS", default="7"))
    REFRESH_TOKEN_HASH_SALT: str = os.getenv(key="REFRESH_TOKEN_HASH_SALT", default="")
    REFRESH_TOKEN_HASH_PEPPER: str = os.getenv(key="REFRESH_TOKEN_HASH_PEPPER", default="")

    # [Token Blacklist]
    TOKEN_BLACKLIST_REDIS_DB: int = int(os.getenv(key="TOKEN_BLACKLIST_REDIS_DB", default="1"))
    TOKEN_BLACKLIST_CLEANUP_INTERVAL: int = int(os.getenv(key="TOKEN_BLACKLIST_CLEANUP_INTERVAL", default="3600"))

    # [Sentry]
    SENTRY_URL: Optional[str] = os.getenv(key="SENTRY_URL")

    # [Firebase]
    FIREBASE_TEST_PHONE_NUMBER: str = os.getenv(key="FIREBASE_TEST_PHONE_NUMBER")

    # [Google Cloud]
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = os.getenv(
        key="GOOGLE_APPLICATION_CREDENTIALS"
    )
    GS_CREDENTIALS: Optional[service_account.Credentials] = None
    GOOGLE_FIREBASE_CERTIFICATE: dict = {}

    @model_validator(mode="after")
    def _load_google_cloud_credentials(self) -> "Configuration":
        """
        Load Google Cloud credentials and Firebase certificate from, in order:
        1) GOOGLE_APPLICATION_CREDENTIALS env var (if provided)
        2) env/google_certificate.json
        3) /etc/secrets/google_certificate.json
        """
        if self.GS_CREDENTIALS is not None and self.GOOGLE_FIREBASE_CERTIFICATE:
            return self

        candidate_paths: list[str] = []
        if self.GOOGLE_APPLICATION_CREDENTIALS:
            candidate_paths.append(self.GOOGLE_APPLICATION_CREDENTIALS)
        candidate_paths.extend([
            "env/google_certificate.json",
            "/etc/secrets/google_certificate.json",
        ])

        for candidate_path in candidate_paths:
            try:
                google_certificate_path: Path = Path(candidate_path)
                credentials = service_account.Credentials.from_service_account_file(
                    candidate_path
                )
                certificate_dict: dict = json.loads(google_certificate_path.read_text())
                self.GS_CREDENTIALS = credentials
                self.GOOGLE_FIREBASE_CERTIFICATE = certificate_dict
                break
            except FileNotFoundError:
                continue
            except Exception as exc:
                logger = logging.getLogger(self.APP_NAME)
                logger.warning(f"Failed to load Google Firebase certificate from {candidate_path}: {exc}")

        return self


settings: Configuration = Configuration()
