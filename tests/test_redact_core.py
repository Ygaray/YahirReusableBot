"""Regression suite for REDACT-01, REDACT-02 (frozen-type half) and REDACT-06 — the
generic secret-scrubbing primitive (``redact_secrets``) and the ``RedactionPattern``
pair type this hub promotes from WeatherBot's proven ``weatherbot/_redact.py``.

Self-proof note (matching ``test_registry.py``'s docstring convention):
``yahir_reusable_bot.redact.core`` does not exist yet, so EVERY assertion in this
module is genuinely RED pre-fix — collection itself fails with an ``ImportError``
before a single test body runs. There is no partial-pass baseline to distinguish
here; the entire file is the RED half of GATE-02's two-commit discipline.

Ported from ``/home/yahir/Projects/WeatherBot/tests/test_redact_hygiene.py``'s
``SENTINEL`` constant and boundary-case matrix (the behavioral spec being
generalized), minus the httpx/Discord-specific leak-path tests, which belong to a
future consumer-side parity gate, not this hub's own core suite.
"""
from __future__ import annotations

import re
import warnings
from dataclasses import FrozenInstanceError, asdict, astuple

import pytest

from yahir_reusable_bot.redact.core import RedactionPattern, redact_secrets

# A fake sentinel key — the value that must never survive redaction anywhere in this
# module. Reused by every test needing a stand-in secret (WeatherBot's own value,
# test_redact_hygiene.py:29). A module-level constant, not a fixture (D-10 house
# convention: no new conftest.py fixtures for a shared test literal).
SENTINEL = "SENTINELKEY_do_not_leak_123"


def test_redact_helper_boundaries():
    """T-05-03 / the 5-case boundary matrix ported verbatim from
    ``test_redact_hygiene.py:56-82``: ``redact_secrets`` replaces only the value,
    stopping at the first delimiter so the label, following params, the trailing
    quote and the case-insensitive token all survive (D-48's backreference shape)."""
    rp = RedactionPattern(
        pattern=re.compile(r"(appid=)[^&\s\"'<>\\]+", re.IGNORECASE),
        replacement=r"\1***",
    )

    # (1) The real raise_for_status message form: params after the key must survive.
    real = f"for url 'x?lat=1&appid={SENTINEL}&units=imperial'"
    out = redact_secrets(real, (rp,))
    assert SENTINEL not in out
    assert "appid=***" in out
    assert "units=imperial" in out  # D-48: following params preserved

    # (2) Stops at the '&' — the next param is intact.
    out2 = redact_secrets(f"appid={SENTINEL}&next=1", (rp,))
    assert out2 == "appid=***&next=1"

    # (3) URL-encoded value: the %XX is part of the captured value, stops at '&'.
    out3 = redact_secrets("appid=A%2Fdef&units=x", (rp,))
    assert out3 == "appid=***&units=x"

    # (4) Quote-terminated (as httpx's message ends the URL): stops at the "'".
    out4 = redact_secrets(f"...appid={SENTINEL}'", (rp,))
    assert out4 == "...appid=***'"

    # (5) Case-insensitive: an uppercase APPID= token is also redacted.
    out5 = redact_secrets(f"APPID={SENTINEL}&units=x", (rp,))
    assert SENTINEL not in out5
    assert "units=x" in out5


def test_redact_secrets_idempotent():
    """REDACT-01 / SC1: re-applying ``redact_secrets`` to already-redacted text is an
    exact no-op — the second pass changes nothing."""
    rp = RedactionPattern(pattern=re.compile(r"(k=)\w+"), replacement=r"\1***")
    once = redact_secrets("k=abc123&x=1", (rp,))
    twice = redact_secrets(once, (rp,))
    assert once == twice == "k=***&x=1"


def test_redact_secrets_zero_patterns_is_identity():
    """D-49: zero patterns is a valid, SILENT identity no-op — no raise, no warning.
    ``warnings.catch_warnings`` + ``simplefilter('error')`` proves genuinely silent,
    not merely un-asserted."""
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert redact_secrets("anything at all", ()) == "anything at all"


def test_redact_secrets_empty_text_returns_empty():
    """EDGE empty (REDACT-01): an empty ``text`` returns the empty string, patterns
    present or not."""
    rp = RedactionPattern(pattern=re.compile(r"(k=)\w+"), replacement=r"\1***")
    assert redact_secrets("", (rp,)) == ""


def test_redact_secrets_applies_patterns_in_registration_order():
    """EDGE ordering (D-49): patterns apply sequentially in the caller's registration
    order — each pattern substitutes against the PREVIOUS pattern's output. Two
    patterns whose matches overlap on one input yield a different, deterministic
    result depending on order — documented, not special-cased."""
    # Pattern A turns "a=1" into "a=X"; pattern B turns "a=X" into "a=Y". Applied
    # A-then-B the whole value collapses to Y; applied B-then-A, B never matches (the
    # input has no "a=X" yet) so only A's substitution survives.
    pattern_a = RedactionPattern(pattern=re.compile(r"a=1"), replacement="a=X")
    pattern_b = RedactionPattern(pattern=re.compile(r"a=X"), replacement="a=Y")

    result_ab = redact_secrets("a=1", (pattern_a, pattern_b))
    result_ba = redact_secrets("a=1", (pattern_b, pattern_a))

    assert result_ab == "a=Y"
    assert result_ba == "a=X"
    assert result_ab != result_ba


def test_redact_secrets_replaces_every_adjacent_occurrence():
    """EDGE adjacency (REDACT-01): two touching occurrences of the same pattern in one
    string are BOTH replaced (replace-all, not replace-first); neither occurrence
    merges with nor clobbers the other."""
    rp = RedactionPattern.literal(SENTINEL)
    text = f"{SENTINEL}{SENTINEL} trailing"
    out = redact_secrets(text, (rp,))
    assert SENTINEL not in out
    assert out == "****** trailing"  # two adjacent "***" replacements, not merged


def test_redact_secrets_does_not_mutate_input_or_patterns():
    """EDGE concurrency (REDACT-01): ``redact_secrets`` holds no state between calls —
    it rebinds only a local, never mutating its ``text`` argument (strings are
    immutable, but this proves identity is untouched via the original binding staying
    intact) or its ``patterns`` sequence."""
    original_text = f"appid={SENTINEL}&units=x"
    rp = RedactionPattern(
        pattern=re.compile(r"(appid=)[^&]+", re.IGNORECASE), replacement=r"\1***"
    )
    patterns = (rp,)
    patterns_before = tuple(patterns)

    result = redact_secrets(original_text, patterns)

    # The original text binding is untouched (str is immutable, but this proves the
    # function never reassigns through a reference the caller can observe).
    assert original_text == f"appid={SENTINEL}&units=x"
    assert result != original_text
    # The patterns sequence is unchanged: same length, same element identities.
    assert len(patterns) == len(patterns_before)
    assert patterns[0] is patterns_before[0]


def test_redact_secrets_masks_non_ascii_literal_at_code_point_level():
    """EDGE encoding (REDACT-01, D-52): ``redact_secrets`` is strict ``str -> str`` and
    matches at Python ``str`` code-point level — a non-ASCII secret is masked by its
    exact code-point sequence, no Unicode normalization, no case folding. ``bytes`` is
    out of contract in Phase 5 (D-52); its tolerance belongs to the Phase-6 seam."""
    non_ascii_secret = "café秘密"  # "café" + CJK "secret" characters
    rp = RedactionPattern.literal(non_ascii_secret)
    text = f"leading ASCII text {non_ascii_secret} trailing ASCII text"
    out = redact_secrets(text, (rp,))
    assert non_ascii_secret not in out
    assert "leading ASCII text" in out
    assert "trailing ASCII text" in out

    # Strict str -> str contract: confirm the annotation, not runtime bytes-tolerance
    # (D-52 relocates that clause to the Phase-6 seam; this core must not "fix" it).
    annotations = redact_secrets.__annotations__
    assert annotations["text"] == "str"
    assert annotations["return"] == "str"


def test_redaction_pattern_is_frozen():
    """REDACT-02 (SC2): ``RedactionPattern`` is frozen — assigning to any field raises
    ``dataclasses.FrozenInstanceError``."""
    rp = RedactionPattern(pattern=re.compile("x"), replacement="y")
    with pytest.raises(FrozenInstanceError):
        rp.replacement = "z"


def test_literal_matches_inside_repr():
    """REDACT-06 / SC4 / T-05-02: a registered literal secret is blocked wherever it
    physically appears — including inside the ``repr()`` of an object that embeds it —
    with NO special code path. This generalizes
    ``test_reraised_exception_request_carries_no_key``
    (``test_redact_hygiene.py:194-218``)."""

    class _Carrier:
        def __repr__(self) -> str:
            return f"<Carrier secret={SENTINEL!r}>"

    rp = RedactionPattern.literal(SENTINEL)
    text = f"got object {_Carrier()!r} while handling request"
    out = redact_secrets(text, (rp,))
    assert SENTINEL not in out
    assert "***" in out


def test_literal_escapes_regex_metacharacters():
    """REDACT-06: ``RedactionPattern.literal`` matches its value by literal
    code-point equality after escaping — a value full of regex metacharacters
    matches only its literal text, never interpreted as a regex."""
    metachar_value = "a.c*d"
    rp = RedactionPattern.literal(metachar_value)

    exact_hit = f"prefix {metachar_value} suffix"
    out = redact_secrets(exact_hit, (rp,))
    assert metachar_value not in out
    assert "***" in out

    # A regex-wildcard near-miss: the UNescaped pattern "a.c*d" would match "abd"
    # ('.' matches any char 'b', 'c*' matches zero 'c's, then literal 'd') — but the
    # escaped literal must NOT match this near-miss, leaving it untouched.
    near_miss = "abd"
    out_near_miss = redact_secrets(near_miss, (rp,))
    assert out_near_miss == near_miss


def test_literal_rejects_empty_or_blank_value():
    """REDACT-06 EDGE empty: ``RedactionPattern.literal`` rejects an empty or
    whitespace-only value with ``ValueError`` at construction — an unrestricted
    empty literal compiles to a pattern matching at every position and would shred
    the entire text with placeholder-separated garbage (D-41 fail-loud-at-construction
    precedent, ``discord/panelkit.py:180-185``)."""
    with pytest.raises(ValueError):
        RedactionPattern.literal("")
    with pytest.raises(ValueError):
        RedactionPattern.literal("   ")


def test_redaction_pattern_repr_does_not_leak_pattern_source():
    """PR-01 / T-05-02: ``repr()`` of a ``RedactionPattern`` never reproduces the
    compiled pattern's source text — a consumer logging its own registered pattern
    set cannot leak a literal secret through the hub object's representation. Asserted
    across ``repr()``, ``str()`` and the ``!r`` f-string conversion (both paths fall
    back to ``__repr__`` since ``__str__`` is deliberately not defined)."""
    rp = RedactionPattern.literal(SENTINEL)
    assert SENTINEL not in repr(rp)
    assert SENTINEL not in str(rp)
    assert SENTINEL not in f"{rp!r}"


def test_redaction_pattern_has_no_instance_dict_so_generic_serializers_cannot_leak():
    """WR-02, accidental-path half: ``slots=True`` removes the instance ``__dict__``
    entirely, so the two paths a GENERIC serializer or logging helper reaches for
    without anyone intending to introspect a dataclass — ``vars(rp)`` and
    ``rp.__dict__`` — now raise instead of handing back the raw, unwrapped
    ``re.Pattern`` (whose own default ``repr`` prints the secret source verbatim).

    These are the paths that leak by ACCIDENT. Closing them is the point: a consumer
    that writes ``logger.info("patterns", extra=vars(rp))`` gets a loud error instead
    of a silently-leaked secret."""
    rp = RedactionPattern.literal(SENTINEL)

    with pytest.raises(TypeError):
        vars(rp)

    with pytest.raises(AttributeError):
        rp.__dict__  # noqa: B018 — attribute access itself is the assertion


def test_redaction_pattern_asdict_still_exposes_raw_pattern_source():
    """WR-02, residual half — a tripwire, NOT an endorsement.

    ``dataclasses.asdict``/``astuple`` still return the RAW ``re.Pattern``, so they
    still print the secret source. This is NOT closable while ``pattern`` stays a
    public field holding the live compiled object that ``redact_secrets`` calls
    ``.sub()`` on — and it is no worse than reading ``rp.pattern.pattern`` directly,
    which is equally public and equally explicit. Both require a caller to
    deliberately introspect the dataclass; neither happens by accident (that class of
    path is closed by the slots test above).

    Pinned so a future change that tries to close this doesn't silently break the
    ``redact_secrets`` call path, which depends on the raw ``pattern`` field staying
    reachable. Closing it properly means an opaque wrapper — a PUBLIC API shape
    change, deliberately out of scope for this phase."""
    rp = RedactionPattern.literal(SENTINEL)

    assert SENTINEL in repr(asdict(rp)["pattern"])
    assert SENTINEL in repr(astuple(rp)[0])

    # The equally-public, equally-explicit path this is no worse than:
    assert SENTINEL in rp.pattern.pattern
