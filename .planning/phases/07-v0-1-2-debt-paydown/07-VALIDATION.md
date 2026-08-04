---
phase: 7
slug: v0-1-2-debt-paydown
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-03
finalized: 2026-08-04
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=9.0.3 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (D-65 adds `filterwarnings = ["error"]` here) |
| **Quick run command** | `uv run pytest -q` |
| **Full suite command** | `uv run pytest -q` (whole suite ~2s — no separate quick subset exists in this repo) |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run the task's specific `-k`-filtered command from the map below
- **After every plan wave:** Run `uv run pytest -q` (full suite — it is ~2s, no reason to sample less)
- **Before `/gsd-verify-work`:** `uv run pytest -q -o 'filterwarnings=error'` must be green — this is
  the actual enforcement mechanism HYG-03/D-65 exists to prove. Per RESEARCH.md Pitfall 1, it is
  **not** equivalent to eyeballing the default warning summary: under the real filter the defect
  surfaces as `PytestUnraisableExceptionWarning`, not the familiar `RuntimeWarning`.
- **Max feedback latency:** ~2 seconds

---

## Per-Task Verification Map

> Task IDs are assigned by the planner; this map is keyed by requirement until plans exist.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-06-01 | 07-06 | 6 | DOCS-02 | — | N/A | unit (new standing gate) | `uv run pytest tests/test_doc_drift.py -x` | ✅ | ✅ green |
| 07-01-02 | 07-01 | 1 | MATCH-03 | — | Duplicate `spec.name` cannot silently shadow a registered command | unit | `uv run pytest tests/test_registry.py -k duplicate -x` | ✅ | ✅ green |
| 07-04-01 | 07-04 | 4 | SURF-02 (`on_online`) | — | N/A | unit | `uv run pytest tests/test_ready_gate.py -k on_online_annotation -x` | ✅ | ✅ green |
| 07-04-01 | 07-04 | 4 | SURF-02 (`render`) | — | N/A | unit | `uv run pytest tests/test_panelkit.py -k render_annotation -x` (needs `localns` workaround, Pitfall 2) | ✅ | ✅ green |
| 07-04-02 | 07-04 | 4 | SURF-02 (`callback`) | — | N/A | manual-only | Manual read of `scheduler/engine.py` docstring recording the decision | N/A | ✅ green |
| 07-02-02 | 07-02 | 2 | DISC-07 | — | A permissions failure is never mislabeled as a pin-cap failure | unit | `uv run pytest tests/test_gateway.py -k retry_pin_forbidden -x` | ✅ | ✅ green |
| 07-02-02 | 07-02 | 2 | DISC-08 | — | A failed eviction-delete leaves the stray in cleanup instead of dropping it | unit | `uv run pytest tests/test_gateway.py -k eviction_delete_failure -x` | ✅ | ✅ green |
| 07-05-02 | 07-05 | 5 | HYG-02 | — | N/A | unit | `uv run pytest tests/test_ready_gate.py tests/test_reload.py -k label_kwarg -x` | ✅ | ✅ green |
| 07-03-02 | 07-03 | 3 | HYG-03 | — | N/A | unit + suite | `uv run pytest tests/test_gateway.py -k stop_does_not_raise -x`, then `uv run pytest -q -o 'filterwarnings=error'` | ✅ | ✅ green |
| 07-05-03 | 07-05 | 5 | LIFE-05 (behavior) | — | N/A | unit (already green — pinned, D-61a) | `uv run pytest tests/test_identity.py -k bundled_short_option -x` | ✅ | ✅ green |
| 07-05-03 | 07-05 | 5 | LIFE-05 (doc) | — | N/A | manual-only | Manual read of `EXTENSION-GUIDE.md` §4 | N/A | ✅ green |
| 07-07-01 | 07-07 | 7 | DOCS-03 | — | N/A | manual-only | Manual read of corrected enumeration vs. SUMMARY's filesystem-verification record | N/A | ✅ green |
| 07-07-01 | 07-07 | 7 | GATE-02 | — | N/A | suite-level | `uv run pytest -q` (zero warnings) + `uv run pytest tests/test_import_hygiene.py -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_doc_drift.py` — **DELIVERED** (plan 07-06, commit `2793076`). Standing gate walking
  `.planning/**/*.md` via the `_MODULE_ROOT` idiom mirrored from `test_import_hygiene.py`, matching the
  **bare** regex `ops[/.]daemon` (bare, *not* `weatherbot/ops/daemon` — a fully-qualified pattern
  misses the bare form, which is PC-D's own lesson). 5 tests: the real gate, 2 self-proofs, and 2
  phantom-exemption guards.
  **Implementation note — deviation from this draft, deliberate:** the draft specified an exempt-list
  of `(relative_path, line_number)` tuples. The shipped gate uses **whole-subtree path prefixes plus a
  content-located window** instead, because line numbers self-invalidate — plan 07-05's own
  REQUIREMENTS.md edit shifts the DOCS-02 block and the archive banners shift ~12 lines, so a
  line-pinned exempt-list would have gone stale within the same phase. Non-vacuity guards were added
  so an exemption that silently matches nothing fails the suite.
- [x] No framework install needed — `pytest` and `structlog` already pinned and installed. Confirmed.
- [x] No other test-infrastructure gaps — every other requirement extended an existing test file.
---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `EXTENSION-GUIDE.md` §4 states the attached-`-mmodule` constraint as a permanent, reasoned limitation | LIFE-05 (doc half) | A prose-accuracy claim; an automated string check derived from the same source cannot validate that the reasoning is correct | Read `EXTENSION-GUIDE.md` §4 and confirm it names the bundled form, states it is a deliberate non-fix, and records the reasoning |
| `SchedulerEngine.register`'s `callback` stays variadic with the rationale recorded | SURF-02 (`callback` third) | Recorded non-issue — the decision is "no change, write down why"; there is no behavior delta to assert | Read `scheduler/engine.py`'s docstring/comment and confirm the rationale is present |
| Corrected enumeration names all three de-hack sites, including the *producing* site (`weatherbot/ops/selfcheck.py`) | DOCS-03 | An automated check derived from the same source as the claim cannot catch an error in that source (the v0.1.2 audit's own lesson); an over-fitted check would just re-encode the mistake | Read the corrected `REQUIREMENTS.md` / `HUB-HARDENING-REPORT-v0.1.2.md` enumeration against the phase SUMMARY's filesystem-verification record; confirm each named path resolves on disk in WeatherBot |

---

## Validation Sign-Off

> **FINALIZED post-execution** by the Nyquist finalizer (`verify:post` → `validate-phase`,
> invoked by execute-phase `finalize_nyquist_validation`). Plan-time draft state has been superseded.

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references — `tests/test_doc_drift.py` delivered
- [x] No watch-mode flags
- [x] Feedback latency < 5s — full suite runs in ~2s
- [x] _(finalizer-only)_ `nyquist_compliant: true` — gap analysis found **zero** MISSING/PARTIAL rows

**Approval:** approved 2026-08-04 — finalizer-owned.

---

## Validation Audit 2026-08-04

| Metric | Count |
|--------|-------|
| Requirements mapped | 13 rows (9 REQ-IDs + GATE-02, SURF-02/LIFE-05 split by site) |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Automated (COVERED) | 10 |
| Manual-only (documented, signed off) | 3 |

**Method.** Each mapped `-k` selector was re-run through `pytest --collect-only` to confirm the named
test actually exists and collects — not merely that a SUMMARY claimed it. Collection counts:
`test_registry.py -k duplicate` 5 · `test_identity.py -k bundled` 1 · `test_ready_gate.py -k on_online` 2 ·
`test_panelkit.py -k render` 1 · `test_gateway.py -k forbidden` 1 · `test_gateway.py -k evict` 2 ·
`test_ready_gate.py -k label` 2 · `test_reload.py -k label` 1 · `test_gateway.py -k stop` 4 ·
`test_doc_drift.py` 5. Zero selectors resolved to zero tests, so no row is vacuous.

**On the 3 manual-only rows.** These are *planned* manual-only entries with recorded justification
(see § Manual-Only above and `07-RESEARCH.md` § Validation Architecture), not coverage gaps. Each was
signed off with evidence in plan 07-07. They are deliberately not automated because a positive-content
grep derived from the same prose it verifies cannot catch an error in that prose — the v0.1.2 audit's
own headline lesson, and the reason DOCS-02 splits into a string-absence gate plus separate
filesystem evidence (D-67).

**Gate-1 agentic self-UAT** was skipped for this phase with reasoning recorded in `07-VERIFICATION.md`
(headless library, no drivable surface; detector matched the structlog kwarg name `label=`).
