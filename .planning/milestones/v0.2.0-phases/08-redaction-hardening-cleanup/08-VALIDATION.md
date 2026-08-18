---
phase: 8
slug: redaction-hardening-cleanup
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-17
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (`pytest>=9.0.3`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]`, `filterwarnings = ["error"]` |
| **Quick run command** | `uv run pytest -q tests/test_redact_sink.py tests/test_redact_core.py tests/test_extension_guide.py` |
| **Full suite command** | `uv run pytest -q` |
| **Static-analysis gate (new)** | `uv run pyright` (after `uv add --dev pyright` + `[tool.pyright]` config + first-run baseline) |

---

## Sampling Rate

- **After every task commit:** targeted `-k`-filtered command from the map below, plus `uv run pyright` once the gate is wired.
- **After every plan wave:** `uv run pytest -q` (full suite, `filterwarnings = ["error"]` — zero warnings tolerated) + `uv run ruff check` + `uv run pytest tests/test_import_hygiene.py -q`.
- **Before `/gsd-verify-work`:** full suite green AND `uv run pyright` green (post-baseline).
- **Max feedback latency:** full suite runs in low single-digit seconds; no watch-mode needed.

---

## Per-Task Verification Map

> Task IDs are assigned by the planner; this map is keyed by requirement until plans exist.

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|---------------------|-------------|--------|
| REDACT-09 | `RedactionPattern.literal(...)`'s raw source stays inaccessible via accidental paths; `asdict`/`astuple` residual is documented + pinned | unit | `uv run pytest tests/test_redact_core.py -k "leak or asdict or wr02" -x` | ✅ (`tests/test_redact_core.py:236-363`) | ✅ green |
| REDACT-10 | `RedactingWriter.write` fails closed on `re.error`; new `on_error` hook fires observably without raising, mirroring `on_redaction`'s swallow-and-continue guard | unit | `uv run pytest tests/test_redact_sink.py -k "malformed or on_error" -x` | ✅ (`tests/test_redact_sink.py:522-602` — hook delivery, no-leak payload gate, raising-hook survival) | ✅ green |
| DOCS-05 | Telemetry semantics ("changed writes, not substitutions / monotonic") and reconfigure-discipline ("call `assert_redaction_active` again after any reconfiguration") claims are regression-gated, each with a non-vacuity self-proof | unit (doc-content) | `uv run pytest tests/test_extension_guide.py -x` | ✅ (`tests/test_extension_guide.py:441-618` — both gates + non-vacuity self-proofs) | ✅ green |
| HYG-04 | `pyright basic` mode gate lands green (baseline-and-burn-down); SURF-02's `get_type_hints` assertions retire-vs-keep decided explicitly | static-analysis (not pytest) | `uv run python scripts/pyright_baseline.py` | ✅ (`scripts/pyright_baseline.py`, `pyright-baseline.json`, `tests/test_pyright_baseline.py`); KEEP decided on observed evidence, `get_type_hints` assertions kept (`tests/test_ready_gate.py`, `tests/test_panelkit.py`) | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] New `on_error` hook in `yahir_reusable_bot/redact/sink.py` — shipped in plan 08-02, RED-first (REDACT-10).
- [x] `EXTENSION-GUIDE.md` §7 malformed-pattern paragraph — shipped in plan 08-03, RED-first (REDACT-10).
- [x] Two new tests in `tests/test_extension_guide.py` (telemetry-semantics gate, reconfigure-discipline gate), each with its own non-vacuity self-proof — shipped in plan 08-03; both pin already-true prose so GATE-02-satisfying evidence is each self-proof, not a RED commit (DOCS-05).
- [x] `pyright` dev-dependency + `[tool.pyright]` config table (`typeCheckingMode = "basic"` explicit) + hand-rolled baseline-and-burn-down gate — shipped in plan 08-04 behind its own human legitimacy checkpoint (approved); portability bug found and fixed in plan 08-05 (HYG-04).

*(REDACT-09 had no Wave 0 gap — its test coverage already existed and was green; plan 08-01 added the rationale-retention gate and plan 08-05 derived its GATE-02 ancestry from git.)*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| REDACT-09 close-vs-accept decision is recorded in `core.py` docstring + `05-SECURITY.md` (UF-01) | REDACT-09 | A prose-accuracy/rationale claim — an automated check derived from the same source cannot validate the reasoning itself | Read `yahir_reusable_bot/redact/core.py`'s `RedactionPattern` docstring and `05-SECURITY.md`'s UF-01 entry; confirm both state the accept decision and rationale |
| SURF-02 `get_type_hints` retire-vs-belt-and-suspenders decision is recorded | HYG-04 | A recorded design decision, not a behavior delta — there is nothing new to assert beyond "the decision is written down and the code matches it" | Read the plan's decision record and confirm the three SURF-02 signatures' runtime assertions match the stated retire/keep choice |

---

## Validation Audit 2026-08-18

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 (all four requirements shipped automated coverage during execution — no post-hoc gap-filling needed) |
| Escalated | 0 |

All four Per-Task Verification Map rows are ✅ green. Zero MISSING/PARTIAL rows remain.

## Validation Sign-Off

> **FINALIZED post-execution** by the Nyquist finalizer (`verify:post` → `validate-phase`,
> invoked by execute-phase `finalize_nyquist_gate`).

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] _(finalizer-only)_ `nyquist_compliant: true` — gap analysis finds zero MISSING/PARTIAL rows

**Approval:** verified 2026-08-18.
