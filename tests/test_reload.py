"""Regression tests for CFG-01 (H03): ``ReloadEngine.reload``'s PHASE-2 reconcile-failure
path rolls back the holder, re-runs the injected ``restore``, and re-raises — but never
fires the injected ``on_rejected`` hook, so the host's "reload rejected" alert is silently
skipped on this path (PHASE-1's validate-reject path fires it correctly).

Self-proof note (D-11, matching ``test_selfproof_*`` in ``tests/test_import_hygiene.py``):
a test that only asserts ``pytest.raises(RuntimeError)`` around a reconcile failure passes
IDENTICALLY before and after the fix — the ORIGINAL reconcile exception propagates either
way, so that half alone would prove nothing. It is the ``len(fired) == 1`` assertion on the
``on_rejected`` side-channel that is genuinely RED pre-fix: pre-fix, ``on_rejected`` is never
invoked on the PHASE-2 path, so ``fired`` stays empty and the assertion fails.
"""

from __future__ import annotations

import pytest

from yahir_reusable_bot.config.holder import ConfigHolder
from yahir_reusable_bot.config.reload import ReloadEngine


class _FakeSchedulerEngine:
    """Minimal scheduler-engine double: only ``list_live_ids()``/``remove()`` are ever
    called by ``ReloadEngine._reconcile()``. This test's injected ``register_jobs`` raises
    before ``remove()`` would be reached, so ``removed`` is recorded only defensively."""

    def __init__(self) -> None:
        self.removed: list[str] = []

    def list_live_ids(self) -> set[str]:
        return set()

    def remove(self, job_id: str) -> None:
        self.removed.append(job_id)


def test_reconcile_failure_fires_on_rejected_once_and_rolls_back():
    """A PHASE-2 reconcile failure (an injected ``register_jobs`` raise) must fire
    ``on_rejected`` EXACTLY ONCE with the reconcile exception, roll the holder back to
    ``old_cfg``, call the injected ``restore(old_cfg)``, and re-raise the ORIGINAL reconcile
    exception unmasked (D-16 both-levels: fire-count + rollback-state in the same test)."""
    old_cfg = "old_cfg_sentinel"
    new_cfg = "new_cfg_sentinel"
    holder = ConfigHolder(old_cfg)
    scheduler_engine = _FakeSchedulerEngine()

    reconcile_exc = RuntimeError("registrar exploded")

    def _validate(path):
        return new_cfg

    def _desired_jobs(cfg):
        return set()

    def _register_jobs(cfg):
        raise reconcile_exc

    restored: list[object] = []

    def _restore(cfg):
        restored.append(cfg)

    fired: list[Exception] = []

    def _on_rejected(exc):
        fired.append(exc)

    engine = ReloadEngine(
        holder,
        scheduler_engine,
        validate=_validate,
        desired_jobs=_desired_jobs,
        register_jobs=_register_jobs,
        restore=_restore,
        on_rejected=_on_rejected,
    )

    with pytest.raises(RuntimeError) as exc_info:
        engine.reload("dummy-path")

    assert exc_info.value is reconcile_exc, (
        "the ORIGINAL reconcile exception must propagate unmasked — the best-effort "
        "on_rejected hook can never replace it (_best_effort_hook swallows hook raises)"
    )
    assert len(fired) == 1, (
        "on_rejected must fire EXACTLY ONCE on the PHASE-2 reconcile-failure path; "
        "pre-fix it never fires at all, so fired stays empty"
    )
    assert fired[0] is reconcile_exc
    assert holder.current() == old_cfg, "the holder must be rolled back to old_cfg"
    assert restored == [old_cfg], "the injected restore must be called with old_cfg"
