---
phase: 04
slug: cleanup-readygate-fatal
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-28
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Plan-time DRAFT — finalized post-execution by the Nyquist finalizer (`verify:post` → `validate-phase`).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (`pytest>=9.0.3`, per `pyproject.toml`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = ["."]`) |
| **Quick run command** | `uv run pytest tests/test_ready_gate.py -q` (plus the SURF-01 import test file, if separate) |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~0.3 seconds (verified: 71 passed in 0.27s on unmodified HEAD this session) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_ready_gate.py -q` (targeted, sub-second)
- **After every plan wave:** Run `uv run pytest -q` (full suite — 0.27s, no reason to skip)
- **Before `/gsd-verify-work`:** Full suite must be green, including `tests/test_import_hygiene.py`'s three standing gates (grimp graph, isolated-import blocker, AST-litmus)
- **Max feedback latency:** <1 second

---

## Per-Task Verification Map

> Plan/Wave/Task columns are assigned by the planner (plans not yet written at draft time); the
> requirement → test rows below are lifted from RESEARCH.md §Validation Architecture. Every fix is
> **RED-first** — the test must fail against pre-fix source.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | SURF-01 | — | `from yahir_reusable_bot.discord import summon_panel` succeeds | import-smoke | `uv run pytest -k summon_panel_reexport -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SURF-01 | — | `discord/__init__.py` `__all__` contains `"summon_panel"` | unit | `uv run pytest -k summon_panel_all -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LIFE-04 | T-04-01 | Fatal probe → `run()` returns `ReadyOutcome.FATAL`, no re-probe (`stop.wait` never called after fatal) | unit | `uv run pytest tests/test_ready_gate.py::test_fatal_probe_returns_fatal_outcome_no_reprobe -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LIFE-04 | — | Fatal probe → `on_fail` fires exactly once, `on_online` never fires | unit | `uv run pytest tests/test_ready_gate.py::test_fatal_probe_fires_on_fail_not_on_online -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LIFE-04 | — | Non-fatal failing probe path byte-identical to today (severity log + interruptible re-probe still fires) | unit | `uv run pytest tests/test_ready_gate.py::test_non_fatal_failure_still_reprobes -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LIFE-04 | — | Passing probe → `run()` returns `ReadyOutcome.ONLINE`; emit ordering `on_online → log → READY=1` preserved | unit | `uv run pytest tests/test_ready_gate.py::test_online_probe_returns_online_outcome_preserves_ordering -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LIFE-04 | — | `stop`-exhausted loop → `run()` returns `ReadyOutcome.SHUTDOWN` | unit | `uv run pytest tests/test_ready_gate.py::test_stop_set_returns_shutdown_outcome -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LIFE-04 | T-04-01 | `bool(ONLINE) is True` AND `bool(SHUTDOWN) is False` AND `bool(FATAL) is False` (both non-ONLINE members sampled) | unit | `uv run pytest tests/test_ready_gate.py::test_only_online_is_truthy -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LIFE-04 | — | `HealthResult(ok=False, reason="x")` constructs with `fatal` defaulting `False` (additive-field non-regression) | unit | `uv run pytest tests/test_ready_gate.py::test_health_result_fatal_defaults_false -x` | ❌ W0 | ⬜ pending |
| GATE-01 | — | all | SURF-01, LIFE-04 | — | Full suite + import-hygiene/litmus/grimp layering stay green | full suite | `uv run pytest -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ready_gate.py` — NEW file, covers LIFE-04's 7 test rows above (does not exist yet)
- [ ] A SURF-01 import test — either a small new file or an extension of existing import-surface coverage (planner's call per CONTEXT.md discretion)
- [ ] No new fixtures needed in `conftest.py` — existing `fake_stop_event` (`_InstantStopEvent`) is reusable for the no-stop-set shapes; a SHUTDOWN test uses a real pre-`.set()` `threading.Event()`
- Framework install: none — pytest already installed, suite already green

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| WeatherBot de-hack sites named in phase summary | LIFE-04 (H18) | Cross-repo documentation deliverable — the two WeatherBot sites (`scheduler/wiring.py` `_on_fail`, `ops/daemon.py` gate-return) are *documented for the repin*, not touched by this phase | Confirm the phase SUMMARY names both sites for the human-gated repin (ECOSYSTEM.md §3) |

*All in-repo code behaviors have automated verification; the only manual item is the cross-repo repin documentation deliverable.*

---

## Validation Sign-Off

> **Plan-time state is a DRAFT.** Frontmatter stays `status: draft` and `nyquist_compliant: false`.
> These are finalized ONLY post-execution by the Nyquist finalizer (the `verify:post` →
> `validate-phase` hook, invoked by execute-phase `finalize_nyquist_validation` after Gate-1). Never
> set `nyquist_compliant: true` at plan time (INC-2026-07-27-01).

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`tests/test_ready_gate.py` + SURF-01 import test)
- [ ] No watch-mode flags
- [ ] Feedback latency < 1s
- [ ] _(finalizer-only, post-execution)_ `nyquist_compliant` — leave `false` at plan time; the finalizer sets `true` iff its gap analysis finds zero gaps

**Approval:** pending — finalizer-owned, not set at plan time
