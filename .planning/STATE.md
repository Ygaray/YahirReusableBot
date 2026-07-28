---
gsd_state_version: 1.0
milestone: v0.1.2
milestone_name: — Hub hardening
current_phase: 04
current_phase_name: Cleanup + ReadyGate fatal outcome
status: planning
stopped_at: Phase 4 context gathered
last_updated: "2026-07-28T14:05:22.590Z"
last_activity: 2026-07-28
last_activity_desc: Phase 03 complete, transitioned to Phase 04
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 12
  completed_plans: 12
  percent: 75
---

# Project State

## Current Position

Phase: 04 — Cleanup + ReadyGate fatal outcome
Plan: Not started
Status: Ready to plan
Last activity: 2026-07-28 — Phase 03 complete, transitioned to Phase 04

## Session

**Last session:** 2026-07-28T14:05:22.580Z
**Stopped at:** Phase 4 context gathered
**Resume file:** .planning/phases/04-cleanup-readygate-fatal/04-CONTEXT.md

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
| Phase 03 P01 | 10min | 1 tasks | 2 files |
| Phase 03 P02 | 10min | 2 tasks | 2 files |
| Phase 03 P03 | 6min | 2 tasks | 4 files |
| Phase 03 P04 | 8min | 2 tasks | 2 files |
| Phase 03 P05 | 12min | 2 tasks | 2 files |

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
- [Phase ?]: SCHED-01 fixed: SchedulerEngine.remove idempotent via except KeyError (dependency-free — apscheduler is NOT a hub dependency; JobLookupError IS a KeyError subclass); adds module-level structlog logger (D-38)
- [Phase ?]: RED-first two-commit proof recorded for SCHED-01: test-only commit 0d1f828 is the direct parent of fix commit 5e6fbf8 (D-13)
- [Phase ?]: SchedulerEngine.remove becoming idempotent is a consumer-visible silent->tolerant behavior change, named for the milestone's human-gated close-out (version bump/tag/WeatherBot repin) alongside the two release steps already deferred
- [Phase ?]: LIFE-02 fixed: write_pid_atomic sets fd = -1 after the happy-path os.close, except-path close guarded with if fd != -1 (D-42) — reused fd integer can never be double-closed
- [Phase ?]: LIFE-02 test double is the repo's FIRST monkeypatch use (delegating fake os, real close counted through, deliberate house-style extension, D-09-style flag)
- [Phase ?]: LIFE-03 fixed: _argv_matches_marker basenames both argv[0] and proc_marker (D-39) — fixes non-Linux degrade AND real Linux path-shaped matching; -m branch untouched
- [Phase ?]: RED-first two-commit proof recorded for LIFE-02 (a815e26 -> 0c14258) and LIFE-03 (bbfccca -> 820353f); GATE-01 green at 44 passed
- [Phase ?]: MATCH-02 fixed: CommandRegistry.__init__ raises ValueError inside its existing derivation pass when spec.name is empty or not already casefolded (D-34); no per-match casefold fallback
- [Phase ?]: RED-first two-commit proof recorded for MATCH-02: test-only commit d98d3fc is the direct parent of fix commit fd38b47 (D-13)
- [Phase ?]: MATCH-02's new build-time ValueError is a consumer-visible silent->fail-loud behavior change, named for the milestone's human-gated close-out alongside SCHED-01's idempotent-remove change
- [Phase ?]: MATCH-01 fixed: match.py gains _keyword_boundary(stripped, name) mapping the keyword boundary to the ORIGINAL string index (D-35); fixes arg mis-slice for length-changing casefolds (ss, fi, st); adversarial overshoot folds into the existing continue/non-match
- [Phase ?]: RED-first two-commit proof recorded for MATCH-01: test-only commit 39ababf is the direct parent of fix commit 2fa1908 (D-13); GATE-01 green at 58 passed
- [Phase ?]: RELY-02 fixed: _within_burst_wait guards burst_size <= 1 (D-36), degrades to burst_spread_s instead of raising ZeroDivisionError; burst_size > 1 math unchanged
- [Phase ?]: RED-first two-commit proof recorded for RELY-02: test-only commit 4579dc5 is the direct parent of fix commit 5567a38 (D-13)
- [Phase ?]: RELY-03 fixed: two_burst_wait docstring gains a loud D-37 standalone-desync precondition (stop_after_attempt(2 * burst_size)); no coupling machinery added, function body unchanged
- [Phase ?]: RED-first two-commit proof recorded for RELY-03: test-only commit 5c8b9cb is the direct parent of fix commit 3079e9c (D-13); GATE-01 green at 63 passed
- [Phase ?]: DISC-05 fixed: interaction_check guards if not interaction.user: (falsy, not is None) at the TOP, catching both None and discord.py 2.7.1's real absence sentinel discord.utils.MISSING (RESEARCH Pitfall 1); emits existing reject-log shape, returns False, no ephemeral ack
- [Phase ?]: RED-first two-commit proof recorded for DISC-05: test-only commit 18ea58d is the direct parent of fix commit ed18d8b (D-13); the RED test calls interaction_check directly and never asserts anything about on_error
- [Phase ?]: DISC-06 fixed: PanelKit.__init__ raises ValueError (not assert) when not marker or not marker.strip(), placed right after super().__init__(timeout=None), before collaborator assignments/_build_children/_assert_layout — closes the cid.startswith("") owns-everything hole at the source
- [Phase ?]: RED-first two-commit proof recorded for DISC-06: test-only commit ee73757 is the direct parent of fix commit 2a3e0c7 (D-13); GATE-01 green at 70 passed
- [Phase ?]: Phase 3 complete (5/5 plans): three consumer-visible behavior changes consolidated for the human-gated milestone close-out — D-38 SchedulerEngine.remove idempotent, D-34 CommandRegistry ValueError, D-41 PanelKit empty-marker ValueError; none live in any consumer until repin/deploy (ECOSYSTEM.md §3)
