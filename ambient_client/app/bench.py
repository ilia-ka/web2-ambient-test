from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, List, Optional

from ..streaming import StreamResult
from .provider_utils import ProviderSettings


@dataclass(frozen=True)
class RunSpec:
    index: int
    total: int
    is_warmup: bool
    label_suffix: str


class BenchRecorder:
    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, record: Dict[str, object]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True))
                handle.write("\n")
        except OSError as exc:
            print(f"Warning: Unable to write bench record: {exc}")


def iter_run_specs(bench_enabled: bool, warmup: int, runs: int) -> List[RunSpec]:
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


def build_bench_meta(
    bench_warmup: int,
    bench_runs: int,
    stall_threshold_ms: int,
    prompt_sha256: str,
    request_params: Dict[str, object],
    content_mode: str,
    on_error: str,
    prompt_file: Optional[str],
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
        "prompt_file": prompt_file,
        "request_params": request_params,
        "content_mode": content_mode,
        "on_error": on_error,
    }


def build_bench_record(
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


def attach_result_metrics(
    record: Dict[str, object],
    result: StreamResult,
    content_mode: str,
) -> Dict[str, object]:
    record.update(
        {
            "success": result.success,
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
    return record
