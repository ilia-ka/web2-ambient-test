from receipt_verifier.checks import verify_receipt
from receipt_verifier.result import VerificationResult


def verify(receipt: object) -> VerificationResult:
    return verify_receipt(receipt)
