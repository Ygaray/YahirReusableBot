---
phase: 03-public-surface-footguns
plan: 02
subsystem: infra
tags: [lifecycle, pid-file, process-identity, monkeypatch, pytest, os-fd]

# Dependency graph
requires:
  - phase: 03-public-surface-footguns/01
    provides: GATE-01 green baseline (SCHED-01 fixed, 39 passed pre-this-plan)
provides:
  - write_pid_atomic that structurally cannot double-close its temp fd (LIFE-02, D-42)
  - _argv_matches_marker basenamed symmetrically on both sides (LIFE-03, D-39)
  - the repo's first pytest `monkeypatch`-based test double (delegating fake `os`)
affects: [03-03, 03-04, 03-05, phase-4]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pytest built-in `monkeypatch` fixture for a delegating fake `os` module (test-only, first use in this repo)"
    - "fd = -1 sentinel guard for at-most-once close, replacing try/except OSError: pass"
    - "basename-both-sides symmetry fix for a marker/argv0 compare"

key-files:
  created: []
  modified:
    - yahir_reusable_bot/lifecycle/identity.py
    - tests/test_identity.py

key-decisions:
  - "LIFE-02 fixed: write_pid_atomic sets fd = -1 immediately after the happy-path os.close, except-path close guarded with `if fd != -1` (D-42) — a reused fd integer can never be double-closed; re-raise posture and temp unlink unchanged"
  - "LIFE-02 test double delegates to the REAL os.close (counts real invocations) rather than a no-op stub, proving the structural closed-at-most-once invariant; this is the repo's FIRST monkeypatch use — a deliberate house-style extension (pytest core, not a mocking library), flagged the same way Phase 1 flagged conftest.py (D-09) and pytest.raises()"
  - "LIFE-03 fixed: _argv_matches_marker compares prog == Path(proc_marker.decode(...)).name instead of the raw un-basenamed proc_marker (D-39) — fixes the non-Linux /proc-absent degrade AND real Linux matching for a path-shaped marker; no-op for a normal basename marker; the -m module branch is untouched"
  - "RED-first two-commit proof recorded for LIFE-02: test-only commit a815e26 is the direct parent of fix commit 0c14258 (D-13)"
  - "RED-first two-commit proof recorded for LIFE-03: test-only commit bbfccca is the direct parent of fix commit 820353f (D-13)"

patterns-established:
  - "monkeypatch-substituted delegating fake module (types.SimpleNamespace(**vars(real_module))) for proving structural invariants without forcing a non-deterministic OS-level race"

requirements-completed: [LIFE-02, LIFE-03]

coverage:
  - id: D1
    description: "write_pid_atomic never double-closes the temp fd; a failing os.replace re-raises the original error with exactly one os.close call"
    requirement: "LIFE-02"
    verification:
      - kind: unit
        ref: "tests/test_identity.py#test_life_02_write_pid_atomic_closes_temp_fd_exactly_once_on_replace_failure"
        status: pass
      - kind: unit
        ref: "tests/test_identity.py#test_life_02_write_pid_atomic_happy_path_still_writes_one_pid_file"
        status: pass
    human_judgment: false
  - id: D2
    description: "_argv_matches_marker basenames both argv[0] and proc_marker, so a path-shaped proc_marker matches the non-Linux degrade sentinel and real Linux argv0 matching; a normal basename marker still matches (no-op regression)"
    requirement: "LIFE-03"
    verification:
      - kind: unit
        ref: "tests/test_identity.py#test_life_03_non_linux_degrade_holds_for_path_shaped_marker"
        status: pass
      - kind: unit
        ref: "tests/test_identity.py#test_life_03_real_linux_basename_matches_path_shaped_marker"
        status: pass
      - kind: unit
        ref: "tests/test_identity.py#test_life_03_plain_basename_marker_still_matches_no_op_regression"
        status: pass
    human_judgment: false
  - id: D3
    description: "GATE-01: full suite + import-hygiene stay green after both fixes"
    requirement: "GATE-01"
    verification:
      - kind: integration
        ref: "uv run pytest -q (44 passed)"
        status: pass
      - kind: integration
        ref: "uv run pytest tests/test_import_hygiene.py -q (8 passed)"
        status: pass
    human_judgment: false

# Metrics
duration: 10min
completed: 2026-07-28
status: complete
---

# Phase 3 Plan 2: LIFE-02 + LIFE-03 (lifecycle/identity.py) Summary

**write_pid_atomic guarded against fd double-close (D-42) and _argv_matches_marker basenamed symmetrically on both sides (D-39), both RED-first, GATE-01 green at 44 passed**

## Performance

- **Duration:** ~10 min
- **Completed:** 2026-07-28
- **Tasks:** 2
- **Files modified:** 2 (`yahir_reusable_bot/lifecycle/identity.py`, `tests/test_identity.py`)

## Accomplishments
- LIFE-02: `write_pid_atomic` sets `fd = -1` immediately after the happy-path `os.close(fd)`; the except-path close is now guarded with `if fd != -1` instead of `try: os.close(fd) except OSError: pass` — a reused fd integer can never be silently double-closed. Re-raise posture and temp-file unlink preserved byte-identical.
- LIFE-03: `_argv_matches_marker` now basenames BOTH `argv[0]` and `proc_marker` (`prog == Path(proc_marker.decode("utf-8", "replace")).name`), fixing the non-Linux `/proc`-absent degrade AND real Linux matching for a path-shaped `proc_marker`; a no-op for a normal basename marker; the `-m` module branch untouched.
- Introduced this repo's first pytest `monkeypatch` use (LIFE-02's delegating fake `os` module, real `close` delegated-through counter + raising `replace`) — a deliberate house-style extension, not a mocking-library adoption.
- Both findings RED-first: 4 new commits (test → feat, test → feat), each test-only commit the direct parent of its fix commit (D-13).
- GATE-01 confirmed green after each GREEN commit: full suite went 39 → 41 (LIFE-02) → 44 passed (LIFE-03); import-hygiene stayed 8 passed throughout.

## Task Commits

Each task was committed atomically (RED-parent/GREEN-child per D-13):

1. **Task 1: LIFE-02 — write_pid_atomic fd double-close guard**
   - `a815e26` (test) — add failing test for LIFE-02 fd double-close guard
   - `0c14258` (feat) — guard write_pid_atomic against fd double-close (LIFE-02)
2. **Task 2: LIFE-03 — basename both sides in _argv_matches_marker**
   - `bbfccca` (test) — add failing tests for LIFE-03 path-shaped proc_marker
   - `820353f` (feat) — basename both sides in _argv_matches_marker (LIFE-03)

_Note: both tasks were two-commit RED/GREEN pairs (D-13); no REFACTOR commit was needed for either._

## Files Created/Modified
- `yahir_reusable_bot/lifecycle/identity.py` — LIFE-02 fd-guard fix in `write_pid_atomic`; LIFE-03 basename-both-sides fix in `_argv_matches_marker`. No new source symbols; both function signatures unchanged.
- `tests/test_identity.py` — extended with 5 new tests (2 for LIFE-02, 3 for LIFE-03), the LIFE-02 monkeypatch double, and a module-docstring note flagging the first monkeypatch use.

## Decisions Made
- LIFE-02: `fd = -1` guard (D-42), matching the plan's locked fix shape exactly; no architectural change.
- LIFE-02 test double delegates to the real `os.close` (proves the structural invariant) rather than a no-op stub, per RESEARCH.md's explicit rationale — a real fd-reuse race is non-deterministic and unprovable in a single-threaded test.
- LIFE-03: basename both sides (D-39), matching the plan's locked fix shape exactly; confirmed strictly more correct than the original finding report (fixes both the non-Linux degrade and real Linux path-shaped matching).
- Test naming: both LIFE-02 and LIFE-03 test functions are prefixed `test_life_02_*` / `test_life_03_*` so the plan's specified `-k life_02` / `-k life_03` verify commands select exactly the right rows.

## Deviations from Plan

### Auto-fixed Issues

None — both fixes applied exactly per the plan's locked shapes (D-42, D-39) and the RESEARCH.md/PATTERNS.md ready-to-adapt code. No Rule 1/2/3 auto-fixes were needed.

### Out-of-Scope Discovery (logged, not fixed)

**1. Pre-existing `ruff` E731 in `identity.py`**
- **Found during:** Task 1 verification pass (`uv run ruff check`)
- **Issue:** `cmdline_reader = lambda p: _read_proc_cmdline(p, proc_marker=proc_marker)` (inside `is_running_process`, pre-existing line, not touched by either LIFE-02 or LIFE-03) assigns a lambda to a name instead of using `def`.
- **Confirmed pre-existing:** stashed this plan's diff and re-ran `ruff check` against the pre-plan source — the same E731 fires at the same logical line, confirming it predates both fixes.
- **Action:** Out of scope per the SCOPE BOUNDARY rule (a pre-existing issue unrelated to the current task's changes). Logged to `.planning/phases/03-public-surface-footguns/deferred-items.md`, not fixed. Not part of GATE-01 (which is pytest full suite + import-hygiene only; no ruff gate is wired into this phase's verification).

---

**Total deviations:** 0 auto-fixed; 1 out-of-scope item logged (not a deviation from plan execution).
**Impact on plan:** None — plan executed exactly as written for both findings.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. No consumer-visible behavior change requiring a repin note (both LIFE-02 and LIFE-03 are edge-only, happy-path-preserving fixes per the plan's success criteria).

## Next Phase Readiness
- GATE-01 green (44 passed, 8 import-hygiene passed) — ready for Wave 3 (03-03, MATCH-01 + MATCH-02).
- No blockers. The `monkeypatch` house-style extension is now established precedent for any future test needing a delegating fake of a stdlib module.

---
*Phase: 03-public-surface-footguns*
*Completed: 2026-07-28*
