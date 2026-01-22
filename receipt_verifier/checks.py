from typing import Any, Dict, List, Tuple

from receipt_verifier.hashes import sha256_json


def _require_dict(value: object, name: str) -> Tuple[bool, str, Dict[str, Any]]:
    if not isinstance(value, dict):
        return False, f"{name} is missing or not an object", {}
    return True, "", value


def _require_list(value: object, name: str) -> Tuple[bool, str, List[Any]]:
    if not isinstance(value, list):
        return False, f"{name} is missing or not a list", []
    return True, "", value


def _check_counts(meta: Dict[str, Any], events: List[Any], raw_events: List[Any]) -> Tuple[bool, str]:
    expected_count = meta.get("event_count")
    if expected_count is not None and expected_count != len(events):
        return False, f"event_count mismatch (meta={expected_count}, actual={len(events)})"
    expected_raw_count = meta.get("raw_event_count")
    if expected_raw_count is not None and expected_raw_count != len(raw_events):
        return False, (
            f"raw_event_count mismatch (meta={expected_raw_count}, "
            f"actual={len(raw_events)})"
        )
    return True, ""


def _check_hash(meta: Dict[str, Any], key: str, payload: List[Any]) -> Tuple[bool, str]:
    expected = meta.get(key)
    if not isinstance(expected, str):
        return False, f"{key} is missing"
    actual = sha256_json(payload)
    if expected != actual:
        return False, f"{key} mismatch (expected={expected}, actual={actual})"
    return True, ""


def verify_receipt(receipt: object) -> Tuple[bool, str]:
    ok, reason, receipt_dict = _require_dict(receipt, "receipt")
    if not ok:
        return False, reason

    ok, reason, meta = _require_dict(receipt_dict.get("meta"), "meta")
    if not ok:
        return False, reason
    ok, reason, events = _require_list(receipt_dict.get("events"), "events")
    if not ok:
        return False, reason
    ok, reason, raw_events = _require_list(receipt_dict.get("raw_events"), "raw_events")
    if not ok:
        return False, reason

    ok, reason = _check_counts(meta, events, raw_events)
    if not ok:
        return False, reason

    ok, reason = _check_hash(meta, "events_sha256", events)
    if not ok:
        return False, reason
    ok, reason = _check_hash(meta, "raw_events_sha256", raw_events)
    if not ok:
        return False, reason

    return True, "hashes match and structure is valid"
