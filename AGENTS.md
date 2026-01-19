# Repository Guidelines

## Project Structure & Module Organization
This repository is a small Python script split into the `ambient_client/` package. The entry point is `main.py`, configuration is loaded in `ambient_client/config.py`, environment parsing lives in `ambient_client/env_loader.py`, and the request logic is in `ambient_client/web2_req.py`. There is no `tests/` directory yet; if the script grows, introduce a `tests/` directory for unit tests. The `.venv/` directory is a local virtual environment and is ignored by Git.

## Build, Test, and Development Commands
- `python -m pip install requests` installs the only runtime dependency used by the script.
- `python main.py` runs the request flow locally.
- No build or test commands are defined yet; add them here when you introduce a build step or test suite.

## Coding Style & Naming Conventions
Follow standard Python style (PEP 8): 4-space indentation, snake_case for functions and variables, CapWords for classes, and UPPER_CASE for constants. Keep side effects in functions and preserve the `if __name__ == "__main__":` entry point so the module can be imported safely in the future.

## Testing Guidelines
There are no tests in the repository today. If you add tests, create a `tests/` folder, use `test_*.py` naming, and document the chosen framework and coverage expectations in this section.

## Commit & Pull Request Guidelines
Git history uses Conventional Commit-style messages (e.g., `feat: complete task`). Follow the `type: short summary` format (`feat:`, `fix:`, `chore:`). For pull requests, include a concise summary, rationale, and how you validated the change (commands run or “not run”). Attach before/after output or screenshots for user-visible behavior changes.

## Security & Configuration Tips
Do not commit secrets. Use `AMBIENT_API_URL` and `AMBIENT_API_KEY` in `.env` (copy from `.env.example`) and keep `.env` out of Git.
