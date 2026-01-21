from typing import Tuple

from ..config import load_env_file
from ..streaming import stream_chat
from .ambient import get_ambient_settings
from .openai import get_openai_settings
from .openrouter import get_openrouter_settings
from .prompt import load_prompt
from .provider_utils import ProviderSettings


def _run_stream(label: str, api_url: str, api_key: str, prompt: str, model: str) -> bool:
    print(f"{label} stream:")
    result = stream_chat(api_url, api_key, prompt, model)
    if not result:
        return False
    _, ttfb, ttc = result
    print(f"Time to first token: {ttfb * 1000:.0f} ms")
    print(f"Time to completion: {ttc * 1000:.0f} ms")
    return True


def _run_provider(settings: ProviderSettings, prompt: str, had_output: bool) -> Tuple[bool, bool]:
    if not settings.enabled:
        return True, had_output
    if not settings.api_key:
        print(
            f"Error: {settings.key_env_hint} is not set. Add it to .env or your environment."
        )
        return False, had_output
    if not settings.models:
        print(
            f"Error: No {settings.name} models enabled. Set {settings.model_env_hint} "
            "and enable per-model flags if needed."
        )
        return False, had_output
    for model in settings.models:
        if had_output:
            print("")
        if not _run_stream(
            f"{settings.name} ({model})",
            settings.api_url,
            settings.api_key,
            prompt,
            model,
        ):
            return False, had_output
        had_output = True
    return True, had_output


def run() -> None:
    load_env_file()
    prompt = load_prompt()
    if prompt is None:
        return

    had_output = False
    for settings in (
        get_ambient_settings(),
        get_openai_settings(),
        get_openrouter_settings(),
    ):
        success, had_output = _run_provider(settings, prompt, had_output)
        if not success:
            return
