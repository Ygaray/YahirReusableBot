---
phase: 08-redaction-hardening-cleanup
plan: 04
subsystem: testing
tags: [pyright, static-typing, dev-tooling, baseline-diff, hyg-04]

# Dependency graph
requires:
  - phase: 08-03
    provides: REDACT-10 doc half + DOCS-05 doc-gate tests, full suite green baseline for this plan's diffs
provides:
  - "pyright 1.1.411 adopted as a dev-only static type-check gate in basic mode over yahir_reusable_bot/"
  - "scripts/pyright_baseline.py — hand-rolled baseline-and-burn-down diff gate, unit-tested standalone"
  - "pyright-baseline.json — committed first-run baseline (12 diagnostics, 34 files analyzed)"
  - "CLAUDE.md Toolchain section documents the new gate command"
affects: [08-05, future-phases-touching-yahir_reusable_bot]

actuals:
  tokens: 6430
  tasks: 2
  commits: 2

tech-stack:
  added: ["pyright>=1.1.411 (dev-only)"]
  patterns:
    - "Baseline-and-burn-down gate keyed on (repo-relative file, rule, message) — immune to line drift, standalone script beside ruff, never wired into pytest"

key-files:
  created:
    - tests/test_pyright_baseline.py
    - scripts/pyright_baseline.py
    - pyright-baseline.json
  modified:
    - pyproject.toml
    - CLAUDE.md
    - uv.lock

key-decisions:
  - "typeCheckingMode set EXPLICITLY to basic in [tool.pyright] — pyright's own default is standard, which is stricter than D-03 locked"
  - "include scoped to yahir_reusable_bot/ only (source-only) — tests/ and scripts/ excluded to avoid flooding the first-run baseline with dynamic-eval/monkeypatch/stdlib-scaffolder noise; widening is a documented follow-up"
  - "Gate is a standalone script (scripts/pyright_baseline.py), not a pytest test — keeps the suite free of a Node runtime dependency and preserves sub-5-second feedback latency"

patterns-established:
  - "Hand-rolled baseline-diff gate for a tool with no native baseline mechanism: run --outputjson, key on a position-independent tuple, diff against a committed JSON baseline, fail only on genuinely new keys"

requirements-completed: [HYG-04]

coverage:
  - id: D1
    description: "pyright adopted as a dev-only dependency with typeCheckingMode explicitly basic, never inherited from pyright's own (stricter) default"
    requirement: HYG-04
    verification:
      - kind: unit
        ref: "grep typeCheckingMode pyproject.toml — present, value basic"
        status: pass
      - kind: other
        ref: "grep pyright pyproject.toml — present in [dependency-groups].dev AND [tool.pyright], absent from [project].dependencies"
        status: pass
    human_judgment: false
  - id: D2
    description: "Baseline-diff gate's key-building and diffing logic is unit-tested with synthetic diagnostics, covering new-key detection, line-drift tolerance, message-collision detection, missing-rule non-collapse, path relativization, burn-down tolerance, and both halves of the zero-files vacuity distinction"
    requirement: HYG-04
    verification:
      - kind: unit
        ref: "tests/test_pyright_baseline.py — 8 tests, all pass"
        status: pass
    human_judgment: false
  - id: D3
    description: "The gate runs green against the committed first-run baseline (12 diagnostics, 34 files analyzed), with the vacuity guard and new-diagnostic detection both OBSERVED working (not merely assumed) via a temporary mis-scoped include and a temporary scratch type error, each reverted after observation"
    requirement: HYG-04
    verification:
      - kind: other
        ref: "uv run python scripts/pyright_baseline.py — exits 0, 'Gate PASSED'"
        status: pass
    human_judgment: true
    rationale: "The two required observed-behavior proofs (vacuity guard firing, new-diagnostic detection firing) were performed manually during execution and their literal output is recorded below in this SUMMARY; no automated regression test re-runs pyright itself against a broken repo state, so a human should confirm the recorded transcripts satisfy the plan's evidence requirement."
  - id: D4
    description: "Package legitimacy checkpoint for pyright (SUS verdict from unknown-downloads) was reviewed and approved by a human operator before uv add --dev pyright ran"
    requirement: HYG-04
    verification: []
    human_judgment: true
    rationale: "Package-legitimacy approval is an operator decision recorded in 08-CONTEXT.md's Runtime Decisions section (2026-08-18); this plan's Task 1 checkpoint was pre-approved per that record and executed directly, not re-verified by automation."

duration: ~20min
completed: 2026-08-18
status: complete
---

# Phase 8 Plan 04: Adopt pyright basic with a hand-rolled baseline gate Summary

**Adopted pyright 1.1.411 in `basic` mode as a dev-only standing type-check gate over `yahir_reusable_bot/`, with a hand-rolled `(file, rule, message)` baseline-diff script (no off-the-shelf baseline tool exists for pyright) that is itself unit-tested and was observed both passing and failing before commit.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-08-18 (session start)
- **Completed:** 2026-08-18T07:09:20-06:00
- **Tasks:** 2 (Task 1's package-legitimacy checkpoint was pre-approved per `08-CONTEXT.md` Runtime Decisions and executed inline, not a separate commit)
- **Files modified:** 6 (2 created test/script files, 1 created baseline JSON, 3 modified: `pyproject.toml`, `CLAUDE.md`, `uv.lock`)

## Accomplishments

- `pyright` landed as a dev-only dependency (`[dependency-groups].dev`, never `[project].dependencies`), with an explicit `[tool.pyright]` config table pinning `typeCheckingMode = "basic"` — never left to pyright's own stricter `standard` default.
- `scripts/pyright_baseline.py` implements the baseline-and-burn-down mechanism pyright ships no native equivalent for: `_diagnostic_key` (repo-relative, rule, message — immune to line drift), `_new_diagnostics` (sorted diff against the committed baseline), `_assert_run_was_not_vacuous` (rejects a zero-files-analyzed run as a mis-scoped `include`, distinct from a legitimate empty-diagnostics clean run), and a `main()` with gate and `--write-baseline` modes.
- `tests/test_pyright_baseline.py` — eight synthetic, RED-first unit tests drive the diff logic with hand-built dicts shaped like `pyright --outputjson` entries; pyright itself is never invoked by the test suite, so the gate stays outside `uv run pytest` and imposes no Node-runtime dependency on the suite.
- First-run baseline committed: 12 diagnostics across 34 files analyzed — nothing fixed, suppressed, or annotated away.
- `CLAUDE.md` Toolchain section extended with the new gate command alongside the existing test/lint/import-hygiene commands.

## First-run baseline

- **pyright version:** 1.1.411
- **Install form used:** plain `uv add --dev pyright` (not the `nodejs` extra) — the default `nodeenv`-based Node provisioning succeeded on first invocation with no failure, so the `pyright[nodejs]` fallback was not needed.
- **Diagnostic count:** 12 diagnostics, 34 files analyzed, 0 warnings, 2.147s.
- **Diagnostic rules represented (one line per entry):**
  - `reportMissingImports` — `yahir_reusable_bot/config/reload.py` (1) — `watchfiles` import unresolved (optional dependency not installed in this dev env)
  - `reportRedeclaration` — `yahir_reusable_bot/discord/gateway.py` (1) — `on_message` parameter declaration obscured by a later declaration
  - `reportAttributeAccessIssue` — `yahir_reusable_bot/discord/panelkit.py` (1) — assigning `disabled` on `Item[Unknown]`
  - `reportRedeclaration` — `yahir_reusable_bot/lifecycle/identity.py` (1) — `cmdline_reader` parameter declaration obscured
  - `reportAttributeAccessIssue` — `yahir_reusable_bot/redact/sink.py` (5) — `write`/`flush` on the generically-typed `object` target parameter (the deliberate `target: object` seam `RedactingWriter` wraps)
  - `reportArgumentType` — `yahir_reusable_bot/redact/verify.py` (2) — `object` passed where `Iterable[_T]` expected in an `enumerate` call
  - `reportOptionalMemberAccess` — `yahir_reusable_bot/reliability/retry.py` (1) — `.result` accessed on a value typed as possibly `None`

  All 12 are consistent with the codebase's deliberate `Any`/`object`-at-seams injection architecture (D-62 precedent) rather than a `typeCheckingMode` misconfiguration — a flood would have looked like dozens-to-hundreds of findings across every module; this is a small, plausible, source-file-scoped set. None were fixed, suppressed, or annotated in this plan (baseline-and-burn-down, explicitly out of scope for this bounded cleanup phase).

## Gate observed working

**1. Vacuity guard fired against a mis-scoped include.** Temporarily changed `pyproject.toml`'s `[tool.pyright].include` from `["yahir_reusable_bot"]` to `["nonexistent_dir_xyz"]`, then ran the gate:

```
Traceback (most recent call last):
  ...
  File ".../scripts/pyright_baseline.py", line 110, in _assert_run_was_not_vacuous
    raise AssertionError(...)
AssertionError: pyright analyzed ZERO files — this means the [tool.pyright] 'include'
configuration matched nothing, most likely a mis-scoped path. This is NOT the same as
a clean run and is treated as a gate failure. Check pyproject.toml's [tool.pyright].include.
Exit code: 1
```

Reverted `include` back to `["yahir_reusable_bot"]`; the gate immediately returned to green (`pyright: 12 diagnostic(s) this run, 12 in the committed baseline. Gate PASSED`).

**2. Diff gate flagged a scratch type error.** Temporarily appended a deliberately-broken function to `yahir_reusable_bot/redact/core.py` (`def _scratch_type_error_for_gate_observation(x: int) -> str: return x`), then ran the gate:

```
1 NEW diagnostic(s) not present in the baseline:
  yahir_reusable_bot/redact/core.py [reportReturnType]: Type "int" is not assignable to return type "str"
  "int" is not assignable to "str"
pyright: 13 diagnostic(s) this run, 12 in the committed baseline.
Exit code: 1
```

Reverted `core.py` to its committed state (`git diff --stat yahir_reusable_bot/redact/core.py` confirmed empty); the gate immediately returned to green (`pyright: 12 diagnostic(s) this run, 12 in the committed baseline. Gate PASSED`).

## Task Commits

Each task was committed atomically:

1. **Task 2: Add RED-first unit tests for the baseline diff logic** - `b71a2a4` (test) — genuinely RED, `scripts.pyright_baseline` did not exist; `ModuleNotFoundError` at collection.
2. **Task 3: Land pyright, the explicit config, the diff gate, and the committed baseline (GREEN)** - `cc7e34b` (feat) — all 8 diff-logic tests green, full suite 214 passed, ruff clean, import-hygiene 10 passed.

**Task 1** (the package-legitimacy checkpoint) required no commit of its own — it was pre-approved per `08-CONTEXT.md`'s Runtime Decisions section (operator approval recorded 2026-08-18) and executed directly as `uv add --dev pyright` at the start of Task 3.

**Plan metadata:** committed separately per worktree protocol (SUMMARY.md + REQUIREMENTS.md only — STATE.md/ROADMAP.md updates are the orchestrator's post-wave responsibility).

## Files Created/Modified

- `tests/test_pyright_baseline.py` - Eight synthetic RED-first unit tests pinning the baseline-diff gate's contract
- `scripts/pyright_baseline.py` - The hand-rolled baseline-and-burn-down gate (`_diagnostic_key`, `_new_diagnostics`, `_assert_run_was_not_vacuous`, `main`)
- `pyright-baseline.json` - Committed first-run baseline (12 diagnostics, 34 files analyzed)
- `pyproject.toml` - `pyright>=1.1.411` added to `[dependency-groups].dev`; new `[tool.pyright]` config table (`typeCheckingMode = "basic"`, `pythonVersion = "3.12"`, `include = ["yahir_reusable_bot"]`)
- `CLAUDE.md` - Toolchain section documents pyright as a dev-only tool and the new gate command
- `uv.lock` - Updated by `uv add --dev pyright` (adds `pyright`, `nodeenv`)

## Decisions Made

- **`typeCheckingMode` set explicitly to `"basic"`.** Confirmed via research (`08-RESEARCH.md` Pitfall 2) that pyright's own default is `standard`, stricter than D-03's locked mode — an omitted key would have silently shipped a different gate. Comment left in `pyproject.toml` recording why the key is load-bearing.
- **`include` scoped to `yahir_reusable_bot/` only**, per the plan's own "Plan-time decisions" section resolving 08-RESEARCH.md's Open Question 2 — test files' dynamic-eval patterns and `scripts/`'s standalone pre-checker scaffolder would inflate the first-run baseline for zero public-surface benefit. Recorded as a follow-up, not silently dropped.
- **Plain `uv add --dev pyright` install (no `nodejs` extra needed).** The default Node provisioning succeeded transparently on first `pyright` invocation; no fallback to `pyright[nodejs]` was required.
- **`on_error` hook payload / retire-vs-keep `get_type_hints` question:** not this plan's concern — CONTEXT.md's D-03 already locked "keep the existing `get_type_hints` assertions as the narrow enforcement... (retire-vs-belt-and-suspenders decided explicitly at plan time)" as **keep** (belt-and-suspenders), so no action was needed here. That decision was settled when the plan was authored, not left open for this execution.

## Deviations from Plan

None — plan executed exactly as written. The pre-approved package-legitimacy checkpoint (Task 1) was honored per the dispatch prompt's `<pre_approved_checkpoint>` instruction and `08-CONTEXT.md`'s recorded 2026-08-18 operator approval; no new checkpoint was raised.

## Issues Encountered

None. `uv add --dev pyright` succeeded on the first attempt with no Node-provisioning failure, so no fallback to the `nodejs` extra was needed.

## User Setup Required

None beyond the package-legitimacy approval already recorded and honored (`08-CONTEXT.md` Runtime Decisions, 2026-08-18).

## Next Phase Readiness

- HYG-04 is closed: pyright runs green as a standing dev-only gate, its baseline is committed and portable (repo-relative keys), its diff logic is unit-tested, and both the vacuity guard and new-diagnostic detection have been directly observed working.
- The 12-diagnostic baseline is a dated, honest starting point for a future burn-down; none of the sites were touched by this plan.
- Plan 08-05 (GATE-02 close-out audit) can now confirm this plan's RED→GREEN commit adjacency and purity alongside the phase's other three plans.

---
*Phase: 08-redaction-hardening-cleanup*
*Completed: 2026-08-18*

## Self-Check: PASSED

- FOUND: tests/test_pyright_baseline.py
- FOUND: scripts/pyright_baseline.py
- FOUND: pyright-baseline.json
- FOUND: .planning/phases/08-redaction-hardening-cleanup/08-04-SUMMARY.md
- FOUND commit: b71a2a4 (test(08-04): add RED-first unit tests for the pyright baseline diff logic)
- FOUND commit: cc7e34b (feat(08-04): adopt pyright basic with a hand-rolled baseline gate)
- FOUND commit: 093896b (docs(08-04): complete pyright baseline gate plan)
