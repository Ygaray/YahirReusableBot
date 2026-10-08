"""Status-file reporter (SEAM-09): a bot's liveness and last outcomes, written for outside readers.

Writes ``$XDG_STATE_HOME/yahir-bots/<bot>.json`` (schema_version 1) atomically — temp file in the
same directory, then ``os.replace`` — every ``interval_s`` seconds and immediately on each event.
Readers (the usage-dashboard Bots tab) treat a heartbeat older than 3 x ``interval_s`` as stale, so a
hung or SIGKILLed bot is visible even though its file survives it.

Best-effort like :class:`SystemdNotifier`: an ``OSError`` while writing is swallowed, never raised —
status reporting must not be load-bearing for liveness. Error strings pass through
:func:`redact_secrets` with the bot's own patterns and are capped at 300 characters; no message
content is ever recorded. stdlib only.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Sequence

from ..channels import DeliveryResult
from ..redact.core import RedactionPattern, redact_secrets

SCHEMA_VERSION = 1
ERROR_CAP = 300


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
    def start(self) -> None:
        """Write the first status and start the heartbeat loop (a daemon thread)."""
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
            self.heartbeat()

    # -- events --------------------------------------------------------------
    def mark_discord(self, connected: bool) -> None:
        with self._lock:
            prev = self._status["discord"]
        if prev is not None and prev["connected"] == connected:
            self._update()
            return
        self._update(discord={"connected": connected, "since": self._clock().isoformat()})

    def record_delivery(self, result: DeliveryResult) -> None:
        self._update(last_delivery={"at": self._clock().isoformat(), "ok": result.ok,
                                    "error": None if result.ok else self._clean(result.detail or "delivery failed")})

    def record_job(self, name: str, ok: bool, error: str | None = None) -> None:
        self._update(last_job={"name": name, "at": self._clock().isoformat(), "ok": ok,
                               "error": self._clean(error) if error else None})

    def record_error(self, message: str) -> None:
        self._update(last_error={"at": self._clock().isoformat(), "message": self._clean(message)})

    # -- internals -------------------------------------------------------------
    def _clean(self, text: str) -> str:
        return redact_secrets(text, self._patterns)[:ERROR_CAP]

    def _update(self, **fields: Any) -> None:
        with self._lock:
            self._status.update(fields, heartbeat_at=self._clock().isoformat())
            snapshot = json.dumps(self._status)
            try:
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
            except OSError:
                pass  # best-effort, like SystemdNotifier: never let status writing crash the bot
