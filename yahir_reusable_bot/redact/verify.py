"""``assert_redaction_active`` — the wiring-time proof the Phase-6 backstop is not
merely present but actually installed and actually active (REDACT-07, D-56), plus the
warn-only processor-ordering sub-check D-60 folds into the same call.

This module reads the CONSUMER's live ``structlog`` configuration and never writes it.
Its raise happens at wiring time — before anything is serving — which is why this
module's fail-loud posture does not conflict with the degrade-don't-raise rule that
governs the write path itself (``RedactingWriter.write`` in ``sink.py`` never raises;
this module's own check, called once at boot or mid-run, does). The ordering sub-check
deliberately WARNS while the writer check RAISES — a reader must not mistake that
asymmetry for an inconsistency: D-60 records exactly why (the sink already catches
every traceback unconditionally regardless of processor order, so a mis-ordered
*optional, additive* processor is reduced defense-in-depth, not a security regression).

A backstop silently dropped by a second ``structlog.configure()`` call looks
byte-identical to a working one from the outside. This is the only mechanism in the
milestone that makes that difference observable, so its own failure mode matters more
than its success path: it must never return a passing result it cannot actually
justify. Every inconclusive introspection result — an unrecognised factory type, a
missing private attribute, a file target that isn't the hub's own writer, a writer
nested inside a consumer's own proxy — raises. There is no "unknown, assume fine" path.

This is one of exactly two modules under ``redact/`` permitted to import ``structlog``
(the other is ``processor.py``, plan 06-03) — everything else in this subpackage stays
stdlib only and imports no sibling ``yahir_reusable_bot`` subpackage.
"""

from __future__ import annotations

import warnings

import structlog

from yahir_reusable_bot.redact.sink import RedactingWriter

# The published opt-in contract (D-60): any callable in a processor chain that sets
# this attribute to a truthy value declares itself a redaction processor and will be
# considered by the ordering sub-check below. A CONSTANT, not a function identity, is
# the coupling point — this is what lets a consumer's own hand-written redaction
# processor participate, and what lets this module ship, build and test before
# `processor.py` (plan 06-03) exists: the sub-check never imports it.
REDACTION_PROCESSOR_MARKER = "_is_redaction_processor"

_RECOGNISED_FACTORY_TYPES = (structlog.PrintLoggerFactory, structlog.WriteLoggerFactory)


def assert_redaction_active(*, deep: bool = False) -> None:
    """Prove the hub's ``RedactingWriter`` is installed in the LIVE ``structlog``
    configuration (REDACT-07), and warn (never raise, D-60) if an optional redaction
    processor is present but mis-ordered relative to the exception formatters.

    Keyword-only ``deep`` so the call site reads unambiguously at a consumer's
    composition root. Order of operations, each its OWN distinguishable failure:

    1. Read the live configuration once. If the logger factory is not an instance of
       either ``structlog.PrintLoggerFactory`` or ``structlog.WriteLoggerFactory``,
       raise — naming the actual type and stating this introspection only knows how
       to read those two.
    2. If that factory does not expose the private ``_file`` attribute the shipped
       factories store their ``file=`` argument in, raise in its OWN wording — naming
       the installed structlog version. This branch exists because the dependency is
       pinned with a lower bound only (``structlog>=26.1.0``, no upper bound); a
       future release renaming this private attribute must surface here, distinctly,
       rather than being collapsed into "the consumer forgot to wire it" (RESEARCH
       Pitfall 5).
    3. If that file target is not an instance of ``RedactingWriter``, raise — naming
       the type actually found AND stating the fix for the nested-proxy case: wrap
       the stream with the hub's writer FIRST, then wrap that in any additional proxy
       the project needs. This is the deliberate hard raise of RESEARCH open question
       2 — no unwrap convention is built this phase; a consumer's own proxy nested
       around the writer is reported as a loud failure, never a false pass.
    4. When ``deep`` is set, delegate to the located instance's
       ``probe_redaction_path()`` and let its ``ValueError`` propagate — that method
       already owns the empty-pattern-set and disabled-writer cases and is proven
       never to touch the wrapped target, so this function adds no sentinel handling
       of its own.
    5. Call the ordering sub-check LAST, so a mis-ordered optional component can never
       pre-empt a genuine wiring failure with its own (non-raising) warning.

    Returns ``None`` on success. Emits no log line, performs no write, and mutates no
    configuration — the whole point is that this is safe to call at boot AND mid-run
    in production.
    """
    factory = structlog.get_config()["logger_factory"]
    if not isinstance(factory, _RECOGNISED_FACTORY_TYPES):
        raise ValueError(
            f"assert_redaction_active: the configured logger_factory is "
            f"{type(factory).__name__}, not PrintLoggerFactory or WriteLoggerFactory "
            f"— this introspection only knows how to read those two factory types"
        )
    if not hasattr(factory, "_file"):
        raise ValueError(
            f"assert_redaction_active: the installed structlog "
            f"{structlog.__version__}'s {type(factory).__name__} no longer exposes "
            f"the private `_file` attribute this introspection is coupled to — this "
            f"is a structlog implementation-detail change, not a consumer wiring "
            f"bug; revisit this module's introspection against the installed version"
        )
    target = factory._file
    if not isinstance(target, RedactingWriter):
        raise ValueError(
            f"assert_redaction_active: the configured logger_factory's file target "
            f"is {type(target).__name__}, not RedactingWriter. If RedactingWriter is "
            f"wrapped inside your own proxy, this check cannot see through it — wrap "
            f"your stream with RedactingWriter FIRST, then wrap that in any "
            f"additional proxy your project needs."
        )
    if deep:
        target.probe_redaction_path()
    _warn_if_processor_misordered()


def _warn_if_processor_misordered() -> None:
    """D-60: locate any processor in the live chain that opted in via
    ``REDACTION_PROCESSOR_MARKER`` and compare its position to the first recognised
    exception formatter. WARNS ONLY, never raises — the sink (``RedactingWriter``)
    already catches every traceback unconditionally regardless of processor order, so
    a mis-ordered *optional, additive* processor is reduced defense-in-depth, not a
    security regression.
    """
    processors = structlog.get_config()["processors"]
    marked_indices = [
        index
        for index, processor in enumerate(processors)
        if getattr(processor, REDACTION_PROCESSOR_MARKER, False)
    ]
    if not marked_indices:
        # A consumer who did not adopt the optional processor has nothing to be
        # warned about.
        return

    formatter_index = next(
        (
            index
            for index, processor in enumerate(processors)
            if isinstance(processor, structlog.processors.ExceptionRenderer)
        ),
        None,
    )
    if formatter_index is None:
        # A custom formatter this module does not recognise must produce an honest
        # unknown, never a false pass.
        warnings.warn(
            "assert_redaction_active: a redaction processor is present in the "
            "processors chain, but no recognised exception-formatter type "
            "(structlog.processors.ExceptionRenderer) was found — could not "
            "verify the redaction processor's position relative to traceback "
            "rendering",
            stacklevel=2,
        )
        return

    if min(marked_indices) < formatter_index:
        warnings.warn(
            "assert_redaction_active: a redaction processor is positioned before "
            "the exception formatter in the processors chain — it will never see "
            "traceback text, which is still a live (type, value, traceback) tuple "
            "at that point. Move the redaction processor AFTER the exception "
            "formatter (e.g. structlog.processors.format_exc_info / "
            "dict_tracebacks) for full defense-in-depth. RedactingWriter remains "
            "the load-bearing backstop regardless of this ordering.",
            stacklevel=2,
        )
