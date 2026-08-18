---
phase: 08-redaction-hardening-cleanup
plan: 03
subsystem: docs
tags: [python, pytest, documentation, regression-testing, structlog, redaction]

# Dependency graph
requires:
  - phase: 08-02
    provides: on_error optional hook on RedactingWriter, mirroring on_redaction's registration shape (code half of REDACT-10)
provides:
  - "EXTENSION-GUIDE.md section 7 malformed-pattern fail-closed contract paragraph, naming the placeholder behavior and the on_error hook"
  - "Three token-anchored regression gates (malformed contract, telemetry semantics, reconfigure discipline), each with a proven non-vacuous self-proof"
  - "Standing anchor-collision guard preventing a future anchor from colliding with the recipe-2 ordering assertion"
affects: [08-05 (phase gate audit)]

# Actuals (#2632)
actuals:
  tokens: 4112
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Whitespace-normalized anchor matching: collapse the guide's own hard-wrap line breaks (re.sub(r\"\\s+\", \" \", ...)) before substring-matching a multi-word anchor phrase, since a phrase can straddle a markdown line-wrap boundary even though it reads as one sentence"

key-files:
  created: []
  modified:
    - tests/test_extension_guide.py
    - EXTENSION-GUIDE.md

key-decisions:
  - "Anchor tokens chosen exactly as pinned in the plan's Plan-time decisions table, confirmed marker-free (no anchor spans an em dash, backtick, or emphasis marker)"
  - "The two new 'pins' gates (telemetry semantics, reconfigure discipline) normalize whitespace before matching, collapsing hard-wrap line breaks into single spaces — discovered necessary live when the reconfigure-discipline 'reason' anchor ('configuration is global mutable state') turned out to straddle EXTENSION-GUIDE.md's own line wrap at :186-187. The already-committed Task 1 malformed-contract gate was NOT touched to add this normalization since its anchors do not span a wrap boundary and the plan prohibits editing already-committed test code within this plan"
  - "DOCS-05's two D-04 gates (telemetry, reconfigure) land GREEN on arrival, per the plan's stated disposition — the claims they pin are already true of the guide as written, so GATE-02 evidence is each gate's non-vacuity self-proof observed failing against a broken copy, not an artificial RED commit. Matches the Phase-6 Known-limitations precedent (T-06-16)"

patterns-established:
  - "Non-vacuity self-proof pair (2-function shape): a content gate plus a sibling self-proof that excises the target paragraph from a temp copy, monkey-patches GUIDE_PATH, calls the gate directly, and asserts it raises AssertionError with the vacuous-reraise discriminator — copied verbatim from the Known-limitations gate template for all three new gate pairs"

requirements-completed: [REDACT-10, DOCS-05]

coverage:
  - id: D1
    description: "EXTENSION-GUIDE.md section 7 states the malformed-pattern write-path contract consumer-facing: fails closed, withholds the payload behind a fixed placeholder, never raises, and the optional on_error hook makes it observable"
    requirement: "REDACT-10"
    verification:
      - kind: unit
        ref: "tests/test_extension_guide.py#test_seam_08_section_states_the_malformed_pattern_failclosed_contract"
        status: pass
      - kind: unit
        ref: "tests/test_extension_guide.py#test_selfproof_malformed_contract_gate_catches_a_deleted_paragraph"
        status: pass
    human_judgment: false
  - id: D2
    description: "Section 7 telemetry semantics (changed-writes, not-a-substitution-total, monotonic) are regression-gated with a proven non-vacuous self-proof"
    requirement: "DOCS-05"
    verification:
      - kind: unit
        ref: "tests/test_extension_guide.py#test_seam_08_section_pins_the_changed_writes_telemetry_semantics"
        status: pass
      - kind: unit
        ref: "tests/test_extension_guide.py#test_selfproof_telemetry_semantics_gate_catches_a_deleted_paragraph"
        status: pass
    human_judgment: false
  - id: D3
    description: "Section 7 reconfigure-recheck discipline (call again after any reconfiguration, global-mutable-state reason) is regression-gated with a proven non-vacuous self-proof"
    requirement: "DOCS-05"
    verification:
      - kind: unit
        ref: "tests/test_extension_guide.py#test_seam_08_section_pins_the_reconfiguration_recheck_discipline"
        status: pass
      - kind: unit
        ref: "tests/test_extension_guide.py#test_selfproof_reconfigure_discipline_gate_catches_a_deleted_paragraph"
        status: pass
    human_judgment: false
  - id: D4
    description: "No new anchor token collides with the pre-existing recipe-2 ordering assertion, enforced mechanically rather than by review"
    requirement: "DOCS-05"
    verification:
      - kind: unit
        ref: "tests/test_extension_guide.py#test_new_anchor_tokens_do_not_collide_with_the_recipe_2_ordering_assertion"
        status: pass
    human_judgment: false

duration: ~25min
completed: 2026-08-17
status: complete
---

# Phase 8 Plan 3: EXTENSION-GUIDE.md malformed-pattern contract + non-vacuous DOCS-05 regression gates Summary

**Closed REDACT-10's documentation half (new section 7 paragraph naming the fail-closed placeholder and `on_error` hook) and all of DOCS-05 (three token-anchored regression gates — malformed contract, telemetry semantics, reconfigure discipline — each proven non-vacuous by observed self-proof failure against a broken copy, plus a standing anchor-collision guard).**

## Performance

- **Duration:** ~25 min
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- `EXTENSION-GUIDE.md` section 7 gained a new bolded-lead-in paragraph, "When a pattern is malformed.", stating the trigger (unregistered `RedactionPattern` raising `re.error`), the fail-closed disposition (withhold + fixed placeholder, never forward, never raise), and the `on_error` observability hook contract (fires after the placeholder write, receives only the error, never the withheld payload, never moves `redaction_count`) — placed immediately after "Telemetry, described accurately." and before "Known limitations." per the plan's placement decision.
- `tests/test_extension_guide.py` gained `_SEAM_08_NEW_ANCHORS` (one constant holding all three gates' anchor tuples) plus three gate/self-proof pairs and a standing collision guard — 8 new test functions, 226 net-new lines, zero deleted lines across all three task commits.
- REDACT-10 fully closed: the malformed-pattern contract now lives in both the `write` docstring (already, from 08-02) and the consumer-facing guide (this plan).
- DOCS-05 fully closed: all three of section 7's load-bearing behavioral claims (malformed contract, telemetry semantics, reconfigure discipline) are now regression-gated, matching the T-06-16 Known-limitations precedent from Phase 6.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the malformed-pattern contract gate, committed RED** - `4dc6f2c` (test)
2. **Task 2: State the malformed-pattern fail-closed contract in section 7 (GREEN)** - `aa59a1a` (docs)
3. **Task 3: Gate the telemetry and reconfigure claims, plus the anchor-collision constraint** - `6900c42` (test)

**Plan metadata:** (this commit, made by the orchestrator after wave completion)

## Files Created/Modified
- `tests/test_extension_guide.py` - Added `_SEAM_08_NEW_ANCHORS`, the malformed-contract gate pair (Task 1, RED-first), the telemetry-semantics gate pair, the reconfigure-discipline gate pair, and the anchor-collision guard (Task 3, GREEN-on-arrival per DOCS-05's stated disposition)
- `EXTENSION-GUIDE.md` - Added the "When a pattern is malformed." paragraph to section 7 (Task 2)

## Decisions Made
- Anchor tokens used exactly as pinned in the plan's Plan-time decisions table.
- The telemetry-semantics and reconfigure-discipline gates normalize whitespace (collapse hard-wrap line breaks to single spaces) before anchor matching. This was discovered necessary live: the reconfigure-discipline "reason" anchor phrase (`configuration is global mutable state`) turned out to straddle EXTENSION-GUIDE.md's own markdown line wrap at `:186`→`:187` (`...configuration is\nglobal mutable state...`), so a literal-newline substring match failed even though the phrase reads as one contiguous sentence to a human. Fixed via `re.sub(r"\s+", " ", section_text.lower())` in the two Task 3 gate functions. The already-committed Task 1 malformed-contract gate was deliberately left untouched — its anchors do not span a wrap boundary (confirmed) and editing already-committed test code within this plan would violate the plan's own additive-only prohibition, so this qualifies as a Rule 1 (auto-fix bug) fix scoped to the two new gates it actually affects, not a rewrite of committed code.
- DOCS-05's two D-04 gates (telemetry, reconfigure) shipped GREEN on arrival, matching the plan's stated disposition — no artificial RED commit was manufactured. GATE-02 evidence is each gate's self-proof, confirmed non-vacuous by the live observations below.

## Deviations from Plan

**1. [Rule 1 - Bug] Working-tree state lost during a self-proof observation step, redone**
- **Found during:** Task 3's manual non-vacuity observation for the collision guard
- **Issue:** After observing the collision guard go red against a deliberately-injected colliding anchor, I ran `git checkout -- tests/test_extension_guide.py` to revert the scratch mutation. Task 3's test additions were still uncommitted at that point, so this checkout reverted the file all the way back to the Task 1 commit (`4dc6f2c`), silently discarding the five new Task 3 test functions along with the intended scratch-mutation revert.
- **Fix:** Re-applied the full Task 3 addition (telemetry pair, reconfigure pair, collision guard), this time with the whitespace-normalization fix folded in from the start rather than as a follow-up edit, then re-ran the full verification sweep (`tests/test_extension_guide.py` 16/16, full suite 206/206, import-hygiene 10/10, ruff clean) before committing.
- **Files modified:** `tests/test_extension_guide.py` (no net change to the final committed content vs. what would have been committed without the mistake — the redo reproduced the identical five test functions)
- **Verification:** `git diff --stat` on the eventual Task 3 commit shows 226 insertions, 0 deletions — purely additive, matching the acceptance criteria.
- **Committed in:** `6900c42` (Task 3 commit; no separate commit needed since the loss occurred entirely before Task 3's first commit attempt)

---

**Total deviations:** 1 auto-fixed (1 process mistake, self-corrected before commit)
**Impact on plan:** No impact on the final committed artifacts — the redo produced identical content and the mistake never touched a committed state. Recorded per this project's process-transparency convention.

## Issues Encountered
None beyond the deviation above.

## Self-proof non-vacuity evidence

Per this plan's `<output>` requirement, each of the three new gates and the collision guard was proven non-vacuous by live observation — a scratch mutation applied to a real copy, the matching test re-run, the failure captured, then reverted. All four observations below are from the actual GATE-02 verification pass performed during this plan's execution (not asserted from the self-proof tests' own internal logic, which is a separate, also-passing check).

### 1. Malformed-pattern contract gate
**Mutation:** In a scratch copy of `EXTENSION-GUIDE.md`, reworded the trigger anchor: `**When a pattern is malformed.**` → `**When a pattern is abnormal.**` (only "malformed" → "abnormal" in the heading; the word "malformed" no longer appears anywhere in the guide).
**Test run:** `uv run pytest tests/test_extension_guide.py::test_seam_08_section_states_the_malformed_pattern_failclosed_contract -q`
**Observed failure:**
```
E       AssertionError: SEAM-08 section is missing malformed-pattern fail-closed contract concept(s): ['the trigger'] (REDACT-10)
E       assert not ['the trigger']
```
**Reverted:** `git checkout -- EXTENSION-GUIDE.md`; full guide-test suite re-confirmed green (16/16) afterward.

### 2. Telemetry semantics gate
**Mutation:** In a scratch copy, `is monotonic for process lifetime` → `is cumulative for process lifetime`.
**Test run:** `uv run pytest tests/test_extension_guide.py::test_seam_08_section_pins_the_changed_writes_telemetry_semantics -q`
**Observed failure:**
```
E       AssertionError: SEAM-08 section is missing telemetry semantics concept(s): ['monotonicity'] (DOCS-05)
E       assert not ['monotonicity']
```
**Reverted:** `git checkout -- EXTENSION-GUIDE.md`.

### 3. Reconfigure discipline gate
**Mutation:** In a scratch copy, `global mutable state` → `shared runtime configuration`.
**Test run:** `uv run pytest tests/test_extension_guide.py::test_seam_08_section_pins_the_reconfiguration_recheck_discipline -q`
**Observed failure:**
```
E       AssertionError: SEAM-08 section is missing reconfigure-discipline concept(s): ['the reason'] (DOCS-05)
E       assert not ['the reason']
```
This same reword-and-rerun also independently confirmed the whitespace-normalization fix is load-bearing (the original wrap-unaware match failed identically on the LIVE, unmodified guide before the fix was applied — see Decisions Made above).
**Reverted:** `git checkout -- EXTENSION-GUIDE.md`; full guide-test suite re-confirmed green (16/16) afterward.

### 4. Anchor-collision guard
**Mutation:** In a scratch edit of `tests/test_extension_guide.py`, added a deliberately colliding anchor: `"the observability hook": ("on_error",)` → `"the observability hook": ("on_error", "deliberately before any stdlib"),` (the injected string contains the incumbent `"before any"` collision substring from `:123`).
**Test run:** `uv run pytest tests/test_extension_guide.py::test_new_anchor_tokens_do_not_collide_with_the_recipe_2_ordering_assertion -q`
**Observed failure:**
```
E       AssertionError: New anchor token(s) collide with the existing recipe-2 ordering assertion ('before any') at tests/test_extension_guide.py:123: ['deliberately before any stdlib']
E       assert not ['deliberately before any stdlib']
```
**Reverted:** intended via `git checkout -- tests/test_extension_guide.py`, which (per the Deviations section above) also reverted Task 3's then-uncommitted work; Task 3's additions were redone from scratch and re-verified before commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- REDACT-10 and DOCS-05 are both fully closed. Section 7 now states the malformed-pattern fail-closed contract consumer-facing, and all three of its load-bearing behavioral claims are regression-gated with proven non-vacuous self-proofs.
- 08-04 (the remaining Phase 8 plan — static type-check gate, D-03) is unaffected by this plan's scope; no shared files touched.
- 08-05 (phase gate audit) can cite this plan's commit adjacency (`4dc6f2c` RED → `aa59a1a` GREEN → `6900c42` DOCS-05-GATE-02-adjacent) directly from git history.
- No blockers.

---
*Phase: 08-redaction-hardening-cleanup*
*Completed: 2026-08-17*

## Self-Check: PASSED

- FOUND: `.planning/phases/08-redaction-hardening-cleanup/08-03-SUMMARY.md`
- FOUND: `4dc6f2c` (Task 1 RED commit)
- FOUND: `aa59a1a` (Task 2 GREEN commit)
- FOUND: `6900c42` (Task 3 commit)
- FOUND: `662cb07` (SUMMARY.md commit)
