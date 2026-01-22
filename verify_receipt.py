import argparse
import copy
import hashlib
import json
import sys
from typing import Any, Dict, Tuple


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _load_receipt(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _verify(receipt: object) -> Tuple[bool, str]:
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
    actual_events_hash = _sha256_json(events)
    if expected_events_hash != actual_events_hash:
        return (
            False,
            f"events_sha256 mismatch (expected={expected_events_hash}, actual={actual_events_hash})",
        )

    expected_raw_hash = meta.get("raw_events_sha256")
    if not isinstance(expected_raw_hash, str):
        return False, "raw_events_sha256 is missing"
    actual_raw_hash = _sha256_json(raw_events)
    if expected_raw_hash != actual_raw_hash:
        return (
            False,
            f"raw_events_sha256 mismatch (expected={expected_raw_hash}, actual={actual_raw_hash})",
        )

    return True, "hashes match and structure is valid"


def _tamper(receipt: Dict[str, Any], mode: str) -> Dict[str, Any]:
    tampered = copy.deepcopy(receipt)
    if mode == "event":
        events = tampered.get("events")
        if isinstance(events, list) and events:
            if isinstance(events[0], dict):
                events[0]["tampered"] = True
            else:
                events[0] = f"{events[0]} [tampered]"
        else:
            tampered["events"] = [{"tampered": True}]
        return tampered
    if mode == "raw":
        raw_events = tampered.get("raw_events")
        if isinstance(raw_events, list) and raw_events:
            raw_events[0] = f"{raw_events[0]} "
        else:
            tampered["raw_events"] = ["tampered"]
        return tampered
    if mode == "meta":
        meta = tampered.setdefault("meta", {})
        if isinstance(meta, dict):
            meta["events_sha256"] = "tampered"
        return tampered
    raise ValueError(f"Unknown tamper mode: {mode}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal receipt verifier.")
    parser.add_argument("receipt", help="Path to receipt JSON file.")
    parser.add_argument(
        "--tamper",
        choices=["event", "raw", "meta"],
        help="Modify a field in-memory to demonstrate rejection.",
    )
    args = parser.parse_args()

    receipt = _load_receipt(args.receipt)
    if args.tamper:
        receipt = _tamper(receipt, args.tamper)

    ok, reason = _verify(receipt)
    verdict = "VERIFIED" if ok else "REJECTED"
    print(f"{verdict}: {reason}")
    print("Guarantees:")
    print("- Detects tampering for fields covered by stored hashes.")
    print("- Confirms basic structure and event counts.")
    print("Does not guarantee:")
    print("- Origin/authenticity (no signatures).")
    print("- That the model actually ran or output is correct.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
