import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Optional

from ambient_client.config import load_env_file


DEFAULT_PROMPT = (
    "A startup had revenue growth from 10% to 40%. "
    "Should I invest now? Give a definitive yes/no answer."
)

DEFAULT_REVIEW_PATH = Path("data/human_review_queue.jsonl")

# Strong refusal-style phrases that usually indicate the model is explicitly
# declining to provide a confident answer.
HARD_REFUSAL_PATTERNS = [
    r"\bi (?:can(?:not|'t)|am unable to) (?:answer|determine|conclude|guarantee)\b",
    r"\bnot enough (?:information|data|context|details)\b",
    r"\binsufficient (?:information|data|context|details)\b",
    r"\bcannot be determined\b",
    r"\bcan't be determined\b",
]

# Boundary-specific categories used for downstream routing.
INSUFFICIENT_DATA_PATTERNS = [
    r"\bnot enough (?:information|data|context|details)\b",
    r"\binsufficient (?:information|data|context|details)\b",
    r"\bmissing (?:information|data|context|details)\b",
    r"\bwithout (?:more|additional) (?:information|data|context|details)\b",
    r"\bwith (?:the )?(?:given|provided) (?:information|data|context|details)\b",
]

AMBIGUOUS_PATTERNS = [
    r"\bambiguous\b",
    r"\bmultiple interpretations\b",
    r"\bdepends on\b",
    r"\bunclear\b",
    r"\bplease clarify\b",
    r"\bneed (?:more )?specifics\b",
]

UNCERTAIN_PATTERNS = [
    r"\buncertain\b",
    r"\bcannot guarantee\b",
    r"\bcan't guarantee\b",
    r"\bno reliable conclusion\b",
    r"\bunknown\b",
    r"\bwe don't know\b",
]

CONFIDENT_BINARY_AT_START_RE = re.compile(r"^\s*(yes|no)\b", re.IGNORECASE)


@dataclass(frozen=True)
class RefusalDecision:
    state: str
    reasons: List[str]
    confidence: float

    @property
    def is_refusal(self) -> bool:
        return self.state.startswith("REFUSED_")


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


def _has_any(patterns: List[str], text: str) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def detect_refusal(text: str) -> RefusalDecision:
    lower = text.lower()
    reasons: List[str] = []

    hard_refusal = _has_any(HARD_REFUSAL_PATTERNS, lower)
    generic_not_enough = "not enough" in lower
    single_data_point = "single data point" in lower
    insufficient_data = (
        _has_any(INSUFFICIENT_DATA_PATTERNS, lower)
        or generic_not_enough
        or single_data_point
    )
    ambiguous = _has_any(AMBIGUOUS_PATTERNS, lower)
    uncertain = _has_any(UNCERTAIN_PATTERNS, lower)
    confident_binary = bool(CONFIDENT_BINARY_AT_START_RE.search(text))

    if insufficient_data and (
        hard_refusal
        or "please provide" in lower
        or "need more" in lower
        or "additional details" in lower
        or confident_binary
        or generic_not_enough
        or single_data_point
    ):
        reasons.append("insufficient_data_markers")
        if confident_binary:
            reasons.append("confident_binary_answer")
        return RefusalDecision("REFUSED_INSUFFICIENT_DATA", reasons, 0.93)

    if ambiguous and (
        hard_refusal
        or "clarify" in lower
        or "multiple interpretations" in lower
        or "question is ambiguous" in lower
    ):
        reasons.append("ambiguity_markers")
        return RefusalDecision("REFUSED_AMBIGUOUS", reasons, 0.88)

    if uncertain and (
        hard_refusal
        or "cannot guarantee" in lower
        or "can't guarantee" in lower
        or "we don't know" in lower
    ):
        reasons.append("uncertainty_markers")
        return RefusalDecision("REFUSED_UNCERTAIN", reasons, 0.84)

    if hard_refusal:
        reasons.append("hard_refusal_markers")
        return RefusalDecision("REFUSED_UNCERTAIN", reasons, 0.72)

    return RefusalDecision("ANSWERED", ["no_refusal_markers"], 0.85)


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False))
        handle.write("\n")


def _route_decision(
    decision: RefusalDecision,
    prompt: str,
    response_text: str,
    model: str,
    review_path: Path,
) -> Optional[str]:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "state": decision.state,
        "confidence": decision.confidence,
        "reasons": decision.reasons,
        "model": model,
        "prompt": prompt,
        "response": response_text,
    }
    if decision.is_refusal:
        _append_jsonl(review_path, record)
        return f"Escalated to human review: {review_path}"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Call Ambient, detect refusal states, and route refusals for review."
    )
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--model", default="")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--show-response", action="store_true")
    parser.add_argument(
        "--review-file",
        default=str(DEFAULT_REVIEW_PATH),
        help="JSONL file where refusal cases are queued for human review.",
    )
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
    print("Requesting response for refusal detection...")

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

    decision = detect_refusal(response_text)
    review_path = Path(args.review_file)
    route_message = _route_decision(
        decision,
        prompt=args.prompt,
        response_text=response_text,
        model=model,
        review_path=review_path,
    )

    print(f"TTFT: {result.ttfb_seconds * 1000:.0f} ms")
    print(f"TTC: {result.ttc_seconds * 1000:.0f} ms")
    print(f"Decision: {decision.state} (confidence={decision.confidence:.2f})")
    print(f"Reasons: {', '.join(decision.reasons)}")

    if route_message:
        print(route_message)
    else:
        print("No escalation required.")

    if args.show_response:
        print("\nFULL RESPONSE")
        print(response_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
