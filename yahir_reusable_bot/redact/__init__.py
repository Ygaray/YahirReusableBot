"""The generic secret-redaction mechanism (PC-01).

Exports the pattern/replacement pair type a consumer registers its own secret
shapes against (:class:`RedactionPattern`, including its literal-value
constructor), the substitution loop that applies a sequence of them to
arbitrary rendered text (:func:`redact_secrets`), the registration entry
(:func:`register_patterns`) that vets a consumer's patterns — a cheap
structural check plus a bounded wall-clock ReDoS probe — before freezing them
into an immutable collection, and :class:`RedactingWriter` (Phase 6, PC-01) —
the load-bearing, renderer-agnostic sink a consumer wires into their own
``structlog`` render target and/or ``sys.stderr`` (D-54) to make the scrubbing
mechanism actually run against live log output. Every secret shape — what a
key looks like, what to replace it with — is injected by the consumer; this
module assembles nothing of its own and hardcodes no pattern.

This is a pure leaf subpackage: ``core.py``, ``registry.py`` and ``sink.py``
are stdlib only, importing no sibling ``yahir_reusable_bot`` subpackage.
(Sibling plans 06-02/06-03 extend this enumeration with ``verify.py`` and
``processor.py``, the only modules under this package permitted to import
``structlog``.) The hub never wires this into a live logger on its own and
never reads ambient process state (an environment variable, a global flag) to
decide whether redaction runs — that wiring, and any disablement toggle, is
entirely the consumer's composition-root policy.
"""

from __future__ import annotations

from yahir_reusable_bot.redact.core import RedactionPattern, redact_secrets
from yahir_reusable_bot.redact.registry import register_patterns
from yahir_reusable_bot.redact.sink import RedactingWriter

__all__ = [
    "RedactionPattern",
    "redact_secrets",
    "register_patterns",
    "RedactingWriter",
]
