---
phase: 2
slug: latent-runtime-robustness
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-27
finalized: 2026-07-27
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `02-RESEARCH.md` § Validation Architecture. Plan-time DRAFT —
> the per-task IDs are finalized when the planner assigns them; compliance is
> signed off ONLY post-execution by the Nyquist finalizer.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥9.0.3 (no `pytest-asyncio` — house style is inline `asyncio.run()`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths=["tests"]`, `pythonpath=["."]`) |
| **Quick run command** | `uv run pytest -q tests/test_gateway.py tests/test_reload.py tests/test_selection.py` |
| **Full suite command** | `uv run pytest -q` (GATE-01: includes `test_import_hygiene.py` litmus/grimp) |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run the file-scoped quick command for the finding just touched
  (e.g. `uv run pytest tests/test_gateway.py -k death -x` after DISC-01's RED test, then again
  after its fix — proving the RED→GREEN transition per D-13's two-commit idiom).
- **After every plan wave:** Run `uv run pytest -q` (full suite) — must include
  `test_import_hygiene.py` green (GATE-01 spans the whole milestone).
- **Before `/gsd-verify-work`:** Full suite green, with each of the five findings carrying a
  test-only commit as the direct parent of its fix commit.
- **Max feedback latency:** ~5 seconds.

---

## Per-Requirement Verification Map

> Task-granular IDs (`2-NN-MM`) are assigned by the planner; this draft maps at the
> requirement level. Threat refs are populated from each PLAN.md `<threat_model>` block.

| Requirement | Finding | Behavior sampled | Test Type | Automated Command | File Exists | Status |
|-------------|---------|------------------|-----------|-------------------|-------------|--------|
| CFG-01 (H03) | reload reconcile-reject alert | `on_rejected` fires **exactly once** before re-raise on PHASE-2 failure AND holder rolled back to `old_cfg` (both levels) | unit | `uv run pytest tests/test_reload.py -k reject -x` | ✅ (`test_reload.py` created W0) | ✅ green |
| DISC-01 (H04) | gateway death-reason | fake `LoginFailure` start → `is_alive()` False + reason `login_failure`; generic crash → reason `crashed` | unit | `uv run pytest tests/test_gateway.py -k death -x` | ✅ | ✅ green |
| DISC-02 (H05) | panel re-summon atomicity | (a) NotFound mid-delete → both remaining deletes run, net 1 live pinned panel; (b) at pin-cap ≥2 owned → fresh panel ends up pinned; (b′) at pin-cap with a **single** owned panel → fresh panel still pinned (WR-01 boundary) | unit | `uv run pytest tests/test_gateway.py -k summon -x` | ✅ | ✅ green |
| DISC-03 (H07) | `stop()` TOCTOU | fake loop: `is_running()` True but `run_coroutine_threadsafe` raises `RuntimeError` → `stop()` returns without raising AND still joins | unit | `uv run pytest tests/test_gateway.py -k stop -x` | ✅ | ✅ green |
| DISC-04 (H08) | selection snapshot contract | `snapshot()`-captured value unaffected by interleaved `set()`; `.value` re-read reflects the write | unit | `uv run pytest tests/test_selection.py -x` | ✅ (`test_selection.py` created W0) | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_reload.py` — new file; first-ever unit coverage for `config/reload.py` in this repo.
- [ ] `tests/test_selection.py` — new file; first-ever unit coverage for `discord/selection.py`.
- [ ] `tests/conftest.py` growth — **not required** unless a synthetic double (client/channel/loop)
      is genuinely shared across ≥2 test files (D-10 rule). DISC-01/02/03 all live in
      `tests/test_gateway.py`, so their doubles likely stay local.
- [ ] Framework install — none; `pytest` already installed and pinned.

---

## Under-Sampling Risks (per finding — what a fix could false-green against)

- **CFG-01:** Asserting only "hook was called" — without **exactly once** AND the rollback state
  (`holder.current() == old_cfg`) — false-greens a fix that double-fires or skips rollback. Keep
  both assertions in the same test (D-16 both-levels).
- **DISC-01:** Asserting only `is_alive() is False` without the death-reason value false-greens an
  accessor that is never wired. Sample **both** the `LoginFailure` and generic-crash branches — a
  one-branch fix false-greens a one-branch test.
- **DISC-02:** The two success-criteria halves are proven by *different* code paths (per-item catch
  vs. headroom-reserve-before-send); sampling only mode (a) false-greens mode (b). Independent
  fixtures required.
- **DISC-03:** Asserting `stop()` doesn't raise without asserting `join()` still ran false-greens a
  fix that swallows and early-`return`s. The criterion is "cannot raise AND still joins."
- **DISC-04:** Asserting only `snapshot()` stability false-greens an over-fix that also freezes
  `.value` after first read. Keep the `.value`-still-reflects-the-write assertion in the same test.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| — | — | — | All phase behaviors have automated (hub-assertable) verification. |

*DISC-04's consumer-side `wiring.py` symptom is explicitly out of hub scope and not verified here.*

---

## Validation Audit 2026-07-27

Post-execution finalizer (auto mode) — coverage audited against the executed phase.

| Metric | Count |
|--------|-------|
| Requirements | 5 |
| COVERED (green automated) | 5 |
| PARTIAL | 0 |
| MISSING | 0 |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

Every requirement (CFG-01, DISC-01, DISC-02, DISC-03, DISC-04) has a green, hub-assertable
automated test. Full suite `uv run pytest -q` → 35 passed (incl. GATE-01 import-hygiene).
Wave 0 test files (`tests/test_reload.py`, `tests/test_selection.py`) were created and are green.
The code-review boundary fix WR-01 added a dedicated single-owned-panel regression under DISC-02.
→ **Nyquist-compliant: zero coverage gaps.**

## Validation Sign-Off

> Finalized post-execution by the Nyquist finalizer (`verify:post` → `validate-phase`, auto mode)
> after Gate-1 passed. `nyquist_compliant: true` is set here because the coverage audit found zero gaps.

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (`test_reload.py`, `test_selection.py` — both created, green)
- [x] No watch-mode flags
- [x] Feedback latency < 10s (~0.5s full suite)
- [x] `nyquist_compliant` set `true` by the finalizer — zero gaps found

**Approval:** approved 2026-07-27 — finalizer (auto mode), zero coverage gaps
