"""Regression suite for REDACT-04 and REDACT-08 — the load-bearing, renderer-agnostic
``RedactingWriter`` sink, its lock-guarded redaction counter, and the in-memory dry-run
probe (D-54 through D-59).

Self-proof note (matching ``test_redact_core.py``'s docstring convention):
``yahir_reusable_bot.redact.sink`` does not exist yet, so EVERY assertion in this module
is genuinely RED pre-fix — collection itself fails with an ``ImportError`` before a
single test body runs. There is no partial-pass baseline to distinguish here; the
entire file is the RED half of GATE-02's two-commit discipline.

Ported from the promotion source at
``/home/yahir/Projects/WeatherBot/weatherbot/__init__.py`` (``_LiveStderr``, lines
26-62) — the proven non-``str`` triage order this seam generalizes — and from
``06-RESEARCH.md``'s verified live reproductions against structlog 26.1.0 (Pitfalls
1-4, 6), which supply the adversarial traceback shape, the aggregating capture double,
the JSON boundary-class case, and the stderr-swap ordering this file proves.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import threading
import unicodedata

import pytest
import structlog

from yahir_reusable_bot.redact.core import RedactionPattern
from yahir_reusable_bot.redact.sink import RedactingWriter

# A fake sentinel key — the value that must never survive redaction anywhere in this
# module. The exact Phase-5 value (test_redact_core.py:30), reused rather than
# reinvented (D-10 house convention: a module-level constant, not a fixture).
SENTINEL = "SENTINELKEY_do_not_leak_123"


class _CaptureDouble:
    """A hand-written file-like double accumulating EVERY ``write()`` call.

    Load-bearing per RESEARCH Pitfall 2: one structlog emission can span more than one
    ``write()`` call (``PrintLoggerFactory`` calls it twice per emission — body, then a
    trailing ``"\\n"``). A double exposing only a ``.last_write`` attribute would be
    structurally incapable of proving a secret's absence; ``all_output`` joins every
    accumulated piece so an assertion against it genuinely covers the whole emission.

    ``pieces`` intentionally accepts any object, not only ``str`` — the non-text
    forwarding tests below write a raw, non-string payload directly to the writer and
    must observe it landing in this double BY IDENTITY, which a str-coercing append
    would destroy.
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
    """Reset global structlog configuration after every test in this module.

    A ``structlog.configure(...)`` call in one test is process-wide mutable state; left
    unreset it would leak into the next test in this file, or into any of the other 100+
    tests across the suite. Kept local to this file, not promoted to ``conftest.py`` —
    module independence beats DRY for a one-line teardown used by only one module.
    """
    yield
    structlog.reset_defaults()


def test_sink_scrubs_full_rendered_traceback():
    """REDACT-04 / SC1 (D-54, RESEARCH Pitfall 1): a ``logger.exception(...)`` rendered
    through ``dev.ConsoleRenderer`` with ZERO exception-formatting processors in the
    chain still comes out of the wrapped sink with the secret masked — asserted against
    the FULL captured output, never ``str(exc)`` alone. This is the exact case a
    processor-only design structurally cannot see: ``ConsoleRenderer`` self-renders a
    formatted traceback straight into its own output buffer, bypassing ``event_dict``
    entirely, regardless of processor order."""
    capture = _CaptureDouble()
    pattern = RedactionPattern.literal(SENTINEL)
    structlog.configure(
        processors=[structlog.dev.ConsoleRenderer(colors=False)],
        logger_factory=structlog.PrintLoggerFactory(
            file=RedactingWriter(capture, (pattern,))
        ),
        cache_logger_on_first_use=False,
    )
    log = structlog.get_logger("t")
    try:
        raise ValueError(f"secret={SENTINEL}")
    except ValueError:
        log.exception("boom", field=f"appid={SENTINEL}")

    assert SENTINEL not in capture.all_output
    # Traceback evidence really was rendered (and really was scrubbed), not just
    # never emitted at all.
    assert "ValueError" in capture.all_output


def test_sink_scrubbed_json_line_round_trips():
    """REDACT-04 / SC1 second half: a ``JSONRenderer``-produced line carrying the
    secret still parses with ``json.loads`` after redaction, and a neighbouring
    non-secret field survives verbatim. Uses a BOUNDARY-CLASS pattern rather than a
    literal containing a quote/backslash (RESEARCH Pitfall 3) — the delimiter-free
    sentinel keeps this test's structural claim (redaction doesn't break JSON syntax)
    from being conflated with the separate boundary-class-under-redaction concern."""
    capture = _CaptureDouble()
    pattern = RedactionPattern(
        pattern=re.compile(r'("appid": ")[^"]+', re.IGNORECASE),
        replacement=r"\1***",
    )
    structlog.configure(
        processors=[structlog.processors.JSONRenderer()],
        logger_factory=structlog.PrintLoggerFactory(
            file=RedactingWriter(capture, (pattern,))
        ),
        cache_logger_on_first_use=False,
    )
    structlog.get_logger("t").warning("leak", appid=SENTINEL, units="imperial")

    body = capture.pieces[0]
    assert SENTINEL not in body
    parsed = json.loads(body)  # must not raise
    assert parsed["units"] == "imperial"


def test_sink_aggregates_every_write_call_of_one_emission():
    """RESEARCH Pitfall 2, pinned as a live property rather than a comment: one
    ``PrintLoggerFactory`` emission spans MORE THAN ONE ``write()`` call. A test
    asserting on ``capture.pieces[0]`` alone would be structurally incapable of
    proving the secret's absence from the whole emission."""
    capture = _CaptureDouble()
    pattern = RedactionPattern.literal(SENTINEL)
    structlog.configure(
        processors=[structlog.dev.ConsoleRenderer(colors=False)],
        logger_factory=structlog.PrintLoggerFactory(
            file=RedactingWriter(capture, (pattern,))
        ),
        cache_logger_on_first_use=False,
    )
    structlog.get_logger("t").warning("leak", field=f"appid={SENTINEL}")

    assert len(capture.pieces) >= 2
    assert SENTINEL not in capture.all_output


def test_sink_stderr_recipe_scrubs_non_structlog_output(monkeypatch, capsys):
    """D-55, proving D-54 recipe 2: with ``RedactingWriter`` installed as
    ``sys.stderr`` BEFORE the stream handler is constructed (RESEARCH Pitfall 6 —
    ordering is the whole point), non-structlog output (a stdlib ``logging`` record
    and a bare ``print(..., file=sys.stderr)``) comes out scrubbed."""
    monkeypatch.setattr(
        sys, "stderr", RedactingWriter(sys.stderr, (RedactionPattern.literal(SENTINEL),))
    )

    # Constructed AFTER the swap: logging.StreamHandler() resolves sys.stderr at
    # construction time, not lazily on every write (Pitfall 6).
    logger = logging.getLogger("test_redact_sink_stderr_recipe")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    try:
        logger.info("stdlib-record appid=%s", SENTINEL)
        print(f"printed-line appid={SENTINEL}", file=sys.stderr)
    finally:
        logger.removeHandler(handler)
        handler.close()

    captured = capsys.readouterr().err
    assert SENTINEL not in captured
    assert "stdlib-record" in captured
    assert "printed-line" in captured


def test_sink_writelines_does_not_bypass_redaction():
    """This is the leak-closure test (RESEARCH T-06-06): delegating ``writelines`` to
    the wrapped target would open a silent bypass the moment the writer stands in for
    ``sys.stderr``. Every line must route through the scrubbing ``write`` path."""
    capture = _CaptureDouble()
    writer = RedactingWriter(capture, (RedactionPattern.literal(SENTINEL),))

    writer.writelines([f"line one appid={SENTINEL}", "line two, nothing secret"])

    assert SENTINEL not in capture.all_output
    assert writer.redaction_count == 1


def test_sink_decodes_bytes_before_scrubbing():
    """D-52: non-text triage lives at THIS seam, never inside ``redact_secrets``.
    ``bytes`` are decoded UTF-8 with ``errors='replace'`` before scrubbing, so an
    undecodable byte sequence never raises inside logging."""
    capture = _CaptureDouble()
    writer = RedactingWriter(capture, (RedactionPattern.literal(SENTINEL),))

    writer.write(f"appid={SENTINEL}".encode())
    assert isinstance(capture.pieces[0], str)
    assert SENTINEL not in capture.pieces[0]

    # Undecodable UTF-8 must not raise; the replacement-character path.
    writer.write(b"\xff\xfe not valid utf-8")
    assert isinstance(capture.pieces[1], str)


def test_sink_decodes_bytearray_and_memoryview_before_scrubbing():
    """WR-01 regression: ``bytearray`` and ``memoryview`` are buffer-protocol
    payloads, not instances of ``bytes`` (``isinstance(bytearray(b"x"), bytes)`` is
    ``False``), so an `isinstance(data, bytes)`-only triage lets a secret carried in
    either type reach the target completely unscrubbed. Both must be decoded and
    scrubbed exactly like a ``bytes`` payload."""
    capture = _CaptureDouble()
    writer = RedactingWriter(capture, (RedactionPattern.literal(SENTINEL),))

    writer.write(bytearray(f"appid={SENTINEL}".encode()))
    assert isinstance(capture.pieces[0], str)
    assert SENTINEL not in capture.pieces[0]

    writer.write(memoryview(f"appid={SENTINEL}".encode()))
    assert isinstance(capture.pieces[1], str)
    assert SENTINEL not in capture.pieces[1]


def test_sink_forwards_non_text_payload_untouched():
    """A payload that is neither ``str`` nor ``bytes`` is forwarded to the target
    UNTOUCHED and BY IDENTITY, nothing raises, and the count does not advance."""
    capture = _CaptureDouble()
    writer = RedactingWriter(capture, (RedactionPattern.literal(SENTINEL),))
    marker = object()

    writer.write(marker)

    assert capture.pieces[0] is marker
    assert writer.redaction_count == 0


def test_sink_empty_write_forwards_and_does_not_count():
    """EDGE empty (REDACT-04): ``write('')`` forwards the empty string, raises
    nothing, and leaves ``redaction_count`` unchanged. A write whose scrubbed output
    equals its input never increments the count either."""
    capture = _CaptureDouble()
    writer = RedactingWriter(capture, (RedactionPattern.literal(SENTINEL),))

    writer.write("")
    assert capture.pieces == [""]
    assert writer.redaction_count == 0

    writer.write("nothing secret in this line")
    assert writer.redaction_count == 0


def test_sink_matches_at_code_point_level_without_normalization():
    """EDGE encoding (REDACT-04): matching happens at Python ``str`` code-point level
    with no Unicode normalization and no case folding applied by the seam — this is
    documented contract inherited from ``redact_secrets``, not a defect. An
    NFD-decomposed occurrence of an NFC-formed pattern is NOT masked; a caller needing
    equivalence normalizes before writing."""
    composed = unicodedata.normalize("NFC", "café秘密" + SENTINEL)
    capture = _CaptureDouble()
    writer = RedactingWriter(capture, (RedactionPattern.literal(composed),))

    writer.write(f"before {composed} after")
    assert composed not in capture.pieces[-1]

    decomposed = unicodedata.normalize("NFD", composed)
    writer.write(f"before {decomposed} after")
    assert decomposed in capture.pieces[-1]


def test_sink_disabled_forwards_untouched_and_never_counts():
    """Disablement is an explicit constructor parameter (D-53); a writer constructed
    with redaction off forwards untouched and never counts. The default (parameter
    omitted) DOES scrub — proving the default is ON."""
    capture_off = _CaptureDouble()
    writer_off = RedactingWriter(
        capture_off, (RedactionPattern.literal(SENTINEL),), enabled=False
    )
    writer_off.write(f"appid={SENTINEL}")
    assert SENTINEL in capture_off.all_output
    assert writer_off.redaction_count == 0

    capture_on = _CaptureDouble()
    writer_on = RedactingWriter(capture_on, (RedactionPattern.literal(SENTINEL),))
    writer_on.write(f"appid={SENTINEL}")
    assert SENTINEL not in capture_on.all_output


def test_sink_disabled_or_unpatterned_forwards_bytes_by_identity():
    """WR-02 regression: the method's own docstring promises a ``not text,
    redaction off, or an empty pattern set`` write is forwarded ``UNTOUCHED and BY
    IDENTITY``. For a ``bytes`` payload that promise only holds if the disabled or
    unpatterned path never decodes it into a brand-new ``str`` object first — a
    disabled/unpatterned writer must hand the target the EXACT original ``bytes``
    object it was given, not a decoded copy (which would also raise ``TypeError``
    against a real binary-mode target)."""
    payload = f"appid={SENTINEL}".encode()

    capture_disabled = _CaptureDouble()
    writer_disabled = RedactingWriter(
        capture_disabled, (RedactionPattern.literal(SENTINEL),), enabled=False
    )
    writer_disabled.write(payload)
    assert capture_disabled.pieces[0] is payload

    capture_unpatterned = _CaptureDouble()
    writer_unpatterned = RedactingWriter(capture_unpatterned, ())
    writer_unpatterned.write(payload)
    assert capture_unpatterned.pieces[0] is payload


def test_sink_delegates_unknown_stream_attributes_to_target():
    """``__getattr__`` delegates attributes this class does not define to the wrapped
    target, proving the writer is a usable ``sys.stderr`` stand-in for callers that
    consult ``isatty``/``encoding``. ``write``, ``writelines`` and ``flush`` are the
    writer's OWN bound methods and are never delegated."""

    class _StreamDouble:
        encoding = "utf-8"

        def __init__(self) -> None:
            self.wrote: list[object] = []

        def write(self, data: object) -> int:
            self.wrote.append(data)
            return 0

        def writelines(self, lines: object) -> None:  # pragma: no cover - unused
            raise AssertionError("target.writelines must never be reached directly")

        def flush(self) -> None:
            pass

        def isatty(self) -> bool:
            return True

    target = _StreamDouble()
    writer = RedactingWriter(target, ())

    assert writer.isatty() is True
    assert writer.encoding == "utf-8"

    assert writer.write is not target.write
    assert writer.writelines is not target.writelines
    assert writer.flush is not target.flush


def test_telemetry_counts_changed_writes_and_is_monotonic():
    """REDACT-08 / D-58. A fresh writer reports 0; an unchanged write leaves 0; one
    changed write reports 1; a single write in which THREE occurrences are substituted
    still reports exactly 2 — one more, not three. This is the changed-writes
    contract, not a substitution count: a future reader must not "fix" it. The counter
    is monotonic — reading it twice never resets or decreases it."""
    capture = _CaptureDouble()
    writer = RedactingWriter(capture, (RedactionPattern.literal(SENTINEL),))

    assert writer.redaction_count == 0
    writer.write("nothing to see here")
    assert writer.redaction_count == 0
    writer.write(f"one {SENTINEL} here")
    assert writer.redaction_count == 1
    writer.write(f"{SENTINEL} {SENTINEL} {SENTINEL}")  # three substitutions, one write
    assert writer.redaction_count == 2

    first_read = writer.redaction_count
    second_read = writer.redaction_count
    assert first_read == second_read == 2


def test_telemetry_is_thread_safe_under_concurrent_writes():
    """D-59: N threads each performing M changed writes against ONE shared writer
    leave the count at exactly N*M — the increment is guarded by a ``threading.Lock``
    rather than relying on GIL-era atomicity. A ``threading.Barrier`` forces the
    threads to actually overlap rather than run serially."""
    capture = _CaptureDouble()
    writer = RedactingWriter(capture, (RedactionPattern.literal(SENTINEL),))
    thread_count = 8
    writes_per_thread = 200
    barrier = threading.Barrier(thread_count)

    def _worker() -> None:
        barrier.wait()
        for _ in range(writes_per_thread):
            writer.write(SENTINEL)

    threads = [threading.Thread(target=_worker) for _ in range(thread_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert writer.redaction_count == thread_count * writes_per_thread


def test_on_redaction_hook_receives_count_and_cannot_break_logging():
    """D-57 / D-52. A hook appending its argument receives the post-increment count
    values in order. A hook that raises does not propagate out of ``write``, the
    scrubbed text still reaches the target, and the count still advances. With no
    hook supplied (the default), nothing is called."""
    seen: list[int] = []
    capture = _CaptureDouble()
    writer = RedactingWriter(
        capture, (RedactionPattern.literal(SENTINEL),), on_redaction=seen.append
    )
    writer.write(f"{SENTINEL} one")
    writer.write(f"{SENTINEL} two")
    assert seen == [1, 2]

    def _boom(count: int) -> None:
        raise RuntimeError("hook exploded")

    capture_raising = _CaptureDouble()
    writer_raising = RedactingWriter(
        capture_raising, (RedactionPattern.literal(SENTINEL),), on_redaction=_boom
    )
    writer_raising.write(f"{SENTINEL} three")  # must not raise
    assert SENTINEL not in capture_raising.all_output
    assert writer_raising.redaction_count == 1

    capture_default = _CaptureDouble()
    writer_default = RedactingWriter(capture_default, (RedactionPattern.literal(SENTINEL),))
    writer_default.write(f"{SENTINEL} four")  # no hook supplied — nothing to call


def test_write_never_raises_and_never_leaks_on_a_malformed_hand_built_pattern():
    """WR-03 regression. ``core.py``'s own contract for ``redact_secrets`` is
    explicit that a hand-built, unregistered, malformed pattern (out of
    ``register_patterns``'s vetting contract) can raise ``re.error`` — e.g. a
    replacement template referencing an out-of-range group. ``verify.py``'s module
    docstring nonetheless asserts ``write()`` "never raises." This is the guard that
    makes that claim literally true: two failure modes are on the table and only one
    is acceptable — propagating the exception would break the caller's hot logging
    call (the precise failure mode this module otherwise guards against for
    ``on_redaction``); forwarding the payload untouched would silently emit text
    this writer could not prove was clean, defeating the backstop. The guard fails
    CLOSED: the write must not raise, AND the original (possibly secret-bearing)
    text must never reach the target un-redacted."""
    malformed = RedactionPattern(pattern=re.compile(r"(a)"), replacement=r"\2")
    capture = _CaptureDouble()
    writer = RedactingWriter(capture, (malformed,))

    result = writer.write(f"a secret appid={SENTINEL} a")  # must not raise

    assert isinstance(result, int)
    assert capture.pieces  # something was written — the write path was not skipped
    forwarded = capture.pieces[0]
    assert f"appid={SENTINEL}" not in forwarded
    assert SENTINEL not in forwarded


def test_probe_redaction_path_never_writes_to_target():
    """D-56 / open question 1. On an enabled writer with a non-empty pattern set,
    ``probe_redaction_path()`` returns ``None`` and the capture double's ``pieces``
    list is EMPTY afterwards — the mechanical proof that the deep check can never
    route a sentinel to real output."""
    capture = _CaptureDouble()
    writer = RedactingWriter(capture, (RedactionPattern.literal(SENTINEL),))

    assert writer.probe_redaction_path() is None
    assert capture.pieces == []


def test_probe_redaction_path_raises_on_empty_pattern_set():
    """This closes the exact gap D-56 names: introspection alone would pass with an
    empty pattern set; the probe must raise ``ValueError`` instead."""
    capture = _CaptureDouble()
    writer = RedactingWriter(capture, ())

    with pytest.raises(ValueError):
        writer.probe_redaction_path()


def test_probe_redaction_path_raises_when_disabled_and_never_echoes_a_value():
    """A wired but disabled writer raises ``ValueError`` from the probe ("installed"
    is not the same as "active"), and neither probe error message echoes the
    sentinel, a scrubbed value, or raw pattern source — the proof mechanism must never
    become its own leak path."""
    capture = _CaptureDouble()
    pattern = RedactionPattern.literal(SENTINEL)
    writer = RedactingWriter(capture, (pattern,), enabled=False)

    with pytest.raises(ValueError) as excinfo:
        writer.probe_redaction_path()

    message = str(excinfo.value)
    assert SENTINEL not in message
    assert pattern.pattern.pattern not in message


# ---------------------------------------------------------------------------
# REDACT-10 / D-01: the optional `on_error` hook on the fail-closed
# malformed-pattern branch (`sink.py`'s `except re.error` at :157-164).
#
# RED-first note: this whole group is genuinely RED pre-fix.
# `RedactingWriter.__init__` accepts no `on_error` keyword today, so every
# construction below raises `TypeError` on an unexpected keyword argument
# before a single assertion in any of these four tests runs.
#
# The malformed pattern used throughout is deliberately BOTH secret-bearing
# AND malformed: its compiled source IS the sentinel itself, and its
# replacement template references a capture group that does not exist, so it
# raises `re.error` on every write. `RedactionPattern.literal(SENTINEL)`
# cannot be used here — its replacement defaults to a well-formed value, so
# it never raises.
# ---------------------------------------------------------------------------


def _malformed_secret_bearing_pattern() -> RedactionPattern:
    return RedactionPattern(pattern=re.compile(re.escape(SENTINEL)), replacement=r"\2")


def test_on_error_hook_fires_with_the_error_when_a_malformed_pattern_raises():
    """The hook fires exactly once with the real `re.error`, and the fail-closed
    write behavior it observes is unperturbed: the placeholder still reaches the
    target, and neither the sentinel nor the original payload text does."""
    received: list[BaseException] = []
    capture = _CaptureDouble()
    writer = RedactingWriter(
        capture,
        (_malformed_secret_bearing_pattern(),),
        on_error=received.append,
    )

    result = writer.write(f"a secret appid={SENTINEL} a")

    assert isinstance(result, int)
    assert len(received) == 1
    assert isinstance(received[0], re.error)
    assert capture.pieces
    forwarded = capture.pieces[0]
    assert SENTINEL not in forwarded
    assert f"appid={SENTINEL}" not in forwarded


def test_on_error_payload_never_carries_the_secret_pattern_source():
    """Standing no-leak gate (T-08-02-01). Sweeps every string-valued attribute
    reachable via `dir(exc)` — not a hardcoded attribute name — so an attribute a
    future CPython release adds is covered too. A non-vacuity guard runs first so
    a gate that silently received nothing cannot pass."""
    received: list[BaseException] = []
    capture = _CaptureDouble()
    writer = RedactingWriter(
        capture,
        (_malformed_secret_bearing_pattern(),),
        on_error=received.append,
    )

    writer.write(f"a secret appid={SENTINEL} a")

    # Non-vacuity guard: the exception must have actually been delivered.
    assert len(received) == 1
    exc = received[0]
    assert str(exc) != ""

    assert SENTINEL not in str(exc), "the sentinel leaked via str(exc)"
    assert SENTINEL not in repr(exc), "the sentinel leaked via repr(exc)"
    for attr_name in dir(exc):
        if attr_name.startswith("__"):
            continue
        try:
            value = getattr(exc, attr_name)
        except AttributeError:
            continue
        if not isinstance(value, str):
            continue
        assert SENTINEL not in value, (
            f"the sentinel leaked via re.error attribute {attr_name!r}={value!r} — "
            "if this fires, the hub must stop forwarding the raw exception object "
            "to on_error and start forwarding an elided summary instead"
        )


def test_on_error_hook_that_raises_cannot_break_the_hot_write_path():
    """D-52 guard, mirroring `on_redaction`'s `_boom` template: a raising
    `on_error` callback is swallowed. `write()` still returns normally, the
    placeholder still reaches the target, and the sentinel never does."""
    capture = _CaptureDouble()

    def _boom(exc: re.error) -> None:
        raise RuntimeError("on_error hook exploded")

    writer = RedactingWriter(
        capture,
        (_malformed_secret_bearing_pattern(),),
        on_error=_boom,
    )

    result = writer.write(f"a secret appid={SENTINEL} a")  # must not raise

    assert isinstance(result, int)
    assert capture.pieces
    assert SENTINEL not in capture.all_output


def test_the_two_hooks_never_cross_fire_and_the_counter_ignores_the_malformed_path():
    """`on_redaction` and `on_error` are mutually exclusive per write: a
    successful redaction fires only `on_redaction` and advances the counter; a
    malformed-pattern withholding fires only `on_error` and the counter stays at
    0 (`write`'s docstring point 2a — no substitution actually happened)."""
    redaction_seen: list[int] = []
    error_seen: list[BaseException] = []
    capture_success = _CaptureDouble()
    writer_success = RedactingWriter(
        capture_success,
        (RedactionPattern.literal(SENTINEL),),
        on_redaction=redaction_seen.append,
        on_error=error_seen.append,
    )

    writer_success.write(f"{SENTINEL} one")

    assert redaction_seen == [1]
    assert error_seen == []
    assert writer_success.redaction_count == 1

    redaction_seen2: list[int] = []
    error_seen2: list[BaseException] = []
    capture_malformed = _CaptureDouble()
    writer_malformed = RedactingWriter(
        capture_malformed,
        (_malformed_secret_bearing_pattern(),),
        on_redaction=redaction_seen2.append,
        on_error=error_seen2.append,
    )

    writer_malformed.write(f"{SENTINEL} two")

    assert redaction_seen2 == []
    assert len(error_seen2) == 1
    assert writer_malformed.redaction_count == 0
