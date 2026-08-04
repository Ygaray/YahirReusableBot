---
phase: 07-v0-1-2-debt-paydown
plan: 01
subsystem: registry
tags: [python, command-registry, validation]

# Dependency graph
requires:
  - phase: 03-reusable-public-surface-footguns
    provides: D-34's existing non-empty/casefold validation loop in CommandRegistry.__init__
provides:
  - Construction-time duplicate CommandSpec.name rejection in CommandRegistry, closing MATCH-03
affects: [registry]

# Tech tracking
tech-stack:
  added: []
  patterns: ["seen: set[str] uniqueness check added inside an existing single-pass validation loop, not a second pass"]

key-files:
  created: []
  modified:
    - tests/test_registry.py
    - yahir_reusable_bot/registry/registry.py

key-decisions:
  - "Duplicate-name uniqueness check lands inside the existing D-34 for-loop (one pass, not two), raising ValueError before self.by_name is derived, per CONTEXT.md D-33 discretion."
  - "Uniqueness compares spec.name by Python str equality over code points, no Unicode normalization — matches D-34's verbatim-comparison posture and is pinned by a dedicated NFC/NFD regression test."
  - "Empty-registry and single-spec-registry construction are pinned as GREEN-both-ways boundary guards (never trip the duplicate check), following the pinned-limitation idiom from tests/test_identity.py."

patterns-established:
  - "GREEN-both-ways boundary-guard tests (degenerate input, equality-semantics) live alongside genuinely-RED regression tests in the same file, each explicitly labeled in its docstring so the GATE-02 RED-first ancestry audit does not misread them as a gap."

requirements-completed: [MATCH-03]

coverage:
  - id: D1
    description: "Constructing a CommandRegistry from two CommandSpecs sharing a name raises ValueError at construction, naming the duplicated value, before by_name is derived; build_registry propagates the same error"
    requirement: "MATCH-03"
    verification:
      - kind: unit
        ref: "tests/test_registry.py#test_duplicate_name_raises_at_construction"
        status: pass
      - kind: unit
        ref: "tests/test_registry.py#test_duplicate_name_raises_through_build_registry"
        status: pass
      - kind: unit
        ref: "tests/test_registry.py#test_value_error_names_the_duplicated_value"
        status: pass
    human_judgment: false
  - id: D2
    description: "Degenerate-input and Unicode-normalization equality-semantics contracts pinned: empty/single-spec registries never trip the duplicate guard; NFC/NFD name variants are distinct registrations, not duplicates"
    requirement: "MATCH-03"
    verification:
      - kind: unit
        ref: "tests/test_registry.py#test_empty_and_single_spec_registries_construct_without_duplicate_guard"
        status: pass
      - kind: unit
        ref: "tests/test_registry.py#test_unicode_normalization_variants_are_distinct_names_not_duplicates"
        status: pass
    human_judgment: false

# Metrics
duration: 10min
completed: 2026-08-04
status: complete
---

# Phase 07 Plan 01: MATCH-03 duplicate CommandSpec.name rejection Summary

**CommandRegistry now raises ValueError at construction when two CommandSpecs share a name, closing the one real public-surface footgun the v0.1.2 audit left open.**

## Performance

- **Duration:** ~10 min
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments
- Extended `tests/test_registry.py` with 5 new tests: 3 genuinely RED against pre-fix source (duplicate raises at construction, through `build_registry`, and the message names the duplicated value) and 2 GREEN-both-ways boundary guards (empty/single-spec registries; NFC/NFD Unicode-normalization-variant names are distinct, not duplicates).
- Added a `seen: set[str]` uniqueness check inside the existing D-34 validation loop in `CommandRegistry.__init__`, raising `ValueError` before `self.by_name` is derived. No second pass, no change to `by_name`/`by_keyword_len_desc`/`render_help`.
- Full suite (163 passed, 1 pre-existing unrelated warning — HYG-03, tracked separately), import-hygiene gate (10 passed), and `ruff check` all green.

## Task Commits

Each task was committed atomically:

1. **Task 1: Commit the MATCH-03 duplicate-name tests RED** - `d92351d` (test)
2. **Task 2: Add the uniqueness check to the D-34 validation loop (GREEN)** - `7da4568` (fix)

GATE-02 RED-first ancestry: `7da4568` is the direct git parent of `d92351d`'s child commit (verified via `git log --oneline -2`), and the RED commit's `git ls-tree` predates the fix — the two duplicate-raise assertions genuinely failed against pre-fix `registry.py` (`DID NOT RAISE ValueError`) before the GREEN commit landed.

**Plan metadata:** (this commit, following the SUMMARY write)

## Files Created/Modified
- `tests/test_registry.py` - Added 5 tests (3 RED, 2 GREEN-both-ways) + docstring self-proof addendum for MATCH-03
- `yahir_reusable_bot/registry/registry.py` - Added `seen: set[str]` uniqueness check inside the existing D-34 loop; new `# MATCH-03 (v0.1.2 WR-02):` comment block explaining the fix's placement and rationale

## Decisions Made
- Followed CONTEXT.md's Claude's Discretion for MATCH-03 exactly: `seen: set[str]` inside the existing loop (not a second pass), error type locked to `ValueError`, message interpolates only `spec.name` (never `spec.bind` or the whole spec) per the threat register's T-07-01-01 mitigation.
- Used explicit `é` / `́` escape sequences (rather than bare literal `café` typed twice) for the two Unicode-normalization-variant test strings, to make the NFC/NFD distinction self-documenting and immune to any source-encoding ambiguity.

**Exact `ValueError` message text shipped:**
```
CommandSpec.name must be unique per registry (a duplicate silently overwrites in by_name while by_keyword_len_desc and render_help still carry both entries); got duplicate 'status'
```

**Consumer-breaking note:** the WeatherBot duplicate-`spec.name` sweep required by this change is surfaced for the human-gated repin (per `ECOSYSTEM.md` §3 and CONTEXT.md's MATCH-03 discretion) and was **NOT** executed as part of this plan. No WeatherBot file, `pyproject.toml` version, or tag was touched.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

MATCH-03 closed; full suite and import-hygiene gates green. Ready for 07-02 (the next sequenced plan in this phase). The pre-existing HYG-03 warning (`1 warning` in the full-suite run) is out of scope for this plan and is addressed by a later plan in this phase per the ROADMAP.

---
*Phase: 07-v0-1-2-debt-paydown*
*Completed: 2026-08-04*

## Self-Check: PASSED

- FOUND: tests/test_registry.py
- FOUND: yahir_reusable_bot/registry/registry.py
- FOUND: .planning/phases/07-v0-1-2-debt-paydown/07-01-SUMMARY.md
- FOUND: d92351d (test commit)
- FOUND: 7da4568 (fix commit)
