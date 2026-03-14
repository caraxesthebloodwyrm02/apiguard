# SKILL: Resilience Integration Engineering

## Identity

**Name:** APIGuard Resilience Integration  
**Type:** Production infrastructure hardening via composable resilience primitives  
**Domain:** Python backend systems, API clients, microservice middleware  

## What This Skill Does

Systematically replaces fragile, unprotected HTTP call sites in a target codebase with production-grade resilience patterns (circuit breaking, rate limiting, retry with backoff) using the APIGuard library — without breaking existing functionality.

## Routine (Step-by-Step)

### Phase 0 — Reconnaissance
1. **Inventory the target project** — read README, pyproject.toml, middleware stack, and router structure.
2. **Identify resilience gaps** — grep for raw `httpx.Client`, `httpx.AsyncClient`, and SDK `.create()` calls that lack retry/circuit/rate-limit coverage.
3. **Map call sites** — classify each as:
   - **Direct HTTP** (swap transport) — e.g., `httpx.Client` / `httpx.AsyncClient`
   - **SDK-wrapped** (wrap at method level with CircuitBreaker) — e.g., `openai.ChatCompletion.create`
   - **Skip** — local-only calls (no network I/O)
4. **Verify APIGuard primitives** — confirm `TokenBucket`, `CircuitBreaker`, `RetryHandler`, `AsyncRateLimitedClient`, `BucketRegistry` are available and importable.

### Phase 1 — Adapter Layer
5. **Create a standalone resilience module** in the target package (e.g., `tools/rag/resilience.py`) that:
   - Imports APIGuard primitives with **lazy try/except** for graceful fallback.
   - Provides **no-op shims** (`_NoOpBreaker`, `None` buckets) when APIGuard is absent.
   - Exposes **factory functions**: `get_circuit_breaker(service)`, `get_token_bucket(service)`, `get_retry_handler(service)`, `create_async_resilient_client(service)`.
   - Uses **singleton registries** so all callers share the same health signal per service.
   - Includes a `LIMITATIONS` header per Trust Layer Rule 3.2.
6. **Avoid cross-package coupling** — the resilience module must not import from unrelated application layers (e.g., `tools/rag` must not depend on `application.mothership.middleware`).

### Phase 2 — Provider Wiring
7. **Wire direct HTTP providers** — replace raw `httpx.Client`/`AsyncClient` with `create_async_resilient_client()` or wrap sync paths with `with self._breaker:`.
8. **Wire SDK providers** — add `self._breaker = get_circuit_breaker(service)` in `__init__`, wrap each SDK call in `with self._breaker:`.
9. **Handle edge cases** — when fallback returns plain `httpx.AsyncClient`, guard calls like `_check_client()` that are APIGuard-specific with `hasattr()`.

### Phase 3 — Graceful Degradation
10. **Make all module-level imports lazy** — any file that imports APIGuard at the top level must use `try/except ModuleNotFoundError` with a `_HAS_APIGUARD` flag.
11. **Provide counter-based fallback** for rate limiting when APIGuard's `BucketRegistry` is unavailable.
12. **Ensure lazy import chains** — if File A imports File B which imports APIGuard, either make B's import lazy or make A's import of B lazy.

### Phase 4 — Validation
13. **Import smoke tests** — verify each modified module imports cleanly: `uv run python -c "from module import Class; print('OK')"`.
14. **Run existing test suites** — confirm zero regressions across unit, integration, and security tests.
15. **Write dedicated resilience tests** — cover singleton behavior, no-op fallback, guarded calls, and (when APIGuard is present) real integration.
16. **Run full regression** — `uv run pytest -q --tb=short` to confirm no new failures.

### Phase 5 — Hardening & Commit
17. **Fix pre-existing bugs found during integration** — e.g., missing RFC headers, missing test dependencies.
18. **Stage only integration-related files** — use `git add` selectively, ignore unrelated changes.
19. **Commit with conventional format** — `feat(scope): description` with itemized body.
20. **Verify commit completeness** — `git diff --cached --name-only` before commit, `git log --oneline -1` after.

## Quality Gates

| Gate | Criteria |
|------|----------|
| **G1 — No Import Crashes** | All modified modules import without error in both apiguard-present and apiguard-absent environments |
| **G2 — Zero Regressions** | Full test suite shows no new failures attributable to changes |
| **G3 — Graceful Degradation** | System functions correctly (without resilience) when apiguard is not installed |
| **G4 — Test Coverage** | Dedicated test file with ≥10 tests covering factories, no-op fallback, and guarded calls |
| **G5 — No Cross-Coupling** | Resilience module has zero imports from unrelated application layers |
| **G6 — RFC Compliance** | All 429 responses include `Retry-After` header |
| **G7 — Conventional Commit** | Single atomic commit with `feat(scope):` format |

## Anti-Patterns to Avoid

- **Hard module-level imports** of optional dependencies
- **Cross-package coupling** (e.g., `tools/` importing from `application/`)
- **Testing only the happy path** — always test the no-apiguard fallback
- **Committing unrelated changes** — stage only what belongs to the integration
- **Using `&&` in PowerShell** — use `;` instead
- **Perpetrator-voice safety patterns** — per Trust Layer Rule 1.1, use descriptive nouns not action verbs

## Metrics This Skill Optimizes

- **Provider coverage**: % of outbound HTTP call sites with resilience
- **Regression count**: Must be 0
- **Lines of code per hour**: Tracks implementation velocity
- **Test density**: Tests per modified file
- **Time to commit**: Total wall-clock from exploration to committed code
