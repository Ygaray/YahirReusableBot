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

MATCH-03 (v0.1.2 WR-02) self-proof addendum: a test asserting a DUPLICATE registry "still
constructs" would pass IDENTICALLY before and after the fix — the pre-fix ``__init__`` has
no uniqueness check at all, so two specs sharing a name always construct fine either way.
The genuinely RED assertion is ``pytest.raises(ValueError)`` around
``CommandRegistry([_spec("status"), _spec("status")])``: pre-fix, this constructs SILENTLY
with a duplicate overwriting in ``by_name`` while ``by_keyword_len_desc`` carries both
entries — it only raises once the D-34 loop grows a ``seen: set[str]`` uniqueness check.
The empty-registry, single-spec, and Unicode-normalization-variant tests below are
deliberately NOT RED-provable — they pin degenerate-input and equality-semantics contracts
that construct successfully both before and after the fix (the pinned-limitation idiom from
``tests/test_identity.py:165``); each says so in its own docstring.
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


def test_duplicate_name_raises_at_construction():
    """Two CommandSpecs sharing a name must raise ValueError at construction (MATCH-03,
    v0.1.2 WR-02). Without this check, a duplicate silently overwrites in ``by_name``
    while ``by_keyword_len_desc`` and ``render_help`` carry both entries — so
    ``match_command`` can resolve a different ``CommandSpec`` than ``by_name`` holds.

    RED pre-fix: CommandRegistry.__init__ performs no uniqueness check, so this
    constructs silently with no raise at all.
    """
    with pytest.raises(ValueError):
        CommandRegistry([_spec("status"), _spec("status")])


def test_duplicate_name_raises_through_build_registry():
    """build_registry forwards to CommandRegistry, so the ValueError propagates through
    it for free — no separate validation needed in build_registry itself (mirrors the
    existing D-34 *_through_build_registry pair)."""
    with pytest.raises(ValueError):
        build_registry([_spec("status"), _spec("status")])


def test_value_error_names_the_duplicated_value():
    """The raised message must name the duplicated spec.name so a consumer can see which
    registration collided (mirrors test_value_error_names_the_offending_uppercase_value)."""
    with pytest.raises(ValueError, match="status"):
        CommandRegistry([_spec("status"), _spec("status")])


def test_empty_and_single_spec_registries_construct_without_duplicate_guard():
    """Degenerate-input boundary guard (probe: MATCH-03/empty), GREEN both before and
    after the fix — an empty or single-spec registry never has a duplicate to trip the
    guard, so this pins the contract rather than proving the RED case.

    CommandRegistry([]) constructs with empty derived views; a single-spec registry
    constructs with a one-entry by_name.
    """
    empty_registry = CommandRegistry([])
    assert empty_registry.by_name == {}
    assert empty_registry.by_keyword_len_desc == ()

    status_spec = _spec("status")
    single_registry = CommandRegistry([status_spec])
    assert single_registry.by_name == {"status": status_spec}


def test_unicode_normalization_variants_are_distinct_names_not_duplicates():
    """Duplicate detection is Python str equality over code points, with NO Unicode
    normalization (probe: MATCH-03/encoding) — GREEN both before and after the fix.

    A precomposed 'café' (NFC, single U+00E9 codepoint) and a decomposed 'café'
    (NFD, 'e' + U+0301 COMBINING ACUTE ACCENT) are distinct str values under code-point
    equality, so registering both together SUCCEEDS with two separate by_name entries.
    This matches the existing D-34 posture: spec.name is compared verbatim after the
    consumer has already casefolded it — the registry never runs unicodedata.normalize.
    """
    precomposed = "caf\u00e9"  # NFC: 'e' + U+00E9 LATIN SMALL LETTER E WITH ACUTE
    decomposed = "café"
    assert precomposed != decomposed  # sanity: distinct str values, same rendered glyphs

    registry = CommandRegistry([_spec(precomposed), _spec(decomposed)])
    assert len(registry.by_name) == 2
