from typing import Any, List, Tuple, cast

from receipt_verifier.result import VerificationResult
from receipt_verifier.types import Receipt, ReceiptMeta
from shared.hashes import sha256_json


def _check_counts(meta: ReceiptMeta, events: List[Any], raw_events: List[Any]) -> Tuple[bool, str]:
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


def _check_hash(meta: ReceiptMeta, key: str, payload: List[Any]) -> Tuple[bool, str, str, str]:
    expected = meta.get(key)
    if not isinstance(expected, str):
        return False, f"{key} is missing", "", ""
    actual = sha256_json(payload)
    if expected != actual:
        return False, f"{key} mismatch", expected, actual
    return True, "", expected, actual


def validate_schema(receipt: object) -> Tuple[bool, str, Receipt]:
    if not isinstance(receipt, dict):
        return False, "receipt is not a JSON object", {}
    meta = receipt.get("meta")
    events = receipt.get("events")
    raw_events = receipt.get("raw_events")
    if not isinstance(meta, dict):
        return False, "meta is missing or not an object", {}
    if not isinstance(events, list):
        return False, "events is missing or not a list", {}
    if not isinstance(raw_events, list):
        return False, "raw_events is missing or not a list", {}
    return True, "", cast(Receipt, receipt)


def verify_receipt(receipt: object) -> VerificationResult:
    ok, reason, parsed = validate_schema(receipt)
    if not ok:
        return VerificationResult(ok=False, reason=reason)

    meta = parsed["meta"]
    events = parsed["events"]
    raw_events = parsed["raw_events"]

    ok, reason = _check_counts(meta, events, raw_events)
    if not ok:
        return VerificationResult(ok=False, reason=reason)

    for key, payload in (("events_sha256", events), ("raw_events_sha256", raw_events)):
        ok, reason, expected, actual = _check_hash(meta, key, payload)
        if not ok:
            if expected and actual:
                return VerificationResult(
                    ok=False,
                    reason=reason,
                    expected=expected,
                    actual=actual,
                )
            return VerificationResult(ok=False, reason=reason)

    return VerificationResult(ok=True, reason="hashes match and structure is valid")
