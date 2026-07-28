<!-- refreshed: 2026-07-08 -->
# Architecture

**Analysis Date:** 2026-07-08

## System Overview

`yahir_reusable_bot` is a **generic, domain-agnostic bot core** that consumer bots import as a library. It exports seven documented pluggable seams (SEAM-01 through SEAM-07) and enforces a strict one-way dependency: consumers may import from the module; the module imports zero consumer code. Everything app-specific is **injected at the consumer's composition root** via constructor-injection of opaque callables.

The architecture is **pure mechanism**: scheduler engine, config hot-reload, delivery abstraction, command registry, reliability/retry, Discord adapter, and process lifecycle. No domain nouns (weather, forecast, reminder, location) appear in any public name, enforced by an import-hygiene gate (`tests/test_import_hygiene.py`).

```text
┌─────────────────────────────────────────────────────────────┐
│          Consumer App (WeatherBot, ReminderBot, …)          │
│       Imports module, wires injection points at root         │
└─────────────────┬───────────────────────────────────────────┘
                  │ (composition root injection)
                  │
┌─────────────────▼───────────────────────────────────────────┐
│              DISCORD ADAPTER                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ BotThread (discord.Client on own thread/event loop)  │   │
│  │ build_client (intents, setup_hook, view register)   │   │
│  │ summon_panel (create-before-delete orchestration)   │   │
│  │ PanelKit (persistent-view, buttons, renders)        │   │
│  │ SelectedContext[I] (generic selection holder)       │   │
│  └──────────────────────────────────────────────────────┘   │
│  `yahir_reusable_bot/discord/`                              │
└─────────────────┬───────────────────────────────────────────┘
                  │
        ┌─────────┴──────────┬──────────────┬──────────────┐
        │                    │              │              │
        ▼                    ▼              ▼              ▼
┌──────────────┐    ┌──────────────┐ ┌──────────┐  ┌──────────────┐
│  SCHEDULER   │    │   CONFIG     │ │ REGISTRY │  │  LIFECYCLE   │
│  ENGINE      │    │   RELOAD     │ │          │  │              │
├──────────────┤    ├──────────────┤ ├──────────┤  ├──────────────┤
│ Thin facade  │    │ Validation   │ │ Command  │  │ ReadyGate    │
│ over         │    │ Atomic swap  │ │ Registry │  │ (startup     │
│ APScheduler  │    │ Job          │ │ Dispatch │  │  health      │
│              │    │ reconcile    │ │ Match    │  │  check)      │
│ register()   │    │              │ │ Bind     │  │              │
│ remove()     │    │ ReloadEngine │ │          │  │ HealthResult │
│ list_live    │    │ ConfigHolder │ │ Spec /   │  │ Severity     │
│              │    │              │ │ Context  │  │              │
└──────────────┘    └──────────────┘ └──────────┘  └──────────────┘
`scheduler/`       `config/`         `registry/`    `lifecycle/`
        │                    │              │              │
        └─────────────────────┴──────────────┴──────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│         RELIABILITY & DELIVERY                              │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────┐  ┌──────────────────────────────┐  │
│ │ Retry Engine (2x8   │  │ Channel (ABC)                │  │
│ │ burst schedule)     │  │ DeliveryResult               │  │
│ │                     │  │ - text-only send()           │  │
│ │ is_transient()      │  │ - provider-agnostic          │  │
│ │ is_auth_failure()   │  │ - retryable if ok=False      │  │
│ │ parse_retry_after() │  │                              │  │
│ │                     │  │ (impl lives in consumer)     │  │
│ │ REASON taxonomy     │  │                              │  │
│ └─────────────────────┘  └──────────────────────────────┘  │
│ `reliability/`              `channels/`                     │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│           PORTS (Abstract Seams)                            │
├─────────────────────────────────────────────────────────────┤
│ · Channel (SEAM-01)     — delivery provider                 │
│ · JobStore (SEAM-03)    — where jobs live (serialization)   │
│ · validate/desired_jobs (SEAM-04) — config schema hooks     │
│ · health_check (SEAM-05) — READY-gate callback              │
│ · registry/bind (SEAM-06) — command specs + handlers        │
│ · SelectedContext (SEAM-07) — panel selection holder        │
│                                                              │
│ `ports/`                                                    │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `BotThread` | Runs `discord.Client` on own thread + event loop; isolates health failures | `yahir_reusable_bot/discord/gateway.py` |
| `build_client` | Constructs Discord client with minimal intents + persistent-view setup | `yahir_reusable_bot/discord/gateway.py` |
| `PanelKit` | Owns persistent operator panel: buttons, renders, error isolation | `yahir_reusable_bot/discord/panelkit.py` |
| `SelectedContext[I]` | Generic holder for current panel selection state | `yahir_reusable_bot/discord/selection.py` |
| `SchedulerEngine` | Non-owning facade over APScheduler; bakes three job-option invariants | `yahir_reusable_bot/scheduler/engine.py` |
| `ConfigHolder[T]` | Lock-free reader + locked writer for live config cell | `yahir_reusable_bot/config/holder.py` |
| `ReloadEngine[T]` | Validate → atomic-swap → job-reconcile orchestrator | `yahir_reusable_bot/config/reload.py` |
| `CommandRegistry` | Immutable registry computed once from app-supplied specs | `yahir_reusable_bot/registry/registry.py` |
| `match_command` | Longest-keyword-first matcher for text dispatch | `yahir_reusable_bot/registry/match.py` |
| `ReadyGate` | Systemd-readiness gate; re-probes health check until pass | `yahir_reusable_bot/lifecycle/ready_gate.py` |
| `Retrying` (via `build_retrying`) | Two-burst retry schedule (8+8 attempts, 45-min mid-pause) | `yahir_reusable_bot/reliability/retry.py` |
| `Channel` (ABC) | Pluggable delivery interface; text-only `send()` | `yahir_reusable_bot/channels/base.py` |

## Pattern Overview

**Overall:** Constructor-injection of opaque callables over structural seams (Protocols).

**Key Characteristics:**
- **One-way dependency** — consumers import the module; the module imports zero consumer code (enforced by import-hygiene gate).
- **No default behavior** — the module assembles nothing. Every configuration point is injected: config validator, health check, command specs, delivery channel, renderer, job registrar.
- **Neutral field names** — every public surface uses generic names (`config`, `result`, `flags`, `severity`, `desired_jobs`, `bind`) — never weather/app-specific nouns.
- **Opaque injection** — the module invokes injected callables and never inspects their internals (bodies, args, returns). This enables sharing across bots with zero redesign.
- **Thread-safety by design** — `ConfigHolder.current()` is lock-free (one atomic bytecode); `replace()` is serializing. `ReloadEngine` owns orchestration; scheduler thread is external. Async/event-loop code runs on the Discord/consumer's own thread(s).

## Layers

**Discord Adapter:**
- Purpose: Bridge to Discord protocol; manage persistent operator panel, button dispatch, error isolation.
- Location: `yahir_reusable_bot/discord/`
- Contains: Gateway (client construction, panel summon), PanelKit (panel UI, command buttons), SelectedContext (selection state).
- Depends on: `discord.py==2.7.1` (exact pin), `structlog` logging, injected render/dispatch callbacks.
- Used by: Consumer app at composition root; the panel's persistent-view `custom_id` routing contract is valid only against the exact discord.py version.

**Scheduler Engine:**
- Purpose: Non-owning facade over APScheduler; enforce three invariant job-options once so they never drift across call sites.
- Location: `yahir_reusable_bot/scheduler/`
- Contains: `SchedulerEngine.register()`, `remove()`, `list_live_ids()`.
- Depends on: APScheduler instance (owned by consumer), opaque job callback.
- Used by: `ReloadEngine` (to reconcile job ids), consumer's registration loop.

**Config Reload Engine:**
- Purpose: Orchestrate hot config reload: validate → atomic-swap → job-reconcile, with all-or-nothing rollback.
- Location: `yahir_reusable_bot/config/`
- Contains: `ConfigHolder[T]` (config cell), `ReloadEngine[T]` (orchestrator).
- Depends on: Injected `validate` (consumer's schema validator), `desired_jobs` (consumer's job deriver), `register_jobs` (consumer's job registrar), scheduler engine.
- Used by: Consumer at composition root; main-loop integration point for config file changes.

**Command Registry & Dispatch:**
- Purpose: Register app-supplied command specs into immutable registry; match text, dispatch to app-injected `bind` handler.
- Location: `yahir_reusable_bot/registry/`
- Contains: `CommandSpec` (spec + bind closure), `CommandRegistry` (registry + help renderer), `match_command`, `dispatch_spec`.
- Depends on: Injected command specs, opaque `bind` closures, DispatchContext (generic bundle).
- Used by: Consumer's CLI/Discord surfaces; registry is built once at startup and frozen.

**Reliability & Retry:**
- Purpose: Two-burst retry schedule (8+8 attempts, ~45-min mid-pause); classify transient vs auth vs permanent failures; honor capped `Retry-After`.
- Location: `yahir_reusable_bot/reliability/`
- Contains: `build_retrying()`, failure classifiers (`is_transient()`, `is_auth_failure()`), reason taxonomy.
- Depends on: `tenacity` library, injected stop event for interruptibility, `httpx` for response inspection.
- Used by: Consumer's fetch/delivery retry paths (not mandatory; consumer may use directly).

**Lifecycle & Readiness:**
- Purpose: Gate systemd `READY=1` on startup health-check re-probe; provide neutral `HealthResult` + `Severity` (no domain nouns).
- Location: `yahir_reusable_bot/lifecycle/`
- Contains: `ReadyGate` (startup probe loop), `HealthResult` + `Severity` (generic health DTO), `sdnotify` (systemd integration).
- Depends on: Injected `health_check` callback, notifier (systemd or test mock), stop event.
- Used by: Consumer's main startup sequence; the gate owns only structured log + `READY=1`; side-effects (durable health row, online ping) ride injected hooks.

**Ports & Seams:**
- Purpose: Define abstract contracts every seam implements; carry serialization constraints (e.g., `JobStore` pickling rules).
- Location: `yahir_reusable_bot/ports/`
- Contains: `JobStore` Protocol (contract + docstring constraints), `Channel` re-export, error-alert callback.
- Depends on: None (pure abstract definitions).
- Used by: Composition root (selection of concrete implementations), import-hygiene gate (validation).

## Data Flow

### Primary Request Path (Discord Command)

1. **User taps Discord panel button** → Discord gateway fires `on_interaction` (bound in `build_client`).
2. **PanelKit handler** (`CmdButton.callback`) receives interaction, checks operator permission.
3. **Command dispatch** → `dispatch_spec(spec, ctx)` invokes app-injected `spec.bind(ctx)` closure off-loop.
4. **App handler** reads config via `ConfigHolder.current()` (lock-free), fetches data, may retry on transient.
5. **Result render** → `render(reply, render_arg)` (app-injected) builds embed.
6. **Panel update** → `PanelKit` edits message in-place with new embed.
7. **On error** → failure-isolation envelope catches, edits panel with error copy, logs (never crashes panel).

### Config Hot-Reload Path

1. **File watch thread** detects config change, flags `ReloadEngine._reload_requested`.
2. **Main loop** calls `service_pending(path)` (consumer-driven, not automatic).
3. **ReloadEngine.reload(path)**:
   - PHASE 1: Injected `validate(path)` parses + validates. On exception, holder + jobs untouched, exception re-raised.
   - PHASE 2: Atomic swap via `ConfigHolder.replace(new_config)`.
   - Job reconcile: compute `desired = injected_desired_jobs(new_config)`, diff vs live.
   - ADD: invoke injected `register_jobs(new_config)` (full idempotent swap).
   - REMOVE: loop through `live - desired`, call `SchedulerEngine.remove(id)`.
   - On any reconcile exception: rollback holder to old config, invoke `restore(old)` hook, re-raise.
4. **Jobs read live config** via `ConfigHolder.current()` on next fire.

### Startup Sequence

1. **ReadyGate.run(stop)**:
   - Loop: call injected `health_check()` → `HealthResult`.
   - If `result.ok`: invoke injected `on_online` hook, emit `READY=1`, return `True`.
   - Else: invoke injected `on_fail(result)` hook (durable health row), log at level `WARNING` or `CRITICAL` per `result.severity`.
   - Re-probe on `stop.wait(interval)` (interruptible).
2. **Consumer's main sequence** (e.g., WeatherBot):
   - Construct wired components at composition root.
   - Start scheduler, config reload engine, Discord thread.
   - Call `ReadyGate(health_check=…).run(stop)` → blocks until health passes.
   - Main loop: poll config changes, handle signals, tick scheduler.

### Retry Path (Fetch Failure)

1. **Fetch raises exception** (e.g., `httpx.HTTPStatusError(429)`).
2. **Retry classifier** (`is_transient()`, etc.) determines if retryable.
3. **`build_retrying()` scheduler** kicks in:
   - Burst 1: 8 attempts across ~10 min.
   - Mid-pause: ~45 min.
   - Burst 2: 8 more attempts.
   - Interruptible via injected `stop` event (no blocking sleeps).
4. **On 429 with `Retry-After`**: wait callable inspects response, honors header (capped at 120s).
5. **Exhausted**: consumer's retry handler decides (alert? keep old briefing?).

**State Management:**
- Config state: held in `ConfigHolder[T]`; jobs read live via `current()` (lock-free, consistent snapshots).
- Selection state: held in `SelectedContext[I]`; panel re-renders from selection on each tap.
- Job registry: held in APScheduler; module reconciles via `SchedulerEngine` per config reload.
- Discord message state: pinned message ID + view edits (create-before-delete ordering enforced by `summon_panel`).

## Key Abstractions

**Channel (SEAM-01):**
- Purpose: Pluggable delivery interface; text-only.
- Examples: `send(text: str) -> DeliveryResult`; consumer implements Discord, Slack, Telegram, SMS variants.
- Pattern: Abstract base class + Protocol enforcement. Module never names provider; only imports `Channel` ABC + tests result.

**JobStore (SEAM-03):**
- Purpose: Where scheduled jobs live; serialization contract for durable backends.
- Examples: `MemoryJobStore` (ships) in `yahir_reusable_bot/ports/jobstore.py`; durable `JobStore` (deferred, nameless).
- Pattern: Protocol with documented constraints (importable callback, picklable args, per-fire re-resolution). Module owns contract, not impl selection.

**ConfigHolder[T] (SEAM-04a):**
- Purpose: Generic, unbound config cell; lock-free read + serializing write.
- Examples: `current()`, `replace(new_config)`.
- Pattern: Generic TypeVar (no base class imposed); validation injected at `ReloadEngine`, not here.

**HealthResult (SEAM-05):**
- Purpose: Generic health-check outcome; neutral severity rung (no domain nouns).
- Examples: `ok: bool`, `reason: str`, `severity: Severity` (WARNING or CRITICAL).
- Pattern: Dataclass; `ReadyGate` never compares `reason` to app string, only branches on `severity`.

**CommandSpec + DispatchContext (SEAM-06):**
- Purpose: Register command specs; dispatch with generic context.
- Examples: `spec.name`, `spec.bind(ctx)`, `ctx.result`, `ctx.config`, `ctx.flags`, `ctx.daemon_state`.
- Pattern: Frozen dataclass; module never reads `bind` body, only calls it. App injects all semantics.

**SelectedContext[I] (SEAM-07):**
- Purpose: Generic holder for current panel selection state.
- Examples: `current()`, `select(item)`.
- Pattern: Generic container; re-read by app contributors on every render to derive option defaults.

## Entry Points

**Composition Root (Consumer-Supplied):**
- Location: Consumer app (e.g., WeatherBot's `weatherbot/scheduler/wiring.py`, `build_runtime()`).
- Triggers: App startup.
- Responsibilities: Import module components, wire all injection points (config validator, health check, command specs, delivery channel, panel render, job registrar), build instances, start Discord thread + scheduler, call `ReadyGate.run()`.

**Module API Surface (Public Imports):**
- `yahir_reusable_bot.discord.BotThread`, `build_client()`, `summon_panel()`
- `yahir_reusable_bot.scheduler.SchedulerEngine`
- `yahir_reusable_bot.config.ConfigHolder`, `ReloadEngine`
- `yahir_reusable_bot.registry.CommandRegistry`, `build_registry()`, `match_command()`, `dispatch_spec()`
- `yahir_reusable_bot.lifecycle.ReadyGate`, `HealthResult`, `Severity`
- `yahir_reusable_bot.reliability.build_retrying()`, failure classifiers
- `yahir_reusable_bot.channels.Channel`, `DeliveryResult`
- `yahir_reusable_bot.ports` — abstract seams

## Architectural Constraints

- **One-way dependency:** No hub file imports a consumer. Enforced by import-hygiene gate (`tests/test_import_hygiene.py`) using `grimp` graph + litmus grep + isolated-import smoke test.
- **No domain nouns in public names:** Every `def`/`class`/parameter annotation name avoids weather/app-specific terms. Docstrings/comments are prose, ignored by gate.
- **No console script:** Module ships library only (`[project.scripts]` omitted from `pyproject.toml`). Consumer app owns the entry point.
- **discord.py pin:** `discord.py==2.7.1` pinned exactly; persistent-view `custom_id` routing contract valid only against this version. Do NOT loosen.
- **APScheduler assumption:** Module owns only thin facade. Consumer builds + owns scheduler lifecycle.
- **Async threading model:** Discord client runs on own thread + event loop via `asyncio.run()` (NOT the blocking `Client.run()`). Health failures isolated; main thread unaffected.
- **Config validation injection:** Module never imports pydantic; validation routes entirely through injected `validate` callable (enforced by import-hygiene gate).
- **No global state:** All state is explicit (holders, registries, engine instances). No module-level singletons.

## Anti-Patterns

### Coupling injection points to a specific consumer

**What happens:** A future bot (ReminderBot) uses the module but the composition root bakes in WeatherBot-specific types (e.g., a validator that expects WeatherBot's `Config` class).

**Why it's wrong:** The seam becomes single-consumer, defeating the whole point of the module. The next bot either re-implements everything or rewrites the seam.

**Do this instead:** Every injected callable must carry zero consumer coupling. Use structural Protocols, generic TypeVars (`ConfigHolder[T]`, `ReloadEngine[T]`), and opaque DTOs (`DispatchContext`, `HealthResult`). The module never names the consumer's types.

### Reading app-specific fields from injected data

**What happens:** `ReloadEngine` or `ReadyGate` reads `result.reason` and compares it to `== "auth_failed"` (an app-named failure class).

**Why it's wrong:** A ReminderBot with its own failure taxonomy breaks immediately; the gate becomes a WeatherBot monopoly.

**Do this instead:** Move semantic interpretation to the boundary. Consumer's `health_check()` returns a `HealthResult` with `severity=Severity.CRITICAL` if it wants the gate to log critically — the module branches on `severity`, never on `reason`. Same for retry: consumer's code classifies via `is_transient()` + `is_auth_failure()` helpers (exported from `reliability`), then patches the exception, then raises it. Module never reads exception fields.

### Holding non-picklable runtime data in job payload

**What happens:** A job's `kwargs` holds a live `ConfigHolder` instance; serialization (for a durable `JobStore`) fails with "cannot pickle ConfigHolder".

**Why it's wrong:** Blocks the durable-store seam (SEAM-03 deferral). Jobs must round-trip through pickle unchanged.

**Do this instead:** Per-fire data that changes (config, client handle, channel reference) rides a re-resolved **registry** accessed by ID at fire time, not baked into the job. Job `args` holds picklable identity (a string id); job `kwargs` re-reads the registry on each fire. `ConfigHolder` belongs in the registry, bound to an id, not in the job.

### Importing consumer nouns into module code

**What happens:** `registry.py` has a line `if spec.group == "Forecast"` to decide dispatch behavior.

**Why it's wrong:** Hard-wires WeatherBot into the module; ReminderBot groups are different; code is not reusable.

**Do this instead:** Use a neutral field. `CommandSpec` carries `needs_flags: bool` — the module branches on this, not group name. Consumer's specs set `needs_flags=True` on specs that need it; the module never knows why.

---

*Architecture analysis: 2026-07-08*
