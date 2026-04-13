"""
Helpers to normalize audit payloads for JSONB and shallow field-level diffs.
"""
import dataclasses
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID


def normalize_for_audit_json(value: Any) -> Any:
    """
    Recursively convert values to JSON-serializable forms for portal_log JSONB.
    Unknown scalars fall back to str() to avoid breaking the audit pipeline.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return normalize_for_audit_json(value.value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): normalize_for_audit_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize_for_audit_json(v) for v in value]
    if isinstance(value, set):
        return [normalize_for_audit_json(v) for v in value]
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.hex()
    try:
        from pydantic import BaseModel

        if isinstance(value, BaseModel):
            return normalize_for_audit_json(value.model_dump(mode="json"))
    except ImportError:
        pass

    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return normalize_for_audit_json(dataclasses.asdict(value))
    return str(value)


def compute_changed_fields_shallow(
    old_data: dict[str, Any],
    new_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    First-level diff between two dicts (already normalized).
    Each entry: {"field": key, "old": ..., "new": ...} using None for missing side.
    """
    keys = set(old_data.keys()) | set(new_data.keys())
    out: list[dict[str, Any]] = []
    for key in sorted(keys):
        old_val: Optional[Any] = old_data[key] if key in old_data else None
        new_val: Optional[Any] = new_data[key] if key in new_data else None
        if old_val != new_val:
            out.append({"field": key, "old": old_val, "new": new_val})
    return out
