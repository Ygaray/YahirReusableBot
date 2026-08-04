"""Regression suite for REDACT-07 — ``assert_redaction_active``, the wiring-time proof
that the Phase-6 backstop is not merely present but actually installed and actually
active, plus the D-60 warn-only processor-ordering sub-check it folds in (D-56, D-60).

Self-proof note (matching ``test_redact_sink.py``'s docstring convention):
``yahir_reusable_bot.redact.verify`` does not exist yet, so EVERY assertion in this
module is genuinely RED pre-fix — collection itself fails with an ``ImportError``
before a single test body runs. There is no partial-pass baseline to distinguish here;
the entire file is the RED half of GATE-02's two-commit discipline.
"""

from __future__ import annotations

import warnings

import pytest
import structlog

from yahir_reusable_bot.redact.core import RedactionPattern
from yahir_reusable_bot.redact.sink import RedactingWriter
from yahir_reusable_bot.redact.verify import (
    REDACTION_PROCESSOR_MARKER,
    assert_redaction_active,
)

# The same fake sentinel key the rest of the phase uses (D-10 house convention: a
# module-level constant, not a fixture).
SENTINEL = "SENTINELKEY_do_not_leak_123"


class _CaptureDouble:
    """A minimal, hand-written file-like double accumulating every ``write()`` call.

    No mocking library anywhere in this repo's suite (house convention) — a plain
    accumulating list is the whole mechanism.
    """

    def __init__(self) -> None:
        self.pieces: list[object] = []

    def write(self, data: object) -> int:
        self.pieces.append(data)
        return len(data) if isinstance(data, str) else len(str(data))

    def flush(self) -> None:
        pass


class _NoFileFactory(structlog.PrintLoggerFactory):
    """A ``PrintLoggerFactory`` subclass whose ``__init__`` deliberately never sets
    the private ``_file`` attribute the shipped factories store their ``file=``
    argument in. ``isinstance`` against ``PrintLoggerFactory`` still succeeds — only
    the attribute lookup fails. Simulates the dependency-upgrade drift RESEARCH
    Pitfall 5 warns about (the private-attribute coupling has no upper version pin)."""

    def __init__(self) -> None:  # noqa: D107 — deliberately does not call super().__init__
        pass


class _ProxyStream:
    """A trivial proxy nested AROUND a ``RedactingWriter``, exposing only
    ``write``/``flush`` — the exact shape ``assert_redaction_active`` structurally
    cannot see through (RESEARCH open question 2). WeatherBot's own lazy-``sys.stderr``
    -resolving wrapper is of exactly this kind."""

    def __init__(self, target: object) -> None:
        self._target = target

    def write(self, data: object) -> int:
        return self._target.write(data)

    def flush(self) -> None:
        self._target.flush()


@pytest.fixture(autouse=True)
def _reset_structlog_after_each_test():
    """Reset global structlog configuration after every test in this module — the
    same one-line teardown ``test_redact_sink.py`` established, kept module-local
    rather than promoted to ``conftest.py`` (module independence beats DRY for a
    one-line teardown used by only one file)."""
    yield
    structlog.reset_defaults()


def _marked_processor(logger, method_name, event_dict):
    """Stands in for the not-yet-built ``redaction_processor`` (plan 06-03) AND
    simultaneously proves the marker contract works for a consumer's own hand-written
    redaction processor: it opts into the ordering sub-check purely by setting
    ``REDACTION_PROCESSOR_MARKER`` on itself, never by identity or import."""
    return event_dict


setattr(_marked_processor, REDACTION_PROCESSOR_MARKER, True)


def _wire(processors, *, writer: object, factory_cls=structlog.PrintLoggerFactory) -> None:
    """Keep the ``structlog.configure(...)`` wiring detail in one place instead of
    repeating it across thirteen tests."""
    structlog.configure(
        processors=processors,
        logger_factory=factory_cls(file=writer),
        cache_logger_on_first_use=False,
    )


def test_assert_redaction_active_passes_when_the_writer_is_wired():
    """SC3 / D-56: the plain (introspection-only) call passes silently — returns
    ``None``, raises nothing, emits no warning, and writes nothing anywhere — when the
    hub's own writer is genuinely the live ``PrintLoggerFactory`` file target."""
    capture = _CaptureDouble()
    writer = RedactingWriter(capture, (RedactionPattern.literal(SENTINEL),))
    _wire([], writer=writer)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert assert_redaction_active() is None

    assert capture.pieces == []


def test_assert_redaction_active_passes_for_the_write_logger_factory_too():
    """Both shipped structlog factory types must be recognised, not just the one the
    consumer happens to use."""
    capture = _CaptureDouble()
    writer = RedactingWriter(capture, (RedactionPattern.literal(SENTINEL),))
    _wire([], writer=writer, factory_cls=structlog.WriteLoggerFactory)

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert assert_redaction_active() is None

    assert capture.pieces == []


def test_assert_redaction_active_raises_when_no_backstop_is_installed():
    """The baseline negative case: nothing at all is configured."""
    structlog.reset_defaults()
    with pytest.raises(ValueError):
        assert_redaction_active()


def test_assert_redaction_active_raises_after_a_reconfigure_drops_the_writer():
    """SC3 and RESEARCH Pitfall 7 — the headline scenario REDACT-07 exists for: the
    writer is wired and the check passes, then a SECOND ``structlog.configure()`` call
    (WeatherBot has two independent call sites) omits the writer. That second
    configuration produces unredacted logs with no error of its own — this is the only
    mechanism able to observe the difference."""
    capture = _CaptureDouble()
    writer = RedactingWriter(capture, (RedactionPattern.literal(SENTINEL),))
    _wire([], writer=writer)
    assert assert_redaction_active() is None

    _wire([], writer=_CaptureDouble())  # reconfigured WITHOUT the writer

    with pytest.raises(ValueError):
        assert_redaction_active()


def test_assert_redaction_active_raises_distinctly_for_an_unrecognised_factory_type():
    """The first of three distinct failure classes (Pitfall 5): a ``logger_factory``
    that is neither shipped factory type. A plain callable is enough to trigger it,
    and the raised message must name the offending type."""
    factory = lambda *args, **kwargs: None  # noqa: E731 — a plain callable is the point
    structlog.configure(
        processors=[], logger_factory=factory, cache_logger_on_first_use=False
    )

    with pytest.raises(ValueError) as excinfo:
        assert_redaction_active()

    assert type(factory).__name__ in str(excinfo.value)


def test_assert_redaction_active_raises_distinctly_when_the_private_file_attribute_is_absent():
    """The second distinct failure class (RESEARCH Pitfall 5): ``isinstance`` still
    succeeds (it genuinely IS a ``PrintLoggerFactory``) but the private ``_file``
    attribute this introspection is coupled to is absent — simulating the
    dependency-upgrade drift the unbounded version pin makes possible. The message
    must name the installed structlog version, not collapse into the "wrong writer
    type" branch."""
    structlog.configure(
        processors=[], logger_factory=_NoFileFactory(), cache_logger_on_first_use=False
    )

    with pytest.raises(ValueError) as excinfo:
        assert_redaction_active()

    assert structlog.__version__ in str(excinfo.value)


def test_assert_redaction_active_raises_distinctly_when_the_file_target_is_not_the_hub_writer():
    """The third distinct failure class: a correctly-typed factory whose file target
    is a plain double, not ``RedactingWriter``. The message must name the actual type
    it found."""
    target = _CaptureDouble()
    _wire([], writer=target)

    with pytest.raises(ValueError) as excinfo:
        assert_redaction_active()

    assert type(target).__name__ in str(excinfo.value)


def test_the_three_failure_messages_are_mutually_distinct():
    """The mechanical form of Pitfall 5's requirement: a maintainer debugging a raised
    check must be able to tell "the logging library changed" from "the consumer forgot
    to wire it" from "the factory type is unknown" — three DISTINCT messages, never a
    single collapsed one."""
    messages: list[str] = []

    structlog.configure(
        processors=[], logger_factory=lambda *a, **k: None, cache_logger_on_first_use=False
    )
    with pytest.raises(ValueError) as excinfo:
        assert_redaction_active()
    messages.append(str(excinfo.value))

    structlog.configure(
        processors=[], logger_factory=_NoFileFactory(), cache_logger_on_first_use=False
    )
    with pytest.raises(ValueError) as excinfo:
        assert_redaction_active()
    messages.append(str(excinfo.value))

    _wire([], writer=_CaptureDouble())
    with pytest.raises(ValueError) as excinfo:
        assert_redaction_active()
    messages.append(str(excinfo.value))

    assert len(set(messages)) == 3


def test_assert_redaction_active_raises_when_the_writer_is_nested_inside_a_proxy():
    """A PINNED LIMITATION, not a regression (RESEARCH open question 2, resolved in
    favour of the hard raise, assumption A1) — mirroring the "tripwire, NOT an
    endorsement" framing in ``tests/test_redact_core.py``. A consumer's own proxy
    nested AROUND ``RedactingWriter`` (WeatherBot's own lazy-``sys.stderr``-resolving
    wrapper is exactly this shape) defeats this introspection by design: a deliberate
    false negative, never a false pass. The message must not leave the consumer
    guessing — it states the fix (wrap with the hub writer FIRST, then any additional
    proxy)."""
    capture = _CaptureDouble()
    writer = RedactingWriter(capture, (RedactionPattern.literal(SENTINEL),))
    proxy = _ProxyStream(writer)
    _wire([], writer=proxy)

    with pytest.raises(ValueError) as excinfo:
        assert_redaction_active()

    assert "wrap" in str(excinfo.value).lower()


def test_deep_check_raises_on_an_empty_pattern_set():
    """This is exactly D-56's stated justification for having a deep mode at all: a
    writer constructed with an empty pattern sequence PASSES the default
    (introspection-only) call — proving the gap is real — and only the opt-in deep
    call raises."""
    capture = _CaptureDouble()
    writer = RedactingWriter(capture, ())
    _wire([], writer=writer)

    assert assert_redaction_active() is None
    with pytest.raises(ValueError):
        assert_redaction_active(deep=True)


def test_deep_check_raises_when_the_wired_writer_is_disabled():
    """Installed is not the same as active: a writer constructed with redaction
    switched off passes the default call and only the deep call catches it."""
    capture = _CaptureDouble()
    writer = RedactingWriter(
        capture, (RedactionPattern.literal(SENTINEL),), enabled=False
    )
    _wire([], writer=writer)

    assert assert_redaction_active() is None
    with pytest.raises(ValueError):
        assert_redaction_active(deep=True)


def test_deep_check_writes_nothing_to_the_configured_destination():
    """The mechanical proof that the deep check cannot become a leak path: with a
    healthy writer, the deep call completes and the capture double recorded ZERO
    writes."""
    capture = _CaptureDouble()
    writer = RedactingWriter(capture, (RedactionPattern.literal(SENTINEL),))
    _wire([], writer=writer)

    assert assert_redaction_active(deep=True) is None
    assert capture.pieces == []


def test_ordering_check_warns_and_never_raises():
    """The D-60 matrix, isolated per scoped block so the ordering result is never
    conflated with the writer result — a correctly wired writer underlies all four
    blocks, so a raise anywhere in this test would be a defect in the ordering
    sub-check, not in the writer's own wiring:

    (a) the marked processor placed BEFORE ``format_exc_info`` warns, and
        ``assert_redaction_active`` still returns normally;
    (b) placed AFTER ``format_exc_info`` emits NO warning;
    (c) present in a chain with NO recognised exception-formatter type emits a
        generic "could not verify order" warning — never a silent pass;
    (d) a chain with no marked processor at all emits no ordering warning at all —
        the sub-check has nothing to say about a consumer who did not opt in.

    Also asserts no warning message anywhere in this matrix — nor the writer's own
    output — contains ``SENTINEL`` or the compiled pattern's source text.
    """
    capture = _CaptureDouble()
    pattern = RedactionPattern.literal(SENTINEL)
    writer = RedactingWriter(capture, (pattern,))
    fmt = structlog.processors.format_exc_info
    collected: list[str] = []

    # (a) marked processor BEFORE the formatter — warns, never raises.
    _wire([_marked_processor, fmt], writer=writer)
    with pytest.warns(UserWarning) as record:
        assert assert_redaction_active() is None
    assert len(record) == 1
    collected.append(str(record[0].message))

    # (b) marked processor AFTER the formatter — silent, no warning at all.
    _wire([fmt, _marked_processor], writer=writer)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert assert_redaction_active() is None

    # (c) marked processor present, NO recognised exception-formatter type — warns
    # generically, never a silent pass.
    _wire([_marked_processor], writer=writer)
    with pytest.warns(UserWarning) as record:
        assert assert_redaction_active() is None
    assert len(record) == 1
    collected.append(str(record[0].message))

    # (d) no marked processor at all — the sub-check has nothing to say about a
    # consumer who never opted into the optional processor.
    _wire([fmt], writer=writer)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert assert_redaction_active() is None

    assert capture.pieces == []
    for message in collected:
        assert SENTINEL not in message
        assert pattern.pattern.pattern not in message
