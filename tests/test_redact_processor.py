"""Regression suite for REDACT-05 — the optional, additive ``redaction_processor``:
its string-scrubbing behavior, its chain-order precondition and non-substitutability
warnings, the ``REDACTION_PROCESSOR_MARKER`` self-check opt-in, and the pinned
processor-only limitation (D-60, RESEARCH Pitfall 1).

Self-proof note (matching ``test_redact_sink.py``'s and ``test_redact_verify.py``'s
docstring convention): ``yahir_reusable_bot.redact.processor`` does not exist yet, so
EVERY assertion in this module is genuinely RED pre-fix — collection itself fails with
an ``ImportError`` before a single test body runs. There is no partial-pass baseline to
distinguish here; the entire file is the RED half of GATE-02's two-commit discipline.
"""

from __future__ import annotations

import unicodedata
import warnings

import pytest
import structlog

from yahir_reusable_bot.redact.core import RedactionPattern
from yahir_reusable_bot.redact.processor import redaction_processor
from yahir_reusable_bot.redact.sink import RedactingWriter
from yahir_reusable_bot.redact.verify import (
    REDACTION_PROCESSOR_MARKER,
    assert_redaction_active,
)

# The same fake sentinel key the rest of the phase uses (D-10 house convention: a
# module-level constant, not a fixture).
SENTINEL = "SENTINELKEY_do_not_leak_123"


class _CaptureDouble:
    """A hand-written file-like double accumulating EVERY ``write()`` call.

    Reused shape from ``test_redact_sink.py``/``test_redact_verify.py`` (RESEARCH
    Pitfall 2: one emission can span more than one ``write()`` call) — ``pieces``
    accepts any object, and ``all_output`` joins every accumulated piece so an
    assertion against it genuinely covers the whole emission.
    """

    def __init__(self) -> None:
        self.pieces: list[object] = []

    def write(self, data: object) -> int:
        self.pieces.append(data)
        return len(data) if isinstance(data, str) else len(str(data))

    def flush(self) -> None:
        pass

    @property
    def all_output(self) -> str:
        return "".join(p if isinstance(p, str) else str(p) for p in self.pieces)


@pytest.fixture(autouse=True)
def _reset_structlog_after_each_test():
    """Reset global structlog configuration after every test in this module — the
    same one-line teardown ``test_redact_sink.py``/``test_redact_verify.py``
    established, kept module-local rather than promoted to ``conftest.py`` (module
    independence beats DRY for a one-line teardown used by only one file)."""
    yield
    structlog.reset_defaults()


def test_processor_scrubs_string_event_values():
    """REDACT-05 / SC2: the returned processor scrubs every string ``event_dict``
    value pre-render. Called directly with a plain mapping — no structlog
    configuration is needed to exercise this unit-level case, since the returned
    closure is a plain callable following structlog's processor calling convention."""
    processor = redaction_processor((RedactionPattern.literal(SENTINEL),))
    event_dict = {"event": f"appid={SENTINEL}", "other": "safe"}

    result = processor(None, "info", event_dict)

    assert SENTINEL not in result["event"]
    assert "***" in result["event"]
    assert result["other"] == "safe"


def test_processor_leaves_non_string_values_untouched():
    """The processor must not "helpfully" coerce a non-``str`` value — coercing would
    change what a downstream renderer receives. An ``int``, ``None``, a nested
    ``dict``, a ``list``, and a live exception-info triple all come back by IDENTITY,
    proving none of them was stringified."""
    processor = redaction_processor((RedactionPattern.literal(SENTINEL),))
    nested = {"inner": "value"}
    items = [1, 2, 3]
    int_value = 7
    none_value = None
    try:
        raise ValueError("boom")
    except ValueError as exc:
        exc_info = (type(exc), exc, exc.__traceback__)
        event_dict = {
            "n": int_value,
            "none": none_value,
            "nested": nested,
            "items": items,
            "exc_info": exc_info,
        }
        result = processor(None, "info", event_dict)

    assert result["n"] is int_value
    assert result["none"] is None
    assert result["nested"] is nested
    assert result["items"] is items
    assert result["exc_info"] is exc_info


def test_processor_returns_the_same_mapping_object():
    """structlog's processor calling convention threads ONE mapping through the
    chain; returning a copy would silently discard mutations a later processor made
    in some chain shapes. The returned object must be the SAME object passed in."""
    processor = redaction_processor((RedactionPattern.literal(SENTINEL),))
    event_dict = {"event": f"appid={SENTINEL}"}

    result = processor(None, "info", event_dict)

    assert result is event_dict


def test_processor_with_no_patterns_is_an_exact_identity():
    """EDGE empty (REDACT-05): ``redaction_processor(())`` inherits the Phase-5
    silent-no-op contract (``redact_secrets`` returns text unchanged for a falsy
    pattern sequence) — every value comes back untouched, nothing raises, and nothing
    warns."""
    processor = redaction_processor(())
    event_dict = {"event": "anything at all"}

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = processor(None, "info", event_dict)

    assert result is event_dict
    assert event_dict == {"event": "anything at all"}


def test_processor_with_an_empty_mapping_returns_it_unchanged():
    """EDGE empty (REDACT-05), second half: an ``event_dict`` with zero entries comes
    back empty and by identity — the loop over zero items is a legitimate no-op."""
    processor = redaction_processor((RedactionPattern.literal(SENTINEL),))
    event_dict: dict[str, object] = {}

    result = processor(None, "info", event_dict)

    assert result is event_dict
    assert result == {}


def test_processor_matches_at_code_point_level_without_normalization():
    """EDGE encoding (REDACT-05): matching happens at Python ``str`` code-point level
    with no Unicode normalization and no case folding of its own — inherited
    documented contract from ``redact_secrets``, not a defect. An NFD-decomposed
    occurrence of an NFC-formed pattern is NOT masked."""
    composed = unicodedata.normalize("NFC", "café秘密" + SENTINEL)
    processor = redaction_processor((RedactionPattern.literal(composed),))

    composed_result = processor(None, "info", {"event": f"before {composed} after"})
    assert composed not in composed_result["event"]

    decomposed = unicodedata.normalize("NFD", composed)
    decomposed_result = processor(None, "info", {"event": f"before {decomposed} after"})
    assert decomposed in decomposed_result["event"]


def test_processor_does_not_decode_bytes_values():
    """EDGE encoding (REDACT-05), second half: the processor never decodes ``bytes``
    — a ``bytes`` value passes through as ``bytes``, BY IDENTITY. Non-text triage
    belongs to the sink seam (D-52); duplicating it here would create a second,
    drift-prone copy of a security-sensitive contract. ``RedactingWriter`` still
    catches this payload once it is rendered to text by a renderer downstream."""
    processor = redaction_processor((RedactionPattern.literal(SENTINEL),))
    raw = f"appid={SENTINEL}".encode()
    event_dict = {"event": raw}

    result = processor(None, "info", event_dict)

    assert result["event"] is raw
    assert isinstance(result["event"], bytes)


def test_processor_docstring_states_the_chain_order_precondition():
    """REDACT-05's literal ask, asserted mechanically — not left to editorial
    goodwill. Asserted against lowercase-normalised substrings so wording can evolve
    without this test becoming a spelling checker; the concepts asserted are: order,
    the exception-formatter dependency, and the not-sufficient-alone claim."""
    doc = (redaction_processor.__doc__ or "").lower()

    assert doc
    assert "order" in doc
    assert "exception" in doc
    assert "not sufficient" in doc


def test_processor_carries_the_self_check_marker():
    """The returned processor carries the published ``REDACTION_PROCESSOR_MARKER``
    attribute truthy, so ``assert_redaction_active`` discovers it by opt-in contract.
    Proves the second half end-to-end: a correctly wired sink, with the real
    processor placed BEFORE ``format_exc_info``, makes ``assert_redaction_active``
    emit a warning while still returning normally."""
    assert getattr(redaction_processor(()), REDACTION_PROCESSOR_MARKER, False)

    capture = _CaptureDouble()
    writer = RedactingWriter(capture, (RedactionPattern.literal(SENTINEL),))
    real_processor = redaction_processor((RedactionPattern.literal(SENTINEL),))
    structlog.configure(
        processors=[real_processor, structlog.processors.format_exc_info],
        logger_factory=structlog.PrintLoggerFactory(file=writer),
        cache_logger_on_first_use=False,
    )

    with pytest.warns(UserWarning):
        assert assert_redaction_active() is None


def test_processor_scrubs_a_formatted_traceback_when_ordered_after_the_exception_formatter():
    """The positive additive-value case: correctly ordered AFTER
    ``format_exc_info``, the processor DOES scrub a formatted traceback that has
    already been rendered into the event mapping. ``format_exc_info`` (unlike
    ``dict_tracebacks``, which nests the traceback as structured data rather than a
    flat string) renders the exception into a single ``event_dict["exception"]``
    string — the exact shape this processor's shallow, top-level scrub loop can
    reach. A PLAIN capture double is the file target (deliberately NO sink), so the
    scrubbing is attributed to the processor alone."""
    capture = _CaptureDouble()
    pattern = RedactionPattern.literal(SENTINEL)
    structlog.configure(
        processors=[
            structlog.processors.format_exc_info,
            redaction_processor((pattern,)),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=capture),
        cache_logger_on_first_use=False,
    )
    log = structlog.get_logger("t")
    try:
        raise ValueError(f"secret={SENTINEL}")
    except ValueError:
        log.exception("boom")

    assert SENTINEL not in capture.all_output
    # Traceback evidence really was rendered (and really was scrubbed), not just
    # never emitted at all.
    assert "ValueError" in capture.all_output


def test_processor_only_configuration_still_leaks_a_traceback_without_the_sink():
    """PINNED LIMITATION, reproducing RESEARCH Pitfall 1 live — a TRIPWIRE, NOT an
    endorsement (mirrors ``test_redact_core.py``'s "tripwire, NOT an endorsement"
    framing). A processor-only configuration (no ``RedactingWriter`` sink) with
    ``dev.ConsoleRenderer`` self-rendering the traceback into its own output buffer
    still leaks the secret, because the traceback never passes through
    ``event_dict`` as a string this processor can see. This is exactly WHY the sink
    is load-bearing, not a Phase-6 defect. If this test ever starts failing, the
    correct response is to investigate whether ``dev.ConsoleRenderer``'s behaviour
    changed — never to delete this test."""
    capture = _CaptureDouble()
    pattern = RedactionPattern.literal(SENTINEL)
    structlog.configure(
        processors=[
            redaction_processor((pattern,)),
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=capture),
        cache_logger_on_first_use=False,
    )
    log = structlog.get_logger("t")
    try:
        raise ValueError(f"secret={SENTINEL}")
    except ValueError:
        log.exception("boom")

    assert SENTINEL in capture.all_output
