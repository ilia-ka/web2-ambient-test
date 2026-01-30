from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import requests

from shared.hashes import sha256_json

@dataclass(frozen=True)
class StreamResult:
    text: str
    ttfb_seconds: float
    ttc_seconds: float
    receipt_path: Optional[str] = None
    output_chars: int = 0
    content_chars: int = 0
    reasoning_chars: int = 0
    parse_errors: int = 0
    stall_count: int = 0
    stall_max_gap_seconds: float = 0.0
    usage: Optional[Dict[str, object]] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    started_at: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


def _safe_write(text: str) -> None:
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        sys.stdout.buffer.write(text.encode(encoding, errors="replace"))
        sys.stdout.flush()


def _extract_content_parts(event: object) -> Tuple[Optional[str], Optional[str]]:
    if not isinstance(event, dict):
        return None, None
    choices = event.get("choices")
    if choices:
        choice = choices[0]
        delta = choice.get("delta") or choice.get("message") or {}
        if isinstance(delta, dict):
            content = delta.get("content")
            reasoning = delta.get("reasoning_content")
            if isinstance(content, str) and content == "":
                content = None
            if isinstance(reasoning, str) and reasoning == "":
                reasoning = None
            return (
                content if isinstance(content, str) else None,
                reasoning if isinstance(reasoning, str) else None,
            )
        elif isinstance(delta, str):
            return delta, None
    content = event.get("content")
    if isinstance(content, str):
        return content, None
    return None, None


def _build_payload(
    model: str,
    prompt: str,
    request_params: Optional[Dict[str, object]],
) -> Dict[str, object]:
    payload: Dict[str, object] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }
    if request_params:
        for key, value in request_params.items():
            if value is not None:
                payload[key] = value
    return payload


def _select_emitted_text(
    content: Optional[str],
    reasoning: Optional[str],
    content_mode: str,
) -> Optional[str]:
    if content_mode == "content":
        return content
    if content_mode == "reasoning":
        return reasoning
    return content or reasoning


def _update_usage_from_event(
    event: object,
    usage: Optional[Dict[str, object]],
) -> Optional[Dict[str, object]]:
    if not isinstance(event, dict):
        return usage
    event_usage = event.get("usage")
    if isinstance(event_usage, dict):
        return event_usage
    choices = event.get("choices")
    if not choices:
        return usage
    choice = choices[0]
    if isinstance(choice, dict):
        choice_usage = choice.get("usage")
        if isinstance(choice_usage, dict):
            return choice_usage
    return usage


def _iter_sse_data(
    response: requests.Response,
    raw_events: Optional[List[str]],
) -> Iterable[str]:
    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        line = raw_line.strip()
        if not line.startswith("data:"):
            continue
        data = line[len("data:"):].strip()
        if raw_events is not None:
            raw_events.append(data)
        yield data


def _safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")


def _write_receipt(
    receipt_dir: Path,
    label: str,
    model: str,
    payload: Dict[str, object],
) -> Optional[str]:
    try:
        receipt_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        label_slug = _safe_slug(label) or "stream"
        model_slug = _safe_slug(model) or "model"
        path = receipt_dir / f"receipt_{timestamp}_{label_slug}_{model_slug}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        return str(path)
    except OSError as exc:
        print(f"Warning: Unable to write receipt: {exc}")
        return None


def stream_chat(
    api_url: str,
    api_key: str,
    prompt: str,
    model: str = "zai-org/GLM-4.6",
    receipt_dir: Optional[Path] = None,
    receipt_label: str = "",
    request_params: Optional[Dict[str, object]] = None,
    stall_threshold_seconds: Optional[float] = None,
    content_mode: str = "content_or_reasoning",
    output_handler: Optional[Callable[[str], None]] = None,
    error_handler: Optional[Callable[[str], None]] = None,
) -> StreamResult:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload = _build_payload(model, prompt, request_params)

    start = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    first_token_at = None
    last_token_at = None
    stall_count = 0
    stall_max_gap = 0.0
    chunks = []
    events: List[Dict[str, object]] = []
    raw_events: List[str] = []
    parse_errors = 0
    output_chars = 0
    usage: Optional[Dict[str, object]] = None
    status_code: Optional[int] = None
    content_chars = 0
    reasoning_chars = 0
    if receipt_dir is not None:
        receipt_dir = Path(receipt_dir)
    emit = output_handler or _safe_write
    emit_error = error_handler or (lambda msg: print(msg))

    try:
        with requests.post(
            api_url,
            headers=headers,
            json=payload,
            stream=True,
            timeout=60,
        ) as response:
            status_code = response.status_code
            response.raise_for_status()
            for data in _iter_sse_data(
                response,
                raw_events if receipt_dir is not None else None,
            ):
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    parse_errors += 1
                    continue
                if receipt_dir is not None and isinstance(event, dict):
                    events.append(event)
                usage = _update_usage_from_event(event, usage)
                content, reasoning = _extract_content_parts(event)
                if content:
                    content_chars += len(content)
                if reasoning:
                    reasoning_chars += len(reasoning)
                emitted_text = _select_emitted_text(content, reasoning, content_mode)
                if not emitted_text:
                    continue
                now = time.perf_counter()
                if first_token_at is None:
                    first_token_at = now
                if last_token_at is not None:
                    gap = now - last_token_at
                    if gap > stall_max_gap:
                        stall_max_gap = gap
                    if stall_threshold_seconds is not None and gap >= stall_threshold_seconds:
                        stall_count += 1
                last_token_at = now
                chunks.append(emitted_text)
                output_chars += len(emitted_text)
                emit(emitted_text)
    except requests.RequestException as exc:
        error = str(exc)
        response = getattr(exc, "response", None)
        if response is not None:
            status_code = response.status_code
        emit_error(f"Error: {error}")
        end = time.perf_counter()
        if first_token_at is None:
            first_token_at = end
        emit("\n")
        return StreamResult(
            text="".join(chunks),
            ttfb_seconds=first_token_at - start,
            ttc_seconds=end - start,
            receipt_path=None,
            output_chars=output_chars,
            content_chars=content_chars,
            reasoning_chars=reasoning_chars,
            parse_errors=parse_errors,
            stall_count=stall_count,
            stall_max_gap_seconds=stall_max_gap,
            usage=usage,
            error=error,
            status_code=status_code,
            started_at=started_at,
        )

    end = time.perf_counter()
    if first_token_at is None:
        first_token_at = end
    emit("\n")
    receipt_path = None
    if receipt_dir is not None:
        events_hash = sha256_json(events)
        raw_events_hash = sha256_json(raw_events)
        receipt_payload = {
            "meta": {
                "label": receipt_label or "stream",
                "model": model,
                "api_url": api_url,
                "started_at": started_at,
                "ttfb_seconds": first_token_at - start,
                "ttc_seconds": end - start,
                "event_count": len(events),
                "raw_event_count": len(raw_events),
                "parse_errors": parse_errors,
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "events_sha256": events_hash,
                "raw_events_sha256": raw_events_hash,
            },
            "events": events,
            "raw_events": raw_events,
        }
        receipt_path = _write_receipt(receipt_dir, receipt_label, model, receipt_payload)
    return StreamResult(
        text="".join(chunks),
        ttfb_seconds=first_token_at - start,
        ttc_seconds=end - start,
        receipt_path=receipt_path,
        output_chars=output_chars,
        content_chars=content_chars,
        reasoning_chars=reasoning_chars,
        parse_errors=parse_errors,
        stall_count=stall_count,
        stall_max_gap_seconds=stall_max_gap,
        usage=usage,
        status_code=status_code,
        started_at=started_at,
    )
