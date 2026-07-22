---
phase: 1
slug: reachable-reliability
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-22
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `01-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (9.0.3+, already installed and pinned) |
| **Config file** | `pyproject.toml` → `[tool.pytest.ini_options]` (`testpaths=["tests"]`, `pythonpath=["."]`, `addopts="-ra"`) |
| **Quick run command** | `uv run pytest tests/test_retry.py tests/test_identity.py -v` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~2 seconds quick · ~10 seconds full |

No framework install is needed — `pytest`, `httpx`, and `tenacity` are already present in the lock.

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_retry.py tests/test_identity.py -v`
- **After every plan wave:** Run `uv run pytest` (full suite — includes `test_gateway.py` and the
  standing `test_import_hygiene.py` gate)
- **Before `/gsd-verify-work`:** Full suite must be green on the phase branch (D-14)
- **Max feedback latency:** 10 seconds

Sub-second feedback is achievable despite the production `mid_pause_s=2700` default because the
retry tests inject `attempts_per_burst=2, burst_spread_s=0, mid_pause_s=0` plus a fake `stop_event`
whose `.wait(timeout)` returns immediately (D-09). No test sleeps in real time.

**No CI enforces any of this** (D-15) — there is no `.github/workflows` and no pre-commit hook in
this repo. "Green" means the executor ran the commands above locally. That is a deliberate accepted
condition of the phase, not an oversight.

---

## Per-Task Verification Map

Bound to real plan/task IDs after planning (plans committed `8fffd90`). Every row must land on some
task's `<verify>` before the plan passes Dimension 8.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-T1 | 01 | 1 | RELY-01, LIFE-01 | — | N/A (pre-fix baseline capture) | baseline | `uv run pytest` green at branch point | ✅ exists | ⬜ pending |
| 01-01-T2 | 01 | 1 | RELY-01, LIFE-01 | — | N/A (test substrate) | fixture | `uv run pytest tests/ --collect-only -q` | ❌ W0 | ⬜ pending |
| 01-02-T1 | 02 | 2 | RELY-01 | — | N/A (RED commit, test alone) | unit | `uv run pytest tests/test_retry.py` must FAIL | ❌ W0 | ⬜ pending |
| 01-02-T2 | 02 | 2 | RELY-01 | — | Exhausted transient reports `transient_exhausted`, never `internal_error` | unit (behavioral) | `uv run pytest tests/test_retry.py -x` | ❌ W0 | ⬜ pending |
| 01-03-T1 | 03 | 3 | LIFE-01 | T-1-01 | N/A (RED commit, test alone) | unit | `uv run pytest tests/test_identity.py` must FAIL | ❌ W0 | ⬜ pending |
| 01-03-T2 | 03 | 3 | LIFE-01 | T-1-01 | Guard must NOT match a recycled PID → cannot SIGHUP an unrelated process; DOES match a daemon behind one or two interpreter flags | unit | `uv run pytest tests/test_identity.py -x` | ❌ W0 | ⬜ pending |
| 01-04-T1 | 04 | 4 | RELY-01, LIFE-01, GATE-01 | — | All gates green; RED-first ancestry proven | audit | `uv run pytest` + `git merge-base --is-ancestor` | ✅ exists | ⬜ pending |
| 01-04-T3 | 04 | 4 | GATE-01 | — | Hub imports no consumer; no domain nouns | unit (existing) | `uv run pytest tests/test_import_hygiene.py` | ✅ exists | ⬜ pending |

`01-04-T2` is the human merge-authorization checkpoint — no automated command by design.

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures: fake `stop_event` with instant `.wait(timeout)`, and a
  NUL-separated cmdline-bytes builder (D-09 / D-10). Both new test files depend on it. This file is
  a deliberate departure from `TESTING.md:36` and `:142`, which record "no conftest.py, no
  fixtures" — that doc goes stale when this phase lands and must be updated.
- [ ] `tests/test_retry.py` — new file (D-08); covers RELY-01
- [ ] `tests/test_identity.py` — new file (D-08); covers LIFE-01
- [ ] Framework install — **none required**

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| RED-first proof | RELY-01, LIFE-01 | Proving a test fails against *pre-fix* source cannot be asserted by the post-fix suite — the source state under test no longer exists once the fix lands (D-13) | Per D-13: run each new test against the unfixed source (stash the fix / check out the pre-fix blob), capture the failure output, and record it in the commit or plan evidence before applying the fix. Then re-run to show green. |

Everything else in this phase has automated verification.

---

## Under-Sampling Risks (false-green modes to avoid)

Carried forward from `01-RESEARCH.md` — these were verified empirically, not reasoned about:

1. **RELY-01 — type-only assertion.** A test asserting only `pytest.raises(RemoteProtocolError)`
   without also asserting the attempt count reached `2 * attempts_per_burst` passes **identically
   before and after the fix**. Pre-fix, `is_transient` returning `False` also propagates the original
   exception — just after 1 attempt instead of 4. This is the single highest-risk false-green in the
   phase: it would look like proof of D-17 and prove nothing. The attempt-count assertion (D-16) is
   what makes it genuinely RED pre-fix.
2. **RELY-01 — hand-rolled retrying.** Testing against a locally constructed `tenacity.Retrying(...)`
   instead of the hub's real `build_retrying(...)` validates tenacity, not the hub's
   `retry_error_callback` wiring — which is the actual load-bearing fix surface.
3. **LIFE-01 — partial truth table.** Testing fewer than all four D-19-locked rows, especially
   omitting the recycled-PID decoy (`python -m pytest <marker>` → must be `False`), leaves the live
   defect unverified. That row is the *only* one current production code gets wrong; the other three
   pass by coincidence of the slice-window bug.
4. **LIFE-01 — import-only test.** Asserting the fixed function imports/compiles without asserting
   its return value per row is RED for the wrong reason (or not RED at all), defeating D-13.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`conftest.py`, `test_retry.py`, `test_identity.py`)
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] Every under-sampling risk above is refuted by a concrete assertion in the shipped tests
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
