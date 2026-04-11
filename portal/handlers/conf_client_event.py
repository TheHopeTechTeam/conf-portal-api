"""
Handler for conf-frontend client telemetry ingestion.
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

import ujson
from pydantic import ValidationError

from portal.libs.contexts.request_context import get_request_context, RequestContext
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.logger import logger
from portal.providers.firebase.base import FirebaseProvider
from portal.serializers.v1.conf_client_event import ConfClientEventCreate


class ConfClientEventHandler:
    """
    Accepts sanitized client diagnostics; always completes without raising to the client.
    """

    def __init__(self, firebase_provider: FirebaseProvider):
        self._firebase_provider = firebase_provider
        self._req_ctx: Optional[RequestContext] = get_request_context()

    @distributed_trace()
    async def ingest(self, raw_body: bytes) -> dict[str, bool]:
        try:
            if not raw_body:
                logger.warning("conf_client_event empty_body")
                return {"accepted": True}
            try:
                parsed = ujson.loads(raw_body)
            except (ValueError, TypeError, OverflowError) as exc:
                logger.warning("conf_client_event json_parse_failed", extra={"error": str(exc)})
                return {"accepted": True}

            if not isinstance(parsed, dict):
                logger.warning("conf_client_event body_not_object")
                return {"accepted": True}

            try:
                model = ConfClientEventCreate.model_validate(parsed)
            except ValidationError as exc:
                logger.warning(
                    "conf_client_event validation_failed",
                    extra={"errors": exc.errors()},
                )
                return {"accepted": True}

            document: dict[str, Any] = model.model_dump(mode="json", exclude_none=True)
            document["server_received_at"] = datetime.now(timezone.utc).isoformat()
            if self._req_ctx:
                raw = self._req_ctx.ip or self._req_ctx.client_ip or ""
                document["client_host"] = raw[:128]

            try:
                await asyncio.to_thread(
                    self._firebase_provider.write_conf_client_event_document,
                    document,
                )
            except Exception as exc:
                logger.exception(f"conf_client_event firestore_write_failed: {exc}")
            return {"accepted": True}
        except Exception as exc:
            logger.exception(f"conf_client_event unexpected_failure: {exc}")
            return {"accepted": True}
