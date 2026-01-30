import json
from pathlib import Path
from typing import Dict, Iterable, List


def iter_paths(values: List[str]) -> Iterable[Path]:
    for raw in values:
        path = Path(raw)
        if path.is_dir():
            yield from sorted(path.glob("bench_*.jsonl"))
        else:
            yield path


def load_run_records(paths: List[str], include_warmup: bool) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []
    for path in iter_paths(paths):
        if not path.exists():
            print(f"Warning: {path} does not exist, skipping.")
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                print(f"Warning: Invalid JSON in {path}, skipping line.")
                continue
            if record.get("type") != "run":
                continue
            if not include_warmup and record.get("warmup"):
                continue
            records.append(record)
    return records
