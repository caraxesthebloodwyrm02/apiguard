#!/usr/bin/env bash
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  python3 -m pip install uv
fi

uv sync --frozen --extra dev
uv run ruff check .
uv run pytest -q --tb=short
uvx --from build pyproject-build
