---
phase: 01-reachable-reliability
verified: 2026-07-22T23:58:06Z
status: passed
score: 8/9 must-haves verified
behavior_unverified: 1 # the concurrent/interrupted-retry backstop truth — present by non-modification, no test exercises it
overrides_applied: 0
re_verification: null
behavior_unverified_items:

  - truth: "Concurrent and interrupted retry behavior is unchanged by this phase — build_retrying's sleep=stop_event.wait interruptibility wiring (retry.py:241, now :265) and its retry_error_callback (retry.py:247, now :271) are not modified, and the broadened is_transient introduces no shared mutable state, so a Retrying driven from two threads classifies identically and a mid-schedule shutdown still abandons the pause."
    test: "Drive build_retrying from two threads concurrently against a stop_event that gets .set() mid-schedule, and confirm (a) both threads classify the same exception identically and (b) the interrupted thread abandons its pause rather than completing the full mid_pause_s wait."
    expected: "Identical classification across threads; the interrupted schedule exits early rather than sleeping the full pause."
    why_human: "No test in this phase drives Retrying from two threads or interrupts a mid-schedule pause — this is asserted by non-modification of the wiring, not by execution. The plan's own <verification> section explicitly marks this `verification: backstop` and states it abstains to human_needed absent explicit evidence. Grep/presence checks cannot prove a concurrency invariant."
human_verification:

  - test: "Drive build_retrying from two threads concurrently against a stop_event that gets .set() mid-schedule."
    expected: "Both threads classify the triggering exception identically (is_transient is pure/stateless); the interrupted thread's schedule abandons the pause rather than completing the full mid_pause_s (production default 2700s) wait."
    why_human: "Flagged by Plan 02's own must_haves as `verification: backstop` — an assumption asserted by non-modification of build_retrying's sleep=stop_event.wait wiring and retry_error_callback, not exercised by any test in this phase. The plan explicitly states this abstains to human_needed unless explicit evidence is produced; this is by design, not an oversight."
---

# Phase 1: Reachable reliability Verification Report

**Phase Goal:** Close the only two defects live and unmitigated in a real consumer today.
**Verified:** 2026-07-22T23:58:06Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `is_transient` classifies `RemoteProtocolError`/`WriteError` transient; drives the two-burst retry; exhaustion escapes `Retrying.__call__` as itself (D-17 hub-scoped restatement of `transient_exhausted`) | ✓ VERIFIED | Live check on current `main`: `is_transient(RemoteProtocolError('x')) is True`, `is_transient(WriteError('x')) is True`. `tests/test_retry.py::test_exhausted_transient_escapes_as_itself_after_full_budget` drives the real `build_retrying(fake_stop_event, attempts_per_burst=2, burst_spread_s=0, mid_pause_s=0)`, asserts exactly 4 attempts and `type(exc_info.value) is httpx.RemoteProtocolError` (never `tenacity.RetryError`). `REASON_TRANSIENT_EXHAUSTED` confirmed defined at `retry.py:75`, assigned only consumer-side — the hub-scoped restatement is the only assertable form and it is asserted. Test passes (`uv run pytest tests/test_retry.py -v` → 7 passed). |
| 2 | `LocalProtocolError` still classifies non-transient (deny-by-default, not a blanket `TransportError`) | ✓ VERIFIED | Live check: `is_transient(LocalProtocolError('x')) is False`. `tests/test_retry.py::test_classification_excludes_local_protocol_error` and `test_classification_excludes_proxy_error_and_unsupported_protocol` pass, proving `ProxyError`/`UnsupportedProtocol` also stay non-transient — a blanket `TransportError` rule would have flipped both. |
| 3 | Identity guard does not match the recycled-PID positional decoy (`python -m pytest <marker>`); does match `python -O -m <marker> run` | ✓ VERIFIED | Live check on current `main`: decoy argv → `False`; one-flag daemon argv → `True`. Source at `identity.py:185-190` implements a first-`-m`-wins scan with bounds-checked exact adjacency, replacing the old overlapping-slice test. All 7 `tests/test_identity.py` rows pass. |
| 4 | New regression tests for both fail against pre-fix source (RED-first, D-13) | ✓ VERIFIED | Mechanically re-proven this session (not merely trusted from SUMMARY): checked out `yahir_reusable_bot/reliability/retry.py` and `yahir_reusable_bot/lifecycle/identity.py` at pre-phase commit `6baf992`, ran the current `tests/test_retry.py` and `tests/test_identity.py` against them. Result: `test_retry.py` → 4 failed/3 passed (`test_classification_includes_remote_protocol_error`, `test_classification_includes_network_errors`, `test_classification_is_pure_and_repeatable`, `test_exhausted_transient_escapes_as_itself_after_full_budget` — the last failing on `assert 1 == 4`, not a type-only assertion); `test_identity.py` → 2 failed/5 passed (`test_decoy_positional_marker_arg_does_not_match` failing `assert True is False` — the live security defect — and `test_two_interpreter_flags_before_module_switch_matches`). Both counts match the SUMMARY verbatim. Working tree restored via `cp` from backup; `git status --porcelain` confirmed only the three pre-existing unrelated modifications remained, and `uv run pytest` returned to 23 passed after restore. |
| 5 | Git history structurally proves RED-first ordering (independent of the SUMMARY narrative) | ✓ VERIFIED | `git merge-base --is-ancestor e7c959d f6e4fb2` succeeds; `e7c959d` touches exactly `tests/test_retry.py`; `f6e4fb2` touches exactly `yahir_reusable_bot/reliability/retry.py`. `git merge-base --is-ancestor 0f0a9ad 5273c13` succeeds; `0f0a9ad` touches exactly `tests/test_identity.py`; `5273c13` touches exactly `yahir_reusable_bot/lifecycle/identity.py`. Merge commit `81df616` has exactly 2 parents (`git log -1 --format=%P` → two SHAs) — a real `--no-ff`, not flattened. All four fix/test commits plus the merge commit are reachable from `main` (`git merge-base --is-ancestor <c> main` succeeds for all five). |
| 6 | GATE-01 (full suite + import-hygiene gates) stays green across the phase | ✓ VERIFIED | `uv run pytest` on current `main` → 23 passed. `uv run pytest tests/test_import_hygiene.py` → 8 passed. GATE-01 correctly left `[ ]` unchecked in `.planning/REQUIREMENTS.md` (milestone-standing, spans all 4 phases) — this is deliberate, not a gap, per the Plan 01 traceability note the phase consistently follows. |
| 7 | Zero dependency change across the phase | ✓ VERIFIED | `git diff 6baf992...HEAD -- pyproject.toml uv.lock` produces empty output. |
| 8 | Merge to `main` only after full suite green on branch; `main` green post-merge (D-14) | ✓ VERIFIED | Merge commit `81df616` on `main`; `uv run pytest` and `uv run pytest tests/test_import_hygiene.py` both green on current `main` (23/8 passed), independently re-run this session, not merely inherited from the SUMMARY's claim. |
| 9 | Concurrent and interrupted retry behavior is unchanged (Plan 02 `must_haves.truths`, `verification: backstop`) | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | `build_retrying`'s `sleep=stop_event.wait` wiring (now `retry.py:265`) and `retry_error_callback` (now `retry.py:271`) are confirmed unmodified by this phase's diff, and `is_transient` introduces no new module-level state (pure function, confirmed by `test_classification_is_pure_and_repeatable`). But no test in this phase drives `Retrying` from two threads or interrupts a mid-schedule pause — the plan's own frontmatter marks this truth `verification: backstop` and its `<verification>` section states explicitly that it abstains to `human_needed` absent explicit evidence. Presence/non-modification is not behavioral proof of a concurrency invariant. |

**Score:** 8/9 truths verified (1 present + wired by non-modification, behavior-unverified per the plan's own declared backstop)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/conftest.py` | Two fixtures: `fake_stop_event`, `cmdline_bytes`; no `httpx`/`tenacity`/`yahir_reusable_bot` imports | ✓ VERIFIED | Exists, defines exactly `cmdline_bytes` and `fake_stop_event` plus `_InstantStopEvent`; no forbidden imports. |
| `tests/test_retry.py` | 7 tests, drives real `build_retrying`, no hand-rolled `tenacity.Retrying` | ✓ VERIFIED | 7 module-level `test_*` functions present, `build_retrying` imported and driven directly, no `Retrying(` construction. |
| `tests/test_identity.py` | 7 tests, all through public `is_running_process` seam with `cmdline_reader=` injection | ✓ VERIFIED | 7 functions present, `is_running_process` called with `cmdline_reader=` in every test, no raw `/proc` access. |
| `yahir_reusable_bot/reliability/retry.py` | `is_transient` broadened to `(TimeoutException, NetworkError, RemoteProtocolError)` | ✓ VERIFIED | Confirmed via live execution and source read; docstring carries D-01/D-02/D-03 rationale. |
| `yahir_reusable_bot/lifecycle/identity.py` | `_argv_matches_marker` uses first-`-m`-wins scan | ✓ VERIFIED | Confirmed via live execution and source read (`enumerate` loop at lines 185-190); argv0-basename branch byte-identical to pre-fix. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `tests/test_retry.py` | `yahir_reusable_bot/reliability/retry.py` | imports real `build_retrying`/`is_transient`, no hand-rolled `Retrying` | ✓ WIRED | Confirmed by source read and shape check (`Retrying(` absent). |
| `tests/test_retry.py` | `tests/conftest.py` | consumes `fake_stop_event` | ✓ WIRED | Test signature takes `fake_stop_event` fixture parameter, used in `build_retrying(fake_stop_event, ...)`. |
| `tests/test_identity.py` | `yahir_reusable_bot/lifecycle/identity.py` | calls public `is_running_process` with injected `cmdline_reader=` | ✓ WIRED | Confirmed 7/7 calls use the public seam. |
| `tests/test_identity.py` | `tests/conftest.py` | consumes `cmdline_bytes` | ✓ WIRED | All 7 tests take `cmdline_bytes` fixture parameter. |
| `phase-01-reachable-reliability` | `main` | `--no-ff` merge after green gates, authorized at Task 2 checkpoint | ✓ WIRED | Merge commit `81df616` has 2 parents; developer "approved" recorded in `01-04-SUMMARY.md`; post-merge suite re-run green on `main`. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| RELY-01 classifier + exhaustion escape, live on `main` | `uv run python -c "..."` asserting `is_transient` truth table + `build_retrying` exhaustion behavior | `ALL CRITERIA LIVE ON CURRENT MAIN` | ✓ PASS |
| LIFE-01 truth table, live on `main` | Same one-liner, `is_running_process` decoy + flagged-daemon rows | Both assertions passed | ✓ PASS |
| RED-first proof, mechanically re-run (not trusted from SUMMARY) | Checked out pre-fix `retry.py`/`identity.py` at `6baf992`, ran `tests/test_retry.py` and `tests/test_identity.py` against them, restored | `test_retry.py`: 4 failed/3 passed; `test_identity.py`: 2 failed/5 passed — matches SUMMARY verbatim, attempt-count assertion (`1 == 4`) and decoy assertion (`True is False`) confirmed load-bearing | ✓ PASS |
| Full suite on `main` | `uv run pytest -q` | `23 passed` | ✓ PASS |
| Import-hygiene gate (GATE-01) | `uv run pytest tests/test_import_hygiene.py -q` | `8 passed` | ✓ PASS |
| Dependency immutability | `git diff 6baf992...HEAD -- pyproject.toml uv.lock` | empty | ✓ PASS |
| Merge structure | `git log -1 --format=%P 81df616` \| wc -w | `2` (real `--no-ff`, not flattened) | ✓ PASS |

### Probe Execution

Step 7c: SKIPPED (no runnable entry points / no probe scripts found — this is not a migration or tooling phase; `find scripts -path '*/tests/probe-*.sh'` returned nothing, and no PLAN/SUMMARY references a probe).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| RELY-01 (H02) | 01-02 | `is_transient` broadening | ✓ SATISFIED | Marked `[x]` in REQUIREMENTS.md; live behavior confirmed above; git ancestry confirmed. |
| LIFE-01 (H01) | 01-03 | `_argv_matches_marker` first-`-m` scan | ✓ SATISFIED | Marked `[x]` in REQUIREMENTS.md; live behavior confirmed above; git ancestry confirmed. |
| GATE-01 | 01-01/02/03/04 | full suite + import-hygiene stays green | ✓ SATISFIED (phase contribution only) | Correctly left `[ ]` unchecked — milestone-standing, spans all 4 phases per Plan 01's own traceability note. This phase's contribution (zero regressions across both fixes) is verified green; the box should NOT be checked until Phase 4 closes, and it correctly is not. |

No orphaned requirements: cross-referencing `.planning/REQUIREMENTS.md`, only RELY-01, LIFE-01, and the milestone-standing GATE-01 map to Phase 1; all three appear in at least one plan's `requirements:` frontmatter field.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `yahir_reusable_bot/lifecycle/identity.py` | 121 | `E731` lambda assignment (ruff) | ℹ️ Info | Pre-existing, confirmed unrelated to this phase's fix (untouched by `git diff HEAD~1 HEAD` at the LIFE-01 fix commit); logged in `deferred-items.md` by Plans 02/03; independently re-confirmed this session (`uv run ruff check` scoped to phase files reports exactly this one error). Not a phase-introduced regression. |
| `yahir_reusable_bot/lifecycle/identity.py` | 160-177 (docstring) | "KNOWN LIMITATION" note (attached `-mmodule` form false negative, WR-01) | ℹ️ Info | Pre-existing inherited gap (identical in pre-fix `argv[1:3]`/`argv[1:4]` window), not a phase regression. Only the documentation half was applied (`0296c17`, docstring-only — confirmed via `git show --stat` showing 1 file, 17 insertions/5 deletions, all within the docstring); the behavioral question is deliberately left pending human decision per `01-REVIEW-FIX.md`. This is an accepted, tracked-gap disposition, not a silent drop — assessed as defensible for this phase's goal (closing the two ROADMAP-locked live defects), since the attached-`-m` form is a distinct, pre-existing gap outside this phase's two named defects. |

No `TBD`/`FIXME`/`XXX` markers found in any file modified by this phase (`tests/conftest.py`, `tests/test_retry.py`, `tests/test_identity.py`, `yahir_reusable_bot/reliability/retry.py`, `yahir_reusable_bot/lifecycle/identity.py`). No blocker-level anti-patterns found.

### Human Verification Required

#### 1. Concurrent / interrupted retry behavior (RELY-01 backstop truth)

**Test:** Drive `build_retrying` from two threads concurrently against a `fake_stop_event`-style double that gets `.set()` (or equivalent "shutdown requested") mid-schedule, and confirm (a) both threads classify the same triggering exception identically via `is_transient`, and (b) the interrupted thread's retry schedule abandons its pause rather than completing the full `mid_pause_s` wait (production default 2700s).
**Expected:** Identical classification across threads (no shared mutable state); early abandonment of the pause on interruption.
**Why human:** This is Plan 02's own declared `must_haves.truths` entry with `verification: backstop` — the plan's `<verification>` section states explicitly: "this truth abstains to `human_needed` unless explicit evidence is produced — that is intended, not a gap to paper over." No test in this phase exercises mid-schedule interruption or parallel invocation; the claim rests on non-modification of `build_retrying`'s `sleep=stop_event.wait` wiring and `retry_error_callback`, which is necessary but not sufficient proof of a concurrency invariant. Presence/non-modification checks cannot substitute for a concurrency test.

## Known-State Items Assessed (not reported as new gaps, per phase instructions)

- **4 pre-existing repo-wide `ruff check` errors** outside this phase's touched files — independently re-confirmed this session, unchanged in count and location; logged in `deferred-items.md`. Adequate handling.
- **WR-01 (attached `-mmodule` form false negative)** — inherited pre-existing gap, only documentation applied (`0296c17`, confirmed docstring-only), behavioral fix deliberately deferred to human decision. Assessed as defensible: this is a distinct gap from the two ROADMAP-locked defects (RELY-01/LIFE-01) this phase's goal targets, and leaving it as an honestly-tracked gap (rather than silently fixing or silently ignoring it) is the correct disposition for a phase whose scope is explicitly the two named live defects.
- **Unresolved LIFE-01 edge-probe item (consumer-side concurrent-signal race)** — correctly carried forward in `01-03-SUMMARY.md` and `01-04-SUMMARY.md` as an unclassified, never-auto-dismissed probe row. Consumer-side (WeatherBot's reload/signal path) and outside this hub repo's Architectural Responsibility Map — no test in this repo could assert it without replicating consumer logic, which the phase's own D-18 reasoning correctly rejects. Not listed as a human-verification item here because it is not resolvable within this repo's scope; correctly documented as an external follow-up rather than silently dropped.
- **Plan 01-02 executor's prohibited `git stash`/`git stash pop` use** — self-caught, recovered, and independently re-verified this session: `git status --porcelain` on current `main` shows only the three pre-existing unrelated modifications (`.planning/config.json`, `ECOSYSTEM.md`, `uv.lock`), and `e7c959d`/`f6e4fb2` each touch exactly their expected single file. Final state is clean.
- **`.planning/config.json`, `ECOSYSTEM.md`, `uv.lock`** pre-existing uncommitted modifications — confirmed still present, untouched by this phase, and correctly left alone throughout this verification (restored via targeted `cp`, never `git checkout .` or `git add -A`).

### Gaps Summary

No blocking gaps. All four ROADMAP-locked success criteria are mechanically verified against the actual codebase, not merely accepted from SUMMARY.md narrative — including the git-history-dependent RED-first claim (criterion 4), which was independently re-proven this session by checking out pre-fix source and re-running the current test files against it (results matched the SUMMARY verbatim on both failure counts and the specific failing assertions). The only open item is a single human-verification point that the phase's own plan frontmatter explicitly and correctly flagged in advance as a `backstop`-tier truth requiring human confirmation rather than claiming false completeness — this is honest self-accounting by the phase, not a gap the phase tried to hide.

---

_Verified: 2026-07-22T23:58:06Z_
_Verifier: Claude (gsd-verifier)_
