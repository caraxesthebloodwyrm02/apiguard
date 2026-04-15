# Contributing to APIGuard

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Git 2.30+

## Setup

```bash
git clone https://github.com/GRID-INTELLIGENCE/APIGuard.git
cd APIGuard
uv sync --group dev --group test
```

## Development

```bash
# Run tests
uv run pytest -q --tb=short

# Lint
uv run ruff check .

# Format
uv run ruff format .
```

## License

MIT License - see [LICENSE](LICENSE)
