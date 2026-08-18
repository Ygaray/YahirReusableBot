---
phase: 04-cleanup-readygate-fatal
plan: 02
subsystem: infra
tags: [python, package-surface, import-hygiene, discord]

# Dependency graph
requires:
  - phase: 04-cleanup-readygate-fatal (plan 01)
    provides: LIFE-04 ReadyOutcome fatal-outcome fix, standing GATE-01 green baseline (78 passed)
provides:
  - summon_panel re-exported from yahir_reusable_bot.discord (docstring <-> gateway.__all__ <-> package __init__ three-way agreement)
affects: [milestone v0.1.2 human-gated close-out]

# Tech tracking
tech-stack:
  added: []
  patterns: [package __all__ re-export idiom (join onto existing gateway import line, no new import line)]

key-files:
  created: [tests/test_discord_surface.py]
  modified: [yahir_reusable_bot/discord/__init__.py]

key-decisions:
  - "D-47 (export scope): summon_panel re-exported ONLY from discord/__init__.py, never at the top-level yahir_reusable_bot package"

patterns-established: []

requirements-completed: [SURF-01, GATE-01]

coverage:
  - id: D1
    description: "from yahir_reusable_bot.discord import summon_panel succeeds; discord.__all__ contains summon_panel; docstring/gateway.__all__/package __init__ now agree (SURF-01)"
    requirement: "SURF-01"
    verification:
      - kind: unit
        ref: "tests/test_discord_surface.py#test_summon_panel_reexport_succeeds"
        status: pass
    human_judgment: false
  - id: D2
    description: "summon_panel scoped to the discord subpackage only — NOT importable from the top-level yahir_reusable_bot package (D-47 scope guard)"
    requirement: "SURF-01"
    verification:
      - kind: other
        ref: "uv run python -c \"from yahir_reusable_bot import summon_panel\" (raises ImportError, confirmed manually during execution)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Full pytest suite + import-hygiene (grimp graph + isolated-import + AST litmus) stay green (GATE-01)"
    requirement: "GATE-01"
    verification:
      - kind: unit
        ref: "uv run pytest -q (79 passed)"
        status: pass
      - kind: unit
        ref: "uv run pytest tests/test_import_hygiene.py -q (8 passed)"
        status: pass
    human_judgment: false

duration: 3min
completed: 2026-07-28
status: complete
---

> **Archival note (added 2026-08-04, Phase 7 DOCS-02/DOCS-03):** this is an archived v0.1.2 record; the consumer gate-return de-hack path this record names does not exist as spelled — the correct path is `weatherbot/scheduler/daemon.py`, and the enumeration is also incomplete without the producing site `weatherbot/ops/selfcheck.py`. The body below is preserved unrevised as the historical record. See `.planning/v0.1.2-MILESTONE-AUDIT.md` DOC-DRIFT-01 / DOC-DRIFT-02.

# Phase 4 Plan 2: Discord public-surface re-export (SURF-01) Summary

**Closed the docstring/gateway.__all__/package __init__ three-way drift by joining `summon_panel` onto `discord/__init__.py`'s existing gateway import line and `__all__`, scoped to the subpackage only (D-47).**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-07-28T14:44:00Z (approx, per commit timestamps)
- **Completed:** 2026-07-28T14:44:33Z
- **Tasks:** 2 completed
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments
- RED-first proof: `tests/test_discord_surface.py::test_summon_panel_reexport_succeeds` committed while genuinely failing (`ImportError`) against unfixed source
- GREEN fix: `summon_panel` joined onto the existing `from yahir_reusable_bot.discord.gateway import BotThread, build_client` line and appended to `__all__`, mirroring the exact `BotThread`/`build_client`/`PanelKit`/`SelectedContext` idiom
- D-47 scope guard verified: `summon_panel` is NOT importable from the top-level `yahir_reusable_bot` package (only from `yahir_reusable_bot.discord`)
- Docstring left byte-identical (it was already correct — the fix is purely the missing re-export leg)
- Full suite green at 79 passed (was 78 pre-plan, +1 new test); `tests/test_import_hygiene.py` green at 8 passed (grimp graph + isolated-import + AST litmus)

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — write tests/test_discord_surface.py** - `1e762bf` (test)
2. **Task 2: GREEN — add summon_panel re-export to discord/__init__.py** - `eefffc9` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `tests/test_discord_surface.py` - NEW. `test_summon_panel_reexport_succeeds`: the RED-first import-smoke test whose body is the literal statement `from yahir_reusable_bot.discord import summon_panel`, plus an `__all__` membership assertion. No `hasattr` indirection, no mocking library.
- `yahir_reusable_bot/discord/__init__.py` - `summon_panel` joined onto the existing gateway import line and appended to `__all__`. Docstring unchanged.

## Decisions Made
- D-47 (export scope, from 04-CONTEXT.md, applied verbatim): re-export ONLY from `discord/__init__.py`, never at the top-level `yahir_reusable_bot` package. No new decisions made during execution — plan followed exactly as written since D-47 fully specified the fix shape and 04-RESEARCH.md/04-PATTERNS.md gave the exact target diff.

## Deviations from Plan

None — plan executed exactly as written. Both tasks matched their `<action>` and `<acceptance_criteria>` blocks precisely; no auto-fixes, no architectural questions, no auth gates.

## Issues Encountered
None.

## Known Stubs
None.

## Threat Flags
None — this plan's threat model (T-04-04 surface widening, T-04-05 import-hygiene regression) was fully anticipated in 04-CONTEXT.md/04-01-PLAN.md's threat_model block and both mitigations were verified during execution (scope guard test + full import-hygiene suite green). No new, unanticipated security-relevant surface was introduced.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 4 is now fully complete: both findings from the v0.1.2 hardening report (LIFE-04 in 04-01, SURF-01 here in 04-02) are fixed, RED-first proven, and GATE-01-green.
- **Human-gated close-out remaining (ECOSYSTEM.md §3, NOT performed autonomously):** `pyproject.toml` version bump `0.1.1 -> 0.1.2`, cut the `v0.1.2` tag, then WeatherBot's repin (`[tool.uv.sources]` bump -> `uv lock --upgrade` -> `uv sync` -> deploy) followed by the two named de-hack sites (`weatherbot/scheduler/wiring.py` `_on_fail` fatal branch, `weatherbot/ops/daemon.py` gate-return exit-code check) collapsing onto `ReadyOutcome.FATAL`. These are surfaced for confirmation, not executed here.
- No blockers.

---
*Phase: 04-cleanup-readygate-fatal*
*Completed: 2026-07-28*

## Self-Check: PASSED

- FOUND: tests/test_discord_surface.py
- FOUND: yahir_reusable_bot/discord/__init__.py
- FOUND: .planning/phases/04-cleanup-readygate-fatal/04-02-SUMMARY.md
- FOUND: 1e762bf (test commit)
- FOUND: eefffc9 (feat commit)
