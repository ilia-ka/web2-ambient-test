import os
from pathlib import Path

from ambient_client.config import get_config
from ambient_client.gemini_streaming import stream_gemini
from ambient_client.streaming import stream_chat


def main() -> None:
    config = get_config()
    if not config:
        return
    api_url, api_key = config
    prompt_file = os.getenv("AMBIENT_PROMPT_FILE", "").strip()
    if prompt_file:
        try:
            prompt = Path(prompt_file).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"Error: Unable to read AMBIENT_PROMPT_FILE '{prompt_file}': {exc}")
            return
    else:
        prompt = os.getenv("AMBIENT_PROMPT", "What is Ambient Network on Solana?")
    model = os.getenv("AMBIENT_MODEL", "large")

    print("Ambient stream:")
    result = stream_chat(api_url, api_key, prompt, model)
    if not result:
        return
    _, ttfb, ttc = result
    print(f"Time to first token: {ttfb * 1000:.0f} ms")
    print(f"Time to completion: {ttc * 1000:.0f} ms")

    closed_url = os.getenv("CLOSED_API_URL")
    closed_key = os.getenv("CLOSED_API_KEY")
    closed_provider = os.getenv("CLOSED_API_PROVIDER", "").strip().lower()
    if closed_key and (closed_url or closed_provider == "gemini"):
        closed_model = os.getenv("CLOSED_API_MODEL", model)
        print("\nClosed API stream:")
        if closed_provider == "gemini":
            closed_url = (
                closed_url
                or "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{closed_model}:streamGenerateContent?alt=sse"
            )
            closed_result = stream_gemini(closed_url, closed_key, prompt)
        else:
            closed_result = stream_chat(closed_url, closed_key, prompt, closed_model)
        if not closed_result:
            return
        _, closed_ttfb, closed_ttc = closed_result
        print(f"Time to first token: {closed_ttfb * 1000:.0f} ms")
        print(f"Time to completion: {closed_ttc * 1000:.0f} ms")


if __name__ == "__main__":
    main()
