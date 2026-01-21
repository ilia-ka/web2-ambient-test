import os

from ..config import get_config
from ..streaming import stream_chat
from .openai import get_openai_settings
from .prompt import load_prompt


def _run_stream(label: str, api_url: str, api_key: str, prompt: str, model: str) -> bool:
    print(f"{label} stream:")
    result = stream_chat(api_url, api_key, prompt, model)
    if not result:
        return False
    _, ttfb, ttc = result
    print(f"Time to first token: {ttfb * 1000:.0f} ms")
    print(f"Time to completion: {ttc * 1000:.0f} ms")
    return True


def run() -> None:
    config = get_config()
    if not config:
        return
    ambient_enabled, api_url, api_key = config
    prompt = load_prompt()
    if prompt is None:
        return
    model = os.getenv("AMBIENT_MODEL", "zai-org/GLM-4.6")

    ambient_ran = False
    if ambient_enabled:
        if not _run_stream("Ambient", api_url, api_key, prompt, model):
            return
        ambient_ran = True

    openai_settings = get_openai_settings()
    if openai_settings.enabled:
        if not openai_settings.api_key:
            print("Error: OPENAI_API_KEY is not set. Add it to .env or your environment.")
            return
        if ambient_ran:
            print("")
        _run_stream(
            "OpenAI",
            openai_settings.api_url,
            openai_settings.api_key,
            prompt,
            openai_settings.model,
        )
