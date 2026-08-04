"""``RedactingWriter`` — the load-bearing, renderer-agnostic redaction backstop (PC-01).

This is what makes REDACT-04's promise true. It wraps any file-like ``target`` and
intercepts the FULLY RENDERED text a renderer hands it — event fields and any formatted
traceback fused into ONE payload — so coverage does not depend on which processor chain
or which renderer produced that text (D-54). The optional structlog processor
(``redact/processor.py``) scrubs ``event_dict`` string values BEFORE render and is real,
additive defense-in-depth, but it structurally cannot see a traceback a self-rendering
renderer (e.g. ``structlog.dev.ConsoleRenderer``) formats straight into its own output
buffer — this sink is what catches that case regardless.

D-54 names exactly two wirings for this one class. The hub performs NEITHER of them —
that is always the consumer's own composition-root line of code, never something this
module does on its own initiative (a library silently mutating process-wide state is
exactly what D-53 forbids):

1. **Required** — pass an instance as structlog's render target:
   ``structlog.PrintLoggerFactory(file=RedactingWriter(sys.stderr, patterns))``.
2. **Optional, broader** — the consumer assigns
   ``sys.stderr = RedactingWriter(sys.stderr, patterns)`` in their own composition
   root, EARLY (before constructing any stdlib ``logging`` handler), picking up
   stdlib-``logging`` records, stray ``print()``, and third-party library output for
   free — zero extra hub code, because this class already has to wrap an arbitrary
   file-like target to satisfy recipe 1.

Non-``str``/``bytes`` triage (D-52) lives HERE, not inside ``redact_secrets`` — that
function stays a pinned, strict ``str -> str`` transform. This module declares no
import edge to ``structlog`` or to any sibling ``yahir_reusable_bot`` subpackage: the
backstop is pure file-like duck typing, which is exactly what makes it usable against
any write target, not only a structlog render target.
"""

from __future__ import annotations

import re
import threading
from collections.abc import Callable, Iterable, Sequence

from yahir_reusable_bot.redact.core import RedactionPattern, redact_secrets

# D-56's fixed, non-secret dry-run sentinel. Self-describing in any accidental sighting
# so an operator who spots it in output immediately knows it is not a real leak.
_PROBE_TEXT = "redaction-self-check-probe-not-a-secret"

# WR-03's fail-closed placeholder (see `write`'s docstring, point 2a): forwarded
# INSTEAD of the original payload when a hand-built, unregistered, malformed
# `RedactionPattern` makes `redact_secrets` itself raise `re.error`. Self-describing
# and echoes neither the withheld text nor any pattern source, so an operator who
# spots it immediately understands why the original line is missing.
_MALFORMED_PATTERN_PLACEHOLDER = (
    "[yahir_reusable_bot.redact: a malformed RedactionPattern raised during "
    "redaction — original text withheld to avoid an unproven, possibly "
    "unredacted write]"
)


class RedactingWriter:
    """Wraps ANY file-like ``target``; scrubs every write before forwarding.

    Renderer-agnostic BY CONSTRUCTION: this class never inspects an ``event_dict`` — it
    only ever sees the text a renderer (or a stdlib ``logging`` handler, or a bare
    ``print()``) has already produced. That single property is what lets one class
    satisfy both of D-54's wirings.
    """

    def __init__(
        self,
        target: object,
        patterns: Sequence[RedactionPattern],
        *,
        enabled: bool = True,
        on_redaction: Callable[[int], None] | None = None,
    ) -> None:
        """Store the wiring; read no ambient process state.

        ``enabled`` (D-53) is the explicit, keyword-only disablement parameter and
        defaults to redaction ON. This class never reads an environment variable or any
        other ambient process-level flag to decide whether it runs — a security
        backstop that defaults to off, or that can be switched off invisibly, is not a
        backstop.

        ``on_redaction`` (D-57) is an optional push hook, off by default. When
        supplied, it fires from inside :meth:`write`'s guarded increment (see there for
        the swallow-and-continue contract, D-52).
        """
        self._target = target
        self._patterns = patterns
        self._enabled = enabled
        self._on_redaction = on_redaction
        self._lock = threading.Lock()  # D-59: a real lock, not GIL-era int += atomicity
        self._count = 0

    def write(self, data: object) -> int:
        """Scrub ``data`` if it is (or decodes to) text, then forward it.

        D-52 triage, in exactly this order:

        1. ``bytes``, ``bytearray``, and ``memoryview`` are all decoded UTF-8 with
           ``errors="replace"`` — every buffer-protocol payload, not only ``bytes``
           itself (``isinstance(bytearray(b"x"), bytes)`` is ``False``, so a
           ``bytes``-only check would let a ``bytearray``/``memoryview`` payload
           bypass redaction entirely) — but ONLY when redaction is enabled AND the
           pattern set is non-empty, i.e. only when substitution is actually about
           to run. A disabled or unpatterned writer never decodes a bytes-like
           payload at all, so it reaches point 3 below as the exact original object,
           never a newly decoded ``str`` copy (which would also raise ``TypeError``
           against a real binary-mode target). An undecodable payload must never
           raise inside logging, which could mask the very error being logged.
        2. Only if the payload is now a ``str`` AND redaction is enabled AND the
           pattern set is non-empty does substitution run — delegated to
           :func:`yahir_reusable_bot.redact.core.redact_secrets` in exactly one call;
           this method never re-implements the scrub loop.

           2a. WR-03 guard: ``redact_secrets``'s own contract (``core.py``) promises
               no raise only for a WELL-FORMED, ``register_patterns``-vetted
               pattern — a hand-built, unregistered ``RedactionPattern`` (e.g. a
               replacement template referencing an out-of-range group) is out of
               that contract and can still raise ``re.error``. This call is guarded:
               on ``re.error`` the ORIGINAL payload is never forwarded (an unproven
               payload might still carry the very secret redaction exists to catch)
               and the exception never propagates (which would break the caller's
               hot logging call — precisely the failure mode this module otherwise
               guards against for ``on_redaction`` just below). Instead a fixed,
               non-secret placeholder is written in its place: this method fails
               CLOSED, not open. The redaction counter is not incremented and
               ``on_redaction`` does not fire for this path — no substitution
               actually happened, only a withholding.
        3. Every other path — not text, redaction off, or an empty pattern set —
           forwards the payload to the target UNTOUCHED and BY IDENTITY. This holds
           for a ``bytes``/``bytearray``/``memoryview`` payload too: point 1's decode
           is skipped entirely in this case, so identity is preserved.

        D-58: the redaction counter counts CHANGED WRITES, not individual
        substitutions. Comparing the scrubbed result to the input with one ``!=`` on
        two strings already held in memory is the whole counting mechanism —
        deliberately NOT re-running patterns with a counting substitution (``.subn()``)
        to obtain an exact per-substitution total, which would roughly double regex
        cost on every log line forever for a number nobody acts on per-substitution
        anyway (see the module-level counter's own docstring, D-58).

        The lock (D-59) guards only the increment and the captured read of the new
        count; the optional hook then runs OUTSIDE the lock, wrapped in a
        swallow-and-continue guard (D-52/D-57) so a raising or slow consumer hook can
        never break the logging path itself.

        Returns whatever the wrapped target's own ``write`` returned — never a
        fabricated length, so the caller learns how much actually reached the real
        destination.
        """
        if isinstance(data, (bytes, bytearray, memoryview)):
            if not (self._enabled and self._patterns):
                return self._target.write(data)
            data = bytes(data).decode("utf-8", "replace")
        if isinstance(data, str) and self._enabled and self._patterns:
            try:
                scrubbed = redact_secrets(data, self._patterns)
            except re.error:
                # WR-03 (see this method's own docstring, point 2a): a hand-built,
                # unregistered pattern is out of `redact_secrets`'s documented
                # contract and can raise here. Fail CLOSED — withhold the original
                # (possibly secret-bearing) payload rather than forward it
                # unredacted, and never let the exception itself reach the caller's
                # hot logging call.
                return self._target.write(_MALFORMED_PATTERN_PLACEHOLDER)
            if scrubbed != data:
                with self._lock:
                    self._count += 1
                    current = self._count
                hook = self._on_redaction
                if hook is not None:
                    try:
                        hook(current)
                    except Exception:  # noqa: BLE001 — never break the hot write path
                        pass
            return self._target.write(scrubbed)
        return self._target.write(data)

    def writelines(self, lines: Iterable[object]) -> None:
        """Route every line through :meth:`write` — NEVER delegated to the target.

        Once this writer stands in for ``sys.stderr`` (D-54 recipe 2), a delegated
        ``writelines`` would be a silent, total bypass of the entire backstop: any
        caller that reaches for the batch method instead of ``write`` would skip
        scrubbing entirely. Iterating and calling ``self.write`` for each item is what
        closes that leak path.
        """
        for line in lines:
            self.write(line)

    def flush(self) -> None:
        """Forward to the wrapped target."""
        self._target.flush()

    def __getattr__(self, name: str) -> object:
        """Delegate any attribute this class does not define to the wrapped target.

        This is what makes the writer a usable ``sys.stderr`` stand-in for callers that
        consult ``isatty``, ``fileno``, ``encoding`` and similar stream attributes.
        ``write``, ``writelines`` and ``flush`` are defined directly on this class and
        therefore never reach this hook. Any name beginning with an underscore raises
        ``AttributeError`` immediately, guarding against recursion from a lookup that
        occurs before this instance's own attributes (``_target`` in particular) are
        bound.
        """
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._target, name)

    @property
    def redaction_count(self) -> int:
        """The number of CHANGED writes so far (D-58) — not a substitution count.

        Monotonic for process lifetime: this value never resets or decreases while the
        instance lives. A consumer wanting a rate diffs two point-in-time reads of this
        property.
        """
        with self._lock:
            return self._count

    @property
    def enabled(self) -> bool:
        """Whether this instance was constructed with redaction on (D-53).

        Exists so a self-check or a consumer can distinguish "installed" from "active"
        without reaching into a private attribute.
        """
        return self._enabled

    def probe_redaction_path(self) -> None:
        """D-56's opt-in, in-memory-only deep dry-run — proves BEHAVIOUR, not wiring.

        Deliberately does NOT require ``_PROBE_TEXT`` to match a registered pattern —
        requiring a match would force every consumer to register a permanent canary
        pattern purely for self-checking, which nothing in this milestone asks for.
        Instead this method proves the scrub CODE PATH actually executes:

        - Raises ``ValueError`` when this writer is disabled — "installed" is not the
          same as "active".
        - Raises a DIFFERENTLY WORDED ``ValueError`` when the pattern set is empty —
          the precise gap introspection alone would miss (D-56's own stated example).
        - Otherwise runs :func:`redact_secrets` against the fixed probe text and
          returns ``None``.

        This method NEVER touches the wrapped target — no ``write``, no
        ``writelines``, no ``flush`` — which structurally eliminates the "can the
        canary leak?" failure mode: a broken backstop cannot make this probe itself
        emit anywhere. Neither raised message echoes the probe text, a scrubbed value,
        or raw pattern source.
        """
        if not self._enabled:
            raise ValueError(
                "probe_redaction_path: this RedactingWriter is disabled "
                "(enabled=False) — installed is not the same as active, so the "
                "dry-run scrub path cannot be proven to run"
            )
        if not self._patterns:
            raise ValueError(
                "probe_redaction_path: this RedactingWriter has an empty pattern "
                "set — there is nothing for the dry-run scrub to prove, which is "
                "exactly the silent-off state introspection alone would miss"
            )
        redact_secrets(_PROBE_TEXT, self._patterns)
