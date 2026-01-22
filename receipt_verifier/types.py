from typing import Any, List, TypedDict


class ReceiptMeta(TypedDict, total=False):
    api_url: str
    event_count: int
    events_sha256: str
    label: str
    model: str
    parse_errors: int
    prompt_sha256: str
    raw_event_count: int
    raw_events_sha256: str
    started_at: str
    ttc_seconds: float
    ttfb_seconds: float


class Receipt(TypedDict):
    meta: ReceiptMeta
    events: List[Any]
    raw_events: List[Any]
