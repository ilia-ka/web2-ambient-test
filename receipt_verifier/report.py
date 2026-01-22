import sys
from typing import List

from receipt_verifier.result import VerificationResult


_COLOR_CODES = {
    "red": "31",
    "green": "32",
}


def _colorize(text: str, color: str) -> str:
    if not sys.stdout.isatty():
        return text
    code = _COLOR_CODES.get(color)
    if not code:
        return text
    return f"\x1b[{code}m{text}\x1b[0m"


def build_report(result: VerificationResult) -> List[str]:
    verdict = "VERIFIED" if result.ok else "REJECTED"
    color = "green" if result.ok else "red"
    verdict = _colorize(verdict, color)
    if result.expected is not None and result.actual is not None:
        expected = _colorize(str(result.expected), "green")
        actual = _colorize(str(result.actual), "red")
        header = f"{verdict}: {result.reason} (expected={expected}, actual={actual})"
    else:
        header = f"{verdict}: {result.reason}"
    lines = [header]
    lines.append("Guarantees:")
    lines.append("- Detects tampering for fields covered by stored hashes.")
    lines.append("- Confirms basic structure and event counts.")
    lines.append("Does not guarantee:")
    lines.append("- Origin/authenticity (no signatures).")
    lines.append("- That the model actually ran or output is correct.")
    return lines


def print_report(result: VerificationResult) -> None:
    print("\n".join(build_report(result)))
