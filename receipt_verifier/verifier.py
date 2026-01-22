from typing import Any, Dict, Tuple

from receipt_verifier.hashes import sha256_json


def verify(receipt: object) -> Tuple[bool, str]:
    if not isinstance(receipt, dict):
        return False, "receipt is not a JSON object"
    meta = receipt.get("meta")
    events = receipt.get("events")
    raw_events = receipt.get("raw_events")
    if not isinstance(meta, dict):
        return False, "meta is missing or not an object"
    if not isinstance(events, list):
        return False, "events is missing or not a list"
    if not isinstance(raw_events, list):
        return False, "raw_events is missing or not a list"

    expected_count = meta.get("event_count")
    if expected_count is not None and expected_count != len(events):
        return False, f"event_count mismatch (meta={expected_count}, actual={len(events)})"
    expected_raw_count = meta.get("raw_event_count")
    if expected_raw_count is not None and expected_raw_count != len(raw_events):
        return False, (
            f"raw_event_count mismatch (meta={expected_raw_count}, "
            f"actual={len(raw_events)})"
        )

    expected_events_hash = meta.get("events_sha256")
    if not isinstance(expected_events_hash, str):
        return False, "events_sha256 is missing"
    actual_events_hash = sha256_json(events)
    if expected_events_hash != actual_events_hash:
        return (
            False,
            f"events_sha256 mismatch (expected={expected_events_hash}, "
            f"actual={actual_events_hash})",
        )

    expected_raw_hash = meta.get("raw_events_sha256")
    if not isinstance(expected_raw_hash, str):
        return False, "raw_events_sha256 is missing"
    actual_raw_hash = sha256_json(raw_events)
    if expected_raw_hash != actual_raw_hash:
        return (
            False,
            f"raw_events_sha256 mismatch (expected={expected_raw_hash}, "
            f"actual={actual_raw_hash})",
        )

    return True, "hashes match and structure is valid"
