"""Regression tests for REDACT-02 (frozen, pure, order-preserving registration) and
REDACT-03 (registration-time ReDoS vetting) — ``yahir_reusable_bot.redact.registry``.

Every assertion below is genuinely RED before this plan's fix lands: the module under
test, ``yahir_reusable_bot.redact.registry``, does not exist yet, so collection itself
fails with ``ModuleNotFoundError`` before a single test body runs. This mirrors the
RED-first two-commit discipline ``tests/test_registry.py`` and ``tests/test_redact_core.py``
already established (module-docstring convention: name the requirement IDs, state why
the assertions are genuinely red pre-fix, no mocking library, plain construction).

Imports the private probe helpers (``_looks_pathological``, ``_blows_budget``) and the
``_REDOS_BUDGET_S`` constant directly, not just the public ``register_patterns`` entry
point: several tests must attribute a rejection to the STRUCTURAL check specifically, or
prove the TIMING probe is independently load-bearing when the structural check does NOT
flag a pattern — that attribution is impossible through the public entry point alone
(Pitfall 5, assumption A2).
"""

from __future__ import annotations

import re
import time

import pytest

from yahir_reusable_bot.redact.core import RedactionPattern, redact_secrets
from yahir_reusable_bot.redact.registry import (
    _REDOS_BUDGET_S,
    _looks_pathological,
    register_patterns,
)


def _nested_quantifier_pattern() -> RedactionPattern:
    """A textbook nested-quantifier shape — a group containing a quantifier, itself
    quantified — the cheap structural pass exists to catch (T-05-01)."""
    return RedactionPattern(pattern=re.compile(r"(a+)+$"), replacement="***")


def _overlapping_alternation_pattern() -> RedactionPattern:
    """A redundant-alternation shape with NO nested-quantifier substring — the
    structural heuristic must NOT flag it, so only the wall-clock timing probe can
    catch it (Pitfall 5, assumption A2)."""
    return RedactionPattern(pattern=re.compile(r"(a|a)*$"), replacement="***")


def _fibonacci_style_pattern() -> RedactionPattern:
    """A Fibonacci-style overlapping-alternation shape — no nested-quantifier
    substring, so the structural pass cannot see it, AND a backtracking blowup slow
    enough to survive well past the ladder's original fine-tier tail (CR-01 / T-05-06).
    This is the exact shape that exposed the fine-to-coarse termination gap: pre-fix,
    the next ladder rung after the fine tier's tail jumped straight from 24 to 100,
    and a single `search()` call at that rung against this pattern would run for an
    effectively unbounded amount of wall-clock time."""
    return RedactionPattern(pattern=re.compile(r"(a|aa)+$"), replacement="***")


def _proven_boundary_pattern() -> RedactionPattern:
    """The proven boundary pattern ported verbatim (as a string literal only — no
    identifier in this module carries the originating app's domain noun) from the
    app-local scrubber this phase generalizes: a capture group plus a negated
    character class stopping at the first delimiter, paired with a backreference
    replacement template. Must never be false-rejected (assumption A1)."""
    return RedactionPattern(
        pattern=re.compile(r"(appid=)[^&\s\"'<>\\]+", re.IGNORECASE),
        replacement=r"\1***",
    )


def test_register_patterns_rejects_catastrophic_pattern():
    """T-05-01: a nested-quantifier pattern is caught by the structural pass AND
    rejected end-to-end by ``register_patterns``."""
    rp = _nested_quantifier_pattern()
    assert _looks_pathological(rp.pattern) is True
    with pytest.raises(ValueError):
        register_patterns([rp])


def test_register_patterns_rejects_catastrophic_pattern_the_structural_check_misses():
    """Pitfall 5 / assumption A2: an alternation shape the structural heuristic does
    NOT flag is still rejected — proving the timing probe is independently
    load-bearing, not redundant with the structural check."""
    rp = _overlapping_alternation_pattern()
    assert _looks_pathological(rp.pattern) is False
    with pytest.raises(ValueError):
        register_patterns([rp])


def test_register_patterns_accepts_proven_boundary_pattern():
    """Assumption A1: no false-reject. The proven boundary pattern registers without
    raising and comes back unchanged in the returned tuple."""
    rp = _proven_boundary_pattern()
    result = register_patterns([rp])
    assert result == (rp,)


def test_register_patterns_vetting_stays_far_under_budget():
    """Assumption A4, settled by measurement not estimate: the full registration
    call for the proven boundary pattern completes in well under a tenth of the
    configured ReDoS budget, read from the module constant (never a hard-coded
    duplicate of it)."""
    rp = _proven_boundary_pattern()
    start = time.perf_counter()
    register_patterns([rp])
    elapsed = time.perf_counter() - start
    assert elapsed <= _REDOS_BUDGET_S / 10


def test_register_patterns_vetting_terminates_in_bounded_time():
    """This pins only the STRUCTURAL short-circuit's own speed: `_nested_quantifier_pattern()`
    is caught by `_looks_pathological`, and Python's `or` in `register_patterns` never
    evaluates `_blows_budget` once the left operand is True — so this test does NOT
    exercise the ladder's own termination behavior (CR-01 correction to this
    docstring's prior, misleading claim). The ladder's fine-to-coarse termination
    property is pinned separately by
    `test_register_patterns_catches_slow_ramping_pattern_before_coarse_tier_hangs`
    below, using a pattern the structural check cannot see."""
    rp = _nested_quantifier_pattern()
    assert _looks_pathological(rp.pattern) is True
    start = time.perf_counter()
    with pytest.raises(ValueError):
        register_patterns([rp])
    elapsed = time.perf_counter() - start
    assert elapsed < 5.0


def test_register_patterns_catches_slow_ramping_pattern_before_coarse_tier_hangs():
    """CR-01 / T-05-06: a Fibonacci-style catastrophic pattern that the structural
    check misses AND whose backtracking blowup is too slow to trip the budget within
    the ladder's original fine tier must still be caught — proving the fine-to-coarse
    transition itself (not just the fine tier in isolation) is bounded. Pre-fix, the
    next rung past the fine tier's tail jumped straight to 100 and this call would
    never return; the wall-clock ceiling below re-fails this test if that termination
    gap is ever reintroduced."""
    rp = _fibonacci_style_pattern()
    assert _looks_pathological(rp.pattern) is False
    start = time.perf_counter()
    with pytest.raises(ValueError):
        register_patterns([rp])
    elapsed = time.perf_counter() - start
    assert elapsed < 5.0


def test_register_patterns_honors_skip_redos_check():
    """D-50: the per-pattern opt-out genuinely bypasses BOTH checks — a pattern
    rejected without the flag is accepted with it, proving it is load-bearing and
    not a no-op."""
    base = _nested_quantifier_pattern()
    with pytest.raises(ValueError):
        register_patterns([base])
    opted_out = RedactionPattern(
        pattern=base.pattern,
        replacement=base.replacement,
        skip_redos_check=True,
    )
    result = register_patterns([opted_out])
    assert result == (opted_out,)


def test_register_patterns_returns_immutable_collection():
    result = register_patterns([_proven_boundary_pattern()])
    assert isinstance(result, tuple)
    with pytest.raises(TypeError):
        result[0] = None  # type: ignore[index]


def test_register_patterns_preserves_input_order():
    """EDGE ordering (REDACT-02): no sorting, no dedup, no reordering — the returned
    tuple is positionally equal to the input sequence."""
    first = RedactionPattern(pattern=re.compile("(x=)a"), replacement=r"\1*")
    second = RedactionPattern(pattern=re.compile("(y=)b"), replacement=r"\1*")
    third = RedactionPattern(pattern=re.compile("(z=)c"), replacement=r"\1*")
    result = register_patterns([first, second, third])
    assert result == (first, second, third)


def test_register_patterns_keeps_duplicate_patterns():
    """EDGE adjacency (REDACT-02): registering the same object twice keeps BOTH
    entries — no merge, no reject — and the result is still idempotent under
    re-application via ``redact_secrets``."""
    rp = RedactionPattern(pattern=re.compile("(k=)v"), replacement=r"\1*")
    result = register_patterns([rp, rp])
    assert len(result) == 2
    assert result[0] is rp
    assert result[1] is rp
    text = "k=v k=v"
    once = redact_secrets(text, result)
    twice = redact_secrets(once, result)
    assert once == twice


def test_register_patterns_empty_input_returns_empty_tuple():
    """EDGE empty (REDACT-02): zero patterns is a legitimate registration state, but
    ``patterns`` is a REQUIRED positional parameter with no default."""
    assert register_patterns(()) == ()
    with pytest.raises(TypeError):
        register_patterns()  # type: ignore[call-arg]


def test_register_patterns_holds_no_module_level_state():
    """EDGE concurrency (REDACT-02) / SC2: the registry module declares no
    module-level mutable container, and two calls with different inputs never
    accumulate into one another."""
    import yahir_reusable_bot.redact.registry as registry_module

    mutable_types = (list, dict, set, bytearray)
    offending = [
        name
        for name, value in vars(registry_module).items()
        if not name.startswith("__") and isinstance(value, mutable_types)
    ]
    assert offending == []

    first_input = [RedactionPattern(pattern=re.compile("(p=)1"), replacement=r"\1*")]
    second_input = [RedactionPattern(pattern=re.compile("(q=)2"), replacement=r"\1*")]
    first_result = register_patterns(first_input)
    second_result = register_patterns(second_input)
    assert first_result == tuple(first_input)
    assert second_result == tuple(second_input)


def test_register_patterns_error_does_not_echo_pattern_source():
    """PR-02 / T-05-02: a rejected entry may be a literal-constructed pattern whose
    source IS the plaintext secret. The raised message must name the offending
    entry's INDEX and must never interpolate its source text."""
    sentinel = "ZZSENTINELZZ"
    ok = _proven_boundary_pattern()
    bad = RedactionPattern(pattern=re.compile(rf"({sentinel}+)+$"), replacement="***")
    with pytest.raises(ValueError) as excinfo:
        register_patterns([ok, bad])
    message = str(excinfo.value)
    assert sentinel not in message
    assert "1" in message


def test_register_patterns_rejects_malformed_replacement_template():
    """WR-01: a `replacement` template referencing a capture group that does not
    exist in `pattern` (a consumer typo, e.g. `\\2` against a single-group pattern)
    must be rejected at REGISTRATION time with a `ValueError`, not sail through
    silently and raise for the first time deep inside `redact_secrets` at a hot log
    call site. This holds regardless of `skip_redos_check` — the malformed-template
    check is independent of ReDoS vetting."""
    malformed = RedactionPattern(pattern=re.compile(r"(a)"), replacement=r"\2***")
    with pytest.raises(ValueError, match="malformed"):
        register_patterns([malformed])

    malformed_opted_out = RedactionPattern(
        pattern=re.compile(r"(a)"), replacement=r"\2***", skip_redos_check=True
    )
    with pytest.raises(ValueError, match="malformed"):
        register_patterns([malformed_opted_out])


def test_register_patterns_accepts_well_formed_backreference_replacement():
    """WR-01 companion (no false-reject): a `replacement` template whose
    backreference DOES correspond to a real capture group registers cleanly."""
    rp = _proven_boundary_pattern()
    result = register_patterns([rp])
    assert result == (rp,)
