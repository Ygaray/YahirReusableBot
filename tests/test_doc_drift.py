"""The standing planning-doc drift gate (DOCS-02) — no active ``.planning/`` artifact may name
the stale, nonexistent WeatherBot de-hack path.

The v0.1.2 audit's own headline lesson is that an automated check derived from the same source
as the claim it verifies cannot catch an error in that source: ``04-01-PLAN.md:257`` held an
``<automated>`` grep that asserted the WRONG path and passed anyway. D-67 (07-CONTEXT.md) answers
that with TWO deliberately separate mechanisms:

1. **This file — an always-runs in-suite gate with no cross-repo dependency.** Scans every
   ``.planning/**/*.md`` for the BARE regex ``ops[/.]daemon`` (not the fully-qualified
   ``weatherbot/ops/daemon`` form — three of the fourteen historical drift sites write the
   unprefixed spelling, so a fully-qualified pattern would miss exactly the sites the audit
   warned about; that is the audit's own headline lesson recurring at gate-authoring time).
2. **One-time filesystem evidence, recorded in the phase SUMMARY, not a test** — that the
   corrected paths resolve on disk in a WeatherBot checkout. Not part of this file; a
   ``skipif(weatherbot_missing)`` test would be the SAME false-assurance failure class the audit
   warned about (a check that silently does not run), so it is deliberately not attempted here.

Following ``tests/test_import_hygiene.py``'s convention, every gate below is paired with a
self-proof — a guard is only trustworthy if a deliberately-injected violation is PROVEN to trip
it. So the module has TWO halves:

1. The REAL ``.planning/`` tree must PASS the gate (every active artifact names a real path).
2. Deliberately-constructed synthetic data, run through the SAME scan/locator helpers, must FAIL
   (or must resolve non-vacuously) — proving the scan logic itself, not a copy of it.
"""

from __future__ import annotations

import re
from pathlib import Path

# The ``_MODULE_ROOT`` path idiom from ``tests/test_import_hygiene.py:64``, applied to
# ``.planning/`` instead of the package root.
_PLANNING_ROOT = Path(__file__).resolve().parent.parent / ".planning"

# BARE two-segment form, deliberately NOT prefixed with ``weatherbot/``. Three of the fourteen
# drift sites (``04-CONTEXT.md:48``, ``04-RESEARCH.md:15``, ``04-VALIDATION.md:77``) write the
# unprefixed ``ops/daemon.py`` spelling with no consumer-package prefix. A gate greping the
# fully-qualified ``weatherbot/ops/daemon.py`` would silently miss all three — a check derived
# from a narrower string than the error cannot catch the error. That is the audit's own headline
# lesson (DOC-DRIFT-01); the pattern here is bare on purpose.
_DRIFT_RE = re.compile(r"ops[/.]daemon")

# The one file with a LINE-SCOPED exemption rather than a whole-file exemption — the DOCS-02
# requirement bullet itself must keep naming the nonexistent path (it IS the error being
# described), but the rest of the file must not.
_REQUIREMENTS_REL = "REQUIREMENTS.md"

# The marker text used to locate the DOCS-02 requirement block inside REQUIREMENTS.md's line
# list. Located by CONTENT, not by an absolute line number — line numbers in an actively-edited
# requirements file shift (07-05 already shifted this block once), and a stale numeric exemption
# would silently excuse the wrong line.
_DOCS02_MARKER = "**DOCS-02**"

# Whole-file/whole-subtree exemptions. Every entry carries its own inline comment stating WHY it
# is exempt (D-67 requires a per-entry reason). MUST NOT be used to retire a real drift site —
# only to record that a mention is INTENTIONAL (the mention names the stale path AS the error
# being described, or as part of specifying/recording the correction itself).
_EXEMPT_PREFIXES: tuple[str, ...] = (
    # The retrospective that REPORTS the drift — it names the stale path as the finding being
    # described (DOC-DRIFT-01/02). Rewriting it would destroy the record of the finding.
    "v0.1.2-MILESTONE-AUDIT.md",
    # The frozen v0.1.2 archive — annotated with a drift banner (Task 3), never rewritten. One
    # archived plan (``04-01-PLAN.md:257``) holds the automated check that passed by grepping the
    # wrong string — the primary evidence for the audit's headline lesson.
    "milestones/",
    # This phase's own CONTEXT / RESEARCH / PATTERNS / VALIDATION / DISCUSSION-LOG / PLAN /
    # SUMMARY artifacts, which must quote the stale path in order to specify and record its
    # correction.
    "phases/07-v0-1-2-debt-paydown/",
)


# ---------------------------------------------------------------------------
# Shared scan logic — the SAME helpers the gate AND its self-proofs call.
# ---------------------------------------------------------------------------


def _collect_planning_lines() -> dict[str, list[tuple[int, str]]]:
    """Read every ``.planning/**/*.md`` file as UTF-8, one-based ``(lineno, text)`` pairs.

    Matching is per CODE POINT over UTF-8-decoded text, so both the bare ``ops/daemon`` spelling
    and the fully-qualified ``weatherbot/ops/daemon`` spelling are caught by the same regex
    downstream — there is no separate encoding-specific code path to drift out of sync.
    """
    collected: dict[str, list[tuple[int, str]]] = {}
    for path in sorted(_PLANNING_ROOT.rglob("*.md")):
        rel = path.relative_to(_PLANNING_ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        collected[rel] = list(enumerate(text.splitlines(), start=1))
    return collected


def _docs02_block_lines(lines: list[tuple[int, str]]) -> set[int]:
    """Return the one-based line numbers belonging to REQUIREMENTS.md's DOCS-02 block.

    Starts at the line containing the DOCS-02 requirement marker and runs up to but NOT
    including the next line that begins a sibling top-level bullet (``- [``) or a new section
    heading (``#``). The window is HALF-OPEN at that terminator: a match ON the terminator line
    itself is not exempt (pinned by
    ``test_selfproof_scan_does_not_exempt_the_line_after_the_block_window``).
    """
    start: int | None = None
    for lineno, text in lines:
        if _DOCS02_MARKER in text:
            start = lineno
            break
    if start is None:
        return set()

    block = {start}
    for lineno, text in lines:
        if lineno <= start:
            continue
        stripped = text.lstrip()
        if stripped.startswith("- [") or stripped.startswith("#"):
            break
        block.add(lineno)
    return block


def _scan_drift(
    files_to_lines: dict[str, list[tuple[int, str]]],
    exempt_prefixes: tuple[str, ...],
    exempt_lines: dict[str, set[int]],
) -> list[tuple[str, int]]:
    """Return every ``_DRIFT_RE`` match not covered by an exemption, SORTED for determinism.

    A match is exempt if its path starts with any ``exempt_prefixes`` entry, OR its exact
    ``(path, line)`` pair is inside ``exempt_lines`` (the DOCS-02 line-scoped window). Sorting by
    ``(relative_path, line_number)`` is part of the contract — a failure message must be
    deterministic across runs, matching ``_scan_framework_leaks``'s ``sorted(leaks)`` idiom at
    ``tests/test_import_hygiene.py:360``.
    """
    violations: list[tuple[str, int]] = []
    for rel_path, lines in files_to_lines.items():
        if any(rel_path.startswith(prefix) for prefix in exempt_prefixes):
            continue
        file_exempt_lines = exempt_lines.get(rel_path, set())
        for lineno, text in lines:
            if lineno in file_exempt_lines:
                continue
            if _DRIFT_RE.search(text):
                violations.append((rel_path, lineno))
    return sorted(violations)


# ---------------------------------------------------------------------------
# The real gate.
# ---------------------------------------------------------------------------


def test_no_active_planning_artifact_names_the_stale_daemon_path():
    """No active ``.planning/`` artifact names the stale, nonexistent daemon path (DOCS-02).

    Non-vacuity guarded twice before the real assertion: the planning root must genuinely be a
    directory, and the scan must genuinely have collected at least one file — a scan that
    silently visited nothing would be the exact false-assurance failure class the audit warned
    about (T-07-06-02).
    """
    assert _PLANNING_ROOT.is_dir(), f"{_PLANNING_ROOT} is not a directory — scan would be vacuous"

    files_to_lines = _collect_planning_lines()
    assert files_to_lines, "collected zero .planning/**/*.md files — scan would be vacuous"

    requirements_lines = files_to_lines.get(_REQUIREMENTS_REL, [])
    docs02_window = _docs02_block_lines(requirements_lines)
    exempt_lines = {_REQUIREMENTS_REL: docs02_window}

    violations = _scan_drift(files_to_lines, _EXEMPT_PREFIXES, exempt_lines)
    detail = {
        f"{path}:{lineno}": text
        for path, lineno in violations
        for file_lineno, text in files_to_lines[path]
        if file_lineno == lineno
    }
    assert violations == [], (
        "active planning artifact names the stale weatherbot/ops/daemon.py path "
        f"(the real path is weatherbot/scheduler/daemon.py): {detail}"
    )


# ---------------------------------------------------------------------------
# Self-proofs — prove the scan logic itself, driven by synthetic data.
# ---------------------------------------------------------------------------


def test_selfproof_drift_scan_catches_unexempted_match():
    """Prove ``_scan_drift`` is not a no-op: an unexempted match MUST be flagged, an exempt-prefix
    match must NOT be, and a benign non-matching line must NOT be. If the scan were ever loosened
    to a no-op, this self-proof goes RED.
    """
    synthetic = {
        "backlog/SOME-REPORT.md": [
            (1, "the origin line still says weatherbot/ops/daemon.py here"),  # must be flagged
        ],
        "v0.1.2-MILESTONE-AUDIT.md": [
            (1, "the finding names weatherbot/ops/daemon.py as the drift"),  # exempt prefix
        ],
        "backlog/OTHER.md": [
            (1, "this line is entirely benign and matches nothing"),  # no match at all
        ],
    }
    leaks = _scan_drift(synthetic, _EXEMPT_PREFIXES, {})
    assert leaks == [("backlog/SOME-REPORT.md", 1)]


def test_selfproof_scan_does_not_exempt_the_line_after_the_block_window():
    """Pin the DOCS-02 exempt window's half-open boundary explicitly.

    A synthetic REQUIREMENTS.md-shaped entry carries two matching lines: one inside the supplied
    ``exempt_lines`` set, one on the very next line, which is not. Only the second must be
    flagged (probe: DOCS-02/adjacency).
    """
    synthetic = {
        _REQUIREMENTS_REL: [
            (5, "inside the window: weatherbot/ops/daemon.py"),
            (6, "just outside the window: weatherbot/ops/daemon.py"),
        ],
    }
    exempt_lines = {_REQUIREMENTS_REL: {5}}
    leaks = _scan_drift(synthetic, (), exempt_lines)
    assert leaks == [(_REQUIREMENTS_REL, 6)]


def test_requirements_docs02_exemption_is_not_a_phantom():
    """The computed DOCS-02 window must be non-empty AND actually contain a matching line.

    Without this, the line-scoped exemption could silently degrade to excusing nothing (or the
    wrong region, after an edit) and the real gate above would prove less than it claims.
    Mirrors ``test_redact_sink_never_imports_structlog``'s "the allowlist is not excusing a
    phantom" assertion at ``tests/test_import_hygiene.py:410-414`` (probe: DOCS-02/empty).
    """
    files_to_lines = _collect_planning_lines()
    requirements_lines = files_to_lines[_REQUIREMENTS_REL]
    docs02_window = _docs02_block_lines(requirements_lines)
    assert docs02_window, "DOCS-02 block locator found nothing — phantom line-scoped exemption"

    has_match_inside_window = any(
        _DRIFT_RE.search(text) for lineno, text in requirements_lines if lineno in docs02_window
    )
    assert has_match_inside_window, (
        "the DOCS-02 window contains no matching line — the exemption excuses nothing real"
    )


def test_every_exempt_prefix_resolves_on_disk():
    """Every ``_EXEMPT_PREFIXES`` entry must match at least one existing path under
    ``_PLANNING_ROOT``, so a typo'd or stale prefix fails loudly instead of quietly exempting
    nothing (probe: DOCS-02/empty).
    """
    for prefix in _EXEMPT_PREFIXES:
        target = _PLANNING_ROOT / prefix
        assert target.exists(), (
            f"exempt prefix {prefix!r} resolves to no existing path under {_PLANNING_ROOT} — "
            "phantom exemption"
        )
