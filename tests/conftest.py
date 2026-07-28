"""Shared pytest fixtures for the hub's test suite.

This is the repo's FIRST `conftest.py`. That is an intentional, locked
convention change (Phase 1 CONTEXT.md D-09), not an oversight — the standing
`.planning/codebase/TESTING.md` documented "no conftest.py" and "no
`@pytest.fixture` decorators in use" as of 2026-07-08, and this file
supersedes both claims starting with Phase 1.

Per D-10 this file stays MINIMAL: it holds only what Phase 1's two regression
suites (`tests/test_retry.py`, `tests/test_identity.py`) actually need. It
grows when a real second caller appears — the same build-in-consumer-then-
promote discipline the ecosystem uses for production code (`ECOSYSTEM.md`
§6), applied here to test doubles. Do not add fixtures for `reload.py`,
`registry/`, `scheduler/`, or `panelkit` — those belong to Phases 2-4.

Both doubles below are hand-written synthetic objects, matching the rest of
the repo's test style: this repo uses no mocking library (no `pytest-mock`,
no `unittest.mock`).
"""
from __future__ import annotations

import pytest


class _InstantStopEvent:
    """A `threading.Event`-shaped double whose `.wait()` returns immediately.

    `build_retrying` (yahir_reusable_bot/reliability/retry.py:265) wires
    `sleep=stop_event.wait` as the LOCKED interruptible-sleep constraint — the
    entire two-burst schedule sleeps via this callable, never the blocking
    stdlib `time.sleep`. The production default `MID_PAUSE_S` is 2700 seconds;
    a real `threading.Event` here would make an exhaustion test actually sleep
    for 45 minutes. Returning `False` (not `True`) is the "not set" signal, so
    tenacity keeps scheduling the next attempt instead of abandoning the
    schedule early — the fake reproduces "never asked to stop", not "asked to
    stop immediately".
    """

    def wait(self, timeout: float | None = None) -> bool:
        return False


@pytest.fixture
def fake_stop_event() -> _InstantStopEvent:
    """A fresh `_InstantStopEvent` per test — the interruptible-sleep double."""
    return _InstantStopEvent()


@pytest.fixture
def cmdline_bytes():
    """A callable `(*parts: bytes) -> bytes` building a `/proc/<pid>/cmdline` buffer.

    Joins its byte arguments with `b"\\x00"` and appends a trailing `b"\\x00"`,
    reproducing the exact wire shape the kernel emits for `/proc/<pid>/cmdline`
    (NUL-separated argv, trailing NUL). This is what
    `yahir_reusable_bot.lifecycle.identity._argv_matches_marker` parses via
    `cmdline.split(b"\\x00")`, discarding the empty trailing part.
    """

    def _build(*parts: bytes) -> bytes:
        return b"\x00".join(parts) + b"\x00"

    return _build
