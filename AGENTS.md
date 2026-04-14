# Repository Guidelines

## Project Structure & Module Organization
This repository is for building a launcher that can run Django applications over different server protocols. The root repository is the product codebase. Use [`.codex/daphne`](/opt/worker/qzh-dlp/servicorn/.codex/daphne) as a reference implementation only, not as the primary place for new features. Keep runtime code in top-level packages as they are introduced, group protocol-specific adapters by protocol, and place shared bootstrapping logic in a common module. Put tests in a top-level `tests/` package that mirrors the source layout.

## Build, Test, and Development Commands
The repository is still being bootstrapped, so prefer simple, explicit commands and update this guide when tooling changes.

- Use `/opt/venv/servicorn` as the default virtual environment for all Python-related commands in this repository.
- `/opt/venv/servicorn/bin/python -m pip install -e .[tests]`: install the project in editable mode once packaging is added.
- `/opt/venv/servicorn/bin/pytest -v`: expected default test command for the future `tests/` suite.
- `/opt/venv/servicorn/bin/python -m servicorn`: preferred pattern for local manual runs once the package entry point exists.

If you add `tox`, `nox`, or `make` targets, document them in `README.md` and keep them aligned with this file.

## Coding Style & Naming Conventions
Use Python with 4-space indentation, type hints on public interfaces, and small modules with clear responsibilities. Name modules and functions in `snake_case`, classes in `PascalCase`, and constants in `UPPER_SNAKE_CASE`. Prefer protocol-oriented names such as `http_runner.py`, `ws_runner.py`, or `asgi_adapter.py`. If formatting tools are added, standardize on `black` and `isort` rather than mixing styles.

## Testing Guidelines
Write pytest tests next to the behavior they validate, using files named `test_*.py`. Cover protocol startup, shutdown, configuration parsing, and Django app loading with regression-focused tests. Add integration tests for each supported protocol and keep fixtures minimal. When behavior differs from Daphne or another reference server, encode that difference in tests.

## Commit & Pull Request Guidelines
Current history is minimal, so use short imperative commit subjects such as `Add HTTP protocol bootstrap`. Keep each commit focused on one behavior change. Pull requests should explain the protocol or startup path affected, list tests run, and link any issue or design note. Include logs or terminal output when changing startup behavior or CLI UX.

## Reference & Safety Notes
Do not copy large chunks from [`.codex/daphne`](/opt/worker/qzh-dlp/servicorn/.codex/daphne) without reviewing compatibility and licensing context. Treat it as design input for protocol handling, CLI ergonomics, and test ideas. Avoid committing secrets, local socket paths, or environment-specific Django settings.
