from dataclasses import dataclass
import json
import sys
import time
from typing import Optional

import requests


@dataclass(frozen=True)
class StreamResult:
    text: str
    ttfb_seconds: float
    ttc_seconds: float


def _safe_write(text: str) -> None:
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        sys.stdout.buffer.write(text.encode(encoding, errors="replace"))
        sys.stdout.flush()


def _extract_content(event: object) -> Optional[str]:
    if not isinstance(event, dict):
        return None
    choices = event.get("choices")
    if choices:
        choice = choices[0]
        delta = choice.get("delta") or choice.get("message") or {}
        if isinstance(delta, dict):
            content = delta.get("content")
            if isinstance(content, str):
                return content
        elif isinstance(delta, str):
            return delta
    content = event.get("content")
    if isinstance(content, str):
        return content
    return None


def stream_chat(
    api_url: str,
    api_key: str,
    prompt: str,
    model: str = "zai-org/GLM-4.6",
) -> Optional[StreamResult]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }

    start = time.perf_counter()
    first_token_at = None
    chunks = []

    try:
        with requests.post(
            api_url,
            headers=headers,
            json=payload,
            stream=True,
            timeout=60,
        ) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                line = raw_line.strip()
                if not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                content = _extract_content(event)
                if not content:
                    continue
                if first_token_at is None:
                    first_token_at = time.perf_counter()
                chunks.append(content)
                _safe_write(content)
    except requests.RequestException as exc:
        print(f"Error: {exc}")
        return None

    end = time.perf_counter()
    if first_token_at is None:
        first_token_at = end
    _safe_write("\n")
    return StreamResult(
        text="".join(chunks),
        ttfb_seconds=first_token_at - start,
        ttc_seconds=end - start,
    )
