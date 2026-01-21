import os
import re
from typing import List

from ..utils import is_enabled


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
