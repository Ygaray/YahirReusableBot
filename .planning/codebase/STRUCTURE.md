# Codebase Structure

**Analysis Date:** 2026-07-08

## Directory Layout

```
yahir_reusable_bot/
├── __init__.py                    # Module boundary; one-way dependency contract
├── discord/                       # Discord adapter (SEAM-07 + gateway + panel)
│   ├── __init__.py
│   ├── gateway.py                 # BotThread, build_client(), summon_panel()
│   ├── panelkit.py                # PanelKit (persistent view + buttons + render)
│   └── selection.py               # SelectedContext[I] (selection state holder)
├── scheduler/                     # Scheduler facade (SEAM-03 job coordination)
│   ├── __init__.py
│   └── engine.py                  # SchedulerEngine (thin APScheduler wrapper)
├── config/                        # Config reload orchestration (SEAM-04)
│   ├── __init__.py
│   ├── holder.py                  # ConfigHolder[T] (lock-free cell)
│   └── reload.py                  # ReloadEngine[T] (validate → swap → reconcile)
├── channels/                      # Delivery abstraction (SEAM-01)
│   ├── __init__.py
│   └── base.py                    # Channel (ABC) + DeliveryResult
├── registry/                      # Command registry & dispatch (SEAM-06)
│   ├── __init__.py
│   ├── spec.py                    # CommandSpec + DispatchContext (frozen specs)
│   ├── registry.py                # CommandRegistry (immutable, computed once)
│   ├── match.py                   # match_command() (longest-keyword-first)
│   └── dispatch.py                # dispatch_spec() + dispatch_reply()
├── reliability/                   # Retry engine (RELY-01/02)
│   ├── __init__.py
│   └── retry.py                   # build_retrying(), classifiers, reason taxonomy
├── lifecycle/                     # Startup health + readiness (SEAM-05)
│   ├── __init__.py
│   ├── ready_gate.py              # ReadyGate (startup probe loop)
│   ├── health.py                  # HealthResult + Severity (generic health DTO)
│   ├── sdnotify.py                # systemd-notify integration
│   └── identity.py                # Process identity guard
└── ports/                         # Abstract seams / contracts (SEAM-01, SEAM-03)
    ├── __init__.py
    ├── jobstore.py                # JobStore Protocol + MemoryJobStore
    ├── alerts.py                  # Error-alert callback interface
    └── occurrence.py              # Occurrence data interface

tests/
├── test_import_hygiene.py         # One-way dependency + litmus gates
├── test_gateway.py                # Discord gateway tests
└── (additional test files as needed)

scripts/
├── new_consumer.py                # Scaffolder for new consumer bots

.planning/
├── codebase/                      # Codebase mapping documents (this directory)
│   ├── ARCHITECTURE.md
│   └── STRUCTURE.md
└── (project planning files)

pyproject.toml                      # Build config + exact dependencies
ECOSYSTEM.md                        # Multi-repo constitution (hub + consumers)
EXTENSION-GUIDE.md                  # Seam reference + extension points
CLAUDE.md                           # Project instructions
```

## Directory Purposes

**`yahir_reusable_bot/`:**
- Purpose: Root package; public API surface; defines module boundary and one-way dependency.
- Contains: Subpackage `__init__.py` docstrings + re-exports of public API.
- Key files: `__init__.py` (module docstring enforcing D-01 contract).

**`discord/`:**
- Purpose: Discord protocol adapter; Discord client lifecycle, gateway event handlers, persistent operator panel, command button dispatch, UI state holder.
- Contains: `BotThread` (client on own thread), `build_client()` (intents + setup), `summon_panel()` (create-before-delete), `PanelKit` (panel view + buttons + renders), `SelectedContext[I]` (selection holder).
- Key files: `gateway.py` (entry point for Discord wiring), `panelkit.py` (UI logic, error isolation).

**`scheduler/`:**
- Purpose: Thin facade over APScheduler; enforce invariant job options once.
- Contains: `SchedulerEngine` (register, remove, list_live_ids).
- Key files: `engine.py` (bakes `misfire_grace_time=None`, `coalesce=True`, `max_instances=1`).

**`config/`:**
- Purpose: Config hot-reload plumbing; atomic config swap + job reconcile on reload.
- Contains: `ConfigHolder[T]` (generic config cell), `ReloadEngine[T]` (orchestration).
- Key files: `holder.py` (lock-free read, serializing write), `reload.py` (validate → swap → reconcile).

**`channels/`:**
- Purpose: Delivery abstraction; pluggable provider interface (text-only).
- Contains: `Channel` (ABC), `DeliveryResult` (outcome DTO).
- Key files: `base.py` (interface + contract docstring; consumer implements providers).

**`registry/`:**
- Purpose: Command spec registration + dispatch; command matching + result binding.
- Contains: `CommandSpec` (frozen spec), `CommandRegistry` (immutable registry), `DispatchContext` (generic dispatch args), matchers + dispatchers.
- Key files: `spec.py` (specs + context), `registry.py` (registry builder), `match.py` (matcher), `dispatch.py` (dispatch orchestration).

**`reliability/`:**
- Purpose: Retry scheduling + failure classification; two-burst retry engine.
- Contains: `build_retrying()` (return tenacity `Retrying` object), classifiers (`is_transient()`, `is_auth_failure()`), reason taxonomy, `Retry-After` parser.
- Key files: `retry.py` (single file; imports `tenacity`).

**`lifecycle/`:**
- Purpose: Process startup + health readiness; systemd integration; process identity.
- Contains: `ReadyGate` (startup probe), `HealthResult` + `Severity` (generic health DTO), systemd-notify notifier, process identity guard.
- Key files: `ready_gate.py` (gate logic), `health.py` (DTO), `sdnotify.py` (systemd-notify), `identity.py` (identity guard).

**`ports/`:**
- Purpose: Abstract interface definitions (Protocols) + serialization contracts.
- Contains: `JobStore` (Protocol + constraints docstring), `MemoryJobStore` (shipped impl), error-alert callback interface, occurrence data interface.
- Key files: `jobstore.py` (contract + shipped impl), `__init__.py` (public re-exports).

**`tests/`:**
- Purpose: Module test suite; import-hygiene enforcement.
- Contains: Import-hygiene gates (`grimp` graph, litmus grep, isolated-import smoke), unit tests, integration tests.
- Key files: `test_import_hygiene.py` (one-way dependency + litmus guards; self-proofs included).

**`scripts/`:**
- Purpose: Developer utilities; consumer scaffolding.
- Contains: `new_consumer.py` (bootstraps new consumer bot repo with correct structure + hub pin).
- Key files: `new_consumer.py` (invoked as `python3 scripts/new_consumer.py <BotName>`).

## Key File Locations

**Entry Points:**
- `yahir_reusable_bot/__init__.py`: Module boundary docstring (D-01 one-way dependency contract).
- `yahir_reusable_bot/discord/gateway.py`: Discord adapter entry; consumer calls `build_client()` + `BotThread()` here.
- `yahir_reusable_bot/config/reload.py`: Config reload entry; consumer instantiates `ReloadEngine` here.
- `yahir_reusable_bot/registry/registry.py`: Command registry entry; consumer calls `build_registry()` here.
- `yahir_reusable_bot/lifecycle/ready_gate.py`: Startup readiness entry; consumer calls `ReadyGate().run(stop)` here.

**Configuration:**
- `pyproject.toml`: Build config, exact dependencies (`discord.py==2.7.1` pinned), dev tools, entry point config (NO `[project.scripts]`; library-only).
- `ECOSYSTEM.md`: Multi-repo constitution; hub + consumer shape; cross-repo jurisdiction; tier classification (litmus).
- `EXTENSION-GUIDE.md`: Seam reference; each SEAM-01 through SEAM-07 with status (implemented/deferred) + examples.
- `CLAUDE.md`: Project-specific instructions; one-way dependency rule; toolchain (uv, Python 3.12+, pytest, ruff, grimp).

**Core Logic:**
- `yahir_reusable_bot/config/holder.py`: Lock-free config cell; load-bearing concurrency contract.
- `yahir_reusable_bot/config/reload.py`: Atomic config swap + job reconcile orchestration.
- `yahir_reusable_bot/discord/panelkit.py`: Persistent panel logic; live-routing trap fix; clone path rebuilds callbacks.
- `yahir_reusable_bot/registry/registry.py`: Immutable registry + help renderer.
- `yahir_reusable_bot/reliability/retry.py`: Two-burst retry + failure classification + `Retry-After` parsing.

**Testing:**
- `tests/test_import_hygiene.py`: One-way dependency gate (`grimp`), litmus grep (no domain nouns), isolated-import smoke, self-proofs.
- `tests/test_gateway.py`: Gateway (BotThread, build_client, summon_panel) integration tests.

## Naming Conventions

**Files:**
- Lowercase with underscores: `gateway.py`, `panelkit.py`, `holder.py`, `ready_gate.py`.
- Test files: `test_*.py` (pytest discovery convention).
- Utility scripts: `new_consumer.py` (imperative verb + noun).

**Directories:**
- Lowercase, plural when natural plural concept: `discord/`, `channels/`, `lifecycle/` (abstract concept), `ports/` (abstract seam names).
- Single-concept naming: `config/`, `scheduler/`, `registry/`, `reliability/`.
- Avoid domain nouns: `channels/` not `delivery_channels/`, `registry/` not `command_registry/` (name scope implicit in import path).

**Functions:**
- `build_*` for constructors/factories: `build_client()`, `build_registry()`, `build_retrying()`.
- `is_*` for predicates: `is_transient()`, `is_auth_failure()`.
- Verb + noun / descriptive: `match_command()`, `dispatch_spec()`, `dispatch_reply()`, `summon_panel()`, `parse_retry_after()`.
- CONSTANTS: Lowercase with underscores: `BURST_SIZE`, `MID_PAUSE_S`, `REQUIRED_PANEL_PERMS`.

**Classes:**
- PascalCase: `BotThread`, `SchedulerEngine`, `ConfigHolder`, `ReloadEngine`, `CommandRegistry`, `CommandSpec`, `DispatchContext`, `HealthResult`, `Severity`, `Channel`, `DeliveryResult`, `PanelKit`, `CmdButton`, `SelectedContext`, `ReadyGate`, `MemoryJobStore`.
- ABC subclasses: no prefix (just `Channel`, `JobStore` Protocol).
- Protocols (structural seams): no prefix; names match what they represent.

**Type Variables:**
- Single capital letter: `T` (generic config type in `ConfigHolder[T]`, `ReloadEngine[T]`), `I` (generic selection item type in `SelectedContext[I]`).
- Intentionally unbound (no bounds) where polymorphism across bots is needed (e.g., `T` in `ConfigHolder[T]` — a reminder bot's config is different from weather bot's; no shared base).

**Module-Private:**
- Prefix underscore: `_log` (structlog logger), `_WATCH_QUIET_MS` (internal timing constant), `_LITMUS` (litmus regex pattern), `_safe_error_edit()` (error edit helper in panelkit).

## Where to Add New Code

**New Feature (e.g., a new reliability pattern):**
- Implementation: `yahir_reusable_bot/reliability/`
- Tests: `tests/test_reliability.py` or `tests/test_<feature>.py`
- Entry point: Re-export public function/class in `yahir_reusable_bot/reliability/__init__.py`
- Verify: Pass import-hygiene gate; no domain nouns; no consumer imports.

**New Seam/Extension Point (e.g., a second Channel provider):**
- Abstract interface: Already exists in hub (e.g., `Channel` ABC in `yahir_reusable_bot/channels/base.py`).
- Concrete implementation: Build in consumer's `_promotable/` subpackage (hub-clean), then promote to hub via `git mv` once proven.
- Promotion criteria: Litmus check (generic, reusable, no consumer imports), consumer suite passes, hub suite passes, new hub test covers it.

**New Internal Seam/Module Component (e.g., a new lifecycle piece):**
- Location: Appropriate subpackage (`yahir_reusable_bot/lifecycle/`, `yahir_reusable_bot/config/`, etc.).
- Pattern: Constructor-injection of opaque callables; no consumer coupling; neutral field/parameter names.
- Re-export: Add to subpackage `__init__.py` + top-level `yahir_reusable_bot/__init__.py` if public.
- Tests: Add to `tests/test_<subpackage>.py`.
- Verify: Import-hygiene gate, no domain nouns.

**Config/Build Changes:**
- `pyproject.toml`: Dependency changes, Python version bump, build-backend change.
- Constraint: `discord.py==2.7.1` is immutable (persistent-view wire contract); never loosen to range.
- Dev tooling: `pytest`, `ruff`, `grimp`, `syrupy` (snapshots), `time-machine` (time-mocking).

## Special Directories

**`.planning/codebase/`:**
- Purpose: Codebase mapping documents (consumed by GSD planner/executor).
- Generated: Yes (by `/gsd-map-codebase` skill).
- Committed: Yes (reference docs for future work).

**`graphify-out/`:**
- Purpose: Codebase call-graph cache (from `/gsd-graphify` analysis).
- Generated: Yes (by `/gsd-graphify`).
- Committed: No (temporary analysis artifacts; safe to delete and re-generate).

**`.pytest_cache/` / `__pycache__/` / `.venv/`:**
- Purpose: Build artifacts, virtual environment.
- Generated: Yes (by pytest, Python, uv).
- Committed: No (`.gitignore`-d).

**`dist/`:**
- Purpose: Built distribution (wheel, sdist).
- Generated: Yes (by `uv build` or `hatchling build`).
- Committed: No (build output; re-generated per release).

## Module Organization Notes

**One import root:** Consumers import from `yahir_reusable_bot` only (or its subpackages directly). No internal paths like `yahir_reusable_bot._internal.something` escape to consumers.

**Public vs. internal:** Every public function/class is re-exported in its subpackage `__init__.py` and often the top-level `yahir_reusable_bot/__init__.py` for convenience. Module-private helpers use underscore prefix and live in implementation files.

**Seam design:** Abstract Protocols (`Channel`, `JobStore`) live in `ports/` or their natural home (e.g., `Channel` in `channels/`). The protocol is the contract; implementations are consumer-side or promoted from consumer `_promotable/`.

**Test isolation:** Import-hygiene gate runs on every phase (enforced by CI / local pre-commit hook). Tests import no consumer code. A new test that accidentally imports `weatherbot` will fail the gate immediately.

---

*Structure analysis: 2026-07-08*
