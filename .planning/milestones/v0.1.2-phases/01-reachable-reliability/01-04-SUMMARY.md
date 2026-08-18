---
phase: 01-reachable-reliability
plan: 04
subsystem: testing
tags: [merge, red-first-audit, gate-01, pytest, import-hygiene]

# Dependency graph
requires:
  - phase: 01-reachable-reliability (Plans 01-03)
    provides: "Both fixes (RELY-01, LIFE-01) green on the phase branch, plus the hub's first test substrate"
provides:
  - "01-VALIDATION.md signed off (nyquist_compliant: true, wave_0_complete: true, status: complete)"
  - "phase-01-reachable-reliability merged into main via --no-ff, RED-first ancestry preserved"
  - "Full suite (23 passed) and GATE-01 import-hygiene gate (8 passed) re-proven green ON main post-merge"
affects: ["02-latent-runtime-robustness"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mechanical RED-first audit: git merge-base --is-ancestor + single-file-touched check on the test-adding commit, run as a phase-closing gate rather than trusted from plan-level narrative"
    - "--no-ff merge to main preserves a phase's RED-first four-commit structure as a visible, auditable unit instead of flattening it"

key-files:
  created: []
  modified:
    - .planning/phases/01-reachable-reliability/01-VALIDATION.md

key-decisions:
  - "Signed off 01-VALIDATION.md: all Per-Task Verification Map rows bound to real plan/task IDs, all four under-sampling risks refuted by named assertions, nyquist_compliant: true"
  - "Merged with --no-ff per D-14/T-1-07 — RED-first ancestry (e7c959d->f6e4fb2, 0f0a9ad->5273c13) stays visible on main, not squashed"
  - "GATE-01 left unchecked in REQUIREMENTS.md — it is milestone-standing (spans all 4 phases) and is only marked complete once it has held green across the whole milestone, per Plan 01's own traceability note"
  - "No version bump, no v0.1.2 tag, no [tool.uv.sources] repin, no uv sync, no deploy — all human-gated per ECOSYSTEM.md §3, confirmed by direct inspection post-merge"

requirements-completed: [RELY-01, LIFE-01]

coverage:
  - id: D1
    description: "01-VALIDATION.md signed off with every Per-Task Verification Map row bound to a real plan/task ID and every under-sampling risk refuted by a named assertion"
    requirement: "GATE-01"
    verification:
      - kind: unit
        ref: "grep -q 'nyquist_compliant: true' .planning/phases/01-reachable-reliability/01-VALIDATION.md"
        status: pass
    human_judgment: false
  - id: D2
    description: "RED-first git ancestry mechanically proven for both fixes (test-adding commit is a strict, single-file-touching ancestor of the fix commit)"
    requirement: "RELY-01"
    verification:
      - kind: unit
        ref: "git merge-base --is-ancestor e7c959d f6e4fb2 (RELY-01); git merge-base --is-ancestor 0f0a9ad 5273c13 (LIFE-01)"
        status: pass
    human_judgment: false
  - id: D3
    description: "--no-ff merge of phase-01-reachable-reliability into main, authorized at the Task 2 checkpoint; full suite and GATE-01 re-proven green ON main post-merge"
    requirement: "LIFE-01"
    verification:
      - kind: unit
        ref: "uv run pytest (23 passed on main); uv run pytest tests/test_import_hygiene.py (8 passed on main)"
        status: pass
    human_judgment: false
  - id: D4
    description: "No version bump, tag, repin, uv sync, or deploy performed by this plan"
    verification:
      - kind: unit
        ref: "git show main:pyproject.toml | grep 'version = \"0.1.1\"'; git tag --list 'v0.1.2' (empty)"
        status: pass
    human_judgment: false

duration: ~25min
completed: 2026-07-22
status: complete
---

# Phase 1 Plan 4: Audit, Sign-Off, and Merge Summary

**Mechanically audited RED-first git ancestry for both hub fixes, signed off `01-VALIDATION.md`, and merged `phase-01-reachable-reliability` into `main` with `--no-ff` after explicit developer authorization — full suite (23 passed) and the GATE-01 import-hygiene gate (8 passed) re-proven green on `main` post-merge.**

## Performance

- **Duration:** ~25 min (across two sessions — Task 1 audit, then a checkpoint pause for Task 2, then this continuation for Task 3)
- **Started:** 2026-07-22
- **Completed:** 2026-07-22
- **Tasks:** 3/3 (Task 2 was a human-authorization checkpoint, no file changes)
- **Files modified:** 1 (`01-VALIDATION.md`, signed off in Task 1)

## Accomplishments

- **Task 1 (prior session):** Ran the full gate set on the phase branch (`uv run pytest` — 23
  passed; `uv run pytest tests/test_import_hygiene.py` — 8 passed; `uv run ruff check` — 4
  pre-existing errors outside this phase's touched files). Mechanically proved RED-first ancestry
  for both fixes via `git merge-base --is-ancestor` plus a single-file-touched check on each
  test-adding commit. Confirmed zero dependency drift (`pyproject.toml`/`uv.lock` byte-identical
  between merge base and branch tip). Signed off `01-VALIDATION.md`: all Per-Task Verification Map
  rows bound to real plan/task IDs, all four under-sampling risks refuted by named assertions,
  `nyquist_compliant: true`.
- **Task 2 (prior session):** Presented the merge-authorization checkpoint — both production diffs,
  the branch commit list, the Task 1 gate results, and the consumer-impact note (broadening
  `is_transient` is a silent retry-behavior change for every consumer at repin). Developer responded
  **"approved."**
- **Task 3 (this session, continuation):** Verified pre-merge state matched the continuation
  briefing exactly (HEAD `3fd6fc5` on the phase branch, `main` at `6baf992`, the same three
  pre-existing dirty files). Merged `phase-01-reachable-reliability` into `main` with `--no-ff`
  (merge commit `81df616`), preserving the four-commit RED-first structure as a visible unit in
  history. Re-ran the full suite and the GATE-01 import-hygiene gate ON `main` post-merge — both
  green, proving D-14's "main only ever receives green commits" rather than assuming the branch
  result transfers. Confirmed both fixes are live on `main` by direct execution. Confirmed no
  version bump, no `v0.1.2` tag, no repin, no `uv sync`, and no deploy occurred. Confirmed the
  phase branch is preserved (not deleted) and the three pre-existing uncommitted modifications
  (`.planning/config.json`, `ECOSYSTEM.md`, `uv.lock`) remain unstaged and untouched.

## Task Commits

1. **Task 1: Audit phase gates, RED-first evidence, false-green refutations** — `3fd6fc5` (docs)
   — signed off `01-VALIDATION.md`
2. **Task 2: Merge-authorization checkpoint** — no commit (a human decision gate; response:
   "approved")
3. **Task 3: Merge to main and hand deferred obligations forward** — `81df616` (merge, `--no-ff`)
   — merges the phase branch into `main`; this SUMMARY and the final metadata commit follow

## Files Created/Modified

- `.planning/phases/01-reachable-reliability/01-VALIDATION.md` — Signed off in Task 1: Per-Task
  Verification Map bound to real IDs, under-sampling risks refuted, `nyquist_compliant: true`.
- No production files modified by Plan 04 — RELY-01 and LIFE-01's actual code changes landed in
  Plans 02 and 03 respectively; this plan audits, authorizes, and merges.

## Decisions Made

- Followed D-14 exactly: `main` received the phase's commits only after the full suite and
  GATE-01 were green on the branch, and again re-proven green on `main` after the merge — not
  assumed to transfer.
- Used `--no-ff` per T-1-07's mitigation: a fast-forward would have flattened the RED-first
  four-commit structure (`e7c959d`→`f6e4fb2`, `0f0a9ad`→`5273c13`) that is this phase's central,
  otherwise-unfalsifiable evidence (T-1-06).
- Left `GATE-01` unchecked in `.planning/REQUIREMENTS.md`. It is milestone-standing — spans all
  4 phases of v0.1.2 — and Plan 01's own traceability note is explicit that it should be marked
  complete only once it has held green across the *whole* milestone, not after any single phase.
  Marking it complete here would misrepresent a milestone-level gate as phase-scoped.
- Did not delete `phase-01-reachable-reliability` — it remains the RED-first evidence, preserved
  per the plan's explicit instruction.
- Performed no version bump, tag, repin, `uv sync`, or deploy — all four remain human-gated per
  `ECOSYSTEM.md` §3 and fire only after Phase 4, confirmed by direct post-merge inspection
  (`pyproject.toml` still `0.1.1`; `git tag --list 'v0.1.2'` empty).

## Deviations from Plan

None — Task 3 executed exactly as the plan specified: `--no-ff` merge, post-merge suite +
GATE-01 re-run, phase branch preserved, no milestone-level action taken.

### Process Finding (carried forward per continuation-briefing instruction 6 — not this plan's own deviation, but must not be buried)

**The Plan 01-02 executor used `git stash` / `git stash pop` — a prohibited destructive-git
operation** (documented in `01-02-SUMMARY.md`'s own "Process note" section). While investigating
the repo-wide `uv run ruff check` acceptance criterion, the executor stashed working-tree state to
compare pre-fix vs. post-fix `ruff` output. The subsequent `stash pop` failed because a
pre-existing, unrelated `uv.lock` modification conflicted with the stash contents — exactly the
failure mode this project's `destructive_git_prohibition` rule exists to prevent. No commits or
committed history were affected; the stash only ever held uncommitted working-tree changes. The
executor self-caught the failure and recovered per-file via `git checkout stash@{0} -- <path>` for
each affected file (the `retry.py` fix, plus the three pre-existing unrelated uncommitted
modifications), verified byte-for-byte against the stash diff, then dropped the stash. A first
commit attempt briefly bundled three unrelated dirty files (picked up as already-staged by the
recovery checkout) alongside `retry.py`; this was caught immediately by inspecting `git show
--name-only --format= HEAD`, corrected via `git reset --soft HEAD~1` + `git restore --staged` on
the three unrelated files, and recommitted with `retry.py` alone. This orchestrator (Plan 04, Task
1) independently verified the final state was clean: the stash list was empty, no conflict markers
remained anywhere in the tree, and both `f6e4fb2` (fix) and `e7c959d` (test) each touch exactly
one file. **Recorded here as a process finding for future phases, not re-litigated or re-fixed** —
the recovery was already complete and verified before this plan started.

## Issues Encountered

None. Pre-merge state matched the continuation briefing exactly; the merge, both re-run gates, and
all negative assertions (no version bump / tag / repin / sync / deploy) passed on the first attempt.

**Requirements traceability:** `RELY-01` and `LIFE-01` were already marked complete in
`.planning/REQUIREMENTS.md` by Plans 02 and 03 respectively (their fixes actually landed green).
This plan does not re-mark them. `GATE-01` remains unchecked — see "Decisions Made" above.

## User Setup Required

None for this plan's own scope. See "Deferred / Carried-Forward Obligations" below for what
requires human action *later*, at the milestone-level close-out after Phase 4.

## Deferred / Carried-Forward Obligations

Per the plan's `<output>` instruction and the continuation briefing's instruction 6, every item
below is named with its reason and owner so none of it evaporates at phase close:

1. **`.planning/codebase/TESTING.md` is now stale.** Line ~36 ("No `conftest.py`") and line ~142
   ("No `@pytest.fixture` decorators in use") are contradicted by this phase's D-09/D-10 as of the
   merge just performed. Line ~239 ("No `pytest.raises()` currently") was *already* stale before
   this phase — `tests/test_import_hygiene.py:243` has used `pytest.raises` since before Phase 1
   started. Refreshing this document is explicitly deferred housekeeping per `01-CONTEXT.md`'s
   "Deferred Ideas" section, not a gap in this phase — but it is now overdue, and Phases 2-4 will
   inherit two false conventions from it (no conftest, no fixtures) if it is not refreshed before
   they start reading it for guidance. **Owner: whoever picks up the next housekeeping pass, or the
   Phase 2 planner if it reads `TESTING.md` for conventions before that pass happens.**

2. **`httpx.ProxyError` as transient — deferred, reason intact.** Neither current transport
   (OpenWeather via httpx directly, Discord via `discord.py`) proxies, so treating `ProxyError` as
   transient today would be unreachable code with no honest RED-first test behind it. **Owner:
   whoever ships the first consumer that runs behind a proxy and has a real reproduction** — it is
   a one-line change at that point, per `01-CONTEXT.md`'s "Deferred Ideas."

3. **An injectable / per-consumer-configurable transient classifier — deferred, reason intact.**
   Raised implicitly by D-02's observation that "the hub cannot see its consumers' failure modes."
   This is a new capability, not a fix, and belongs in its own phase, gated by the repo's
   rule-of-three promotion discipline — only once a second consumer actually wants a different
   transient boundary than the first. **Owner: a future phase, not this milestone's remaining
   phases unless a second consumer's need materializes.**

4. **The milestone-level human-gated close-out is NOT started by this plan.** After Phase 4:
   `pyproject.toml` version bump `0.1.1` → `0.1.2`, cut tag `v0.1.2`, repin WeatherBot's
   `[tool.uv.sources]` from `v0.1.1` to `v0.1.2`, `uv sync --frozen`, then re-run WeatherBot's own
   suite against the repinned hub. **Carry the RELY-01 consumer-impact note into that close-out
   explicitly:** broadening `is_transient` is a silent behavior change for WeatherBot at repin — a
   `RemoteProtocolError`/`WriteError`/`CloseError` that previously failed fast after 1 attempt will,
   after the repin, retry across the full two-burst schedule (up to roughly 75 minutes) before
   exhaustion. Nothing in this hub triggers the change; it lands only when WeatherBot cuts the
   repin. **Owner: the human-gated close-out step after Phase 4, per `ECOSYSTEM.md` §3 and
   `01-02-SUMMARY.md`'s own "Silent-Behavior-Change-at-Repin Note."**

5. **The unresolved LIFE-01 edge-probe item (consumer-side concurrent-signal race) — restated, not
   resolved.** Category `unclassified` from the planner's deterministic edge probe: a race between
   this guard's boolean return (`is_running_process`) and the consumer's actual subsequent SIGHUP
   delivery, which happens entirely in consumer-side code (WeatherBot's reload sender), outside this
   hub repo's Architectural Responsibility Map. No test in this repo can assert it without
   replicating consumer-side signal-delivery logic here, which would violate the same reasoning
   (D-18) that keeps `fire_slot`'s reason-picking logic out of the hub's own tests. Restated per
   `01-03-SUMMARY.md`'s own carry-forward instruction so it survives into phase verification as a
   flagged assumption rather than a silent pass. **Owner: whoever owns WeatherBot's reload/signal
   delivery path, if this race is ever empirically reproduced.**

6. **What the new test substrate hands Phase 2:** `tests/conftest.py` with its two D-10-bounded
   fixtures (`fake_stop_event`, `cmdline_bytes`), the flat `tests/test_<module>.py` naming
   convention (D-08), and the RED-first two-commit-per-fix discipline (D-13) — commit the
   regression test alone against pre-fix source, confirm it fails, then commit the fix as its
   direct child — that the remaining 13 hardening findings across Phases 2-4 inherit as the
   established pattern. Phase 2's planner should read `tests/test_retry.py` and
   `tests/test_identity.py` as the reference shape before writing new regression tests, and should
   NOT add speculative fixtures to `conftest.py` beyond what a real second caller in Phase 2
   actually needs (D-10's minimal-bound discipline).

## GATE-01 Status (milestone-standing — reported honestly, not closed early)

`GATE-01` ("the full suite plus the standing import-hygiene gates stay green across every phase")
held green throughout Phase 1: on the phase branch at every task boundary (Plans 01-03), at the
Task 1 audit in this plan, and again on `main` immediately post-merge (`uv run pytest
tests/test_import_hygiene.py` — 8 passed). **It is NOT being marked complete in
`.planning/REQUIREMENTS.md` by this plan** — GATE-01 spans all 4 phases of the v0.1.2 milestone and
is only truthfully "complete" once it has held green across the entire milestone, not after one
phase. Phase 1's contribution to that milestone-spanning proof is: zero regressions to the one-way
dependency, the grimp layering graph, or the no-domain-noun litmus across both fixes and the new
test substrate.

## Next Phase Readiness

- `main` holds both fixes (RELY-01, LIFE-01) and the hub's first test substrate
  (`tests/conftest.py`, `tests/test_retry.py`, `tests/test_identity.py`), all proven green by a
  post-merge run, not merely inherited from the branch.
- `phase-01-reachable-reliability` remains as a preserved branch — the RED-first evidence is
  intact and auditable at any future point via the same `git merge-base --is-ancestor` mechanism
  used in Task 1.
- Phase 2 ("Latent runtime robustness" — CFG-01, DISC-01 through DISC-04) can branch from `main`
  with a clean, green baseline and should follow the RED-first two-commit-per-fix convention this
  phase established.
- The six deferred/carried-forward obligations above are not blockers for Phase 2 starting, but
  the stale `TESTING.md` (item 1) should be refreshed before Phase 2's planner reads it for
  conventions, to avoid inheriting the wrong ones.
- No blockers for Phase 2.

---
*Phase: 01-reachable-reliability*
*Completed: 2026-07-22*

## Self-Check: PASSED

- FOUND: .planning/phases/01-reachable-reliability/01-VALIDATION.md
- FOUND: 3fd6fc5 (git log --oneline --all)
- FOUND: 81df616 (git log --oneline --all)
- FOUND: e7c959d, f6e4fb2, 0f0a9ad, 5273c13 (git log --oneline --all)
- CONFIRMED: `git rev-parse --abbrev-ref HEAD` == main
- CONFIRMED: `git rev-parse --verify phase-01-reachable-reliability` resolves (branch preserved)
- CONFIRMED: `uv run pytest` on main == 23 passed
- CONFIRMED: `uv run pytest tests/test_import_hygiene.py` on main == 8 passed
- CONFIRMED: pyproject.toml on main still reads version = "0.1.1"
- CONFIRMED: `git tag --list 'v0.1.2'` is empty
