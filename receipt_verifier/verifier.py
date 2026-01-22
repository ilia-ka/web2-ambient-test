from typing import Tuple

from receipt_verifier.checks import verify_receipt


def verify(receipt: object) -> Tuple[bool, str]:
    return verify_receipt(receipt)
