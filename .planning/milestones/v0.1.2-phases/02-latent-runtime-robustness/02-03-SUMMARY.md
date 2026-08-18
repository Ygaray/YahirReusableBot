---
phase: 02-latent-runtime-robustness
plan: 03
subsystem: infra
tags: [discord.py, asyncio, concurrency-contract, panel-selection, hub-library]

# Dependency graph
requires:
  - phase: 02-latent-runtime-robustness
    provides: "02-02 (DISC-01/02/03 gateway.py fixes, full suite green baseline)"
requires_prior:
  - "01-reachable-reliability — D-11 no-mocking-library house style, D-13 two-commit RED-first idiom, D-17 hub-assertable-observable discipline"
provides:
  - "SelectedContext.snapshot() — additive read-once method carrying an await-safety contract (DISC-04)"
  - "Extended SelectedContext class docstring naming the interleaved-await hazard + snapshot()-before-await idiom (D-30)"
affects: ["human-gated close-out (repin note: WeatherBot's wiring.py adopts snapshot() at repin)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Additive read-once method alongside an existing property, named to carry a usage contract rather than change semantics (same shape as .value/.set())"
    - "Pure in-memory interleaving test via asyncio.gather + asyncio.sleep(0), no mocking library, no discord.py import"

key-files:
  created:
    - tests/test_selection.py
  modified:
    - yahir_reusable_bot/discord/selection.py

key-decisions:
  - "D-29: snapshot() added to SelectedContext, semantically identical to .value, named to carry the await-safety contract (capture once before an await, never re-read after)"
  - "D-30: class docstring's single-writer note extended with the interleaved-await hazard and the snapshot()-before-await idiom; no lock/context-manager/frozen-type added"

patterns-established:
  - "Contract + API only scoping: the hub makes an await-safety idiom explicit and offers a safe primitive without chasing the consumer-side symptom (wiring.py stays out of scope)"

requirements-completed: [DISC-04, GATE-01]

coverage:
  - id: D1
    description: "A value captured via snapshot() before an interleaved await is unchanged after a concurrent set() runs during the yield, while a plain .value re-read after the same yield reflects the write — proving the idiom is load-bearing and that .value is not frozen after first read."
    requirement: "DISC-04"
    verification:
      - kind: unit
        ref: "tests/test_selection.py#test_snapshot_is_stable_across_interleaved_set_but_value_reflects_it"
        status: pass
    human_judgment: false
  - id: D2
    description: "Full suite (34 tests) + import-hygiene/litmus/grimp gates (GATE-01) stay green after the fix; no new imports introduced."
    requirement: "GATE-01"
    verification:
      - kind: unit
        ref: "uv run pytest -q (34 passed)"
        status: pass
    human_judgment: false

# Metrics
duration: 10min
completed: 2026-07-27
status: complete
---

# Phase 2 Plan 3: DISC-04 SelectedContext await-safety contract Summary

**`SelectedContext` gains a `snapshot()` read-once method and an explicit interleaved-await hazard docstring, closing DISC-04 as a contract-plus-API-only fix — no lock added, `.value` unfrozen, first-ever test coverage for `selection.py`.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-07-27T22:39:30Z (approx.)
- **Completed:** 2026-07-27T22:43:52Z
- **Tasks:** 2 (RED test commit → GREEN fix commit)
- **Files modified:** 2 (`yahir_reusable_bot/discord/selection.py`, new `tests/test_selection.py`)

## Accomplishments

- **DISC-04 (H08):** `SelectedContext` gains a `snapshot(self) -> I` method (D-29), placed alongside the existing `.value` property and `.set()`. It returns `self._value` — semantically identical to `.value` — but its distinct name and docstring carry the await-safety contract: capture once into a local before any `await`, then use only the local; never re-read `.value` (or call `snapshot()` again) after an intervening `await`.
- The class docstring's existing single-writer "Concurrency contract" note (`:15-22`) gained a new paragraph (D-30) naming the interleaved-await hazard explicitly: a `Select` tap's `on_select` callback and a command-button handler's `await` both run cooperatively on the same single-threaded gateway loop, so an off-loop `await` can yield control back to a rebinding `on_select` — the H08 cosmetic race. The paragraph prescribes `snapshot()`-before-`await` as the fix.
- No lock, context manager, or frozen/immutable snapshot type was added (D-30 rejected these as over-built for a single-loop interleaving hazard, not cross-thread mutation) — `SelectedContext` keeps its deliberate lock-free minimalism relative to `ConfigHolder`.
- `.value` and `.set()` are behaviorally unchanged: `.value` still reflects a later `set()` — the fix is additive only, guarding against the over-fix risk RESEARCH.md flagged (freezing `.value` after first read would break the legitimate fresh-read-after-callback case).
- Consumer-side `wiring.py` (WeatherBot's actual observed-symptom fix site) was **not** touched — out of hub scope per REQUIREMENTS.md:73-76 and the phase's "contract + API only" boundary.
- First-ever unit coverage for `discord/selection.py`: `tests/test_selection.py`, one test function asserting BOTH halves of the contract in the same test (D-33 under-sampling guard) — `snapshot()`-captured value stable across an interleaved `set()`, AND a `.value` re-read after the same yield reflects the write.
- Full suite green: `uv run pytest -q` — 34 passed (up from 34 tracked after Plan 02; net +1 new test), including `test_import_hygiene.py` (GATE-01). No new imports.

## Task Commits

Each task was committed atomically as its own RED→GREEN two-commit pair:

1. **Task 1: DISC-04 RED** — `cbc08ae` (test-only, `tests/test_selection.py`)
2. **Task 2: DISC-04 GREEN** — `d8502e5` (fix, `yahir_reusable_bot/discord/selection.py`)

**RED-first two-commit ancestry (D-13) confirmed:**
- `d8502e5`'s direct parent is `cbc08ae` (test-only, touches only `tests/test_selection.py`).
- Verified via `git log --oneline -3 -- tests/test_selection.py yahir_reusable_bot/discord/selection.py`.

## Files Created/Modified

- `tests/test_selection.py` (NEW) — one test function, `test_snapshot_is_stable_across_interleaved_set_but_value_reflects_it`, driving the interleaving with `asyncio.gather` over three coroutines (a snapshot-reader, a value-reader, and a writer), each yielding via `asyncio.sleep(0)`. No discord.py import (Pitfall 4) — pure in-memory reproduction of the hazard.
- `yahir_reusable_bot/discord/selection.py` — added `snapshot(self) -> I` next to `.value`/`.set()`; extended the class docstring's Concurrency-contract note with the interleaved-await hazard paragraph and the snapshot()-before-await idiom (D-30).

## Decisions Made

- D-29 (from CONTEXT.md, applied verbatim): `snapshot()` added, semantically identical to `.value`, named to carry the contract; contract + API only, `wiring.py` untouched.
- D-30 (from CONTEXT.md, applied verbatim): class docstring extended with the interleaved-await hazard and the snapshot()-before-await idiom; no lock/context-manager/frozen-type added — rejected as over-built for a single-loop interleaving hazard per RESEARCH.md's Anti-Patterns section.

## Deviations from Plan

None - plan executed exactly as written. Both tasks matched their `<action>`/`<acceptance_criteria>`/`<verify>` blocks; no Rule 1-4 auto-fixes were needed.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Human-Gated Close-Out Note (ECOSYSTEM.md §3)

**Flag for the human-gated close-out:** `SelectedContext.snapshot()` is NEW additive public surface. WeatherBot's `wiring.py` post-await re-read (the actual observed DISC-04 defect) should adopt this idiom once WeatherBot repins to a hub tag containing this fix — that adoption is WeatherBot's own fix, not performed here. No tag, repin, or deploy was performed in this plan — autonomous fix + test work only, per ECOSYSTEM.md §3.

## Next Phase Readiness

- DISC-04 fully closed: RED-first two-commit proof, full suite (34 tests) + GATE-01 (`test_import_hygiene.py`) green.
- Phase 02 (latent-runtime-robustness) all three plans complete: CFG-01 (Plan 01), DISC-01/02/03 (Plan 02), DISC-04 (Plan 03). GATE-01 remains milestone-standing per Plan 01/02 precedent — only fully closed once green across the whole v0.1.2 milestone (Phases 1-4).
- No blockers.

---
*Phase: 02-latent-runtime-robustness*
*Completed: 2026-07-27*

## Self-Check: PASSED

- FOUND: yahir_reusable_bot/discord/selection.py
- FOUND: tests/test_selection.py
- FOUND: commit cbc08ae (DISC-04 test-only RED commit)
- FOUND: commit d8502e5 (DISC-04 fix GREEN commit)
