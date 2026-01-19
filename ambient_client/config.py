import os
from pathlib import Path

from .env_loader import load_env

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def get_config():
    load_env(ENV_PATH)
    api_url = os.getenv("AMBIENT_API_URL")
    api_key = os.getenv("AMBIENT_API_KEY")
    if not api_url:
        print("Error: AMBIENT_API_URL is not set. Add it to .env or your environment.")
        return None
    if not api_key:
        print("Error: AMBIENT_API_KEY is not set. Add it to .env or your environment.")
        return None
    return api_url, api_key
