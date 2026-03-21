# APIGuard Copilot Instructions

- Preserve the public library API unless the PR explicitly changes it.
- Use `uv`, not raw `pip`, for validation and CI commands.
- Keep changes compatible with the supported Python versions in `pyproject.toml`.
- Prefer focused tests for retry, circuit breaker, and adapter changes.
- Never hardcode credentials or weaken transport security behavior.
