"""``register_patterns`` — vet, then freeze, a consumer's redaction patterns (PC-01).

Vetting is a ONE-TIME registration cost, never a per-log-line cost: stdlib ``re`` has
no timeout, hub logging is synchronous, and the Discord adapter runs an asyncio
gateway loop, so a consumer's pathological regex would starve heartbeats and drop the
live connection with no diagnostic pointing at the pattern. This is the D-34
fail-loud-at-registration posture applied to REDACT-03: a pathological pattern is a
consumer wiring bug that must surface at build time, because there is no runtime
rescue for an uninterruptible ``re`` search once it is on the hot path.

This module is NOT a proof that a passed pattern is safe (prohibition PR-03). The
structural heuristic below is deliberately non-exhaustive, and the timing probe
samples a finite, pattern-agnostic corpus — a shape neither happens to catch could
still exist. Vetting narrows the pathological-pattern class it is known to reach; it
does not certify the absence of every possible one, and ``skip_redos_check=True`` is
never the remedy for a rejection — a rejection means rewrite the pattern; the opt-out
is only for a pattern whose worst case the consumer has independently reasoned is
bounded.

Stdlib only, plus an absolute intra-package import of :class:`RedactionPattern` — this
module imports no sibling ``yahir_reusable_bot`` subpackage (pure-leaf discipline,
verified by ``tests/test_import_hygiene.py``).
"""

from __future__ import annotations

import re
import time
from collections.abc import Sequence

from yahir_reusable_bot.redact.core import RedactionPattern

# Cheap structural first pass: a group containing a quantifier, itself quantified,
# e.g. ``(a+)+``, ``(x*)*`` — the textbook nested-quantifier ReDoS shape. Deliberately
# a HEURISTIC, not exhaustive: an overlapping-alternation shape like ``(a|a)*$`` has
# no nested-quantifier substring at all, so this pass cannot see it — the wall-clock
# timing probe below is the actual safety net for that class of shape. This pass
# exists purely for speed and a clearer, more specific error on the shapes it can see.
_NESTED_QUANTIFIER_RX = re.compile(r"\([^()]*[+*][^()]*\)[+*]")

# Deliberately GENEROUS per D-50: pure-Python wall-clock timing is machine-dependent,
# so a tight budget would false-reject a legitimate pattern on a loaded host. A benign
# pattern completes the entire ladder below in single-digit milliseconds (measured);
# genuinely catastrophic backtracking blows this budget by orders of magnitude even at
# a small ladder rung. Internal detail, not public API — tunable without touching this
# module's signature (D-50).
_REDOS_BUDGET_S = 0.3

# Ascending repeat counts probed against the corpus below. The fine tier (the first
# nine rungs) grows by exactly +2 per rung — this bounds the overshoot for an
# exponentially-growing pattern to roughly a 4x jump between two consecutive rungs
# (2**(n+2) / 2**n == 4), so a catastrophic pattern is caught at a small rung instead
# of at one huge probe. The coarse tier (the last four rungs) is reached only by a
# pattern that showed no superlinear growth in the fine tier, and exists to catch a
# polynomial (not exponential) blowup that the fine tier's short probes are too small
# to reveal.
_REDOS_LADDER: tuple[int, ...] = (8, 10, 12, 14, 16, 18, 20, 22, 24, 100, 400, 1600, 4000)

# Pattern-agnostic adversarial SHAPES (the registry knows nothing about any consumer's
# pattern shape, so this corpus must stay generic): a single repeated character, a
# repeated digit run, and a repeated query-parameter fragment — spanning the character
# classes most likely to appear in a real consumer pattern (tokens, URLs, query
# strings). Each shape is repeated by a ladder count and suffixed with ``"!"`` inside
# ``_blows_budget`` — a character unlikely to satisfy a well-formed pattern's tail,
# forcing the "almost but not quite" backtracking that triggers catastrophic patterns.
_REDOS_CORPUS: tuple[str, ...] = ("a", "0123456789", "abc=def&")


def _looks_pathological(pattern: re.Pattern[str]) -> bool:
    """Cheap structural pre-check: does ``pattern``'s source contain the textbook
    nested-quantifier shape? Heuristic, non-exhaustive — see the module docstring."""
    return bool(_NESTED_QUANTIFIER_RX.search(pattern.pattern))


def _blows_budget(pattern: re.Pattern[str]) -> bool:
    """Wall-clock probe: does ``pattern`` exceed ``_REDOS_BUDGET_S`` of CUMULATIVE
    search time against the adversarial corpus, escalated one ladder rung at a time?

    Termination correction over a naive single-long-probe design (load-bearing, do
    not simplify back): each individual ``search`` call is its own step, and the
    cumulative elapsed time is compared against the budget AFTER EVERY search,
    returning True the moment it is exceeded. This module never builds one large
    probe string and times a single search over it — ``re`` cannot be interrupted, so
    a single search over a long probe against a catastrophic pattern would run to
    completion and hang the very call this check exists to bound (T-05-06). Because
    the fine tier of ``_REDOS_LADDER`` grows by only +2 repeats per rung, an
    exponentially-growing pattern's per-rung cost rises by at most ~4x, bounding the
    overshoot past the budget instead of leaving it unbounded.
    """
    start = time.perf_counter()
    for count in _REDOS_LADDER:
        for shape in _REDOS_CORPUS:
            probe = shape * count + "!"
            pattern.search(probe)
            if time.perf_counter() - start > _REDOS_BUDGET_S:
                return True
    return False


def register_patterns(
    patterns: Sequence[RedactionPattern],
) -> tuple[RedactionPattern, ...]:
    """Vet, then freeze, a consumer's ``patterns`` (REDACT-02 + REDACT-03).

    ``patterns`` is REQUIRED with no default — matching ``build_registry``'s posture
    and D-49's "the consumer hands zero patterns explicitly": ``register_patterns(())``
    is a legitimate, silent no-op returning ``()``, but omitting the argument entirely
    raises ``TypeError``, never silently defaulting to empty.

    Every entry is checked in one pass, before any derived state exists, mirroring the
    validate-then-derive idiom in ``registry/registry.py`` (borrowed as an idiom only —
    this is a free function, not a stateful class). An entry whose ``skip_redos_check``
    is True skips both checks entirely (D-50's explicit, per-pattern opt-out). Every
    other entry is rejected if it looks structurally pathological OR blows the
    wall-clock budget against the adversarial corpus.

    On success, returns a NEW ``tuple(patterns)`` — a frozen collection positionally
    equal to the input, preserving order, keeping duplicates, and never sorting or
    deduplicating. This function reads and writes no module-level mutable state: two
    calls with different inputs never accumulate into one another, and repeated calls
    in any order and any test ordering (isolated or full-suite) produce independent
    results (SC2).
    """
    for index, rp in enumerate(patterns):
        if rp.skip_redos_check:
            continue
        if _looks_pathological(rp.pattern) or _blows_budget(rp.pattern):
            # Fail LOUD at registration (D-34's precedent, applied to REDACT-03): a
            # pathological pattern is a consumer wiring bug that must surface at build
            # time, because stdlib `re` cannot be interrupted and there is no runtime
            # rescue once this pattern reaches a hot log call site. A ValueError (not
            # an assert) because this is genuine untrusted-input validation that must
            # survive `-O`. The message names the entry by INDEX and by its
            # source-eliding `__repr__` (from redact/core.py) — NEVER by interpolating
            # `rp.pattern.pattern` directly: a rejected entry may be a
            # literal-constructed pattern whose source IS the plaintext secret, and
            # echoing it here would leak that secret into exactly the logs this
            # package exists to scrub (PR-02, T-05-02).
            raise ValueError(
                f"RedactionPattern at index {index} rejected at registration — it "
                f"triggered the nested-quantifier structural check or exceeded the "
                f"ReDoS wall-clock budget against the adversarial probe corpus: "
                f"{rp!r}. Rewrite the pattern to avoid catastrophic backtracking "
                f"(e.g. remove nested or overlapping quantifiers). "
                f"skip_redos_check=True is NOT a way to silence this rejection — it "
                f"is only for a pattern whose worst-case cost the consumer has "
                f"independently reasoned is bounded."
            )
    return tuple(patterns)
