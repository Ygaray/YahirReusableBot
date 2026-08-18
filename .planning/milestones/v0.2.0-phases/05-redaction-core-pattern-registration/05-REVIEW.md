---
phase: 05-redaction-core-pattern-registration
reviewed: 2026-07-29T18:45:52Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - yahir_reusable_bot/redact/__init__.py
  - yahir_reusable_bot/redact/core.py
  - yahir_reusable_bot/redact/registry.py
  - tests/test_redact_core.py
  - tests/test_redact_registry.py
  - tests/test_import_hygiene.py
findings:
  critical: 1
  warning: 2
  info: 0
  total: 3
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-07-29T18:45:52Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the new `redact/` subpackage (`core.py`, `registry.py`, `__init__.py`) and its
test suite plus the additive `test_import_hygiene.py` change. Pure-leaf discipline, the
"no domain nouns" naming rule, and the source-eliding `__repr__`/index-only error message
convention are all correctly implemented for the paths they were designed for. `ruff`/full
suite passing is not evidence these paths are correct, and one of them — the escalating
ReDoS wall-clock ladder that is this phase's core security control — has a genuine,
empirically-demonstrated termination gap: a class of real-world catastrophic pattern can
slip past both the structural check and the entire fine-grained ladder, then hang
indefinitely on a single coarse-tier probe, which is exactly the failure mode the design
exists to prevent. The test suite does not catch this because the one test whose docstring
claims to pin the termination guarantee never actually exercises the ladder at all (a
short-circuit issue). Two secondary issues (a false "never raises" contract, and a
secret-leak path around the `__repr__` override) are documented below as warnings.

## Critical Issues

### CR-01: `register_patterns`'s escalating ReDoS ladder is not actually bounded — a single `search()` call can hang indefinitely

**File:** `yahir_reusable_bot/redact/registry.py:39-97` (structural pre-check, ladder constant, `_blows_budget`), interacting with the short-circuit at `registry.py:127`; misleading test at `tests/test_redact_registry.py:98-108`

**Issue:**

The module's entire safety argument (module docstring, `registry.py:1-23`, and the
`_blows_budget` docstring, `registry.py:75-97`) rests on the claim that the ladder's small
step size bounds the overshoot past the budget, so a catastrophic pattern is always caught
"at a small rung instead of at one huge probe." That claim is true for the **fine tier**
(`8,10,...,24`, a `+2` step each time), but the **coarse tier** jumps from `24` straight to
`100`, then `400`, `1600`, `4000` — an absolute jump of `76` at the fine→coarse boundary
alone. For an exponential-time pattern whose growth-rate constant happens to be small enough
that cumulative elapsed time is still under the `0.3s` budget at rung `24`, the next single
`pattern.search()` call (at count `100`) is not "a small rung" at all — it is a jump large
enough to make an exponential-time search run for an effectively unbounded amount of wall-clock
time, with no way to interrupt it (`re.Pattern.search` is uninterruptible, as the module's own
docstring elsewhere correctly notes).

This is not a theoretical concern — it is empirically demonstrated:

1. `RedactionPattern(pattern=re.compile(r"(a|aa)+$"), replacement="***")` is a real,
   well-known "Fibonacci-style" catastrophic-backtracking shape.
2. `_looks_pathological` does **not** flag it — its regex source has no substring inside a
   group that also carries a nested quantifier (verified: `_NESTED_QUANTIFIER_RX.search(...)`
   returns `None` for this pattern), so vetting falls through entirely to `_blows_budget`.
3. Measured single-`search()` times for this pattern against the `"a"` corpus shape (the
   first shape tried at every rung):

   | count (n) | elapsed (s) |
   |---|---|
   | 24 | 0.025 |
   | 26 | 0.052 |
   | 28 | 0.151 |
   | 30 | 0.397 |

   Cumulative elapsed time through the *entire fine tier* (all rungs `8..24`, all 3 corpus
   shapes) stays comfortably under `0.3s` (well under `0.05s` cumulative in fact) — the fine
   tier never fires the budget check. The very next rung tried is `100`.
4. A follow-up timed run (`n = 32, 34, 36, 38, 40`, 25s timeout) never even completed the
   loop — confirming the growth is already well past any reasonable wall-clock budget by
   `n≈32-40`, decades before the ladder's `n=100` rung. A single `search()` call at `n=100`
   for this pattern would run for a length of time with no practical upper bound —
   `register_patterns` would simply never return.

The test suite gives false confidence here. `test_register_patterns_vetting_terminates_in_bounded_time`
(`tests/test_redact_registry.py:98-108`) claims in its docstring to "pin the termination
correction (T-05-06)," using `_nested_quantifier_pattern()` (`(a+)+$`). But that pattern
**is** caught by `_looks_pathological` (its own preceding test,
`test_register_patterns_rejects_catastrophic_pattern`, asserts
`_looks_pathological(rp.pattern) is True`). Because `register_patterns` evaluates
`if _looks_pathological(rp.pattern) or _blows_budget(rp.pattern):` with Python's short-circuit
`or` (`registry.py:127`), `_blows_budget` — the ladder logic the test's docstring claims to
verify — is **never called** in this test. The only test that genuinely exercises
`_blows_budget` alone is `test_register_patterns_rejects_catastrophic_pattern_the_structural_check_misses`,
which uses `(a|a)*$` — a shape whose backtracking blowup is fast enough to trip the budget
check while still inside the fine tier (measured: already over budget by n≈20-22), so it
never reaches the coarse tier either. **No test in the suite exercises the fine→coarse
transition or proves the coarse tier is actually bounded**, and the one that claims to does
not run the code path it claims to verify.

**Fix:**

Two independent problems need fixing:

1. **The ladder itself.** Replace the coarse tier's large absolute jumps with a step size
   that preserves the same bounded-multiplicative-growth property the fine tier already has
   (e.g. continue the same small ratio throughout, or explicitly cap the maximum single-probe
   size/time by checking elapsed *before* committing to the next rung and refusing to jump by
   more than a small constant factor):

   ```python
   # Instead of a hardcoded absolute-count ladder with a large coarse jump:
   _REDOS_LADDER: tuple[int, ...] = (8, 10, 12, 14, 16, 18, 20, 22, 24, 100, 400, 1600, 4000)

   # Prefer a ladder whose ratio between consecutive rungs never exceeds the fine tier's own
   # bound (~1.2x absolute / ~4x per two steps), all the way through — e.g. geometric doubling
   # from a higher floor, or simply keep the +2 cadence out further before switching tiers:
   _REDOS_LADDER: tuple[int, ...] = tuple(range(8, 41, 2)) + (48, 64, 96, 144, 216, 324)
   ```

   Whatever replacement shape is chosen, add an assertion (as a module-level test or a
   startup self-check) that verifies no two consecutive rungs differ by more than the
   documented bound, so a future edit to the constant can't silently reintroduce the gap.

2. **The test.** Add a regression test that actually exercises `_blows_budget` against a
   pattern the structural check misses AND whose blowup is slow enough to survive the fine
   tier (e.g. `(a|aa)+$` at a bounded, sub-budget count first, to confirm the design change
   in (1) catches it before the coarse tier can hang):

   ```python
   def test_register_patterns_catches_slow_ramping_pattern_before_coarse_tier_hangs():
       """A Fibonacci-style catastrophic pattern that the structural check misses AND
       whose backtracking blowup is too slow to trip the fine tier must still be caught
       — proving the fine-to-coarse transition (not just the fine tier alone) is bounded."""
       rp = RedactionPattern(pattern=re.compile(r"(a|aa)+$"), replacement="***")
       assert _looks_pathological(rp.pattern) is False
       start = time.perf_counter()
       with pytest.raises(ValueError):
           register_patterns([rp])
       assert time.perf_counter() - start < 5.0
   ```

   Also correct or remove the misleading docstring claim in
   `test_register_patterns_vetting_terminates_in_bounded_time` — as written today it verifies
   only the structural-check fast path, not the ladder's termination behavior it claims to pin.

## Warnings

### WR-01: `redact_secrets`'s "never raises" contract is false for a malformed `replacement` template

**File:** `yahir_reusable_bot/redact/core.py:117` (docstring claim), `yahir_reusable_bot/redact/core.py:136-140` (implementation), `yahir_reusable_bot/redact/registry.py:100-149` (no validation of this at registration)

**Issue:** The `redact_secrets` docstring states unconditionally: "This function never
raises." That is false whenever a `RedactionPattern.replacement` references a capture group
that does not exist in `pattern` — `re.Pattern.sub()` raises `re.error` in that case:

```
>>> re.compile(r"(a)").sub(r"\2", "a")
re.error: invalid group reference 2 at position 1
```

`register_patterns` (the module's own registration-time vetting gate, whose entire premise
is "surface a consumer wiring bug at build time, because there is no runtime rescue once this
pattern reaches a hot log call site") only vets ReDoS risk (structural + timing). It performs
no validation that `replacement`'s backreferences are well-formed against `pattern`'s actual
group count. A consumer's malformed pattern — a typo'd backreference index, or a named-group
reference to a group that doesn't exist — sails through registration silently and then raises
for the first time deep inside `redact_secrets`, at exactly the hot-path log call site this
module exists to protect (the same failure mode REDACT-03/the ReDoS vetting was built to
avoid, just for a different malformed-pattern class).

**Fix:** Either (a) narrow the docstring's claim to explicitly exclude a malformed
`replacement` template ("never raises for a well-formed pattern/replacement pair — an
out-of-range backreference is a consumer wiring bug caught at registration, not here"), or
(b), consistent with the module's own "fail loud at registration" philosophy, have
`register_patterns` proactively catch this by test-substituting each pattern against a
trivial matching probe inside a `try/except re.error` and re-raising as the same
registration-time `ValueError` used for ReDoS rejections:

```python
try:
    rp.pattern.sub(rp.replacement, "")
except re.error as exc:
    raise ValueError(
        f"RedactionPattern at index {index} rejected at registration — its "
        f"replacement template is malformed: {exc}"
    ) from exc
```

### WR-02: `RedactionPattern`'s source-eliding `__repr__` does not cover `dataclasses.asdict`/`vars()` access

**File:** `yahir_reusable_bot/redact/core.py:83-101` (the `__repr__` override); no coverage in `tests/test_redact_core.py:224-234`

**Issue:** The custom `__repr__` correctly blocks a secret leaking through `repr(rp)`,
`str(rp)`, and `f"{rp!r}"` (all three are tested at `tests/test_redact_core.py:230-233`). But
it only overrides the `RedactionPattern` object's own representation — it does nothing about
`dataclasses.asdict(rp)`, `dataclasses.astuple(rp)`, `vars(rp)`, or `rp.__dict__`, all of
which return/expose the **raw** `pattern` field (the underlying `re.Pattern` object, unwrapped
from `RedactionPattern`). That raw `re.Pattern` object carries Python's own default `repr`,
e.g. `re.compile('SENTINELKEY_do_not_leak_123')` — the exact plaintext secret the whole
module exists to keep out of logs. A consumer who does the very natural-looking
`logger.info("registered pattern: %s", dataclasses.asdict(pattern))`, or simply
`print(vars(rp))` while debugging, reintroduces the leak the `__repr__` override was built to
close, with no test or documentation flagging this as unsafe.

**Fix:** Since hiding the `pattern` field entirely isn't viable (`redact_secrets` needs
`rp.pattern.sub(...)` on the live compiled object), document the danger explicitly in the
class docstring next to the existing `__repr__` rationale — e.g. "`dataclasses.asdict()`/
`vars()`/`__dict__` bypass this elision entirely and expose the raw compiled pattern (and
therefore its secret source, for a `literal()`-built entry) via `re.Pattern`'s own default
`repr` — never pass this object's raw fields to a serializer or logger; only `repr(rp)`/
`str(rp)` are safe." Optionally add a regression test asserting this is indeed the current
(dangerous) behavior, so a future change that tries to "fix" it doesn't silently break the
`redact_secrets` call path that depends on the raw field being reachable.

---

_Reviewed: 2026-07-29T18:45:52Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
