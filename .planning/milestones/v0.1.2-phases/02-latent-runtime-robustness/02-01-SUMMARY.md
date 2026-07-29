---
phase: 02-latent-runtime-robustness
plan: 01
subsystem: infra
tags: [config-reload, hooks, error-handling, hub-library]

# Dependency graph
requires:
  - phase: 01-reachable-reliability
    provides: D-11 no-mocking-library house style, D-13 two-commit RED-first idiom, D-16 both-levels assertion habit, D-17 hub-assertable-observable discipline, tests/conftest.py foundation
provides:
  - "ReloadEngine.reload PHASE-2 reconcile-failure path now fires on_rejected before re-raising"
  - "tests/test_reload.py — first-ever unit coverage for yahir_reusable_bot/config/reload.py"
affects: [02-02, 02-03, human-gated close-out (repin note)]

# Tech tracking
tech-stack:
  added: []
  patterns: ["fire-before-reraise best-effort hook reused verbatim on a second rejection path"]

key-files:
  created: [tests/test_reload.py]
  modified: [yahir_reusable_bot/config/reload.py]

key-decisions:
  - "D-31: fire _best_effort_hook(self._on_rejected, exc, label=\"reconcile-rolled-back\") before the PHASE-2 raise, mirroring PHASE-1's fire-before-reraise order (log -> restore -> fire hook -> raise)"
  - "D-32: reuse the same on_rejected hook, no new public surface — distinctness lives only in the internal log label"

patterns-established:
  - "Fire-before-reraise best-effort hook pattern now applied on both rejection paths (PHASE-1 validate-reject and PHASE-2 reconcile-rolled-back) in ReloadEngine.reload"

requirements-completed: [CFG-01]

coverage:
  - id: D1
    description: "PHASE-2 reconcile failure fires on_rejected exactly once with the reconcile exception, before re-raising the ORIGINAL (unmasked) exception, with the holder + injected restore both rolled back to old_cfg"
    requirement: "CFG-01"
    verification:
      - kind: unit
        ref: "tests/test_reload.py#test_reconcile_failure_fires_on_rejected_once_and_rolls_back"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-07-27
status: complete
---

# Phase 2 Plan 1: CFG-01 reconcile-reject alert fix Summary

**PHASE-2 reconcile-failure path in `ReloadEngine.reload` now fires `on_rejected` before re-raising, matching the PHASE-1 precedent exactly — closed via RED-first two-commit proof, reusing `_best_effort_hook` verbatim.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-27T22:25Z (approx.)
- **Completed:** 2026-07-27T22:30Z
- **Tasks:** 2 (RED test, GREEN fix)
- **Files modified:** 2 (1 created: `tests/test_reload.py`; 1 modified: `yahir_reusable_bot/config/reload.py`)

## Accomplishments
- First-ever unit coverage for `config/reload.py` (`tests/test_reload.py`), proving the PHASE-2 reconcile-failure path's full contract in one test: exactly-once hook fire, correct exception identity, holder rollback, and injected-restore call — all in the same test per D-16's both-levels habit.
- `ReloadEngine.reload`'s PHASE-2 `except Exception:` block now binds the reconcile exception (`except Exception as exc:`) and fires `self._best_effort_hook(self._on_rejected, exc, label="reconcile-rolled-back")` immediately before the existing `raise`, closing CFG-01 (H03): a rejected reload is now operator-visible on BOTH rejection paths, not just PHASE-1 validation.
- Rollback/restore ordering (`reload.py:150-157`) stays byte-identical; the ORIGINAL reconcile exception is confirmed (by the test) to still be the one that propagates — the best-effort hook guard (`_best_effort_hook`, reused verbatim, unmodified) cannot mask it.
- Docstring for `reload()` updated to state the D-31/D-32 contract inline (house style: rationale lives in the docstring, not just the commit message).

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — test_reload.py asserts on_rejected fires once before re-raise + rollback** - `4853c78` (test)
2. **Task 2: GREEN — fire on_rejected before the PHASE-2 re-raise** - `3bcd174` (fix)

**RED-first two-commit ancestry (D-13) confirmed:** `3bcd174`'s direct parent is `4853c78` (test-only commit, touches only `tests/test_reload.py`).

## Files Created/Modified
- `tests/test_reload.py` - NEW. One test function (`test_reconcile_failure_fires_on_rejected_once_and_rolls_back`) constructing a real `ReloadEngine` with all collaborators hand-injected (a fake scheduler-engine double + plain closures per the house no-mocking-library style, D-11); an injected `register_jobs` raise drives the PHASE-2 reconcile-failure path.
- `yahir_reusable_bot/config/reload.py` - `reload()`'s PHASE-2 `except` block: bound the reconcile exception and added the `on_rejected` hook fire before `raise`; updated the method docstring with the D-31/D-32 contract.

## Decisions Made
- D-31 (from CONTEXT.md, applied verbatim): fire `_best_effort_hook(self._on_rejected, exc, label="reconcile-rolled-back")` immediately before the `raise` at reload.py's PHASE-2 block, matching PHASE-1's exact statement order (log → restore → fire hook → raise).
- D-32 (from CONTEXT.md, applied verbatim): no second hook, no phase/reason enum — the same `on_rejected` callback is reused; the two rejection paths are distinguished only by their internal log label (`reload-rejected` vs. `reconcile-rolled-back`), not by new public API surface.

## Deviations from Plan

None - plan executed exactly as written. Both tasks matched the plan's `<action>` and `<acceptance_criteria>` precisely; no Rule 1-4 auto-fixes were needed.

## Issues Encountered

None. A pre-existing, unrelated lint finding was noticed while running `ruff check` on the modified file (`pathlib.Path` imported but unused at `reload.py:46`) — confirmed via `git show HEAD~1` to predate this plan's changes entirely. Per the deviation rules' scope boundary ("only auto-fix issues DIRECTLY caused by the current task's changes"), this was left untouched and is not part of this plan's scope.

## User Setup Required

None - no external service configuration required.

## Human-Gated Close-Out Note (ECOSYSTEM.md §3)

**Flag for the human-gated close-out:** CFG-01 makes `on_rejected` fire on the PHASE-2 reconcile-failure path where it previously never fired — a silent→loud behavior change any consumer (WeatherBot) will observe once it repins to a hub tag containing this fix. A consumer whose injected `on_rejected` callback assumes it only ever fires on PHASE-1 validation errors should re-verify that assumption at repin time. No tag, repin, or deploy was performed here — this is autonomous fix + test work only, per ECOSYSTEM.md §3.

## Next Phase Readiness

- CFG-01 fully closed: RED-first two-commit proof, full suite (28 tests) + GATE-01 (`test_import_hygiene.py`) green.
- Plans 02 and 03 (DISC-01/02/03 in `gateway.py`, DISC-04 in `selection.py`) are unblocked — Wave 1 (this plan) is the only Wave-1 dependency for Wave 2, per the plan's sequencing note (RED tests never overlap a sibling's full-suite gate).
- No blockers.

---
*Phase: 02-latent-runtime-robustness*
*Completed: 2026-07-27*

## Self-Check: PASSED

- FOUND: tests/test_reload.py
- FOUND: yahir_reusable_bot/config/reload.py
- FOUND: commit 4853c78 (test-only RED commit)
- FOUND: commit 3bcd174 (fix GREEN commit)
