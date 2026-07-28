---
gsd_state_version: 1.0
milestone: v0.1.2
milestone_name: — Hub hardening
current_phase: 03
current_phase_name: Reusable public-surface footguns
status: executing
stopped_at: Phase 3 context gathered
last_updated: "2026-07-28T01:01:11.460Z"
last_activity: 2026-07-27
last_activity_desc: Phase 02 complete, transitioned to Phase 03
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 7
  completed_plans: 7
  percent: 50
---

# Project State

## Current Position

Phase: 03 — Reusable public-surface footguns
Plan: Not started
Status: Ready to execute
Last activity: 2026-07-27 — Phase 02 complete, transitioned to Phase 03

## Session

**Last session:** 2026-07-28T00:07:48.982Z
**Stopped at:** Phase 3 context gathered
**Resume file:** .planning/phases/03-public-surface-footguns/03-CONTEXT.md

## Performance Metrics

| Phase | Plan | Duration | Notes |
|-------|------|----------|-------|
| Phase 01 P01 | 15min | 2 tasks | 1 files |
| Phase 01 P02 | ~20min | 2 tasks | 2 files |
| Phase 01 P03 | ~20min | 2 tasks | 2 files |
| Phase 01 P04 | ~25min | 3 tasks | 1 files |
| Phase 02 P01 | 15min | 2 tasks | 2 files |
| Phase 02 P02 | 25min | 3 tasks | 2 files |
| Phase 02 P03 | 10min | 2 tasks | 2 files |

## Decisions

- [Phase ?]: Recreated stale .venv (path mismatch after repo move) before running any Phase 1 verification — Rule 3 blocking-issue fix, no packages changed
- [Phase ?]: Cut phase-01-reachable-reliability from main with zero divergence (D-14); pre-fix baseline for RELY-01/LIFE-01 confirmed by execution
- [Phase ?]: tests/conftest.py founded with exactly two D-10-bounded fixtures (fake_stop_event, cmdline_bytes) — repo's first conftest.py
- [Phase ?]: RELY-01 fixed: is_transient broadened to (TimeoutException, NetworkError, RemoteProtocolError) per D-01/D-02/D-03, deny-by-default preserved
- [Phase ?]: RED-first two-commit proof recorded for RELY-01: test-only commit e7c959d is the direct parent of fix commit f6e4fb2 (D-13)
- [Phase ?]: D-17 hub-scoped restatement encoded literally in the exhaustion test: exhausted RemoteProtocolError must escape Retrying.__call__ as itself, not tenacity.RetryError
- [Phase ?]: LIFE-01 fixed: _argv_matches_marker replaced overlapping-slice membership with a first-`-m`-wins scan (D-04/D-06), bounds-checked, never raises
- [Phase ?]: RED-first two-commit proof recorded for LIFE-01: test-only commit 0f0a9ad is the direct parent of fix commit 5273c13 (D-13)
- [Phase ?]: Signed off 01-VALIDATION.md: RED-first ancestry mechanically proven for both fixes, all four under-sampling risks refuted by named assertions, nyquist_compliant: true
- [Phase ?]: Merged phase-01-reachable-reliability into main with --no-ff (81df616) after explicit developer authorization; RED-first four-commit structure preserved, full suite + GATE-01 re-proven green on main
- [Phase ?]: GATE-01 left unchecked in REQUIREMENTS.md — milestone-standing, spans all 4 phases, only marked complete once green across the whole v0.1.2 milestone
- [Phase ?]: No version bump, tag, repin, uv sync, or deploy performed — all human-gated per ECOSYSTEM.md §3, deferred to after Phase 4
- [Phase ?]: CFG-01 fixed: PHASE-2 reconcile-failure path now fires on_rejected (via _best_effort_hook, reused verbatim) before re-raising, matching PHASE-1's precedent (D-31/D-32)
- [Phase ?]: RED-first two-commit proof recorded for CFG-01: test-only commit 4853c78 is the direct parent of fix commit 3bcd174 (D-13)
- [Phase ?]: DISC-01 fixed: BotThread gains death_reason() (login_failure/crashed) alongside unchanged is_alive() (D-21/D-22/D-23); no hub-side reconnect wrapper
- [Phase ?]: RED-first two-commit proof recorded for DISC-01: test-only commit 510ef05 is the direct parent of fix commit 7173027 (D-13)
- [Phase ?]: DISC-02 fixed: summon_panel per-item delete catch (D-25) + pin-cap headroom-reserve (D-26) closes 2+-live-panels and fresh-but-unpinned bugs; foreign-pin-saturation documented as residual (D-27); create-before-delete preserved (D-24)
- [Phase ?]: RED-first two-commit proof recorded for DISC-02: test-only commit ca5114e is the direct parent of fix commit f06f20e (D-13)
- [Phase ?]: DISC-03 fixed: BotThread.stop() moves run_coroutine_threadsafe inside its existing try (D-28) — never raises on the loop-closed TOCTOU, thread join always reached
- [Phase ?]: RED-first two-commit proof recorded for DISC-03: test-only commit 5b8427d is the direct parent of fix commit 8f715b2 (D-13)
- [Phase ?]: DISC-04 fixed: SelectedContext gains snapshot() (D-29) + extended await-safety docstring (D-30), no lock added, .value unfrozen; contract + API only, wiring.py untouched
- [Phase ?]: RED-first two-commit proof recorded for DISC-04: test-only commit cbc08ae is the direct parent of fix commit d8502e5 (D-13)
