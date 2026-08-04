"""The generic secret-redaction mechanism (PC-01).

Exports the pattern/replacement pair type a consumer registers its own secret
shapes against (:class:`RedactionPattern`, including its literal-value
constructor), the substitution loop that applies a sequence of them to
arbitrary rendered text (:func:`redact_secrets`), the registration entry
(:func:`register_patterns`) that vets a consumer's patterns — a cheap
structural check plus a bounded wall-clock ReDoS probe — before freezing them
into an immutable collection, :class:`RedactingWriter` (Phase 6, PC-01) — the
load-bearing, renderer-agnostic sink a consumer wires into their own
``structlog`` render target and/or ``sys.stderr`` (D-54) to make the scrubbing
mechanism actually run against live log output, and
:func:`assert_redaction_active` (Phase 6, PC-01, REDACT-07) — the wiring-time
proof that the backstop is not merely present but actually installed and
active, plus :data:`REDACTION_PROCESSOR_MARKER`, the published opt-in
attribute an optional redaction processor sets on itself to participate in
that proof's warn-only ordering sub-check (D-60). Every secret shape — what a
key looks like, what to replace it with — is injected by the consumer; this
module assembles nothing of its own and hardcodes no pattern.

This is a pure leaf subpackage with one enumerated exception: ``core.py``,
``registry.py`` and ``sink.py`` are stdlib only; ``verify.py`` is coupled to
the logging library (one of exactly two modules under this package permitted
to import ``structlog`` — the other is ``processor.py``, plan 06-03). No
module here imports a sibling ``yahir_reusable_bot`` subpackage. The hub never
wires this into a live logger on its own and never reads ambient process
state (an environment variable, a global flag) to decide whether redaction
runs — that wiring, and any disablement toggle, is entirely the consumer's
composition-root policy.
"""

from __future__ import annotations

from yahir_reusable_bot.redact.core import RedactionPattern, redact_secrets
from yahir_reusable_bot.redact.registry import register_patterns
from yahir_reusable_bot.redact.sink import RedactingWriter
from yahir_reusable_bot.redact.verify import (
    REDACTION_PROCESSOR_MARKER,
    assert_redaction_active,
)

__all__ = [
    "RedactionPattern",
    "redact_secrets",
    "register_patterns",
    "RedactingWriter",
    "assert_redaction_active",
    "REDACTION_PROCESSOR_MARKER",
]
