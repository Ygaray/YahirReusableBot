"""The generic secret-scrubbing primitive (PC-01) — a pattern/replacement pair type
plus the substitution loop that applies a sequence of them to arbitrary rendered text.

This generalizes a production-proven, single-purpose scrubber (one hardcoded regex,
one hardcoded replacement) into a mechanism any consumer registers its own patterns
against. Only the pattern SHAPE is generic here; the pattern CONTENT (what secret
looks like what) is always injected by the consumer, never hardcoded in this module.

The load-bearing idea generalized from the proven implementation is the VALUE
BOUNDARY: a scrub must stop at the first delimiter after the secret value — a
following separator character, whitespace, a quote, an angle bracket, or a
backslash — rather than consuming to end-of-line. Stopping there is what keeps a
label, any trailing parameters, or a closing quote/URL intact while only the secret
value itself is masked. A boundary style that consumes too far turns a diagnosable
incident into an undiagnosable one — the exact failure mode this module exists to
avoid (see the module's threat model, T-05-03).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, repr=False)
class RedactionPattern:
    """A pre-compiled pattern paired with its replacement template (D-48).

    ``pattern`` must already be compiled — accepting a raw string here would make
    late compilation (and flags desynced from their pattern) structurally possible,
    which this type forecloses entirely: the ONLY way to build one is with an
    already-compiled ``re.Pattern``.

    ``replacement`` is any valid ``re.sub`` replacement template. A positional
    backreference (``r"\\1***"``) and a named-group reference (``r"\\g<keep>***"``)
    both work — this type enforces neither style, though named groups are the
    RECOMMENDED convention for new patterns (a positional backreference silently
    shifts if a consumer later adds a capture group).

    ``skip_redos_check`` is a defaulted, additive field (mirrors the project's
    additive-and-defaulted-field posture): a per-pattern opt-out a companion
    registration helper may read to skip its wall-clock vetting for a pattern known
    to be legitimately slow. This module never reads it — it exists purely as a
    carried value.

    Frozen: assigning to any field raises ``dataclasses.FrozenInstanceError``.
    """

    pattern: re.Pattern[str]
    replacement: str
    skip_redos_check: bool = False

    @classmethod
    def literal(cls, value: str, replacement: str = "***") -> "RedactionPattern":
        """Build a pattern that matches ``value`` by literal code-point equality.

        A literal is not a second code path — it feeds the exact same compiled-
        pattern pipeline every other pattern uses via ``re.escape``, so it matches
        ``value`` wherever it physically appears (including inside another object's
        own ``repr()``), never interpreted as a regex. A literal replaces the WHOLE
        matched value with ``replacement``; unlike a labeled pattern there is no
        surrounding text to preserve, so there is nothing to keep.

        Guarded before compiling: an empty or whitespace-only ``value`` would
        compile to a pattern matching at every position in any text, which would
        shred the entire string into placeholder-separated garbage on the very
        first call — the same class of footgun a standing empty-marker guard
        elsewhere in this project rejects at construction rather than at first use.
        Raised here, not later, because the mistake is only ever cheap to diagnose
        at the exact call that made it. The message intentionally does not echo
        ``value`` — the value being rejected may itself be a secret in transit.
        """
        if not value or not value.strip():
            raise ValueError(
                "RedactionPattern.literal() requires a non-empty, non-whitespace "
                "value — an empty or blank value would compile to a pattern "
                "matching at every position and destroy the entire text it is "
                "applied to"
            )
        return cls(pattern=re.compile(re.escape(value)), replacement=replacement)

    def __repr__(self) -> str:
        """Source-eliding representation (why the dataclass sets ``repr=False``).

        A ``RedactionPattern`` built via :meth:`literal` holds the secret value
        verbatim inside its compiled pattern's source text. The dataclass-generated
        default ``repr`` would print that source text, so a consumer logging its own
        registered pattern set (``"registered %r", pattern``) would leak the exact
        value this module exists to mask. This elision is unconditional, not
        conditional on how the pattern was built — a consumer can hand-construct a
        secret-bearing pattern without :meth:`literal`, so a conditional rule would
        be unsound. ``__str__`` is deliberately not defined; Python falls back to
        ``__repr__``, so both call paths (and ``!r`` f-string interpolation) are
        covered by this one override.
        """
        return (
            f"RedactionPattern(pattern=<compiled len={len(self.pattern.pattern)} "
            f"flags={self.pattern.flags!r}>, replacement={self.replacement!r}, "
            f"skip_redos_check={self.skip_redos_check!r})"
        )


def redact_secrets(text: str, patterns: Sequence[RedactionPattern]) -> str:
    """Scrub every pattern in ``patterns`` from ``text``, in registration order.

    Applies each pattern's substitution sequentially — each pattern's ``sub`` runs
    against the PREVIOUS pattern's output, not the original ``text`` — so an
    overlapping pair of patterns produces a result that depends on the caller's
    registration order. That dependence is documented behavior, not special-cased
    away: a consumer controls order by controlling the sequence it hands in.

    An empty or falsy ``patterns`` returns ``text`` unchanged immediately, with no
    regex work, no raise and no warning — a consumer wiring this mechanism before
    registering anything is a legitimate, silent no-op state, not an error.

    This function never raises. It is strict ``str -> str``: matching happens at
    Python ``str`` code-point level, with no Unicode normalization and no case
    folding performed by this function itself (a pattern's own ``re.IGNORECASE``
    flag, if set, travels with it). A caller needing NFC/NFD equivalence normalizes
    ``text`` before calling. A non-``str`` argument is out of this function's
    contract; tolerating other types (e.g. decoding ``bytes``) is owned by whatever
    seam sits between an arbitrary write call and this function, never by this
    function itself — folding that tolerance in here would let a malformed caller
    silently succeed instead of surfacing at its own boundary.

    Never mutates ``text`` or ``patterns``: each pattern's substitution rebinds only
    a local variable, so the caller's original string and sequence are always
    left exactly as handed in, and concurrent calls sharing one frozen ``patterns``
    tuple do not interfere with one another.

    Every ``RedactionPattern.pattern`` is already compiled before it ever reaches
    this function — no compilation occurs here, so this loop can run on a hot path
    (a log call site) without ever paying compilation cost per call.
    """
    if not patterns:
        return text
    for rp in patterns:
        text = rp.pattern.sub(rp.replacement, text)
    return text
