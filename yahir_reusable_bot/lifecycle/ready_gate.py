"""The ``ReadyGate`` — reusable systemd-readiness gate over an injected health-check.

The module-side generalization of the app daemon's startup gate (SEAM-05, D-01),
cloning the ``ReloadEngine`` recipe: constructor-injection + opaque passthrough +
symmetric best-effort hooks. It owns the genuinely-reusable, pitfall-dense triad a
reminder bot would otherwise re-hand-write:

- the interruptible ``while not stop.is_set()`` re-probe loop — it calls the
  INJECTED ``health_check`` on every pass, branches the startup log level on the
  NEUTRAL :class:`~yahir_reusable_bot.lifecycle.health.Severity` field of the
  returned :class:`HealthResult` (NEVER by comparing ``reason`` to an app string),
  and waits on ``stop.wait(interval)`` — NEVER ``time.sleep`` — so a ``systemctl
  stop`` mid-probe breaks promptly (Pitfall 2, T-25-02);
- the ``READY=1`` emit — the module owns ONLY ``notifier.ready()`` and a
  weather-noun-free structured online log; and

What the gate deliberately does NOT do (stays the app's / injected, D-02a): it
owns ZERO durable I/O. The durable health row, the heartbeat tick, and the online
ping all ride the injected best-effort ``on_online`` hook (invoked once on the
first pass) and the per-outcome ``on_fail`` hook (invoked on each failing probe).
A hook that raises is logged + swallowed and NEVER masks the gate result.

Heartbeat tick (D-01): this gate uses the sanctioned Option (d) — it does NOT
hold a scheduler handle. The app re-registers the ``__heartbeat__`` IntervalTrigger
tick via the existing ``SchedulerEngine.register(...)`` one-liner at the
composition root, so ``run_daemon`` stays byte-identical and the gate carries no
scheduler dependency.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable

import structlog

from .health import HealthResult, Severity

_log = structlog.get_logger(__name__)

# Startup self-check re-probe cadence (lifted from the app daemon, D-04). 120s:
# frequent enough that a recovered network / propagating credential recovers
# within ~2 min of becoming good, gentle enough it never approaches any upstream
# rate limit. A module default — an app may override per construction.
RE_PROBE_INTERVAL_S = 120


class ReadyOutcome(Enum):
    """The distinct terminal outcomes of :meth:`ReadyGate.run` (LIFE-04, D-44).

    Only :attr:`ONLINE` is truthy (the ``__bool__`` override below) so every
    existing ``if gate.run(stop):`` caller stays byte-compatible: both
    non-online outcomes (``SHUTDOWN``, ``FATAL``) evaluate falsy exactly like
    the old ``return False`` did. New/updated callers branch on identity
    instead (``outcome is ReadyOutcome.FATAL``) to distinguish a clean
    shutdown from a terminal probe failure without overloading the ``stop``
    Event.
    """

    ONLINE = "online"
    SHUTDOWN = "shutdown"
    FATAL = "fatal"

    def __bool__(self) -> bool:
        return self is ReadyOutcome.ONLINE


class ReadyGate:
    """Gate systemd ``READY=1`` on an injected health-check, re-probing until it passes.

    Construct with the ``health_check`` callable + a ``notifier`` (anything with a
    ``ready()`` method) positionally, and the optional hooks keyword-only. Drive by
    :meth:`run` with a ``threading.Event``-style ``stop``. The gate stores every
    collaborator by reference and invokes it opaquely — it never inspects the
    health result beyond ``ok`` and the neutral ``severity`` rung.
    """

    def __init__(
        self,
        health_check: Callable[[], HealthResult],
        notifier: Any,
        *,
        re_probe_interval: float = RE_PROBE_INTERVAL_S,
        on_online: Callable[..., None] | None = None,
        on_fail: Callable[[HealthResult], None] | None = None,
    ) -> None:
        self._health_check = health_check
        self._notifier = notifier
        self._re_probe_interval = re_probe_interval
        self._on_online = on_online
        self._on_fail = on_fail

    def run(self, stop) -> "ReadyOutcome":
        """Re-probe until the health-check passes, goes fatal, or ``stop`` is set.

        On EVERY non-ok outcome the per-outcome ``on_fail`` hook fires FIRST (the
        app stamps its durable health row there, D-02a) — unconditionally, fatal
        or not. Then, if ``result.fatal`` is True (LIFE-04, D-46), the gate logs a
        fatal event at ``critical`` and returns :attr:`ReadyOutcome.FATAL`
        IMMEDIATELY — no re-probe wait, ``on_online`` never fires (the gate never
        went online). Otherwise the startup log branches on the NEUTRAL
        ``result.severity`` rung — CRITICAL rung -> ``critical``, else
        ``warning`` — NEVER comparing ``reason`` to an app-named string, and the
        re-probe wait is the interruptible ``stop.wait(interval)`` (NEVER
        ``time.sleep``, Pitfall 2): it returns True if ``stop`` was set during the
        wait, so a shutdown mid-probe breaks promptly.

        Returns :attr:`ReadyOutcome.ONLINE` once the health-check first passes —
        at which point the gate fires the ``on_online`` hook (the app's
        health-row ``online`` stamp + tick + ping, D-02a), emits ``READY=1`` via
        ``notifier.ready()``, and logs the structured online event. Returns
        :attr:`ReadyOutcome.SHUTDOWN` if ``stop`` was set first (clean shutdown
        during the gate — the caller falls straight through without starting
        work or emitting the online signal). Returns :attr:`ReadyOutcome.FATAL`
        on a terminal probe failure (see above). Only ``ONLINE`` is truthy
        (:class:`ReadyOutcome`'s ``__bool__`` override), so an existing
        ``if gate.run(stop):`` caller stays byte-compatible for the non-fatal
        cases; a caller that cares about the fatal case branches on identity.
        """
        while not stop.is_set():
            result = self._health_check()
            if result.ok:
                # First pass: app side-effects ride on_online (D-02a); the module
                # owns ONLY the structured log + READY=1, at this exact point so the
                # emit ordering stays byte-identical.
                self._best_effort_hook(self._on_online, result, label="on_online")
                _log.info("bot online")
                self._notifier.ready()
                return ReadyOutcome.ONLINE
            # Per-outcome hook (the app's durable health row, D-02a) — fires on
            # EVERY failing probe, fatal or not.
            self._best_effort_hook(self._on_fail, result, label="on_fail")
            # NEW (LIFE-04, D-46): fatal short-circuit, after on_fail, before the
            # severity-branch log below — no re-probe wait, on_online never fires.
            if result.fatal:
                _log.critical(
                    "startup self-check fatal failure",
                    reason=result.reason,
                    detail=result.detail,
                )
                return ReadyOutcome.FATAL
            # Branch the startup log on the NEUTRAL severity rung, NOT a reason string.
            if result.severity >= Severity.CRITICAL:
                _log.critical(
                    "startup self-check critical failure",
                    reason=result.reason,
                    detail=result.detail,
                )
            else:
                _log.warning(
                    "startup self-check not ready",
                    reason=result.reason,
                    detail=result.detail,
                )
            # Interruptible re-probe wait: returns True if stop was set during the
            # wait -> clean shutdown (NEVER a blocking time.sleep, Pitfall 2).
            if stop.wait(self._re_probe_interval):
                break
        return ReadyOutcome.SHUTDOWN

    # ------------------------------------------------------------------ #
    # best-effort hook guard (cloned verbatim from ReloadEngine, D-09)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _best_effort_hook(
        hook: Callable[[Any], None] | None, arg: Any, *, label: str
    ) -> None:
        """Invoke an optional hook best-effort: a None hook is a no-op; a raise is swallowed.

        A hook failure is logged (outcome-only) and swallowed so it can NEVER mask
        the gate's own result — the online transition or the re-probe outcome.
        """
        if hook is None:
            return
        try:
            hook(arg)
        except Exception:  # noqa: BLE001 — best-effort; never mask the engine result
            _log.warning(f"{label} hook failed; engine result unaffected")
