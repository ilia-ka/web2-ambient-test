import argparse
import sys

from receipt_verifier.receipt_io import load_receipt
from receipt_verifier.tamper import tamper
from receipt_verifier.verifier import verify


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal receipt verifier.")
    parser.add_argument("receipt", help="Path to receipt JSON file.")
    parser.add_argument(
        "--tamper",
        choices=["event", "raw", "meta"],
        help="Modify a field in-memory to demonstrate rejection.",
    )
    args = parser.parse_args()

    receipt = load_receipt(args.receipt)
    if args.tamper:
        receipt = tamper(receipt, args.tamper)

    ok, reason = verify(receipt)
    verdict = "VERIFIED" if ok else "REJECTED"
    print(f"{verdict}: {reason}")
    print("Guarantees:")
    print("- Detects tampering for fields covered by stored hashes.")
    print("- Confirms basic structure and event counts.")
    print("Does not guarantee:")
    print("- Origin/authenticity (no signatures).")
    print("- That the model actually ran or output is correct.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
