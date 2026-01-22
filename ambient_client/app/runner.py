import os
from pathlib import Path
from typing import Optional, Tuple

from ..config import load_env_file
from ..streaming import stream_chat
from ..utils import is_enabled
from .ambient import get_ambient_settings
from .openai import get_openai_settings
from .openrouter import get_openrouter_settings
from .prompt import load_prompt
from .provider_utils import ProviderSettings


def _receipt_dir_for(settings: ProviderSettings) -> Optional[Path]:
    if settings.name != "Ambient":
        return None
    if not is_enabled(os.getenv("AMBIENT_RECEIPT_SAVE"), default=True):
        return None
    dir_value = os.getenv("AMBIENT_RECEIPT_DIR", "data").strip()
    if not dir_value:
        return None
    return Path(dir_value)


def _run_stream(
    label: str,
    api_url: str,
    api_key: str,
    prompt: str,
    model: str,
    receipt_dir: Optional[Path],
    receipt_label: str,
) -> bool:
    print(f"{label} stream:")
    result = stream_chat(
        api_url,
        api_key,
        prompt,
        model,
        receipt_dir=receipt_dir,
        receipt_label=receipt_label,
    )
    if not result:
        return False
    print(f"Time to first token: {result.ttfb_seconds * 1000:.0f} ms")
    print(f"Time to completion: {result.ttc_seconds * 1000:.0f} ms")
    if result.receipt_path:
        print(f"Receipt saved to: {result.receipt_path}")
    return True


def _run_provider(settings: ProviderSettings, prompt: str, had_output: bool) -> Tuple[bool, bool]:
    if not settings.enabled:
        return True, had_output
    error = settings.validation_error()
    if error:
        print(error)
        return False, had_output
    receipt_dir = _receipt_dir_for(settings)
    for model in settings.models:
        if had_output:
            print("")
        if not _run_stream(
            f"{settings.name} ({model})",
            settings.api_url,
            settings.api_key,
            prompt,
            model,
            receipt_dir,
            settings.name,
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
