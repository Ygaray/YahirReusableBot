---
phase: 08-redaction-hardening-cleanup
plan: 05
subsystem: testing
tags: [gate-02, git-ancestry, pyright, get-type-hints, human-gated-closeout, audit, hyg-04]

# Dependency graph
requires:
  - phase: 08-01
    provides: REDACT-09 RED/GREEN commit pair audited by this plan
  - phase: 08-02
    provides: REDACT-10 hook RED/GREEN commit pair audited by this plan
  - phase: 08-03
    provides: REDACT-10 guide RED/GREEN commit pair + DOCS-05's two non-vacuity self-proofs audited by this plan
  - phase: 08-04
    provides: pyright basic-mode gate + baseline this plan's D-03 experiment runs against
provides:
  - "D-03 retire-vs-keep settled as KEEP on observed evidence (get_type_hints assertions kept alongside pyright)"
  - "KEEP rationale recorded in tests/test_ready_gate.py, tests/test_panelkit.py, and pyproject.toml"
  - "REQUIREMENTS.md's HYG-04 bullet corrected to match the shipped decision"
  - "GATE-02 RED-first ancestry proven from git trees for all four Phase-8 RED/GREEN pairs"
  - "DOCS-05's no-RED-commit disposition recorded with its reason and Phase-6 precedent"
  - "REDACT-09 closed (checkbox + status row) now that its ancestry is proven"
  - "Human-gated v0.2.0 close-out re-surfaced with this phase's additions named, nothing performed"
  - "Pre-existing pyright-baseline.json portability bug fixed (Rule 1 auto-fix, not plan-scoped)"
affects: [milestone-close-out, v0.2.0-repin]

actuals:
  tokens: 5101
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "git worktree add --detach <sha> for genuine-RED-ness verification (never git stash), reproducing Phase 7's GATE-02 audit method"
    - "Baseline-diff gates that persist a committed comparison artifact must relativize paths at WRITE time, not only at compare time — the writer's absolute path is otherwise baked into the artifact and breaks the moment it's read from a different checkout (worktree, clone, or merge target)"

key-files:
  created: []
  modified:
    - tests/test_ready_gate.py
    - tests/test_panelkit.py
    - pyproject.toml
    - .planning/REQUIREMENTS.md
    - scripts/pyright_baseline.py
    - pyright-baseline.json
    - tests/test_pyright_baseline.py

key-decisions:
  - "D-03 retire-vs-keep settled KEEP, on two run experiments (on_online AND render, not just the plan-mandated one) rather than reasoning: pyright stays green against a scratch-widened annotation while the paired get_type_hints assertion goes red"
  - "REDACT-09 flipped to complete only after its ancestry was independently proven in this plan (the one of the four Phase-8 requirements still unflipped entering this task); REDACT-10/DOCS-05/HYG-04 were already flipped by their own plans ahead of the intended flip-after-proof sequencing — flagged as a sequencing deviation, not a correctness one, since this task's derivation now retroactively confirms all three hold"
  - "STATE.md is NOT modified by this plan despite the plan's own files_modified list and Task 2/3 action text both specifying STATE.md edits — this worktree's dispatch protocol (parallel_execution block) explicitly forbids modifying STATE.md/ROADMAP.md in worktree-isolated execution; all STATE.md-bound content (four decision-log lines, the WR-02 Todos annotation, the close-out re-surfacing) is recorded below for the orchestrator to fold in post-merge"

patterns-established: []

requirements-completed: [REDACT-09]

coverage:
  - id: D1
    description: "D-03 retire-vs-keep settled as KEEP via observed run experiments (not reasoning): scratch-widened on_online AND render annotations both pass the pyright gate and fail their get_type_hints assertion, proving pyright does not subsume the stopgap"
    requirement: HYG-04
    verification:
      - kind: unit
        ref: "uv run pytest tests/test_ready_gate.py -k on_online -q against scratch-widened source -> 1 failed; uv run pytest tests/test_panelkit.py -k render_annotation -q against scratch-widened source -> 1 failed; uv run python scripts/pyright_baseline.py against both -> exit 0 each time (full transcripts in this SUMMARY's D-03 section)"
        status: pass
    human_judgment: false
  - id: D2
    description: "KEEP rationale recorded at three sites: both SURF-02 docstrings in tests/test_ready_gate.py, the render-arity docstring in tests/test_panelkit.py, and a new [tool.pyright] comment in pyproject.toml"
    requirement: HYG-04
    verification:
      - kind: unit
        ref: "grep -c pyright tests/test_ready_gate.py (8); grep -c pyright tests/test_panelkit.py (6); grep -c get_type_hints pyproject.toml (3)"
        status: pass
    human_judgment: false
  - id: D3
    description: "REQUIREMENTS.md's HYG-04 bullet corrected to record the KEEP decision instead of the stale supersede claim, citing plan 08-05, with no checkbox/status change in that commit"
    requirement: HYG-04
    verification:
      - kind: unit
        ref: "grep -c KEEP .planning/REQUIREMENTS.md (1); grep -c 08-05 .planning/REQUIREMENTS.md (2); uv run pytest tests/test_doc_drift.py -x -q (5 passed)"
        status: pass
    human_judgment: false
  - id: D4
    description: "GATE-02 RED-first ancestry derived from git trees (adjacency, genuine RED-ness via scratch git worktree, commit purity) for all four RED/GREEN pairs this phase produced"
    requirement: GATE-02
    verification:
      - kind: unit
        ref: "git rev-parse <green>^ == <red> for all 4 pairs; git worktree add --detach <red-sha> reproduced each RED failure live; git show --stat <red> touched only its test file (full transcripts in this SUMMARY's GATE-02 ancestry section)"
        status: pass
    human_judgment: false
  - id: D5
    description: "DOCS-05's no-RED-commit disposition recorded with its reason and the Phase-6 Known-limitations precedent, distinguished from REDACT-10's guide gate in the same file which DID ship a genuine RED commit"
    requirement: DOCS-05
    verification:
      - kind: unit
        ref: "uv run pytest tests/test_extension_guide.py -k 'telemetry_semantics or reconfiguration_recheck or reconfigure_discipline or anchor_tokens_do_not_collide' -q -> 5 passed (re-verified live); commit 6900c42's own message states all five GREEN on arrival"
        status: pass
    human_judgment: true
    rationale: "That no RED commit legitimately exists is a reasoned disposition following a stated precedent, not a fact a grep alone establishes — recorded here for a human to confirm the reasoning holds, matching how DOCS-05's manual-only row was always scoped in 08-VALIDATION.md."
  - id: D6
    description: "REDACT-09 checkbox and status-row flipped to complete, dated 2026-08-18, only after its ancestry was proven in this plan"
    requirement: REDACT-09
    verification:
      - kind: unit
        ref: "grep -n REDACT-09 .planning/REQUIREMENTS.md shows [x] in both the Track C bullet and the status table row"
        status: pass
    human_judgment: false
  - id: D7
    description: "Human-gated v0.2.0 close-out re-surfaced with this phase's additions (the on_error hook, the pyright baseline gate) named; nothing in it performed"
    requirement: GATE-02
    verification:
      - kind: unit
        ref: "git tag --list 'v0.2.0' empty; grep 'version = \"0.1.2\"' pyproject.toml still holds; git status --porcelain shows no file outside .planning/ modified"
        status: pass
    human_judgment: true
    rationale: "Absence-of-execution is mechanically confirmed above, but completeness of the re-surfaced enumeration is a human-judgment call, matching Phase 7's treatment of the same close-out surfacing (07-07-SUMMARY.md)."
  - id: D8
    description: "Pre-existing pyright-baseline.json portability bug fixed: the committed baseline stored the writing checkout's raw absolute paths, so the gate failed on every checkout but the one that wrote it (reproduced live in this worktree before any Task 1 edit)"
    requirement: HYG-04
    verification:
      - kind: unit
        ref: "uv run pytest tests/test_pyright_baseline.py -q -> 9 passed (new portability round-trip test added); uv run python scripts/pyright_baseline.py -> exit 0 after regenerating the baseline from this worktree"
        status: pass
    human_judgment: false

# Metrics
duration: ~35min
completed: 2026-08-18
status: complete
---

# Phase 08 Plan 05: D-03 retire-vs-keep on observed evidence, GATE-02 ancestry from git, human-gated close-out re-surfaced Summary

**Settled the last open Phase-8 decision (D-03 retire-vs-keep) as KEEP by running the experiment rather than reasoning about it, fixed a pre-existing pyright-baseline portability bug that was silently breaking the gate across git worktrees, derived GATE-02's RED-first ancestry from git trees for all four Phase-8 requirement pairs, closed REDACT-09, and re-surfaced the human-gated v0.2.0 close-out with nothing in it performed.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-08-18 (session start)
- **Completed:** 2026-08-18
- **Tasks:** 3 (plus one Rule-1 auto-fix commit ahead of Task 1, required to unblock every task's own verification)
- **Files modified:** 7 (2 test files, `pyproject.toml`, `.planning/REQUIREMENTS.md`, plus 3 files from the pre-Task-1 baseline-portability fix)

## Accomplishments

- D-03's retire-vs-keep question settled as **KEEP** on two observed run experiments (`on_online` and, for extra confidence, `render` too — the plan mandated only the first) rather than reasoning: both scratch-widened annotations passed the pyright gate and failed their paired `get_type_hints` assertion.
- KEEP rationale recorded at all three sites a future reader might look: both SURF-02 docstrings in `tests/test_ready_gate.py`, the render-arity docstring in `tests/test_panelkit.py`, and a new `[tool.pyright]` comment in `pyproject.toml`.
- `REQUIREMENTS.md`'s HYG-04 bullet corrected — the stale "adopting it supersedes the stopgap" clause replaced with the KEEP decision and its one-line reason, citing plan 08-05.
- GATE-02's RED-first ancestry derived from git trees (never asserted in prose) for all four Phase-8 RED/GREEN pairs, using Phase 7's `git worktree add --detach` method.
- DOCS-05's no-RED-commit disposition recorded with its reason and the Phase-6 Known-limitations precedent, explicitly distinguished from REDACT-10's guide gate in the same file, which DID ship a genuine RED commit.
- REDACT-09 closed (checkbox + status row), the last of the four Phase-8 requirements still open entering this task.
- The human-gated v0.2.0 close-out re-surfaced with this phase's two additions named (the `on_error` hook, the pyright baseline gate); nothing in it performed.
- **Unplanned, Rule-1 auto-fix:** discovered and fixed a pre-existing bug in `scripts/pyright_baseline.py` (shipped by plan 08-04) that made the committed baseline non-portable across checkouts — it broke this plan's own Task 1 verification before any Task 1 edit was made.

## D-03 retire-vs-keep experiment

Per the plan's action text, the experiment was run against `on_online`. It was independently repeated against `render` (in `tests/test_panelkit.py`) before writing that file's docstring, since the same claim was being made there and a run beats an inference from analogy.

**Experiment 1 — `on_online`.** Scratch-widened `yahir_reusable_bot/lifecycle/ready_gate.py`'s `on_online` parameter from `Callable[[HealthResult], None] | None` back to `Callable[..., None] | None` (SURF-02's pre-narrowing form):

```
$ uv run python scripts/pyright_baseline.py
pyright: 12 diagnostic(s) this run, 12 in the committed baseline.
Gate PASSED — no diagnostics outside the committed baseline.
EXIT: 0

$ uv run pytest tests/test_ready_gate.py -k on_online -q
.F                                                                       [100%]
FAILED tests/test_ready_gate.py::test_on_online_annotation_is_narrowed_to_health_result
E       assert typing.Optional[typing.Callable[..., NoneType]] == (typing.Callable[[yahir_reusable_bot.lifecycle.health.HealthResult], NoneType] | None)
1 failed, 1 passed, 10 deselected in 0.04s
EXIT: 1
```

Reverted with `git checkout -- yahir_reusable_bot/lifecycle/ready_gate.py`; confirmed via `git status --porcelain yahir_reusable_bot/` (empty) and `git diff HEAD -- yahir_reusable_bot/` (empty).

**Experiment 2 — `render`.** Scratch-widened `yahir_reusable_bot/discord/panelkit.py`'s `render` parameter from `Callable[[Any, Any], discord.Embed]` back to `Callable[..., discord.Embed]`:

```
$ uv run python scripts/pyright_baseline.py
pyright: 12 diagnostic(s) this run, 12 in the committed baseline.
Gate PASSED — no diagnostics outside the committed baseline.
EXIT: 0

$ uv run pytest tests/test_panelkit.py -k render_annotation -q
F                                                                        [100%]
FAILED tests/test_panelkit.py::test_render_annotation_is_arity_narrowed_to_two_positional_args
E       assert typing.Callable[..., discord.embeds.Embed] == typing.Callable[[typing.Any, typing.Any], discord.embeds.Embed]
1 failed, 7 deselected in 0.17s
EXIT: 1
```

Reverted with `git checkout -- yahir_reusable_bot/discord/panelkit.py`; confirmed via the same two empty checks.

**Observation matches the plan's prediction exactly, both times:** widening a public-surface annotation back to its loose pre-narrowing form is not a type error, so the pyright gate stays green; the `get_type_hints` assertion — which compares the resolved hint against one specific expected type — goes red. **Decision: KEEP.** The two mechanisms enforce different properties: pyright checks internal consistency between an annotation and how the code uses it; the assertions check that three specific public signatures carry one specific narrowed annotation. Retiring the assertions would leave the narrowed public surface — reaching consumers only at the imminent repin — enforced by nothing.

## GATE-02 ancestry (derived from git)

For each of the four RED/GREEN commit pairs this phase produced, three facts were established directly from git — never asserted in prose — reproducing Phase 7's method (`07-07-SUMMARY.md`).

| Requirement | RED commit | GREEN commit | Adjacency | Genuine RED-ness (scratch `git worktree`, literal output) | Purity |
|---|---|---|---|---|---|
| REDACT-09 (08-01) | `a12b838` | `916d4cd` | `git rev-parse 916d4cd^` = `a12b838` — MATCH | `uv run pytest tests/test_redact_core.py -k wr02_accept_rationale_survives -q` → `1 failed` — `AssertionError: WR-02 accept rationale is missing concept(s) ['phase8_ratification']` | `tests/test_redact_core.py` only (87 insertions) |
| REDACT-10 hook (08-02) | `724ae55` | `db59297` | `git rev-parse db59297^` = `724ae55` — MATCH | `uv run pytest tests/test_redact_sink.py -k "on_error or cross_fire" -q` → `4 failed` — `TypeError: RedactingWriter.__init__() got an unexpected keyword argument 'on_error'` (all four) | `tests/test_redact_sink.py` only (143 insertions) |
| REDACT-10 guide (08-03) | `4dc6f2c` | `aa59a1a` | `git rev-parse aa59a1a^` = `4dc6f2c` — MATCH | `uv run pytest tests/test_extension_guide.py -k "malformed_pattern_failclosed or seam_08" -q` → `1 failed, 7 passed` — `AssertionError: SEAM-08 section is missing malformed-pattern fail-closed contract concept(s): ['the trigger', 'the disposition', 'the withheld payload', 'the observability hook']` | `tests/test_extension_guide.py` only (117 insertions) |
| HYG-04 diff gate (08-04) | `b71a2a4` | `cc7e34b` | `git rev-parse cc7e34b^` = `b71a2a4` — MATCH | `uv run pytest tests/test_pyright_baseline.py -q` → collection `ERROR`: `ModuleNotFoundError: No module named 'scripts.pyright_baseline'` | `tests/test_pyright_baseline.py` only (148 insertions) |

Method, matching Phase 7 exactly: each RED commit's tree was checked out into a scratch worktree (`git worktree add --detach /tmp/gsd-gate02-audit/<name> <red-sha>` — never `git stash`), the requirement's test command was run there to reproduce a real failure, and the worktree was removed (`git worktree remove --force`) before moving to the next pair. `git status --short` in this worktree was empty both before and after the whole audit, and `git rev-parse --abbrev-ref HEAD` confirmed this worktree's own branch (`worktree-agent-aa73965b755036b57`) was never touched by any of the four scratch checkouts. All four pairs hold on every one of the three facts — GATE-02's RED-first obligation is satisfied for REDACT-09, REDACT-10 (both halves), and HYG-04.

## DOCS-05 disposition

DOCS-05's two D-04 gates — `test_seam_08_section_pins_the_changed_writes_telemetry_semantics` and `test_seam_08_section_pins_the_reconfiguration_recheck_discipline` (both in `tests/test_extension_guide.py`, landed in commit `6900c42`) — pin prose that was **already true** of `EXTENSION-GUIDE.md` §7 before this phase touched anything: the telemetry-semantics and reconfigure-discipline paragraphs already existed, unchanged, from the Phase-6 promotion. There is no pre-fix source for these two gates to be RED against, so **no RED commit exists for them, and none was manufactured.**

This is a deliberate disposition, not a gap. The GATE-02-satisfying evidence for these two gates is each one's non-vacuity self-proof — `test_selfproof_telemetry_semantics_gate_catches_a_deleted_paragraph` and `test_selfproof_reconfigure_discipline_gate_catches_a_deleted_paragraph` — each of which writes a temporary copy of the guide with its target paragraph deleted, points `GUIDE_PATH` at it, re-runs the primary assertion, and asserts it fails there. Commit `6900c42`'s own message states this explicitly: "All five tests GREEN on arrival per this plan's DOCS-05 GATE-02 disposition: the two claims they pin are already true of the guide as written, so the gate is proven non-vacuous by each self-proof observed failing against a broken copy, not by a RED commit." Re-verified live in this plan:

```
$ uv run pytest tests/test_extension_guide.py -k "telemetry_semantics or reconfiguration_recheck or reconfigure_discipline or anchor_tokens_do_not_collide" -v
tests/test_extension_guide.py::test_seam_08_section_pins_the_changed_writes_telemetry_semantics PASSED
tests/test_extension_guide.py::test_selfproof_telemetry_semantics_gate_catches_a_deleted_paragraph PASSED
tests/test_extension_guide.py::test_seam_08_section_pins_the_reconfiguration_recheck_discipline PASSED
tests/test_extension_guide.py::test_selfproof_reconfigure_discipline_gate_catches_a_deleted_paragraph PASSED
tests/test_extension_guide.py::test_new_anchor_tokens_do_not_collide_with_the_recipe_2_ordering_assertion PASSED
5 passed, 11 deselected in 0.03s
```

**Precedent:** this treatment mirrors the Phase-6 Known-limitations gate (`tests/test_extension_guide.py:324-403`, `test_seam_08_section_states_architectural_inversion` + its self-proof), which pinned already-true prose the same way, and which this plan's own docstring block in `test_extension_guide.py` cites by name ("Phase 8 plan 03 ... three new content gates ... each paired with a non-vacuity self-proof").

**Distinction from REDACT-10's guide gate, in the SAME file:** `test_seam_08_section_states_the_malformed_pattern_failclosed_contract` (also in `tests/test_extension_guide.py`, also landed in Phase 8 plan 03) **DID** ship a genuine RED commit (`4dc6f2c`, in the GATE-02 ancestry table above) — because that paragraph genuinely did not exist before the fix landed. The distinction between "pin already-true prose" (DOCS-05, no RED commit) and "pin newly-added prose" (REDACT-10's guide half, genuine RED commit) is real and mechanically observable in the same file's git history, not a convenience.

## Human-gated close-out — surfaced, not performed

Per `ECOSYSTEM.md` §3, the following is handed to the human for confirmation. **Nothing below was executed by this plan or any plan in Phase 8.** This restates Phase 7's close-out (`07-07-SUMMARY.md`) with Phase 8's additions folded in.

1. **Version bump and tag cut** — `pyproject.toml` `0.1.2 → 0.2.0`, tag `v0.2.0`. Not done here. Verified: `git tag --list 'v0.2.0'` is empty; `pyproject.toml` still reads `version = "0.1.2"`.
2. **The WeatherBot repin** — `[tool.uv.sources]` bump `v0.1.2 → v0.2.0`, `uv lock --upgrade`, `uv sync`. Not done here.
3. **Two separately-green checks, never bundled** (unchanged from Phase 7's framing):
   - **(a) The PC-01 parity gate** — WeatherBot's existing, unmodified `tests/test_redact_hygiene.py` (6 tests) against the hub-backed replacement; all 6 must pass before `weatherbot/_redact.py` is deleted. Two of the six need a **signature-level test update**, not merely an import swap, because `RedactingWriter`'s constructor differs from the app-local `_LiveStderr` it replaces (Phase-6 carry-forward, unchanged).
   - **(b) The MATCH-03 duplicate-`spec.name` sweep** — WeatherBot's command specs must be swept for duplicate names before the repin lands.
4. **The SURF-02 blast-radius note** (unchanged from Phase 7): narrowing `on_online` is a public hub-surface change; the only live consumer's handler already conforms.
5. **The permanent scope boundary** (unchanged): `weatherbot/weather/client.py`'s domain-specific redacted re-raise stays app-local forever.
6. **NEW from Phase 8 — REDACT-10's `on_error` hook.** `RedactingWriter`'s constructor has gained an optional, keyword-only `on_error: Callable[[re.error], None] | None = None` parameter (mirroring `on_redaction`'s shape, fires only inside the existing fail-closed `except re.error` branch, receives only the caught exception — never the withheld payload). This changes NO existing call site (default `None`, purely additive) — the repin **may** wire it, but nothing requires it to.
7. **NEW from Phase 8 — the hub now carries a pyright gate the consumer does not inherit.** `scripts/pyright_baseline.py` + `pyright-baseline.json` are dev-only, `[dependency-groups].dev`-scoped tooling; a consumer pinning the hub via `[tool.uv.sources]` does not install `pyright` and is not gated by this baseline. This is a hub-internal hygiene mechanism, not a contract the repin needs to satisfy.

No version bump, tag, repin, `uv sync`, or deploy was performed by this plan or any plan in Phase 8. `git status --porcelain` at the end of Task 3 showed only `.planning/REQUIREMENTS.md` modified — no file outside `.planning/` was touched by this task.

## Task Commits

Each task was committed atomically:

1. **Rule-1 auto-fix (pre-Task-1): pyright baseline portability** — `93b2c62` (fix) — pre-existing bug from plan 08-04, discovered because it blocked Task 1's own verification before any Task 1 edit.
2. **Task 1: Settle D-03's retire-vs-keep on observed evidence, and record it** — `96b2168` (docs)
3. **Task 2: Correct the stale HYG-04 wording and record the phase's decisions** — `7eec05f` (docs) — STATE.md portion deferred, see Deviations.
4. **Task 3: Derive GATE-02 ancestry from git, flip the checkboxes, and re-surface the close-out** — `d0b5698` (docs) — STATE.md portion deferred, see Deviations.

**Plan metadata:** committed separately per worktree protocol (SUMMARY.md + REQUIREMENTS.md only — STATE.md/ROADMAP.md updates are the orchestrator's post-wave responsibility).

## Files Created/Modified

- `tests/test_ready_gate.py` — both SURF-02 docstrings extended with the post-HYG-04 KEEP rationale.
- `tests/test_panelkit.py` — the render-arity docstring extended with the same KEEP rationale, plus the accurate detail that the render signature's home IS inside pyright's include scope while this test file is not.
- `pyproject.toml` — new `[tool.pyright]` comment cross-referencing the D-03 KEEP decision and its observed evidence.
- `.planning/REQUIREMENTS.md` — HYG-04 bullet corrected (KEEP, not supersede); REDACT-09 checkbox + status row flipped to complete, dated.
- `scripts/pyright_baseline.py` — Rule-1 fix: `_diagnostic_key` now passes an already-relative file path through unchanged; new `_relativize_diagnostics` rewrites persisted diagnostics to repo-relative paths at `--write-baseline` time.
- `pyright-baseline.json` — regenerated from this worktree with the fixed writer: same 12 diagnostics across the same 34 files, now portable.
- `tests/test_pyright_baseline.py` — new regression test reproducing the two-checkout write/read scenario end to end.

## Decisions Made

- **D-03 retire-vs-keep: KEEP**, settled by two run experiments (see above), not reasoning.
- **REDACT-09 flip sequencing:** REDACT-10, DOCS-05, and HYG-04 were already flipped to complete by their own plans (08-02/08-03/08-04) ahead of the phase's intended "flip only after Task-3 ancestry proof" sequencing (`08-05-PLAN.md`'s `must_haves.truths` states this explicitly: "checkboxes and status rows flip only AFTER their ancestry is proven, never before — the same sequencing Phase 7 used"). This task's independent ancestry derivation now retroactively confirms all three hold, so no correction was needed to the earlier plans' commits — but the sequencing itself was not followed as designed. Recorded here rather than silently glossed over.
- **STATE.md decision-log content, prepared here for the orchestrator to fold in post-merge** (this worktree's dispatch protocol forbids direct STATE.md edits):
  - **D-02 / REDACT-09** — already recorded in STATE.md by an earlier merge (08-01's decision-log line). No new line needed; REDACT-09's *closure* (checkbox flip, ancestry proof) is what plan 08-05 newly adds, not the D-02 decision itself.
  - **D-01 / REDACT-10** — already recorded in STATE.md (08-02's decision-log line, `on_error` hook shape and payload).
  - **D-04 / DOCS-05** — already recorded in STATE.md (08-03's decision-log line, the two prose gates + the anchor-collision guard).
  - **D-03 / HYG-04 (NEW — not yet in STATE.md's Decisions list):** pyright `basic` mode adopted with an explicit `typeCheckingMode` key (D-03), `include` scoped to `yahir_reusable_bot/` only (source-only, tests/scripts excluded per 08-04's plan-time decision), the hand-rolled `scripts/pyright_baseline.py` baseline-and-burn-down gate with its first-run count (12 diagnostics, 34 files analyzed, 08-04), and now, from this plan: the D-03 retire-vs-keep call settled as **KEEP** on two observed experiments (`on_online`, `render`) — pyright verifies annotation-internal-consistency, the `get_type_hints` assertions verify three specific narrowed signatures, and a silent re-widening passes the former and fails the latter. Also from this plan: a pre-existing bug in `scripts/pyright_baseline.py` (the committed baseline stored the writing checkout's raw absolute paths, breaking the gate on every OTHER checkout including the one this branch merges into) was fixed and the baseline regenerated with portable relative paths.
  - **§ Todos — Phase-5 WR-02 residual:** the existing STATE.md Todos entry ("Residual from Phase 5's code review (WR-02)") should be annotated — strike-through style, matching the resolved Phase-7 todos already in that section — as **settled by REDACT-09 in Phase 8** (plan 08-01, ratified ACCEPT under D-02; ancestry proven in plan 08-05). Do not delete the entry.
  - **Close-out re-surfacing:** the full "Human-gated close-out — surfaced, not performed" section above should be folded into STATE.md, superseding Phase 7's version of the same section.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a pre-existing pyright-baseline portability bug (shipped by plan 08-04)**
- **Found during:** Pre-Task-1 verification (running `uv run python scripts/pyright_baseline.py` cold, before any Task 1 edit).
- **Issue:** `pyright-baseline.json` (committed by plan 08-04) stored pyright's raw absolute `file` paths verbatim. This worktree's absolute path differs from the worktree that wrote the baseline (`agent-afa9e3f8c092818ca`), so `_diagnostic_key`'s `relative_to(root)` call raised for every baseline entry; the `except` fallback then kept the baseline's now-foreign absolute path unchanged, making the entire baseline compare unequal to a live run's (correctly relativized) keys. Reproduced live: `uv run python scripts/pyright_baseline.py` exited 1 and listed all 8 unique baseline keys as "new" — before this worktree had made a single edit.
- **Fix:** `_diagnostic_key` now passes an already-relative file path through unchanged (not just the absolute case). New `_relativize_diagnostics` helper rewrites each diagnostic's `file` field to a repo-relative POSIX path before `--write-baseline` persists it, so the artifact is portable the moment it's written. `pyright-baseline.json` regenerated from this worktree: identical 12 diagnostics across the identical 34 files, now with portable paths.
- **Files modified:** `scripts/pyright_baseline.py`, `pyright-baseline.json`, `tests/test_pyright_baseline.py` (new regression test).
- **Verification:** `uv run pytest tests/test_pyright_baseline.py -q` → 9 passed (8 pre-existing + 1 new); `uv run python scripts/pyright_baseline.py` → exit 0.
- **Committed in:** `93b2c62` (separate fix commit, ahead of Task 1 — this is infrastructure that unblocks every task's own verification, not part of Task 1's docs-only scope).
- **Why this matters beyond this worktree:** without the fix, the SAME failure would have recurred the moment this branch merges into `main` (whose absolute path matches neither worktree that touched the baseline before this fix), silently breaking HYG-04's standing gate for every future contributor.

**2. [Operational deviation, not a deviation rule] STATE.md and ROADMAP.md not modified**
- **Found during:** Task 2 and Task 3, both of which specify `.planning/STATE.md` edits in their action text, and the plan's own `files_modified` frontmatter lists `.planning/STATE.md`.
- **Issue:** This worktree's dispatch protocol (`<parallel_execution>` block in the spawn prompt) explicitly forbids modifying `.planning/STATE.md` or `.planning/ROADMAP.md` in worktree-isolated execution — those are the orchestrator's post-merge responsibility, to avoid cross-agent merge conflicts on shared files.
- **Resolution:** All STATE.md-bound content (the D-03/HYG-04 decision-log line, the WR-02 Todos annotation, the re-surfaced close-out) is recorded in full above, under "Decisions Made" and "Human-gated close-out — surfaced, not performed," for the orchestrator to fold into STATE.md after merge. This is not a Rule 1-4 deviation (no bug, no missing functionality, no blocker, no architectural question) — it is the worktree protocol's explicit, higher-priority instruction overriding the plan's file list for this one shared artifact.
- **Acceptance-criteria impact:** Task 2's and Task 3's criteria naming `.planning/STATE.md` (grep for `KEEP`/`REDACT-09`/etc., or the `on_error` mention) could not be verified against this worktree's git tree directly. Checked what could be checked: `grep -c 'on_error' .planning/STATE.md` in the PRE-EXISTING file (before this plan touched anything) already returns 2 — from the 08-02 decision-log entry — so that specific criterion is already satisfied without action; the remaining STATE.md criteria will be satisfied once the orchestrator applies the content recorded above.

---

**Total deviations:** 1 Rule-1 auto-fix (pyright baseline portability) + 1 operational deviation (STATE.md/ROADMAP.md deferred to orchestrator per worktree protocol).
**Impact on plan:** The Rule-1 fix was necessary for correctness — without it, HYG-04's standing gate silently breaks on every checkout but the one that wrote the baseline, including the eventual merge target. The STATE.md deferral is a protocol-mandated adjustment, not scope creep; all intended content is preserved above for the orchestrator to apply.

## Issues Encountered

None beyond the pyright-baseline portability bug documented above, which self-resolved with the Rule-1 fix.

## User Setup Required

None. The human-gated close-out items above are **surfaced for confirmation**, not something this plan can or does execute.

## Next Phase Readiness

Phase 8 is complete. All four Phase-8 requirements (REDACT-09, REDACT-10, DOCS-05, HYG-04) are closed on proven evidence: REDACT-09 newly closed by this plan; REDACT-10, DOCS-05, and HYG-04 already closed by their own plans and now retroactively confirmed by this plan's independent GATE-02 ancestry derivation. GATE-02 itself stays **unchecked** in `REQUIREMENTS.md` — milestone-standing, same treatment GATE-01 received in v0.1.2 — and this was Phase 8 of the milestone, so with this plan's close all of Milestone v0.2.0's phase work is done. The human-gated close-out above is ready for confirmation whenever the human elects to act on it — no part of it was performed by this plan or any plan in Phase 8.

Full suite: `uv run pytest -q` → 215 passed, zero warnings. `uv run pytest tests/test_import_hygiene.py -q` → 10 passed. `uv run pytest tests/test_doc_drift.py -q` → 5 passed. `uv run python scripts/pyright_baseline.py` → exit 0 (Gate PASSED). `uv run ruff check` → All checks passed.

---
*Phase: 08-redaction-hardening-cleanup*
*Completed: 2026-08-18*

## Self-Check: PASSED

- FOUND: tests/test_ready_gate.py
- FOUND: tests/test_panelkit.py
- FOUND: pyproject.toml
- FOUND: .planning/REQUIREMENTS.md
- FOUND: scripts/pyright_baseline.py
- FOUND: pyright-baseline.json
- FOUND: tests/test_pyright_baseline.py
- FOUND: .planning/phases/08-redaction-hardening-cleanup/08-05-SUMMARY.md
- FOUND commit: 93b2c62 (fix(08-05): make the pyright baseline gate portable across checkouts)
- FOUND commit: 96b2168 (docs(08-05): settle D-03 retire-vs-keep as KEEP on observed evidence and record the rationale)
- FOUND commit: 7eec05f (docs(08-05): correct the stale HYG-04 stopgap wording)
- FOUND commit: d0b5698 (docs(08-05): derive GATE-02 ancestry from git and close REDACT-09)
