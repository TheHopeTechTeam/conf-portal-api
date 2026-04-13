"""
AdminLogHandler
"""
from typing import Any, Optional
from uuid import UUID

from portal.libs.consts.enums import OperationType
from portal.libs.contexts.request_context import get_request_context
from portal.libs.contexts.user_context import get_user_context
from portal.libs.decorators.sentry_tracer import distributed_trace
from portal.libs.events.publisher import publish_event_in_background
from portal.libs.events.types import AdminOperationLogEvent
from portal.libs.logger import logger
from portal.libs.utils.audit_log_payload import (
    compute_changed_fields_shallow,
    normalize_for_audit_json,
)


class AdminLogHandler:
    """AdminLogHandler"""

    @distributed_trace()
    def create_log(
        self,
        operation_type: OperationType,
        record_id: Optional[UUID] = None,
        operation_code: Optional[str] = None,
        old_data: Optional[dict[str, Any]] = None,
        new_data: Optional[dict[str, Any]] = None,
        changed_fields: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        """
        Create an operation log (schedules AdminOperationLogEvent in the background).
        Client IP and user agent are taken from request context when set by middleware.
        Any unexpected error is logged and suppressed so callers are not interrupted.
        :param operation_type:
        :param record_id:
        :param operation_code:
        :param old_data:
        :param new_data:
        :param changed_fields: When omitted and both old_data and new_data are dicts,
            values are normalized for JSONB and changed_fields is computed (shallow diff).
        :return:
        """
        try:
            resolved_old_data = old_data
            resolved_new_data = new_data
            resolved_changed_fields = changed_fields
            if (
                changed_fields is None
                and isinstance(old_data, dict)
                and isinstance(new_data, dict)
            ):
                try:
                    resolved_old_data = normalize_for_audit_json(old_data)
                    resolved_new_data = normalize_for_audit_json(new_data)
                    if isinstance(resolved_old_data, dict) and isinstance(resolved_new_data, dict):
                        resolved_changed_fields = compute_changed_fields_shallow(
                            resolved_old_data,
                            resolved_new_data,
                        )
                    else:
                        resolved_old_data = old_data
                        resolved_new_data = new_data
                        resolved_changed_fields = None
                        logger.warning(
                            "audit_log_payload normalize did not return dict for old/new; "
                            "falling back to raw payloads without changed_fields"
                        )
                except Exception:
                    resolved_old_data = old_data
                    resolved_new_data = new_data
                    resolved_changed_fields = None
                    logger.exception(
                        "audit_log_payload normalize or diff failed; "
                        "falling back to raw payloads without changed_fields"
                    )
            user_ctx = get_user_context()
            created_by = user_ctx.username if user_ctx and user_ctx.username else None
            created_by_id = user_ctx.user_id if user_ctx and user_ctx.user_id else None
            req_ctx = get_request_context()
            ip_address = None
            user_agent = None
            if req_ctx:
                ip_address = req_ctx.ip or req_ctx.client_ip
                user_agent = req_ctx.user_agent
            publish_event_in_background(
                event=AdminOperationLogEvent(
                    operation_type=operation_type,
                    record_id=record_id,
                    operation_code=operation_code,
                    old_data=resolved_old_data,
                    new_data=resolved_new_data,
                    changed_fields=resolved_changed_fields,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    created_by=created_by,
                    created_by_id=created_by_id,
                )
            )
        except Exception as e:
            logger.warning(f"AdminLogHandler.create_log failed: {e}")
