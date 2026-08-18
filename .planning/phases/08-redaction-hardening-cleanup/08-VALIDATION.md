---
phase: 8
slug: redaction-hardening-cleanup
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| REDACT-09 | `RedactionPattern.literal(...)`'s raw source stays inaccessible via accidental paths; `asdict`/`astuple` residual is documented + pinned | unit | `uv run pytest tests/test_redact_core.py -k "leak or asdict" -x` | ✅ (`tests/test_redact_core.py:236-273`) | ✅ green — already shipped; plan task is verify/cross-reference, not new code |
| REDACT-10 | `RedactingWriter.write` fails closed on `re.error`; new `on_error` hook fires observably without raising, mirroring `on_redaction`'s swallow-and-continue guard | unit | `uv run pytest tests/test_redact_sink.py -k "malformed or on_error" -x` | Placeholder test exists (`:435-458`); `on_error` test does NOT exist yet | ⬜ Wave 0 gap |
| DOCS-05 | Telemetry semantics ("changed writes, not substitutions / monotonic") and reconfigure-discipline ("call `assert_redaction_active` again after any reconfiguration") claims are regression-gated, each with a non-vacuity self-proof | unit (doc-content) | `uv run pytest tests/test_extension_guide.py -x` | Both new tests do NOT exist yet; template pattern (`:324-403`) confirmed present | ⬜ Wave 0 gap |
| HYG-04 | `pyright basic` mode gate lands green (baseline-and-burn-down); SURF-02's `get_type_hints` assertions retire-vs-keep decided explicitly | static-analysis (not pytest) | `uv run pyright` | Tool not installed, config not written | ⬜ Wave 0 gap |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] New `on_error` hook in `yahir_reusable_bot/redact/sink.py` — does not exist today; needs a RED-first test in `tests/test_redact_sink.py` before implementation (REDACT-10).
- [ ] `EXTENSION-GUIDE.md` §7 malformed-pattern paragraph — does not exist yet (REDACT-10).
- [ ] Two new tests in `tests/test_extension_guide.py` (telemetry-semantics gate, reconfigure-discipline gate) mirroring the Known-limitations gate pattern at `:324-403`, each with its own non-vacuity self-proof — do not exist yet (DOCS-05).
- [ ] `pyright` dev-dependency (`uv add --dev pyright`) + `[tool.pyright]` config table (`typeCheckingMode = "basic"` explicit, not default) + first-run baseline mechanism (hand-rolled diff script — no `pyright-baseline` package exists on PyPI/npm) — none of this exists in the repo today (HYG-04).

*(REDACT-09 has no Wave 0 gap — its test coverage already exists and is green.)*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| REDACT-09 close-vs-accept decision is recorded in `core.py` docstring + `05-SECURITY.md` (UF-01) | REDACT-09 | A prose-accuracy/rationale claim — an automated check derived from the same source cannot validate the reasoning itself | Read `yahir_reusable_bot/redact/core.py`'s `RedactionPattern` docstring and `05-SECURITY.md`'s UF-01 entry; confirm both state the accept decision and rationale |
| SURF-02 `get_type_hints` retire-vs-belt-and-suspenders decision is recorded | HYG-04 | A recorded design decision, not a behavior delta — there is nothing new to assert beyond "the decision is written down and the code matches it" | Read the plan's decision record and confirm the three SURF-02 signatures' runtime assertions match the stated retire/keep choice |

---

## Validation Sign-Off

> **FINALIZED post-execution** by the Nyquist finalizer (`verify:post` → `validate-phase`,
> invoked by execute-phase `finalize_nyquist_validation`). This is a plan-time DRAFT only.

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] _(finalizer-only)_ `nyquist_compliant: true` — gap analysis finds zero MISSING/PARTIAL rows

**Approval:** pending — finalizer-owned, not set at plan time.
