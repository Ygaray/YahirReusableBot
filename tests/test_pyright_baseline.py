"""Regression suite for HYG-04's pyright baseline-diff gate (D-03).

Self-proof note (matching ``test_redact_sink.py``'s docstring convention):
``scripts.pyright_baseline`` does not exist yet, so EVERY assertion in this module is
genuinely RED pre-fix — collection itself fails with an ``ImportError`` before a single
test body runs. There is no partial-pass baseline to distinguish here; the entire file
is the RED half of GATE-02's two-commit discipline.

Every test below is SYNTHETIC: pyright itself is never invoked. The tests drive the
gate's pure key-building and diffing helpers with hand-built dicts shaped like
pyright's ``--outputjson`` ``generalDiagnostics`` entries, so this suite stays fast
(no Node runtime dependency) and stays independent of whatever pyright happens to find
in this codebase on a given day. That independence is what lets these tests pin the
gate's CONTRACT (line-drift tolerance, path relativization, burn-down tolerance, the
too-loose/too-tight key failure modes, and the zero-files vacuity distinction) rather
than merely recording today's diagnostic count.
"""
from __future__ import annotations

from pathlib import Path

from scripts.pyright_baseline import (
    _assert_run_was_not_vacuous,
    _diagnostic_key,
    _new_diagnostics,
)

_ROOT = Path("/repo")


def _diag(
    *,
    file: str = "/repo/yahir_reusable_bot/redact/sink.py",
    message: str = "Type of parameter is partially unknown",
    rule: str | None = "reportUnknownParameterType",
    line: int = 10,
    character: int = 4,
) -> dict:
    """Build one synthetic diagnostic dict, varying exactly the fields a caller overrides.

    Shaped like a single ``generalDiagnostics`` entry from ``pyright --outputjson``:
    an absolute ``file``, a ``severity``, a ``message``, a ``range`` with start/end
    line+character, and an optional ``rule``.
    """
    entry: dict = {
        "file": file,
        "severity": "error",
        "message": message,
        "range": {
            "start": {"line": line, "character": character},
            "end": {"line": line, "character": character + 5},
        },
    }
    if rule is not None:
        entry["rule"] = rule
    return entry


def test_a_diagnostic_absent_from_the_baseline_is_flagged():
    current = [_diag()]
    baseline: list[dict] = []
    new = _new_diagnostics(current, baseline, _ROOT)
    assert new == [_diagnostic_key(_diag(), _ROOT)]


def test_a_diagnostic_present_in_the_baseline_is_not_flagged():
    current = [_diag()]
    baseline = [_diag()]
    assert _new_diagnostics(current, baseline, _ROOT) == []


def test_line_number_drift_alone_is_not_a_new_diagnostic():
    """Pitfall 4's core contract. Without this, every unrelated edit above a flagged
    line looks like a fresh error — the single most important test in this file.
    """
    current = [_diag(line=42, character=8)]
    baseline = [_diag(line=10, character=4)]
    assert _new_diagnostics(current, baseline, _ROOT) == []


def test_a_different_message_in_an_already_flagged_file_is_flagged():
    """Pins the opposite failure mode: a key too loose to distinguish a genuinely
    new problem inside an already-known file.
    """
    current = [_diag(message="A completely different diagnostic")]
    baseline = [_diag(message="Type of parameter is partially unknown")]
    new = _new_diagnostics(current, baseline, _ROOT)
    assert new == [_diagnostic_key(current[0], _ROOT)]


def test_a_missing_rule_does_not_collapse_distinct_diagnostics():
    """Some pyright diagnostics carry no rule. A key builder that defaults them all
    to the same empty value and then compares only file-plus-rule would merge two
    genuinely distinct diagnostics into one.
    """
    current = [
        _diag(rule=None, message="first distinct message"),
        _diag(rule=None, message="second distinct message"),
    ]
    baseline: list[dict] = []
    new = _new_diagnostics(current, baseline, _ROOT)
    assert len(new) == 2
    assert len(set(new)) == 2


def test_diagnostic_keys_are_repo_relative_not_absolute():
    """What makes a committed baseline portable — without this, a baseline is valid
    only on the machine that generated it.
    """
    current = _diag(file="/repo/yahir_reusable_bot/redact/sink.py")
    baseline = _diag(file="/some/other/checkout/yahir_reusable_bot/redact/sink.py")
    key_current = _diagnostic_key(current, Path("/repo"))
    key_baseline = _diagnostic_key(baseline, Path("/some/other/checkout"))
    assert key_current == key_baseline


def test_a_baseline_entry_that_no_longer_reproduces_is_not_an_error():
    """Burn-down must be allowed, or the gate punishes the very progress it exists
    to enable.
    """
    current: list[dict] = []
    baseline = [_diag()]
    assert _new_diagnostics(current, baseline, _ROOT) == []


def test_a_run_that_analyzed_zero_files_is_rejected_as_vacuous():
    """Drives the vacuity helper with both halves of the distinction it must draw:
    a zero-files-analyzed report is rejected, and a positive file count with an empty
    diagnostics list (a legitimate clean run) is accepted, NOT rejected. Conflating
    'checked nothing' with 'found nothing' in either direction is the failure this
    test forecloses.
    """
    vacuous_report = {
        "generalDiagnostics": [],
        "summary": {"filesAnalyzed": 0, "errorCount": 0, "warningCount": 0},
    }
    raised = False
    try:
        _assert_run_was_not_vacuous(vacuous_report)
    except (AssertionError, ValueError):
        raised = True
    assert raised, "a zero-files-analyzed report must be rejected as vacuous"

    clean_report = {
        "generalDiagnostics": [],
        "summary": {"filesAnalyzed": 12, "errorCount": 0, "warningCount": 0},
    }
    _assert_run_was_not_vacuous(clean_report)  # must not raise — clean, not vacuous
