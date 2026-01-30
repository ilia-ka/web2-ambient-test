from typing import Dict, List, Tuple


def sort_summaries(
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
