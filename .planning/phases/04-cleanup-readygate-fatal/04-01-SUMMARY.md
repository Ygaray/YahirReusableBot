---
phase: 04-cleanup-readygate-fatal
plan: 01
subsystem: lifecycle
tags: [enum, dataclass, ready-gate, health-check, structlog]

# Dependency graph
requires:
  - phase: 03-reusable-public-surface-footguns
    provides: import-hygiene gate green, RED-first test-posture convention (D-13)
provides:
  - "ReadyOutcome enum (ONLINE/SHUTDOWN/FATAL) with __bool__ override, exported from lifecycle/__init__.py"
  - "HealthResult.fatal additive bool field (default False)"
  - "ReadyGate.run fatal short-circuit: on_fail fires, then immediate ReadyOutcome.FATAL return, no re-probe wait"
  - "Named WeatherBot de-hack sites for the human-gated v0.1.2 repin"
affects: [phase-04-plan-02, milestone-v0.1.2-close-out]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Enum + __bool__ override for tri-state truthy/falsy-compatible return values"
    - "Additive defaulted dataclass field appended after the existing defaulted tail (severity -> fatal)"

key-files:
  created:
    - tests/test_ready_gate.py
  modified:
    - yahir_reusable_bot/lifecycle/health.py
    - yahir_reusable_bot/lifecycle/ready_gate.py
    - yahir_reusable_bot/lifecycle/__init__.py

key-decisions:
  - "D-44: ReadyOutcome is a plain Enum (not IntEnum) with __bool__ returning self is ReadyOutcome.ONLINE — keeps every existing `if gate.run(stop):` caller byte-compatible"
  - "D-45: HealthResult.fatal is an additive bool = False field, orthogonal to severity (log-level axis stays independent of recoverability axis)"
  - "D-46: fatal short-circuit sits after on_fail (durable health-row stamp never dropped) and before the severity-branch log; on_online never fires on a non-ok path"

patterns-established:
  - "Tri-state enum outcome with legacy-compatible truthiness (__bool__ override) for evolving a bool-returning API without breaking callers"

requirements-completed: [LIFE-04, GATE-01]

coverage:
  - id: D1
    description: "ReadyGate.run returns ReadyOutcome.FATAL immediately on a fatal probe, with no stop.wait re-probe"
    requirement: LIFE-04
    verification:
      - kind: unit
        ref: "tests/test_ready_gate.py#test_fatal_probe_returns_fatal_outcome_no_reprobe"
        status: pass
    human_judgment: false
  - id: D2
    description: "On a fatal probe, on_fail fires exactly once and on_online never fires"
    requirement: LIFE-04
    verification:
      - kind: unit
        ref: "tests/test_ready_gate.py#test_fatal_probe_fires_on_fail_not_on_online"
        status: pass
    human_judgment: false
  - id: D3
    description: "Non-fatal failing probe path stays byte-identical to today (on_fail fires, severity-branch log fires, interruptible re-probe wait still runs)"
    requirement: LIFE-04
    verification:
      - kind: unit
        ref: "tests/test_ready_gate.py#test_non_fatal_failure_still_reprobes"
        status: pass
    human_judgment: false
  - id: D4
    description: "A passing probe returns ReadyOutcome.ONLINE with on_online -> log -> notifier.ready() ordering preserved"
    requirement: LIFE-04
    verification:
      - kind: unit
        ref: "tests/test_ready_gate.py#test_online_probe_returns_online_outcome_preserves_ordering"
        status: pass
    human_judgment: false
  - id: D5
    description: "A stop-exhausted loop returns ReadyOutcome.SHUTDOWN"
    requirement: LIFE-04
    verification:
      - kind: unit
        ref: "tests/test_ready_gate.py#test_stop_set_returns_shutdown_outcome"
        status: pass
    human_judgment: false
  - id: D6
    description: "bool(ONLINE) is True, bool(SHUTDOWN) is False, bool(FATAL) is False (both non-ONLINE members sampled)"
    requirement: LIFE-04
    verification:
      - kind: unit
        ref: "tests/test_ready_gate.py#test_only_online_is_truthy"
        status: pass
    human_judgment: false
  - id: D7
    description: "HealthResult(ok=False, reason='x') still constructs, fatal defaults False"
    requirement: LIFE-04
    verification:
      - kind: unit
        ref: "tests/test_ready_gate.py#test_health_result_fatal_defaults_false"
        status: pass
    human_judgment: false
  - id: D8
    description: "ReadyOutcome importable via `from yahir_reusable_bot.lifecycle import ReadyOutcome`, joins __all__"
    requirement: LIFE-04
    verification:
      - kind: unit
        ref: "tests/test_ready_gate.py (module-level import)"
        status: pass
    human_judgment: false
  - id: D9
    description: "Full pytest suite + import-hygiene gate (grimp/isolated-import/AST litmus) stay green; zero weather vocabulary introduced"
    requirement: GATE-01
    verification:
      - kind: unit
        ref: "uv run pytest -q (78 passed)"
        status: pass
      - kind: unit
        ref: "uv run pytest tests/test_import_hygiene.py -q (8 passed)"
        status: pass
    human_judgment: false
  - id: D10
    description: "SUMMARY names both WeatherBot de-hack sites for the human-gated repin"
    verification: []
    human_judgment: true
    rationale: "Documentation-completeness check on this SUMMARY's own content — no automated test asserts prose; verified by the grep in this plan's Task 3 <verify> block and by direct read of the 'De-hack sites' section below."

duration: 12min
completed: 2026-07-28
status: complete
---

# Phase 4 Plan 1: ReadyGate fatal outcome (LIFE-04) Summary

**ReadyGate.run now returns a three-member ReadyOutcome enum (ONLINE/SHUTDOWN/FATAL, only ONLINE truthy) instead of bool, with HealthResult gaining an additive `fatal` field so a terminal probe short-circuits without a re-probe wait.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-28T14:33:45Z (first task-file read)
- **Completed:** 2026-07-28T14:40:31Z
- **Tasks:** 3
- **Files modified:** 4 (1 new test file, 3 source files)

## Accomplishments
- `ReadyOutcome` enum (`ONLINE`/`SHUTDOWN`/`FATAL`) defined in `ready_gate.py` with a `__bool__` override constraining truthiness to `ONLINE` only — every existing `if gate.run(stop):` caller stays byte-compatible.
- `HealthResult` gains an additive `fatal: bool = False` field (D-45), orthogonal to `severity`; every existing construction keeps compiling unchanged.
- `ReadyGate.run`'s failing-probe branch grows a fatal short-circuit: `on_fail` fires first (unchanged, durable health-row stamp preserved), then if `result.fatal` is `True` the gate logs at `critical` and returns `ReadyOutcome.FATAL` immediately with no `stop.wait()` re-probe; `on_online` never fires on this path. The non-fatal failing path (severity-branch log + interruptible re-probe wait) is byte-identical to before.
- `ReadyOutcome` exported from `lifecycle/__init__.py`'s `__all__` alongside `ReadyGate`.
- RED-first proof: `tests/test_ready_gate.py` (7 tests) committed while failing (`ImportError: cannot import name 'ReadyOutcome'`) against pre-fix source, then turned green by the implementation commit.

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — write tests/test_ready_gate.py covering all LIFE-04 edges** - `175072b` (test)
2. **Task 2: GREEN — land ReadyOutcome + HealthResult.fatal + run rewrite + export** - `d7939d8` (feat)
3. **Task 3: Document the WeatherBot de-hack sites** - this SUMMARY (docs, part of plan metadata commit)

**Plan metadata:** recorded via the standard docs commit following this SUMMARY.

_Note: no refactor commit was needed — the GREEN implementation matched the target diff shape from 04-PATTERNS.md exactly on the first pass._

## Files Created/Modified
- `tests/test_ready_gate.py` - NEW. 7 RED-first LIFE-04 regression tests using hand-written stop-event doubles (`is_set()` + `wait()`) and hook/notifier order-recorders — no `unittest.mock`/`pytest-mock`, matching the repo's standing convention.
- `yahir_reusable_bot/lifecycle/health.py` - `HealthResult` gains `fatal: bool = False` as the last field, plus a docstring addition documenting it as orthogonal to `severity`.
- `yahir_reusable_bot/lifecycle/ready_gate.py` - `ReadyOutcome` enum defined (after `RE_PROBE_INTERVAL_S`, before `class ReadyGate`); `run`'s return type is now `ReadyOutcome`; the failing-probe branch gains the fatal short-circuit; docstring updated to describe all three outcomes.
- `yahir_reusable_bot/lifecycle/__init__.py` - imports and re-exports `ReadyOutcome` alongside `ReadyGate` in `__all__`.

## Decisions Made
- Followed CONTEXT.md's locked D-44/D-45/D-46 exactly as specified; no gray areas required a fresh decision during execution.
- Kept `ReadyOutcome` defined in `ready_gate.py` (not `health.py`) per RESEARCH.md's Assumption A1 (co-located with its producer, Claude's Discretion).
- Added a short docstring note to `HealthResult.fatal` beyond the plan's minimum ("append the field only") — judged non-scope-creep documentation hygiene consistent with the rest of the file's existing doc density; no behavior change.

## Deviations from Plan

None - plan executed exactly as written. The implementation matched 04-PATTERNS.md's target diff shape (Pattern 3) on the first pass; no auto-fixes, no blocking issues, no architectural questions arose.

## Issues Encountered
None.

## De-hack sites for the v0.1.2 repin

This phase ships the hub-side `ReadyOutcome.FATAL` mechanism only. It does **not** touch
WeatherBot. Per `ECOSYSTEM.md` §3, the `pyproject.toml` version bump (`0.1.1` -> `0.1.2`), the
`v0.1.2` tag cut, and the WeatherBot repin (`[tool.uv.sources]` bump -> `uv lock --upgrade` ->
`uv sync` -> deploy) are **human-gated** — surfaced here for confirmation, never performed
autonomously by this plan or this phase.

After that repin lands, WeatherBot can collapse its app-side `fatal` `threading.Event` workaround
onto `ReadyOutcome.FATAL` at exactly two consumer sites (per `HUB-HARDENING-REPORT-v0.1.2.md` §4
and `04-CONTEXT.md` §specifics):

1. **`weatherbot/scheduler/wiring.py` `_on_fail`** (fatal branch) — deletes the separate `fatal`
   `threading.Event` it currently sets/checks to signal a terminal probe out-of-band; after the
   repin it can branch directly on the hub's `ReadyOutcome.FATAL` return value instead.
2. **`weatherbot/ops/daemon.py`** — the gate-return exit-code check currently inspects the
   overloaded stop/fatal `Event` pair; after the repin it consumes `ReadyOutcome.FATAL` directly
   from `ReadyGate.run`'s return value to decide its process exit code.

No autonomous bump/tag/repin task exists anywhere in this phase's plans.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- LIFE-04 (H18) and GATE-01's per-phase gate for Phase 4 Plan 1 are both closed: full suite (78 passed) and `tests/test_import_hygiene.py` (8 passed) green.
- The remaining Phase 4 plan (SURF-01, H17 — `summon_panel` re-export) is independent and unblocked by this plan.
- Once all Phase 4 plans are done, the milestone's human-gated close-out (bump/tag/repin, including the two de-hack sites named above) is ready to surface for confirmation.

---
*Phase: 04-cleanup-readygate-fatal*
*Completed: 2026-07-28*
