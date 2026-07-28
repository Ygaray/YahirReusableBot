---
phase: 1
slug: reachable-reliability
status: complete
nyquist_compliant: true
wave_0_complete: true
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
| 01-01-T1 | 01 | 1 | RELY-01, LIFE-01 | — | N/A (pre-fix baseline capture) | baseline | `uv run pytest` green at branch point | ✅ exists | ✅ green |
| 01-01-T2 | 01 | 1 | RELY-01, LIFE-01 | — | N/A (test substrate) | fixture | `uv run pytest tests/ --collect-only -q` | ✅ exists (`e00ccf3`) | ✅ green |
| 01-02-T1 | 02 | 2 | RELY-01 | — | N/A (RED commit, test alone) | unit | `uv run pytest tests/test_retry.py` must FAIL | ✅ exists (`e7c959d`) | ✅ green (RED confirmed pre-fix: 4 failed/3 passed, verbatim in 01-02-SUMMARY.md) |
| 01-02-T2 | 02 | 2 | RELY-01 | — | Exhausted transient reports `transient_exhausted`, never `internal_error` (D-17 hub-scoped restatement) | unit (behavioral) | `uv run pytest tests/test_retry.py -x` | ✅ exists (`f6e4fb2`) | ✅ green (7/7 passed) |
| 01-03-T1 | 03 | 3 | LIFE-01 | T-1-01 | N/A (RED commit, test alone) | unit | `uv run pytest tests/test_identity.py` must FAIL | ✅ exists (`0f0a9ad`) | ✅ green (RED confirmed pre-fix: 2 failed/5 passed, verbatim in 01-03-SUMMARY.md) |
| 01-03-T2 | 03 | 3 | LIFE-01 | T-1-01 | Guard must NOT match a recycled PID → cannot SIGHUP an unrelated process; DOES match a daemon behind one or two interpreter flags | unit | `uv run pytest tests/test_identity.py -x` | ✅ exists (`5273c13`) | ✅ green (7/7 passed) |
| 01-04-T1 | 04 | 4 | RELY-01, LIFE-01, GATE-01 | — | All gates green; RED-first ancestry proven | audit | `uv run pytest` + `git merge-base --is-ancestor` | ✅ exists | ✅ green (23 passed; both RED-first ordering audits print PROVEN) |
| 01-04-T3 | 04 | 4 | GATE-01 | — | Hub imports no consumer; no domain nouns | unit (existing) | `uv run pytest tests/test_import_hygiene.py` | ✅ exists | ✅ green (8 passed) |

`01-04-T2` is the human merge-authorization checkpoint — no automated command by design.

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Signed off 2026-07-22:** every row above is bound to its real plan/task ID and mechanically
verified this session — see the Validation Sign-Off section below for the exact commands run and
their output.

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
   **Refuted by:** `tests/test_retry.py::test_exhausted_transient_escapes_as_itself_after_full_budget`'s
   `assert attempts[0] == 4` line — confirmed genuinely RED pre-fix in 01-02-SUMMARY.md's verbatim
   output (`assert 1 == 4`, not merely a passing `pytest.raises`).
2. **RELY-01 — hand-rolled retrying.** Testing against a locally constructed `tenacity.Retrying(...)`
   instead of the hub's real `build_retrying(...)` validates tenacity, not the hub's
   `retry_error_callback` wiring — which is the actual load-bearing fix surface.
   **Refuted by:** the same `test_exhausted_transient_escapes_as_itself_after_full_budget` calling
   `build_retrying(fake_stop_event, attempts_per_burst=2, burst_spread_s=0, mid_pause_s=0)` directly
   (`tests/test_retry.py:114-116`) — the hub's real constructor, not a locally shaped `Retrying`; the
   escape assertion (`type(exc_info.value) is httpx.RemoteProtocolError`, never `RetryError`) proves
   the `retry_error_callback` wiring at `retry.py:247` specifically, which a hand-rolled `Retrying`
   would bypass entirely.
3. **LIFE-01 — partial truth table.** Testing fewer than all four D-19-locked rows, especially
   omitting the recycled-PID decoy (`python -m pytest <marker>` → must be `False`), leaves the live
   defect unverified. That row is the *only* one current production code gets wrong; the other three
   pass by coincidence of the slice-window bug.
   **Refuted by:** `tests/test_identity.py::test_decoy_positional_marker_arg_does_not_match` (the
   recycled-PID decoy itself, confirmed RED pre-fix — `assert True is False` in 01-03-SUMMARY.md's
   verbatim output) plus its six sibling rows covering the remaining three D-19-locked truth-table
   entries and two additive rows (`test_interpreter_flag_before_module_switch_matches`,
   `test_plain_module_switch_form_matches`, `test_argv0_basename_form_matches`,
   `test_two_interpreter_flags_before_module_switch_matches`,
   `test_nested_selector_switch_does_not_match`).
4. **LIFE-01 — import-only test.** Asserting the fixed function imports/compiles without asserting
   its return value per row is RED for the wrong reason (or not RED at all), defeating D-13.
   **Refuted by:** every row in `tests/test_identity.py` asserting a concrete boolean return value
   from `is_running_process(...)` (`is True` / `is False`), never a bare import or collection check —
   see e.g. `test_decoy_positional_marker_arg_does_not_match`'s
   `assert is_running_process(...) is False` and the six other rows' matching `is True`/`is False`
   assertions.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (`conftest.py`, `test_retry.py`, `test_identity.py`) —
  all three now exist and are committed (`e00ccf3`, `e7c959d`/`f6e4fb2`, `0f0a9ad`/`5273c13`)
- [x] No watch-mode flags
- [x] Feedback latency < 10s — full suite runs in 0.23s (`uv run pytest`, 23 passed)
- [x] Every under-sampling risk above is refuted by a concrete assertion in the shipped tests
- [x] `nyquist_compliant: true` set in frontmatter

### Phase-level gate results (this session, on `phase-01-reachable-reliability`)

- `uv run pytest` → **23 passed** in 0.23s: `test_gateway.py` 1 (pre-existing) +
  `test_identity.py` 7 + `test_import_hygiene.py` 8 (pre-existing, GATE-01) + `test_retry.py` 7
- `uv run pytest tests/test_import_hygiene.py` → **8 passed** (GATE-01 standing gate green)
- `uv run pytest tests/test_retry.py tests/test_identity.py -v` → **14 passed**
- `uv run ruff check` → 4 pre-existing errors, all outside this phase's `files_modified`
  (`scripts/new_consumer.py:197`, `yahir_reusable_bot/config/reload.py:46`,
  `yahir_reusable_bot/discord/selection.py:30`, `yahir_reusable_bot/lifecycle/identity.py:121`),
  logged in `deferred-items.md` by Plans 02/03; scoped to this phase's touched files, `ruff check`
  is clean.
- RED-first ordering audit, RELY-01: `git merge-base --is-ancestor e7c959d f6e4fb2` succeeds,
  `e7c959d` touches exactly `tests/test_retry.py` → **RELY-01 RED-first ordering PROVEN**
- RED-first ordering audit, LIFE-01: `git merge-base --is-ancestor 0f0a9ad 5273c13` succeeds,
  `0f0a9ad` touches exactly `tests/test_identity.py` → **LIFE-01 RED-first ordering PROVEN**
- Dependency immutability: `git diff $(git merge-base main HEAD) HEAD -- pyproject.toml uv.lock`
  is empty — zero dependency change across the phase.
- `git status --porcelain` confirms `.planning/config.json`, `ECOSYSTEM.md`, `uv.lock` remain
  modified-but-uncommitted, exactly as they were before this plan started — none were swept into
  a phase commit.

### ROADMAP Phase 1 success criteria checked against evidence

1. **`is_transient` classifies `RemoteProtocolError`/`WriteError` transient; drives the two-burst
   retry; exhaustion reports `transient_exhausted` not `internal_error`.** — Classification: proven
   by `test_classification_includes_remote_protocol_error` and
   `test_classification_includes_network_errors`. The literal `transient_exhausted` clause is
   satisfied via the **D-17 hub-scoped restatement**, not literally: `REASON_TRANSIENT_EXHAUSTED` is
   *defined* at `retry.py:75` but assigned only by consumer-side `fire_slot` code that does not exist
   in this repo. The hub-assertable equivalent —an exhausted `RemoteProtocolError` escapes
   `Retrying.__call__` as itself, never wrapped in `tenacity.RetryError` — is proven by
   `test_exhausted_transient_escapes_as_itself_after_full_budget`.
2. **`LocalProtocolError` stays non-transient (not a blanket `TransportError`).** — Proven by
   `test_classification_excludes_local_protocol_error` and
   `test_classification_excludes_proxy_error_and_unsupported_protocol` (deny-by-default, D-02).
3. **Identity guard does not match the recycled-PID positional decoy; does match
   `python -O -m <marker> run`.** — Proven by `test_decoy_positional_marker_arg_does_not_match`
   (False) and `test_interpreter_flag_before_module_switch_matches` (True).
4. **New regression tests for both fail against pre-fix source.** — Proven mechanically by the
   RED-first ordering audits above plus the verbatim RED output recorded in 01-02-SUMMARY.md
   (4 failed/3 passed) and 01-03-SUMMARY.md (2 failed/5 passed).

**Approval:** signed off 2026-07-22
