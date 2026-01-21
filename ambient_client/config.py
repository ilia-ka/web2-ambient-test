import os
from pathlib import Path

from .env_loader import load_env
from .utils import is_enabled

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
DEFAULT_API_URL = "https://api.ambient.xyz/v1/chat/completions"


def get_config():
    load_env(ENV_PATH)
    ambient_enabled = is_enabled(os.getenv("AMBIENT_ENABLED"), default=True)
    api_url = os.getenv("AMBIENT_API_URL", DEFAULT_API_URL).strip()
    api_key = os.getenv("AMBIENT_API_KEY")
    if ambient_enabled:
        if not api_key:
            print(
                "Error: AMBIENT_API_KEY is not set. Add it to .env or your environment."
            )
            return None
        if not api_url:
            print("Error: AMBIENT_API_URL is not set. Add it to .env or your environment.")
            return None
    return ambient_enabled, api_url, api_key
