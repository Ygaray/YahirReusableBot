---
phase: 05-redaction-core-pattern-registration
plan: 03
subsystem: infra
tags: [redaction, testing, import-hygiene, gate-audit, security]

# Dependency graph
requires:
  - phase: 05-redaction-core-pattern-registration (plan 01)
    provides: "RedactionPattern frozen dataclass, redact_secrets, redact/ pure-leaf subpackage"
  - phase: 05-redaction-core-pattern-registration (plan 02)
    provides: "register_patterns, ReDoS vetting, redact/registry.py"
provides:
  - "redact_scanned litmus coverage guard inside test_litmus_clean — redact/ can never silently drop out of AST-signature coverage after a future relocation"
  - "GATE-02 RED-first ancestry audit for REDACT-01/02/03/06, proven from git trees (not asserted in prose)"
  - "Recorded WeatherBot parity-test plan for the human-gated close-out, with the Phase-5-core vs Phase-6-seam split empirically verified against the actual WeatherBot test file"
  - "Recorded D-52 wording adjustment: redact_secrets is locked as strict str -> str; the non-str-tolerance clause is Phase 6's"
affects: [phase-6-redaction-seam, phase-7-debt-paydown, milestone-close-out]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Path-scoped rglob coverage guard: one guard per subpackage inside test_litmus_clean, each asserting its own filename set is a subset of its own subdirectory's scan — matches the three pre-existing lifecycle/registry/discord guards exactly, extended (not replaced) for redact/"

key-files:
  created: []
  modified:
    - tests/test_import_hygiene.py

key-decisions:
  - "The redact_scanned guard is an ADDITION for convention consistency, not a fix — the standing gate's rglob scan already auto-covers redact/ today (confirmed green, unedited, before the edit: 105 passed, 8 import-hygiene passed, ruff clean). It exists so a future refactor that relocates redact/ cannot silently drop it from litmus coverage, matching why the lifecycle/registry/discord guards exist."
  - "Verified the six WeatherBot parity-gate assertion names against the actual source at /home/yahir/Projects/WeatherBot/tests/test_redact_hygiene.py rather than trusting 05-VALIDATION.md's list: 4 of 6 exercise Phase-5-core-equivalent behavior only (redact_appid / client.py's own re-raise logic), 2 of 6 (test_discord_on_message_does_not_dump_key, test_livestderr_write_tolerates_and_scrubs_bytes) depend on the _LiveStderr/structlog sink backstop that is Phase 6's deliverable, so the parity gate cannot fully re-pass until Phase 6 ships."
  - "D-52's non-str clause is restated as a locked contract, not a Phase-5 gap: redact_secrets is strict str -> str by design; Phase 6 owns tolerance via the sink wrapper, matching the proven _LiveStderr.write design."

patterns-established: []

requirements-completed: [REDACT-01, REDACT-02, REDACT-03, REDACT-06]

coverage:
  - id: D1
    description: "The standing import-hygiene gate confirmed green UNEDITED against the new redact/ tree before any change was made (CONTEXT.md's no-edit claim empirically confirmed, not assumed)"
    verification:
      - kind: unit
        ref: "uv run pytest tests/test_import_hygiene.py -q (8 passed, pre-edit)"
        status: pass
    human_judgment: false
  - id: D2
    description: "redact_scanned coverage guard added inside test_litmus_clean, path-scoped to redact/, asserting {core.py, registry.py} subset — matches the lifecycle/registry/discord guard shape exactly"
    requirement: "REDACT-01"
    verification:
      - kind: unit
        ref: "tests/test_import_hygiene.py#test_litmus_clean (redact_scanned block)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The new guard is proven non-vacuous — the same subset assertion fails against a directory lacking those filenames (yahir_reusable_bot/reliability)"
    verification:
      - kind: unit
        ref: "uv run python -c \"...assert {'core.py','registry.py'}<=ok; assert not {'core.py','registry.py'}<=bad\""
        status: pass
    human_judgment: false
  - id: D4
    description: "GATE-02 RED-first ancestry proven from git trees for both requirement pairs: 05-01 pair (753f3d5 -> 104cdbe) covers REDACT-01/REDACT-06/REDACT-02-type-half; 05-02 pair (751cda9 -> cad067e) covers REDACT-02-registration-half/REDACT-03"
    requirement: "REDACT-02"
    verification:
      - kind: other
        ref: "git rev-parse adjacency + git ls-tree RED-ness proof + git show commit-purity check (see Section B below)"
        status: pass
    human_judgment: false
  - id: D5
    description: "All three standing gates green and recorded post-edit: full suite (105 passed), import-hygiene (8 passed), ruff clean, build command succeeds"
    verification:
      - kind: unit
        ref: "uv run pytest -q (105 passed, 1.88s)"
        status: pass
      - kind: unit
        ref: "uv run pytest tests/test_import_hygiene.py -q (8 passed)"
        status: pass
      - kind: other
        ref: "uv run ruff check"
        status: pass
      - kind: other
        ref: "uv run python -c 'import yahir_reusable_bot'"
        status: pass
    human_judgment: false
  - id: D6
    description: "WeatherBot parity-test plan and client.py scope boundary recorded for the human-gated close-out, with the Phase-5-core vs Phase-6-seam split verified against actual WeatherBot source"
    verification: []
    human_judgment: true
    rationale: "The parity gate itself is a cross-repo, human-gated repin deliverable (ECOSYSTEM.md §3) — this plan records the plan, it does not and must not execute the repin or run WeatherBot's test suite as part of this repo's automated gate."

# Metrics
duration: ~10min
completed: 2026-07-29
status: complete
---

# Phase 5 Plan 3: Litmus coverage guard + phase gate audit Summary

**Added the `redact/` litmus coverage guard (confirming the standing gate's no-edit claim empirically first), then proved GATE-02's RED-first ancestry from git trees for all four Phase-5 requirements and recorded the human-gated close-out obligations.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-07-29T18:35:00Z (approx.)
- **Completed:** 2026-07-29T18:45:00Z (approx.)
- **Tasks:** 2
- **Files modified:** 2 (`tests/test_import_hygiene.py`, this SUMMARY)

## Accomplishments

- **Pre-edit confirmation (Task 1, Step 1):** ran `uv run pytest tests/test_import_hygiene.py -q`
  against the gate file exactly as committed by plan 05-02 — **8 passed**, UNEDITED. This
  empirically confirms 05-CONTEXT.md's claim that adding `redact/` requires no edit to the
  standing gate: the gate's `rglob`/`pkgutil.walk_packages` scans auto-cover any new subpackage
  today. Also confirmed at the same moment: `uv run pytest -q` → 105 passed; `uv run ruff check` →
  clean.
- **`redact_scanned` coverage guard added (Task 1, Step 2):** a fourth path-scoped guard inside
  `test_litmus_clean`, in the exact shape of the three existing lifecycle/registry/discord guards
  — `{path.name for path in (_MODULE_ROOT / "redact").rglob("*.py")}` asserted to be a superset of
  `{"core.py", "registry.py"}`, with the established "…coverage gap…" assertion-message form. This
  is explicitly an ADDITION for convention consistency (a one-line comment says so above the
  block), not a fix for a failing gate — a future refactor that relocates `redact/` will now fail
  loudly instead of silently dropping out of litmus coverage.
- **GATE-02 ancestry audit (Task 2):** both RED/GREEN pairs proven adjacent and RED-then-GREEN from
  git trees alone (Section B below); all four requirement IDs mapped to their pair.
- **Five-criteria walk (Task 2):** ROADMAP Phase 5's five success criteria each cited against a
  specific test/command (Section C below), including the D-52 wording-adjustment statement.
- **Human-gated close-out record (Task 2):** the six-assertion WeatherBot parity plan and the
  `client.py` scope boundary copied forward from `05-VALIDATION.md`, with the Phase-5-core vs.
  Phase-6-seam split verified directly against `/home/yahir/Projects/WeatherBot/tests/test_redact_hygiene.py`
  rather than left unexamined (Section D below).
- **Explicitly NOT done (Task 2):** no version bump, tag, repin, `uv sync`, or deploy; no Phase-6
  artifact created (Section E below).

## Task Commits

Each task was committed atomically:

1. **Task 1: Confirm the no-edit claim, then add the `redact/` litmus coverage guard** -
   `6cfba0e` (test) — `tests/test_import_hygiene.py` only, 10 insertions, 0 deletions.
2. **Task 2: Phase gate audit — GATE-02 ancestry proof, standing gates, close-out record** -
   (this commit) — `.planning/phases/05-redaction-core-pattern-registration/05-03-SUMMARY.md` only;
   no source, no test changed.

## Files Created/Modified

- `tests/test_import_hygiene.py` - extended `test_litmus_clean` with the `redact_scanned` guard
  (10 lines added, 0 deleted, single file in the commit — surgical per the plan's constraint)
- `.planning/phases/05-redaction-core-pattern-registration/05-03-SUMMARY.md` - this phase gate
  audit record

## Section A — Standing gates (post-edit)

| Gate | Command | Result |
|---|---|---|
| Full suite | `uv run pytest -q` | **105 passed, 1 warning in 1.88s** (delta: +25 from the 80-test milestone baseline recorded in PROJECT.md) |
| Import hygiene | `uv run pytest tests/test_import_hygiene.py -q` | **8 passed in 0.28s** |
| Lint | `uv run ruff check` | **All checks passed!** |
| Build command | `uv run python -c 'import yahir_reusable_bot'` | exits 0, no output — import succeeds |

Pre-edit confirmation (recorded separately, see Accomplishments): `uv run pytest tests/test_import_hygiene.py -q` passed **8 passed** against the gate file BEFORE Task 1's edit — the no-edit claim is empirically confirmed, not assumed.

## Section B — GATE-02 RED-first ancestry proof

Resolved with `git rev-parse` (no checkout performed):

| Plan | RED SHA | GREEN SHA | Adjacency (`GREEN^ == RED`) |
|---|---|---|---|
| 05-01 | `753f3d5` (`753f3d5ed7a0792d980644aa3bf58ec31b0da1a5`) | `104cdbe` (`104cdbeb43a166a5f394ad552bb4a8ea08d73edd`) | **Confirmed** — `git rev-parse 104cdbe^` == `753f3d5ed7a0792d980644aa3bf58ec31b0da1a5` |
| 05-02 | `751cda9` (`751cda9142c010244f08eb5d88865f3ea617cced`) | `cad067e` (`cad067edd7c2755b0827dd9c002df00023651fc9`) | **Confirmed** — `git rev-parse cad067e^` == `751cda9142c010244f08eb5d88865f3ea617cced` |

RED-ness proven from the tree (`git ls-tree -r <RED_SHA> --name-only`), not asserted:

- **05-01 RED (`753f3d5`)**: contains `tests/test_redact_core.py` (count 1); does NOT contain
  `yahir_reusable_bot/redact/core.py` (count 0) — this commit's tree could not have collected, let
  alone passed.
- **05-02 RED (`751cda9`)**: contains `tests/test_redact_registry.py` (count 1); does NOT contain
  `yahir_reusable_bot/redact/registry.py` (count 0) — same proof shape.

Commit purity (`git show --name-only --pretty=format:`):

- `753f3d5` touches only `tests/test_redact_core.py` — 0 paths outside `tests/`.
- `104cdbe` touches only `yahir_reusable_bot/redact/__init__.py`,
  `yahir_reusable_bot/redact/core.py` — 0 paths outside `yahir_reusable_bot/`.
- `751cda9` touches only `tests/test_redact_registry.py` — 0 paths outside `tests/`.
- `cad067e` touches only `yahir_reusable_bot/redact/__init__.py`,
  `yahir_reusable_bot/redact/registry.py` — 0 paths outside `yahir_reusable_bot/`.

**Requirement-to-pair mapping (recorded so a later audit does not re-derive it):**

| Requirement | Covered by pair | Notes |
|---|---|---|
| REDACT-01 | 05-01 (`753f3d5` -> `104cdbe`) | `redact_secrets` boundary matrix, idempotence, zero-pattern no-op |
| REDACT-06 | 05-01 (`753f3d5` -> `104cdbe`) | `RedactionPattern.literal`, repr elision, empty/blank rejection |
| REDACT-02 (frozen-type half) | 05-01 (`753f3d5` -> `104cdbe`) | `RedactionPattern` frozen-dataclass behavior |
| REDACT-02 (registration half) | 05-02 (`751cda9` -> `cad067e`) | `register_patterns` immutability, order-preservation, no module-level state |
| REDACT-03 | 05-02 (`751cda9` -> `cad067e`) | Nested-quantifier structural rejection, alternation-shape timing-probe rejection, bounded termination, `skip_redos_check` opt-out |

## Section C — Success-criteria walk (ROADMAP Phase 5)

1. **`redact_secrets(text, patterns)` masks the secret while diagnostics survive, is idempotent,
   and returns non-`str` input without raising mid-exception-handling.** Masking/diagnostics/
   idempotence: `tests/test_redact_core.py::test_redact_helper_boundaries`,
   `::test_redact_secrets_idempotent`. **D-52 wording adjustment, stated loudly**: the "returns
   non-`str` input without raising mid-exception-handling" clause is **deliberately relocated to
   REDACT-04 / Phase 6's seam**, matching the proven `_LiveStderr.write` design — `redact_secrets`
   is strict `str -> str` by design (no `isinstance` guard, no `try/except`, no `re.compile` call
   anywhere in its body, per 05-01-SUMMARY.md D5). Phase-5 verification **must not report a gap**
   because of this: it is the LOCKED contract, and Phase 6 owns the tolerance assertion via
   `test_livestderr_write_tolerates_and_scrubs_bytes` (see Section D).
2. **Patterns compiled once at registration, frozen into an immutable collection; identical
   results in isolation and full-suite order.** `tests/test_redact_registry.py::test_register_patterns_returns_immutable_collection`,
   `::test_register_patterns_holds_no_module_level_state`, plus the module-level-mutable-container
   scan in 05-02-SUMMARY.md D11. `uv run pytest -q` (full-suite order) and
   `uv run pytest tests/test_redact_registry.py -q` (isolation) both green at 105/12 passed
   respectively.
3. **A nested/overlapping-quantifier pattern that blows a wall-clock budget is rejected at
   registration, never silently accepted.** `tests/test_redact_registry.py::test_register_patterns_rejects_catastrophic_pattern`
   (structural check) and `::test_register_patterns_rejects_catastrophic_pattern_the_structural_check_misses`
   (alternation shape the structural check misses, caught by the escalating wall-clock probe alone
   — proving the probe is independently load-bearing, not redundant).
4. **A registered literal secret is blocked wherever it appears, including inside a `repr()`.**
   `tests/test_redact_core.py::test_literal_matches_inside_repr`.
5. **Every `def`/`class`/param/annotation name under `redact/` passes the AST litmus, and
   `redact/` imports no sibling subpackage (pure leaf).** `tests/test_import_hygiene.py::test_litmus_clean`
   (now carrying the `redact_scanned` guard added in Task 1) plus the grimp pure-leaf check
   recorded in both 05-01-SUMMARY.md and 05-02-SUMMARY.md D5/D13.

## Section D — Human-gated close-out record (STATE.md Todo)

Copied forward from `05-VALIDATION.md` § "Manual-Only Verifications", with the Phase-5-core vs.
Phase-6-seam split now **verified against the actual source** at
`/home/yahir/Projects/WeatherBot/tests/test_redact_hygiene.py` (read directly, not left
unexamined):

**The six assertions that must re-pass unmodified against the hub-backed replacement (import
swapped only):**

| Test | Exercises |
|---|---|
| `test_redact_helper_boundaries` | Phase-5 core only — calls `redact_appid`/`redact_secrets` directly |
| `test_onecall_failure_redacts_key_and_keeps_status` | Phase-5 core only — `client.py`'s own redacted re-raise (checks `str(exc)` and `traceback.format_exception` directly, not through structlog) |
| `test_geocode_failure_redacts_key` | Phase-5 core only — same `client.py` re-raise logic |
| `test_discord_on_message_does_not_dump_key` | **Phase-6 seam** — its part (b) drives `structlog.get_logger(...).error(...)` and asserts the `_LiveStderr` backstop scrubs a raw, un-redacted line; this cannot re-pass until Phase 6's sink/processor is wired |
| `test_reraised_exception_request_carries_no_key` | Phase-5 core only — the `client.py` scope-boundary test: asserts no key on `exc.request`/`exc.response.request` attributes |
| `test_livestderr_write_tolerates_and_scrubs_bytes` | **Phase-6 seam** — explicitly the non-str-tolerant `_LiveStderr.write` backstop that D-52 relocates to Phase 6 |

**Conclusion:** 4 of 6 assertions exercise Phase-5-core-equivalent behavior and could in principle
be re-run once the hub import is swapped into `client.py`/`redact_appid`'s call sites; the other 2
depend on Phase 6's sink/processor seam and **cannot fully re-pass until Phase 6 ships** — so the
repin step must not treat a partial (4/6) green as sufficient for a full parity claim.

**`client.py` scope boundary:** `weatherbot/weather/client.py`'s domain-specific redacted re-raise
(the logic `test_onecall_failure_redacts_key_and_keeps_status`, `test_geocode_failure_redacts_key`,
and `test_reraised_exception_request_carries_no_key` all exercise) is **permanently out of PC-01
scope** — it stays app-local forever. At repin, confirm `client.py` is untouched by the import
swap beyond pointing its redaction call at the hub, and re-run
`test_reraised_exception_request_carries_no_key` as the scope-boundary check.

**Independent verification instruction:** PC-01 (this promotion) must be verified independently of
WR-02/MATCH-03 (the milestone's other, unrelated breaking change) — one combined green CI run does
not attribute a failure to the right change. Verify the redaction repin and the `spec.name` change
in separate runs.

## Section E — Explicitly NOT done

- No version bump (`pyproject.toml` stays at its current version).
- No `v0.2.0` (or any) tag cut.
- No WeatherBot repin, no `uv lock --upgrade`, no `uv sync`.
- No deploy.
- No Phase-6 artifact created: `ls yahir_reusable_bot/redact/` contains only `__init__.py`,
  `core.py`, `registry.py` — no `sink.py`, no `processor.py` (`grep -Ec 'sink.py|processor.py'` on
  the directory listing is `0`).
- `git log --oneline -12` contains no `bump`/`tag v`/`repin`/`deploy` token (case-insensitive grep
  count is `0`).

All of the above is human-gated per `ECOSYSTEM.md` §3 and was not performed by this workflow.

## Decisions Made

- The `redact_scanned` guard copies the exact shape of the three pre-existing guards
  (`scanned`/`registry_scanned`/`discord_scanned`) rather than introducing a new convention —
  keeps `test_litmus_clean` internally consistent as it grows.
- The Phase-5-core vs. Phase-6-seam split for the six WeatherBot parity assertions was determined
  by reading the actual WeatherBot test source rather than inferring from names alone — this
  surfaced that `test_discord_on_message_does_not_dump_key`'s part (b) depends on the `_LiveStderr`
  backstop, which the plan's read-only instructions did not require but which materially changes
  what "4 of 6 pass at repin" vs. "6 of 6 pass at repin" means for the close-out.

## Deviations from Plan

None — plan executed exactly as written. Task 1 made a single surgical addition (10 insertions, 0
deletions, one file) with no other test function touched. Task 2 changed no source and no test;
it produced this SUMMARY as its sole deliverable, per the plan's explicit `<output>` contract.

One voluntary extension beyond the plan's minimum `read_first` list: Task 2 read the actual
WeatherBot test file directly (`/home/yahir/Projects/WeatherBot/tests/test_redact_hygiene.py`) to
verify the Phase-5-core/Phase-6-seam split empirically rather than leaving it unexamined — this is
in the spirit of the plan's own "confirm empirically, don't assume" instruction from Task 1 and
does not change any acceptance criterion.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 5 is closed: all four requirements (REDACT-01, REDACT-02, REDACT-03, REDACT-06) have
  provable RED-first ancestry, all three standing gates are green (105 passed, 8 import-hygiene,
  ruff clean), and the `redact/` public surface (`RedactionPattern`, `redact_secrets`,
  `register_patterns`) is locked with no rename expected before Phase 6.
- Phase 6 (Insertion seams + provable backstop) can now build the structlog sink/processor seam on
  top of this locked surface — the D-52 non-str-tolerance clause and the two Phase-6-dependent
  WeatherBot parity assertions (`test_discord_on_message_does_not_dump_key`,
  `test_livestderr_write_tolerates_and_scrubs_bytes`) are its explicit target.
- The human-gated close-out record (parity-test plan, `client.py` scope boundary, independent
  PC-01/WR-02 verification instruction) is now written down for whoever performs the eventual
  repin — not to be improvised at that time.
- No blockers.

---
*Phase: 05-redaction-core-pattern-registration*
*Completed: 2026-07-29*
