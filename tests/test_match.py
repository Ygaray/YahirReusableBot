"""Regression tests for MATCH-01 (H06, D-35): ``match_command`` currently slices
``rest = stripped[len(spec.name):]`` — the UN-folded original string sliced with the
FOLDED keyword's length — so a length-changing casefold (``ß``->``ss``, ``ﬁ``->``fi``)
mis-slices the raw argument.

Self-proof note (matching ``test_selfproof_*`` in ``tests/test_import_hygiene.py`` /
``test_retry.py:1-13``): a test that only checks ``folded.startswith(spec.name)`` would
pass IDENTICALLY before and after the fix (that keyword test is unaffected by this bug).
The genuinely RED assertion is the end-to-end ``ParsedCommand`` result:
``match_command("ßtatus hello", [spec("sstatus")])`` pre-fix slices
``stripped[len("sstatus"):]`` == ``stripped[7:]`` — one character too far into the
6-character original ``"ßtatus"`` (index 6 is the correct original boundary; the folded
keyword's length, 7, overshoots by the one character ``ß`` gained on folding). That
overshot slice lands ON ``"hello"`` with no leading whitespace, so the existing
word-boundary guard (``rest and not rest[0].isspace()``) rejects it and the WHOLE match
fails — pre-fix returns ``spec=None, arg=None`` for a keyword that should have matched,
not merely a mis-sliced arg. The fix (mapping the boundary to the ORIGINAL string) is
what lets these specs match at all, with the correct raw-case arg.

No prior ``tests/test_match.py`` exists (RESEARCH.md Pitfall 5, refining CONTEXT.md's
canonical_refs which claims otherwise) — this file founds the test substrate for
``registry/match.py``, following the module-name convention and the plain-construction /
no-mocking-library house style (``tests/conftest.py`` module docstring). Per RESEARCH.md
Common Pitfalls #4, the adversarial single-character-overshoot row (``spec.name="s"``,
input ``"ß foo"``) is the sharpest discriminator that a naive length-equality boundary
scan is buggy — included below alongside the two CONTEXT-named cases and one extra
adversarial ligature (``ﬆ``->``st``).
"""
from __future__ import annotations

from yahir_reusable_bot.registry.match import match_command
from yahir_reusable_bot.registry.spec import CommandSpec


def _spec(name: str) -> CommandSpec:
    """A minimal, plain-construction CommandSpec factory (house style, no mocking)."""
    return CommandSpec(
        name=name,
        group="General",
        summary="a placeholder command",
        bind=lambda ctx: None,
    )


def test_length_changing_casefold_sharp_s_extracts_correct_raw_arg():
    """RED pre-fix: 'ß' casefolds to 'ss' (length 2 from 1 original char), so
    len('sstatus') == 7 overshoots the correct boundary (original index 6) by one
    character, landing the slice directly on 'hello' with no leading space — the
    existing word-boundary guard then rejects it and the WHOLE match fails
    (spec=None), not merely a wrong arg. The boundary must be computed against the
    ORIGINAL string."""
    result = match_command("ßtatus hello", [_spec("sstatus")])
    assert result.spec is not None
    assert result.spec.name == "sstatus"
    assert result.arg == "hello"


def test_ligature_fi_extracts_correct_raw_arg():
    """RED pre-fix: 'ﬁ' (single codepoint) casefolds to 'fi' (2 chars) — same
    length-changing-casefold class as the sharp-s case, verified independently."""
    result = match_command("ﬁnd hello", [_spec("find")])
    assert result.spec is not None
    assert result.spec.name == "find"
    assert result.arg == "hello"


def test_ligature_st_extracts_correct_raw_arg():
    """Extra adversarial ligature beyond the two CONTEXT-named cases: 'ﬆ' casefolds to
    'st' (2 chars), verified end-to-end in RESEARCH.md Code Examples #1."""
    result = match_command("ﬆatus hi", [_spec("status")])
    assert result.spec is not None
    assert result.spec.name == "status"
    assert result.arg == "hi"


def test_adversarial_single_char_overshoot_is_a_non_match():
    """The sharpest discriminator (RESEARCH.md Pitfall 4): spec.name='s' (length 1), input
    'ß foo' — folded == 'ss foo', which DOES pass folded.startswith('s'), but the very
    first original character ('ß') alone folds to 2 characters, so no original-index
    prefix has folded-length exactly 1 — the boundary scan overshoots from 0 straight to
    2 without ever hitting 1. This is provably NOT a real word-boundary match (no Unicode
    casefold expansion contains whitespace) and must be a clean non-match, not a mis-slice
    or a crash."""
    result = match_command("ß foo", [_spec("s")])
    assert result.spec is None
    assert result.arg is None


def test_empty_input_is_a_clean_non_match():
    result = match_command("", [_spec("status")])
    assert result.spec is None
    assert result.arg is None


def test_whitespace_only_input_is_a_clean_non_match():
    result = match_command("   ", [_spec("status")])
    assert result.spec is None
    assert result.arg is None


def test_raw_case_preserved_for_ascii_regression_guard():
    """Regression guard: the arg must never be lowercased, even for a plain-ASCII
    keyword with no length-changing casefold involved at all."""
    result = match_command("status HeLLo", [_spec("status")])
    assert result.spec is not None
    assert result.arg == "HeLLo"
