"""Regression tests for MATCH-02 (H13, D-34): ``CommandRegistry`` never validates
``spec.name`` at construction, so an empty name can silently claim blank input and an
uppercase name can become permanently unmatchable (``match_command`` only ever tests a
CASEFOLDED input against ``spec.name`` verbatim — an uppercase name never matches
anything, forever, with no signal at build time).

Self-proof note (matching ``test_selfproof_*`` in ``tests/test_import_hygiene.py`` /
``test_retry.py:1-13``): a test that only asserts ``CommandRegistry([...])`` "works" for a
valid spec passes IDENTICALLY before and after the fix — the pre-fix `__init__` has no
validation loop at all, so a well-formed spec always constructs fine either way. The
genuinely RED assertions are the two ``pytest.raises(ValueError)`` cases below (empty name,
uppercase name): pre-fix, `CommandRegistry.__init__` performs no name check whatsoever, so
both specs construct SILENTLY with no exception — these two assertions fail pre-fix and
only pass once D-34's validation loop is added.

No prior ``tests/test_registry.py`` exists (RESEARCH.md Pitfall 5) — this file founds the
test substrate for ``registry/registry.py``, following the module-name convention
(``test_retry.py``/``retry.py``, ``test_identity.py``/``identity.py``) and the plain-
construction / no-mocking-library house style (``tests/conftest.py`` module docstring).
"""
from __future__ import annotations

import pytest

from yahir_reusable_bot.registry.registry import CommandRegistry, build_registry
from yahir_reusable_bot.registry.spec import CommandSpec


def _spec(name: str) -> CommandSpec:
    """A minimal, plain-construction CommandSpec factory (house style, no mocking)."""
    return CommandSpec(
        name=name,
        group="General",
        summary="a placeholder command",
        bind=lambda ctx: None,
    )


def test_empty_name_raises_at_construction():
    """An empty spec.name can no longer silently claim blank input (D-34, MATCH-02).

    RED pre-fix: CommandRegistry.__init__ performs no name validation, so this constructs
    silently with no raise at all.
    """
    with pytest.raises(ValueError):
        CommandRegistry([_spec("")])


def test_empty_name_raises_through_build_registry():
    """build_registry forwards to CommandRegistry, so the ValueError propagates through
    it for free — no separate validation needed in build_registry itself."""
    with pytest.raises(ValueError):
        build_registry([_spec("")])


def test_uppercase_name_raises_at_construction():
    """An uppercase spec.name can no longer become permanently unmatchable (D-34,
    MATCH-02): match_command casefolds the INPUT text and tests it against spec.name
    verbatim, so an uppercase name like 'Status' would never match anything, forever,
    with no signal at build time. RED pre-fix: no raise."""
    with pytest.raises(ValueError):
        CommandRegistry([_spec("Status")])


def test_uppercase_name_raises_through_build_registry():
    with pytest.raises(ValueError):
        build_registry([_spec("Status")])


def test_valid_names_still_construct_without_regression():
    """Well-formed (non-empty, already-casefolded) specs must construct exactly as
    before — no regression to the valid-spec path. Exercises by_name and
    by_keyword_len_desc, the two derived views the validation loop sits alongside."""
    status_spec = _spec("status")
    cloudy_spec = _spec("next-cloudy")
    registry = CommandRegistry([status_spec, cloudy_spec])

    assert registry.by_name == {"status": status_spec, "next-cloudy": cloudy_spec}
    # Longest-keyword-first ordering must be preserved (unrelated to this fix, but a
    # regression guard that the validation loop didn't disturb the existing derivation).
    assert registry.by_keyword_len_desc == (cloudy_spec, status_spec)


def test_value_error_names_the_offending_empty_value():
    """The raised message must name the offending spec.name so a consumer can see which
    spec is malformed (Claude's Discretion on exact wording; it MUST name the value)."""
    with pytest.raises(ValueError, match=re_escape_empty()):
        CommandRegistry([_spec("")])


def test_value_error_names_the_offending_uppercase_value():
    with pytest.raises(ValueError, match="Status"):
        CommandRegistry([_spec("Status")])


def re_escape_empty() -> str:
    """`pytest.raises(match=...)` treats the arg as a regex; an empty repr (`''`) is a
    literal substring with no special regex chars, so no escaping is actually needed —
    named as a tiny helper so the intent (match the empty-value repr) reads clearly at
    the call site."""
    return r"''"
