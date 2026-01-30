import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


def _iter_paths(values: List[str]) -> Iterable[Path]:
    for raw in values:
        path = Path(raw)
        if path.is_dir():
            yield from sorted(path.glob("bench_*.jsonl"))
        else:
            yield path


def _percentile(values: List[float], quantile: float) -> Optional[float]:
    if not values:
        return None
    if quantile <= 0:
        return min(values)
    if quantile >= 1:
        return max(values)
    sorted_values = sorted(values)
    rank = (len(sorted_values) - 1) * quantile
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = rank - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _usage_total(usage: Optional[Dict[str, object]]) -> Optional[float]:
    if not usage:
        return None
    total = usage.get("total_tokens")
    if isinstance(total, (int, float)):
        return float(total)
    prompt = usage.get("prompt_tokens")
    if not isinstance(prompt, (int, float)):
        prompt = usage.get("input_tokens")
    completion = usage.get("completion_tokens")
    if not isinstance(completion, (int, float)):
        completion = usage.get("output_tokens")
    if isinstance(prompt, (int, float)) or isinstance(completion, (int, float)):
        return float(prompt or 0) + float(completion or 0)
    return None


def _format_pair(value: Optional[float], suffix: str = "") -> str:
    if value is None:
        return "n/a"
    if suffix:
        return f"{value:.0f}{suffix}"
    return f"{value:.0f}"


def _format_rate(success: int, total: int) -> str:
    if total == 0:
        return "0/0"
    percent = success / total * 100
    return f"{success}/{total} ({percent:.0f}%)"


def _format_value(value: Optional[float], extra: Optional[str] = None) -> str:
    if value is None:
        return "n/a"
    if extra:
        return f"{value:.0f} ({extra})"
    return f"{value:.0f}"


def _summarize(records: List[Dict[str, object]]) -> List[Dict[str, object]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, object]]] = {}
    for record in records:
        provider = record.get("provider") or "Unknown"
        model = record.get("model") or "Unknown"
        grouped.setdefault((str(provider), str(model)), []).append(record)

    summaries = []
    for (provider, model), items in sorted(grouped.items()):
        total_runs = len(items)
        success_runs = [item for item in items if item.get("success")]
        success_count = len(success_runs)
        ttfb_ms = [float(item["ttfb_ms"]) for item in success_runs if item.get("ttfb_ms") is not None]
        ttc_ms = [float(item["ttc_ms"]) for item in success_runs if item.get("ttc_ms") is not None]
        stall_counts = [
            float(item["stall_count"]) for item in success_runs if item.get("stall_count") is not None
        ]
        stall_gaps = [
            float(item["stall_max_gap_ms"])
            for item in success_runs
            if item.get("stall_max_gap_ms") is not None
        ]
        output_chars = [
            float(item["output_chars"]) for item in success_runs if item.get("output_chars") is not None
        ]
        content_chars = [
            float(item["content_chars"]) for item in success_runs if item.get("content_chars") is not None
        ]
        reasoning_chars = [
            float(item["reasoning_chars"]) for item in success_runs if item.get("reasoning_chars") is not None
        ]
        usage_tokens = []
        for item in success_runs:
            total_tokens = _usage_total(item.get("usage"))
            if total_tokens is not None:
                usage_tokens.append(float(total_tokens))

        summaries.append(
            {
                "provider": provider,
                "model": model,
                "runs_total": total_runs,
                "runs_success": success_count,
                "success_rate": success_count / total_runs if total_runs else 0.0,
                "ttfb_ms_p50": _percentile(ttfb_ms, 0.5),
                "ttfb_ms_p90": _percentile(ttfb_ms, 0.9),
                "ttc_ms_p50": _percentile(ttc_ms, 0.5),
                "ttc_ms_p90": _percentile(ttc_ms, 0.9),
                "stall_count_avg": sum(stall_counts) / len(stall_counts) if stall_counts else None,
                "stall_gap_ms_p90": _percentile(stall_gaps, 0.9),
                "output_chars_p50": _percentile(output_chars, 0.5),
                "content_chars_p50": _percentile(content_chars, 0.5),
                "reasoning_chars_p50": _percentile(reasoning_chars, 0.5),
                "usage_tokens_p50": _percentile(usage_tokens, 0.5),
                "usage_tokens_coverage": f"{len(usage_tokens)}/{success_count}"
                if success_count
                else "0/0",
            }
        )
    return summaries


def _render_markdown(summaries: List[Dict[str, object]], include_content: bool) -> str:
    headers = [
        "Provider",
        "Model",
        "Runs",
        "Success",
        "TTFT p50/p90 (ms)",
        "TTC p50/p90 (ms)",
        "Stalls avg",
        "Stall max p90 (ms)",
        "Output chars p50",
        "Tokens p50",
    ]
    if include_content:
        headers.extend(["Content chars p50", "Reasoning chars p50"])
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in summaries:
        ttfb = f"{_format_pair(row['ttfb_ms_p50'])}/{_format_pair(row['ttfb_ms_p90'])}"
        ttc = f"{_format_pair(row['ttc_ms_p50'])}/{_format_pair(row['ttc_ms_p90'])}"
        usage_extra = None
        if row.get("usage_tokens_p50") is not None and row.get("usage_tokens_coverage"):
            usage_extra = row["usage_tokens_coverage"]
        cells = [
            row["provider"],
            row["model"],
            str(row["runs_total"]),
            _format_rate(row["runs_success"], row["runs_total"]),
            ttfb,
            ttc,
            _format_value(row["stall_count_avg"]),
            _format_pair(row["stall_gap_ms_p90"]),
            _format_pair(row["output_chars_p50"]),
            _format_value(row["usage_tokens_p50"], usage_extra),
        ]
        if include_content:
            cells.extend(
                [
                    _format_pair(row["content_chars_p50"]),
                    _format_pair(row["reasoning_chars_p50"]),
                ]
            )
        lines.append(
            "| " + " | ".join(cells) + " |"
        )
    return "\n".join(lines)


def _sort_summaries(
    summaries: List[Dict[str, object]],
    sort_by: str,
    descending: bool,
) -> List[Dict[str, object]]:
    sort_by = sort_by.strip().lower()
    if sort_by in ("provider", "model"):
        return sorted(
            summaries,
            key=lambda row: (row.get(sort_by, "") or "").lower(),
            reverse=descending,
        )

    field_map = {
        "success_rate": "success_rate",
        "ttfb_p50": "ttfb_ms_p50",
        "ttfb_p90": "ttfb_ms_p90",
        "ttc_p50": "ttc_ms_p50",
        "ttc_p90": "ttc_ms_p90",
        "stall_avg": "stall_count_avg",
        "stall_p90": "stall_gap_ms_p90",
        "output_p50": "output_chars_p50",
        "tokens_p50": "usage_tokens_p50",
        "content_p50": "content_chars_p50",
        "reasoning_p50": "reasoning_chars_p50",
    }
    field = field_map.get(sort_by, "ttc_ms_p50")

    def numeric_key(row: Dict[str, object]) -> Tuple[int, float]:
        value = row.get(field)
        if value is None:
            return (1, 0.0)
        numeric = float(value)
        return (0, -numeric if descending else numeric)

    return sorted(summaries, key=numeric_key)


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize bench_*.jsonl results.")
    parser.add_argument("paths", nargs="+", help="Bench JSONL file(s) or a directory.")
    parser.add_argument("--include-warmup", action="store_true", help="Include warmup runs.")
    parser.add_argument(
        "--include-content",
        action="store_true",
        help="Include content/reasoning character columns.",
    )
    parser.add_argument(
        "--sort",
        default="provider",
        help=(
            "Sort by: provider, model, success_rate, ttfb_p50, ttfb_p90, "
            "ttc_p50, ttc_p90, stall_avg, stall_p90, output_p50, tokens_p50, "
            "content_p50, reasoning_p50."
        ),
    )
    parser.add_argument("--desc", action="store_true", help="Sort descending.")
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format.",
    )
    args = parser.parse_args()

    records: List[Dict[str, object]] = []
    for path in _iter_paths(args.paths):
        if not path.exists():
            print(f"Warning: {path} does not exist, skipping.")
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                print(f"Warning: Invalid JSON in {path}, skipping line.")
                continue
            if record.get("type") != "run":
                continue
            if not args.include_warmup and record.get("warmup"):
                continue
            records.append(record)

    summaries = _summarize(records)
    summaries = _sort_summaries(summaries, args.sort, args.desc)
    if args.format == "json":
        print(json.dumps({"summaries": summaries}, indent=2))
        return 0
    print(_render_markdown(summaries, args.include_content))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
