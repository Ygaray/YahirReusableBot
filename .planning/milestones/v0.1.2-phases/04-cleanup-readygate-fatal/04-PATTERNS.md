# Phase 4: Cleanup + ReadyGate fatal outcome - Pattern Map

**Mapped:** 2026-07-28
**Files analyzed:** 6 (4 modify, 2 new)
**Analogs found:** 6 / 6 (all self-analogs — every file's own current source is the analog; this
is a same-file evolution phase, not a new-module phase)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|---------------|
| `yahir_reusable_bot/lifecycle/ready_gate.py` | service (lifecycle engine) | event-driven (probe loop → outcome) | itself (current `ReadyGate.run`) | exact (in-place evolution) |
| `yahir_reusable_bot/lifecycle/health.py` | model (DTO) | transform (n/a, pure data) | itself (current `HealthResult`, `severity` field precedent) | exact (in-place evolution) |
| `yahir_reusable_bot/lifecycle/__init__.py` | config (package surface / `__all__`) | request-response (import surface) | itself (current `__all__` list) | exact |
| `yahir_reusable_bot/discord/__init__.py` | config (package surface / `__all__`) | request-response (import surface) | itself (current re-export idiom for `BotThread`/`build_client`/`PanelKit`/`SelectedContext`) | exact |
| `tests/test_ready_gate.py` | test | event-driven (probe-loop outcome assertions) | `tests/conftest.py` (`_InstantStopEvent`/`fake_stop_event`), `tests/test_import_hygiene.py`, `tests/test_reload.py` (RED-first two-commit convention) | role-match |
| SURF-01 import test (new or extension) | test | request-response (import-smoke) | `tests/test_import_hygiene.py` (import-surface assertion style) | role-match |

## Pattern Assignments

### `yahir_reusable_bot/lifecycle/ready_gate.py` (service, event-driven)

**Analog:** itself — `ReadyGate.run`, current source at `yahir_reusable_bot/lifecycle/ready_gate.py:72-119`.

**Imports pattern** (lines 30-38, unchanged — add nothing new; `ReadyOutcome` is defined in this
same module per research recommendation, so no new import needed here):
```python
from __future__ import annotations

from typing import Any, Callable

import structlog

from .health import HealthResult, Severity

_log = structlog.get_logger(__name__)
```

**Core pattern — current `run` body to evolve** (lines 72-119, byte-exact current source):
```python
def run(self, stop) -> bool:
    while not stop.is_set():
        result = self._health_check()
        if result.ok:
            self._best_effort_hook(self._on_online, result, label="on_online")
            _log.info("bot online")
            self._notifier.ready()
            return True
        self._best_effort_hook(self._on_fail, result, label="on_fail")
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
        if stop.wait(self._re_probe_interval):
            break
    return False
```

**Target diff (D-44/D-46 synthesis, from RESEARCH.md Pattern 3)** — insert `ReadyOutcome` enum
above the class (after `RE_PROBE_INTERVAL_S`, before `class ReadyGate:`, line 47), change the
return type annotation to `-> "ReadyOutcome"`, and rewrite the body:
```python
class ReadyOutcome(Enum):
    ONLINE = "online"
    SHUTDOWN = "shutdown"
    FATAL = "fatal"

    def __bool__(self) -> bool:
        return self is ReadyOutcome.ONLINE


class ReadyGate:
    ...
    def run(self, stop) -> "ReadyOutcome":
        while not stop.is_set():
            result = self._health_check()
            if result.ok:
                self._best_effort_hook(self._on_online, result, label="on_online")
                _log.info("bot online")
                self._notifier.ready()
                return ReadyOutcome.ONLINE                      # was: return True

            self._best_effort_hook(self._on_fail, result, label="on_fail")

            # NEW: fatal short-circuit — after on_fail, before the severity-branch log (D-46).
            if result.fatal:
                _log.critical(
                    "startup self-check fatal failure",
                    reason=result.reason,
                    detail=result.detail,
                )
                return ReadyOutcome.FATAL                        # no stop.wait() re-probe

            # Unchanged non-fatal severity-branch log (byte-identical to today).
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
            if stop.wait(self._re_probe_interval):
                break
        return ReadyOutcome.SHUTDOWN                             # was: return False
```
Requires adding `from enum import Enum` to the imports block (line 32 area, alongside
`from typing import Any, Callable`).

**Error handling pattern (unchanged, reused verbatim):** `_best_effort_hook`
(lines 125-139) — None-safe hook invoker; swallow-and-log-on-raise; never masks the gate result.
Reused as-is for the fatal path's `on_fail` call — no new error-handling code needed.

---

### `yahir_reusable_bot/lifecycle/health.py` (model, transform)

**Analog:** itself — `HealthResult` current source at
`yahir_reusable_bot/lifecycle/health.py:48-63`, specifically the `severity` field's additive-default
precedent (D-45 explicitly mirrors this).

**Current dataclass (verbatim, lines 48-63):**
```python
@dataclass(frozen=True)
class HealthResult:
    ok: bool
    reason: str
    detail: str = ""
    severity: Severity = Severity.WARNING
```

**Target diff (D-45) — append ONLY, after `severity` (last field, keeps dataclass field-ordering
rule satisfied: defaulted fields must trail non-defaulted ones):**
```python
@dataclass(frozen=True)
class HealthResult:
    ok: bool
    reason: str
    detail: str = ""
    severity: Severity = Severity.WARNING
    fatal: bool = False          # NEW — D-45, additive, defaults False
```
No import changes needed (`dataclass` already imported line 26).

---

### `yahir_reusable_bot/lifecycle/__init__.py` (config, request-response)

**Analog:** itself — current `__all__` at lines 27-36.

**Current (verbatim):**
```python
from .ready_gate import ReadyGate
...
__all__ = [
    "ReadyGate",
    "SystemdNotifier",
    "HealthResult",
    "Severity",
    "LifecycleIdentity",
    "is_running_process",
    "write_pid_atomic",
    "read_pid",
]
```

**Target diff (D-44) — import + `__all__` entry alongside `ReadyGate`:**
```python
from .ready_gate import ReadyGate, ReadyOutcome
...
__all__ = [
    "ReadyGate",
    "ReadyOutcome",
    "SystemdNotifier",
    "HealthResult",
    "Severity",
    "LifecycleIdentity",
    "is_running_process",
    "write_pid_atomic",
    "read_pid",
]
```

---

### `yahir_reusable_bot/discord/__init__.py` (config, request-response)

**Analog:** itself — the existing re-export idiom in the SAME file, verbatim current source
(lines 21-25):
```python
from yahir_reusable_bot.discord.gateway import BotThread, build_client
from yahir_reusable_bot.discord.panelkit import PanelKit
from yahir_reusable_bot.discord.selection import SelectedContext

__all__ = ["BotThread", "build_client", "PanelKit", "SelectedContext"]
```

**Target diff (D-47) — join `summon_panel` onto the existing gateway import line + `__all__`, no
new import line, no docstring change (docstring already correct per CONTEXT.md):**
```python
from yahir_reusable_bot.discord.gateway import BotThread, build_client, summon_panel
from yahir_reusable_bot.discord.panelkit import PanelKit
from yahir_reusable_bot.discord.selection import SelectedContext

__all__ = ["BotThread", "build_client", "PanelKit", "SelectedContext", "summon_panel"]
```

---

### `tests/test_ready_gate.py` (test, event-driven — NEW file)

**Analog:** `tests/conftest.py` (fixture/double conventions) + `tests/test_import_hygiene.py` /
`tests/test_reload.py` (RED-first two-commit proof convention, D-13).

**Test-double pattern to reuse from `tests/conftest.py`** (lines 25-46 — hand-written double, no
mocking library, matches repo-wide "no `unittest.mock`" convention):
```python
class _InstantStopEvent:
    """A `threading.Event`-shaped double whose `.wait()` returns immediately."""

    def wait(self, timeout: float | None = None) -> bool:
        return False


@pytest.fixture
def fake_stop_event() -> _InstantStopEvent:
    """A fresh `_InstantStopEvent` per test — the interruptible-sleep double."""
    return _InstantStopEvent()
```
`fake_stop_event` is directly reusable for ONLINE/FATAL-outcome tests (never asked to stop —
`is_set()` defaults falsy on a real `threading.Event()`, and `.wait()` never blocks). For a
SHUTDOWN-outcome test, construct a real `threading.Event()` and call `.set()` before invoking
`run()` — no new fixture needed (per RESEARCH.md "Wave 0 Gaps").

**Health-result construction pattern** — build inline, not via fixture (matches `HealthResult`'s
plain-dataclass-construction style used across `health.py`'s own docstring examples):
```python
HealthResult(ok=False, reason="probe failed", detail="conn refused", fatal=True)
HealthResult(ok=True, reason="ok")
HealthResult(ok=False, reason="degraded", severity=Severity.WARNING)  # non-fatal path
```

**RED-first two-commit convention** — see `tests/test_reload.py`'s module docstring (D-13): write
the test against unmodified `HEAD` first, confirm it fails (`ImportError` on `ReadyOutcome`, or
`TypeError` on the unexpected `fatal=` kwarg to `HealthResult`), THEN apply the source diff and
confirm green. Do not skip the pre-fix red run.

**Six test rows to cover (from RESEARCH.md's Phase Requirements → Test Map), each a small,
independent `def test_...():`, no shared fixture beyond `fake_stop_event`:**
1. `test_online_probe_returns_online_outcome_preserves_ordering` — passing probe → `ONLINE`,
   `on_online` fires before `_log.info`/`notifier.ready()` (assert call order via a list side-effect
   in a hand-written stub hook, not a mock).
2. `test_fatal_probe_returns_fatal_outcome_no_reprobe` — `fatal=True` probe → `FATAL`, `stop.wait`
   never invoked (use a stop double whose `.wait` raises `AssertionError` if called, to prove
   no-reprobe).
3. `test_fatal_probe_fires_on_fail_not_on_online` — `on_fail` invoked exactly once, `on_online`
   never invoked, on a fatal probe.
4. `test_non_fatal_failure_still_reprobes` — `fatal=False`, `severity=WARNING/CRITICAL` failing
   probe → severity-branch log fires + `stop.wait` IS invoked (byte-identical-to-today regression
   guard).
5. `test_stop_set_returns_shutdown_outcome` — real `threading.Event()` pre-`.set()` → `SHUTDOWN`.
6. `test_only_online_is_truthy` — Pitfall 3 guard: `bool(ReadyOutcome.ONLINE) is True`,
   `bool(ReadyOutcome.SHUTDOWN) is False`, `bool(ReadyOutcome.FATAL) is False` — sample BOTH
   non-ONLINE members, not just one.

Plus one `HealthResult` additive-field regression test (may live in this file or a
`test_health.py`, planner's call):
`test_health_result_fatal_defaults_false` — `HealthResult(ok=False, reason="x").fatal is False`.

---

### SURF-01 import test (test, request-response — NEW or extension)

**Analog:** `tests/test_import_hygiene.py` — the exact-import-statement assertion style (avoids
the `hasattr`-after-side-effect footgun, Pitfall 4).

**Pattern to copy — the RED test IS the success-criterion import itself, not an indirect check:**
```python
def test_summon_panel_reexport_succeeds():
    from yahir_reusable_bot.discord import summon_panel  # noqa: F401 — import IS the assertion

    assert "summon_panel" in __import__(
        "yahir_reusable_bot.discord", fromlist=["__all__"]
    ).__all__
```
Or more simply, two separate assertions in one test function: the bare `from ... import
summon_panel` (raises `ImportError` pre-fix) plus a direct `__all__` membership check against
`yahir_reusable_bot.discord.__all__`. Do NOT use `hasattr(module, "summon_panel")` after any
other test in the same session has imported `yahir_reusable_bot.discord.gateway` — this is the
exact false-pass risk RESEARCH.md's Pitfall 4 names.

**Placement:** either a new small file (e.g. `tests/test_discord_surface.py`) or an added test
function inside `tests/test_import_hygiene.py` — no existing file of that exact name; planner's
discretion per CONTEXT.md.

---

## Shared Patterns

### No mocking library / hand-written test doubles
**Source:** `tests/conftest.py` (repo-wide convention, stated explicitly in its own docstring:
"this repo uses no mocking library (no `pytest-mock`, no `unittest.mock`)")
**Apply to:** `tests/test_ready_gate.py` and the SURF-01 test — use plain classes/closures for
stop-event doubles and hook call-order recorders, never `unittest.mock.Mock`.

### RED-first two-commit proof (D-13)
**Source:** `tests/test_reload.py` module docstring (established convention), reaffirmed as
GATE-01 posture in CONTEXT.md D-43 (Phase-3)
**Apply to:** every new test in this phase — write against unmodified `HEAD`, confirm failure,
then apply the source fix, confirm green.

### Opaque passthrough / neutral-field branching (D-02 lifecycle litmus)
**Source:** `yahir_reusable_bot/lifecycle/health.py` module docstring + `ReadyGate.run`'s existing
`result.severity` branch (lines 103-114)
**Apply to:** `ready_gate.py`'s new `result.fatal` branch — read the field, never inspect `reason`/
`detail` as a string; log them as opaque structured fields exactly like the existing severity
branch does (`reason=result.reason, detail=result.detail`).

### No domain nouns / litmus-clean naming
**Source:** `tests/test_import_hygiene.py` (grimp graph + AST litmus grep, scans `ready_gate.py`
and `health.py` by hardcoded filename per RESEARCH.md's Sampling Rate section)
**Apply to:** `ReadyOutcome` member names (`ONLINE`/`SHUTDOWN`/`FATAL`), `fatal` field name, and
all new log message strings — zero weather vocabulary, verified already true of the planned names.

## No Analog Found

None — every file in this phase is a modification of its own existing source (in-place API
evolution), so each file's own current state IS its analog. No cross-file pattern borrowing was
needed beyond the shared test-convention and litmus-hygiene patterns above.

## Metadata

**Analog search scope:** `yahir_reusable_bot/lifecycle/`, `yahir_reusable_bot/discord/`, `tests/`
(entire repo — small codebase, no directory pruning needed)
**Files scanned:** `ready_gate.py`, `health.py`, `lifecycle/__init__.py`, `discord/__init__.py`,
`discord/gateway.py` (reference only), `tests/conftest.py`, `tests/test_import_hygiene.py`
(referenced via RESEARCH.md, not re-read — already excerpted there)
**Pattern extraction date:** 2026-07-28
</content>
