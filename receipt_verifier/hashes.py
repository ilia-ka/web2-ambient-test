import hashlib
import json


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: object) -> str:
    data = canonical_json(value).encode("utf-8")
    return hashlib.sha256(data).hexdigest()
