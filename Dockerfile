FROM python:3.13-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
# Note: we might need README.md if hatchling requires it
# COPY README.md ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM base AS dev
RUN uv sync --frozen
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "apiguard.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS prod
RUN useradd -r -s /bin/false apiguard
USER apiguard
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "apiguard.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
