"""The generic secret-redaction mechanism (PC-01).

Exports the pattern/replacement pair type a consumer registers its own secret
shapes against (:class:`RedactionPattern`, including its literal-value
constructor), the substitution loop that applies a sequence of them to
arbitrary rendered text (:func:`redact_secrets`), and the registration entry
(:func:`register_patterns`) that vets a consumer's patterns — a cheap
structural check plus a bounded wall-clock ReDoS probe — before freezing them
into an immutable collection. Every secret shape — what a key looks like, what
to replace it with — is injected by the consumer; this module assembles
nothing of its own and hardcodes no pattern.

This is a pure leaf subpackage: stdlib only in this phase, importing no sibling
``yahir_reusable_bot`` subpackage. The hub never wires this into a live logger on
its own and never reads ambient process state (an environment variable, a global
flag) to decide whether redaction runs — that wiring, and any disablement toggle,
is entirely the consumer's composition-root policy.
"""

from __future__ import annotations

from yahir_reusable_bot.redact.core import RedactionPattern, redact_secrets
from yahir_reusable_bot.redact.registry import register_patterns

__all__ = ["RedactionPattern", "redact_secrets", "register_patterns"]
