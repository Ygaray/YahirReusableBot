---
phase: 04
slug: cleanup-readygate-fatal
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-28
validated: 2026-07-28
---

# Phase 04 — Validation Strategy

> Per-phase validation contract. **Finalized post-execution** by the Nyquist finalizer
> (`verify:post` → `validate-phase`, auto mode): every phase requirement has a passing automated
> test — zero coverage gaps — so `nyquist_compliant: true`.

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

> Finalized against the executed phase. Every row's test now exists and passes (full suite: 80
> passed; the LIFE-04 + SURF-01 files: 9 passed). Each fix was **RED-first** — the RED test commit
> (`175072b`, `1e762bf`) precedes its GREEN fix commit (`d7939d8`, `eefffc9`), independently
> re-verified by the phase verifier against pre-fix source.

| Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File | Status |
|------|------|-------------|------------|-----------------|-----------|-------------------|------|--------|
| 04-02 | 1 | SURF-01 | — | `from yahir_reusable_bot.discord import summon_panel` succeeds; `discord.__all__` contains it | import-smoke | `uv run pytest tests/test_discord_surface.py::test_summon_panel_reexport_succeeds -x` | ✅ | ✅ green |
| 04-02 | 1 | SURF-01 (D-47 scope) | — | `summon_panel` NOT surfaced at top-level `yahir_reusable_bot` (guard; WR-01) | unit | `uv run pytest tests/test_discord_surface.py::test_summon_panel_not_widened_to_top_level_package -x` | ✅ | ✅ green |
| 04-01 | 1 | LIFE-04 | T-04-01 | Fatal probe → `run()` returns `ReadyOutcome.FATAL`, no re-probe | unit | `uv run pytest tests/test_ready_gate.py::test_fatal_probe_returns_fatal_outcome_no_reprobe -x` | ✅ | ✅ green |
| 04-01 | 1 | LIFE-04 | — | Fatal probe → `on_fail` fires, `on_online` never fires | unit | `uv run pytest tests/test_ready_gate.py::test_fatal_probe_fires_on_fail_not_on_online -x` | ✅ | ✅ green |
| 04-01 | 1 | LIFE-04 | — | Non-fatal failing probe path byte-identical (severity log + interruptible re-probe still fires) | unit | `uv run pytest tests/test_ready_gate.py::test_non_fatal_failure_still_reprobes -x` | ✅ | ✅ green |
| 04-01 | 1 | LIFE-04 | — | Passing probe → `ReadyOutcome.ONLINE`; emit ordering `on_online → log → READY=1` preserved | unit | `uv run pytest tests/test_ready_gate.py::test_online_probe_returns_online_outcome_preserves_ordering -x` | ✅ | ✅ green |
| 04-01 | 1 | LIFE-04 | — | `stop`-exhausted loop → `ReadyOutcome.SHUTDOWN` | unit | `uv run pytest tests/test_ready_gate.py::test_stop_set_returns_shutdown_outcome -x` | ✅ | ✅ green |
| 04-01 | 1 | LIFE-04 | T-04-01 | `bool(ONLINE) is True` AND `bool(SHUTDOWN) is False` AND `bool(FATAL) is False` (both non-ONLINE sampled) | unit | `uv run pytest tests/test_ready_gate.py::test_only_online_is_truthy -x` | ✅ | ✅ green |
| 04-01 | 1 | LIFE-04 | — | `HealthResult(ok=False, reason="x")` constructs with `fatal` defaulting `False` (additive-field) | unit | `uv run pytest tests/test_ready_gate.py::test_health_result_fatal_defaults_false -x` | ✅ | ✅ green |
| both | all | GATE-01 | — | Full suite + import-hygiene/litmus/grimp layering stay green | full suite | `uv run pytest -q` (80) · `uv run pytest tests/test_import_hygiene.py -q` (8) | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_ready_gate.py` — created; covers LIFE-04's 7 test rows above (7 passed)
- [x] SURF-01 import test — created as `tests/test_discord_surface.py` (2 passed, incl. the WR-01 top-level guard)
- [x] No new fixtures needed in `conftest.py` — existing `fake_stop_event` (`_InstantStopEvent`) reused for the no-stop-set shapes; the SHUTDOWN test uses a real pre-`.set()` `threading.Event()`
- Framework install: none — pytest already installed, suite green

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| WeatherBot de-hack sites named in phase summary | LIFE-04 (H18) | Cross-repo documentation deliverable — the two WeatherBot sites (`scheduler/wiring.py` `_on_fail`, `ops/daemon.py` gate-return) are *documented for the repin*, not touched by this phase | Confirm the phase SUMMARY names both sites for the human-gated repin (ECOSYSTEM.md §3) |

*All in-repo code behaviors have automated verification; the only manual item is the cross-repo repin documentation deliverable.*

---

## Validation Sign-Off

> **Finalized post-execution** by the Nyquist finalizer (`verify:post` → `validate-phase`, auto mode)
> after Gate-1 passed. Zero coverage gaps → `nyquist_compliant: true` (INC-2026-07-27-01: this flag
> is set ONLY here, never at plan time).

- [x] All tasks have `<automated>` verify (9 dedicated tests + the standing full-suite/import-hygiene gate)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covered all MISSING references (`tests/test_ready_gate.py` + `tests/test_discord_surface.py` created)
- [x] No watch-mode flags
- [x] Feedback latency < 1s (full suite ~0.26s)
- [x] `nyquist_compliant` — set `true`: gap analysis found zero gaps (every phase requirement has a passing automated test)

**Approval:** approved 2026-07-28 — Nyquist finalizer (auto), zero gaps

---

## Validation Audit 2026-07-28

| Metric | Count |
|--------|-------|
| Requirements audited | 2 (SURF-01, LIFE-04) + standing GATE-01 |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Coverage | SURF-01 COVERED · LIFE-04 COVERED · GATE-01 COVERED |

Every phase requirement maps to a passing automated test (9 dedicated tests across
`tests/test_ready_gate.py` and `tests/test_discord_surface.py`; full suite 80 passed;
import-hygiene 8 passed). No MISSING or PARTIAL rows → `nyquist_compliant: true`. No auditor spawn
was needed (zero gaps; auto mode).
