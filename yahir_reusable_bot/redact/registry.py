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

# Ascending repeat counts probed against the corpus below, from a low floor through a
# high ceiling that still catches a slow polynomial (not just exponential) blowup.
# EVERY rung — not just an early subset — differs from the rung before it by at most
# ``_REDOS_LADDER_MAX_RATIO``. This is what bounds the overshoot past the budget for
# an exponentially-growing pattern to that same ratio AT EVERY STEP, so a catastrophic
# pattern is always caught at a small rung instead of surfacing for the first time as
# one huge, uninterruptible probe (T-05-06 / CR-01). A prior version of this ladder
# jumped straight from 24 to 100 after a bounded-growth run of small rungs — for a
# pattern whose exponential blowup was just slow enough to stay under budget through
# rung 24, that single jump was not "a small rung," it was an effectively unbounded
# wall-clock probe. ``_validate_ladder_growth_bound`` below enforces the ratio cap at
# import time so a future edit can't silently reintroduce that gap.
_REDOS_LADDER_MAX_RATIO = 2.0
_REDOS_LADDER: tuple[int, ...] = tuple(range(8, 41, 2)) + (48, 64, 96, 144, 216, 324)

# Pattern-agnostic adversarial SHAPES (the registry knows nothing about any consumer's
# pattern shape, so this corpus must stay generic): a single repeated character, a
# repeated digit run, and a repeated query-parameter fragment — spanning the character
# classes most likely to appear in a real consumer pattern (tokens, URLs, query
# strings). Each shape is repeated by a ladder count and suffixed with ``"!"`` inside
# ``_blows_budget`` — a character unlikely to satisfy a well-formed pattern's tail,
# forcing the "almost but not quite" backtracking that triggers catastrophic patterns.
_REDOS_CORPUS: tuple[str, ...] = ("a", "0123456789", "abc=def&")


def _validate_ladder_growth_bound(ladder: tuple[int, ...], max_ratio: float) -> None:
    """Fail loud at import time if any two consecutive ``ladder`` rungs grow by more
    than ``max_ratio`` — the invariant ``_blows_budget`` relies on to keep every probe
    bounded (T-05-06 / CR-01). Deliberately a plain function call (not a bare
    ``assert``) so this self-check survives ``-O``: a silently-widened ladder gap is
    exactly the defect this exists to catch, and stripping the check under an
    optimize flag would defeat the point.
    """
    for previous, current in zip(ladder, ladder[1:]):
        ratio = current / previous
        if ratio > max_ratio:
            raise AssertionError(
                f"_REDOS_LADDER rung {current} is a {ratio:.2f}x jump from the "
                f"preceding rung {previous}, exceeding the {max_ratio}x growth bound "
                f"a single _blows_budget probe must stay within to remain bounded "
                f"(T-05-06). Add intermediate rungs instead of widening this jump."
            )


_validate_ladder_growth_bound(_REDOS_LADDER, _REDOS_LADDER_MAX_RATIO)


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
    completion and hang the very call this check exists to bound (T-05-06).

    That correction is only sound if the elapsed-time check actually gets a chance to
    fire BEFORE an unbounded probe — which means every rung of ``_REDOS_LADDER``, not
    just an early subset of them, must grow by a bounded ratio over the rung before it
    (enforced at import time by ``_validate_ladder_growth_bound``, against
    ``_REDOS_LADDER_MAX_RATIO``). With that invariant held throughout the whole
    ladder, an exponentially-growing pattern's per-rung cost rises by at most
    ``_REDOS_LADDER_MAX_RATIO`` between any two consecutive probes — so the probe that
    finally exceeds the budget is itself still bounded, and it is that probe's own
    bounded runtime, never a disproportionate jump to a much larger rung, that returns
    control to the caller (CR-01: a prior ladder shape violated this for a rung near
    the fine/coarse boundary and could hang indefinitely).
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
    this is a free function, not a stateful class). Every entry — regardless of
    ``skip_redos_check`` — first has its ``replacement`` template validated against its
    own ``pattern``'s group count: a malformed template (e.g. a backreference to a
    capture group that does not exist) is a consumer wiring bug that must surface here,
    not for the first time deep inside ``redact_secrets`` at a hot log call site with no
    runtime rescue. An entry whose ``skip_redos_check`` is True then skips both ReDoS
    checks (D-50's explicit, per-pattern opt-out). Every other entry is rejected if it
    looks structurally pathological OR blows the wall-clock budget against the
    adversarial corpus.

    On success, returns a NEW ``tuple(patterns)`` — a frozen collection positionally
    equal to the input, preserving order, keeping duplicates, and never sorting or
    deduplicating. This function reads and writes no module-level mutable state: two
    calls with different inputs never accumulate into one another, and repeated calls
    in any order and any test ordering (isolated or full-suite) produce independent
    results (SC2).
    """
    for index, rp in enumerate(patterns):
        try:
            # A trivial, empty probe is enough: `re.Pattern.sub` validates a
            # replacement template's backreferences eagerly, at template-compile
            # time, before it ever attempts a match — so this raises `re.error` for a
            # malformed template regardless of whether the probe text matches
            # `rp.pattern` (WR-01). Never echoes `rp.pattern.pattern`: the message
            # names the entry by INDEX only, same convention as the ReDoS rejection
            # below (PR-02, T-05-02).
            rp.pattern.sub(rp.replacement, "")
        except re.error as exc:
            raise ValueError(
                f"RedactionPattern at index {index} rejected at registration — its "
                f"replacement template is malformed against its pattern's capture "
                f"groups: {exc}"
            ) from exc
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
