import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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


def _int_env(key: str, default: Optional[int] = None) -> Optional[int]:
    raw = os.getenv(key, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"Warning: Invalid {key}='{raw}', using default.")
        return default


def _float_env(key: str, default: Optional[float] = None) -> Optional[float]:
    raw = os.getenv(key, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        print(f"Warning: Invalid {key}='{raw}', using default.")
        return default


def _parse_stop_sequences(raw: str) -> Optional[List[str]]:
    raw = raw.strip()
    if not raw:
        return None
    if raw.startswith("["):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            print("Warning: REQUEST_STOP is not valid JSON; using raw value.")
        else:
            if isinstance(value, list) and all(isinstance(item, str) for item in value):
                return value
            print("Warning: REQUEST_STOP JSON must be a list of strings; using raw value.")
    parts = [part.strip() for part in raw.split("|") if part.strip()]
    return parts or None


def _load_request_params() -> Dict[str, object]:
    params: Dict[str, object] = {}
    temperature = _float_env("REQUEST_TEMPERATURE")
    if temperature is not None:
        params["temperature"] = temperature
    max_tokens = _int_env("REQUEST_MAX_TOKENS")
    if max_tokens is not None:
        params["max_tokens"] = max_tokens
    top_p = _float_env("REQUEST_TOP_P")
    if top_p is not None:
        params["top_p"] = top_p
    seed = _int_env("REQUEST_SEED")
    if seed is not None:
        params["seed"] = seed
    stop = _parse_stop_sequences(os.getenv("REQUEST_STOP", ""))
    if stop:
        params["stop"] = stop
    return params


def _bench_settings() -> Tuple[bool, int, int]:
    enabled = is_enabled(os.getenv("BENCH_ENABLED"), default=False)
    if not enabled:
        return False, 0, 1
    warmup = _int_env("BENCH_WARMUP", default=1)
    if warmup is None:
        warmup = 1
    warmup = max(0, warmup)
    runs = _int_env("BENCH_RUNS", default=3)
    if runs is None:
        runs = 3
    runs = max(1, runs)
    return True, warmup, runs


def _run_stream(
    label: str,
    api_url: str,
    api_key: str,
    prompt: str,
    model: str,
    receipt_dir: Optional[Path],
    receipt_label: str,
    request_params: Optional[Dict[str, object]] = None,
) -> bool:
    print(f"{label} stream:")
    result = stream_chat(
        api_url,
        api_key,
        prompt,
        model,
        receipt_dir=receipt_dir,
        receipt_label=receipt_label,
        request_params=request_params,
    )
    if not result:
        return False
    print(f"Time to first token: {result.ttfb_seconds * 1000:.0f} ms")
    print(f"Time to completion: {result.ttc_seconds * 1000:.0f} ms")
    if result.receipt_path:
        print(f"Receipt saved to: {result.receipt_path}")
    return True


def _run_provider(
    settings: ProviderSettings,
    prompt: str,
    had_output: bool,
    request_params: Optional[Dict[str, object]],
    bench_enabled: bool,
    bench_warmup: int,
    bench_runs: int,
) -> Tuple[bool, bool]:
    if not settings.enabled:
        return True, had_output
    error = settings.validation_error()
    if error:
        print(error)
        return False, had_output
    receipt_dir = _receipt_dir_for(settings)
    for model in settings.models:
        if bench_enabled:
            total_runs = bench_warmup + bench_runs
            for run_index in range(total_runs):
                is_warmup = run_index < bench_warmup
                if had_output:
                    print("")
                if is_warmup:
                    label = f"{settings.name} ({model}) warmup {run_index + 1}/{bench_warmup}"
                else:
                    run_number = run_index - bench_warmup + 1
                    label = f"{settings.name} ({model}) run {run_number}/{bench_runs}"
                if not _run_stream(
                    label,
                    settings.api_url,
                    settings.api_key,
                    prompt,
                    model,
                    receipt_dir,
                    settings.name,
                    request_params=request_params,
                ):
                    return False, had_output
                had_output = True
        else:
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
                request_params=request_params,
            ):
                return False, had_output
            had_output = True
    return True, had_output


def run() -> None:
    load_env_file()
    prompt = load_prompt()
    if prompt is None:
        return

    request_params = _load_request_params()
    bench_enabled, bench_warmup, bench_runs = _bench_settings()
    if bench_enabled:
        print(f"Bench mode: warmup={bench_warmup}, runs={bench_runs}")
    had_output = False
    for settings in (
        get_ambient_settings(),
        get_openai_settings(),
        get_openrouter_settings(),
    ):
        success, had_output = _run_provider(
            settings,
            prompt,
            had_output,
            request_params if request_params else None,
            bench_enabled,
            bench_warmup,
            bench_runs,
        )
        if not success:
            return
