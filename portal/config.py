"""
Configuration
"""
import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional, Any, Type, Tuple

import yaml
from dotenv import load_dotenv
from google.oauth2 import service_account
from pydantic import model_validator
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, EnvSettingsSource, PydanticBaseSettingsSource

from portal.libs.shared import Converter
from portal.schemas.rate_limiter import RateLimitersConfig

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
        if isinstance(list[str], type(field.annotation)):
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
    APP_VERSION: str = os.getenv(key="VERSION", default="v0.1.0")
    IS_PROD: bool = ENV == "prod"
    IS_DEV: bool = ENV not in ["prod", "stg"]
    APP_FQDN: str = os.getenv(key="APP_FQDN", default="localhost")
    BASE_URL: str = f"https://{APP_FQDN}" if not IS_DEV else f"http://{APP_FQDN}"  # noqa
    ADMIN_PORTAL_URL: str = os.getenv(key="ADMIN_PORTAL_URL", default="http://localhost:5173")

    # [FastAPI]
    HOST: str = os.getenv(key="HOST", default="127.0.0.1")
    PORT: int = os.getenv(key="PORT", default=8000)

    # [CORS]
    CORS_ALLOWED_ORIGINS: list[str] = os.getenv(key="CORS_ALLOWED_ORIGINS", default="*").split()
    CORS_ALLOW_ORIGINS_REGEX: Optional[str] = os.getenv(key="CORS_ALLOW_ORIGINS_REGEX")

    # [AWS]
    AWS_STORAGE_BUCKET_NAME: str = APP_NAME
    AWS_ACCESS_KEY_ID: str = os.getenv(key="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = os.getenv(key="AWS_SECRET_ACCESS_KEY")
    AWS_S3_REGION_NAME: str = os.getenv(key="AWS_S3_REGION_NAME")
    AWS_S3_CACHE_CONTROL: str = os.getenv(key="AWS_S3_CACHE_CONTROL", default="max-age=86400")
    MAX_UPLOAD_SIZE: int = int(os.getenv(key="MAX_UPLOAD_SIZE", default=5 * 1024 * 1024))  # 3MB

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
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv(key="JWT_ACCESS_TOKEN_EXPIRE_MINUTES", default="15"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv(key="REFRESH_TOKEN_EXPIRE_DAYS", default="7"))
    REFRESH_TOKEN_HASH_SALT: str = os.getenv(key="REFRESH_TOKEN_HASH_SALT", default="")
    REFRESH_TOKEN_HASH_PEPPER: str = os.getenv(key="REFRESH_TOKEN_HASH_PEPPER", default="")

    # [Password Reset]
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = int(os.getenv(key="PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", default="60"))
    PASSWORD_RESET_TOKEN_SALT: str = os.getenv(key="PASSWORD_RESET_TOKEN_SALT", default="")

    # [Check-in Token]
    CHECK_IN_TOKEN_EXPIRE_SECONDS: int = int(os.getenv(key="CHECK_IN_TOKEN_EXPIRE_SECONDS", default="30"))

    # [Token Blacklist]
    TOKEN_BLACKLIST_REDIS_DB: int = int(os.getenv(key="TOKEN_BLACKLIST_REDIS_DB", default="1"))
    TOKEN_BLACKLIST_CLEANUP_INTERVAL: int = int(os.getenv(key="TOKEN_BLACKLIST_CLEANUP_INTERVAL", default="3600"))

    # [Rate Limiting]
    # 限流器配置從 YAML 檔案載入，見 _load_rate_limiters_config 方法
    RATE_LIMITERS_CONFIG: Optional[RateLimitersConfig] = None

    # [Sentry]
    SENTRY_URL: Optional[str] = os.getenv(key="SENTRY_URL")

    # [Firebase]
    FIREBASE_TEST_PHONE_NUMBER: str = os.getenv(key="FIREBASE_TEST_PHONE_NUMBER")

    # [Gmail SMTP]
    SMTP_HOST: str = os.getenv(key="SMTP_HOST")
    SMTP_PORT: int = int(os.getenv(key="SMTP_PORT", default="587"))
    SMTP_USER: str = os.getenv(key="SMTP_USER")
    SMTP_PASSWORD: str = os.getenv(key="SMTP_PASSWORD")
    SMTP_FROM_EMAIL: str = os.getenv(key="SMTP_FROM_EMAIL")

    # [Google Cloud]
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = os.getenv(
        key="GOOGLE_APPLICATION_CREDENTIALS"
    )
    GS_CREDENTIALS: Optional[service_account.Credentials] = None
    GOOGLE_FIREBASE_CERTIFICATE: dict = {}

    # [Logging]
    SENSITIVE_PARAMS: set[str] = set(os.getenv(key="SENSITIVE_PARAMS", default="password,secret,api_key").split(","))

    # [Notification]
    ENABLE_PUSH_NOTIFICATION: bool = os.getenv(key="ENABLE_PUSH_NOTIFICATION", default=True)

    # [The Hope Ticket System]
    THEHOPE_TICKET_SYSTEM_URL: str = os.getenv(key="THE_HOPE_TICKET_SYSTEM_URL")
    THEHOPE_TICKET_SYSTEM_API_KEY: str = os.getenv(key="THE_HOPE_TICKET_SYSTEM_API_KEY")


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
        project_dir = Path(__file__).resolve().parent.parent
        candidate_paths.extend(
            [
                os.path.join(project_dir, "env/google_certificate.json"),
                "/etc/secrets/google_certificate.json",
            ]
        )

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

    @model_validator(mode="after")
    def _load_rate_limiters_config(self) -> "Configuration":
        """
        Load rate limiters configuration from the YAML file, in order:
        1) RATE_LIMITERS_CONFIG_PATH env var (if provided)
        2) env/rate_limiters.yaml
        3) /etc/secrets/rate_limiters.yaml
        """
        if self.RATE_LIMITERS_CONFIG:
            return self

        candidate_paths: list[str] = []
        rate_limiters_config_path = os.getenv(key="RATE_LIMITERS_CONFIG_PATH")
        if rate_limiters_config_path:
            candidate_paths.append(rate_limiters_config_path)

        project_dir = Path(__file__).resolve().parent.parent
        candidate_paths.extend(
            [
                os.path.join(project_dir, "env/rate_limiters.yaml"),
                "/etc/secrets/rate_limiters.yaml",
            ]
        )

        for candidate_path in candidate_paths:
            try:
                rate_limiters_path: Path = Path(candidate_path)
                if rate_limiters_path.exists():
                    config_dict = yaml.safe_load(rate_limiters_path.read_text())
                    self.RATE_LIMITERS_CONFIG = RateLimitersConfig(**config_dict)
                    logger = logging.getLogger(self.APP_NAME)
                    logger.info(f"Rate limiters config loaded from {candidate_path}")
                    break
            except FileNotFoundError:
                continue
            except Exception as exc:
                logger = logging.getLogger(self.APP_NAME)
                logger.warning(f"Failed to load rate limiters config from {candidate_path}: {exc}")

        # 如果沒有載入到配置，使用預設值
        if not self.RATE_LIMITERS_CONFIG:
            logger = logging.getLogger(self.APP_NAME)
            logger.warning("Rate limiters config not found, using default values")
            default_config_dict = {
                "default": {
                    "short": {"times": 10, "seconds": 1},
                    "medium": {"times": 50, "seconds": 30},
                    "long": {"times": 1000, "seconds": 3600},
                },
                "read": {
                    "short": {"times": 20, "seconds": 1},
                    "medium": {"times": 100, "seconds": 30},
                    "long": {"times": 1800, "seconds": 3600},
                },
                "write": {
                    "short": {"times": 10, "seconds": 1},
                    "medium": {"times": 60, "seconds": 30},
                    "long": {"times": 1200, "seconds": 3600},
                }
            }
            self.RATE_LIMITERS_CONFIG = RateLimitersConfig(**default_config_dict)

        return self

    @property
    def is_prod(self) -> bool:
        return self.ENV.lower() == "prod"

    @property
    def is_dev(self) -> bool:
        return self.ENV.lower() not in ("prod", "stg")


@lru_cache()
def get_settings() -> Configuration:
    return Configuration()


settings: Configuration = get_settings()
