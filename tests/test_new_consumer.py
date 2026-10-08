import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("new_consumer", Path(__file__).resolve().parent.parent / "scripts" / "new_consumer.py")
nc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(nc)


def test_bot_slug():
    assert nc.bot_slug("GsdAlertBot") == "gsd-alert-bot"
    assert nc.bot_slug("ReminderBot") == "reminder-bot"
    assert nc.bot_slug("Reminder Bot") == "reminder-bot"


def test_unit_file_runs_the_venv_entry_point_as_notify():
    unit = nc.unit_file("gsd-alert-bot", Path("/home/u/Projects/GsdAlertBot"))
    assert "Type=notify" in unit and "Restart=on-failure" in unit and "WantedBy=default.target" in unit
    assert "ExecStart=/home/u/Projects/GsdAlertBot/.venv/bin/gsd-alert-bot run" in unit
    assert "uv run" not in unit


def test_adopt_line():
    assert nc.adopt_line("GsdAlertBot", "GsdAlertBot", "gsd-alert-bot") == \
        "yahir-tn adopt gsd-alert-bot --project GsdAlertBot --unit gsd-alert-bot.service"


def test_wiring_stub_shows_status_reporter():
    stub = nc.wiring_stub("gsdalertbot")
    for needle in ("StatusReporter", "ReportingChannel", "on_job_result", "on_connection", "reporter.stopping()"):
        assert needle in stub


def test_pyproject_has_both_script_entries():
    text = nc.pyproject("gsd-alert-bot", "gsdalertbot", "GsdAlertBot", "u", "v1", "/h", "gsd-alert-bot")
    assert 'gsdalertbot = "gsdalertbot.cli:main"' in text
    assert 'gsd-alert-bot = "gsdalertbot.cli:main"' in text


def test_pyproject_single_script_entry_when_slug_equals_import_root():
    text = nc.pyproject("weatherbot", "weatherbot", "WeatherBot", "u", "v1", "/h", "weatherbot")
    assert text.count('weatherbot = "weatherbot.cli:main"') == 1
