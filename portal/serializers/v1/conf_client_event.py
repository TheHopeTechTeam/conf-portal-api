"""
Serializers for conf-frontend client telemetry (email link / app open flow).
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


ConfClientEventName = Literal[
    "finish_sign_in_mount",
    "email_link_shape_check",
    "redirect_to_app_start",
    "deep_link_fallback_https",
    "install_prompt_shown",
    "client_error",
]

ConfClientPlatform = Literal["ios", "android", "unknown"]

ConfClientDeepLinkKind = Literal["custom_scheme", "https_app_link", "none"]


class ConfClientLinkMeta(BaseModel):
    """
    Safe URL metadata only (no query values).
    """

    link_length: Optional[int] = Field(None, ge=0, le=100_000)
    link_host: Optional[str] = Field(None, max_length=253)
    query_key_names: Optional[list[str]] = Field(None, max_length=50)

    @field_validator("link_host")
    @classmethod
    def link_host_must_not_look_like_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if "://" in value or "/" in value or "?" in value:
            raise ValueError("link_host must be a hostname only")
        return value

    @field_validator("query_key_names")
    @classmethod
    def query_key_names_limited(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        if value is None:
            return value
        for name in value:
            if len(name) > 64:
                raise ValueError("query key name too long")
            if any(c in name for c in ["=", "&", "?", " "]):
                raise ValueError("invalid query key name")
        return value


class ConfClientEventCreate(BaseModel):
    """
    Ingest model for client-reported diagnostics (sanitized).
    """

    model_config = {"extra": "forbid"}

    event_name: ConfClientEventName
    source: Literal["conf-frontend"] = "conf-frontend"
    pathname: Optional[str] = Field(None, max_length=512)
    platform: Optional[ConfClientPlatform] = None
    is_sign_in_with_email_link: Optional[bool] = None
    is_in_app_browser: Optional[bool] = None
    has_react_native_webview: Optional[bool] = None
    deep_link_kind: Optional[ConfClientDeepLinkKind] = None
    link_meta: Optional[ConfClientLinkMeta] = None
    user_agent: Optional[str] = Field(None, max_length=512)
    client_timestamp_iso: Optional[str] = Field(None, max_length=64)
    error_code: Optional[str] = Field(None, max_length=64)
    error_message_short: Optional[str] = Field(None, max_length=200)

    @model_validator(mode="after")
    def reject_oob_like_strings(self) -> "ConfClientEventCreate":
        """
        Reject payloads that accidentally include sign-in link material.
        """
        blob = self.model_dump(mode="json", exclude_none=True)

        def scan(value: object) -> None:
            if isinstance(value, str):
                lowered = value.lower()
                if "oobcode=" in lowered or "&oobcode" in lowered:
                    raise ValueError("payload must not contain oobCode")
            elif isinstance(value, list):
                for item in value:
                    scan(item)
            elif isinstance(value, dict):
                for item in value.values():
                    scan(item)

        scan(blob)
        return self
