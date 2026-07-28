---
phase: 03-public-surface-footguns
plan: 01
subsystem: infra
tags: [scheduler, structlog, apscheduler, idempotency, tdd]

# Dependency graph
requires: []
provides:
  - "SchedulerEngine.remove is idempotent — an already-gone job id is a no-op success, not a raise"
  - "Dependency-free except KeyError pattern for a host-scheduler lookup-miss (no apscheduler import), proven first for later plans in this phase to reuse"
affects: [03-02-lifecycle-identity, 03-03-registry, 03-04-retry, 03-05-panelkit]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Idempotent swallow via except KeyError: (no third-party dependency import) for a host-injected collaborator's lookup-miss signal, mirroring Path.unlink(missing_ok=True)"
    - "Module-level structlog logger (import structlog; _log = structlog.get_logger(__name__)) added to a previously-unlogged module, mirroring retry.py/panelkit.py"

key-files:
  created: [tests/test_engine.py]
  modified: [yahir_reusable_bot/scheduler/engine.py]

key-decisions:
  - "D-38 implemented as except KeyError: (NOT import apscheduler / except apscheduler.jobstores.base.JobLookupError) — apscheduler's real JobLookupError IS a KeyError subclass (verified against apscheduler 3.x source, RESEARCH.md Pitfall 2); the hub stays host-scheduler-agnostic with zero new dependencies"
  - "Only KeyError is swallowed — a non-KeyError (e.g. RuntimeError) from remove_job re-raises unchanged, proven by a dedicated narrow-swallow test (D-38 vs LIFE-02's masked close)"

patterns-established:
  - "Idempotent-swallow-via-base-exception-class pattern for host-agnostic facades: when a third-party library's specific exception is a subclass of a Python builtin, catch the builtin instead of importing the library"

requirements-completed: [SCHED-01, GATE-01]

coverage:
  - id: D1
    description: "SchedulerEngine.remove returns None without raising when the host scheduler's remove_job signals an already-gone id via KeyError (idempotent no-op success, D-38)"
    requirement: "SCHED-01"
    verification:
      - kind: unit
        ref: "tests/test_engine.py#test_remove_is_idempotent_when_job_already_gone"
        status: pass
      - kind: unit
        ref: "tests/test_engine.py#test_remove_is_idempotent_on_repeat"
        status: pass
    human_judgment: false
  - id: D2
    description: "remove() still forwards a present-id removal to the host scheduler unchanged (the swallow is additive, not a behavior regression on the happy path)"
    requirement: "SCHED-01"
    verification:
      - kind: unit
        ref: "tests/test_engine.py#test_remove_forwards_present_id_removal"
        status: pass
    human_judgment: false
  - id: D3
    description: "A non-lookup-miss exception (e.g. RuntimeError) from remove_job is NOT masked — it re-raises unchanged, so the idempotent swallow stays narrow"
    requirement: "SCHED-01"
    verification:
      - kind: unit
        ref: "tests/test_engine.py#test_remove_does_not_mask_non_lookup_errors"
        status: pass
    human_judgment: false
  - id: D4
    description: "GATE-01: full suite + import-hygiene/litmus/grimp stay green after the fix (39 passed, up from 35 baseline; 0 failed)"
    requirement: "GATE-01"
    verification:
      - kind: unit
        ref: "uv run pytest -q"
        status: pass
      - kind: unit
        ref: "uv run pytest tests/test_import_hygiene.py -q"
        status: pass
    human_judgment: false
  - id: D5
    description: "SchedulerEngine.remove becoming idempotent is a consumer-visible silent→tolerant behavior change requiring human-gated close-out surfacing (version bump, tag, WeatherBot repin)"
    verification: []
    human_judgment: true
    rationale: "This is a process/release decision (ECOSYSTEM.md §3 human-gated close-out), not a code-verifiable outcome — the human must confirm the behavior-change framing and authorize the eventual 0.1.1→0.1.2 bump / v0.1.2 tag / WeatherBot repin (none of which this phase performs)."

duration: 10min
completed: 2026-07-27
status: complete
---

# Phase 3 Plan 1: Idempotent SchedulerEngine.remove Summary

**`SchedulerEngine.remove` is now idempotent for an already-gone job id via a dependency-free `except KeyError:` swallow (no `apscheduler` import), with a new RED-first `tests/test_engine.py` proving it.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-07-27T19:05:53-06:00 (2026-07-28T01:05:53Z)
- **Completed:** 2026-07-27T19:06:47-06:00 (2026-07-28T01:06:47Z)
- **Tasks:** 1 (RED + GREEN two-commit idiom, D-13)
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments
- `SchedulerEngine.remove(job_id)` now catches the host scheduler's lookup-miss `KeyError` (the shape of APScheduler's real `JobLookupError`, verified as a `KeyError` subclass against apscheduler 3.x source) and swallows it with a debug log, so removing an already-gone id is a no-op success instead of a raised exception — analogous to `Path.unlink(missing_ok=True)`.
- Added the module's first `structlog` logger (`import structlog; _log = structlog.get_logger(__name__)`), mirroring the exact shape used in `retry.py:46,54` / `panelkit.py:48,60` — `scheduler/engine.py` previously imported only `from typing import Any, Callable`.
- Founded `tests/test_engine.py` (no prior test existed for `scheduler/engine.py`) with a dependency-free `_FakeRawScheduler` double and four tests: idempotent-swallow (RED pre-fix), present-id-forwards (self-proof control, GREEN pre/post-fix), idempotency-on-repeat (RED pre-fix), and does-not-mask-non-lookup-errors (narrow-swallow proof).
- Zero new dependencies — did not add `apscheduler` to `pyproject.toml`/`uv.lock`; confirmed by grep that `engine.py` contains no `import apscheduler` and no broad `except Exception` around `remove_job`.
- GATE-01 reverified green after the fix: full suite 39 passed (up from the 35-passed pre-phase baseline), 0 failed; `tests/test_import_hygiene.py` 8 passed.

## Task Commits

Each task was committed atomically, following the RED-first two-commit idiom (D-13):

1. **Task 1 (RED): add failing test for idempotent SchedulerEngine.remove** - `0d1f828` (test)
2. **Task 1 (GREEN): SchedulerEngine.remove idempotent via dependency-free except KeyError** - `5e6fbf8` (feat)

D-13 proof: `0d1f828` (test-only) is the direct parent commit of `5e6fbf8` (the fix) — verified via `git rev-parse HEAD^ HEAD`.

**Plan metadata:** (this commit, following)

## Files Created/Modified
- `tests/test_engine.py` - NEW. `_FakeRawScheduler` double (`raise_on_remove` flag) + 4 tests covering the idempotent swallow, present-id-forward, repeat-idempotency, and narrow-swallow (non-KeyError re-raises) contracts.
- `yahir_reusable_bot/scheduler/engine.py` - Added module-level `import structlog` + `_log = structlog.get_logger(__name__)`; `remove()` wraps `self._scheduler.remove_job(job_id)` in `try/except KeyError:` with a debug log on swallow; docstring extended to state the D-38 idempotent contract and the host-agnostic `KeyError`-not-`apscheduler` rationale.

## Decisions Made
- **D-38 mechanism confirmed as `except KeyError:`, not `import apscheduler`.** CONTEXT.md's D-38 literally says "catch `JobLookupError`" — the plan's `<critical_correction>` (backed by RESEARCH.md's verified Pitfall 2) makes clear `apscheduler` is not and must not become a hub dependency, since `JobLookupError` IS a `KeyError` subclass. Implemented exactly as researched; did not "fix it back" to an apscheduler import.
- **Narrow swallow, not `except Exception`.** Only `KeyError` is caught; a `RuntimeError` (or any other exception) from `remove_job` re-raises unchanged, proven by a dedicated test — this keeps a genuine host-scheduler backend failure loud (D-38 vs. LIFE-02's masked-close anti-pattern, which this phase explicitly avoids repeating).

## Deviations from Plan

None - plan executed exactly as written. The plan's `<critical_correction>` and `<read_first>` guidance (RESEARCH.md Code Examples #2, 03-PATTERNS.md's SCHED-01 section) were followed verbatim for both the fix shape and the test double shape.

## Issues Encountered

None. Pre-existing uncommitted changes to `.planning/config.json`, `ECOSYSTEM.md`, and `uv.lock` were present in the working tree at plan start (from a prior, unrelated session) and were left untouched — not staged or committed as part of this plan's task or final metadata commit, since they are out of this plan's scope.

## User Setup Required

None - no external service configuration required.

## Human-Gated Close-Out Note (surface, not performed)

**Consumer-visible behavior change for human close-out:** `SchedulerEngine.remove` is now idempotent (silent→tolerant) — a consumer (currently WeatherBot) that previously relied on `remove` raising for an already-gone job id (e.g. to detect a reconcile bug) will now see a silent no-op instead. This is named here per ECOSYSTEM.md §3 for the milestone's human-gated close-out, which also covers: the `pyproject.toml` `0.1.1 → 0.1.2` version bump, cutting the `v0.1.2` tag, and the WeatherBot repin. None of these three release steps are performed by this phase — they remain deferred to the milestone close-out after all five Phase 3 plans (and Phase 4) complete.

## Next Phase Readiness
- SCHED-01 fully closed; GATE-01 green at 39 passed / 0 failed.
- The dependency-free `except <BuiltinBase>:` pattern (catch a third-party exception's Python builtin base class instead of importing the library) is now proven in this codebase and available as a reference for any future finding with a similar host-agnostic-facade shape.
- Ready for Plan 02 (`lifecycle/identity.py` — LIFE-02 + LIFE-03), per RESEARCH.md's recommended serial sequencing (Wave 1 of 5, strictly serial — no overlapping RED-to-GREEN windows between plans).

---
*Phase: 03-public-surface-footguns*
*Completed: 2026-07-27*

## Self-Check: PASSED

- FOUND: tests/test_engine.py
- FOUND: yahir_reusable_bot/scheduler/engine.py
- FOUND: .planning/phases/03-public-surface-footguns/03-01-SUMMARY.md
- FOUND commit: 0d1f828 (RED)
- FOUND commit: 5e6fbf8 (GREEN)
