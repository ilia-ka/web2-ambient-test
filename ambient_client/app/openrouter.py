from dataclasses import dataclass
import os
from typing import List

from ..utils import is_enabled
from .provider_utils import (
    build_chat_completions_url,
    filter_enabled_models,
    parse_models,
)


@dataclass(frozen=True)
class OpenRouterSettings:
    enabled: bool
    api_url: str
    api_key: str
    models: List[str]


def build_openrouter_api_url() -> str:
    default_url = "https://openrouter.ai/api/v1/chat/completions"
    return build_chat_completions_url(
        os.getenv("OPENROUTER_API_URL", ""),
        os.getenv("OPENROUTER_BASE_URL", ""),
        default_url,
    )


def get_openrouter_settings() -> OpenRouterSettings:
    api_key = os.getenv("OPENROUTER_API", "").strip()
    if not api_key:
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    enabled = is_enabled(os.getenv("OPENROUTER_ENABLED"), default=bool(api_key))
    api_url = build_openrouter_api_url()
    models = parse_models(os.getenv("OPENROUTER_MODELS", "").strip())
    if not models:
        model = os.getenv("OPENROUTER_MODEL", "openai/gpt-5.2").strip()
        if model:
            models = [model]
    models = filter_enabled_models("OPENROUTER", models)
    return OpenRouterSettings(enabled=enabled, api_url=api_url, api_key=api_key, models=models)
