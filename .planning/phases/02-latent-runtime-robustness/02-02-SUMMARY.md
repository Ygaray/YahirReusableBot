---
phase: 02-latent-runtime-robustness
plan: 02
subsystem: infra
tags: [discord.py, gateway, panel-pin, error-handling, hub-library]

# Dependency graph
requires:
  - phase: 02-latent-runtime-robustness
    provides: "02-01 (D-13 two-commit RED-first idiom, D-11 no-mocking-library house style, Wave 1 baseline)"
requires_prior:
  - "01-reachable-reliability — D-11 no-mocking-library house style, D-13 two-commit RED-first idiom, D-17 hub-assertable-observable discipline"
provides:
  - "BotThread.death_reason() — additive death-reason accessor alongside is_alive() (DISC-01)"
  - "summon_panel per-item delete resilience + pin-cap headroom-reserve (DISC-02)"
  - "BotThread.stop() degrade-not-raise on the loop-closed TOCTOU (DISC-03)"
affects: [02-03, human-gated close-out (repin note)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level REASON_* string-constant taxonomy (retry.py:75-77 idiom) applied to a second module (gateway.py)"
    - "Per-item try/except around a delete loop, narrowing an outer sole-exception backstop to its true TOCTOU scope"
    - "Cross-thread schedule-inside-try degrade-not-raise for asyncio.run_coroutine_threadsafe"

key-files:
  created: []
  modified:
    - yahir_reusable_bot/discord/gateway.py
    - tests/test_gateway.py

key-decisions:
  - "D-21/D-22/D-23: gateway liveness/reconnect contract settled as liveness-only — NO hub-side reconnect wrapper; death_reason() is purely additive, is_alive() unchanged"
  - "D-24/D-25/D-26/D-27: summon_panel keeps create-before-delete; per-item delete catch closes the 2+-live-panels bug; pin-cap headroom-reserve (evict one owned stray, retry pin) closes the fresh-but-unpinned bug; foreign-pin-saturation is a documented residual (loud CRITICAL, not chased)"
  - "D-28: stop() moves run_coroutine_threadsafe inside its existing try — a RuntimeError from a loop that closed mid-call is logged and swallowed, never raised; the thread join is unconditionally reached"

patterns-established:
  - "REASON_* death-reason taxonomy is now a repo-wide idiom (retry.py + gateway.py), not a one-off"
  - "Pin-cap detection stays cap-number-agnostic — react to discord.HTTPException generically, never hardcode a count (A1/A2 unresolved in RESEARCH.md)"

requirements-completed: [DISC-01, DISC-02, DISC-03, GATE-01]

coverage:
  - id: D1
    description: "A LoginFailure death leaves is_alive() False AND death_reason() == 'login_failure'; a generic crash leaves death_reason() == 'crashed'. is_alive() semantics unchanged; no hub-side reconnect wrapper added."
    requirement: "DISC-01"
    verification:
      - kind: unit
        ref: "tests/test_gateway.py#test_bot_thread_records_login_failure_death_reason"
        status: pass
      - kind: unit
        ref: "tests/test_gateway.py#test_bot_thread_records_crashed_death_reason_on_generic_exception"
        status: pass
    human_judgment: false
  - id: D2
    description: "A NotFound on the first owned stray's delete() does not abort the remaining deletes; net state is exactly one live pinned panel."
    requirement: "DISC-02"
    verification:
      - kind: unit
        ref: "tests/test_gateway.py#test_summon_panel_continues_deleting_after_notfound_mid_delete"
        status: pass
    human_judgment: false
  - id: D3
    description: "At the pin cap with >=2 owned panels, one owned stray is evicted before the fresh panel's pin succeeds (headroom-reserve); >=1 owned panel is live at every step."
    requirement: "DISC-02"
    verification:
      - kind: unit
        ref: "tests/test_gateway.py#test_summon_panel_reserves_pin_headroom_at_cap_so_fresh_panel_ends_up_pinned"
        status: pass
    human_judgment: false
  - id: D4
    description: "stop() never raises RuntimeError when the loop closes between the is_running() fast-path check and the run_coroutine_threadsafe schedule, and the thread join still runs."
    requirement: "DISC-03"
    verification:
      - kind: unit
        ref: "tests/test_gateway.py#test_stop_does_not_raise_and_still_joins_when_loop_closes_mid_call"
        status: pass
    human_judgment: false
  - id: D5
    description: "Full suite (33 tests) + import-hygiene/litmus/grimp gates (GATE-01) stay green after all three fixes."
    requirement: "GATE-01"
    verification:
      - kind: unit
        ref: "uv run pytest -q (33 passed)"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-07-27
status: complete
---

# Phase 2 Plan 2: DISC-01/02/03 gateway.py fixes Summary

**A dead bot now leaves a programmatic death-reason signal, a re-summoned panel can never leave 2+ live panels or a fresh-but-unpinned one at the pin cap, and `stop()` can no longer raise on a loop-closed TOCTOU — all three closed via RED-first two-commit proof per finding.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-27T22:31Z (approx.)
- **Completed:** 2026-07-27T22:38Z
- **Tasks:** 3 (each its own RED test commit → GREEN fix commit)
- **Files modified:** 2 (`yahir_reusable_bot/discord/gateway.py`, `tests/test_gateway.py`)

## Accomplishments

- **DISC-01 (H04):** `BotThread` gains a `death_reason()` read accessor alongside the unchanged `is_alive()` — two module-level `REASON_*` string constants (`login_failure`, `crashed`) mirror `retry.py:75-77`'s existing taxonomy idiom. The ROADMAP's open retry/backoff design decision is settled as liveness-only (D-21): no hub-side reconnect wrapper is added, since discord.py's own `reconnect=True` already retries every recoverable disconnect, and the failures that reach `_run`'s except handlers are exactly the ones discord.py deliberately refuses to retry. Both branches (login-failure and generic-crash) are sampled independently per the RESEARCH under-sampling risk.
- **DISC-02 (H05):** `summon_panel`'s delete loop now guards each `old.delete()` with its own `try/except (discord.NotFound, discord.HTTPException, discord.Forbidden)` (D-25) — a failed delete logs a warning and continues rather than aborting the rest. A new pin-cap headroom-reserve branch (D-26) catches `discord.HTTPException` from the fresh panel's `pin()`, evicts ONE owned stray (when >=2 exist), and retries the pin — cap-number-agnostic throughout (no hardcoded 50/250, per RESEARCH's A1/A2 assumption). Create-before-delete ordering (D-24) is preserved byte-identically. The outer sole-`Forbidden` catch is narrowed to the send/pin TOCTOU backstop; a `Forbidden` from `pin()` is explicitly re-raised to it rather than being swallowed by the new cap-retry branch. A foreign-pin-saturated channel (no owned stray to evict) sends the fresh panel and emits a loud CRITICAL instead of silently leaving it unpinned — documented as a residual limitation (D-27), not chased further.
- **DISC-03 (H07):** `BotThread.stop()` moves `asyncio.run_coroutine_threadsafe(...)` inside its existing `try` (previously outside it), so a `RuntimeError("Event loop is closed")` raised when the loop closes between the `is_running()` fast-path check and the schedule call is caught by the same `except Exception` that already guarded `future.result()`. `stop()` never raises, and `self._thread.join(timeout=timeout)` is unconditionally reached — no early return was added in the except (D-28).
- Full suite green: `uv run pytest -q` — 33 passed (up from 28 after Plan 01), including `test_import_hygiene.py` (GATE-01).

## Task Commits

Each task was committed atomically as its own RED→GREEN two-commit pair:

1. **Task 1: DISC-01 RED** — `510ef05` (test) → **DISC-01 GREEN** — `7173027` (fix)
2. **Task 2: DISC-02 RED** — `ca5114e` (test) → **DISC-02 GREEN** — `f06f20e` (fix)
3. **Task 3: DISC-03 RED** — `5b8427d` (test) → **DISC-03 GREEN** — `8f715b2` (fix)

**RED-first two-commit ancestry (D-13) confirmed for each finding:**
- `7173027`'s direct parent is `510ef05` (test-only, touches only `tests/test_gateway.py`).
- `f06f20e`'s direct parent is `ca5114e` (test-only, touches only `tests/test_gateway.py`).
- `8f715b2`'s direct parent is `5b8427d` (test-only, touches only `tests/test_gateway.py`).

## Files Created/Modified

- `tests/test_gateway.py` — grew from 1 to 6 test functions: two `death` tests (DISC-01, both branches), two `summon` tests (DISC-02, independent fixtures for the per-item-delete half and the pin-cap-headroom half), one `stop` test (DISC-03, real closed loop + proxy per RESEARCH Pitfall 3, zero timing/flakiness).
- `yahir_reusable_bot/discord/gateway.py` — `REASON_LOGIN_FAILURE`/`REASON_CRASHED` module constants; `BotThread.__init__` initializes `self._death_reason`; `_run`'s two except branches set it; new `death_reason()` accessor; `summon_panel`'s pin now has an inner try/except (Forbidden re-raised, HTTPException triggers headroom-reserve); the delete loop is per-item try/except; `BotThread.stop()`'s `run_coroutine_threadsafe` moved inside its existing try. Docstrings for `BotThread`, `summon_panel`, `death_reason()`, and `stop()` state the D-21/D-23/D-25/D-26/D-27/D-28 contracts inline (house style).

## Decisions Made

- D-21/D-22/D-23 (from CONTEXT.md, applied verbatim): liveness-only contract — no hub-side reconnect wrapper; `death_reason()` purely additive; `is_alive()` is the documented host park-loop signal.
- D-24/D-25/D-26/D-27 (from CONTEXT.md, applied verbatim): create-before-delete preserved; per-item delete catch; pin-cap headroom-reserve (implemented as catch-and-retry on the pin call itself, since "at the cap" is only knowable by attempting the pin — the fixture-level signal RESEARCH/CONTEXT explicitly permit); foreign-pin-saturation documented as a residual, not fixed.
- D-28 (from CONTEXT.md, applied verbatim): schedule-inside-try degrade-not-raise; `loop.is_running()` retained as a fast path only, no longer a guarantee.
- Implementation detail (Claude's Discretion per CONTEXT.md): the pin-cap headroom-reserve is realized as "attempt pin → catch HTTPException → evict one owned stray if >=2 exist → retry pin" rather than a proactive pre-send eviction, since the cap cannot be detected before attempting the pin without hardcoding a specific count (prohibited by D-26/A1/A2). This satisfies the plan's literal test description ("the fixture only lets pin() succeed after one owned stray was deleted first") and preserves create-before-delete (the fresh panel is still sent before any delete occurs).

## Deviations from Plan

None - plan executed exactly as written. All three tasks matched their `<action>`/`<acceptance_criteria>`/`<verify>` blocks; no Rule 1-4 auto-fixes were needed beyond the discretionary implementation-shape choice noted above (already anticipated by CONTEXT.md's "Claude's Discretion" section, not a deviation).

## Issues Encountered

A `RuntimeWarning: coroutine ... was never awaited` appears in the DISC-03 test's output (both pre- and post-fix). This is an inherent property of the exact failure mode under test: when `run_coroutine_threadsafe` raises before scheduling (because the loop is closed), the `self._client.close()` coroutine object it was passed is never consumed — no code path can avoid this without changing when the coroutine object is constructed, which is out of scope for D-28's fix (guard the schedule call, not the coroutine's lifecycle). Not a regression; harmless in this synthetic-double context (no real coroutine work is pending).

## User Setup Required

None - no external service configuration required.

## Human-Gated Close-Out Note (ECOSYSTEM.md §3)

**Flag for the human-gated close-out:** `BotThread.death_reason()` is NEW public surface a consumer's park-loop can read (additive alongside `is_alive()`) — WeatherBot's host loop may want to branch on it (e.g., log a sharper operator message for `login_failure` vs. `crashed`) once it repins to a hub tag containing this fix. The DISC-01 design decision (liveness-only, no hub reconnect wrapper) is now settled and load-bearing — any future consumer request for auto-respawn should be evaluated against this decision, not silently re-opened. No tag, repin, or deploy was performed here — this is autonomous fix + test work only, per ECOSYSTEM.md §3.

## Next Phase Readiness

- DISC-01/02/03 fully closed: RED-first two-commit proof for each finding, full suite (33 tests) + GATE-01 (`test_import_hygiene.py`) green.
- Plan 03 (DISC-04 in `selection.py`) is unblocked — it touches a disjoint file and has no dependency on this plan's changes.
- No blockers.

---
*Phase: 02-latent-runtime-robustness*
*Completed: 2026-07-27*

## Self-Check: PASSED

- FOUND: yahir_reusable_bot/discord/gateway.py
- FOUND: tests/test_gateway.py
- FOUND: commit 510ef05 (DISC-01 test-only RED commit)
- FOUND: commit 7173027 (DISC-01 fix GREEN commit)
- FOUND: commit ca5114e (DISC-02 test-only RED commit)
- FOUND: commit f06f20e (DISC-02 fix GREEN commit)
- FOUND: commit 5b8427d (DISC-03 test-only RED commit)
- FOUND: commit 8f715b2 (DISC-03 fix GREEN commit)
