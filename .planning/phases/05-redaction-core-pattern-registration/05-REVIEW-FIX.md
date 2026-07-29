---
phase: 05-redaction-core-pattern-registration
fixed_at: 2026-07-29T18:56:23Z
review_path: .planning/phases/05-redaction-core-pattern-registration/05-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 5: Code Review Fix Report

**Fixed at:** 2026-07-29T18:56:23Z
**Source review:** .planning/phases/05-redaction-core-pattern-registration/05-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### CR-01: `register_patterns`'s escalating ReDoS ladder is not actually bounded — a single `search()` call can hang indefinitely

**Files modified:** `yahir_reusable_bot/redact/registry.py`, `tests/test_redact_registry.py`
**Commit:** `047431e`
**Status:** fixed: requires human verification

**Applied fix:** The orchestrator independently reproduced this hang before dispatch
(`(a|aa)+$` blows past the fine tier and hits the un-interruptible 24 -> 100 jump).
Replaced the ladder's hardcoded fine/coarse two-tier shape
(`8,10,...,24, 100, 400, 1600, 4000`) with a single continuous ladder whose growth
ratio never exceeds a documented bound end-to-end:
`tuple(range(8, 41, 2)) + (48, 64, 96, 144, 216, 324)` (max observed ratio ~1.5x,
capped at `_REDOS_LADDER_MAX_RATIO = 2.0`). Added
`_validate_ladder_growth_bound()`, a plain function (not a bare `assert`, so it
survives `-O`) called once at import time, that raises `AssertionError` if any two
consecutive rungs ever exceed the ratio cap again — this is the "startup
self-check" the review's Fix section called for, so a future edit can't silently
reintroduce the 24->100-style gap. Updated the `_blows_budget` docstring and the
ladder's module-level comment to state the corrected termination argument (the
whole ladder is bounded, not just an early subset).

Empirically re-verified against the orchestrator's exact repro pattern
(`re.compile(r"(a|aa)+$")`): with the new ladder, `_blows_budget` now returns
`True` at rung 30, total cumulative elapsed ~0.64s, largest single probe ~0.4s —
no unbounded jump, no hang.

Test changes: corrected the misleading docstring on
`test_register_patterns_vetting_terminates_in_bounded_time` (it only exercises the
structural short-circuit, per the review's finding, since Python's `or` never
evaluates `_blows_budget` once `_looks_pathological` is `True`) and added
`test_register_patterns_catches_slow_ramping_pattern_before_coarse_tier_hangs`,
which builds the `(a|aa)+$` pattern, asserts `_looks_pathological(...) is False`
(confirming the structural check misses it), and asserts a `< 5.0`s wall-clock
ceiling around the `register_patterns` call. **Verified RED-first**: this exact
test, run against the pre-fix `registry.py` under a 12s `timeout`, was killed
(exit code 124) — it genuinely hangs against the old ladder, confirmed empirically
in this session before the fix was reapplied.

Flagged `requires human verification` per this agent's operating rules for
logic-classified fixes: the new ladder shape and ratio bound (`2.0`) are a design
choice within the budget/ladder/corpus internals the phase's constraints leave
tunable, and while empirically re-verified against the reported repro pattern and
the full test suite, the correctness of the chosen ratio bound as a *general*
guarantee (not just for this one repro) is a judgment call worth a human's
confirmation.

### WR-01: `redact_secrets`'s "never raises" contract is false for a malformed `replacement` template

**Files modified:** `yahir_reusable_bot/redact/registry.py`, `yahir_reusable_bot/redact/core.py`, `tests/test_redact_registry.py`
**Commit:** `124df2e`
**Status:** fixed

**Applied fix:** Per the phase's project constraints (option (b), consistent with
the module's fail-loud-at-registration posture — constraints explicitly ruled out
adding try/except in the `redact_secrets` hot path), added registration-time
validation in `register_patterns`: for every entry (regardless of
`skip_redos_check`, since this is an independent concern from ReDoS vetting),
`rp.pattern.sub(rp.replacement, "")` is called inside a `try/except re.error`.
Verified empirically that `re.Pattern.sub` validates a replacement template's
backreferences eagerly at template-compile time, before attempting any match — so
an empty probe string is sufficient to catch a malformed template even when it
would never match. On failure, raises the same registration-time `ValueError`
convention used elsewhere in this module, naming the entry by INDEX only (never
echoing `rp.pattern.pattern`, preserving the source-eliding convention project
constraint #5 requires). Also narrowed `redact_secrets`'s docstring claim from an
unconditional "never raises" to "never raises for a well-formed pattern/replacement
pair," documenting that a hand-built, unregistered, malformed pattern is out of
this function's contract and can still raise `re.error` — `register_patterns` is
what guarantees well-formedness for any pattern that reached it via that path.

Added `test_register_patterns_rejects_malformed_replacement_template` (asserts
rejection both with and without `skip_redos_check=True`, proving the check is
independent of ReDoS vetting) and
`test_register_patterns_accepts_well_formed_backreference_replacement` (no
false-reject companion). **Verified RED-first**: run against the pre-fix
`registry.py` in this session, the malformed-template test failed cleanly with
`Failed: DID NOT RAISE ValueError` (not a hang) — confirming genuine RED before
the fix landed.

### WR-02: `RedactionPattern`'s source-eliding `__repr__` does not cover `dataclasses.asdict`/`vars()` access

**Files modified:** `yahir_reusable_bot/redact/core.py`, `tests/test_redact_core.py`
**Commit:** `1212d07`
**Status:** fixed

**Applied fix:** Per the review's Fix section (hiding the raw `pattern` field
entirely isn't viable — `redact_secrets` needs the live compiled object for
`rp.pattern.sub(...)`), documented the danger explicitly in the `__repr__` method's
docstring: `dataclasses.asdict()`/`astuple()`/`vars()`/`__dict__` all bypass the
elision and expose the raw compiled `re.Pattern`, which carries Python's own
default `repr` and so still prints a `literal()`-built entry's secret source
verbatim. States plainly that only `repr(rp)`/`str(rp)` are safe; raw fields must
never be passed to a serializer or logger. Added
`test_redaction_pattern_asdict_and_vars_still_expose_raw_pattern_source`, a
tripwire test (not a fix to the underlying behavior, per the review's own framing
— this is intentionally left as-is because closing it would break the
`redact_secrets` call path) that pins today's known-dangerous behavior across all
three access paths (`asdict`, `vars`, `__dict__`), so a future change that tries to
"fix" this without understanding the tradeoff breaks a test instead of silently
reintroducing an untested regression either way.

---

_Fixed: 2026-07-29T18:56:23Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
