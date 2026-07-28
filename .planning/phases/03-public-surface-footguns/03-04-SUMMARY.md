---
phase: 03-public-surface-footguns
plan: 04
subsystem: reliability
tags: [tenacity, retry, python]

# Dependency graph
requires:
  - phase: 03-public-surface-footguns (03-03)
    provides: CommandRegistry casefold-symmetry fix (MATCH-01/MATCH-02), GATE-01 baseline at 58 passed
provides:
  - "_within_burst_wait guards burst_size <= 1, degrading to burst_spread_s instead of raising ZeroDivisionError (RELY-02, D-36)"
  - "two_burst_wait carries a loud D-37 standalone-desync precondition in its docstring, pinned by an executable mid-pause test (RELY-03)"
affects: [reliability, retry-schedule-consumers]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "guard-and-degrade over raise for a structurally-unreachable-in-production division edge (D-36)"
    - "docstring-precondition-as-honest-ceiling when a callable structurally cannot self-check a caller's coupling (D-37) -- no factory, no assert"

key-files:
  created: []
  modified:
    - yahir_reusable_bot/reliability/retry.py
    - tests/test_retry.py

key-decisions:
  - "RELY-02 fixed: _within_burst_wait gains an if burst_size <= 1: return burst_spread_s guard placed AFTER the attempt_number == burst_size mid-pause branch and BEFORE the division; burst_size > 1 spread+jitter math left byte-identical (D-36)"
  - "RELY-03 fixed: two_burst_wait's docstring gains a loud PRECONDITION paragraph -- a standalone caller MUST pair it with stop=stop_after_attempt(2 * burst_size); function BODY unchanged, no factory, no assert (D-37)"
  - "RED-first two-commit proof recorded for RELY-02: test-only commit 4579dc5 is the direct parent of fix commit 5567a38 (D-13)"
  - "RED-first two-commit proof recorded for RELY-03: test-only commit 5c8b9cb is the direct parent of fix commit 3079e9c (D-13)"

requirements-completed: [RELY-02, RELY-03]

coverage:
  - id: D1
    description: "burst_size <= 1 degrades to burst_spread_s instead of raising ZeroDivisionError inside the tenacity wait; build_retrying(attempts_per_burst=1) driven to exhaustion never raises ZeroDivisionError"
    requirement: RELY-02
    verification:
      - kind: unit
        ref: "tests/test_retry.py#test_rely_02_burst_size_one_does_not_raise_zerodivisionerror"
        status: pass
      - kind: unit
        ref: "tests/test_retry.py#test_rely_02_within_burst_wait_burst_size_one_returns_float_no_raise"
        status: pass
      - kind: unit
        ref: "tests/test_retry.py#test_rely_02_burst_size_one_degrades_to_spread_base"
        status: pass
      - kind: unit
        ref: "tests/test_retry.py#test_rely_02_burst_size_greater_than_one_unchanged"
        status: pass
    human_judgment: false
  - id: D2
    description: "two_burst_wait's docstring carries the D-37 standalone-desync precondition (stop_after_attempt(2 * burst_size)) and the mid-pause fires exactly at attempt_number == burst_size, pinned by an executable test; no coupling machinery added"
    requirement: RELY-03
    verification:
      - kind: unit
        ref: "tests/test_retry.py#test_rely_03_mid_pause_pinned_and_precondition_documented"
        status: pass
    human_judgment: false

# Metrics
duration: 8min
completed: 2026-07-27
status: complete
---

# Phase 3 Plan 4: RELY-02 + RELY-03 retry burst_size coupling fix Summary

**`_within_burst_wait` guards the `burst_size <= 1` division (degrade to `burst_spread_s`, never raise) and `two_burst_wait` gains a loud docstring precondition instead of coupling machinery for its structural inability to self-check a standalone caller's stop bound.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-07-28T01:20:00Z (approx)
- **Completed:** 2026-07-28T01:25:44Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- RELY-02 (D-36): `_within_burst_wait` no longer raises `ZeroDivisionError` when `burst_size <= 1` -- it returns `burst_spread_s` (the spread base, no jitter) instead, confirmed via a `build_retrying(attempts_per_burst=1)` exhaustion drive (tenacity's wait-before-stop order, RESEARCH Pitfall 3, meant the crash reproduced on the terminal attempt even though `stop_after_attempt(2)` was about to end the schedule).
- RELY-03 (D-37): `two_burst_wait`'s docstring now states loudly that a standalone caller wiring it into their OWN `Retrying` MUST pair it with `stop=stop_after_attempt(2 * burst_size)`, since the function structurally only ever sees `retry_state.attempt_number` and cannot see the stop bound. No coupling machinery (no matched-pair factory, no assert) was added -- the mid-pause-at-`attempt_number == burst_size` behavior is pinned by an executable test instead.
- Both fixes landed together in this one plan per the ROADMAP's RELY-02/RELY-03 pairing.

## Task Commits

Each task was committed as a RED-parent/GREEN-child pair (D-13):

1. **Task 1: RELY-02 guard** -
   - `4579dc5` (test) - add failing test for RELY-02 burst_size<=1 ZeroDivisionError
   - `5567a38` (feat) - guard burst_size<=1 in _within_burst_wait, degrade not raise
2. **Task 2: RELY-03 precondition** -
   - `5c8b9cb` (test) - add failing test for RELY-03 two_burst_wait precondition docstring
   - `3079e9c` (feat) - document D-37 standalone-desync precondition on two_burst_wait

**Plan metadata:** (this commit) - docs: complete 03-04 plan

## Files Created/Modified
- `yahir_reusable_bot/reliability/retry.py` - `_within_burst_wait` gains the `burst_size <= 1` guard (D-36); `two_burst_wait`'s docstring gains the D-37 precondition paragraph (body unchanged)
- `tests/test_retry.py` - extended (RELY-01 tests from Phase 1 remain untouched) with 4 RELY-02 tests and 1 RELY-03 test

## Decisions Made
- RELY-02's guard sits precisely between the existing mid-pause early-return and the division, so the `burst_size > 1` spread+jitter math stays byte-identical -- verified by a dedicated regression test (`test_rely_02_burst_size_greater_than_one_unchanged`).
- RELY-02's RED test drives `build_retrying(attempts_per_burst=1, ...)` to full exhaustion (black-box, per D-43) rather than only unit-testing `_within_burst_wait` directly, so it exercises tenacity's real wait-before-stop call order (RESEARCH Pitfall 3) -- a test that only asserted `_within_burst_wait`'s return value would have missed the exact code path where the crash actually happens inside `Retrying.__call__`.
- RELY-03's fix is docstring-only by design (D-37 linchpin): `two_burst_wait` cannot receive the stop bound, so a hard assert is physically impossible and a matched-pair factory is over-built for an unreachable footgun (no consumer calls `two_burst_wait` standalone; `build_retrying` is the only wired path and already couples correctly). The mid-pause-pin test asserts identically before and after the fix (regression guard); only the docstring-presence assertion is genuinely RED pre-fix -- this asymmetry is documented in the test's self-proof docstring per D-11 house style.

## Deviations from Plan

None - plan executed exactly as written. No architectural changes, no missing dependencies, no auth gates.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- GATE-01 green: full suite `uv run pytest -q` at 63 passed (up from the 58-passed baseline after wave 3, +5 new tests); `uv run pytest tests/test_import_hygiene.py -q` at 8 passed.
- RELY-02 + RELY-03 both land in this plan (the ROADMAP pairing satisfied).
- No version bump, tag, repin, uv sync, or deploy performed -- all human-gated per ECOSYSTEM.md §3, deferred until after Phase 4 (per the standing decision recorded in earlier phase summaries).
- Ready for Wave 5 (the final plan of Phase 3).

---
*Phase: 03-public-surface-footguns*
*Completed: 2026-07-27*

## Self-Check: PASSED

- FOUND: .planning/phases/03-public-surface-footguns/03-04-SUMMARY.md
- FOUND: 4579dc5 (test RELY-02)
- FOUND: 5567a38 (feat RELY-02)
- FOUND: 5c8b9cb (test RELY-03)
- FOUND: 3079e9c (feat RELY-03)
