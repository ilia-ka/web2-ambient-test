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
class OpenAISettings:
    enabled: bool
    api_url: str
    api_key: str
    models: List[str]


def build_openai_api_url() -> str:
    default_url = "https://api.openai.com/v1/chat/completions"
    return build_chat_completions_url(
        os.getenv("OPENAI_API_URL", ""),
        os.getenv("OPENAI_BASE_URL", ""),
        default_url,
    )


def get_openai_settings() -> OpenAISettings:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    enabled = is_enabled(os.getenv("OPENAI_ENABLED"), default=bool(api_key))
    api_url = build_openai_api_url()
    models = parse_models(os.getenv("OPENAI_MODELS", "").strip())
    if not models:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        if model:
            models = [model]
    models = filter_enabled_models("OPENAI", models)
    return OpenAISettings(enabled=enabled, api_url=api_url, api_key=api_key, models=models)
