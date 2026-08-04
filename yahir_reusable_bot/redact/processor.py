"""``redaction_processor`` — the OPTIONAL, ADDITIVE half of the structlog insertion
seam (REDACT-05, PC-01). ``RedactingWriter`` (``sink.py``) is the load-bearing
backstop; this processor scrubs ``event_dict`` string values BEFORE render, which is
genuinely valuable for a structured-log consumer but can never replace the sink — a
renderer that formats a traceback directly into its own output buffer (RESEARCH
Pitfall 1) bypasses this seam entirely regardless of where it sits in the processors
chain.

D-60 records why the chain-order precondition lives in this module's own docstring
plus a WARN-ONLY self-check (:func:`yahir_reusable_bot.redact.verify.assert_redaction_active`)
rather than a hard guard: the sink already catches every traceback unconditionally
regardless of processor order, so a mis-ordered *optional, additive* processor is
reduced defense-in-depth, not a security regression. A hard startup crash over a
component the ROADMAP explicitly says can be dropped under scope pressure would be
disproportionate.

**Rejected alternative — a chain-builder helper returning a pre-ordered processors
list.** This would give the strongest guarantee, but to genuinely place the processor
"after the exception formatters" it must know which renderer and which formatter the
consumer chose — that annexes composition-root policy no matter how the "it only
returns, it never configures" framing is worded. Revisit only if REDACT-05 stops being
optional in a later milestone (D-60).

This is the second and last module under ``redact/`` permitted to import ``structlog``
(the other is ``verify.py``, plan 06-02); it imports no sibling ``yahir_reusable_bot``
subpackage.
"""

from __future__ import annotations

from collections.abc import Callable, MutableMapping, Sequence

from yahir_reusable_bot.redact.core import RedactionPattern, redact_secrets
from yahir_reusable_bot.redact.verify import REDACTION_PROCESSOR_MARKER


def redaction_processor(
    patterns: Sequence[RedactionPattern],
) -> Callable[[object, str, MutableMapping[str, object]], MutableMapping[str, object]]:
    """Return a standard-signature structlog processor scrubbing string
    ``event_dict`` values pre-render (REDACT-05).

    ⚠ CHAIN-ORDER PRECONDITION. Place this AFTER any exception formatter —
    ``structlog.processors.format_exc_info`` / ``structlog.processors.dict_tracebacks``,
    or any other ``structlog.processors.ExceptionRenderer`` instance — in your
    ``processors=[...]`` list, or it will never see traceback text: until an
    exception formatter runs, ``exc_info`` is still a live
    ``(type, value, traceback)`` tuple, not a string. Both shipped formatters named
    above are instances of that one public renderer class, so a reader can check
    their own chain against it.

    ⚠ NOT SUFFICIENT ALONE, even correctly ordered. Some renderers (e.g.
    ``structlog.dev.ConsoleRenderer``) format exception information directly into
    their own output buffer, bypassing ``event_dict`` entirely regardless of where
    this processor sits in the chain (RESEARCH Pitfall 1, reproduced live and pinned
    by this module's own test suite). ``RedactingWriter`` (``redact/sink.py``) is
    the load-bearing backstop; this processor is additive defense-in-depth for a
    consumer who wants field-level scrubbing before serialization — never a
    replacement. This warning is not decoration: it is the mitigation for this
    phase's transparency prohibition (a consumer must never come to believe
    processor-only coverage is complete), and it is asserted by a test.

    The returned closure takes structlog's three positional arguments (logger,
    method name, ``event_dict``), walks the mapping's items, and replaces every
    value that is a ``str`` with
    :func:`yahir_reusable_bot.redact.core.redact_secrets` — this function never
    re-implements substitution. It does not decode ``bytes`` (that triage belongs to
    the sink seam, D-52 — duplicating it here would be a second, drift-prone copy of
    a security-sensitive contract), does not touch keys, and does not coerce any
    other non-string value. It returns the SAME mapping object it was handed, never
    a copy, matching structlog's processor calling convention — some chain shapes
    would silently discard a later processor's mutation against a copy.

    The returned closure carries
    :data:`yahir_reusable_bot.redact.verify.REDACTION_PROCESSOR_MARKER` set truthy —
    this is how :func:`yahir_reusable_bot.redact.verify.assert_redaction_active`'s
    ordering self-check discovers this processor's position without importing it,
    which keeps that self-check shippable independently of this optional component,
    and lets a consumer's own hand-written redaction processor opt into the same
    check identically.
    """

    def _processor(
        logger: object, method_name: str, event_dict: MutableMapping[str, object]
    ) -> MutableMapping[str, object]:
        # Materialise the key list first (rather than iterate .items() while
        # reassigning): no key is ever added or removed here, so mutating in place
        # is already safe, but an explicit key list makes that safety visible
        # rather than relying on a reader re-deriving it.
        for key in list(event_dict):
            value = event_dict[key]
            if isinstance(value, str):
                event_dict[key] = redact_secrets(value, patterns)
        return event_dict

    # The published opt-in contract (D-60): setting this attribute is how the
    # ordering self-check discovers this processor's position in a processors chain
    # without importing this module — see verify.py's own comment on the same
    # constant. A consumer's own hand-written redaction processor opts into the
    # identical check by setting this same attribute on their own callable.
    setattr(_processor, REDACTION_PROCESSOR_MARKER, True)
    return _processor
