---
phase: 01-reachable-reliability
fixed_at: 2026-07-22T23:23:15Z
review_path: .planning/phases/01-reachable-reliability/01-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: partial
---

# Phase 01: Code Review Fix Report

**Fixed at:** 2026-07-22T23:23:15Z
**Source review:** .planning/phases/01-reachable-reliability/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (fix_scope: all — Critical + Warning + Info)
- Fixed: 3 (all documentation-only; one, WR-01, deliberately fixed only its
  documentation half — see note below)
- Skipped: 0

`status` was `partial` at the original review-fix run because WR-01's finding
described two possible remedies (extend the scan's behavior, OR document the
gap as an explicit known limitation) and that run applied only the
documentation half per an explicit scoping instruction — the behavioral
question (whether to also match the attached `-mmodule` form) was carried
back to the human, unresolved, rather than auto-decided there.

**WR-01 behavioral half — RESOLVED 2026-07-27 (option a, human-chosen).**
The scan now recognizes the attached `-m<module>` form. Applied RED-first
(this repo's D-13 discipline) as a two-commit pair on `main`, direct
child-of-parent:
- `f9e614a` test(01): RED — `test_attached_module_switch_form_matches`,
  `test_attached_module_switch_with_leading_flag_matches`, and
  `test_attached_first_m_wins_over_nested_selector` (the last also RED because
  the old scan had a false POSITIVE on `python -mpytest -m <marker>`, matching
  pytest's own `-m` selector), plus `test_bundled_short_option_group_not_matched`
  as a GREEN boundary guard.
- fix commit (below): a two-line loop addition recognizing a token whose first
  two bytes are `-m`; module target is that token's remainder. Full suite
  27 passed, import-hygiene 8 passed.

A NEW decision D-20 was recorded (in the `identity.py` docstring alongside
D-04..D-07): the scan matches only a token whose first two bytes are `-m`.
Bundled short-option groups where `-m` is not first (`python -Omexamplebot`,
`python -Imjson.tool` — both valid CPython, verified) remain a deliberate
residual false negative, because decoding Python's full short-option-bundling
grammar risks a false POSITIVE (SIGHUP to the wrong PID), the strictly worse
failure for a PID-recycling guard. `status` for WR-01 is now `all_fixed`.

## Fixed Issues

### WR-01: `-m` scan doesn't handle Python's attached `-mmodule` form; D-06's "mirrors Python's CLI grammar" claim is incomplete

**Files modified:** `yahir_reusable_bot/lifecycle/identity.py`
**Commit:** `0296c17`
**Applied fix:** Documentation-only, per explicit scope ruling — behavior of
`_argv_matches_marker` was NOT changed (`git diff` on this file touches only
docstring lines; verified before commit).

- Softened the overstated claim "This mirrors Python's own CLI grammar" to
  "This handles the space-separated `-m <module>` form of Python's CLI
  grammar" — accurate to what the scan actually does.
- Added a new "KNOWN LIMITATION" paragraph, in the same style as the
  existing D-05/D-07 rejected-alternative notes, recording: CPython also
  accepts the attached `-mmodule` form (verified: `python3 -mjson.tool`);
  the scan does not match it because it only matches a standalone `b"-m"`
  token; this causes a false negative (a live daemon launched with the
  attached form is reported as not-running); this is an inherited
  pre-existing gap, not a regression from this fix's diff (the prior
  fixed-position check had the identical blind spot); and, unlike D-05/D-07,
  there is no recorded decision rejecting the attached form as out of
  scope — it is a tracked gap, not a deliberate exclusion.

**Deliberately NOT applied — carried back to the human:** The finding's Fix
section offered two remedies: (a) extend the scan to also match the attached
`b"-m" + proc_marker` token, or (b) document the gap as an explicit rejected
alternative if it's deliberately out of scope. Per this run's scope ruling,
only the documentation was written (option (b)'s form, but without asserting
it is deliberately rejected — the note is framed as an open, undecided gap,
not a closed decision). Whether to also fix the *behavior* (option (a)) is
explicitly reserved for the human: this finding's originating fix was
previously reviewed and authorized diff-by-diff before merging to `main`,
and silently broadening what it matches now, without that same review, would
undercut that authorization. **Action needed from the human:** decide
whether to (a) extend `_argv_matches_marker` to also match the attached
`-m<module>` form, closing the false negative, or (b) formally accept it as
a permanent, recorded non-goal (which would then warrant demoting this
paragraph from "KNOWN LIMITATION" to a D-numbered rejected-alternative entry
alongside D-05/D-07, plus the regression test the review's Fix section
sketched).

### WR-02: `test_classification_is_pure_and_repeatable` is unlabeled in the self-proof convention the rest of the file follows

**Files modified:** `tests/test_retry.py`
**Commit:** `76db2a7`
**Applied fix:** Added the missing RED/GREEN self-proof annotation to the
test's docstring, matching the exact phrasing style of its sibling
`test_classification_includes_remote_protocol_error`: "RED pre-fix — pre-fix
`is_transient(RemoteProtocolError)` returns `False` for every call, failing
this assertion; this also guards that a future refactor doesn't introduce
per-call nondeterminism (e.g. caching keyed on identity) into the
classifier." No test logic or assertions changed.

### IN-01: Stale cross-file line citation in `conftest.py`

**Files modified:** `tests/conftest.py`
**Commit:** `3052199`
**Applied fix:** Independently re-verified the correct line before editing
(per the scope ruling, rather than trusting either number in the review):
`grep -n "sleep=stop_event.wait" yahir_reusable_bot/reliability/retry.py`
confirms the wiring is at line 265 in the current file (both the review's
"241" and its proposed "265" needed independent confirmation — 265 is
correct). Updated the `_InstantStopEvent` docstring's cross-file citation
from `retry.py:241` to `retry.py:265`. Pure documentation; no code changed.

## Skipped Issues

None — all three in-scope findings were fixed (with WR-01's behavioral half
deliberately out of scope for this run, as detailed above, per explicit
instruction rather than a verification failure).

---

_Fixed: 2026-07-22T23:23:15Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
