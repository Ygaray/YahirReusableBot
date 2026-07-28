"""Regression tests for LIFE-04 (H18): ``ReadyGate.run`` gains a first-class fatal
outcome (D-44/D-45/D-46) instead of overloading the ``stop`` Event for a fatal probe.

RED-first two-commit proof (D-13, matching ``tests/test_reload.py``'s convention): this
file is written and committed while it FAILS against pre-fix source — ``ReadyOutcome`` is
unimportable from ``yahir_reusable_bot.lifecycle`` and ``HealthResult`` rejects the
``fatal=`` kwarg. The very next commit lands the fix and turns this file green.

All doubles below are hand-written (no ``unittest.mock`` / ``pytest-mock`` per this
repo's standing convention, ``tests/conftest.py``). Stop doubles implement BOTH
``is_set()`` and ``wait()`` since ``ReadyGate.run`` calls both (unlike the shared
``fake_stop_event`` fixture in ``conftest.py``, which only implements ``.wait()``).
"""

from __future__ import annotations

import threading

from yahir_reusable_bot.lifecycle import ReadyGate, ReadyOutcome
from yahir_reusable_bot.lifecycle.health import HealthResult


class _NeverStopEvent:
    """Stop double: never asked to stop (``is_set()`` False), ``.wait()`` never blocks.

    Used for the ONLINE and FATAL outcome tests, where the loop must reach the
    health-check on its first (and only) pass without the loop's ``stop.wait()``
    re-probe path ever running.
    """

    def is_set(self) -> bool:
        return False

    def wait(self, timeout: float | None = None) -> bool:
        return False


class _NoReprobeStopEvent:
    """Stop double: ``is_set()`` False (loop enters), but ``.wait()`` RAISES if called.

    Proves the fatal short-circuit never reaches the ``stop.wait(interval)`` re-probe
    (D-46 — no re-probe on a fatal outcome).
    """

    def is_set(self) -> bool:
        return False

    def wait(self, timeout: float | None = None) -> bool:
        raise AssertionError("stop.wait() must not be called on the fatal short-circuit path")


class _ReprobeOnceStopEvent:
    """Stop double: ``is_set()`` False, ``.wait()`` records it was called then returns True.

    Used for the non-fatal failing-probe regression test — proves the severity-branch
    re-probe wait IS still reached (byte-identical-to-today behavior), then the loop
    breaks to SHUTDOWN via the True return.
    """

    def __init__(self) -> None:
        self.wait_calls: list[float | None] = []

    def is_set(self) -> bool:
        return False

    def wait(self, timeout: float | None = None) -> bool:
        self.wait_calls.append(timeout)
        return True


class _HookRecorder:
    """A hand-written call-counting/order-recording hook double.

    Appends ``label`` to a shared ``order`` list (for cross-hook ordering assertions)
    and increments its own ``calls`` counter (for exactly-once assertions).
    """

    def __init__(self, order: list[str], label: str) -> None:
        self._order = order
        self._label = label
        self.calls = 0

    def __call__(self, result: HealthResult) -> None:
        self.calls += 1
        self._order.append(self._label)


class _RecordingNotifier:
    """A hand-written notifier double: ``ready()`` appends to a shared order list."""

    def __init__(self, order: list[str]) -> None:
        self._order = order

    def ready(self) -> None:
        self._order.append("notifier.ready")


def test_online_probe_returns_online_outcome_preserves_ordering():
    order: list[str] = []
    on_online = _HookRecorder(order, "on_online")
    notifier = _RecordingNotifier(order)
    gate = ReadyGate(
        health_check=lambda: HealthResult(ok=True, reason="ok"),
        notifier=notifier,
        on_online=on_online,
    )

    outcome = gate.run(_NeverStopEvent())

    assert outcome is ReadyOutcome.ONLINE
    assert order == ["on_online", "notifier.ready"]
    assert on_online.calls == 1


def test_fatal_probe_returns_fatal_outcome_no_reprobe():
    gate = ReadyGate(
        health_check=lambda: HealthResult(
            ok=False, reason="boom", detail="x", fatal=True
        ),
        notifier=_RecordingNotifier([]),
    )

    outcome = gate.run(_NoReprobeStopEvent())

    assert outcome is ReadyOutcome.FATAL


def test_fatal_probe_fires_on_fail_not_on_online():
    order: list[str] = []
    on_online = _HookRecorder(order, "on_online")
    on_fail = _HookRecorder(order, "on_fail")
    gate = ReadyGate(
        health_check=lambda: HealthResult(
            ok=False, reason="boom", detail="x", fatal=True
        ),
        notifier=_RecordingNotifier([]),
        on_online=on_online,
        on_fail=on_fail,
    )

    outcome = gate.run(_NoReprobeStopEvent())

    assert outcome is ReadyOutcome.FATAL
    assert on_fail.calls == 1
    assert on_online.calls == 0
    assert order == ["on_fail"]


def test_non_fatal_failure_still_reprobes():
    order: list[str] = []
    on_fail = _HookRecorder(order, "on_fail")
    stop = _ReprobeOnceStopEvent()
    gate = ReadyGate(
        health_check=lambda: HealthResult(ok=False, reason="degraded"),
        notifier=_RecordingNotifier([]),
        on_fail=on_fail,
    )

    outcome = gate.run(stop)

    assert outcome is ReadyOutcome.SHUTDOWN
    assert on_fail.calls == 1
    assert stop.wait_calls == [gate._re_probe_interval]


def _unreachable_health_check() -> HealthResult:
    raise AssertionError("health_check must not be called when stop is already set")


def test_stop_set_returns_shutdown_outcome():
    stop = threading.Event()
    stop.set()
    gate = ReadyGate(
        health_check=_unreachable_health_check,
        notifier=_RecordingNotifier([]),
    )

    outcome = gate.run(stop)

    assert outcome is ReadyOutcome.SHUTDOWN


def test_only_online_is_truthy():
    assert bool(ReadyOutcome.ONLINE) is True
    assert bool(ReadyOutcome.SHUTDOWN) is False
    assert bool(ReadyOutcome.FATAL) is False


def test_health_result_fatal_defaults_false():
    result = HealthResult(ok=False, reason="x")

    assert result.fatal is False
