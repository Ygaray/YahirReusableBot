---
phase: 03-public-surface-footguns
plan: 05
subsystem: discord
tags: [discord.py, panelkit, interaction-check, construction-validation, tdd]

# Dependency graph
requires:
  - phase: 03-public-surface-footguns
    provides: "Plans 01-04 (SCHED-01, LIFE-02/03, MATCH-01/02, RELY-02/03) — RED-first two-commit precedent and GATE-01 baseline (63 passed)"
provides:
  - "interaction_check falsy-guarded against absent/MISSING interaction.user (DISC-05, D-40)"
  - "PanelKit.__init__ rejects empty/whitespace marker at construction (DISC-06, D-41)"
  - "tests/test_panelkit.py — first test file for discord/panelkit.py (7 tests)"
affects: [phase-4, milestone-close-out]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Synthetic interaction double (_FakeInteraction/_FakeUser/_FalsySentinel) for testing discord.py View gate logic without real gateway machinery"
    - "Falsy-check guard (not identity/is-None) for discord.py 2.7.1's MISSING sentinel"

key-files:
  created:
    - tests/test_panelkit.py
  modified:
    - yahir_reusable_bot/discord/panelkit.py

key-decisions:
  - "DISC-05 fixed: interaction_check guards `if not interaction.user:` (falsy, NOT is None) at the TOP of the method — catches both None and discord.py 2.7.1's real absence sentinel discord.utils.MISSING (falsy but not None, RESEARCH.md Pitfall 1); emits the existing reject-log shape and returns False, no ephemeral ack"
  - "The RED test calls interaction_check DIRECTLY and asserts it returns False without raising — does NOT assert anything about on_error (RESEARCH.md Pitfall 1 empirically proved on_error IS invoked for an escaping AttributeError in discord.py 2.7.1; the correct RED test sidesteps that question entirely)"
  - "DISC-06 fixed: PanelKit.__init__ raises ValueError immediately after super().__init__(timeout=None), before the collaborator assignments / _build_children / _assert_layout, when not marker or not marker.strip() — closes the cid.startswith(\"\") owns-everything hole at the source"
  - "DISC-06 uses raise ValueError, not assert — genuine consumer-input validation that must survive -O, matching MATCH-02's D-34 reasoning"

patterns-established:
  - "Pattern: falsy-check guards for discord.py sentinel values (MISSING is falsy but not None) — do not use identity checks for library-internal sentinels without verifying their exact shape"

requirements-completed: [DISC-05, DISC-06, GATE-01]

coverage:
  - id: D1
    description: "interaction_check returns False without raising for an absent interaction.user (None), via a falsy guard at the top of the method"
    requirement: "DISC-05"
    verification:
      - kind: unit
        ref: "tests/test_panelkit.py#test_disc_05_interaction_check_returns_false_without_raising_when_user_is_none"
        status: pass
    human_judgment: false
  - id: D2
    description: "interaction_check returns False without raising for a MISSING-shaped falsy (but not None) interaction.user, proving the guard is a falsy check and not an is-None identity check"
    requirement: "DISC-05"
    verification:
      - kind: unit
        ref: "tests/test_panelkit.py#test_disc_05_interaction_check_returns_false_for_missing_shaped_falsy_user"
        status: pass
    human_judgment: false
  - id: D3
    description: "interaction_check still rejects a legitimate non-operator user via the existing non-operator reject path (no regression / false-positive from the new guard)"
    requirement: "DISC-05"
    verification:
      - kind: unit
        ref: "tests/test_panelkit.py#test_disc_05_interaction_check_still_rejects_legitimate_non_operator_user"
        status: pass
    human_judgment: false
  - id: D4
    description: "PanelKit(marker=\"\") raises ValueError at construction"
    requirement: "DISC-06"
    verification:
      - kind: unit
        ref: "tests/test_panelkit.py#test_disc_06_empty_marker_raises_value_error_at_construction"
        status: pass
    human_judgment: false
  - id: D5
    description: "PanelKit(marker=\"   \") (whitespace-only) raises ValueError at construction"
    requirement: "DISC-06"
    verification:
      - kind: unit
        ref: "tests/test_panelkit.py#test_disc_06_whitespace_only_marker_raises_value_error_at_construction"
        status: pass
    human_judgment: false
  - id: D6
    description: "A valid non-empty marker still constructs without regression"
    requirement: "DISC-06"
    verification:
      - kind: unit
        ref: "tests/test_panelkit.py#test_disc_06_valid_marker_still_constructs"
        status: pass
    human_judgment: false
  - id: D7
    description: "The raised ValueError message names the offending (empty) marker value"
    requirement: "DISC-06"
    verification:
      - kind: unit
        ref: "tests/test_panelkit.py#test_disc_06_value_error_names_the_offending_marker"
        status: pass
    human_judgment: false
  - id: D8
    description: "GATE-01: full test suite + import-hygiene gate both green after both fixes"
    requirement: "GATE-01"
    verification:
      - kind: unit
        ref: "uv run pytest -q (70 passed) && uv run pytest tests/test_import_hygiene.py -q (8 passed)"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-07-27
status: complete
---

# Phase 3 Plan 5: DISC-05 + DISC-06 (discord/panelkit.py) Summary

**`interaction_check` now falsy-guards against an absent/MISSING `interaction.user` (returns False, never raises) and `PanelKit.__init__` now rejects an empty/whitespace-only `marker` at construction — both RED-first, both closing existing access-control/validation gaps with zero new dependencies. This is the FINAL plan of Phase 3.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-27T19:29:14-06:00
- **Completed:** 2026-07-27T19:30:14-06:00
- **Tasks:** 2
- **Files modified:** 2 (1 new: `tests/test_panelkit.py`; 1 modified: `yahir_reusable_bot/discord/panelkit.py`)

## Accomplishments

- **DISC-05 (D-40):** `interaction_check` guards `if not interaction.user:` at the TOP of the method (before the unguarded `.bot` dereference) — a falsy check, not `is None`, so it catches both `None` and discord.py 2.7.1's real absence sentinel `discord.utils.MISSING` (a distinct object, falsy but not `None`). Emits the existing reject-log shape (`"panel reject (no user)"`) and returns `False`, no ephemeral ack (there is no user to ack). A legitimate non-operator user still falls through to the unchanged existing non-operator reject.
- **DISC-06 (D-41):** `PanelKit.__init__` raises `ValueError` when `not marker or not marker.strip()`, placed immediately after `super().__init__(timeout=None)` and BEFORE the collaborator assignments / `_build_children()` / `_assert_layout()` — closing the `cid.startswith("")`-owns-everything hole at the source (previously an empty marker made `is_owned_panel` claim every bot-authored pin, so `summon_panel` could delete unrelated pins).
- Founded `tests/test_panelkit.py` (first test file for `discord/panelkit.py`) — 7 tests: 3 DISC-05 rows (None-user RED, MISSING-shaped-falsy-user RED, legitimate-non-operator GREEN regression guard) + 4 DISC-06 rows (empty-marker RED, whitespace-marker RED, valid-marker GREEN regression guard, message-names-value RED).
- Two verified RESEARCH.md corrections baked in and honored: (1) the DISC-05 test calls `interaction_check` DIRECTLY and never asserts anything about `on_error` (Pitfall 1 empirically proved `on_error` IS invoked for an escaping `AttributeError` in discord.py 2.7.1 — asserting it was NOT invoked would have been a wrong test); (2) the guard is a falsy check, not `is None` (the real absence sentinel is `discord.utils.MISSING`, not `None`).
- GATE-01 green: full suite 70 passed (63 baseline + 7 new), import-hygiene 8 passed.

## Task Commits

Each task followed the RED-first two-commit pattern (D-13):

1. **Task 1 (RED): DISC-05 failing tests** - `18ea58d` (test)
2. **Task 1 (GREEN): DISC-05 falsy None/MISSING guard** - `ed18d8b` (fix)
3. **Task 2 (RED): DISC-06 failing tests** - `ee73757` (test)
4. **Task 2 (GREEN): DISC-06 empty/whitespace marker raise** - `2a3e0c7` (fix)

## Files Created/Modified

- `tests/test_panelkit.py` - NEW. `_FakeInteraction`/`_FakeUser`/`_FalsySentinel` synthetic doubles + `_build_test_panel()` minimal valid-panel helper; 7 tests across DISC-05 and DISC-06.
- `yahir_reusable_bot/discord/panelkit.py` - `interaction_check` gains the falsy None/MISSING guard at the top (before `.bot` dereference), extended docstring stating the D-40 sentinel contract; `PanelKit.__init__` gains the empty/whitespace-marker `ValueError` guard right after `super().__init__(timeout=None)`, before the collaborator assignments.

## Decisions Made

- DISC-05 guard is `if not interaction.user:` (falsy check) — an `is None` check would silently miss `discord.utils.MISSING` (verified: neither `User` nor `Member` override `__bool__`, so a real user is always truthy and the falsy check cannot false-positive).
- The RED test calls `interaction_check` directly rather than driving it through `View._scheduled_task`/`on_error` — RESEARCH.md's Pitfall 1 empirically proved `on_error` IS invoked for an escaping `AttributeError` in the pinned discord.py 2.7.1, so a test asserting `on_error` was never called would have been wrong.
- DISC-06 uses `raise ValueError` (not `assert`) — genuine consumer-input validation that must survive `-O`, matching MATCH-02's D-34 precedent; the message names the offending marker value (`{marker!r}`).
- The marker check is placed BEFORE the collaborator assignments and `_build_children()`/`_assert_layout()` so a bad marker fails before any child construction work happens.

## Deviations from Plan

None - plan executed exactly as written. Both fixes, both RED-first two-commit pairs, and the test file match the plan's `<action>` specification precisely.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 3 (public-surface footguns) is now complete — all 5 plans executed (SCHED-01, LIFE-02/03, MATCH-01/02, RELY-02/03, DISC-05/06). GATE-01 is green at 70 passed / 8 import-hygiene passed. No blockers for Phase 4.

### Consolidated consumer-visible behavior changes across Phase 3 (human-gated close-out, ECOSYSTEM.md §3)

Three build-time/runtime silent→loud (or silent→tolerant) behavior changes accumulated across this phase's five plans, none yet live in any consumer until a repin/deploy cycle (human-gated):

1. **D-38 (SCHED-01, Plan 01, `0d1f828`→`5e6fbf8`):** `SchedulerEngine.remove` is now idempotent — an already-gone job id is a no-op success instead of raising. A consumer that previously relied on the raise (e.g. to detect a reconcile bug) will now see silent success instead.
2. **D-34 (MATCH-02, Plan 03, `d98d3fc`→`fd38b47`):** `CommandRegistry.__init__`/`build_registry` now raises `ValueError` for a `spec.name` that is empty or not already casefolded. Previously such a spec constructed silently; a consumer registering a malformed spec will now hit a new build-time failure.
3. **D-41 (DISC-06, this plan, `ee73757`→`2a3e0c7`):** `PanelKit.__init__` now raises `ValueError` for an empty or whitespace-only `marker`. Previously this constructed silently and mis-owned every bot-authored pin; a consumer that (incorrectly) passed an empty marker will now hit a new build-time failure instead of a silent ownership bug.

None of these three are performed as part of any phase execution — the `pyproject.toml` `0.1.1 → 0.1.2` version bump, cutting the `v0.1.2` tag, and the WeatherBot repin/deploy remain deferred to the milestone close-out (`/gsd-complete-milestone` or equivalent), per `ECOSYSTEM.md` §3 and `PROJECT.md`'s "Close-out is human-gated" note.

---
*Phase: 03-public-surface-footguns*
*Completed: 2026-07-27*

## Self-Check: PASSED

- FOUND: tests/test_panelkit.py
- FOUND: yahir_reusable_bot/discord/panelkit.py
- FOUND: .planning/phases/03-public-surface-footguns/03-05-SUMMARY.md
- FOUND commit: 18ea58d (test DISC-05 RED)
- FOUND commit: ed18d8b (fix DISC-05 GREEN)
- FOUND commit: ee73757 (test DISC-06 RED)
- FOUND commit: 2a3e0c7 (fix DISC-06 GREEN)
