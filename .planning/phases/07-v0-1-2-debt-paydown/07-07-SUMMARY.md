---
phase: 07-v0-1-2-debt-paydown
plan: 07
subsystem: gate-audit
tags: [gate-02, git-ancestry, backlog, human-gated-closeout, audit]

# Dependency graph
requires:
  - phase: 07-v0-1-2-debt-paydown/07-01
    provides: MATCH-03 RED/GREEN commit pair audited by this plan
  - phase: 07-v0-1-2-debt-paydown/07-02
    provides: DISC-07/DISC-08 RED/GREEN commit pair audited by this plan
  - phase: 07-v0-1-2-debt-paydown/07-03
    provides: HYG-03 RED/GREEN commit pair and filterwarnings=error baseline audited by this plan
  - phase: 07-v0-1-2-debt-paydown/07-04
    provides: SURF-02 RED/GREEN commit pair audited by this plan
  - phase: 07-v0-1-2-debt-paydown/07-05
    provides: HYG-02 RED/GREEN commit pair and the LIFE-05 D-61a exemption audited by this plan
  - phase: 07-v0-1-2-debt-paydown/07-06
    provides: DOCS-02 RED/GREEN commit pair and DOCS-03 filesystem evidence audited by this plan
provides:
  - "GATE-02 proven from git trees for all seven behavioral requirements (adjacency + genuine RED-ness + purity)"
  - "LIFE-05's D-61a no-behavioral-change exemption recorded, not silently omitted"
  - "Three manual-only sign-offs (SURF-02 callback, LIFE-05 doc, DOCS-03) confirmed against live source"
  - ".planning/backlog/ADOPT-STATIC-TYPE-CHECKER.md — pickup-ready deferred backlog entry"
  - "Human-gated close-out surfaced with its two separately-green checks named, nothing performed"
affects: [GATE-02, milestone-close-out]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "git worktree add --detach <sha> for genuine-RED-ness verification (never git stash, never touches the main working tree's HEAD)"

key-files:
  created:
    - .planning/backlog/ADOPT-STATIC-TYPE-CHECKER.md
  modified: []

key-decisions:
  - "RED-first ancestry proven with git worktree add --detach against a scratch path outside the repo, not git stash — keeps the main working tree's HEAD untouched throughout the audit (destructive-git-prohibition compliant)"
  - "07-VALIDATION.md's per-requirement -k filter strings did not all match the actual test names shipped (e.g. 'label_kwarg' vs the real 'label_as_a_structured_kwarg' / 'structured_kwarg'); this task's ancestry table records the exact -k strings that were actually run against each RED commit, not the validation doc's literal text, so the evidence is real rather than copy-pasted"
  - "The probe rollup arithmetic (21 == 11 + 10) was independently re-derived by reading each of the six prior plans' own 'Flagged Assumptions' equality-check line, not copied from the 07-07-PLAN.md rollup table — both sources agree"

requirements-completed: []

coverage:
  - id: D1
    description: "All four standing gates (full suite, real-filter suite, import-hygiene, ruff) run and recorded green; no source or test file written by Task 1"
    requirement: "GATE-02"
    verification:
      - kind: unit
        ref: "uv run pytest -q (184 passed, zero warnings)"
        status: pass
      - kind: unit
        ref: "uv run pytest -q -o 'filterwarnings=error' (184 passed)"
        status: pass
      - kind: unit
        ref: "uv run pytest tests/test_import_hygiene.py -q (10 passed)"
        status: pass
      - kind: unit
        ref: "uv run ruff check (All checks passed!)"
        status: pass
    human_judgment: false
  - id: D2
    description: "RED-first ancestry (adjacency, genuine RED-ness at the RED commit's tree, commit purity) derived from git for all 7 behavioral requirements"
    requirement: "GATE-02"
    verification:
      - kind: unit
        ref: "git rev-parse <green>^ == <red-sha> for all 6 RED/GREEN commit pairs (DISC-07/DISC-08 share one pair); git worktree checkout of each RED sha reproduces the documented failure; git show --stat <red> lists only test files"
        status: pass
    human_judgment: false
  - id: D3
    description: "LIFE-05's D-61a exemption recorded verbatim with git evidence that identity.py's diff is docstring-only across 07-05"
    requirement: "GATE-02 (LIFE-05 exemption)"
    verification:
      - kind: unit
        ref: "tests/test_identity.py::test_bundled_short_option_group_not_matched (1 passed); git diff b44e555~1..2e97b64 -- yahir_reusable_bot/lifecycle/identity.py shows only docstring lines added"
        status: pass
    human_judgment: false
  - id: D4
    description: "Three manual-only sign-offs confirmed by direct read of live source: SURF-02 callback rationale in scheduler/engine.py's register docstring, LIFE-05 doc half in EXTENSION-GUIDE.md section 4, DOCS-03's corrected three-site enumeration against a live WeatherBot filesystem check"
    requirement: "SURF-02, LIFE-05 (doc), DOCS-03"
    verification: []
    human_judgment: true
    rationale: "All three are manual-only by design per 07-VALIDATION.md (prose-accuracy / recorded-non-issue claims an automated check derived from the same source cannot validate) — this task performed the human read and records the result below, plus mechanical existence checks (file paths on disk) where applicable."
  - id: D5
    description: "The deferred static-type-checker idea is filed as a pickup-ready backlog entry citing SURF-02/D-62/D-63, and no type checker entered the toolchain"
    requirement: "backlog filing"
    verification:
      - kind: unit
        ref: "test -f .planning/backlog/ADOPT-STATIC-TYPE-CHECKER.md; grep -q 'SURF-02' <file>; ! grep -qi 'pyright|mypy|pyre' pyproject.toml"
        status: pass
    human_judgment: false
  - id: D6
    description: "The human-gated close-out is surfaced (version bump, tag, repin, two separately-green checks, SURF-02 blast radius, Phase-6 carry-forward, permanent scope boundary) with nothing in it performed"
    requirement: "ECOSYSTEM.md §3 human gate"
    verification:
      - kind: unit
        ref: "git tag --list 'v0.2.0' empty; grep 'version = \"0.1.2\"' pyproject.toml still holds; git diff HEAD~1 -- pyproject.toml empty; git -C /home/yahir/Projects/WeatherBot status --porcelain unchanged from this plan's baseline"
        status: pass
    human_judgment: false

# Metrics
duration: ~20min
completed: 2026-08-04
status: complete
---

# Phase 07 Plan 07: GATE-02 close-out — git-derived ancestry, manual sign-offs, deferred backlog, human-gated handoff Summary

**Phase 7 closes with GATE-02 proven from git trees (not prose) for all seven behavioral requirements, LIFE-05's no-behavioral-change exemption recorded rather than papered over, three manual-only verifications confirmed against live source, the deferred static-type-checker idea filed as a pickup-ready backlog entry, and the human-gated close-out surfaced with nothing in it performed.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2 completed
- **Files modified:** 1 created (backlog entry), 1 created (this SUMMARY)

## Task 1 — Standing gates + GATE-02 ancestry audit

### Standing gates (literal output)

| Gate | Command | Result |
|---|---|---|
| Full suite | `uv run pytest -q` | `184 passed in 1.98s` — zero warnings in the summary |
| Real filter (the actual HYG-03/D-65 enforcement mechanism) | `uv run pytest -q -o 'filterwarnings=error'` | `184 passed in 1.97s` |
| Import-hygiene (grimp graph + isolated-import + AST litmus + redact confinement) | `uv run pytest tests/test_import_hygiene.py -q` | `10 passed in 0.26s` |
| Standing doc-drift gate | `uv run pytest tests/test_doc_drift.py -q` | `5 passed in 0.06s` |
| Lint | `uv run ruff check` | `All checks passed!` |

`git status --short` and `git diff --stat HEAD -- yahir_reusable_bot/ tests/` were both empty
before Task 1 wrote anything — confirming no source or test file was touched by this audit task,
as required.

### GATE-02 RED-first ancestry — derived from git trees

For each requirement, three facts were established directly from git, not asserted in prose:

1. **Adjacency** — `git rev-parse <GREEN>^` compared against the RED commit's sha.
2. **Genuine RED-ness** — the RED commit's tree was checked out into a scratch `git worktree`
   (`git worktree add --detach <scratch-path> <red-sha>`, never `git stash`, so the main working
   tree's HEAD was never touched) and the requirement's test command was run there, reproducing a
   real failure with the exact assertion text shown.
3. **Purity** — `git show --stat <RED>` lists only test files (or, for DOCS-02, only the new gate
   file `tests/test_doc_drift.py`).

| Requirement | RED commit | GREEN commit | Adjacency | Genuine RED-ness (command + failure) | Purity |
|---|---|---|---|---|---|
| MATCH-03 | `d92351d` | `7da4568` | `git rev-parse 7da4568^` = `d92351d` — MATCH | `uv run pytest tests/test_registry.py -k duplicate -q` → `3 failed, 2 passed` (`DID NOT RAISE ValueError` x3) | `tests/test_registry.py` only (75 insertions) |
| DISC-07 / DISC-08 | `c42e90f` | `802ac85` | `git rev-parse 802ac85^` = `c42e90f` — MATCH | `uv run pytest tests/test_gateway.py -k "retry_pin_forbidden or eviction_delete_failure" -q` → `2 failed` (Forbidden-distinct log absent; `delete_attempts == 1` not `2`) | `tests/test_gateway.py` only (203 insertions) |
| HYG-03 | `b5cbe36` | `b6ba940` | `git rev-parse b6ba940^` = `b5cbe36` — MATCH | `uv run pytest tests/test_gateway.py -k "stop_closes_the_never_scheduled or stop_logs_a_distinct_scheduling_failure" -q` → `2 failed` (scheduling-failure message absent from `cap`; `RuntimeWarning` coroutine-never-awaited emitted) | `tests/test_gateway.py` only (175 insertions) |
| SURF-02 | `7f60a90` | `94e14d9` | `git rev-parse 94e14d9^` = `7f60a90` — MATCH | `uv run pytest tests/test_ready_gate.py tests/test_panelkit.py -k "on_online_annotation or render_annotation" -q` → `2 failed` (`Callable[..., Embed] != Callable[[Any, Any], Embed]`; `on_online` hint still `Callable[..., None] \| None`) | `tests/test_panelkit.py` + `tests/test_ready_gate.py` only (66 insertions) |
| HYG-02 | `b44e555` | `d2e9ca3` | `git rev-parse d2e9ca3^` = `b44e555` — MATCH | `uv run pytest tests/test_ready_gate.py tests/test_reload.py -k structured_kwarg -q` → `2 failed` (`event` carried the interpolated label text, not the fixed string) | `tests/test_ready_gate.py` + `tests/test_reload.py` only (125 insertions) |
| DOCS-02 | `2793076` | `824702e` | `git rev-parse 824702e^` = `2793076` — MATCH | `uv run pytest tests/test_doc_drift.py -q` → `1 failed, 4 passed` (`assert violations == []` failed naming `REQUIREMENTS.md:119` and `HUB-HARDENING-REPORT-v0.1.2.md:213`) | `tests/test_doc_drift.py` only, new file (258 insertions) |

**Deviation from `07-VALIDATION.md`'s literal `-k` strings, recorded for the audit trail:** the
validation doc's HYG-02 filter (`label_kwarg`) does not match either test's actual name
(`test_best_effort_hook_logs_the_label_as_a_structured_kwarg`,
`test_reload_best_effort_hook_logs_the_label_as_a_structured_kwarg`) — no test name contains the
contiguous substring `label_kwarg`. This task used `-k structured_kwarg` (verified to select
exactly the two intended tests and nothing else) instead of the validation doc's stale string, so
the RED-ness evidence above is a real run, not a copy of a non-matching command.

All six RED/GREEN pairs hold on every one of the three facts. GATE-02's RED-first obligation is
satisfied for MATCH-03, DISC-07, DISC-08, SURF-02, HYG-02, HYG-03, and DOCS-02.

### GATE-02 exemption (LIFE-05, D-61a)

LIFE-05 ships **no behavioral change** to `yahir_reusable_bot/lifecycle/identity.py` beyond a
docstring-only addition — `_argv_matches_marker` continues to leave the bundled short-option
group (`python -Om<module>` / `-Im<module>`) undecoded, exactly as before this phase. Per D-61a
(locked in `07-CONTEXT.md`), this requirement's GATE-02 RED-first obligation is satisfied by the
**already-green** pinned limitation test
`tests/test_identity.py::test_bundled_short_option_group_not_matched` — a boundary guard that was
GREEN both before and after v0.1.2's WR-01 fix, and stays GREEN both before and after this phase.
**No artificial RED test was manufactured** for a decision whose decided outcome is "no
behavioral change." Re-verified live in this plan:

```
$ uv run pytest tests/test_identity.py -k bundled_short_option -q
. [100%]
1 passed, 16 deselected in 0.04s

$ git diff b44e555~1..2e97b64 -- yahir_reusable_bot/lifecycle/identity.py
+    Phase 7 (D-61, LIFE-05) ratified this boundary rather than closing it —
+    the decision record lives in ``.planning/phases/07-v0-1-2-debt-paydown/
+    07-CONTEXT.md``. The constraint above is now ALSO stated consumer-facing
+    in ``EXTENSION-GUIDE.md`` section 4, not only here.
```

Five lines added, all inside a docstring paragraph; zero executable lines added, removed, or
modified. This is an intentional exemption, not a gap.

### Manual-only sign-offs

**1. SURF-02 (`callback` third site) — `scheduler/engine.py`'s `register` docstring.**
Confirmed present, verbatim: *"the variadic form IS the accurate contract — this engine is
host-agnostic and a different host binds its own arbitrary callable through this identical hole.
This is injection-by-`Any` at a seam, matching the deliberate `Any` architecture at
`panelkit.render` and `DispatchOutcome.render_arg`, not sloppiness. Reviewed and left as-is; no
test pins this row (a recorded non-issue with no behavior delta is manual-only by design ...)."*
The leave-variadic rationale is present and matches D-62's decided verdict. **Sign-off: PASS.**

**2. LIFE-05 (doc half) — `EXTENSION-GUIDE.md` section 4.** Confirmed present: names the bundled
form explicitly (`python -Omyourmodule`, `python -Imyourmodule`), states "Do not launch your
daemon that way," and records the asymmetric-failure-direction reasoning ("A false negative...
merely reports a live daemon as dead — annoying, but recoverable. A false positive delivers SIGHUP
— whose default disposition is *terminate* — to an unrelated, recycled PID."). This is stated as a
deliberate, permanent limitation, not an unfixed bug. **Sign-off: PASS.**

**3. DOCS-03 — corrected enumerations vs. the WeatherBot checkout on disk.** Both
`.planning/REQUIREMENTS.md` (human-gated close-out block) and
`.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md` (H18 origin sentence) name all three de-hack
sites, including the *producing* site `weatherbot/ops/selfcheck.py:to_health_result` — confirmed
by re-reading both files in this task. Filesystem check re-run live against the WeatherBot
checkout, matching 07-06-SUMMARY.md's recorded evidence exactly:

```
ABSENT weatherbot/ops/daemon.py
EXISTS weatherbot/scheduler/daemon.py
EXISTS weatherbot/ops/selfcheck.py
EXISTS weatherbot/scheduler/wiring.py
```

**Sign-off: PASS.**

### Probe rollup arithmetic — independently re-derived

The phase-wide claim (`21 probe-surfaced == 11 authored + 10 flagged`) was re-checked by reading
each of the six prior plans' own "Flagged Assumptions" equality-check line directly, not copied
from `07-07-PLAN.md`'s rollup table:

| Plan | Requirements | Probe rows | Authored | Flagged | Source line |
|---|---|---|---|---|---|
| 07-01 | MATCH-03 | 2 | 2 | 0 | "2 probe-surfaced == 2 authored into `must_haves` + 0 carried" |
| 07-02 | DISC-07, DISC-08 | 6 | 2 | 4 | "6 probe-surfaced == 2 authored into `must_haves` + 4 carried" |
| 07-03 | HYG-03 | 1 | 1 | 0 | "1 probe-surfaced == 1 authored into `must_haves` + 0 carried" |
| 07-04 | SURF-02 | 1 | 0 | 1 | "1 probe-surfaced == 0 authored into `must_haves` + 1 carried" |
| 07-05 | HYG-02, LIFE-05 | 3 | 2 | 1 | "3 probe-surfaced == 2 authored into `must_haves` + 1 carried" |
| 07-06 | DOCS-02, DOCS-03 | 8 | 4 | 4 | "8 probe-surfaced == 4 authored into `must_haves` + 4 carried" |
| **total** | **9** | **21** | **11** | **10** | 2+6+1+1+3+8=21; 2+2+1+0+2+4=11; 0+4+0+1+1+4=10 |

The rollup holds: **21 == 11 + 10**, confirmed by independent recomputation, not a repeated claim.

## Task 2 — Deferred backlog entry + human-gated close-out surfaced

### Backlog entry filed

`.planning/backlog/ADOPT-STATIC-TYPE-CHECKER.md` created — records what was raised (an annotation
nothing checks is a comment with extra syntax, raised unprompted during SURF-02), why it was
deferred (a toolchain change every future phase then pays; the first run over this codebase's
deliberately `Any`-heavy injection seams surfaces its own backlog), the head start Phase 7 already
shipped (three known-good `get_type_hints`-pinned signatures), and the four sizing decisions for
whoever picks it up (`basic` vs `strict`, baseline-and-burn-down vs fix-all-before-green,
`discord.py==2.7.1`'s stub quality, confirming the `Any`-at-seams sites are annotated as
intentional). No type checker was added to `[dependency-groups].dev` — `pyproject.toml` is
untouched by this plan (`git diff HEAD~1 -- pyproject.toml` is empty, confirmed after this plan's
commits).

### Human-gated close-out — surfaced, NOT performed

Per `ECOSYSTEM.md` §3, the following is handed to the human for confirmation. **Nothing below was
executed by this plan or any prior plan in Phase 7.**

1. **Version bump and tag cut** — `pyproject.toml` `0.1.2 → 0.2.0`, tag `v0.2.0`. Not done here.
   Verified: `git tag --list 'v0.2.0'` is empty; `pyproject.toml` still reads
   `version = "0.1.2"`.
2. **The WeatherBot repin** — `[tool.uv.sources]` bump `v0.1.2 → v0.2.0`, `uv lock --upgrade`,
   `uv sync`. Not done here. Verified: `git -C /home/yahir/Projects/WeatherBot status --porcelain`
   shows only the pre-existing, unrelated dirty state from WeatherBot's own concurrent "v2.2"
   session (`M .planning/config.json`, `?? .planning/REQUIREMENTS.md`) — the same two lines present
   before this plan started (per this plan's `<verified_state_entering_this_plan>` context); this
   plan added nothing to that diff and touched no file under `/home/yahir/Projects/WeatherBot`.
3. **Two separately-green checks, never bundled:**
   - **(a) The PC-01 parity gate** — run WeatherBot's existing, UNMODIFIED
     `tests/test_redact_hygiene.py` (6 tests) against the hub-backed replacement with only the
     import swapped; all 6 assertions must pass before the app-local `weatherbot/_redact.py` is
     deleted.
   - **(b) The MATCH-03 duplicate-`spec.name` sweep** — MATCH-03 turns a previously-silent
     overwrite into a `ValueError` at registration; WeatherBot's command specs must be swept for
     duplicate names before the repin lands.
   - **Why they stay separate:** one bundled repin would conflate the two failure causes — a
     failure during the combined repin would not tell you whether the parity suite or the
     duplicate-name sweep is the culprit. Both checks must go green independently first.
4. **The SURF-02 blast-radius note:** narrowing `on_online` (`Callable[..., None] | None` →
   `Callable[[HealthResult], None] | None`) is a public hub-surface change. The only live
   consumer's handler already conforms — `WeatherBot/weatherbot/scheduler/wiring.py:442`'s
   `_on_online(_result)` is already single-positional, and its tests already pass single-argument
   lambdas — so nothing breaks today, but the repin should confirm this explicitly rather than
   assume it.
5. **The Phase-6 carry-forward** (already recorded in `STATE.md`): the WeatherBot parity suite
   needs a **signature-level test update**, not merely an import swap, because the promoted
   `RedactingWriter`'s constructor differs from the app-local `_LiveStderr` it replaces. Repinning
   without updating the parity test's construction call will fail for a reason unrelated to
   redaction correctness.
6. **The permanent scope boundary:** `weatherbot/weather/client.py`'s domain-specific redacted
   re-raise stays app-local forever — it is domain logic, not a generic backstop — and must be
   confirmed *untouched* by the swap.

No version bump, tag, repin, `uv sync`, or deploy was performed by this plan or any plan in
Phase 7.

## Task Commits

Each task was committed atomically:

1. **Task 1: GATE-02 audit (no source/test changes — audit only)** — recorded in this SUMMARY;
   audit produced no file diff outside this document, so its evidence is captured here rather than
   in a separate commit (per the plan's own instruction: "Do not write any source or test file in
   this task — it is an audit").
2. **Task 2: File the deferred backlog entry + surface the close-out** — committed together with
   this SUMMARY (see the final metadata commit below for the hash).

## Files Created/Modified

- `.planning/backlog/ADOPT-STATIC-TYPE-CHECKER.md` — new pickup-ready backlog entry (Task 2A).
- `.planning/phases/07-v0-1-2-debt-paydown/07-07-SUMMARY.md` — this document (Task 1 audit +
  Task 2 backlog/close-out record).

## Decisions Made

- Used `git worktree add --detach` against a scratchpad path (never `git stash`, per the
  destructive-git-prohibition) to verify genuine RED-ness at each RED commit's tree, then removed
  the worktree (`git worktree remove --force`) and confirmed the main working tree's HEAD and
  `git status` were unaffected throughout.
- Recorded the `-k` filter mismatch between `07-VALIDATION.md`'s literal HYG-02 string
  (`label_kwarg`) and the actual shipped test names, and used a working filter (`structured_kwarg`)
  instead of silently "passing" a command that would have selected zero tests — a stale validation
  doc string is exactly the class of error this phase's own DOCS-02 work targets, so this task
  did not repeat it.
- Independently re-derived the probe-rollup arithmetic from each prior plan's own equality-check
  line rather than trusting the phase-rollup table's restated total, per the acceptance criteria's
  instruction to verify rather than copy.

## Deviations from Plan

None — plan executed exactly as written. The `-k` filter substitution for HYG-02 (above) is
recorded as a decision, not a deviation from the plan's action text: the plan instructed deriving
ancestry from git trees and running "the requirement's `-k`-filtered command from `07-VALIDATION.md`'s
test map," and the validation doc's literal string did not select the intended tests, so a working
equivalent filter was used and the discrepancy is recorded above rather than silently masked.

## Issues Encountered

None beyond the `-k` filter mismatch noted above, which self-resolved by using a working filter
string and documenting the discrepancy.

## User Setup Required

None — no external service configuration required. The human-gated close-out items above are
**surfaced for confirmation**, not something this plan can or does execute.

## Next Phase Readiness

Phase 7 is complete. GATE-02 holds: the full suite (184 passed, zero warnings) plus the standing
import-hygiene gate (10 passed) and the standing doc-drift gate (5 passed) are green, and every
behavioral requirement's RED-first ancestry is proven from git — with LIFE-05's no-behavioral-change
exemption recorded, not hidden. All nine Phase 7 requirements (MATCH-03, LIFE-05, SURF-02, DISC-07,
DISC-08, HYG-02, HYG-03, DOCS-02, DOCS-03) are closed or explicitly decided. GATE-02 itself stays
**unchecked** in `REQUIREMENTS.md` — it is milestone-standing per `ECOSYSTEM.md`/the ROADMAP's
existing convention (same treatment GATE-01 received in v0.1.2) and this is Phase 7 of 3 in
Milestone v0.2.0; Track A (Phases 5–6) is already complete, so with this plan's close all of
Milestone v0.2.0's phase work is done. The human-gated close-out above is ready for confirmation
whenever the human elects to act on it — no part of it was performed by this plan.

---
*Phase: 07-v0-1-2-debt-paydown*
*Completed: 2026-08-04*
