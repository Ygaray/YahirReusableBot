---
phase: 01-reachable-reliability
plan: 03
subsystem: lifecycle
tags: [proc-cmdline, pid-recycling, RED-first, LIFE-01]

# Dependency graph
requires:
  - phase: 01-reachable-reliability (Plan 01)
    provides: "tests/conftest.py cmdline_bytes fixture"
provides:
  - "tests/test_identity.py — LIFE-01 regression suite (7 tests): all 4 D-19-locked truth-table rows, plus the two-interpreter-flag false negative, the pytest-nested-selector discriminator, and the bounds-check degrade guard"
  - "yahir_reusable_bot.lifecycle.identity._argv_matches_marker fixed per D-04/D-06 first-`-m` scan"
affects: [01-04-PLAN.md]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RED-first two-commit proof (D-13): test-only commit, then fix commit as its direct child — git ancestry is the evidence, audited mechanically by Plan 04"
    - "First-`-m`-wins scan (D-04/D-06) replacing overlapping-slice membership testing, mirroring Python's own CLI grammar"

key-files:
  created: [tests/test_identity.py]
  modified: [yahir_reusable_bot/lifecycle/identity.py]

key-decisions:
  - "Implemented D-04 exactly: lowest-index `-m` scan with bounds-checked exact-adjacency check, replacing `b\"-m\" in argv[1:3] and proc_marker in argv[1:4]`"
  - "D-06's 'first -m wins' rule and D-05's rejected fixed-position alternative and D-07's rejected argv0-interpreter-check both written into the docstring, not just the commit message"
  - "argv0-basename branch (identity.py:145-147, unchanged line numbers before the edit) left byte-identical — confirmed via git diff HEAD~1 HEAD showing no `+`/`-` line touching the `prog ==` comparison"
  - "Two-interpreter-flag row (test_two_interpreter_flags_before_module_switch_matches) included as additive coverage beyond the four ROADMAP-locked rows, per the plan's own instruction"

requirements-completed: [LIFE-01]

coverage:
  - id: D1
    description: "is_running_process returns False for the recycled-PID decoy (python -m pytest <marker>) — the phase's sharpest live defect, previously a security-relevant false positive"
    requirement: "LIFE-01"
    verification:
      - kind: unit
        ref: "tests/test_identity.py::test_decoy_positional_marker_arg_does_not_match"
        status: pass
    human_judgment: false
  - id: D2
    description: "is_running_process returns True for a daemon behind one or two interpreter flags before -m (python -O -m <marker> run; python -O -B -m <marker> run) — closes both the locked false-negative row and the additive two-flag row"
    requirement: "LIFE-01"
    verification:
      - kind: unit
        ref: "tests/test_identity.py::test_interpreter_flag_before_module_switch_matches, tests/test_identity.py::test_two_interpreter_flags_before_module_switch_matches"
        status: pass
    human_judgment: false
  - id: D3
    description: "Plain -m form and argv0-basename form both still match (regression guards); argv0-basename branch resolves through the unchanged branch, not the -m branch"
    requirement: "LIFE-01"
    verification:
      - kind: unit
        ref: "tests/test_identity.py::test_plain_module_switch_form_matches, tests/test_identity.py::test_argv0_basename_form_matches"
        status: pass
    human_judgment: false
  - id: D4
    description: "First-`-m`-wins discriminator: python -m pytest -m <marker> (pytest's own -m marker-selector) does not match — proves the rule is correct, not merely convenient"
    requirement: "LIFE-01"
    verification:
      - kind: unit
        ref: "tests/test_identity.py::test_nested_selector_switch_does_not_match"
        status: pass
    human_judgment: false
  - id: D5
    description: "Truncated argv (python -m with nothing after it) degrades to False and never raises IndexError"
    requirement: "LIFE-01"
    verification:
      - kind: unit
        ref: "tests/test_identity.py::test_trailing_module_switch_without_target_does_not_match"
        status: pass
    human_judgment: false
  - id: D6
    description: "Git history proves RED-first: test-only commit (0f0a9ad) is the direct parent of the fix commit (5273c13); neither amended/squashed"
    requirement: "LIFE-01"
    verification:
      - kind: unit
        ref: "git show --name-only --format= HEAD (identity.py only); git show --name-only --format= HEAD~1 (test_identity.py only)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Concurrent-signal race (guard returns True, then the caller's actual signal-send races against a process exit) — flagged unresolved by the planner's edge-probe accounting, consumer-side and outside this repo's Architectural Responsibility Map"
    requirement: "LIFE-01"
    verification: []
    human_judgment: true
    rationale: "The unclassified edge-probe item from the planner's Phase 1 CONTEXT/plan carries this forward unresolved by rule (never auto-dismissed). It names a race between this guard's boolean return and the consumer's subsequent SIGHUP delivery, which happens entirely in the consumer's process, outside this repo. No test in this hub repo can assert it without replicating consumer-side signal-delivery code, which would be out of the hub's Architectural Responsibility Map. Restated here so it survives into phase verification, per the plan's <output> instruction."

duration: ~20min
completed: 2026-07-22
status: complete
---

# Phase 1 Plan 3: LIFE-01 Fix — first-`-m`-scan for `_argv_matches_marker` Summary

**Closed the LIFE-01 recycled-PID SIGHUP false-positive by replacing overlapping-slice membership testing with a bounds-checked first-`-m`-wins scan (D-04/D-06), proven RED-first with a two-commit history: a 7-test regression suite committed alone and failing on both adversarial rows against pre-fix source, then the fix committed as its direct child.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-22 (session continuation from Plan 02)
- **Completed:** 2026-07-22
- **Tasks:** 2/2
- **Files:** 1 created (`tests/test_identity.py`), 1 modified (`yahir_reusable_bot/lifecycle/identity.py`)

## Accomplishments

- Wrote `tests/test_identity.py` — 7 module-level tests covering all four D-19-locked truth-table
  rows (the recycled-PID decoy, one-interpreter-flag daemon, plain `-m` form, argv0-basename
  form), plus the additive two-interpreter-flag row (a genuine live false negative outside the
  locked four), the pytest-nested-selector discriminator proving "first `-m` wins" is correct and
  not merely convenient, and the truncated-argv bounds-check degrade guard.
- Confirmed RED against pre-fix source by execution before committing: exactly 2 of 7 tests
  failed — `test_decoy_positional_marker_arg_does_not_match` and
  `test_two_interpreter_flags_before_module_switch_matches` — the other 5 passed by coincidence
  of the buggy slice window, exactly as the plan predicted.
- Committed the test file alone (`0f0a9ad`), then the `_argv_matches_marker` fix as its direct
  child (`5273c13`) — the RED-first git-ancestry proof Plan 04 will audit via merge-base check.
- All 7 new tests pass GREEN; full suite (23 tests) and the standing `GATE-01` import-hygiene gate
  (8 tests) stay green; `ruff check` scoped to both files touched by this plan reports only the
  already-logged pre-existing `identity.py:121` E731 (unrelated line, untouched by this fix).

## Verbatim RED Output (Task 1, before the fix commit)

```
$ uv run pytest tests/test_identity.py -v
============================= test session starts ==============================
platform linux -- Python 3.13.13, pytest-9.1.1, pluggy-1.6.0
...
collected 7 items

tests/test_identity.py::test_decoy_positional_marker_arg_does_not_match FAILED [ 14%]
tests/test_identity.py::test_interpreter_flag_before_module_switch_matches PASSED [ 28%]
tests/test_identity.py::test_two_interpreter_flags_before_module_switch_matches FAILED [ 42%]
tests/test_identity.py::test_plain_module_switch_form_matches PASSED     [ 57%]
tests/test_identity.py::test_argv0_basename_form_matches PASSED          [ 71%]
tests/test_identity.py::test_nested_selector_switch_does_not_match PASSED [ 85%]
tests/test_identity.py::test_trailing_module_switch_without_target_does_not_match PASSED [100%]

=================================== FAILURES ===================================
_______________ test_decoy_positional_marker_arg_does_not_match ________________

cmdline_bytes = <function cmdline_bytes.<locals>._build at 0x76b8af1a6340>

    def test_decoy_positional_marker_arg_does_not_match(cmdline_bytes):
        """argv ``python -m pytest <marker>``: the marker here is pytest's
        POSITIONAL test-selector argument, so the ``-m`` module target is
        ``pytest``, not the marker. A True here means the reload path can
        deliver SIGHUP to a completely unrelated process that merely recycled
        the PID and happens to be running pytest with the marker name as a
        test-selector argument. RED pre-fix — current code returns True."""
        cmdline = cmdline_bytes(b"python", b"-m", b"pytest", MARKER)
>       assert is_running_process(1, proc_marker=MARKER, cmdline_reader=lambda _: cmdline) is False
E       AssertionError: assert True is False
E        +  where True = is_running_process(1, proc_marker=b'examplebot', cmdline_reader=<function test_decoy_positional_marker_arg_does_not_match.<locals>.<lambda> at 0x76b8af1a6480>)

tests/test_identity.py:39: AssertionError
___________ test_two_interpreter_flags_before_module_switch_matches ____________

cmdline_bytes = <function cmdline_bytes.<locals>._build at 0x76b8af1c2ca0>

    def test_two_interpreter_flags_before_module_switch_matches(cmdline_bytes):
        """argv ``python -O -B -m <marker> run``: TWO interpreter flags push
        ``-m`` past the buggy window entirely. RED pre-fix — current code
        returns False, a genuine live false negative (the daemon is reported
        not-running). This row is NOT one of the four ROADMAP-locked D-19
        criteria; it is included deliberately because RESEARCH.md reproduced it
        against real source, it costs four lines to fix via the D-04 first-``-m``
        scan, and it is one of only two rows that make this file RED pre-fix."""
        cmdline = cmdline_bytes(b"python", b"-O", b"-B", b"-m", MARKER, b"run")
>       assert is_running_process(1, proc_marker=MARKER, cmdline_reader=lambda _: cmdline) is True
E       AssertionError: assert False is True
E        +  where False = is_running_process(1, proc_marker=b'examplebot', cmdline_reader=<function test_two_interpreter_flags_before_module_switch_matches.<locals>.<lambda> at 0x76b8af1c2c00>)

tests/test_identity.py:63: AssertionError
=========================== short test summary info ============================
FAILED tests/test_identity.py::test_decoy_positional_marker_arg_does_not_match
FAILED tests/test_identity.py::test_two_interpreter_flags_before_module_switch_matches
========================= 2 failed, 5 passed in 0.06s ==========================
```

This matches the plan's own prediction exactly: 2 of 7 tests RED pre-fix, both on the adversarial
rows named in the acceptance criteria — no collection or import error, and the other 5 pass by
coincidence of the buggy overlapping-slice window (not by design), as documented in each passing
test's own docstring.

## Task Commits

1. **Task 1: Write tests/test_identity.py and commit it RED, alone** — `0f0a9ad` (test)
   — touches exactly `tests/test_identity.py`
2. **Task 2: Fix _argv_matches_marker with the first-module-switch scan (D-04/D-06) and commit
   it GREEN** — `5273c13` (fix)
   — touches exactly `yahir_reusable_bot/lifecycle/identity.py`, and is the direct child of
   `0f0a9ad`

## Files Created/Modified

- `tests/test_identity.py` — New. 7 module-level test functions per D-11 house style
  (docstring-first, no mocking library, synthetic inline doubles): all four D-19-locked truth-table
  rows, the additive two-interpreter-flag row, the first-`-m`-wins discriminator, and the
  truncated-argv bounds-check guard. Every assertion drives the public `is_running_process` seam
  with an injected `cmdline_reader=`, never the private `_argv_matches_marker` in isolation. Uses
  the neutral placeholder marker `b"examplebot"` — no consumer's real marker.
- `yahir_reusable_bot/lifecycle/identity.py` — `_argv_matches_marker`'s final return replaced with
  a first-`-m`-wins scan: iterate argv from index 1, find the lowest index where the token equals
  `b"-m"`, return whether a following token exists and equals `proc_marker` exactly (bounds check
  + exact-equality adjacency), return False immediately if no `-m` is found. The docstring is
  extended with the D-06 rule statement, the D-05 rejected-fixed-position rationale, the D-07
  rejected-argv0-interpreter-check rationale, and the degrade-never-raise contract. The
  `cmdline.split(b"\x00")` parse, empty-argv guard, and argv0-basename branch are byte-identical —
  confirmed via `git diff HEAD~1 HEAD` showing no modification to the `prog ==` comparison line.

## Decisions Made

- Followed D-04's exact scan shape — lowest-index `-m`, bounds-checked adjacency, no continued
  scanning past the first match.
- Followed D-06: stated the first-`-m`-wins rule as THE rule in the docstring, with the
  `python -m pytest -m <marker>` case as the concrete illustration of why it is correct rather
  than convenient.
- Followed D-05 and D-07: both rejected alternatives (fixed-position check; requiring argv0 to
  look like a Python interpreter) are documented in the docstring as explicitly rejected, with the
  concrete failure mode each would have introduced.
- Included the two-interpreter-flag test as additive coverage beyond the four ROADMAP-locked rows,
  per the plan's explicit instruction — it is one of the two rows that make the file RED and closes
  a real, reproducible false negative.
- Two commits, in order, unamended, per D-13 — verified explicitly after each commit via
  `git show --name-only --format=`.

## Unresolved Edge-Probe Item (carried forward per plan instruction — restated, not resolved)

The plan's own `<threat_model>` section flags one unresolved item from the deterministic edge
probe: **LIFE-01 — category `unclassified`, probe: "unclassified — review manually", status
`unresolved`.** This plan does not resolve it — restating it here so it survives into phase
verification, per the plan's `<output>` instruction and per the no-silent-drop rule (an
unclassified probe row is never auto-resolved and never auto-dismissed).

What this plan covers, in full: the four D-19-locked truth-table rows, both adversarial cases (the
positional-arg decoy and the flag-before-`-m` daemon), the first-`-m`-wins discriminator row, and
the malformed-input degrade path. What remains genuinely uncovered, per the plan's own accounting:
any non-Linux `/proc`-absent behavior (LIFE-03, explicitly Phase 3, not folded in here) and any
concurrent-signal race between this guard returning `True` and the consumer actually sending the
signal — that race lives entirely in consumer-side code (WeatherBot's reload sender), outside this
hub repo's Architectural Responsibility Map, and no test in this repo can assert it without
replicating consumer logic here (which D-18's reasoning, applied by analogy, also rejects).

## Deviations from Plan

### Auto-fixed Issues

None — Rules 1-3 were not triggered. No bugs, missing critical functionality, or blocking issues
were found.

### Deferred (Rule 3 scope boundary — logged, not fixed; appended to existing entry, not duplicated)

**`uv run ruff check` (repo-wide) still reports the same 4 pre-existing errors** already logged in
`.planning/phases/01-reachable-reliability/deferred-items.md` by Plan 02, one of which
(`yahir_reusable_bot/lifecycle/identity.py:121`, E731 lambda assignment) is in a file this plan
modifies. Confirmed the line is untouched by this plan's fix (`git diff HEAD~1 HEAD --
yahir_reusable_bot/lifecycle/identity.py` shows no change to line 121 — the edit is confined to
`_argv_matches_marker`'s docstring and final return, well below line 121). `uv run ruff check`
scoped to this plan's two files (`tests/test_identity.py`,
`yahir_reusable_bot/lifecycle/identity.py`) reports exactly this one pre-existing error and
nothing new. An append-only note was added to `deferred-items.md` recording this confirmation
without re-logging the finding, per the file-read instruction to append rather than duplicate.

---

**Total deviations:** 0 auto-fixed; 1 deferred-item append (pre-existing repo-wide ruff error,
confirmed unrelated and untouched, logged as an append to the existing Plan 02 entry)

## Issues Encountered

None. RED-first execution matched the plan's own prediction exactly on both the failure count and
the specific rows that failed.

**Requirements traceability:** `LIFE-01` is marked complete by this plan — the fix actually lands
green (all 7 regression tests pass, full suite green at 23 tests, import-hygiene gate green).
`GATE-01` is NOT marked complete here; it is milestone-level and spans all 4 phases, per Plan 01's
and Plan 02's own traceability notes, which this plan follows.

## User Setup Required

None — no external service configuration required. The fix itself is autonomous; only the
eventual tag cut / repin / deploy (Plan 04, human-gated per `ECOSYSTEM.md` §3) requires human
confirmation, and that is out of this plan's scope.

## Next Phase Readiness

- `_argv_matches_marker` implements D-04/D-05/D-06/D-07 fully; `tests/test_identity.py` is the
  standing regression suite for LIFE-01.
- Git history is clean two-commit RED-first evidence (`0f0a9ad` → `5273c13`), ready for Plan 04's
  merge-base audit alongside Plan 02's own two-commit pair (`e7c959d` → `f6e4fb2`).
- Both hub defects targeted by this phase (RELY-01, LIFE-01) are now fixed and green. No blockers
  for Plan 04 (the human-gated tag/repin/deploy close-out).
- The unresolved edge-probe item (concurrent-signal race, consumer-side) is carried forward to
  phase verification per the section above — not a blocker for Plan 04, but should not be silently
  dropped from the phase's final accounting.

---
*Phase: 01-reachable-reliability*
*Completed: 2026-07-22*

## Self-Check: PASSED

- FOUND: tests/test_identity.py
- FOUND: yahir_reusable_bot/lifecycle/identity.py
- FOUND: .planning/phases/01-reachable-reliability/01-03-SUMMARY.md
- FOUND: 0f0a9ad (git log --oneline --all)
- FOUND: 5273c13 (git log --oneline --all)
