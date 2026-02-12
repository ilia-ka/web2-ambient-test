import argparse
import os
import re
import sys
from typing import List, Optional, Tuple

from ambient_client.config import load_env_file


DEFAULT_PROMPT = (
    "Compute 125 * 48 and show the final numeric result. "
    "Then explain why diversification matters in financial portfolios."
)

# Signals that usually indicate a deterministic claim:
# - explicit numbers
# - math/logical operators
# - wording tied to calculation/proof-like steps
DETERMINISTIC_KEYWORDS = {
    "compute",
    "calculation",
    "result",
    "equals",
    "therefore",
    "if",
    "then",
    "logic",
    "true",
    "false",
    "proof",
}

# Signals that usually indicate interpretive text:
# - recommendations
# - subjective framing
# - portfolio/advice wording
INTERPRETIVE_KEYWORDS = {
    "recommend",
    "consider",
    "should",
    "might",
    "may",
    "important",
    "depends",
    "in my view",
    "generally",
    "often",
    "diversification",
    "portfolio",
    "risk tolerance",
    "strategy",
    "advice",
}

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
MATH_EXPR_RE = re.compile(r"\b\d+(?:\.\d+)?\s*[\+\-\*/^]\s*\d+(?:\.\d+)?\b")
EQUALITY_RE = re.compile(r"[=≈]")
LOGIC_SYMBOL_RE = re.compile(r"(=>|->|implies|∴)")


def _detect_section_hint(line: str) -> Optional[str]:
    lower = line.strip().lower().rstrip(":")
    if lower in {"deterministic", "calculation", "math", "logic"}:
        return "deterministic"
    if lower in {"interpretive", "explanation", "analysis", "advice", "summary"}:
        return "interpretive"
    return None


def _score_segment(text: str, hint: Optional[str]) -> Tuple[int, int]:
    lower = text.lower()
    det_score = 0
    int_score = 0

    if hint == "deterministic":
        det_score += 2
    elif hint == "interpretive":
        int_score += 2

    if re.search(r"\d", text):
        det_score += 1
    if MATH_EXPR_RE.search(text):
        det_score += 3
    if EQUALITY_RE.search(text):
        det_score += 2
    if LOGIC_SYMBOL_RE.search(lower):
        det_score += 2

    if any(keyword in lower for keyword in DETERMINISTIC_KEYWORDS):
        det_score += 1
    if any(keyword in lower for keyword in INTERPRETIVE_KEYWORDS):
        int_score += 2

    return det_score, int_score


def split_layers(response_text: str) -> Tuple[List[str], List[str]]:
    deterministic_parts: List[str] = []
    interpretive_parts: List[str] = []
    section_hint: Optional[str] = None

    for raw_line in response_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Respect explicit headings when the model outputs them.
        hint = _detect_section_hint(line)
        if hint:
            section_hint = hint
            continue

        # Then split into sentence-like chunks for finer classification.
        for chunk in SENTENCE_SPLIT_RE.split(line):
            text = chunk.strip().lstrip("-* ").strip()
            if not text:
                continue
            det_score, int_score = _score_segment(text, section_hint)

            if det_score > int_score:
                deterministic_parts.append(text)
            elif int_score > det_score:
                interpretive_parts.append(text)
            else:
                # Tie-breaker: numeric/operator-heavy chunks lean deterministic.
                if re.search(r"\d|[=+\-*/^]", text):
                    deterministic_parts.append(text)
                else:
                    interpretive_parts.append(text)

    return deterministic_parts, interpretive_parts


def _dedupe_keep_order(values: List[str]) -> List[str]:
    seen = set()
    output: List[str] = []
    for item in values:
        key = item.strip()
        if key and key not in seen:
            seen.add(key)
            output.append(item)
    return output


def _build_ambient_url() -> str:
    explicit_url = os.getenv("AMBIENT_API_URL", "").strip()
    if explicit_url:
        return explicit_url
    base_url = os.getenv("AMBIENT_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        return "https://api.ambient.xyz/v1/chat/completions"
    if base_url.endswith("/chat/completions"):
        return base_url
    if base_url.endswith("/v1"):
        return f"{base_url}/chat/completions"
    return f"{base_url}/v1/chat/completions"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Call Ambient and split output into deterministic vs interpretive layers."
    )
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--model", default="")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--show-response", action="store_true")
    args = parser.parse_args()

    load_env_file()
    api_key = os.getenv("AMBIENT_API_KEY", "").strip()
    if not api_key:
        print(
            "Error: AMBIENT_API_KEY is not set. Add it to .env or your environment.",
            file=sys.stderr,
        )
        return 1

    api_url = _build_ambient_url()
    model = args.model.strip() or os.getenv("AMBIENT_MODEL", "zai-org/GLM-4.6").strip()
    print(f"Ambient model: {model}")
    print("Requesting mixed deterministic + interpretive response...")

    from ambient_client.streaming import stream_chat

    result = stream_chat(
        api_url,
        api_key,
        args.prompt,
        model=model,
        request_params={
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
        },
        content_mode="content",
        output_handler=lambda _: None,
        error_handler=lambda msg: print(msg, file=sys.stderr),
    )

    if not result.success:
        return 1

    response_text = result.text.strip()
    if not response_text:
        print("No response text returned.", file=sys.stderr)
        return 1

    deterministic, interpretive = split_layers(response_text)
    deterministic = _dedupe_keep_order(deterministic)
    interpretive = _dedupe_keep_order(interpretive)

    print(f"TTFT: {result.ttfb_seconds * 1000:.0f} ms")
    print(f"TTC: {result.ttc_seconds * 1000:.0f} ms")
    if args.show_response:
        print("\nFULL RESPONSE")
        print(response_text)

    print("\nDETERMINISTIC COMPONENTS")
    if deterministic:
        for item in deterministic:
            print(f"- {item}")
    else:
        print("- (none detected by heuristic)")

    print("\nINTERPRETIVE COMPONENTS")
    if interpretive:
        for item in interpretive:
            print(f"- {item}")
    else:
        print("- (none detected by heuristic)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
