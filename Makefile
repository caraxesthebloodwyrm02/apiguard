# Makefile for APIGuard

.PHONY: help install run test lint format

help:
	@echo "APIGuard Development Commands"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install:
	uv sync

run:
	uv run python -m apiguard

test:
	uv run pytest tests/ -q --tb=short

lint:
	uv run ruff check .

format:
	uv run ruff format .
