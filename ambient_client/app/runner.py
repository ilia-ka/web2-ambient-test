from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
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

@dataclass(frozen=True)
class EnvConfig:
    request_params: Dict[str, object]
    content_mode: str
    bench_enabled: bool
    bench_warmup: int
    bench_runs: int
    bench_recorder: Optional["BenchRecorder"]
    prompt_sha256: str
    stall_threshold_seconds: Optional[float]


@dataclass(frozen=True)
class RunSpec:
    index: int
    total: int
    is_warmup: bool
    label_suffix: str


ALLOWED_REQUEST_PARAMS = {
    "temperature",
    "max_tokens",
    "top_p",
    "seed",
    "stop",
    "stream_options",
}

ALLOWED_CONTENT_MODES = {
    "content",
    "reasoning",
    "content_or_reasoning",
}


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


def _bool_env(key: str, default: bool = False) -> bool:
    return is_enabled(os.getenv(key), default=default)


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
    if _bool_env("REQUEST_STREAM_INCLUDE_USAGE", default=False):
        params["stream_options"] = {"include_usage": True}
    return _validate_request_params(params)


def _validate_request_params(params: Dict[str, object]) -> Dict[str, object]:
    unknown = [key for key in params.keys() if key not in ALLOWED_REQUEST_PARAMS]
    if unknown:
        for key in sorted(unknown):
            print(f"Warning: Unsupported request param '{key}' ignored.")
            params.pop(key, None)
    return params


def _load_content_mode() -> str:
    raw = os.getenv("REQUEST_CONTENT_MODE", "").strip().lower()
    if not raw:
        return "content_or_reasoning"
    if raw not in ALLOWED_CONTENT_MODES:
        print(
            "Warning: REQUEST_CONTENT_MODE must be one of "
            f"{', '.join(sorted(ALLOWED_CONTENT_MODES))}; using content_or_reasoning."
        )
        return "content_or_reasoning"
    return raw


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


def _bench_output_path() -> Optional[Path]:
    dir_value = os.getenv("BENCH_OUTPUT_DIR", "data").strip()
    if not dir_value:
        return None
    bench_dir = Path(dir_value)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return bench_dir / f"bench_{timestamp}.jsonl"


def _append_bench_record(path: Path, record: Dict[str, object]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")
    except OSError as exc:
        print(f"Warning: Unable to write bench record: {exc}")


class BenchRecorder:
    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, record: Dict[str, object]) -> None:
        _append_bench_record(self.path, record)


def _build_bench_meta(
    bench_warmup: int,
    bench_runs: int,
    stall_threshold_ms: int,
    prompt_sha256: str,
    request_params: Dict[str, object],
    content_mode: str,
) -> Dict[str, object]:
    return {
        "type": "meta",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "bench": {
            "warmup": bench_warmup,
            "runs": bench_runs,
            "stall_threshold_ms": stall_threshold_ms,
        },
        "prompt_sha256": prompt_sha256,
        "prompt_file": os.getenv("AMBIENT_PROMPT_FILE", "").strip() or None,
        "request_params": request_params,
        "content_mode": content_mode,
    }


def _build_bench_record(
    settings: ProviderSettings,
    model: str,
    prompt_sha256: str,
    run_spec: RunSpec,
) -> Dict[str, object]:
    return {
        "type": "run",
        "provider": settings.name,
        "model": model,
        "api_url": settings.api_url,
        "prompt_sha256": prompt_sha256,
        "warmup": run_spec.is_warmup,
        "run_index": run_spec.index,
        "run_total": run_spec.total,
    }


def _iter_run_specs(bench_enabled: bool, warmup: int, runs: int) -> List[RunSpec]:
    if not bench_enabled:
        return [RunSpec(index=1, total=1, is_warmup=False, label_suffix="")]
    total = warmup + runs
    specs: List[RunSpec] = []
    for idx in range(total):
        is_warmup = idx < warmup
        if is_warmup:
            suffix = f" warmup {idx + 1}/{warmup}"
        else:
            run_number = idx - warmup + 1
            suffix = f" run {run_number}/{runs}"
        specs.append(
            RunSpec(
                index=idx + 1,
                total=total,
                is_warmup=is_warmup,
                label_suffix=suffix,
            )
        )
    return specs


def _run_stream(
    label: str,
    api_url: str,
    api_key: str,
    prompt: str,
    model: str,
    receipt_dir: Optional[Path],
    receipt_label: str,
    request_params: Optional[Dict[str, object]] = None,
    bench_recorder: Optional[BenchRecorder] = None,
    bench_record: Optional[Dict[str, object]] = None,
    stall_threshold_seconds: Optional[float] = None,
    content_mode: str = "content_or_reasoning",
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
        stall_threshold_seconds=stall_threshold_seconds,
        content_mode=content_mode,
    )
    success = result.success
    if bench_recorder is not None and bench_record is not None:
        record = dict(bench_record)
        record.update(
            {
                "success": success,
                "ttfb_ms": round(result.ttfb_seconds * 1000, 3),
                "ttc_ms": round(result.ttc_seconds * 1000, 3),
                "output_chars": result.output_chars,
                "content_chars": result.content_chars,
                "reasoning_chars": result.reasoning_chars,
                "stall_count": result.stall_count,
                "stall_max_gap_ms": round(result.stall_max_gap_seconds * 1000, 3),
                "parse_errors": result.parse_errors,
                "usage": result.usage,
                "error": result.error,
                "status_code": result.status_code,
                "started_at": result.started_at,
                "content_mode": content_mode,
            }
        )
        if result.receipt_path:
            record["receipt_path"] = result.receipt_path
        bench_recorder.write(record)
    if not success:
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
    config: EnvConfig,
) -> Tuple[bool, bool]:
    if not settings.enabled:
        return True, had_output
    error = settings.validation_error()
    if error:
        print(error)
        return False, had_output
    receipt_dir = _receipt_dir_for(settings)
    for model in settings.models:
        for run_spec in _iter_run_specs(config.bench_enabled, config.bench_warmup, config.bench_runs):
            if had_output:
                print("")
            label = f"{settings.name} ({model}){run_spec.label_suffix}"
            bench_record = None
            if config.bench_recorder is not None:
                bench_record = _build_bench_record(
                    settings,
                    model,
                    config.prompt_sha256,
                    run_spec,
                )
            if not _run_stream(
                label,
                settings.api_url,
                settings.api_key,
                prompt,
                model,
                receipt_dir,
                settings.name,
                request_params=config.request_params or None,
                bench_recorder=config.bench_recorder,
                bench_record=bench_record,
                stall_threshold_seconds=config.stall_threshold_seconds,
                content_mode=config.content_mode,
            ):
                had_output = True
                if config.bench_enabled:
                    continue
                return False, had_output
            had_output = True
    return True, had_output


def _load_env_config(prompt: str) -> EnvConfig:
    request_params = _load_request_params()
    content_mode = _load_content_mode()
    bench_enabled, bench_warmup, bench_runs = _bench_settings()
    prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    bench_recorder: Optional[BenchRecorder] = None
    stall_threshold_seconds = None
    if bench_enabled:
        print(f"Bench mode: warmup={bench_warmup}, runs={bench_runs}")
        bench_path = _bench_output_path()
        stall_threshold_ms = _int_env("BENCH_STALL_THRESHOLD_MS", default=2000)
        if stall_threshold_ms is None:
            stall_threshold_ms = 2000
        stall_threshold_seconds = stall_threshold_ms / 1000.0
        if bench_path is not None:
            bench_recorder = BenchRecorder(bench_path)
            meta = _build_bench_meta(
                bench_warmup,
                bench_runs,
                stall_threshold_ms,
                prompt_sha256,
                request_params,
                content_mode,
            )
            bench_recorder.write(meta)
            print(f"Bench output: {bench_path}")
    return EnvConfig(
        request_params=request_params,
        content_mode=content_mode,
        bench_enabled=bench_enabled,
        bench_warmup=bench_warmup,
        bench_runs=bench_runs,
        bench_recorder=bench_recorder,
        prompt_sha256=prompt_sha256,
        stall_threshold_seconds=stall_threshold_seconds,
    )


def run() -> None:
    load_env_file()
    prompt = load_prompt()
    if prompt is None:
        return

    config = _load_env_config(prompt)
    had_output = False
    for settings in (
        get_ambient_settings(),
        get_openai_settings(),
        get_openrouter_settings(),
    ):
        success, had_output = _run_provider(settings, prompt, had_output, config)
        if not success:
            return
