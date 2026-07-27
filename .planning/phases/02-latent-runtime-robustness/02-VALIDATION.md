---
phase: 2
slug: latent-runtime-robustness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-27
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
| CFG-01 (H03) | reload reconcile-reject alert | `on_rejected` fires **exactly once** before re-raise on PHASE-2 failure AND holder rolled back to `old_cfg` (both levels) | unit | `uv run pytest tests/test_reload.py -k reject -x` | ❌ W0 (`test_reload.py` new) | ⬜ pending |
| DISC-01 (H04) | gateway death-reason | fake `LoginFailure` start → `is_alive()` False + reason `login_failure`; generic crash → reason `crashed` | unit | `uv run pytest tests/test_gateway.py -k death -x` | ✅ | ⬜ pending |
| DISC-02 (H05) | panel re-summon atomicity | (a) NotFound mid-delete → both remaining deletes run, net 1 live pinned panel; (b) at pin-cap → fresh panel ends up pinned | unit | `uv run pytest tests/test_gateway.py -k summon -x` | ✅ | ⬜ pending |
| DISC-03 (H07) | `stop()` TOCTOU | fake loop: `is_running()` True but `run_coroutine_threadsafe` raises `RuntimeError` → `stop()` returns without raising AND still joins | unit | `uv run pytest tests/test_gateway.py -k stop -x` | ✅ | ⬜ pending |
| DISC-04 (H08) | selection snapshot contract | `snapshot()`-captured value unaffected by interleaved `set()`; `.value` re-read reflects the write | unit | `uv run pytest tests/test_selection.py -x` | ❌ W0 (`test_selection.py` new) | ⬜ pending |

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

## Validation Sign-Off

> **Plan-time state is a DRAFT.** Frontmatter stays `status: draft` / `nyquist_compliant: false`.
> These are finalized ONLY post-execution by the Nyquist finalizer (`verify:post` → `validate-phase`,
> invoked by execute-phase `finalize_nyquist_validation` after Gate-1). Never set
> `nyquist_compliant: true` at plan time (INC-2026-07-27-01).

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`test_reload.py`, `test_selection.py`)
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] _(finalizer-only, post-execution)_ `nyquist_compliant` — leave `false` at plan time

**Approval:** pending — finalizer-owned, not set at plan time
