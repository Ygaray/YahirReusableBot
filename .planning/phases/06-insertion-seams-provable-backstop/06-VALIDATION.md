---
phase: 6
slug: insertion-seams-provable-backstop
status: validated_partial
nyquist_compliant: false
wave_0_complete: true
created: 2026-08-03
audited: 2026-08-03
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `06-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (dev dependency `pytest>=9.0.3`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]` |
| **Quick run command** | `uv run pytest tests/test_redact_sink.py tests/test_redact_processor.py tests/test_redact_verify.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Measured runtime** | ~0.2s (quick, 46 tests) / ~2s (full, 158 tests) |

House conventions carried from Phase 5 and binding here: module-local `SENTINEL` constant
(not a `conftest.py` fixture until a second caller exists — D-10), hand-written capture doubles
(no `unittest.mock` / `pytest-mock` anywhere in this suite), RED-first two-commit discipline per
GATE-02.

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_redact_sink.py tests/test_redact_processor.py tests/test_redact_verify.py -q`
- **After every plan wave:** Run `uv run pytest -q` (full suite)
- **Before `/gsd-verify-work`:** Full suite green **plus** `uv run pytest tests/test_import_hygiene.py -q` (grimp + litmus gates)
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

> Task IDs are assigned when PLAN.md files are written; the requirement → command mapping below is
> the binding contract. The executor fills the Task ID / Plan / Wave columns as tasks land.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-02 | 06-01 | 1 | REDACT-04 | T-06-01 | Event fields **and** full formatted traceback scrubbed, asserted against full captured output (never `str(exc)` alone), renderer- and chain-order-independent | unit + adversarial | `uv run pytest tests/test_redact_sink.py -x` | ✅ (20 tests) | ✅ green |
| 06-01-02 | 06-01 | 1 | REDACT-04 | T-06-01 | `JSONRenderer` line with an escaped secret still round-trips through `json.loads` after redaction | unit | `uv run pytest tests/test_redact_sink.py -k json -x` | ✅ | ✅ green |
| 06-01-02 | 06-01 | 1 | REDACT-04 (D-55) | T-06-01 | `RedactingWriter` installed as `sys.stderr` scrubs non-structlog output (bare `print()` / stdlib `logging`) | integration | `uv run pytest tests/test_redact_sink.py -k stderr_recipe -x` | ✅ | ✅ green |
| 06-03-02 | 06-03 | 3 | REDACT-05 | T-06-01 | `redaction_processor` scrubs `event_dict` string values; docstring states the chain-order precondition | unit | `uv run pytest tests/test_redact_processor.py -x` | ✅ (11 tests) | ✅ green |
| 06-03-02 | 06-03 | 3 | REDACT-05 | T-06-01 | Negative case: processor-only (no sink) still leaks a traceback under `dev.ConsoleRenderer` — documents the known limitation, proves the sink's necessity | unit | `uv run pytest tests/test_redact_processor.py -k still_leaks_a_traceback -x` | ✅ | ✅ green |
| 06-02-02 | 06-02 | 2 | REDACT-07 | T-06-02 | `assert_redaction_active` raises when the backstop is absent and after a second `structlog.configure()` drops it; passes when installed | unit + integration | `uv run pytest tests/test_redact_verify.py -x` | ✅ (15 tests) | ✅ green |
| 06-02-02 | 06-02 | 2 | REDACT-07 (D-60) | T-06-02 | `assert_redaction_active` **warns, never raises**, when the optional processor is mis-ordered relative to the exception formatters | unit | `uv run pytest tests/test_redact_verify.py -k ordering -x` | ✅ (2 tests) | ✅ green |
| 06-01-02 | 06-01 | 1 | REDACT-08 | T-06-05 | Redaction-count telemetry increments on changed writes only; thread-safe under concurrent `.write()` calls (`threading.Lock`, D-59) | unit + concurrency | `uv run pytest tests/test_redact_sink.py -k telemetry -x` | ✅ (2 tests) | ✅ green |
| 06-04-01 | 06-04 | 4 | DOCS-04 | — | `EXTENSION-GUIDE.md` SEAM-08 row present and flipped to **implemented**, naming the architectural inversion | **manual-only** (no automated doc-content test in this repo's convention) | — | — | ⚠️ manual-only — see gap below |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_redact_sink.py` — REDACT-04, REDACT-08 (20 tests, co-located per the sink/telemetry coupling)
- [x] `tests/test_redact_processor.py` — REDACT-05 (11 tests)
- [x] `tests/test_redact_verify.py` — REDACT-07 incl. the D-60 ordering-warning path (15 tests)
- [x] `tests/test_import_hygiene.py` — `redact_scanned` litmus guard extended to all five `redact/` modules, plus the new `test_redact_sink_never_imports_structlog` invariant (10 tests)
- [x] No new framework or fixture install needed — pytest 9.1.1 and the hand-written-double convention carried over from Phase 5 unchanged

*(Exact module/test file split is Claude's Discretion per CONTEXT.md; adjust names to match the layout the plan settles on, keeping the requirement → command mapping intact.)*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `EXTENSION-GUIDE.md` SEAM-08 row reads **implemented** and states the architectural inversion (hub supplies a toolkit the consumer wires into its own `structlog.configure()`; no `Redactor` Protocol exists) | DOCS-04 | This repo has no automated doc-content assertion convention; the claim is editorial, not mechanical | Open `EXTENSION-GUIDE.md`, find the SEAM-08 row, confirm status column reads implemented and the inversion note is present and accurate |

---

## Validation Audit 2026-08-03

Run by the Nyquist finalizer (`verify:post` → `validate-phase --auto`) after Gate-1 passed.
Auto mode reports honest coverage; it does **not** spawn the auditor or generate tests. Gap-FILLING
stays an explicit human-invoked `/gsd-validate-phase 6`.

| Metric | Count |
|--------|-------|
| Map rows | 9 |
| COVERED (automated, re-run green this audit) | 8 |
| MISSING (no automated regression test) | 1 |
| Resolved by this run | 0 (auto mode does not generate tests) |
| Escalated to Manual-Only | 1 |

**Every mapped command was executed during this audit, not inferred.** One correction applied: the
REDACT-05 negative-case row recorded selector `-k leaks_without_sink`, which silently deselected all
11 tests (0 selected, exit 0 — a vacuous green). The test itself exists and passes; only the
recorded selector was stale. Corrected to `-k still_leaks_a_traceback`, matching the real test name
`test_processor_only_configuration_still_leaks_a_traceback_without_the_sink`.

**The one real gap — DOCS-04.** No automated doc-content test covers `EXTENSION-GUIDE.md`'s SEAM-08
row. Gate-1 self-UAT verified it behaviorally (rung 0, PASS), and the phase goal is met, but a
future edit that removed or regressed the SEAM-08 row would not turn any test red. This is why
`nyquist_compliant` stays `false` — it flags follow-up, it does not reopen the phase.

To close it: run `/gsd-validate-phase 6` (human-invoked, non-auto) and let the auditor generate a
doc-content assertion, or accept it permanently as manual-only.

## Validation Sign-Off

> **Plan-time state is a DRAFT.** Frontmatter stays `status: draft` / `nyquist_compliant: false`.
> These are finalized ONLY post-execution by the Nyquist finalizer (`verify:post` →
> `validate-phase`, invoked by execute-phase `finalize_nyquist_validation` after Gate-1). Never set
> `nyquist_compliant: true` — or otherwise sign off compliance — at plan time (INC-2026-07-27-01).

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — 8/9 map rows automated; DOCS-04 is manual-only
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references — all four Wave 0 items landed
- [x] No watch-mode flags
- [x] Feedback latency < 15s — measured ~2s for the full suite
- [ ] _(finalizer-only, post-execution)_ `nyquist_compliant` — **left `false`**: DOCS-04 has no automated regression test (see Validation Audit above). Not zero gaps, so the finalizer does not flip it.

**Approval:** validated (partial) 2026-08-03 — 8 automated, 1 manual-only. Phase 6 is complete; the DOCS-04 row is tracked follow-up, not a blocker.
