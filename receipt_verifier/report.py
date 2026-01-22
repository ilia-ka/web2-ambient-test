import re
import sys
from typing import List


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


def _colorize_expected_actual(text: str) -> str:
    if not sys.stdout.isatty():
        return text

    def repl_expected(match: re.Match[str]) -> str:
        value = _colorize(match.group(1), "green")
        return f"expected={value}"

    def repl_actual(match: re.Match[str]) -> str:
        value = _colorize(match.group(1), "red")
        return f"actual={value}"

    text = re.sub(r"expected=([^,)\s]+)", repl_expected, text)
    text = re.sub(r"actual=([^,)\s]+)", repl_actual, text)
    return text


def build_report(ok: bool, reason: str) -> List[str]:
    verdict = "VERIFIED" if ok else "REJECTED"
    color = "green" if ok else "red"
    verdict = _colorize(verdict, color)
    reason = _colorize_expected_actual(reason)
    lines = [f"{verdict}: {reason}"]
    lines.append("Guarantees:")
    lines.append("- Detects tampering for fields covered by stored hashes.")
    lines.append("- Confirms basic structure and event counts.")
    lines.append("Does not guarantee:")
    lines.append("- Origin/authenticity (no signatures).")
    lines.append("- That the model actually ran or output is correct.")
    return lines


def print_report(ok: bool, reason: str) -> None:
    print("\n".join(build_report(ok, reason)))
