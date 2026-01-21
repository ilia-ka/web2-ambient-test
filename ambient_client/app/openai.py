from dataclasses import dataclass
import os

from ..utils import is_enabled


@dataclass(frozen=True)
class OpenAISettings:
    enabled: bool
    api_url: str
    api_key: str
    model: str


def build_openai_api_url() -> str:
    explicit_url = os.getenv("OPENAI_API_URL", "").strip()
    if explicit_url:
        return explicit_url
    base_url = os.getenv("OPENAI_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        return "https://api.openai.com/v1/chat/completions"
    if base_url.endswith("/chat/completions"):
        return base_url
    if base_url.endswith("/v1"):
        return f"{base_url}/chat/completions"
    return f"{base_url}/v1/chat/completions"


def get_openai_settings() -> OpenAISettings:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    enabled = is_enabled(os.getenv("OPENAI_ENABLED"), default=bool(api_key))
    api_url = build_openai_api_url()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    return OpenAISettings(enabled=enabled, api_url=api_url, api_key=api_key, model=model)
