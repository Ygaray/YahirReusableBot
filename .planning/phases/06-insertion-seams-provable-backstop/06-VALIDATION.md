---
phase: 6
slug: insertion-seams-provable-backstop
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-03
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
| **Estimated runtime** | ~5 seconds (quick) / ~15 seconds (full) |

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
| TBD | TBD | TBD | REDACT-04 | T-06-01 | Event fields **and** full formatted traceback scrubbed, asserted against full captured output (never `str(exc)` alone), renderer- and chain-order-independent | unit + adversarial | `uv run pytest tests/test_redact_sink.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | REDACT-04 | T-06-01 | `JSONRenderer` line with an escaped secret still round-trips through `json.loads` after redaction | unit | `uv run pytest tests/test_redact_sink.py -k json -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | REDACT-04 (D-55) | T-06-01 | `RedactingWriter` installed as `sys.stderr` scrubs non-structlog output (bare `print()` / stdlib `logging`) | integration | `uv run pytest tests/test_redact_sink.py -k stderr_recipe -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | REDACT-05 | T-06-01 | `redaction_processor` scrubs `event_dict` string values; docstring states the chain-order precondition | unit | `uv run pytest tests/test_redact_processor.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | REDACT-05 | T-06-01 | Negative case: processor-only (no sink) still leaks a traceback under `dev.ConsoleRenderer` — documents the known limitation, proves the sink's necessity | unit | `uv run pytest tests/test_redact_processor.py -k leaks_without_sink -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | REDACT-07 | T-06-02 | `assert_redaction_active` raises when the backstop is absent and after a second `structlog.configure()` drops it; passes when installed | unit + integration | `uv run pytest tests/test_redact_verify.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | REDACT-07 (D-60) | T-06-02 | `assert_redaction_active` **warns, never raises**, when the optional processor is mis-ordered relative to the exception formatters | unit | `uv run pytest tests/test_redact_verify.py -k ordering -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | REDACT-08 | T-06-05 | Redaction-count telemetry increments on changed writes only; thread-safe under concurrent `.write()` calls (`threading.Lock`, D-59) | unit + concurrency | `uv run pytest tests/test_redact_sink.py -k telemetry -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | DOCS-04 | — | `EXTENSION-GUIDE.md` SEAM-08 row present and flipped to **implemented**, naming the architectural inversion | manual review (no automated doc-content test in this repo's convention) | — | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_redact_sink.py` — stubs for REDACT-04, REDACT-08 (co-located per the sink/telemetry coupling)
- [ ] `tests/test_redact_processor.py` — stubs for REDACT-05
- [ ] `tests/test_redact_verify.py` — stubs for REDACT-07 (including the D-60 ordering-warning path)
- [ ] `tests/test_import_hygiene.py` — extend `test_litmus_clean`'s `redact_scanned` assertion set to include `sink.py` and `processor.py` (currently asserts only `{"core.py", "registry.py"}` — see `tests/test_import_hygiene.py:290-296`)
- [ ] No new framework or fixture install needed — pytest 9.1.1 and the hand-written-double convention are already established by Phase 5

*(Exact module/test file split is Claude's Discretion per CONTEXT.md; adjust names to match the layout the plan settles on, keeping the requirement → command mapping intact.)*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `EXTENSION-GUIDE.md` SEAM-08 row reads **implemented** and states the architectural inversion (hub supplies a toolkit the consumer wires into its own `structlog.configure()`; no `Redactor` Protocol exists) | DOCS-04 | This repo has no automated doc-content assertion convention; the claim is editorial, not mechanical | Open `EXTENSION-GUIDE.md`, find the SEAM-08 row, confirm status column reads implemented and the inversion note is present and accurate |

---

## Validation Sign-Off

> **Plan-time state is a DRAFT.** Frontmatter stays `status: draft` / `nyquist_compliant: false`.
> These are finalized ONLY post-execution by the Nyquist finalizer (`verify:post` →
> `validate-phase`, invoked by execute-phase `finalize_nyquist_validation` after Gate-1). Never set
> `nyquist_compliant: true` — or otherwise sign off compliance — at plan time (INC-2026-07-27-01).

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] _(finalizer-only, post-execution)_ `nyquist_compliant` — leave `false` at plan time; the finalizer sets `true` iff its gap analysis finds zero gaps

**Approval:** pending — finalizer-owned, not set at plan time
