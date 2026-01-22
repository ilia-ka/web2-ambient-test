# Streaming Report (Ambient + OpenRouter)

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
- Models: `zai-org/GLM-4.6`, `openai/gpt-5.2`, `deepseek/deepseek-v3.2`, `google/gemini-2.5-flash`, `anthropic/claude-sonnet-4.5`

## Receipt Verification (Micro-Challenge #3)
- Run once to capture a receipt: `python .\main.py`
- Verify a receipt: `python .\verify_receipt.py data\receipt_<...>.json`
- Simulate a rejection: `python .\verify_receipt.py data\receipt_<...>.json --tamper event`
- Guarantees:
  - Detects tampering for fields covered by stored hashes.
  - Confirms basic structure and event counts.
- Does not guarantee:
  - Origin/authenticity (no signatures).
  - That the model actually ran or output is correct.

## Results
- Ambient (zai-org/GLM-4.6): TTFT 2608 ms, TTC 259047 ms (completed).
- OpenRouter (openai/gpt-5.2): TTFT 7570 ms, TTC 63078 ms (completed).
- OpenRouter (deepseek/deepseek-v3.2): TTFT 5489 ms, TTC 184746 ms (completed).
- OpenRouter (google/gemini-2.5-flash): TTFT 1173 ms, TTC 31088 ms (completed).
- OpenRouter (anthropic/claude-sonnet-4.5): TTFT 1926 ms, TTC 77335 ms (completed).

## Notes
- The prompt is long, so completion time is large.
- Merkle (Ambient): 06bb924abe7fc1b4675016f3b99da1d98f92876b09e3990988b2e6143bb05e3b
