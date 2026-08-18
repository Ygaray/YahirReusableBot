---
phase: 05-redaction-core-pattern-registration
plan: 02
subsystem: infra
tags: [redaction, redos, regex, security, stdlib]

# Dependency graph
requires:
  - phase: 05-redaction-core-pattern-registration (plan 01)
    provides: "RedactionPattern frozen dataclass (pattern/replacement/skip_redos_check), redact_secrets, redact/ pure-leaf subpackage"
provides:
  - "register_patterns(patterns) -> tuple[RedactionPattern, ...] — vets then freezes a consumer's patterns"
  - "Structural nested-quantifier check + escalating-ladder wall-clock ReDoS probe, both proven independently load-bearing"
  - "register_patterns added to yahir_reusable_bot/redact's public re-export surface"
affects: [05-03-litmus-coverage-guard, phase-6-redaction-seam]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Registration-time fail-loud ValueError for a consumer wiring bug (pathological regex), matching build_registry/CommandRegistry's validate-in-one-pass idiom applied as a free function"
    - "Escalating-ladder wall-clock probe with a cumulative-elapsed check after EVERY individual search, rather than one long single-shot probe string — bounds overshoot for an uninterruptible re engine (T-05-06 termination correction over RESEARCH.md's design)"
    - "Rejection error names the offending entry by INDEX + source-eliding __repr__, never by interpolating the pattern's own source text (PR-02, T-05-02)"

key-files:
  created:
    - tests/test_redact_registry.py
    - yahir_reusable_bot/redact/registry.py
  modified:
    - yahir_reusable_bot/redact/__init__.py

key-decisions:
  - "Implemented the plan's escalating-ladder probe design (_REDOS_LADDER of 13 rungs, +2 per rung in the fine tier through 24, then 100/400/1600/4000 for the coarse tier) instead of RESEARCH.md's single 8,000-char probe — the single-probe design would run a catastrophic pattern's search to completion (re is uninterruptible) and hang the very call meant to prevent hangs. Cumulative elapsed time is checked after every individual search."
  - "test_register_patterns_accepts_proven_boundary_pattern (renamed from 05-VALIDATION.md's draft test_register_patterns_accepts_proven_appid_pattern) — the draft name embedded a WeatherBot domain noun; this plan's litmus discipline requires no domain noun in any identifier under redact/, so the helper and test were named for what they are (a proven boundary pattern), not the app they came from."
  - "Alternation shape that trips the timing probe (structural check misses it): (a|a)*$ against a repeated 'a' probe. Verified empirically per the plan's requirement — _looks_pathological returns False for this shape (no nested-quantifier substring), but _blows_budget rejects it at ladder rung 22 (measured cumulative ~0.82s before rejection, well under the 5s hard test ceiling and the run completes in well under 1s of wall time in the full suite)."
  - "Rejection message names the offending entry by index and by its source-eliding RedactionPattern.__repr__ (from 05-01), and states the fix is to rewrite the pattern — skip_redos_check=True is explicitly stated as NOT the remedy for a rejection (PR-03)."

patterns-established:
  - "redact/registry.py stays a pure leaf: stdlib only (re, time, collections.abc) plus an absolute intra-package import of RedactionPattern from redact.core — no sibling yahir_reusable_bot subpackage import, verified via grimp."

requirements-completed: [REDACT-02, REDACT-03]

coverage:
  - id: D1
    description: "A nested-quantifier pattern is rejected at registration with ValueError, caught by the cheap structural pass (T-05-01)"
    requirement: "REDACT-03"
    verification:
      - kind: unit
        ref: "tests/test_redact_registry.py#test_register_patterns_rejects_catastrophic_pattern"
        status: pass
    human_judgment: false
  - id: D2
    description: "An alternation-shaped catastrophic pattern the structural heuristic does NOT flag is still rejected — the wall-clock timing probe is independently load-bearing, not redundant (Pitfall 5, assumption A2)"
    requirement: "REDACT-03"
    verification:
      - kind: unit
        ref: "tests/test_redact_registry.py#test_register_patterns_rejects_catastrophic_pattern_the_structural_check_misses"
        status: pass
    human_judgment: false
  - id: D3
    description: "WeatherBot's proven boundary pattern is not false-rejected and registers unchanged (assumption A1)"
    requirement: "REDACT-02"
    verification:
      - kind: unit
        ref: "tests/test_redact_registry.py#test_register_patterns_accepts_proven_boundary_pattern"
        status: pass
    human_judgment: false
  - id: D4
    description: "Full registration-call wall time for the proven boundary pattern is measured (not estimated) and stays far under the budget (assumption A4)"
    requirement: "REDACT-03"
    verification:
      - kind: unit
        ref: "tests/test_redact_registry.py#test_register_patterns_vetting_stays_far_under_budget"
        status: pass
    human_judgment: false
  - id: D5
    description: "Rejection of a catastrophic pattern terminates in bounded time (< 5s) — the escalating ladder bounds overshoot instead of running one huge probe to completion (T-05-06)"
    requirement: "REDACT-03"
    verification:
      - kind: unit
        ref: "tests/test_redact_registry.py#test_register_patterns_vetting_terminates_in_bounded_time"
        status: pass
    human_judgment: false
  - id: D6
    description: "skip_redos_check=True genuinely bypasses both checks — a pattern rejected without the flag is accepted with it (D-50)"
    requirement: "REDACT-03"
    verification:
      - kind: unit
        ref: "tests/test_redact_registry.py#test_register_patterns_honors_skip_redos_check"
        status: pass
    human_judgment: false
  - id: D7
    description: "register_patterns returns an immutable tuple; item assignment raises TypeError"
    requirement: "REDACT-02"
    verification:
      - kind: unit
        ref: "tests/test_redact_registry.py#test_register_patterns_returns_immutable_collection"
        status: pass
    human_judgment: false
  - id: D8
    description: "The returned tuple preserves input order — no sorting, no dedup, no reordering (EDGE ordering)"
    requirement: "REDACT-02"
    verification:
      - kind: unit
        ref: "tests/test_redact_registry.py#test_register_patterns_preserves_input_order"
        status: pass
    human_judgment: false
  - id: D9
    description: "Registering the same pattern object twice keeps both entries; the result is still idempotent under redact_secrets re-application (EDGE adjacency)"
    requirement: "REDACT-02"
    verification:
      - kind: unit
        ref: "tests/test_redact_registry.py#test_register_patterns_keeps_duplicate_patterns"
        status: pass
    human_judgment: false
  - id: D10
    description: "register_patterns(()) returns () without raising; register_patterns() with no argument raises TypeError — patterns is required, no default (EDGE empty)"
    requirement: "REDACT-02"
    verification:
      - kind: unit
        ref: "tests/test_redact_registry.py#test_register_patterns_empty_input_returns_empty_tuple"
        status: pass
    human_judgment: false
  - id: D11
    description: "The registry module declares no module-level mutable container; two calls with different inputs never accumulate into one another (EDGE concurrency, SC2)"
    requirement: "REDACT-02"
    verification:
      - kind: unit
        ref: "tests/test_redact_registry.py#test_register_patterns_holds_no_module_level_state"
        status: pass
      - kind: other
        ref: "uv run python -c \"import yahir_reusable_bot.redact.registry as m;bad=[k for k,v in vars(m).items() if not k.startswith('__') and isinstance(v,(list,dict,set,bytearray))];assert bad==[],bad\""
        status: pass
    human_judgment: false
  - id: D12
    description: "The rejection message names the offending entry by INDEX and never echoes the pattern's source text (PR-02, T-05-02)"
    requirement: "REDACT-03"
    verification:
      - kind: unit
        ref: "tests/test_redact_registry.py#test_register_patterns_error_does_not_echo_pattern_source"
        status: pass
    human_judgment: false
  - id: D13
    description: "redact/registry.py stays a pure leaf: stdlib + redact.core only, no sibling yahir_reusable_bot import, litmus-clean signatures"
    verification:
      - kind: unit
        ref: "uv run pytest -q (105 passed, grown from 93-test baseline)"
        status: pass
      - kind: unit
        ref: "uv run pytest tests/test_import_hygiene.py -q (8 passed)"
        status: pass
      - kind: other
        ref: "grimp graph check — no yahir_reusable_bot.redact.* -> sibling edge"
        status: pass
      - kind: other
        ref: "uv run ruff check"
        status: pass
    human_judgment: false

# Metrics
duration: ~12min
completed: 2026-07-29
status: complete
---

# Phase 5 Plan 2: Registration-time ReDoS vetting + frozen pattern collection Summary

**`register_patterns` vets a consumer's patterns with a structural nested-quantifier check plus an escalating wall-clock ReDoS probe (13-rung ladder, cumulative-elapsed cutoff after every search) before freezing them into an immutable tuple — an alternation shape the structural check misses is still caught by the probe alone, proving both halves are independently load-bearing.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-07-29T18:20:00Z (approx.)
- **Completed:** 2026-07-29T18:32:24Z
- **Tasks:** 2
- **Files modified:** 3 (1 test file created, 1 source file created, 1 source file extended)

## Accomplishments
- `tests/test_redact_registry.py` — 12 tests covering REDACT-02 (frozen/order-preserving/
  duplicate-keeping/empty-required/no-module-state) and REDACT-03 (structural rejection,
  timing-probe-only rejection, no-false-reject, measured margin, bounded termination,
  opt-out, non-echoing error)
- `yahir_reusable_bot/redact/registry.py` — `register_patterns`, `_looks_pathological`,
  `_blows_budget`, and the `_NESTED_QUANTIFIER_RX` / `_REDOS_BUDGET_S` / `_REDOS_LADDER` /
  `_REDOS_CORPUS` internal constants
- `yahir_reusable_bot/redact/__init__.py` extended — `register_patterns` added to the
  public re-export surface alongside `RedactionPattern` and `redact_secrets`
- Empirically settled assumptions A1 (no false-reject), A2 (structural-check-blind
  alternation shape genuinely caught by the timing probe alone), and A4 (measured
  vetting margin, not estimated) on this host

## Task Commits

Each task was committed atomically:

1. **Task 1: Commit tests/test_redact_registry.py RED** - `751cda9` (test) — genuinely
   RED: `ModuleNotFoundError: No module named 'yahir_reusable_bot.redact.registry'` at
   collection.
2. **Task 2: GREEN — build redact/registry.py with a bounded-termination ReDoS probe** -
   `cad067e` (feat) — all 12 registry tests pass; full suite grew from 93 to 105 passed
   in 1.27s (real 1.72s); import-hygiene and ruff green; grimp confirms pure-leaf status.

RED→GREEN ancestry is real and adjacent (`git log --oneline -2` shows `feat(05-02)`
immediately after `test(05-02)` with no commit in between — GATE-02 satisfied).

## Files Created/Modified
- `tests/test_redact_registry.py` - 12-test regression suite for REDACT-02/03, importing
  the private probe helpers so a rejection can be attributed to the structural check vs.
  the timing probe specifically
- `yahir_reusable_bot/redact/registry.py` - `register_patterns` + the structural check and
  escalating-ladder wall-clock ReDoS probe, the load-bearing registration entry
- `yahir_reusable_bot/redact/__init__.py` - re-export surface extended with
  `register_patterns`

## Measured Figures (recorded per plan's `<output>` requirement)

- **Final tuning values:** `_REDOS_BUDGET_S = 0.3`; `_REDOS_LADDER = (8, 10, 12, 14, 16,
  18, 20, 22, 24, 100, 400, 1600, 4000)` (fine tier +2/rung through 24, coarse tier
  100/400/1600/4000); `_REDOS_CORPUS = ("a", "0123456789", "abc=def&")` — no tuning
  changes were needed beyond the plan's specified starting values; all figures below were
  measured against them as-is on this host.
- **Proven boundary pattern vetting time:** measured `0.0019s` (well under
  `_REDOS_BUDGET_S / 10 = 0.03s` — a >150x margin).
- **Catastrophic (nested-quantifier `(a+)+$`) rejection time:** caught immediately by the
  structural pass, well under the 5s test ceiling (structural check runs before the timing
  probe is ever invoked for this shape).
- **Alternation shape found to trip the timing probe:** `(a|a)*$` against the repeated-`a`
  corpus unit — `_looks_pathological` returns `False` for it (no nested-quantifier
  substring), but `_blows_budget` rejects it once cumulative elapsed time exceeds budget at
  ladder rung 22 (measured cumulative ≈0.82s in isolated timing, well inside the 5s
  ceiling used by the bounded-termination test for the nested-quantifier case; this
  alternation-only test carries no explicit time assertion per the plan, but its actual
  runtime is a small fraction of a second in the full-suite run).
- **Full-suite runtime before this plan:** 93 passed in 0.32s (per 05-01-SUMMARY.md).
- **Full-suite runtime after this plan:** **105 passed in 1.27s** (`--durations=5`; real
  wall time 1.72s including uv/pytest startup) — under the 10-second ceiling.

## Decisions Made
- Implemented the plan's escalating-ladder termination correction rather than
  RESEARCH.md's single 8,000-character single-shot probe: `_blows_budget` runs each
  `search` as its own step and compares CUMULATIVE elapsed time against `_REDOS_BUDGET_S`
  after every individual search, returning `True` the moment the budget is exceeded. A
  single long probe against a catastrophic pattern would run to completion (stdlib `re`
  is uninterruptible) and hang the vetting call itself — the exact failure this check
  exists to prevent (T-05-06).
- Renamed `test_register_patterns_accepts_proven_appid_pattern` (05-VALIDATION.md's draft
  name) to `test_register_patterns_accepts_proven_boundary_pattern` — the draft name
  embeds a WeatherBot domain noun (`appid`), which the litmus discipline for `redact/`
  forbids in any identifier. The regex text itself (which legitimately contains
  `"appid="`) still appears as a string literal inside the helper, per the plan's explicit
  carve-out for that case.
- The rejection `ValueError` names the offending entry by its index in the input sequence
  and by its `RedactionPattern.__repr__` (source-eliding, from 05-01) — never by
  interpolating `rp.pattern.pattern` directly — and states plainly that
  `skip_redos_check=True` is not a remedy for a rejection, only for a pattern whose
  worst-case cost the consumer has independently reasoned is bounded (PR-03).
- `register_patterns` follows `build_registry`'s free-function, required-no-default-
  parameter idiom (borrowed as an idiom only, not the `CommandRegistry` class) —
  validates every entry in one pass before returning any derived state.

## Deviations from Plan

None - plan executed exactly as written. All 12 named test functions match the plan's
Artifacts section (with the pre-declared, plan-mandated rename of
`test_register_patterns_accepts_proven_appid_pattern` to
`test_register_patterns_accepts_proven_boundary_pattern`, which the plan itself calls out
as a deliberate divergence from `05-VALIDATION.md`'s draft). No tuning of
`_REDOS_BUDGET_S` / `_REDOS_LADDER` / `_REDOS_CORPUS` beyond the plan's specified starting
values was required — the alternation shape `(a|a)*$` tripped the timing probe on the
first candidate tried, and all timing figures landed comfortably inside their respective
ceilings without adjustment. No source file touched in Task 1; no test file touched in
Task 2.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `register_patterns` is now the complete registration entry for plan 05-03's litmus
  coverage guard to build against, and for Phase 6's structlog sink/processor seam to
  call at composition-root wiring time.
- The public pattern surface for the whole phase is now settled:
  `RedactionPattern`/`redact_secrets` (05-01) plus `register_patterns` (05-02) — no
  rename expected before Phase 6.
- No blockers.

---
*Phase: 05-redaction-core-pattern-registration*
*Completed: 2026-07-29*

## Self-Check: PASSED

All created/modified files verified present on disk (`tests/test_redact_registry.py`,
`yahir_reusable_bot/redact/registry.py`, `yahir_reusable_bot/redact/__init__.py`); both
task commit hashes (`751cda9`, `cad067e`) verified present in git history.
