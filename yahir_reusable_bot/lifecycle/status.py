"""Status-file reporter (SEAM-09): a bot's liveness and last outcomes, written for outside readers.

Writes ``$XDG_STATE_HOME/yahir-bots/<bot>.json`` (schema_version 1) atomically — temp file in the
same directory, then ``os.replace`` — every ``interval_s`` seconds and immediately on each event.
Readers (the usage-dashboard Bots tab) treat a heartbeat older than 3 x ``interval_s`` as stale, so a
hung or SIGKILLed bot is visible even though its file survives it.

Heartbeat: pass the bot's event loop to ``start(loop=...)`` and each beat is posted onto that loop
(``call_soon_threadsafe``), so a blocked or deadlocked loop stops beating and the dashboard marks it
stale. Without a loop the timer thread beats directly and only process death is detected.

Best-effort like :class:`SystemdNotifier`: an ``OSError`` while writing is swallowed, never raised —
status reporting must not be load-bearing for liveness. Error strings pass through the built-in
``BASELINE_PATTERNS`` first, then the bot's own patterns (via :func:`redact_secrets`), then are capped
at 300 characters; no message content is ever recorded. stdlib only.
"""

from __future__ import annotations

import asyncio
import importlib.metadata
import json
import os
import re
import tempfile
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Sequence

import structlog

from ..channels import DeliveryResult
from ..redact.core import RedactionPattern, redact_secrets

_log = structlog.get_logger(__name__)

SCHEMA_VERSION = 1
ERROR_CAP = 300
UNPRINTABLE = "<unprintable error>"

# Always-on baseline: a status file must never carry a credential, whatever patterns the bot wires.
# Order matters: webhook URLs first (their path embeds a token-shaped segment), then bot tokens,
# then header / key=value forms. All are linear-time (no nested quantifiers).
BASELINE_PATTERNS: tuple[RedactionPattern, ...] = (
    RedactionPattern(re.compile(r"https://(?:\w+\.)?discord(?:app)?\.com/api/webhooks/\S+"), "<webhook>"),
    RedactionPattern(re.compile(r"[\w-]{23,28}\.[\w-]{6,7}\.[\w-]{27,}"), "<token>"),
    RedactionPattern(re.compile(r"Bearer\s+\S+", re.IGNORECASE), "Bearer <token>"),
    RedactionPattern(re.compile(r"(Authorization\s*[:=]\s*)\S+(?:[ \t]+\S+)?", re.IGNORECASE), r"\1<redacted>"),
    RedactionPattern(
        re.compile(r"\b((?:[\w-]*(?:token|key|secret))\s*=\s*)[^\s&;,]+", re.IGNORECASE), r"\1<redacted>"
    ),
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def default_state_dir() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "yahir-bots"


class StatusReporter:
    """Holds one bot's status and keeps its status file current. Thread-safe."""

    def __init__(
        self,
        bot: str,
        *,
        scope: str = "user",
        unit: str | None = None,
        state_dir: Path | None = None,
        interval_s: int = 60,
        hub_version: str | None = None,
        patterns: Sequence[RedactionPattern] = (),
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._dir = Path(state_dir) if state_dir is not None else default_state_dir()
        self._patterns = tuple(patterns)
        self._clock = clock
        self._interval_s = interval_s
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._beat_loop: asyncio.AbstractEventLoop | None = None
        if hub_version is None:
            try:
                hub_version = importlib.metadata.version("yahir-reusable-bot")
            except importlib.metadata.PackageNotFoundError:
                hub_version = None
        now = clock().isoformat()
        self._status: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION, "bot": bot, "unit": unit or f"{bot}.service", "scope": scope,
            "hub_version": hub_version, "pid": os.getpid(), "started_at": now, "heartbeat_at": now,
            "interval_s": interval_s, "state": "starting", "discord": None, "last_delivery": None,
            "last_job": None, "last_error": None,
        }

    @property
    def path(self) -> Path:
        return self._dir / f"{self._status['bot']}.json"

    # -- lifecycle ---------------------------------------------------------
    def start(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Write the first status and start the heartbeat timer (a daemon thread).

        With ``loop``, each beat is posted onto that loop, so a hung loop stops beating and goes
        stale. Without it the thread beats directly (process death only). A second call is a no-op.
        """
        if self._thread is not None:
            return
        self._beat_loop = loop
        self._update()
        self._thread = threading.Thread(target=self._loop, name="status-heartbeat", daemon=True)
        self._thread.start()

    def running(self) -> None:
        self._update(state="running")

    def stopping(self) -> None:
        """Graceful shutdown: record ``stopped`` so readers can tell a deliberate stop from a crash."""
        self._stop.set()
        self._update(state="stopped")

    def heartbeat(self) -> None:
        self._update()

    def _loop(self) -> None:
        while not self._stop.wait(self._interval_s):
            try:
                loop = self._beat_loop
                if loop is None:
                    self.heartbeat()
                elif not loop.is_closed():
                    loop.call_soon_threadsafe(self.heartbeat)
            except RuntimeError:  # loop closed under us: the bot is dying, missing beats is correct
                pass
            except Exception:  # one bad tick must never end the loop
                _log.debug("status_heartbeat_failed", exc_info=True)

    # -- events --------------------------------------------------------------
    def mark_discord(self, connected: bool) -> None:
        def change(status: dict[str, Any]) -> dict[str, Any]:
            prev = status["discord"]
            if prev is not None and prev["connected"] == connected:
                return {}
            out: dict[str, Any] = {"discord": {"connected": connected, "since": self._clock().isoformat()}}
            if connected and status["state"] == "starting":
                out["state"] = "running"  # mitigation: a bot that never calls running() still goes green
            return out

        self._update(_compute=change)

    def record_delivery(self, result: DeliveryResult) -> None:
        self._update(last_delivery={"at": self._clock().isoformat(), "ok": result.ok,
                                    "error": None if result.ok else self._clean(result.detail or "delivery failed")})

    def record_job(self, name: str, ok: bool, error: str | None = None) -> None:
        self._update(last_job={"name": name if isinstance(name, str) else self._clean(name), "at": self._clock().isoformat(), "ok": ok,
                               "error": self._clean(error) if error else None})

    def record_error(self, message: str) -> None:
        self._update(last_error={"at": self._clock().isoformat(), "message": self._clean(message)})

    # -- internals -------------------------------------------------------------
    def _clean(self, text: Any) -> str:
        try:
            if not isinstance(text, str):
                text = str(text)
            return redact_secrets(text, (*BASELINE_PATTERNS, *self._patterns))[:ERROR_CAP]
        except Exception:
            return UNPRINTABLE

    def _update(self, _compute: Callable[[dict[str, Any]], dict[str, Any]] | None = None, **fields: Any) -> None:
        """Merge ``fields`` (or the result of ``_compute`` run under the lock) and rewrite the file.

        Never raises: status reporting must not be load-bearing for the bot.
        """
        try:
            with self._lock:
                if _compute is not None:
                    fields = {**fields, **_compute(self._status)}
                self._status.update(fields, heartbeat_at=self._clock().isoformat())
                snapshot = json.dumps(self._status, default=str)
                self._dir.mkdir(mode=0o700, parents=True, exist_ok=True)
                fd, tmp = tempfile.mkstemp(dir=self._dir, prefix=".tmp-", suffix=".json")
                try:
                    with os.fdopen(fd, "w") as fh:
                        fh.write(snapshot)
                    os.chmod(tmp, 0o600)
                    os.replace(tmp, self.path)
                except BaseException:
                    Path(tmp).unlink(missing_ok=True)
                    raise
        except Exception:
            _log.debug("status_write_failed", exc_info=True)
