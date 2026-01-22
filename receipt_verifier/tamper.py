import copy
from typing import Any, Dict


def tamper(receipt: Dict[str, Any], mode: str) -> Dict[str, Any]:
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
