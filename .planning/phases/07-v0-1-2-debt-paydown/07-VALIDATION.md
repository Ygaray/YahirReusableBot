---
phase: 7
slug: v0-1-2-debt-paydown
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-03
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
| TBD | TBD | 0 | DOCS-02 | — | N/A | unit (new standing gate) | `uv run pytest tests/test_doc_drift.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 1 | MATCH-03 | — | Duplicate `spec.name` cannot silently shadow a registered command | unit | `uv run pytest tests/test_registry.py -k duplicate -x` | ✅ | ⬜ pending |
| TBD | TBD | 1 | SURF-02 (`on_online`) | — | N/A | unit | `uv run pytest tests/test_ready_gate.py -k on_online_annotation -x` | ✅ | ⬜ pending |
| TBD | TBD | 1 | SURF-02 (`render`) | — | N/A | unit | `uv run pytest tests/test_panelkit.py -k render_annotation -x` (needs `localns` workaround, Pitfall 2) | ✅ | ⬜ pending |
| TBD | TBD | 1 | SURF-02 (`callback`) | — | N/A | manual-only | Manual read of `scheduler/engine.py` docstring recording the decision | N/A | ⬜ pending |
| TBD | TBD | 1 | DISC-07 | — | A permissions failure is never mislabeled as a pin-cap failure | unit | `uv run pytest tests/test_gateway.py -k retry_pin_forbidden -x` | ✅ | ⬜ pending |
| TBD | TBD | 1 | DISC-08 | — | A failed eviction-delete leaves the stray in cleanup instead of dropping it | unit | `uv run pytest tests/test_gateway.py -k eviction_delete_failure -x` | ✅ | ⬜ pending |
| TBD | TBD | 1 | HYG-02 | — | N/A | unit | `uv run pytest tests/test_ready_gate.py tests/test_reload.py -k label_kwarg -x` | ✅ | ⬜ pending |
| TBD | TBD | 1 | HYG-03 | — | N/A | unit + suite | `uv run pytest tests/test_gateway.py -k stop_does_not_raise -x`, then `uv run pytest -q -o 'filterwarnings=error'` | ✅ | ⬜ pending |
| TBD | TBD | 1 | LIFE-05 (behavior) | — | N/A | unit (already green — pinned, D-61a) | `uv run pytest tests/test_identity.py -k bundled_short_option -x` | ✅ | ⬜ pending |
| TBD | TBD | 2 | LIFE-05 (doc) | — | N/A | manual-only | Manual read of `EXTENSION-GUIDE.md` §4 | N/A | ⬜ pending |
| TBD | TBD | 2 | DOCS-03 | — | N/A | manual-only | Manual read of corrected enumeration vs. SUMMARY's filesystem-verification record | N/A | ⬜ pending |
| TBD | TBD | 2 | GATE-02 | — | N/A | suite-level | `uv run pytest -q` (zero warnings) + `uv run pytest tests/test_import_hygiene.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_doc_drift.py` — new file, DOCS-02's standing gate. Walk `.planning/**/*.md` (via
  `Path(__file__).resolve().parent.parent / ".planning"`, mirroring `test_import_hygiene.py`'s
  `_MODULE_ROOT` convention at line 64), search each file for the **bare** regex `ops[/.]daemon`
  (bare, *not* `weatherbot/ops/daemon` — a fully-qualified pattern misses the bare form, which is
  PC-D's own lesson), and assert every match falls inside an explicit commented exempt-list of
  `(relative_path, line_number)` tuples covering the 3 intentional mentions (`REQUIREMENTS.md:217`,
  `v0.1.2-MILESTONE-AUDIT.md:21`, `v0.1.2-MILESTONE-AUDIT.md:142`) plus the 7 annotated-archive
  files. Include a self-proof half (synthetic string injected into a temp file, proving the scan
  logic itself catches an unexempted match) per this repo's established
  `test_import_hygiene.py` "every gate has a self-proof" convention.
- [ ] No framework install needed — `pytest` and `structlog` are already pinned and installed.
- [ ] No other test-infrastructure gaps — every other requirement extends an existing test file
  using an already-established convention (plain-construction doubles, no mocking library,
  `_spec`/`_Fake*` factory helpers). `structlog.testing.capture_logs()` works out of the box and
  returns `[{"label": ..., "event": ..., "log_level": ...}]` — the exact shape HYG-02/DISC-07's new
  log-content tests need.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `EXTENSION-GUIDE.md` §4 states the attached-`-mmodule` constraint as a permanent, reasoned limitation | LIFE-05 (doc half) | A prose-accuracy claim; an automated string check derived from the same source cannot validate that the reasoning is correct | Read `EXTENSION-GUIDE.md` §4 and confirm it names the bundled form, states it is a deliberate non-fix, and records the reasoning |
| `SchedulerEngine.register`'s `callback` stays variadic with the rationale recorded | SURF-02 (`callback` third) | Recorded non-issue — the decision is "no change, write down why"; there is no behavior delta to assert | Read `scheduler/engine.py`'s docstring/comment and confirm the rationale is present |
| Corrected enumeration names all three de-hack sites, including the *producing* site (`weatherbot/ops/selfcheck.py`) | DOCS-03 | An automated check derived from the same source as the claim cannot catch an error in that source (the v0.1.2 audit's own lesson); an over-fitted check would just re-encode the mistake | Read the corrected `REQUIREMENTS.md` / `HUB-HARDENING-REPORT-v0.1.2.md` enumeration against the phase SUMMARY's filesystem-verification record; confirm each named path resolves on disk in WeatherBot |

---

## Validation Sign-Off

> **Plan-time state is a DRAFT.** Frontmatter stays `status: draft` and `nyquist_compliant: false`.
> These are finalized ONLY post-execution by the Nyquist finalizer (the `verify:post` →
> `validate-phase` hook, invoked by execute-phase `finalize_nyquist_validation` after Gate-1).

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] _(finalizer-only, post-execution)_ `nyquist_compliant` — leave `false` at plan time; the
      finalizer sets `true` iff its gap analysis finds zero gaps

**Approval:** pending — finalizer-owned, not set at plan time
