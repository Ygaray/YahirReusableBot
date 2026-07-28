"""Regression tests for SCHED-01 (H16): ``SchedulerEngine.remove`` forwards
straight to the host scheduler's ``remove_job`` with no idempotence contract —
a reconcile double-remove race (or a misfire-coalesce race) that hits an
already-gone job id raises the host scheduler's lookup-miss error (e.g.
APScheduler's ``JobLookupError``, which IS a ``KeyError`` subclass — verified
against apscheduler 3.x source, RESEARCH.md Common Pitfalls #2) straight out of
``remove``, crashing the host's reconcile loop instead of the intended no-op
success (D-38), analogous to ``Path.unlink(missing_ok=True)``.

Self-proof note (D-11, matching ``test_selfproof_*`` in
``tests/test_import_hygiene.py``): a test that only drives the present-id path
(``remove_job`` succeeds, ``removed`` records the id) passes IDENTICALLY
before and after the fix — that path was never broken. It is
``test_remove_is_idempotent_when_job_already_gone`` that is genuinely RED
pre-fix: pre-fix, ``remove`` has no ``try/except`` around
``self._scheduler.remove_job(job_id)``, so the fake's ``KeyError`` propagates
unchanged and the test fails with an unhandled ``KeyError`` instead of
observing a clean ``None`` return.
"""

from __future__ import annotations

import pytest

from yahir_reusable_bot.scheduler.engine import SchedulerEngine


class _FakeRawScheduler:
    """A minimal double for the host-injected scheduler ``SchedulerEngine``
    wraps. No mocking library (house style, ``tests/conftest.py``) — only the
    one method ``remove`` actually calls."""

    def __init__(self, raise_on_remove: bool = False) -> None:
        self.raise_on_remove = raise_on_remove
        self.removed: list[str] = []

    def remove_job(self, job_id: str) -> None:
        if self.raise_on_remove:
            # apscheduler's real JobLookupError IS a KeyError subclass.
            raise KeyError(f"No job by the id of {job_id} was found")
        self.removed.append(job_id)


def test_remove_is_idempotent_when_job_already_gone():
    """RED pre-fix: a fake whose remove_job raises KeyError (the
    JobLookupError shape) must not propagate out of remove() — SCHED-01/D-38
    requires a no-op success, not a raise."""
    fake = _FakeRawScheduler(raise_on_remove=True)
    engine = SchedulerEngine(fake)

    result = engine.remove("job-x")

    assert result is None, (
        "remove() must return None without raising when the host scheduler's "
        "remove_job signals an already-gone id via KeyError"
    )


def test_remove_forwards_present_id_removal():
    """GREEN pre/post-fix (self-proof control): a present id still forwards
    the removal to the host scheduler unchanged."""
    fake = _FakeRawScheduler(raise_on_remove=False)
    engine = SchedulerEngine(fake)

    engine.remove("job-x")

    assert fake.removed == ["job-x"], (
        "a present-id remove must still forward to the host scheduler's "
        "remove_job — the idempotent swallow must not also swallow real removals"
    )


def test_remove_is_idempotent_on_repeat():
    """The already-gone-id no-op must be stable on repeat — calling remove()
    twice against the same raising fake must succeed both times (SCHED-01
    idempotency edge, mirroring Path.unlink(missing_ok=True) called twice)."""
    fake = _FakeRawScheduler(raise_on_remove=True)
    engine = SchedulerEngine(fake)

    first = engine.remove("job-x")
    second = engine.remove("job-x")

    assert first is None
    assert second is None


def test_remove_does_not_mask_non_lookup_errors():
    """Narrow-swallow proof (D-38 vs LIFE-02's masked close): a NON-KeyError
    failure from remove_job must re-raise unchanged — only the lookup-miss
    KeyError is caught."""

    class _FakeRawSchedulerBroken:
        def remove_job(self, job_id: str) -> None:
            raise RuntimeError("host scheduler backend unavailable")

    engine = SchedulerEngine(_FakeRawSchedulerBroken())

    with pytest.raises(RuntimeError, match="host scheduler backend unavailable"):
        engine.remove("job-x")
