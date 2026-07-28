# Testing Patterns

**Analysis Date:** 2026-07-08

## Test Framework

**Runner:**
- pytest 9.0.3+
- Config: `pyproject.toml` with `[tool.pytest.ini_options]`
  - `testpaths = ["tests"]` — look only in `tests/` directory
  - `pythonpath = ["."]` — add project root to Python path
  - `addopts = "-ra"` — show all (R=passed, A=all) in test summary

**Run Commands:**
```bash
uv run pytest                    # Run all tests in tests/
uv run pytest -v                # Verbose mode (show each test)
uv run pytest tests/test_gateway.py  # Run specific test file
uv run pytest -k test_name       # Run tests matching pattern
```

**Assertion Library:**
- Built-in `assert` statements (no external assertion library)
- Pytest assertion introspection provides detailed failure messages

**Additional Test Tools:**
- `syrupy` (5.3.4+) — snapshot testing (present in dependencies but not used yet)
- `time-machine` (2.16+) — datetime mocking (present in dependencies but not used yet)
- `grimp` (3.14+) — import graph analysis for hygiene testing

## Test File Organization

**Location:**
- All tests in `tests/` directory at repo root
- No subdirectories (flat structure)
- No conftest.py (no shared fixtures defined)

**Naming:**
- Test files: `test_*.py` (e.g., `test_gateway.py`, `test_import_hygiene.py`)
- Test functions: `test_*()` (e.g., `test_on_message_event_dispatches_to_injected_handler_not_itself()`)
- Test class methods: `test_*` (none currently in use; prefer module-level functions)

**Structure:**
```
tests/
├── test_gateway.py              # Behavioral regression tests
└── test_import_hygiene.py       # Architecture/boundary enforcement tests
```

## Test Structure

**Test function anatomy:**
```python
def test_on_message_event_dispatches_to_injected_handler_not_itself():
    """Docstring explaining what is being tested and why."""
    seen: list[object] = []

    async def app_handler(message: object) -> None:
        seen.append(message)

    client = build_client(on_message=app_handler, view=discord.ui.View())
    sentinel = object()
    asyncio.run(client.on_message(sentinel))

    assert seen == [sentinel]
```

**Patterns:**
- **Setup:** Construct test dependencies and helpers
  - Example: Define test callbacks, create sentinel objects, build client instances
  
- **Exercise:** Call the code under test
  - Example: `asyncio.run(client.on_message(sentinel))` for async code
  
- **Verify:** Assert the observable outcome
  - Example: `assert seen == [sentinel]` — check the handler was called exactly once with the right arg

- **No teardown:** Tests clean up implicitly (no fixtures, no `@pytest.fixture` decorators)

## Mocking

**Framework:** No mocking library (no `pytest-mock`, `unittest.mock`)

**Patterns:**
- **Synthetic test doubles** — define minimal test implementations inline
  - Example: `async def app_handler(message: object) -> None: seen.append(message)`
  - Reason: tests document the expected interface by showing a working implementation

- **Sentinel objects** — unique marker objects to verify identity
  ```python
  sentinel = object()
  asyncio.run(client.on_message(sentinel))
  assert seen == [sentinel]
  ```
  - Reason: proves the exact object is passed through, not a copy or transformation

- **sys.meta_path manipulation** — inject import-time blockers
  ```python
  blocker = _AppBlocker()
  sys.meta_path.insert(0, blocker)
  try:
      # test code that must NOT import weatherbot
      importlib.import_module(MODULE)
  finally:
      sys.meta_path.remove(blocker)
  ```
  - Reason: prove that app imports are actually blocked (self-proof)

- **sys.modules cleanup** — reset module cache between tests
  ```python
  finally:
      for key in [k for k in sys.modules if k.startswith(MODULE)]:
          del sys.modules[key]
  ```
  - Reason: ensure fresh import state for the next test

- **Synthetic dictionaries** — pass fake data to prove gate logic
  ```python
  synthetic = {
      "yahir_reusable_bot.channels.base": {
          "weatherbot.weather.models",  # injected leak
          "httpx",                       # legitimate import
      }
  }
  leaks = _scan_app_leaks(synthetic)
  assert leaks == [("yahir_reusable_bot.channels.base", "weatherbot.weather.models")]
  ```
  - Reason: test the scan function itself without needing a real app package

**What to Mock:**
- Minimal: only when necessary to isolate the unit under test
- Avoid: mocking unless the real object has external side effects or is expensive

**What NOT to Mock:**
- Internal functions (call the real implementation)
- Data structures (use real instances)
- Type checking — tests exercise real code, not type-checker paths

## Fixtures and Factories

**Test Data:**
- No `@pytest.fixture` decorators in use
- Data created inline in test functions
- Minimal setup; tests are self-contained

**Example from `test_gateway.py`:**
```python
seen: list[object] = []  # accumulator

async def app_handler(message: object) -> None:  # test double
    seen.append(message)

client = build_client(on_message=app_handler, view=discord.ui.View())
```

**Location:**
- No dedicated fixtures file or `conftest.py`
- Factory patterns would go in helper functions at module level if needed (none currently)

## Coverage

**Requirements:** None enforced
- No `pytest-cov` configuration
- No `.coveragerc` file
- No coverage threshold in CI

**Current State:**
- `test_gateway.py` — one behavioral regression test (1 test function)
- `test_import_hygiene.py` — architecture/boundary enforcement tests (multiple gates + self-proofs)

## Test Types

**Unit Tests:**
- Scope: individual functions (e.g., `build_client`, `summon_panel`, `match_command`)
- Approach: construct minimal dependencies, call function, assert observable output
- Example: `test_on_message_event_dispatches_to_injected_handler_not_itself()` in `test_gateway.py`

**Integration Tests:**
- Scope: cross-module boundaries (e.g., registry + dispatch + specs)
- None currently written (none in `tests/`)
- Would test: how components wire together, contract compliance across modules

**Architecture/Boundary Tests:**
- Scope: enforce structural constraints (import hygiene, no domain nouns in public surface)
- Location: `test_import_hygiene.py`
- Tools: `grimp` for import graph analysis, `ast` for signature parsing
- Self-Proofs: every gate has a "prove the test is not a no-op" counterpart
  - Example: `test_selfproof_import_gate_catches_injected_app_edge()` proves `_scan_app_leaks()` actually detects leaks

**End-to-End Tests:**
- None (would be in consumer bot repos, not the hub module)

## Common Patterns

**Async Testing:**
```python
import asyncio

async def test_function(message: object) -> None:
    seen.append(message)

# In test:
asyncio.run(test_function(sentinel))
```
- Use `asyncio.run()` to run async code in a sync test
- No `@pytest.mark.asyncio` (not configured)
- No `pytest-asyncio` plugin

**Self-Proof Tests:**
Pattern for verifying the test gate itself is not a no-op:

```python
def test_module_imports_zero_app_code():
    """Gate: no module imports app code."""
    graph = grimp.build_graph(MODULE, cache_dir=None)
    edges = {...}
    leaks = _scan_app_leaks(edges)
    assert leaks == [], f"reusable module imports app code: {detail}"

def test_selfproof_import_gate_catches_injected_app_edge():
    """Prove the gate is not a no-op: injected leak MUST be flagged."""
    synthetic = {
        "yahir_reusable_bot.channels.base": {
            "weatherbot.weather.models",  # injected leak
            "httpx",  # legitimate
        }
    }
    leaks = _scan_app_leaks(synthetic)
    assert leaks == [("yahir_reusable_bot.channels.base", "weatherbot.weather.models")]
```

- Real gate passes (no leaks in clean module)
- Self-proof deliberately injects a leak and verifies the gate flags it
- Reason: if the gate ever gets loosened to a no-op, the self-proof goes RED immediately

**Error Testing:**
- No specific error-testing pattern in current tests
- Would use: trigger the error condition, assert observable state (e.g., log output, return value)
- No `pytest.raises()` currently (exceptions bubble, not caught in utilities)

**Import Isolation Testing:**
```python
def test_module_imports_with_app_blocked():
    """Every module imports cleanly with the app namespace blocked."""
    blocker = _AppBlocker()
    sys.meta_path.insert(0, blocker)
    try:
        pkg = importlib.import_module(MODULE)
        for info in pkgutil.walk_packages(pkg.__path__, prefix=MODULE + "."):
            importlib.import_module(info.name)  # raises if any module reaches app code
    finally:
        sys.meta_path.remove(blocker)
        for key in [k for k in sys.modules if k.startswith(MODULE)]:
            del sys.modules[key]
```

- Install a meta-path finder that raises on app imports
- Walk every module under the package
- Cleanup: restore sys.meta_path, purge sys.modules
- Reason: catch TYPE_CHECKING-time app imports the grimp graph might miss

## Test Execution Context

**CI/CD:** Not configured (no `.github/workflows`, no GitLab CI, no pre-commit hooks)

**Local Development:**
```bash
uv run pytest                    # Run all tests
uv run ruff check                # Lint the code
uv run pytest tests/test_import_hygiene.py  # Run just hygiene gate
```

**Gateway Test (`test_gateway.py`):**
- Regression test for P27 (on_message recursion bug)
- Exercises the actual bot client build
- Proves the injected handler is called exactly once (not shadowed)

**Import Hygiene Tests (`test_import_hygiene.py`):**
- Three standing gates:
  1. **Grimp graph:** no `yahir_reusable_bot.*` -> `weatherbot.*` imports
  2. **Isolated import:** every module imports cleanly with app blocked
  3. **Litmus check:** no public name contains weather/domain noun
- Six total test functions:
  1. Real module passes grimp gate
  2. Config module never imports pydantic
  3. Selfproof: injected leak is flagged
  4. Real module imports with app blocked
  5. Selfproof: app import is blocked
  6. Litmus: public names pass litmus pattern

---

*Testing analysis: 2026-07-08*
