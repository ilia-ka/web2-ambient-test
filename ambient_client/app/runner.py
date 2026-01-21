import os

from ..config import get_config
from ..streaming import stream_chat
from .openai import get_openai_settings
from .openrouter import get_openrouter_settings
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
        if not openai_settings.models:
            print(
                "Error: No OpenAI models enabled. Set OPENAI_MODEL or OPENAI_MODELS "
                "and enable per-model flags if needed."
            )
            return
        for index, model in enumerate(openai_settings.models):
            if ambient_ran or index > 0:
                print("")
            if not _run_stream(
                f"OpenAI ({model})",
                openai_settings.api_url,
                openai_settings.api_key,
                prompt,
                model,
            ):
                return

    openrouter_settings = get_openrouter_settings()
    if openrouter_settings.enabled:
        if not openrouter_settings.api_key:
            print("Error: OPENROUTER_API is not set. Add it to .env or your environment.")
            return
        if not openrouter_settings.models:
            print(
                "Error: No OpenRouter models enabled. Set OPENROUTER_MODEL or "
                "OPENROUTER_MODELS and enable per-model flags if needed."
            )
            return
        for index, model in enumerate(openrouter_settings.models):
            if ambient_ran or openai_settings.enabled or index > 0:
                print("")
            if not _run_stream(
                f"OpenRouter ({model})",
                openrouter_settings.api_url,
                openrouter_settings.api_key,
                prompt,
                model,
            ):
                return
