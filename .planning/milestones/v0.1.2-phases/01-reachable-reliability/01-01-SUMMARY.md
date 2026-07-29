---
phase: 01-reachable-reliability
plan: 01
subsystem: testing
tags: [pytest, conftest, fixtures, httpx, tenacity, proc-cmdline]

# Dependency graph
requires: []
provides:
  - "phase-01-reachable-reliability branch, cut clean from main (D-14)"
  - "Executed pre-fix baseline proving both RELY-01 and LIFE-01 defects are live at the branch point"
  - "tests/conftest.py with the two Phase 1 shared fixtures: fake_stop_event, cmdline_bytes"
affects: [01-02-PLAN.md, 01-03-PLAN.md, 01-04-PLAN.md]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "First conftest.py + first @pytest.fixture usage in repo history (D-09), intentionally minimal (D-10)"
    - "RED-first baseline proof: assert the defect's buggy behavior BEFORE any test/fix exists, so later RED is attributable to the new test"

key-files:
  created: [tests/conftest.py]
  modified: []

key-decisions:
  - "Cut phase-01-reachable-reliability from main with zero divergence, per D-14 — main only ever receives green commits"
  - "Recreated .venv (uv sync after rm -rf .venv) because the checked-in venv's python shebang pointed at a stale path (/home/yahir/Projects/YahirReusableBot instead of .../Reusable/YahirReusableBot) — a pre-existing broken-environment condition blocking all verification, fixed per Rule 3 (blocking issue, not a new package install)"
  - "conftest.py imports only pytest + __future__ — no httpx/tenacity/yahir_reusable_bot — so a production import error can never masquerade as a fixture-collection error"

patterns-established:
  - "Test doubles for Phase 1 (and grown minimally for Phases 2-4 only when a real second caller appears) live in tests/conftest.py"

requirements-completed: [RELY-01, LIFE-01, GATE-01]

coverage:
  - id: D1
    description: "Phase branch phase-01-reachable-reliability cut from main with zero divergence"
    requirement: "LIFE-01"
    verification:
      - kind: unit
        ref: "shell: git rev-parse --abbrev-ref HEAD == phase-01-reachable-reliability && git rev-parse phase-01-reachable-reliability == git rev-parse main (at cut time)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Pre-fix baseline proves both RELY-01 (is_transient misses RemoteProtocolError/WriteError) and LIFE-01 (recycled-PID decoy false positive, flag-before-module-switch false negative) are live at the branch point"
    requirement: "RELY-01"
    verification:
      - kind: unit
        ref: "uv run python -c one-liner asserting all 5 pre-fix facts; prints PRE-FIX BASELINE CONFIRMED"
        status: pass
    human_judgment: false
  - id: D3
    description: "tests/conftest.py exists with exactly fake_stop_event and cmdline_bytes fixtures (D-10 minimal bound), full suite + import-hygiene gate stay green"
    requirement: "GATE-01"
    verification:
      - kind: unit
        ref: "uv run pytest tests/ --collect-only -q; uv run pytest; uv run pytest tests/test_import_hygiene.py; uv run ruff check tests/conftest.py"
        status: pass
    human_judgment: false

duration: ~15min
completed: 2026-07-22
status: complete
---

# Phase 1 Plan 1: Substrate Foundation Summary

**Cut the phase-01-reachable-reliability branch, proved both hub defects (RELY-01/LIFE-01) live by execution, and founded tests/conftest.py with the repo's first two pytest fixtures (fake_stop_event, cmdline_bytes).**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-22T21:30Z (approx, per STATE.md session start)
- **Completed:** 2026-07-22T21:47:02Z
- **Tasks:** 2/2
- **Files modified:** 1 (`tests/conftest.py`, created)

## Accomplishments
- Cut `phase-01-reachable-reliability` from `main` HEAD with zero divergence — all Phase 1 commits will land here; `main` only ever sees green commits via the Plan 04 merge (D-14).
- Executed a single verification one-liner proving all five pre-fix facts live at the branch point (verbatim evidence below) — the RED-first reference state Plans 02/03 are measured against.
- Ran the pre-existing suite (`uv run pytest`) green on the fresh branch (9 passed) before any regression test exists, so a later RED is attributable to the new test, not a pre-existing failure.
- Created `tests/conftest.py` — the repo's first `conftest.py` and first `@pytest.fixture` usage — with exactly the two D-10-bounded fixtures (`fake_stop_event`, `cmdline_bytes`) and the private `_InstantStopEvent` helper class. No fixtures for Phases 2-4.

## Pre-Fix Baseline Evidence (D-15: no CI — this is enforced by local `uv run` execution only)

Command run on the fresh `phase-01-reachable-reliability` branch, before any regression test or fix existed:

```bash
uv run python -c "import httpx; from yahir_reusable_bot.reliability.retry import is_transient as T; from yahir_reusable_bot.lifecycle.identity import is_running_process as R; j=lambda *p: b'\x00'.join(p)+b'\x00'; m=b'examplebot'; assert T(httpx.RemoteProtocolError('x')) is False; assert T(httpx.WriteError('x')) is False; assert T(httpx.LocalProtocolError('x')) is False; assert R(1, proc_marker=m, cmdline_reader=lambda _: j(b'python', b'-m', b'pytest', m)) is True; assert R(1, proc_marker=m, cmdline_reader=lambda _: j(b'python', b'-O', b'-B', b'-m', m, b'run')) is False; print('PRE-FIX BASELINE CONFIRMED')"
```

Verbatim output:

```
PRE-FIX BASELINE CONFIRMED
```

This confirms, by execution against the branch-point source (no test file involved):
1. `is_transient(httpx.RemoteProtocolError("x"))` is `False` — the RELY-01 miss.
2. `is_transient(httpx.WriteError("x"))` is `False` — the RELY-01 miss.
3. `is_transient(httpx.LocalProtocolError("x"))` is `False` — correct today, must STAY `False` after the fix.
4. `is_running_process(1, proc_marker=b"examplebot", cmdline_reader=...)` is `True` for argv `python -m pytest examplebot` — the LIFE-01 false POSITIVE (recycled-PID decoy, signalable today).
5. The same call is `False` for argv `python -O -B -m examplebot run` — the LIFE-01 false NEGATIVE (two interpreter flags before the module switch).

**No CI enforces any of this (D-15):** there is no `.github/workflows` directory and no pre-commit hook in this repo. "Green" means the executor ran `uv run pytest` and the one-liner above locally, on this branch, and both exited 0.

Pre-existing suite on the fresh branch, before the conftest or any Phase 1 test existed:

```
$ uv run pytest
============================= test session starts ==============================
collected 9 items
tests/test_gateway.py .                                                  [ 11%]
tests/test_import_hygiene.py ........                                    [100%]
============================== 9 passed in 0.80s ===============================
```

## Task Commits

Task 1 (cut the branch + capture the baseline) produced no file changes — it is a git-branch + verification-only task per the plan, so there is no per-task commit for it.

1. **Task 2: Create tests/conftest.py — the hub's first fixtures** - `e00ccf3` (feat)

**Plan metadata:** (final commit hash recorded below in state-update step)

## Files Created/Modified
- `tests/conftest.py` - New. Defines `_InstantStopEvent` (a `.wait(timeout)` double returning `False` immediately) and two fixtures: `fake_stop_event` (fresh `_InstantStopEvent` per test) and `cmdline_bytes` (a `(*parts: bytes) -> bytes` builder reproducing the `/proc/<pid>/cmdline` NUL-separated wire shape).

## Decisions Made
- Followed D-14 exactly: branch cut from `main` HEAD with `git rev-parse` equality confirmed before any commit landed on it.
- Followed D-10's minimal bound literally — exactly two public fixtures, one private helper class, no speculative fixtures for `reload.py`/`registry/`/`scheduler/`/`panelkit`.
- Kept `tests/conftest.py` free of `httpx`/`tenacity`/`yahir_reusable_bot` imports as instructed, so a production import failure can never masquerade as a fixture-collection error.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Recreated a stale `.venv` pointing at a moved repo path**
- **Found during:** Task 1 (running `uv run pytest` for the first time on the fresh branch)
- **Issue:** `uv run pytest` failed with `Failed to spawn: pytest ... No such file or directory`. Investigation showed `.venv/bin/pytest`'s shebang was `#!/home/yahir/Projects/YahirReusableBot/.venv/bin/python` — a path that no longer exists; the repo currently lives at `/home/yahir/Projects/Reusable/YahirReusableBot`. The checked-in venv was built before the repo was moved/renamed into the `Reusable/` subdirectory and was never regenerated.
- **Fix:** `rm -rf .venv && uv sync` — rebuilt the exact same locked dependency set (`uv.lock` untouched, confirmed via `git status`) at the correct path. No package versions changed; no new packages installed (excluded from Rule 3's package-manager-install carve-out because this reinstalls the identical lockfile, not a new/different dependency).
- **Files modified:** None tracked (`.venv/` is gitignored; `git status --short` before and after the recreation showed the same four pre-existing unrelated modifications: `.planning/STATE.md`, `.planning/config.json`, `ECOSYSTEM.md`, `uv.lock` — none newly touched by the venv rebuild).
- **Verification:** `uv run pytest` (9 passed), the pre-fix baseline one-liner (`PRE-FIX BASELINE CONFIRMED`), and later `uv run pytest tests/test_import_hygiene.py` (8 passed) all ran clean after the fix.
- **Committed in:** N/A — `.venv/` is not a tracked path; no commit contains this change.

---

**Total deviations:** 1 auto-fixed (1 blocking, Rule 3)
**Impact on plan:** Necessary to run any verification at all on this machine; no scope creep — no plan file, production code, or test file was touched by this fix.

## Issues Encountered
None beyond the `.venv` deviation above, which was resolved before Task 1's verification ran.

**Requirements traceability note:** this plan's own frontmatter lists `requirements: [RELY-01,
LIFE-01, GATE-01]`, but Plan 01 does no production-code fix (`is_transient` and
`_argv_matches_marker` are untouched — confirmed by the pre-fix baseline above, which shows both
defects still live at the end of this plan). The actual fixes land in Plan 02 (RELY-01) and
Plan 03 (LIFE-01); GATE-01 is milestone-level and spans all 4 phases. Running
`requirements mark-complete RELY-01 LIFE-01 GATE-01` against this plan's frontmatter would have
checked all three off in `.planning/REQUIREMENTS.md` prematurely, misrepresenting fixed-vs-not-yet-
fixed state. That mark-complete call was made, found incorrect on review, and reverted
(`git checkout -- .planning/REQUIREMENTS.md`) before this plan's final commit. RELY-01 and LIFE-01
should be marked complete by Plans 02 and 03 respectively, once their fixes actually land; GATE-01
should be marked complete only once it has held green across the whole milestone.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `tests/conftest.py` is committed on `phase-01-reachable-reliability` with exactly the two D-10 fixtures Plans 02 (`tests/test_retry.py`) and 03 (`tests/test_identity.py`) both need.
- The pre-fix baseline is recorded verbatim above — Plans 02/03 cite it as the RED-first reference state their new failing tests must diverge from.
- Nothing under `yahir_reusable_bot/` was touched by this plan (verified: `git diff --diff-filter=D` and the full `git status` before commit show only `tests/conftest.py` added).
- No blockers for Plan 02 or Plan 03.

---
*Phase: 01-reachable-reliability*
*Completed: 2026-07-22*

## Self-Check: PASSED

- FOUND: tests/conftest.py
- FOUND: .planning/phases/01-reachable-reliability/01-01-SUMMARY.md
- FOUND: e00ccf3 (git log --oneline --all)
