"""
Tests for audit log payload normalization and shallow diff.
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel

from portal.libs.consts.enums import OperationType
from portal.libs.utils.audit_log_payload import (
    compute_changed_fields_shallow,
    normalize_for_audit_json,
)


class _Color(Enum):
    RED = "red"
    BLUE = "blue"


def test_normalize_primitives_unchanged():
    assert normalize_for_audit_json(None) is None
    assert normalize_for_audit_json(True) is True
    assert normalize_for_audit_json(42) == 42
    assert normalize_for_audit_json("x") == "x"


def test_normalize_uuid_datetime_decimal_enum():
    uid = uuid.uuid4()
    dt = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    d = date(2026, 4, 13)
    assert normalize_for_audit_json(uid) == str(uid)
    assert normalize_for_audit_json(dt) == dt.isoformat()
    assert normalize_for_audit_json(d) == d.isoformat()
    assert normalize_for_audit_json(Decimal("1.25")) == "1.25"
    assert normalize_for_audit_json(OperationType.UPDATE) == "update"
    assert normalize_for_audit_json(_Color.RED) == "red"


def test_normalize_nested_dict_and_collections():
    uid = uuid.uuid4()
    raw = {
        "id": uid,
        "tags": {"a", "b"},
        "items": [{"n": 1}],
    }
    out = normalize_for_audit_json(raw)
    assert out["id"] == str(uid)
    assert sorted(out["tags"]) == ["a", "b"]
    assert out["items"] == [{"n": 1}]


def test_normalize_bytes_utf8():
    assert normalize_for_audit_json(b"hello") == "hello"


def test_normalize_pydantic_model():
    class _M(BaseModel):
        name: str
        count: int

    assert normalize_for_audit_json(_M(name="x", count=2)) == {"name": "x", "count": 2}


def test_normalize_unknown_scalar_to_str():
    class _Thing:
        def __str__(self):
            return "thing"

    assert normalize_for_audit_json(_Thing()) == "thing"


def test_compute_changed_fields_shallow_add_change_remove():
    old = {"a": 1, "b": 2}
    new = {"a": 1, "b": 3, "c": 4}
    diff = compute_changed_fields_shallow(old, new)
    assert diff == [
        {"field": "b", "old": 2, "new": 3},
        {"field": "c", "old": None, "new": 4},
    ]


def test_compute_changed_fields_shallow_no_change():
    old = {"x": 1}
    new = {"x": 1}
    assert compute_changed_fields_shallow(old, new) == []


def test_compute_changed_fields_shallow_sorted_keys_stable_order():
    old = {"z": 1, "a": 2}
    new = {"z": 2, "a": 2}
    diff = compute_changed_fields_shallow(old, new)
    assert [d["field"] for d in diff] == ["z"]
