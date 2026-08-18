---
phase: 07-v0-1-2-debt-paydown
plan: 02
subsystem: discord
tags: [python, discord.py, structlog, exception-handling]

# Dependency graph
requires:
  - phase: 07-v0-1-2-debt-paydown/07-01
    provides: RED-first / GREEN-both-ways pinned-limitation test idioms carried into this plan's doubles
provides:
  - Retry-pin discord.Forbidden discrimination in summon_panel, ordered before discord.HTTPException so it is reachable (DISC-07)
  - Eviction-delete bookkeeping tied to delete success — a failed eviction stays in matches for the cleanup loop to retry (DISC-08)
affects: [discord/gateway]

# Tech tracking
tech-stack:
  added: []
  patterns: ["structlog.testing.capture_logs() for asserting on emitted event strings — first use in this repo", "peek-then-conditionally-remove (matches[0] + try/except/else pop) instead of unconditional pop-then-attempt for a cleanup-list bookkeeping fix"]

key-files:
  created: []
  modified:
    - tests/test_gateway.py
    - yahir_reusable_bot/discord/gateway.py

key-decisions:
  - "The new except discord.Forbidden clause on the retry pin is inserted immediately BEFORE the existing except discord.HTTPException, mirroring the ordering already used at the first msg.pin() (gateway.py:196-200) — Forbidden is a subclass of HTTPException and Python's except is first-match, so reversed order would make the new branch unreachable dead code."
  - "The retry-pin Forbidden branch logs and SWALLOWS — it does NOT re-raise. Re-raising would return from summon_panel before the for old in matches: cleanup loop runs, leaving every stray undeleted. DISC-07's requirement is scoped to the log classification only, not a control-flow change."
  - "DISC-08's fix replaces stray = matches.pop(0) with a peek (stray = matches[0]); removal moves into an else: on the delete try/except so the stray leaves matches only when delete() returns without raising. A failed delete leaves the stray in matches for the for old in matches: loop below to retry on the same call."
  - "num_matches (captured before the cap branch) and the first msg.pin()'s existing Forbidden/HTTPException chain, the D-27 residual branch, the cleanup loop, and the outer TOCTOU backstop were all left untouched, per plan scope."

patterns-established:
  - "structlog.testing.capture_logs() around asyncio.run(...) to assert on cap[*]['event'] strings — reusable for any future gateway.py logging-classification test."
  - "GREEN-both-ways guard tests (labeled in their own docstrings) sit alongside genuinely-RED regression tests in the same file, as established in 07-01."

requirements-completed: [DISC-07, DISC-08]

coverage:
  - id: D1
    description: "A discord.Forbidden raised by the retry pin inside summon_panel is logged with its own distinct event string ('panel pin forbidden on retry (permission revoked mid-summon); fresh panel left unpinned'), never the generic pin-cap message, and is logged-and-swallowed (not re-raised) so the cleanup loop still runs"
    requirement: "DISC-07"
    verification:
      - kind: unit
        ref: "tests/test_gateway.py#test_retry_pin_forbidden_logs_a_distinct_event_not_the_cap_message"
        status: pass
      - kind: unit
        ref: "tests/test_gateway.py#test_retry_pin_http_exception_still_logs_the_cap_message"
        status: pass
      - kind: unit
        ref: "tests/test_gateway.py#test_pin_cap_with_zero_owned_strays_still_logs_the_d27_residual"
        status: pass
    human_judgment: false
  - id: D2
    description: "A failed eviction-delete leaves the stray in matches so the same call's cleanup loop retries it (delete attempted exactly twice); a successful eviction-delete removes the stray so the cleanup loop does not re-delete it (delete attempted exactly once)"
    requirement: "DISC-08"
    verification:
      - kind: unit
        ref: "tests/test_gateway.py#test_eviction_delete_failure_keeps_stray_in_cleanup_and_retries_it"
        status: pass
      - kind: unit
        ref: "tests/test_gateway.py#test_eviction_delete_success_removes_stray_so_cleanup_does_not_redelete"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-08-04
status: complete
---

# Phase 07 Plan 02: DISC-07 / DISC-08 retry-pin Forbidden discrimination + eviction bookkeeping Summary

**`summon_panel`'s retry pin now distinguishes a revoked-permission `discord.Forbidden` from a generic pin-cap `discord.HTTPException` with its own critical log message (logged and swallowed, not re-raised), and a failed eviction-delete stays in the cleanup list to be retried instead of being silently dropped.**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments
- Extended `tests/test_gateway.py` with two new test doubles (`_FakeRetryPinMessage`, `_FakeStubbornStray`) and five tests: 2 genuinely RED against pre-fix source (the new Forbidden-distinct log message, and the failed-eviction retry count), 3 GREEN-both-ways guards (the generic-HTTPException cap message still fires, a successful eviction is not re-deleted, and the zero-owned-stray D-27 residual is untouched).
- Inserted `except discord.Forbidden:` on the retry pin in `summon_panel`, ordered BEFORE the existing `except discord.HTTPException:` (Forbidden is a subclass; ordering is load-bearing per Python's first-match `except` semantics) — logs the new distinct event string and swallows rather than re-raising, preserving the cleanup loop's execution.
- Replaced the unconditional `matches.pop(0)` with a peek (`matches[0]`) plus a conditional pop moved into the delete `try/except`'s `else:` clause, so eviction removal is tied to delete success.
- Full suite (168 passed, 1 pre-existing unrelated warning — HYG-03, tracked separately and out of scope for this plan), import-hygiene gate (10 passed), and `ruff check` all green.

## Task Commits

Each task was committed atomically:

1. **Task 1: Commit the DISC-07 / DISC-08 tests RED** - `c42e90f` (test)
2. **Task 2: Fix summon_panel — Forbidden discrimination + success-tied eviction (GREEN)** - `802ac85` (fix)

**Plan metadata:** (this commit, following the SUMMARY write)

GATE-02 RED-first ancestry: `802ac85` is the direct git child of `c42e90f` (verified via `git log --oneline -3`). Pre-fix, `test_retry_pin_forbidden_logs_a_distinct_event_not_the_cap_message` failed with the new event string absent from `cap` (only the generic cap message was present), and `test_eviction_delete_failure_keeps_stray_in_cleanup_and_retries_it` failed with `delete_attempts == 1` instead of the expected `2` — both genuinely RED against pre-fix `gateway.py`, confirmed by running the target `-k` filter before Task 2 landed.

## Files Created/Modified
- `tests/test_gateway.py` - Added `capture_logs` import, two test doubles (`_FakeRetryPinMessage`, `_FakeStubbornStray`), and five new test functions for DISC-07/DISC-08
- `yahir_reusable_bot/discord/gateway.py` - `summon_panel`'s retry-pin except chain gained a `Forbidden` branch before `HTTPException`; the eviction stray's removal from `matches` moved from an unconditional pop to a success-tied `else:` pop

## Decisions Made
- Followed CONTEXT.md's DISC-07/DISC-08 discretion exactly: Forbidden clause ordered before HTTPException on the retry pin (mirroring the first `msg.pin()`'s idiom at `gateway.py:196-200`), logged-and-swallowed rather than re-raised (preserving control flow so the cleanup loop still runs), and eviction bookkeeping tied to delete success via peek-then-conditional-pop.
- Used `structlog.testing.capture_logs()` for the first time in this repo's test suite (already available via the pinned `structlog>=26.1.0`, per 07-RESEARCH.md's verified output shape) to assert on emitted event strings directly, rather than mocking the logger.
- No `unittest.mock` import added, per acceptance criteria — all test doubles are plain classes matching the existing `_FakeOwnedMessage`/`_FakeChannel`/`_FakeAtCapMessage` construction style.

**Exact new event string shipped:**
```
panel pin forbidden on retry (permission revoked mid-summon); fresh panel left unpinned
```

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

DISC-07 and DISC-08 closed together on the single `summon_panel` collision zone, as the ROADMAP's pairing constraint required. Full suite (168 passed) and import-hygiene gate green. The pre-existing HYG-03 `RuntimeWarning` in `test_stop_does_not_raise_and_still_joins_when_loop_closes_mid_call` remains — it is out of scope for this plan and is owned by 07-03 in the next wave, per the phase's project constraints. Ready for 07-03.

---
*Phase: 07-v0-1-2-debt-paydown*
*Completed: 2026-08-04*

## Self-Check: PASSED

- FOUND: tests/test_gateway.py
- FOUND: yahir_reusable_bot/discord/gateway.py
- FOUND: .planning/phases/07-v0-1-2-debt-paydown/07-02-SUMMARY.md
- FOUND: c42e90f (test commit)
- FOUND: 802ac85 (fix commit)
