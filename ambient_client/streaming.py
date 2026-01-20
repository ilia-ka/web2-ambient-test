import json
import time
from typing import Optional, Tuple

import requests


def stream_chat(
    api_url: str,
    api_key: str,
    prompt: str,
    model: str = "large",
) -> Optional[Tuple[str, float, float]]:
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
                content = None
                if isinstance(event, dict):
                    choices = event.get("choices")
                    if choices:
                        choice = choices[0]
                        delta = choice.get("delta") or choice.get("message") or {}
                        if isinstance(delta, dict):
                            content = delta.get("content")
                        elif isinstance(delta, str):
                            content = delta
                    if content is None:
                        content = event.get("content")
                if not content:
                    continue
                if first_token_at is None:
                    first_token_at = time.perf_counter()
                chunks.append(content)
                print(content, end="", flush=True)
    except requests.RequestException as exc:
        print(f"Error: {exc}")
        return None

    end = time.perf_counter()
    if first_token_at is None:
        first_token_at = end
    print()
    return "".join(chunks), first_token_at - start, end - start
