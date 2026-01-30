import argparse
import json
from typing import Dict, List

from report_tools.format_utils import render_markdown
from report_tools.io_utils import load_run_records
from report_tools.sorting import sort_summaries
from report_tools.summary import summarize


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

    records: List[Dict[str, object]] = load_run_records(args.paths, args.include_warmup)
    summaries = summarize(records)
    summaries = sort_summaries(summaries, args.sort, args.desc)
    if args.format == "json":
        print(json.dumps({"summaries": summaries}, indent=2))
        return 0
    print(render_markdown(summaries, args.include_content))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
