import json
import time
from typing import Optional, Tuple

import requests


def stream_gemini(
    api_url: str,
    api_key: str,
    prompt: str,
) -> Optional[Tuple[str, float, float]]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "x-goog-api-key": api_key,
    }
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
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
                candidates = event.get("candidates") if isinstance(event, dict) else None
                if not candidates:
                    continue
                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    text = part.get("text")
                    if not text:
                        continue
                    if first_token_at is None:
                        first_token_at = time.perf_counter()
                    chunks.append(text)
                    print(text, end="", flush=True)
    except requests.RequestException as exc:
        print(f"Error: {exc}")
        return None

    end = time.perf_counter()
    if first_token_at is None:
        first_token_at = end
    print()
    return "".join(chunks), first_token_at - start, end - start
