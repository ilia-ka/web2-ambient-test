from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    reason: str
    expected: Optional[str] = None
    actual: Optional[str] = None
