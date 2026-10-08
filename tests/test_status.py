import json
import os
import stat
from datetime import UTC, datetime, timedelta

from yahir_reusable_bot.channels import DeliveryResult
from yahir_reusable_bot.lifecycle import StatusReporter
from yahir_reusable_bot.redact.core import RedactionPattern

T0 = datetime(2026, 10, 8, 15, 0, tzinfo=UTC)


class Clock:
    def __init__(self):
        self.t = T0

    def __call__(self):
        return self.t


def reporter(tmp_path, **kw):
    clock = kw.pop("clock", Clock())
    return StatusReporter("test-bot", state_dir=tmp_path / "yahir-bots", hub_version="0.3.0", clock=clock, **kw), clock


def read(r):
    return json.loads(r.path.read_text())


def test_start_writes_the_v1_shape_with_private_modes(tmp_path):
    r, _ = reporter(tmp_path)
    r.start()
    try:
        data = read(r)
        assert data == {
            "schema_version": 1, "bot": "test-bot", "unit": "test-bot.service", "scope": "user",
            "hub_version": "0.3.0", "pid": os.getpid(), "started_at": T0.isoformat(), "heartbeat_at": T0.isoformat(),
            "interval_s": 60, "state": "starting", "discord": None, "last_delivery": None, "last_job": None,
            "last_error": None,
        }
        assert stat.S_IMODE(r.path.stat().st_mode) == 0o600
        assert stat.S_IMODE(r.path.parent.stat().st_mode) == 0o700
    finally:
        r.stopping()


def test_events_write_immediately(tmp_path):
    r, clock = reporter(tmp_path)
    r.start()
    try:
        r.running()
        clock.t = T0 + timedelta(seconds=5)
        r.mark_discord(True)
        r.record_delivery(DeliveryResult(ok=False, detail="HTTP 503"))
        r.record_job("drain-spool", ok=True)
        data = read(r)
        assert data["state"] == "running"
        assert data["discord"] == {"connected": True, "since": (T0 + timedelta(seconds=5)).isoformat()}
        assert data["last_delivery"] == {"at": (T0 + timedelta(seconds=5)).isoformat(), "ok": False, "error": "HTTP 503"}
        assert data["last_job"] == {"name": "drain-spool", "at": (T0 + timedelta(seconds=5)).isoformat(), "ok": True, "error": None}
        assert data["heartbeat_at"] == (T0 + timedelta(seconds=5)).isoformat()
    finally:
        r.stopping()


def test_discord_since_only_moves_on_a_change(tmp_path):
    r, clock = reporter(tmp_path)
    r.start()
    try:
        r.mark_discord(True)
        clock.t = T0 + timedelta(minutes=1)
        r.mark_discord(True)
        assert read(r)["discord"]["since"] == T0.isoformat()
    finally:
        r.stopping()


def test_errors_are_redacted_and_capped(tmp_path):
    import re
    hook = RedactionPattern(pattern=re.compile(r"https://discord\.com/api/webhooks/\S+"), replacement="<webhook>")
    r, _ = reporter(tmp_path, patterns=[hook])
    r.start()
    try:
        r.record_error("POST https://discord.com/api/webhooks/123/SECRET failed " + "x" * 400)
        msg = read(r)["last_error"]["message"]
        assert "SECRET" not in msg and msg.startswith("POST <webhook> failed") and len(msg) == 300
        r.record_delivery(DeliveryResult(ok=False, detail="https://discord.com/api/webhooks/1/TOKEN"))
        assert read(r)["last_delivery"]["error"] == "<webhook>"
    finally:
        r.stopping()


def test_stopping_writes_stopped_and_heartbeat_ticks(tmp_path):
    r, clock = reporter(tmp_path, interval_s=60)
    r.start()
    clock.t = T0 + timedelta(seconds=60)
    r.heartbeat()  # what the background loop calls each interval
    assert read(r)["heartbeat_at"] == (T0 + timedelta(seconds=60)).isoformat()
    r.stopping()
    assert read(r)["state"] == "stopped"


def test_atomic_write_leaves_no_temp_files(tmp_path):
    r, _ = reporter(tmp_path)
    r.start()
    for i in range(20):
        r.record_job(f"j{i}", ok=True)
    r.stopping()
    assert sorted(p.name for p in r.path.parent.iterdir()) == ["test-bot.json"]


def test_write_failure_never_raises(tmp_path):
    blocker = tmp_path / "yahir-bots"
    blocker.write_text("a file where the dir should be")
    r = StatusReporter("test-bot", state_dir=blocker, clock=Clock())
    r.start()          # must not raise
    r.record_job("j", ok=False, error="e")
    r.stopping()


def test_default_state_dir_honours_xdg(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    assert StatusReporter("x").path == tmp_path / "yahir-bots" / "x.json"
