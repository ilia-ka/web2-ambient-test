from typing import Dict, List, Tuple

from .stats_utils import percentile, usage_total


def summarize(records: List[Dict[str, object]]) -> List[Dict[str, object]]:
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
            total_tokens = usage_total(item.get("usage"))
            if total_tokens is not None:
                usage_tokens.append(float(total_tokens))

        summaries.append(
            {
                "provider": provider,
                "model": model,
                "runs_total": total_runs,
                "runs_success": success_count,
                "success_rate": success_count / total_runs if total_runs else 0.0,
                "ttfb_ms_p50": percentile(ttfb_ms, 0.5),
                "ttfb_ms_p90": percentile(ttfb_ms, 0.9),
                "ttc_ms_p50": percentile(ttc_ms, 0.5),
                "ttc_ms_p90": percentile(ttc_ms, 0.9),
                "stall_count_avg": sum(stall_counts) / len(stall_counts) if stall_counts else None,
                "stall_gap_ms_p90": percentile(stall_gaps, 0.9),
                "output_chars_p50": percentile(output_chars, 0.5),
                "content_chars_p50": percentile(content_chars, 0.5),
                "reasoning_chars_p50": percentile(reasoning_chars, 0.5),
                "usage_tokens_p50": percentile(usage_tokens, 0.5),
                "usage_tokens_coverage": f"{len(usage_tokens)}/{success_count}"
                if success_count
                else "0/0",
            }
        )
    return summaries
