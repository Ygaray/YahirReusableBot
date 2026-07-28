---
phase: 3
slug: public-surface-footguns
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-27
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> **Plan-time DRAFT** — per-task rows and the sign-off are finalized post-execution by the Nyquist
> finalizer. Task IDs below are plan-level placeholders (`{plan}-{task}`); the planner assigns final
> IDs. Source: `03-RESEARCH.md` §Validation Architecture (HIGH confidence, verified against the venv).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (pin `>=9.0.3`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths=["tests"]`, `pythonpath=["."]`, `addopts="-ra"` |
| **Quick run command** | `uv run pytest tests/test_<file>.py -v` (per new/modified file) |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~5 seconds (baseline: 35 passed, 0 failed) |

---

## Sampling Rate

- **After every task commit:** Run the specific new/modified test file (`uv run pytest tests/test_<file>.py -v`)
- **After every plan wave:** Run the full suite (`uv run pytest -q`)
- **Before `/gsd-verify-work`:** Full suite green AND `uv run pytest tests/test_import_hygiene.py -q` green (GATE-01)
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

> One row per requirement (9 findings + the standing GATE-01). Plan/wave reflect the research's
> recommended strictly-serial file grouping (scheduler → identity → registry → retry → panelkit),
> so a deliberately-RED test never overlaps a sibling's full-suite gate. Final task IDs are assigned
> by the planner.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-* | 01 | 1 | SCHED-01 (H16) | — | `remove()` idempotent for already-gone id (no raise) | unit | `uv run pytest tests/test_engine.py -x` | ❌ W0 (new) | ⬜ pending |
| 03-02-* | 02 | 2 | LIFE-02 (H14) | — | temp fd closed exactly once on `os.replace` failure; original error re-raises | unit | `uv run pytest tests/test_identity.py -k life_02 -x` | ✅ extend | ⬜ pending |
| 03-02-* | 02 | 2 | LIFE-03 (H15) | — | path-shaped `proc_marker` matches degrade sentinel AND basenamed argv0 | unit | `uv run pytest tests/test_identity.py -k life_03 -x` | ✅ extend | ⬜ pending |
| 03-03-* | 03 | 3 | MATCH-01 (H06) | — | length-changing casefold (`ßtatus`, `ﬁnd`, `ß foo` overshoot) slices raw arg correctly | unit | `uv run pytest tests/test_match.py -x` | ❌ W0 (new) | ⬜ pending |
| 03-03-* | 03 | 3 | MATCH-02 (H13) | T-V5 | empty-name AND uppercase-name spec raise `ValueError` at registration | unit | `uv run pytest tests/test_registry.py -x` | ❌ W0 (new) | ⬜ pending |
| 03-04-* | 04 | 4 | RELY-02 (H09) | T-DoS | `build_retrying(attempts_per_burst=1)` to exhaustion → no `ZeroDivisionError` | unit | `uv run pytest tests/test_retry.py -k rely_02 -x` | ✅ extend | ⬜ pending |
| 03-04-* | 04 | 4 | RELY-03 (H10) | — | mid-pause pinned to `attempt_number == burst_size` by assertion | unit | `uv run pytest tests/test_retry.py -k rely_03 -x` | ✅ extend | ⬜ pending |
| 03-05-* | 05 | 5 | DISC-05 (H11) | T-V4 | `interaction_check` with absent user (`None`/`MISSING`) returns `False`, never raises | unit | `uv run pytest tests/test_panelkit.py -k disc_05 -x` | ❌ W0 (new) | ⬜ pending |
| 03-05-* | 05 | 5 | DISC-06 (H12) | T-V4 | `PanelKit(marker="")` and `marker="   "` raise at construction | unit | `uv run pytest tests/test_panelkit.py -k disc_06 -x` | ❌ W0 (new) | ⬜ pending |
| GATE-01 | all | all | GATE-01 | — | full suite + import-hygiene/litmus/grimp stay green at every commit | integration/gate | `uv run pytest -q && uv run pytest tests/test_import_hygiene.py -q` | ✅ standing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_engine.py` — stubs for SCHED-01 (new file; fake raw scheduler whose `remove_job` raises `KeyError`)
- [ ] `tests/test_match.py` — stubs for MATCH-01 (new file; no existing precedent despite CONTEXT.md canonical_refs)
- [ ] `tests/test_registry.py` — stubs for MATCH-02 (new file)
- [ ] `tests/test_panelkit.py` — stubs for DISC-05/06 (new file; synthetic interaction + bad-marker construction)
- No framework install needed — pytest/ruff/grimp all installed and verified
- No new `tests/conftest.py` fixtures anticipated (D-10: grows only on a real second caller; each new double is used by exactly one file this phase). `cmdline_bytes` (existing) is reusable for LIFE-03.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| — | — | — | — |

*All phase behaviors have automated verification (every finding drives a pure/in-memory hub-assertable observable — no gateway, no `/proc`, no network).*

---

## Validation Sign-Off

> **Plan-time state is a DRAFT.** Frontmatter stays `status: draft` and `nyquist_compliant: false`.
> These are finalized ONLY post-execution by the Nyquist finalizer (the `verify:post` →
> `validate-phase` hook, invoked by execute-phase `finalize_nyquist_validation` after Gate-1). Never
> set `nyquist_compliant: true` — or otherwise "sign off" compliance — at plan time (INC-2026-07-27-01).

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (4 new test files)
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] _(finalizer-only, post-execution)_ `nyquist_compliant` — leave `false` at plan time; the
      finalizer sets `true` iff its gap analysis finds zero gaps

**Approval:** pending — finalizer-owned, not set at plan time
