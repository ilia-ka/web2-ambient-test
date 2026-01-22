from typing import List


def build_report(ok: bool, reason: str) -> List[str]:
    verdict = "VERIFIED" if ok else "REJECTED"
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
