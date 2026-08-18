#!/usr/bin/env python3
"""Baseline-and-burn-down gate for the pyright static type-check (HYG-04, D-03).

Why this exists: pyright ships no native baseline or grandfathering mechanism, and
no helper package fills that gap on either PyPI or npm (confirmed absent this
phase's research, 08-RESEARCH.md § Don't Hand-Roll). D-03 locked "basic mode with a
first-run baseline" — this script IS that baseline mechanism, hand-rolled because
nothing off-the-shelf exists to reach for instead.

What it does: runs ``pyright --outputjson`` over the configured ``[tool.pyright]``
scope, keys each diagnostic on a stable ``(repo-relative file, rule, message)``
tuple, and fails only on keys the committed baseline (``pyright-baseline.json``)
does not already carry. A baseline entry that no longer reproduces is silently
accepted as burn-down progress, not an error.

Accepted limitation, stated honestly: the key omits position (line/character) by
design, so line-number drift on unrelated edits never produces false "new error"
noise. The deliberate trade is that two OCCURRENCES of an identical diagnostic
(same file, rule, and message) in one file collapse to a single baseline entry — a
second occurrence appearing later at a different location will not be flagged,
because its key is indistinguishable from the first. A reader deserves to know this
rather than discover it.

Usage:
    uv run python scripts/pyright_baseline.py                 # gate mode (default)
    uv run python scripts/pyright_baseline.py --write-baseline  # regenerate the baseline

Stdlib only, aside from invoking the installed ``pyright`` executable as a
subprocess.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BASELINE_PATH = _ROOT / "pyright-baseline.json"


def _run_pyright() -> dict:
    """Run pyright with JSON output and parse stdout.

    ``check=False`` is load-bearing: pyright exits non-zero whenever it finds ANY
    diagnostic, including on a totally healthy first run over a codebase with
    pre-existing findings. Treating that as a failure to RUN (rather than a
    reportable outcome) would break this gate on its very first real finding.
    """
    result = subprocess.run(
        ["uv", "run", "pyright", "--outputjson"],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return json.loads(result.stdout)


def _diagnostic_key(diag: dict, root: Path) -> tuple[str, str, str]:
    """Build a stable key: (repo-relative file, rule, message).

    Deliberately omits line/character — line numbers drift on any insertion above a
    flagged line, and keying on position would produce a wave of phantom new errors
    and matching resolutions on every unrelated edit (08-RESEARCH.md Pitfall 4).

    Relativized against ``root`` and emitted in POSIX form so a committed baseline
    compares equal across machines and checkouts; pyright reports absolute paths and
    an unrelativized key would make the baseline useless to anyone but its author.
    If a path falls outside ``root`` (unexpected but not impossible), it is kept
    as-is rather than raising, so the entry stays comparable instead of crashing
    the gate.

    A diagnostic whose ``file`` is ALREADY relative (as persisted by
    ``--write-baseline``, see ``_relativize_diagnostics``) is passed through
    unchanged. This is load-bearing across git worktrees: a live pyright run's
    ``file`` is always absolute under whichever checkout invoked it (``cwd=_ROOT``),
    but the COMMITTED baseline is generated once, in one checkout's absolute path,
    and then read back from every other checkout — a different worktree, a fresh
    clone, or the checkout the branch merges into. Without this branch, comparing
    two absolute paths rooted in different checkouts via ``relative_to`` on the
    CURRENT run's root would raise ``ValueError`` for every baseline entry, and the
    ``except`` fallback would keep the baseline's now-foreign absolute path verbatim
    — silently flagging the entire baseline as "new" diagnostics on every checkout
    but the one that wrote it.
    """
    raw_file = diag.get("file", "")
    file_path = Path(raw_file)
    if not file_path.is_absolute():
        file_key = file_path.as_posix()
    else:
        try:
            rel = file_path.relative_to(root)
            file_key = rel.as_posix()
        except ValueError:
            file_key = file_path.as_posix()
    rule = diag.get("rule") or ""
    message = diag.get("message", "")
    return (file_key, rule, message)


def _relativize_diagnostics(diagnostics: list[dict], root: Path) -> list[dict]:
    """Return ``diagnostics`` with each entry's ``file`` rewritten repo-relative.

    Applied only when WRITING the baseline (``--write-baseline``), never when
    reading a live gate run — a live run's diagnostics are compared in-memory via
    ``_diagnostic_key`` and never need their raw ``file`` field rewritten. Without
    this step the persisted JSON carries the writing checkout's absolute path
    verbatim, defeating the entire purpose of relativization (see
    ``_diagnostic_key``'s docstring): the baseline would silently stop matching the
    moment it is read from any other checkout, including the one this branch
    eventually merges into.
    """
    relativized = []
    for diag in diagnostics:
        new_diag = dict(diag)
        raw_file = diag.get("file", "")
        file_path = Path(raw_file)
        if file_path.is_absolute():
            try:
                new_diag["file"] = file_path.relative_to(root).as_posix()
            except ValueError:
                new_diag["file"] = file_path.as_posix()
        else:
            new_diag["file"] = file_path.as_posix()
        relativized.append(new_diag)
    return relativized


def _new_diagnostics(current: list[dict], baseline: list[dict], root: Path) -> list[tuple[str, str, str]]:
    """Return a sorted list of keys present in ``current`` and absent from ``baseline``.

    A baseline entry with no matching current key is burn-down progress, not an
    error — it is simply never surfaced here. Sorted output is part of the
    contract: the failure report must be deterministic across runs, matching the
    rule the doc-drift gate adopted in Phase 7.
    """
    baseline_keys = {_diagnostic_key(d, root) for d in baseline}
    current_keys = {_diagnostic_key(d, root) for d in current}
    return sorted(current_keys - baseline_keys)


def _assert_run_was_not_vacuous(report: dict) -> None:
    """Raise when the report's summary shows zero files analyzed.

    A mis-scoped ``include`` makes pyright analyze zero files and exit clean — that
    is NOT the same as a genuinely clean run, and reporting it as such would let a
    broken config pass silently forever. A positive file count with an empty
    diagnostics list, by contrast, IS a legitimate clean run and must be accepted.
    """
    files_analyzed = report.get("summary", {}).get("filesAnalyzed", 0)
    if files_analyzed == 0:
        raise AssertionError(
            "pyright analyzed ZERO files — this means the [tool.pyright] "
            "'include' configuration matched nothing, most likely a mis-scoped "
            "path. This is NOT the same as a clean run and is treated as a gate "
            "failure. Check pyproject.toml's [tool.pyright].include."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Regenerate pyright-baseline.json from the current pyright run.",
    )
    args = parser.parse_args()

    report = _run_pyright()
    diagnostics = report.get("generalDiagnostics", [])

    if args.write_baseline:
        _assert_run_was_not_vacuous(report)
        # Persist repo-relative `file` fields, not the raw absolute paths pyright
        # reports. A committed baseline is read back from checkouts other than the
        # one that wrote it (a different git worktree, a fresh clone, or the
        # checkout this branch merges into) — see `_relativize_diagnostics`.
        portable_report = dict(report)
        portable_report["generalDiagnostics"] = _relativize_diagnostics(diagnostics, _ROOT)
        _BASELINE_PATH.write_text(
            json.dumps(portable_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(
            f"Wrote baseline: {len(diagnostics)} diagnostic(s) "
            f"across {report.get('summary', {}).get('filesAnalyzed', 0)} file(s) analyzed."
        )
        return 0

    if not _BASELINE_PATH.exists():
        print(
            f"ERROR: no baseline found at {_BASELINE_PATH}. "
            "Run 'uv run python scripts/pyright_baseline.py --write-baseline' first.",
            file=sys.stderr,
        )
        return 1

    _assert_run_was_not_vacuous(report)

    baseline_report = json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))
    baseline_diagnostics = baseline_report.get("generalDiagnostics", [])

    new_keys = _new_diagnostics(diagnostics, baseline_diagnostics, _ROOT)

    print(
        f"pyright: {len(diagnostics)} diagnostic(s) this run, "
        f"{len(baseline_diagnostics)} in the committed baseline."
    )

    if new_keys:
        print(f"\n{len(new_keys)} NEW diagnostic(s) not present in the baseline:", file=sys.stderr)
        for file_key, rule, message in new_keys:
            rule_display = rule or "(no rule)"
            print(f"  {file_key} [{rule_display}]: {message}", file=sys.stderr)
        return 1

    print("Gate PASSED — no diagnostics outside the committed baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
