> **Archival note (added 2026-08-04, Phase 7 DOCS-02/DOCS-03):** this is an archived v0.1.2 record; the consumer gate-return de-hack path this record names does not exist as spelled — the correct path is `weatherbot/scheduler/daemon.py`, and the enumeration is also incomplete without the producing site `weatherbot/ops/selfcheck.py`. The body below is preserved unrevised as the historical record. See `.planning/v0.1.2-MILESTONE-AUDIT.md` DOC-DRIFT-01 / DOC-DRIFT-02.

# Phase 4: Cleanup + ReadyGate fatal outcome - Research

**Researched:** 2026-07-28
**Domain:** Internal Python refactor — `Enum`/`dataclass` API evolution + package `__all__` re-export hygiene (no external packages, no I/O, no network surface)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-44 (outcome shape — return type):** Replace the `bool` return of `ReadyGate.run` with a
  three-member `ReadyOutcome` enum (`ONLINE`, `SHUTDOWN`, `FATAL`), and override `__bool__` so ONLY
  `ONLINE` is truthy. New/updated callers branch on identity (`outcome is ReadyOutcome.FATAL`);
  every existing `if gate.run(stop):` caller (WeatherBot's `ops/daemon.py` gate-return check for the
  non-fatal case) stays byte-compatible because ONLINE remains truthy and both non-online outcomes
  remain falsy. Export `ReadyOutcome` from `lifecycle/__init__.py`'s `__all__` alongside `ReadyGate`.
  - Why the `__bool__` override is the safe choice, not a magic trick: a plain enum (no override)
    makes ALL members truthy — so an un-updated `if run():` would treat both SHUTDOWN and FATAL as
    "online" and start work on shutdown. Constraining truthiness to ONLINE preserves the
    ROADMAP-locked "ok / clean-shutdown paths keep their current semantics."
  - Rejected — plain enum forcing every caller to `run() is ReadyOutcome.ONLINE`: churns every call
    site, risks the silent un-updated-caller bug above.
  - Rejected — keep `bool`, signal fatal via exception / separate attribute: reintroduces the
    stop-overload-class hack the enhancement exists to remove.

- **D-45 (fatal trigger):** Add a new explicit `fatal: bool = False` field to `HealthResult`,
  app-authored at the boundary; leave `Severity.CRITICAL` re-probe semantics UNCHANGED. The gate
  branches on `result.fatal` exactly as it already branches on the neutral `result.severity` rung —
  opaque passthrough, weather-noun-free, "app classifies, gate branches" (D-02 lifecycle litmus).
  `fatal` is additive (defaults False), so every existing `HealthResult(...)` construction and all
  current tests keep compiling and behaving identically.
  - Rejected — reuse `Severity.CRITICAL` as the fatal trigger: reverses `Severity`'s documented
    stay-alive contract and conflates "how loudly do I log this" with "is this recoverable."
  - Rejected — new `Severity.FATAL` rung above CRITICAL: forces fatalness onto the log-level axis;
    two independent concerns need two fields.

- **D-46 (fatal-path semantics):** On a failing probe, `on_fail` fires first (unchanged — the app's
  durable health-row stamp, D-02a); then if `result.fatal` is True, log the fatal event at
  `critical` and `return ReadyOutcome.FATAL` immediately — no `stop.wait()` re-probe. `on_online`
  does NOT fire (the gate never went online). This mirrors the online path's locked
  "hook → log → return" ordering. The non-fatal failing path is byte-identical to today (existing
  severity-branch log + interruptible re-probe wait). The `fatal` short-circuit sits after the
  `on_fail` invocation and before/at the severity-branch log.
  - Rejected — skip `on_fail` on the fatal path: would drop the app's durable-row stamp for the
    single most important (terminal) failure.
  - Rejected — return FATAL but still do one `stop.wait()` first: pointless latency.

- **D-47 (export scope):** Add `summon_panel` to `discord/__init__.py`'s imports + `__all__`,
  re-exported ONLY from the `discord` subpackage — NOT surfaced at the top-level
  `yahir_reusable_bot` package. The docstring is already correct and `gateway.__all__` already lists
  it, so the fix is purely the missing re-export leg (no docstring edit). RED test:
  `from yahir_reusable_bot.discord import summon_panel` (currently `ImportError`).
  - Rejected — "fix the docstring" (delete the claim instead of exporting): the success criterion
    explicitly wants the import to succeed.
  - Rejected — also re-export at top-level `yahir_reusable_bot`: unnecessary surface widening for
    an adapter-specific symbol.

### Claude's Discretion

- Exact `ReadyOutcome` member ordering / values and whether it subclasses `Enum` vs a plain class
  with `__bool__` — any impl satisfying "only ONLINE truthy, three distinct identities" is fine.
- Exact fatal-log message wording (structured, weather-noun-free, `reason`/`detail` opaque
  passthrough like the existing critical branch).
- Test file placement: a new `tests/test_ready_gate.py` for LIFE-04; SURF-01's import assertion may
  live in a small new test or extend the import-surface coverage — planner's call, provided it's
  RED-first against current source.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope. (PC-01 log secret-redaction promotion remains parked
as backlog Phase 999.5, out of this milestone.)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SURF-01 (H17) | `from yahir_reusable_bot.discord import summon_panel` succeeds; docstring, `gateway.__all__`, package `__init__` agree | Exact current-state diff identified (see "Current Code Shapes" below); one-line fix in `discord/__init__.py` matching the existing re-export idiom for `BotThread`/`build_client`/`PanelKit`/`SelectedContext` |
| LIFE-04 (H18) | `ReadyGate.run` surfaces a fatal probe result as a distinct outcome; ok/clean-shutdown paths keep semantics + emit ordering | Verified `ReadyOutcome.__bool__` override mechanics in this Python 3.12 interpreter; concrete pseudocode diff for `ready_gate.py` synthesizing D-44/D-45/D-46 against the exact current source; frozen-dataclass additive-default-field ordering verified to compile |
</phase_requirements>

## Summary

This phase is two small, independent, purely-internal Python changes with zero new external
dependencies — the entire "research" burden is precise, verified knowledge of the *current* source
shapes and the mechanics of two Python features (`Enum.__bool__` override, frozen-dataclass
field-ordering with additive defaults), not framework/library discovery. Both mechanics were
directly executed in this session's Python 3.12.3 interpreter and behave exactly as CONTEXT.md's
locked decisions assume — there is no residual risk on the "does this even work" axis.

SURF-01 is a one-line fix: `discord/__init__.py` already re-exports four symbols via the exact
idiom (`from yahir_reusable_bot.discord.gateway import BotThread, build_client`); `summon_panel`
needs to join that import line and `__all__` list, verbatim pattern, zero new code.

LIFE-04 is a contained rewrite of `ReadyGate.run`'s failing-probe branch: insert a `fatal` check
immediately after the existing `on_fail` hook call, before the existing severity-branch log,
returning a new `ReadyOutcome.FATAL` sentinel with no re-probe wait. The passing-probe branch is
untouched except its return value (`True` → `ReadyOutcome.ONLINE`), and the loop-exhausted branch
changes `return False` → `return ReadyOutcome.SHUTDOWN`. `HealthResult` gains one additive
`fatal: bool = False` field at the end of the frozen dataclass (after `severity`, which already has
a default) — dataclass field-ordering rules require defaulted fields trail non-defaulted ones, and
`severity` already established that boundary, so `fatal` is a pure append.

**Primary recommendation:** Define `ReadyOutcome` as an `Enum` (not `IntEnum` — it carries no
ordinal/comparison semantics, unlike `Severity`) in `ready_gate.py` itself (co-located with its
producer, mirroring how `Severity`/`HealthResult` live in `health.py` next to their consumer's
import), override `__bool__` to return `self is ReadyOutcome.ONLINE`, and export it from both
`ready_gate.py`'s module surface and `lifecycle/__init__.py`'s `__all__`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Fatal-outcome signaling (`ReadyOutcome`) | Library / reusable core (`lifecycle/ready_gate.py`) | — | The gate is the sole owner of the re-probe loop and its return contract; this is pure library-surface design, no host-app or I/O tier involved |
| Fatal classification (`HealthResult.fatal`) | Consuming application (host composition root, out of this repo) | Library (`health.py` DTO definition only) | D-02 lifecycle litmus: "app classifies, gate branches" — the hub defines the field's *shape*, the app decides *when* to set it True. This repo only ships the DTO field, never sets it |
| Public-surface re-export (`summon_panel`) | Library / reusable core (`discord/__init__.py`) | — | Package `__init__.py` is the sole authority for what's importable from `yahir_reusable_bot.discord`; no other tier participates |

## Standard Stack

No new packages are introduced by this phase. All work uses stdlib (`enum`, `dataclasses`) plus
already-approved dependencies already present in `pyproject.toml`.

### Core (already present, unchanged)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `enum` | 3.12 stdlib | `ReadyOutcome` enum + `__bool__` override | No third-party alternative needed; stdlib `Enum` supports method overrides on the class body, verified working in this session's interpreter |
| Python stdlib `dataclasses` | 3.12 stdlib | Additive `fatal: bool = False` field on `HealthResult` | Frozen dataclass already in use; verified additive-default-field append compiles and behaves correctly |
| `structlog` | already pinned (`>=26.1.0`) | Fatal-path critical log | Existing `_log` logger in `ready_gate.py`, no new import |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain `Enum` + `__bool__` override | `IntEnum` with `ONLINE=1`/others non-truthy-by-construction | Rejected: `IntEnum` members are truthy whenever nonzero, so a `SHUTDOWN=0` hack would be needed and `FATAL` would still need a value carefully chosen non-zero-avoiding scheme — fragile compared to an explicit `__bool__` override. Also `IntEnum` implies ordinal comparison (`<`, `>=`) which is meaningless for these three outcomes (unlike `Severity`, which genuinely wants `>=`) |
| `Enum` subclass with `__bool__` | A plain 3-value `Literal["online", "shutdown", "fatal"]` string return | Rejected: strings don't naturally support the "only ONLINE truthy" override CONTEXT.md locked (D-44), and lose identity-check ergonomics (`outcome is ReadyOutcome.FATAL` vs `outcome == "fatal"`) |
| Additive `fatal: bool` field | A new `FatalHealthResult` subtype | Rejected: reintroduces type-branching the gate would need to inspect; D-45 explicitly wants a flat additive field consistent with how `severity` was added |

**Installation:** none — no `pip install` / `uv add` step for this phase.

## Package Legitimacy Audit

**N/A — this phase installs no external packages.** Every change is internal Python (`enum`,
`dataclasses`, `__all__` list edits) using dependencies already declared and audited in prior
phases (`structlog`, `discord.py`, `pytest`, `grimp`). No `npm view` / `pip index versions` /
registry check is applicable.

## Architecture Patterns

### System Architecture Diagram

```
   Consumer app (e.g. WeatherBot daemon, out of this repo)
        │
        │  constructs ReadyGate(health_check, notifier, on_online=..., on_fail=...)
        ▼
   ┌─────────────────────────────────────────────────────────┐
   │ ReadyGate.run(stop)                                      │  yahir_reusable_bot.lifecycle.ready_gate
   │                                                           │
   │  while not stop.is_set():                                 │
   │     result = health_check()   ◄── app-injected, opaque    │
   │        │                                                  │
   │        ├─ result.ok == True ────────────────────────────► on_online hook (app: durable stamp)
   │        │                                                  │  → _log.info("bot online")
   │        │                                                  │  → notifier.ready()  (READY=1)
   │        │                                                  │  → return ReadyOutcome.ONLINE  ──► consumer: `if outcome:` / start work
   │        │                                                  │
   │        └─ result.ok == False ──────────────────────────► on_fail hook (app: durable stamp, ALWAYS fires)
   │              │                                            │
   │              ├─ result.fatal == True (NEW) ─────────────► _log.critical(fatal event)
   │              │                                            │  → return ReadyOutcome.FATAL (NEW, no re-probe) ──► consumer: `if outcome is ReadyOutcome.FATAL:` → exit / alert
   │              │                                            │
   │              └─ result.fatal == False (unchanged today) ► branch on result.severity
   │                                                            │  CRITICAL → _log.critical(...)
   │                                                            │  else     → _log.warning(...)
   │                                                            │  stop.wait(interval) ─┬─ True (stop set) → break
   │                                                            │                       └─ False → loop again (re-probe)
   │                                                            │
   │  loop exits via `break` (stop set during wait) ──────────► return ReadyOutcome.SHUTDOWN (was `False`) ──► consumer: falsy, clean-shutdown path
   └─────────────────────────────────────────────────────────┘

   yahir_reusable_bot.discord package boundary (SURF-01, unrelated data flow):
   gateway.py (__all__ includes summon_panel) ──[MISSING today]──► discord/__init__.py (__all__)
                                                    add: import + __all__ entry  ──► consumer:
                                                                   `from yahir_reusable_bot.discord import summon_panel`
```

### Recommended Project Structure

No new files/folders — both fixes land in existing modules:
```
yahir_reusable_bot/
├── lifecycle/
│   ├── ready_gate.py    # ReadyOutcome enum defined + used here; run() rewritten
│   ├── health.py        # HealthResult gains `fatal: bool = False`
│   └── __init__.py      # __all__ gains "ReadyOutcome"
└── discord/
    └── __init__.py      # imports + __all__ gain "summon_panel"

tests/
└── test_ready_gate.py   # NEW — RED-first LIFE-04 regression (Claude's discretion on exact name)
```

### Pattern 1: Enum with truthiness override (`ReadyOutcome`)
**What:** A 3-member `Enum` where only one member is truthy, via a `__bool__` override on the enum
class body.
**When to use:** When an existing `bool`-returning API must evolve to carry a third state without
breaking every `if result:` call site that only cares about the original two states collapsing to
one truthy/falsy axis.
**Example (verified working in this session, Python 3.12.3):**
```python
# Source: verified locally against this repo's exact Python 3.12.3 interpreter — see
# Verification Protocol section below for the exact commands run.
from enum import Enum

class ReadyOutcome(Enum):
    ONLINE = "online"
    SHUTDOWN = "shutdown"
    FATAL = "fatal"

    def __bool__(self) -> bool:
        return self is ReadyOutcome.ONLINE

# Byte-compatible old caller:
outcome = ReadyOutcome.SHUTDOWN
if outcome:          # False — unchanged behavior vs. old `if gate.run(stop):`
    ...

# New caller, explicit identity branch (D-44 recommended new-caller idiom):
if outcome is ReadyOutcome.FATAL:
    ...
```

### Pattern 2: Additive default field on a frozen dataclass (`HealthResult.fatal`)
**What:** Append a new field with a default value at the end of an already-partially-defaulted
frozen dataclass.
**When to use:** Whenever a DTO needs a new opt-in field without breaking any existing
positional-or-keyword construction call sites or `dataclass.__eq__`/`repr` consumers.
**Example (verified working in this session):**
```python
# Source: verified locally — dataclass field-ordering rule (all fields after the first
# defaulted field must also have defaults) already satisfied by `severity`'s existing default;
# `fatal` simply extends that same defaulted tail.
from dataclasses import dataclass
from enum import IntEnum

class Severity(IntEnum):
    WARNING = 10
    CRITICAL = 30

@dataclass(frozen=True)
class HealthResult:
    ok: bool
    reason: str
    detail: str = ""
    severity: Severity = Severity.WARNING
    fatal: bool = False          # NEW — D-45, additive, defaults False

# Every existing call site keeps compiling unchanged:
HealthResult(ok=False, reason="x")
# New call sites opt in:
HealthResult(ok=False, reason="x", severity=Severity.CRITICAL, fatal=True)
```

### Pattern 3: `ReadyGate.run`'s rewritten failing-probe branch (synthesis of D-44/D-45/D-46)
**What:** The exact ordering the planner should turn into tasks — `on_fail` unconditionally, THEN
the `fatal` short-circuit (before the existing severity-branch log), THEN (only if not fatal) the
unchanged severity-branch log + interruptible re-probe wait.
**Example (derived directly from the verified current `ready_gate.py` source + locked CONTEXT.md
decisions — not yet written to source; this is the target diff shape):**
```python
# Source: synthesis of D-44/D-45/D-46 against yahir_reusable_bot/lifecycle/ready_gate.py
# (current source read in full this session — see "Current Code Shapes" below for the
# byte-exact before-state).
def run(self, stop) -> "ReadyOutcome":
    while not stop.is_set():
        result = self._health_check()
        if result.ok:
            self._best_effort_hook(self._on_online, result, label="on_online")
            _log.info("bot online")
            self._notifier.ready()
            return ReadyOutcome.ONLINE                      # was: return True

        # Per-outcome hook fires on EVERY failing probe, fatal or not (D-46: "on_fail
        # fires first, unchanged").
        self._best_effort_hook(self._on_fail, result, label="on_fail")

        # NEW: fatal short-circuit sits BEFORE the severity-branch log (D-46).
        if result.fatal:
            _log.critical(
                "startup self-check fatal failure",
                reason=result.reason,
                detail=result.detail,
            )
            return ReadyOutcome.FATAL                        # no stop.wait() re-probe

        # Unchanged non-fatal severity-branch log (byte-identical to today).
        if result.severity >= Severity.CRITICAL:
            _log.critical(
                "startup self-check critical failure",
                reason=result.reason,
                detail=result.detail,
            )
        else:
            _log.warning(
                "startup self-check not ready",
                reason=result.reason,
                detail=result.detail,
            )
        if stop.wait(self._re_probe_interval):
            break
    return ReadyOutcome.SHUTDOWN                             # was: return False
```

### Anti-Patterns to Avoid
- **Skipping `on_fail` on the fatal path:** D-46 explicitly rejects this — it would drop the app's
  durable health-row stamp for the single most important (terminal) failure.
- **Firing `on_online` before returning `FATAL` or `SHUTDOWN`:** the gate never went online on
  either non-ONLINE path; `on_online` must fire on exactly one path (the `result.ok` branch).
- **Using `IntEnum` for `ReadyOutcome`:** invites accidental ordinal comparison (`ReadyOutcome.FATAL
  > ReadyOutcome.ONLINE`) that has no meaning here, unlike `Severity`'s genuine `>=` use.
- **Re-exporting `summon_panel` at the top-level `yahir_reusable_bot` package:** explicitly rejected
  by D-47 — Discord-adapter vocabulary stays scoped to the `discord` subpackage.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tri-state outcome with legacy-compatible truthiness | A custom class with manual `__eq__`/hashing/singleton bookkeeping | Stdlib `Enum` + `__bool__` override | `Enum` already gives free identity semantics, `repr`, hashability, and singleton members; only `__bool__` needs overriding — verified to work exactly as needed |
| Additive DTO field | A new result subtype / union type | A single additive default field on the existing frozen `dataclass` | Matches the existing precedent (`severity` was added the same way); avoids type-branching the gate would need to inspect |

**Key insight:** Both problems already have an established precedent *inside this same file/module*
(`severity`'s addition to `HealthResult`, and the existing `on_online`/`on_fail` hook-then-log
ordering in `ready_gate.py`) — the correct move is to extend the existing pattern, not invent a new
one.

## Common Pitfalls

### Pitfall 1: Forgetting `on_online` must NOT fire on the fatal path
**What goes wrong:** A naive read of "give fatal a distinct outcome" might tempt firing both hooks
symmetrically, or restructuring the loop so `on_online`'s call site moves.
**Why it happens:** The two hooks (`on_online`, `on_fail`) look parallel in the source, but they are
NOT symmetric — `on_fail` fires on every failing probe (fatal or not) while `on_online` fires only
once, on the very first passing probe.
**How to avoid:** Keep the `on_online` call site exactly where it is today (inside the `result.ok`
branch); add the fatal short-circuit only inside the `else` (failing) branch, after `on_fail`.
**Warning signs:** A test asserting `on_online` fired on a fatal-outcome test case — that test
itself would indicate the wrong design, not just a wrong implementation.

### Pitfall 2: Adding `fatal` before `severity` in the dataclass, or without a default
**What goes wrong:** Python raises `TypeError: non-default argument 'X' follows default argument`
if a non-defaulted field is added after `severity: Severity = Severity.WARNING`.
**Why it happens:** Frozen dataclasses (like all dataclasses) require every field after the first
defaulted field to also carry a default.
**How to avoid:** Append `fatal: bool = False` as the LAST field, after `severity`. Verified locally
this session — see Pattern 2 above.
**Warning signs:** Import-time `TypeError` on `yahir_reusable_bot.lifecycle.health` — would show up
immediately in `uv run pytest` collection, not a subtle runtime bug.

### Pitfall 3: `ReadyOutcome` plain-enum truthiness silently reversing consumer behavior
**What goes wrong:** If `__bool__` is forgotten (a plain `Enum` with no override), EVERY member is
truthy by default (Python objects are truthy unless `__bool__`/`__len__` says otherwise). An
un-updated WeatherBot `if gate.run(stop):` caller would then treat `SHUTDOWN` and `FATAL` as
"online" and start work during shutdown — this is the exact regression class D-44 exists to
prevent.
**Why it happens:** `Enum` members are ordinary objects; Python does not make them falsy by default
just because they're not "the first" or "the zero" member (unlike `IntEnum` where a `0`-valued
member is falsy by coincidence of `int.__bool__`).
**How to avoid:** The `__bool__` override is not optional polish — it is the load-bearing mechanism
that keeps `if gate.run(stop):` byte-compatible for existing callers. Verified in this session:
without the override, `bool(ReadyOutcome.SHUTDOWN)` and `bool(ReadyOutcome.FATAL)` would both be
`True` (plain `Enum` truthiness), which is a live regression risk worth an explicit test.
**Warning signs:** A RED-first test that constructs `ReadyOutcome.SHUTDOWN` and `ReadyOutcome.FATAL`
and asserts `bool(x) is False` for both is the correct guard here — the planner should include it
explicitly, not just an ONLINE-is-truthy assertion (an under-sampling risk: testing only the
positive case would not catch a missing/broken `__bool__`).

### Pitfall 4: Testing `summon_panel`'s re-export via `hasattr` instead of a real import
**What goes wrong:** A test like `assert hasattr(yahir_reusable_bot.discord, "summon_panel")` after
first importing `yahir_reusable_bot.discord.gateway` elsewhere in the same test session could
false-pass due to import side effects populating `sys.modules`/attribute caches in unexpected ways.
**Why it happens:** Test-order-dependent import caching is a known pytest footgun class.
**How to avoid:** The RED test should be the exact success-criterion import statement:
`from yahir_reusable_bot.discord import summon_panel` — verified this raises `ImportError` against
current source (confirmed by reading `discord/__init__.py`'s current `__all__`, which lists only
`BotThread`, `build_client`, `PanelKit`, `SelectedContext`).
**Warning signs:** A green test pre-fix would mean the test isn't actually RED — always run the new
test against unmodified `HEAD` first (this repo's established D-13 two-commit RED-first proof
convention, see `tests/test_reload.py`'s docstring for the precedent pattern).

## Code Examples

### Current code shapes (verbatim, pre-fix — read in full this session)

**`discord/__init__.py` (current, the SURF-01 defect site):**
```python
from yahir_reusable_bot.discord.gateway import BotThread, build_client
from yahir_reusable_bot.discord.panelkit import PanelKit
from yahir_reusable_bot.discord.selection import SelectedContext

__all__ = ["BotThread", "build_client", "PanelKit", "SelectedContext"]
```
Fix (one-line-idiom addition, matching the existing style exactly):
```python
from yahir_reusable_bot.discord.gateway import BotThread, build_client, summon_panel
from yahir_reusable_bot.discord.panelkit import PanelKit
from yahir_reusable_bot.discord.selection import SelectedContext

__all__ = ["BotThread", "build_client", "PanelKit", "SelectedContext", "summon_panel"]
```

**`lifecycle/__init__.py` (current — `ReadyOutcome` must join this):**
```python
from .ready_gate import ReadyGate
...
__all__ = [
    "ReadyGate",
    "SystemdNotifier",
    "HealthResult",
    "Severity",
    "LifecycleIdentity",
    "is_running_process",
    "write_pid_atomic",
    "read_pid",
]
```
Fix: add `from .ready_gate import ReadyGate, ReadyOutcome` and insert `"ReadyOutcome"` into
`__all__` (placement alongside `"ReadyGate"` per D-44's explicit instruction).

**`lifecycle/health.py`'s `HealthResult` (current, D-45 site):**
```python
@dataclass(frozen=True)
class HealthResult:
    ok: bool
    reason: str
    detail: str = ""
    severity: Severity = Severity.WARNING
```
Fix: append `fatal: bool = False` (see Pattern 2 above).

**`lifecycle/ready_gate.py`'s `ReadyGate.run` (current signature and full failing-branch body —
D-44/D-46 site):**
```python
def run(self, stop) -> bool:
    while not stop.is_set():
        result = self._health_check()
        if result.ok:
            self._best_effort_hook(self._on_online, result, label="on_online")
            _log.info("bot online")
            self._notifier.ready()
            return True
        self._best_effort_hook(self._on_fail, result, label="on_fail")
        if result.severity >= Severity.CRITICAL:
            _log.critical(
                "startup self-check critical failure",
                reason=result.reason,
                detail=result.detail,
            )
        else:
            _log.warning(
                "startup self-check not ready",
                reason=result.reason,
                detail=result.detail,
            )
        if stop.wait(self._re_probe_interval):
            break
    return False
```
Fix: see "Pattern 3" above for the full target shape.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `ReadyGate.run(stop) -> bool` (True=online, False=clean-shutdown), fatal probes re-probed forever | `ReadyGate.run(stop) -> ReadyOutcome` (ONLINE/SHUTDOWN/FATAL, only ONLINE truthy) | This phase (v0.1.2, Phase 4) | Consumers can branch on `outcome is ReadyOutcome.FATAL` directly instead of overloading a `stop` Event; WeatherBot's app-side `fatal` Event hack becomes deletable after repin |
| `discord/__init__.py` docstring claims `summon_panel` is exported but it isn't | `summon_panel` genuinely re-exported, docstring/`gateway.__all__`/package `__init__` agree | This phase | `from yahir_reusable_bot.discord import summon_panel` succeeds |

**Deprecated/outdated:** none — this is a v0.1.1→v0.1.2 internal hardening step, not a dependency
upgrade.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ReadyOutcome` should be defined in `ready_gate.py` (not `health.py`) | Architecture Patterns / Standard Stack | Low — purely a file-organization choice within Claude's Discretion per CONTEXT.md; either location satisfies the export requirement, and moving it later is a one-line import change with no behavioral impact |

**All other claims in this research were either read verbatim from current source this session, or
mechanically verified by executing the exact `Enum.__bool__` / frozen-dataclass patterns in this
repo's Python 3.12.3 interpreter** — no user confirmation needed beyond A1, which is explicitly
already flagged in CONTEXT.md as Claude's Discretion.

## Open Questions

None — CONTEXT.md's locked decisions (D-44 through D-47) fully specify the fix shape, and this
research verified every mechanical assumption those decisions depend on (enum truthiness override,
dataclass field-ordering) against the actual interpreter and actual current source. The only
remaining choices are explicitly delegated to Claude's Discretion in CONTEXT.md (member ordering,
log wording, test file placement, `ReadyOutcome`'s defining module).

## Environment Availability

**Step 2.6: SKIPPED** — this phase is a pure code-only change (internal `enum`/`dataclasses` edits
and `__all__` list edits). No new external tool, service, runtime, or package is introduced. All
existing dependencies used (`structlog`, `discord.py==2.7.1`, `pytest`, `grimp`) are already
installed and exercised by the current green suite (confirmed: `uv run pytest -q` → 71 passed in
0.27s, this session, on unmodified `HEAD`).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x (`pytest>=9.0.3`, per `pyproject.toml`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = ["."]`) |
| Quick run command | `uv run pytest tests/test_ready_gate.py tests/test_import_hygiene.py -q` (or the new SURF-01 test file, if separate) |
| Full suite command | `uv run pytest -q` (verified this session: 71 passed in 0.27s on unmodified `HEAD` — the full suite is trivially fast; "quick" and "full" are practically the same cost here) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SURF-01 | `from yahir_reusable_bot.discord import summon_panel` succeeds | unit / import-smoke | `uv run pytest tests/test_ready_gate.py::test_summon_panel_reexport_succeeds -x` (or wherever placed) | ❌ Wave 0 |
| SURF-01 | `discord/__init__.py`'s `__all__` contains `"summon_panel"` | unit | same file, a second assertion or test | ❌ Wave 0 |
| LIFE-04 | Fatal probe → `run()` returns `ReadyOutcome.FATAL`, no re-probe wait (`stop.wait` never called after fatal) | unit | `uv run pytest tests/test_ready_gate.py::test_fatal_probe_returns_fatal_outcome_no_reprobe -x` | ❌ Wave 0 |
| LIFE-04 | Fatal probe → `on_fail` fires exactly once, `on_online` never fires | unit | `uv run pytest tests/test_ready_gate.py::test_fatal_probe_fires_on_fail_not_on_online -x` | ❌ Wave 0 |
| LIFE-04 | Non-fatal failing probe path is byte-identical to today (severity-branch log + interruptible re-probe wait still fires) | unit (regression-of-no-regression) | `uv run pytest tests/test_ready_gate.py::test_non_fatal_failure_still_reprobes -x` | ❌ Wave 0 |
| LIFE-04 | Passing probe → `run()` returns `ReadyOutcome.ONLINE`; emit ordering `on_online → log → READY=1` preserved | unit | `uv run pytest tests/test_ready_gate.py::test_online_probe_returns_online_outcome_preserves_ordering -x` | ❌ Wave 0 |
| LIFE-04 | Loop-exhausted-by-`stop` path → `run()` returns `ReadyOutcome.SHUTDOWN` | unit | `uv run pytest tests/test_ready_gate.py::test_stop_set_returns_shutdown_outcome -x` | ❌ Wave 0 |
| LIFE-04 | `bool(ReadyOutcome.SHUTDOWN) is False` AND `bool(ReadyOutcome.FATAL) is False` AND `bool(ReadyOutcome.ONLINE) is True` (Pitfall 3 guard — both non-ONLINE members must be sampled, not just one) | unit | `uv run pytest tests/test_ready_gate.py::test_only_online_is_truthy -x` | ❌ Wave 0 |
| LIFE-04 | `HealthResult(ok=False, reason="x")` still constructs with `fatal` defaulting `False` (additive-field non-regression) | unit | `uv run pytest tests/test_ready_gate.py::test_health_result_fatal_defaults_false -x` (or a `test_health.py` if the planner splits it out) | ❌ Wave 0 |
| GATE-01 | Full suite + import-hygiene/litmus/grimp layering stay green | full suite | `uv run pytest -q` | ✅ (standing gate, `tests/test_import_hygiene.py` already exists) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_ready_gate.py -q` (or wherever the new tests land) — targeted, sub-second
- **Per wave merge:** `uv run pytest -q` (full suite — verified 0.27s cost, no reason to skip full-suite runs even mid-wave)
- **Phase gate:** Full suite green (`uv run pytest -q`) before `/gsd-verify-work`, including
  `tests/test_import_hygiene.py`'s three standing gates (grimp graph, isolated-import blocker,
  AST-litmus) — no new litmus exposure expected (`ReadyOutcome`, `fatal` carry no weather noun; the
  litmus test's own `test_litmus_clean` already scans `ready_gate.py` and `health.py` filenames
  explicitly, per the assertion at `tests/test_import_hygiene.py` reading `_MODULE_ROOT.rglob`
  against the hardcoded filename set `{"ready_gate.py", "sdnotify.py", "health.py", "identity.py"}`)

### Wave 0 Gaps
- [ ] `tests/test_ready_gate.py` — NEW file, covers LIFE-04's 6 test rows above (does not exist yet;
  confirmed via `find tests -iname "*ready*"` this session → no hits)
- [ ] A SURF-01 test — either a small addition to a new file or an extension of existing
  import-surface coverage (planner's call per CONTEXT.md's discretion note); no `test_discord_surface.py`-style file exists yet
- [ ] No new fixtures needed in `conftest.py` — a fatal-probe test needs a `HealthResult(ok=False,
  reason=..., fatal=True)` instance (trivial inline construction, not fixture-worthy) and a stop
  double; the existing `fake_stop_event` fixture (`_InstantStopEvent`, `wait()` always returns
  `False`) is directly reusable for the "no stop set, health-check runs" shape needed by the
  fatal-outcome and online-outcome tests. A SHUTDOWN-outcome test needs a stop double whose
  `is_set()` returns `True` immediately (or a real `threading.Event()` pre-`.set()`) — a real
  `threading.Event()` is simplest here (no `.wait()` timing sensitivity since `is_set()` is checked
  before any probe), no new fixture required.
- Framework install: none — pytest is already installed and the suite already runs green.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | no | Phase touches no authentication surface |
| V3 Session Management | no | Phase touches no session surface |
| V4 Access Control | no | Phase touches no access-control surface |
| V5 Input Validation | marginal | `HealthResult.fatal` is a `bool` set by the *app*, not user input; no validation needed beyond Python's own type system. `ReadyOutcome` enum membership is closed (3 fixed members), so no injection surface exists |
| V6 Cryptography | no | No secrets, tokens, or crypto touched by this phase (D-45's `detail` field remains outcome-only per `health.py`'s existing documented contract — "NEVER a secret" — unchanged by this phase) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Silent truthiness regression (an un-updated `if gate.run(stop):` caller misreading a new enum member as "online") | Tampering (of control-flow logic, not data) | `__bool__` override constraining truthiness to `ONLINE` only (D-44) — this is precisely the mitigation for the one real risk this phase introduces; see Pitfall 3 |

No other STRIDE-relevant pattern applies — this phase has no network input, no auth boundary, and
no persistence layer of its own.

## Sources

### Primary (HIGH confidence)
- `yahir_reusable_bot/lifecycle/ready_gate.py` (read in full this session, HEAD) — exact current
  `ReadyGate.run` source, docstrings, `_best_effort_hook`
- `yahir_reusable_bot/lifecycle/health.py` (read in full this session, HEAD) — exact current
  `HealthResult`/`Severity` source
- `yahir_reusable_bot/lifecycle/__init__.py` (read in full this session, HEAD)
- `yahir_reusable_bot/discord/__init__.py` (read in full this session, HEAD)
- `yahir_reusable_bot/discord/gateway.py` (read in full this session, HEAD) — confirms
  `summon_panel` already in `__all__`
- `.planning/phases/04-cleanup-readygate-fatal/04-CONTEXT.md` — locked decisions D-44..D-47
- `.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md` §4 (H17/H18) — fix direction + de-hack site names
- `.planning/backlog/HUB-FINDINGS-HANDOFF.md` — full failure scenario + evidence
- Local interpreter execution this session (Python 3.12.3) — `Enum.__bool__` override mechanics and
  frozen-dataclass additive-default-field append, both verified to compile and behave as CONTEXT.md
  assumes (see Bash transcript: `ONLINE truthy: True`, `SHUTDOWN truthy: False`,
  `FATAL truthy: False`, `HealthResult(ok=False, reason='x', detail='', severity=<Severity.WARNING:
  10>, fatal=False)`)
- `uv run pytest -q` executed this session on unmodified `HEAD` → `71 passed, 1 warning in 0.27s`
  (confirms current green baseline + full-suite cost)
- `tests/test_import_hygiene.py`, `tests/conftest.py`, `tests/test_reload.py`, `tests/test_gateway.py`
  (read this session) — established RED-first test-double and self-proof conventions this phase's
  new tests should follow

### Secondary (MEDIUM confidence)
None — no external documentation lookups were needed; this phase's entire technical surface is
internal source code and stdlib mechanics, both verified directly.

### Tertiary (LOW confidence)
None.

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — no new packages; stdlib mechanics verified by direct execution
- Architecture: HIGH — exact current source read in full; target diff is a direct synthesis of
  locked CONTEXT.md decisions against verified current code
- Pitfalls: HIGH — each pitfall traces to a specific, already-anticipated risk named in CONTEXT.md
  (D-44's rejected-alternatives discussion) or an established repo test-convention precedent

**Research date:** 2026-07-28
**Valid until:** No expiry pressure — this is an internal refactor with no external
version-drift risk; safe to treat as valid indefinitely for this milestone (v0.1.2, Phase 4).
