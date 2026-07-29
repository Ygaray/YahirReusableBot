---
phase: 03-public-surface-footguns
plan: 03
subsystem: api
tags: [unicode, casefold, command-matching, registry, python]

requires:
  - phase: 03-public-surface-footguns
    provides: "Wave 1-2 fixes (SCHED-01, LIFE-02, LIFE-03) green on main; GATE-01 baseline at 44 passed"
provides:
  - "CommandRegistry.__init__ validates every spec.name (non-empty, already-casefolded) at construction, raising ValueError otherwise (MATCH-02, D-34)"
  - "match_command's _keyword_boundary helper maps the keyword boundary to an index in the ORIGINAL (un-folded) string, fixing arg mis-slicing for length-changing casefolds (MATCH-01, D-35)"
  - "tests/test_registry.py and tests/test_match.py — the first tests for registry.py and match.py"
affects: [03-04, 03-05, milestone-close-out]

tech-stack:
  added: []
  patterns:
    - "Registration-time deny-by-default validation inside an existing single derivation pass (no new traversal) — same idiom as is_transient's deny-by-default posture"
    - "O(n) incremental original-index boundary scan for Unicode casefold length-changes, with overshoot-without-exact-hit folded into the existing continue/non-match control flow"

key-files:
  created:
    - tests/test_registry.py
    - tests/test_match.py
  modified:
    - yahir_reusable_bot/registry/registry.py
    - yahir_reusable_bot/registry/match.py

key-decisions:
  - "D-34: CommandRegistry.__init__ raises ValueError for empty or not-already-casefolded spec.name, validated inside the existing derivation pass, before by_name/by_keyword_len_desc are derived — no per-match casefold fallback"
  - "D-35: _keyword_boundary(stripped, name) computes the ORIGINAL-string index by accumulating each original character's casefolded length until it reaches len(name) exactly; overshoot-without-exact-hit returns None, folding into the existing word-boundary continue"
  - "MATCH-01 + MATCH-02 landed together in one plan per the ROADMAP-mandated pairing — fixing one without the other leaves the matcher half-consistent"

patterns-established:
  - "Registration-time deny-by-default validation (fail-LOUD at construction, raise not assert, names the offending value)"
  - "Boundary-mapped slicing for Unicode-safe raw-case extraction from a casefolded prefix match"

requirements-completed: [MATCH-01, MATCH-02]

coverage:
  - id: D1
    description: "Empty spec.name raises ValueError at CommandRegistry/build_registry construction"
    requirement: MATCH-02
    verification:
      - kind: unit
        ref: "tests/test_registry.py#test_empty_name_raises_at_construction"
        status: pass
      - kind: unit
        ref: "tests/test_registry.py#test_empty_name_raises_through_build_registry"
        status: pass
      - kind: unit
        ref: "tests/test_registry.py#test_value_error_names_the_offending_empty_value"
        status: pass
    human_judgment: false
  - id: D2
    description: "Uppercase spec.name raises ValueError at construction (can never become permanently unmatchable)"
    requirement: MATCH-02
    verification:
      - kind: unit
        ref: "tests/test_registry.py#test_uppercase_name_raises_at_construction"
        status: pass
      - kind: unit
        ref: "tests/test_registry.py#test_uppercase_name_raises_through_build_registry"
        status: pass
      - kind: unit
        ref: "tests/test_registry.py#test_value_error_names_the_offending_uppercase_value"
        status: pass
    human_judgment: false
  - id: D3
    description: "Valid (non-empty, already-casefolded) specs still construct without regression"
    requirement: MATCH-02
    verification:
      - kind: unit
        ref: "tests/test_registry.py#test_valid_names_still_construct_without_regression"
        status: pass
    human_judgment: false
  - id: D4
    description: "Length-changing casefold (sharp-s, fi/st ligatures) extracts the correct RAW-case arg"
    requirement: MATCH-01
    verification:
      - kind: unit
        ref: "tests/test_match.py#test_length_changing_casefold_sharp_s_extracts_correct_raw_arg"
        status: pass
      - kind: unit
        ref: "tests/test_match.py#test_ligature_fi_extracts_correct_raw_arg"
        status: pass
      - kind: unit
        ref: "tests/test_match.py#test_ligature_st_extracts_correct_raw_arg"
        status: pass
    human_judgment: false
  - id: D5
    description: "Adversarial single-character casefold overshoot (spec.name='s', input 'ß foo') is correctly a non-match"
    requirement: MATCH-01
    verification:
      - kind: unit
        ref: "tests/test_match.py#test_adversarial_single_char_overshoot_is_a_non_match"
        status: pass
    human_judgment: false
  - id: D6
    description: "Empty/whitespace-only input and ASCII raw-case preservation remain clean (regression guards)"
    requirement: MATCH-01
    verification:
      - kind: unit
        ref: "tests/test_match.py#test_empty_input_is_a_clean_non_match"
        status: pass
      - kind: unit
        ref: "tests/test_match.py#test_whitespace_only_input_is_a_clean_non_match"
        status: pass
      - kind: unit
        ref: "tests/test_match.py#test_raw_case_preserved_for_ascii_regression_guard"
        status: pass
    human_judgment: false
  - id: D7
    description: "The new build-time ValueError (MATCH-02) is a consumer-visible behavior change requiring human sign-off at the milestone close-out before any repin/deploy"
    verification: []
    human_judgment: true
    rationale: "This is a release-process decision (version bump / tag / WeatherBot repin timing), not a testable code assertion — ECOSYSTEM.md gates all such release steps behind explicit human confirmation."

duration: 6min
completed: 2026-07-27
status: complete
---

# Phase 3 Plan 3: MATCH-01 + MATCH-02 registry casefold-symmetry fix Summary

**CommandRegistry now rejects empty/uppercase spec.name at construction (D-34), and match_command's arg slice is remapped to the original un-folded string via a new O(n) `_keyword_boundary` helper so length-changing casefolds (ß→ss, ﬁ→fi, ﬆ→st) extract the correct raw-case argument instead of silently failing the word-boundary guard (D-35).**

## Performance

- **Duration:** 6 min
- **Started:** 2026-07-27T19:15:40-06:00 (git log, first commit of this plan's work)
- **Completed:** 2026-07-27T19:19:40-06:00
- **Tasks:** 2
- **Files modified:** 4 (2 new test files, 2 source files)

## Accomplishments
- `CommandRegistry.__init__` validates every `spec.name` inside its existing single derivation pass — non-empty AND already-casefolded — raising `ValueError` (naming the offending value) otherwise; `build_registry` forwards the exception for free
- `match.py` gains a new private `_keyword_boundary(stripped, name) -> int | None` helper: an O(n) incremental scan that accumulates each ORIGINAL character's casefolded length and returns the original-string index where it reaches `len(name)` exactly, or `None` on overshoot (folded into the existing `continue`)
- `match_command` now slices `rest = stripped[boundary:]` instead of `stripped[len(spec.name):]`, fixing the arg extraction for `ß`, `ﬁ`, `ﬆ` and any of the 104 length-changing Unicode casefold codepoints, while preserving the RAW-case `ParsedCommand.arg` contract
- Two new test files founding the test substrate for `registry.py` and `match.py` (neither had a prior test)

## Task Commits

Each task followed the RED-parent/GREEN-child two-commit idiom (D-13):

1. **Task 1: MATCH-02 — validate spec.name at CommandRegistry construction**
   - `d98d3fc` (test) — `tests/test_registry.py`: 6 of 7 tests RED pre-fix (empty-name and uppercase-name raise-expectations fail with "DID NOT RAISE")
   - `fd38b47` (feat) — `yahir_reusable_bot/registry/registry.py`: validation loop added inside the existing derivation pass; all 7 tests GREEN

2. **Task 2: MATCH-01 — map the keyword boundary to the original string**
   - `39ababf` (test) — `tests/test_match.py`: 4 of 7 tests RED pre-fix (sharp-s/ligature rows and the adversarial overshoot row fail)
   - `2fa1908` (feat) — `yahir_reusable_bot/registry/match.py`: `_keyword_boundary` helper added, `match_command` uses the mapped boundary; all 7 tests GREEN

**Plan metadata:** committed alongside this SUMMARY (docs commit follows).

## Files Created/Modified
- `tests/test_registry.py` — NEW. 7 tests: empty-name/uppercase-name raise `ValueError` (direct construction and via `build_registry`), the message names the offending value, valid specs still construct without regression.
- `tests/test_match.py` — NEW. 7 tests: sharp-s/ligature (`ß`, `ﬁ`, `ﬆ`) raw-case arg extraction, the adversarial single-char overshoot non-match, empty/whitespace-input non-match, ASCII raw-case regression guard.
- `yahir_reusable_bot/registry/registry.py` — `CommandRegistry.__init__` gains the D-34 validation loop (16 lines added, inside the existing pass, before `by_name`/`by_keyword_len_desc` derivation).
- `yahir_reusable_bot/registry/match.py` — new `_keyword_boundary` private helper (24 lines) plus the `match_command` call-site swap from `stripped[len(spec.name):]` to `stripped[boundary:]` (with a `boundary is None` guard folded into the existing `continue`).

## Decisions Made
- **D-34 (MATCH-02):** Reject loudly at registration — `CommandRegistry.__init__` validates `spec.name` is non-empty and already-casefolded, raising `ValueError` with a message that names the offending value. Rejected alternative (per RESEARCH/CONTEXT): casefold `spec.name` at match time as a tolerant fallback — rejected because it silently hides a consumer wiring bug and pays a per-match cost on the hot path.
- **D-35 (MATCH-01):** Preserve the raw-case arg contract by mapping the keyword boundary back to an index in the ORIGINAL stripped string, using the verified O(n) `_keyword_boundary` algorithm from RESEARCH.md Code Examples §1 (accumulate per-original-character casefolded length; exact-match-only, overshoot → `None` → existing `continue`). Rejected alternative: slicing from the folded string, which would silently lowercase a consumer's argument.
- Both fixes landed in one plan per the ROADMAP-mandated MATCH-01+MATCH-02 pairing — the length mis-slice bites from the INPUT side even with perfectly-normalized names, so the two fixes are genuinely independent axes of one contract and had to ship together.

## Deviations from Plan

None — plan executed exactly as written. The RED test suite for MATCH-01 surfaced a slightly different pre-fix failure MODE than the plan's literal framing ("mis-slices the arg") — in practice, the overshoot slice for the three length-changing-casefold cases (`ßtatus`, `ﬁnd`, `ﬆatus`) lands directly on the argument text with no leading whitespace, so the EXISTING word-boundary guard rejects the match entirely (`spec=None`, not merely a wrong `arg`). This is a more severe symptom of the exact same root cause the plan named, required no plan or algorithm change, and was documented precisely in the test module docstring for accuracy. Not tracked as a Rule 1-4 deviation since it did not change any code path, fix approach, or test assertion shape — only clarified the docstring's description of the pre-fix symptom.

## Issues Encountered
None.

## Consumer-Visible Behavior Change (for milestone close-out)

**MATCH-02's `CommandRegistry`/`build_registry` construction now raises `ValueError`** for a `spec.name` that is empty or not already casefolded (e.g., `"Status"` instead of `"status"`). Before this fix, such a spec constructed silently — an empty name could silently claim blank input, and an uppercase name could become permanently unmatchable with no signal at build time. This is a **new build-time failure mode** a consumer (WeatherBot, or a future bot) could hit if it registers a malformed command spec. Per `ECOSYSTEM.md` §3, this hub change is not live in any consumer until that consumer cuts a repin (new tag → `[tool.uv.sources]` bump → `uv lock --upgrade` → `uv sync` → deploy) — that step remains human-gated and is deferred to the milestone's close-out, alongside the SCHED-01 idempotent-`remove()` behavior change already recorded in Plan 02.

## User Setup Required

None — no external service configuration required. No new dependency, no `pyproject.toml` change (RESEARCH confirms zero new dependencies for this phase).

## Next Phase Readiness

GATE-01 green (58 passed full suite, 8 passed import-hygiene, up from the 44-passed baseline after Wave 2). `registry/` is now fully covered by tests for the first time. Ready for Plan 04 (RELY-02 + RELY-03, `reliability/retry.py`) per the RESEARCH-recommended sequencing — no shared state or import edges between `registry/` and `reliability/`, so this plan's completion has no coupling risk to the next.

---
*Phase: 03-public-surface-footguns*
*Completed: 2026-07-27*

## Self-Check: PASSED

- FOUND: tests/test_registry.py
- FOUND: tests/test_match.py
- FOUND: yahir_reusable_bot/registry/registry.py
- FOUND: yahir_reusable_bot/registry/match.py
- FOUND commit: d98d3fc (test: MATCH-02 RED)
- FOUND commit: fd38b47 (feat: MATCH-02 GREEN)
- FOUND commit: 39ababf (test: MATCH-01 RED)
- FOUND commit: 2fa1908 (feat: MATCH-01 GREEN)
