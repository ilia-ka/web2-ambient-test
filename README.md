# Web2 Weekly Challenges — Ambient

## Configuration
- Install dependency: `python -m pip install requests`
- Set `AMBIENT_API_URL` and `AMBIENT_API_KEY` for Ambient (toggle with `AMBIENT_ENABLED`).
- Use `AMBIENT_MODEL` and `AMBIENT_PROMPT_FILE` to control the request.
- Receipt capture: set `AMBIENT_RECEIPT_SAVE=1` to save raw stream events to `data/` (configure with `AMBIENT_RECEIPT_DIR`).
- Optional OpenAI comparison: set `OPENAI_ENABLED=1`, `OPENAI_API_KEY`, and either `OPENAI_MODEL` or `OPENAI_MODELS`. You can toggle each model with `OPENAI_MODEL_<NAME>_ENABLED=0/1`.
- Optional OpenRouter comparison: set `OPENROUTER_ENABLED=1`, `OPENROUTER_API` (or `OPENROUTER_API_KEY`), and `OPENROUTER_MODELS`. You can toggle each model with `OPENROUTER_MODEL_<NAME>_ENABLED=0/1`.

## Run Context
- Command: `python .\main.py`
- Prompt source: `prompt.txt` (AMBIENT_PROMPT_FILE)
- Providers: Ambient, OpenRouter
- Models: `zai-org/GLM-4.6`, `openai/gpt-5.2`, `deepseek/deepseek-v3.2`, `google/gemini-3-flash-preview`, `anthropic/claude-sonnet-4.5`

## Web2 Developer Loop — Micro-Challenge #4 (Activation - Emergent Behavior)
- Status: in progress.
- Goal: cost + latency reality check (Ambient vs closed API under the same constraints).
- Bench mode (reproducible runs):
  - Enable: `BENCH_ENABLED=1` (optional `BENCH_WARMUP`, `BENCH_RUNS`).
  - Output: `data/bench_<timestamp>.jsonl` (override with `BENCH_OUTPUT_DIR`).
  - Stall detection: `BENCH_STALL_THRESHOLD_MS` (default 2000 ms).
  - Shared request params: `REQUEST_TEMPERATURE`, `REQUEST_MAX_TOKENS`, `REQUEST_TOP_P`, `REQUEST_SEED`, `REQUEST_STOP`.
  - Usage in stream (if supported): `REQUEST_STREAM_INCLUDE_USAGE=1`.
- Config reference (key -> meaning -> default):
  - `BENCH_WARMUP`: warmup runs excluded from summary -> `1`
  - `BENCH_RUNS`: measured runs per model -> `3`
  - `BENCH_STALL_THRESHOLD_MS`: gap to count a stall -> `2000`
  - `REQUEST_TEMPERATURE`: sampling temperature -> unset
  - `REQUEST_MAX_TOKENS`: output cap -> unset
  - `REQUEST_TOP_P`: nucleus sampling -> unset
  - `REQUEST_SEED`: deterministic seed (if supported) -> unset
  - `REQUEST_STOP`: stop sequences -> unset
  - `REQUEST_STREAM_INCLUDE_USAGE`: stream usage if supported -> `0`
  - `REQUEST_CONTENT_MODE`: `content`, `reasoning`, or `content_or_reasoning` -> `content_or_reasoning`
  - `RUN_ON_ERROR`: `abort` or `continue` (default: abort; bench defaults to continue) -> unset
- Report:
  - Generate markdown summary: `python .\report_bench.py data\bench_<timestamp>.jsonl`
  - Or point to a directory: `python .\report_bench.py data`
  - Sort by slowest TTC: `python .\report_bench.py data --sort ttc_p50 --desc`
  - Include content/reasoning columns: `python .\report_bench.py data --include-content`

### Week 4 Results (2026-01-29)
Bench + cost summary (latency from data/bench_20260129_142659.jsonl; OpenRouter spend from dashboard, 2 runs today):
| Provider | Model | Runs | Success | TTFT p50/p90 (ms) | TTC p50/p90 (ms) | Tokens p50 | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ambient | zai-org/GLM-4.6 | 3 | 3/3 (100%) | 1189/1368 | 9192/9221 | 577 | 0.000550 (est.) |
| OpenRouter | anthropic/claude-sonnet-4.5 | 3 | 3/3 (100%) | 1916/2191 | 6128/6526 | 615 | 0.0393 |
| OpenRouter | deepseek/deepseek-v3.2 | 3 | 3/3 (100%) | 1410/17852 | 15285/22688 | 478 | 0.00229 |
| OpenRouter | google/gemini-3-flash-preview | 3 | 3/3 (100%) | 2770/2774 | 3859/4213 | 601 | 0.00654 |
| OpenRouter | openai/gpt-5.2 | 3 | 3/3 (100%) | 5624/5970 | 5905/6188 | 575 | 0.0331 |

Notes:
- All providers: 3/3 success, no stalls.
- DeepSeek showed high variance (TTFT/TTC p90 spikes).
- Ambient streamed reasoning_content; counts reflect streamed reasoning output.
- Ambient cost is estimated from testnet pricing ($0.35/M input, $1.71/M output) using p50 tokens.
- OpenRouter cost uses dashboard totals for today (2 runs); usage tokens are normalized while billing uses native tokens.
- Submission template (English):
  - Developer Loop (post in 💻│developers):
    - Bench table (paste output from `report_bench.py`):
      - Provider vs closed API summary with TTFT/TTC, reliability, stalls, and tokens.
    - Notes:
      - Cost: `...` (usage tokens coverage + pricing assumptions if any).
      - Latency: `...` (p50/p90 and variability).
      - Reliability: `...` (timeouts/stalls/parse errors).
      - Tradeoffs: `...` (verification overhead, determinism, ToS risk).
  - Community Activation (post in 📝│testnet-feedback):
    - What I tried: `...`
    - Why it required Ambient: `...`
    - What worked / didn’t: `...`
    - Lessons learned: `...`

## Web2 Developer Loop — Micro-Challenge #3 (Receipt Verification)
- Run once to capture a receipt: `python .\main.py`
- Verify a receipt: `python .\verify_receipt.py data\receipt_<...>.json`
- Simulate a rejection: `python .\verify_receipt.py data\receipt_<...>.json --tamper event`
- Other tamper modes:
  - `--tamper raw` (edits raw SSE payloads; breaks raw_events hash)
  - `--tamper meta` (edits stored hash metadata; breaks verification)
- How it works:
  - The stream writes a receipt with `events` and `raw_events`.
  - The receipt stores `events_sha256` and `raw_events_sha256` in `meta`.
  - The verifier recomputes those hashes and compares them.
  - Any change in events/raw payloads flips the hash and causes REJECTED.
- Example output (verified):
```
VERIFIED
Reason: hashes match and structure is valid
Guarantees:
- Detects tampering for fields covered by stored hashes.
- Confirms basic structure and event counts.
Does not guarantee:
- Origin/authenticity (no signatures).
- That the model actually ran or output is correct.
```
- Example output (tampered):
```
REJECTED
Reason: events_sha256 mismatch (expected=..., actual=...)
Guarantees:
- Detects tampering for fields covered by stored hashes.
- Confirms basic structure and event counts.
Does not guarantee:
- Origin/authenticity (no signatures).
- That the model actually ran or output is correct.
```

## Web2 Developer Loop — Micro-Challenge #2 Results
- Ambient (zai-org/GLM-4.6): TTFT 2608 ms, TTC 259047 ms (completed).
- OpenRouter (openai/gpt-5.2): TTFT 7570 ms, TTC 63078 ms (completed).
- OpenRouter (deepseek/deepseek-v3.2): TTFT 5489 ms, TTC 184746 ms (completed).
- OpenRouter (google/gemini-2.5-flash): TTFT 1173 ms, TTC 31088 ms (completed).
- OpenRouter (anthropic/claude-sonnet-4.5): TTFT 1926 ms, TTC 77335 ms (completed).

### Notes
- The prompt is long, so completion time is large.
- Merkle (Ambient): 06bb924abe7fc1b4675016f3b99da1d98f92876b09e3990988b2e6143bb05e3b
