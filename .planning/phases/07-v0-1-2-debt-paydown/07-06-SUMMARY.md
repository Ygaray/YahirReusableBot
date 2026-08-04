---
phase: 07-v0-1-2-debt-paydown
plan: 06
subsystem: testing
tags: [doc-drift, standing-gate, pytest, planning-hygiene]

# Dependency graph
requires:
  - phase: 07-v0-1-2-debt-paydown (plan 05)
    provides: current on-disk REQUIREMENTS.md / v0.1.2-MILESTONE-AUDIT.md shape (LIFE-05 edits) this plan built on top of
provides:
  - "tests/test_doc_drift.py — the standing DOCS-02 gate scanning every .planning/**/*.md for the bare ops[/.]daemon regex, with two self-proofs and two phantom-exemption guards"
  - "Corrected active planning artifacts (REQUIREMENTS.md, HUB-HARDENING-REPORT-v0.1.2.md) naming all three consumer de-hack sites including the producing site"
  - "Seven archived v0.1.2 phase-4 files annotated with a drift banner, bodies byte-unchanged"
affects: [07-07, any future doc-drift correction]

# Tech tracking
tech-stack:
  added: []
  patterns: ["standing pytest scan gate with an explicit exempt-list plus a self-proof (mirrors tests/test_import_hygiene.py's shared-helper convention)"]

key-files:
  created:
    - tests/test_doc_drift.py
  modified:
    - .planning/REQUIREMENTS.md
    - .planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md
    - .planning/v0.1.2-MILESTONE-AUDIT.md
    - .planning/milestones/v0.1.2-phases/04-cleanup-readygate-fatal/04-01-PLAN.md
    - .planning/milestones/v0.1.2-phases/04-cleanup-readygate-fatal/04-01-SUMMARY.md
    - .planning/milestones/v0.1.2-phases/04-cleanup-readygate-fatal/04-02-SUMMARY.md
    - .planning/milestones/v0.1.2-phases/04-cleanup-readygate-fatal/04-CONTEXT.md
    - .planning/milestones/v0.1.2-phases/04-cleanup-readygate-fatal/04-RESEARCH.md
    - .planning/milestones/v0.1.2-phases/04-cleanup-readygate-fatal/04-VALIDATION.md
    - .planning/milestones/v0.1.2-phases/04-cleanup-readygate-fatal/04-VERIFICATION.md

key-decisions:
  - "Gate regex is the bare ops[/.]daemon form, not weatherbot-prefixed — confirmed live that a fully-qualified pattern would miss the three bare-form archive sites (04-CONTEXT.md:48, 04-RESEARCH.md:15, 04-VALIDATION.md:77)"
  - "DOCS-02 exemption is line-scoped (content-located block, half-open at the next sibling bullet), not a whole-file exemption — REQUIREMENTS.md's DOCS-02 bullet keeps naming the stale path as the error being described, but the rest of the file must not"
  - "Corrected prose in the two active sites avoids repeating the stale literal weatherbot/ops/daemon.py — describes the error ('does not exist as spelled') rather than quoting it, so the correction itself never re-triggers the drift it fixes"
  - "Archive banners word the correction without repeating the stale path literal either, even though the whole milestones/ subtree is gate-exempt — a correctness-of-prose choice, not a gate requirement"

patterns-established:
  - "_scan_drift(files_to_lines, exempt_prefixes, exempt_lines) — pure, sorted, driven identically by the real gate and by two synthetic self-proofs, mirroring test_import_hygiene.py's _scan_app_leaks/_scan_framework_leaks shape"
  - "_docs02_block_lines(lines) — content-located exemption window (not (path, line_number) tuples), half-open at the next sibling bullet or heading, avoiding the line-number self-invalidation an actively-edited REQUIREMENTS.md would otherwise cause"

requirements-completed: [DOCS-02, DOCS-03]

coverage:
  - id: D1
    description: "Standing pytest gate scans every .planning/**/*.md for the bare ops[/.]daemon regex and fails on any unexempted match"
    requirement: "DOCS-02"
    verification:
      - kind: unit
        ref: "tests/test_doc_drift.py#test_no_active_planning_artifact_names_the_stale_daemon_path"
        status: pass
    human_judgment: false
  - id: D2
    description: "Gate is proven non-vacuous: self-proof catches an injected unexempted match, the DOCS-02 window boundary is half-open, the DOCS-02 exemption is non-phantom, and every exempt prefix resolves on disk"
    requirement: "DOCS-02"
    verification:
      - kind: unit
        ref: "tests/test_doc_drift.py#test_selfproof_drift_scan_catches_unexempted_match"
        status: pass
      - kind: unit
        ref: "tests/test_doc_drift.py#test_selfproof_scan_does_not_exempt_the_line_after_the_block_window"
        status: pass
      - kind: unit
        ref: "tests/test_doc_drift.py#test_requirements_docs02_exemption_is_not_a_phantom"
        status: pass
      - kind: unit
        ref: "tests/test_doc_drift.py#test_every_exempt_prefix_resolves_on_disk"
        status: pass
    human_judgment: false
  - id: D3
    description: "The two active artifacts (REQUIREMENTS.md, HUB-HARDENING-REPORT-v0.1.2.md) name the corrected, real gate-return path and the producing site, three sites total"
    requirement: "DOCS-03"
    verification:
      - kind: manual_procedural
        ref: "manual read of the corrected REQUIREMENTS.md and HUB-HARDENING-REPORT-v0.1.2.md text against this SUMMARY's filesystem-evidence record (D-67 mechanism 2, per 07-RESEARCH.md Open Question 2's manual-only recommendation)"
        status: pass
    human_judgment: true
    rationale: "DOCS-03 is deliberately manual-only per 07-RESEARCH.md Open Question 2 — a positive-content grep test would be over-fitted prose-coupled churn, updating every time the enumeration's wording changes. The corrected three-site enumeration is verified below and mechanically checked by the plan's grep-count acceptance criteria, but the final sign-off is a human read."
  - id: D4
    description: "Seven archived v0.1.2 phase-4 files gain a one-line drift banner; bodies (including the 04-01-PLAN.md <automated> check that is the audit's own headline-lesson evidence) stay byte-unchanged"
    requirement: "DOCS-02"
    verification:
      - kind: unit
        ref: "git diff --stat -- .planning/milestones/ (insertions only, 14 insertions across exactly 7 files, zero deletions)"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-08-04
status: complete
---

# Phase 7 Plan 6: Standing doc-drift gate + corrected de-hack enumeration Summary

**New `tests/test_doc_drift.py` standing gate (bare `ops[/.]daemon` regex, content-located line-scoped exemption, four non-vacuity guards) closes DOCS-02/DOCS-03: the two active planning artifacts now name the real `weatherbot/scheduler/daemon.py` gate-return path plus the producing site `weatherbot/ops/selfcheck.py`, and the seven archived v0.1.2 phase-4 files carry a drift banner with bodies preserved byte-unchanged.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-08-03T23:15Z (approx.)
- **Completed:** 2026-08-04T05:31Z
- **Tasks:** 3
- **Files modified:** 10 (1 created, 9 modified)

## Accomplishments

- Created `tests/test_doc_drift.py`, mirroring `tests/test_import_hygiene.py`'s "every gate has a self-proof" convention: a real gate plus two synthetic self-proofs plus two phantom-exemption guards, all driven through the same `_scan_drift`/`_docs02_block_lines` helpers.
- The gate's `_DRIFT_RE = re.compile(r"ops[/.]daemon")` is deliberately bare — confirmed live it catches all three archive sites that write the unprefixed form, which a `weatherbot/ops/daemon`-qualified pattern would have missed (the audit's own headline lesson, avoided at gate-authoring time this time).
- Corrected the two genuinely-active drift sites (`REQUIREMENTS.md`'s human-gated close-out block, `HUB-HARDENING-REPORT-v0.1.2.md`'s H18 origin sentence) to name three de-hack sites — `weatherbot/scheduler/wiring.py:_on_fail`, `weatherbot/scheduler/daemon.py` (corrected path), and `weatherbot/ops/selfcheck.py:to_health_result` (the producing site) — with the generalizable rule recorded that a de-hack enumeration must name the site that produces the input, not only the sites that consume the outcome.
- Corrected `REQUIREMENTS.md`'s DOCS-02 bullet's stale "11 artifacts" count to the live, twice-independently-reproduced figure of 9 files / 14 lines of genuine drift.
- Annotated `.planning/v0.1.2-MILESTONE-AUDIT.md` with a blockquote correction note after the DOC-DRIFT-01 paragraph (the paragraph itself and the Tech Debt table stay byte-unchanged, per the archive-is-evidence rule).
- Annotated all seven archived `04-cleanup-readygate-fatal/` files with an identical one-line drift banner, placed after YAML frontmatter where present or at the top otherwise; bodies — including `04-01-PLAN.md`'s `<automated>` check that is the primary evidence for the audit's headline lesson — are byte-unchanged (`git diff --stat` shows insertions only, 14 insertions / 0 deletions across exactly the 7 target files).
- Gate genuinely went RED first against the real tree (exactly the two active drift sites) before Task 2's correction turned it GREEN with zero exemptions added.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create the standing doc-drift gate, committed RED** - `2793076` (test)
2. **Task 2: Correct the two active artifacts and complete the enumeration (GREEN)** - `824702e` (docs)
3. **Task 3: Annotate the seven archived v0.1.2 phase-4 files with a drift banner** - `058ff75` (docs)

## Files Created/Modified

- `tests/test_doc_drift.py` - New standing gate: `_PLANNING_ROOT`, `_DRIFT_RE`, `_REQUIREMENTS_REL`, `_EXEMPT_PREFIXES`, `_collect_planning_lines`, `_docs02_block_lines`, `_scan_drift`, and 5 test functions (the real gate + 2 self-proofs + 2 phantom-exemption guards)
- `.planning/REQUIREMENTS.md` - Human-gated close-out block corrected to name all three de-hack sites with the producing-site reasoning; DOCS-02 bullet's stale "11 artifacts" count corrected to "9 files / 14 lines"
- `.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md` - H18's "Consumer de-hack after ship+repin" sentence corrected to name the real gate-return path plus the producing site
- `.planning/v0.1.2-MILESTONE-AUDIT.md` - Blockquote correction note added after DOC-DRIFT-01 paragraph; the paragraph itself and the Tech Debt table are unchanged
- `.planning/milestones/v0.1.2-phases/04-cleanup-readygate-fatal/{04-01-PLAN,04-01-SUMMARY,04-02-SUMMARY,04-CONTEXT,04-RESEARCH,04-VALIDATION,04-VERIFICATION}.md` - Each gains an identical one-line drift banner; bodies unrevised

## Filesystem evidence (one-time, D-67 mechanism 2)

Re-verified 2026-08-04 against the live `/home/yahir/Projects/WeatherBot` checkout:

```
$ for p in weatherbot/ops/daemon.py weatherbot/scheduler/daemon.py weatherbot/ops/selfcheck.py weatherbot/scheduler/wiring.py; do test -f "/home/yahir/Projects/WeatherBot/$p" && echo "EXISTS $p" || echo "ABSENT $p"; done
ABSENT weatherbot/ops/daemon.py
EXISTS weatherbot/scheduler/daemon.py
EXISTS weatherbot/ops/selfcheck.py
EXISTS weatherbot/scheduler/wiring.py
```

The nonexistent path named by the original drift is confirmed absent; the corrected gate-return path, the producing site, and the fatal-branch consumer all confirmed present.

## De-hack sites (DOCS-03)

The corrected enumeration in both `.planning/REQUIREMENTS.md` and
`.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md` now names all three sites:

1. `weatherbot/scheduler/wiring.py:_on_fail` — the fatal-branch `threading.Event` de-hack (consumer).
2. `weatherbot/scheduler/daemon.py` — the gate-return exit-code check (consumer; the **corrected** path — `weatherbot/ops/daemon.py` does not exist).
3. `weatherbot/ops/selfcheck.py:to_health_result` — the **producing** site. Without it classifying `CONFIG_INVALID` as fatal, `HealthResult.fatal` is never set and the `ReadyOutcome.FATAL` branch is unreachable downstream.

## Decisions Made

- Gate regex kept bare (`ops[/.]daemon`, not `weatherbot/ops[/.]daemon`) — verified this is the only form that catches all 14 historical drift lines, including the three archive sites that write the unprefixed spelling.
- Corrected prose in the two active artifacts and in all seven archive banners avoids repeating the stale literal `weatherbot/ops/daemon.py` — phrased as "does not exist as spelled" / "the corrected path" instead. This keeps the correction from ever quoting the exact string it is correcting, even though the archive subtree is gate-exempt regardless (a correctness-of-prose choice per the plan, not a gate requirement).
- DOCS-02's REQUIREMENTS.md exemption stayed line-scoped and content-located (`_docs02_block_lines`, half-open at the next sibling bullet), not converted to a whole-file exemption — the DOCS-02 bullet itself is allowed to keep naming the stale path as the error being described, but the "Human-gated close-out" block two sections above it is not, and the gate now enforces that boundary precisely.

## Deviations from Plan

None — plan executed exactly as written. One clarification worth recording: the plan's illustrative corrected-text wording ("the real path — `weatherbot/ops/daemon.py` does not exist") would itself have tripped the new gate on the two active sites (the stale literal falls outside both the exempt prefixes and the DOCS-02 line-scoped window). Task 1's RED-first sequencing caught this immediately when Task 2's first draft re-ran the gate — the correction was reworded to describe the error without repeating the literal path, and the gate went GREEN with zero exemptions added, exactly as `git diff HEAD~1 -- tests/test_doc_drift.py` (empty) confirms. This is exactly the kind of self-check the phase exists to prove works.

## Issues Encountered

None beyond the wording iteration noted above, which self-resolved via the gate.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `tests/test_doc_drift.py` is a standing gate — any future planning-doc edit that reintroduces the bare or qualified `ops/daemon` string outside an exempt prefix/line will now fail the suite immediately.
- DOCS-02 and DOCS-03 are both closed; 07-07 (the final plan of Phase 7) can proceed without doc-drift as an open item.
- Full suite: 184 passed, zero warnings (`uv run pytest -q -o 'filterwarnings=error'`); `tests/test_import_hygiene.py`: 10 passed; `uv run ruff check`: clean.

---
*Phase: 07-v0-1-2-debt-paydown*
*Completed: 2026-08-04*
