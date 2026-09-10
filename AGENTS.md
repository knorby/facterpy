# AGENTS.md

Guidance for AI agents (and humans) working on facterpy.

## What this is

`facterpy` is a zero-dependency Python library that wraps the `facter` command-line utility (Puppet's system fact collector). It shells out to `facter`, prefers JSON output (facter 3.0+) with automatic fallback to plain-text parsing, and exposes a cached, dictionary-like interface.

- The entire library lives in `facter/__init__.py` — one module, stdlib only. Keep it that way.
- `tests/test_facter.py` — unit tests (all `subprocess.run` calls mocked).
- `tests/test_integration.py` — real-facter integration tests; auto-skip when the `facter` binary is missing.

## Environment

- Python **3.11+** (`requires-python = ">=3.11"`).
- Integration tests need `facter` on PATH (e.g. `brew install facter`, `apt install facter`).
- No project venv is committed; `uv run --with pytest,pytest-cov` works fine for quick runs.

## Commands

```bash
# Run all tests (unit + integration + doctests)
pytest

# Unit tests only, fast
pytest tests/test_facter.py

# Coverage
pytest --cov=facter --cov-report=term-missing

# Lint and format (ruff handles both)
ruff check .
ruff format --check .   # add --fix / plain `ruff format .` to apply

# Type check
mypy facter/

# Everything CI checks, via pre-commit
pre-commit run --all-files
```

Install dev tools with `pip install -e .[dev]` (mypy, pytest, pytest-cov, ruff, pre-commit).

## Conventions

- Formatting and import sorting: ruff (line length 88). Do not introduce black — ruff-format replaces it.
- Type hints: modern syntax (`dict[str, Any]`, `X | None`, `collections.abc.Iterator`). mypy runs strict-ish (see `[tool.mypy]` in `pyproject.toml`).
- API stability: the public `Facter` class API is kept backward compatible. Deprecated `use_yaml` parameter and `uses_yaml` property must stay (they only warn).
- Exceptions: `subprocess.TimeoutExpired` propagates from `run_facter()`; the text-parse fallback path raises `RuntimeError` on nonzero exit.

## Release process

Releases are manual, versioned in `pyproject.toml` (`[project] version`):

1. Bump `version`, update README if compatibility notes changed.
2. Trigger the **Create GitHub Release** workflow (workflow_dispatch) — it tags `v<version>`, builds, and creates the GitHub release.
3. The release publication triggers **Publish to PyPI** (trusted publishing, no tokens).

CI runs on pushes/PRs to `main` only; the stale `master` branch is not active.
