from dataclasses import dataclass
import os
import re
from typing import List

from ..utils import is_enabled


@dataclass(frozen=True)
class ProviderSettings:
    name: str
    enabled: bool
    api_url: str
    api_key: str
    models: List[str]
    key_env_hint: str
    model_env_hint: str


def build_chat_completions_url(explicit_url: str, base_url: str, default_url: str) -> str:
    explicit_url = explicit_url.strip()
    if explicit_url:
        return explicit_url
    base_url = base_url.strip().rstrip("/")
    if not base_url:
        return default_url
    if base_url.endswith("/chat/completions"):
        return base_url
    if base_url.endswith("/v1"):
        return f"{base_url}/chat/completions"
    return f"{base_url}/v1/chat/completions"


def parse_models(raw_models: str) -> List[str]:
    if not raw_models:
        return []
    models: List[str] = []
    for chunk in raw_models.replace("\n", ",").split(","):
        model = chunk.strip()
        if model:
            models.append(model)
    return models


def model_flag_env_key(prefix: str, model: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]+", "_", model).strip("_").upper()
    if not token:
        token = "MODEL"
    return f"{prefix}_MODEL_{token}_ENABLED"


def filter_enabled_models(prefix: str, models: List[str]) -> List[str]:
    enabled_models: List[str] = []
    for model in models:
        flag_key = model_flag_env_key(prefix, model)
        if is_enabled(os.getenv(flag_key), default=True):
            enabled_models.append(model)
    return enabled_models


def _first_env_value(keys: List[str]) -> str:
    for key in keys:
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""


def get_provider_settings(
    name: str,
    prefix: str,
    enabled_env: str,
    api_url_env: str,
    base_url_env: str,
    default_url: str,
    api_key_envs: List[str],
    models_env: str,
    model_env: str,
    default_model: str,
) -> ProviderSettings:
    api_key = _first_env_value(api_key_envs)
    enabled = is_enabled(os.getenv(enabled_env), default=bool(api_key))
    api_url = build_chat_completions_url(
        os.getenv(api_url_env, ""),
        os.getenv(base_url_env, ""),
        default_url,
    )
    models = parse_models(os.getenv(models_env, "").strip())
    if not models:
        model = os.getenv(model_env, default_model).strip()
        if model:
            models = [model]
    models = filter_enabled_models(prefix, models)
    key_env_hint = " or ".join(api_key_envs)
    model_env_hint = f"{model_env} or {models_env}"
    return ProviderSettings(
        name=name,
        enabled=enabled,
        api_url=api_url,
        api_key=api_key,
        models=models,
        key_env_hint=key_env_hint,
        model_env_hint=model_env_hint,
    )
