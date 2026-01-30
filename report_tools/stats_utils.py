from typing import Dict, List, Optional


def percentile(values: List[float], quantile: float) -> Optional[float]:
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


def usage_total(usage: Optional[Dict[str, object]]) -> Optional[float]:
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
