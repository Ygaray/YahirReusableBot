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
import typing
from typing import Callable

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


# -- SURF-02 (D-62): on_online annotation narrowing, get_type_hints enforcement ----- #


def test_on_online_annotation_is_narrowed_to_health_result():
    """``ReadyGate.__init__``'s ``on_online`` hint must equal ``on_fail``'s already-correct
    shape. RED pre-fix (verified live, RESEARCH.md § Pattern 4): the loose
    ``Callable[..., None] | None`` resolves to
    ``typing.Optional[typing.Callable[..., NoneType]]``, which does not equal the narrowed
    form below. WHY the narrowing is accurate, not merely stylistic: the hub always invokes
    the hook with exactly one argument — ``self._best_effort_hook(self._on_online, result,
    label="on_online")`` at ``ready_gate.py:135`` — so there is no variadic call shape in
    reality; the loose annotation was drift, and this assertion is the enforcement
    mechanism a static type checker would otherwise provide (this repo runs none, D-63)."""
    hints = typing.get_type_hints(ReadyGate.__init__)

    assert hints["on_online"] == Callable[[HealthResult], None] | None


def test_on_fail_annotation_is_unchanged():
    """Regression guard on the sibling: ``on_fail`` was ALREADY
    ``Callable[[HealthResult], None] | None`` before this plan touched anything, and this
    plan's edit narrows ``on_online`` TO match this shape rather than perturbing the
    sibling. GREEN both before and after Task 2's fix — proving the fix is additive to
    ``on_online`` alone."""
    hints = typing.get_type_hints(ReadyGate.__init__)

    assert hints["on_fail"] == Callable[[HealthResult], None] | None
