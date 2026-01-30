from typing import Dict, List, Optional


def format_pair(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{value:.0f}"


def format_rate(success: int, total: int) -> str:
    if total == 0:
        return "0/0"
    percent = success / total * 100
    return f"{success}/{total} ({percent:.0f}%)"


def format_value(value: Optional[float], extra: Optional[str] = None) -> str:
    if value is None:
        return "n/a"
    if extra:
        return f"{value:.0f} ({extra})"
    return f"{value:.0f}"


def render_markdown(summaries: List[Dict[str, object]], include_content: bool) -> str:
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
        ttfb = f"{format_pair(row['ttfb_ms_p50'])}/{format_pair(row['ttfb_ms_p90'])}"
        ttc = f"{format_pair(row['ttc_ms_p50'])}/{format_pair(row['ttc_ms_p90'])}"
        usage_extra = None
        if row.get("usage_tokens_p50") is not None and row.get("usage_tokens_coverage"):
            usage_extra = row["usage_tokens_coverage"]
        cells = [
            row["provider"],
            row["model"],
            str(row["runs_total"]),
            format_rate(row["runs_success"], row["runs_total"]),
            ttfb,
            ttc,
            format_value(row["stall_count_avg"]),
            format_pair(row["stall_gap_ms_p90"]),
            format_pair(row["output_chars_p50"]),
            format_value(row["usage_tokens_p50"], usage_extra),
        ]
        if include_content:
            cells.extend(
                [
                    format_pair(row["content_chars_p50"]),
                    format_pair(row["reasoning_chars_p50"]),
                ]
            )
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
