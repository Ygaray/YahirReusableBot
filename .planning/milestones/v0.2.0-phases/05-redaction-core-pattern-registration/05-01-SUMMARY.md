---
phase: 05-redaction-core-pattern-registration
plan: 01
subsystem: infra
tags: [redaction, regex, dataclass, security, stdlib]

# Dependency graph
requires: []
provides:
  - "yahir_reusable_bot/redact/ pure-leaf subpackage (stdlib only)"
  - "RedactionPattern frozen dataclass — pattern + replacement pair, literal() constructor, source-eliding __repr__"
  - "redact_secrets(text, patterns) -> str — the public scrubbing loop"
affects: [05-02-pattern-registration-redos-vetting, 05-03-litmus-coverage-guard, phase-6-redaction-seam]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Frozen dataclass with repr=False + explicit source-eliding __repr__ for objects that hold a secret verbatim in a compiled field"
    - "Fail-loud-at-construction ValueError for a footgun input (empty/blank literal), message never echoing the offending value"
    - "Pure str -> str transform with no I/O, no raise, no mutation — validation lives at the registration boundary (plan 05-02), never in the hot substitution loop"

key-files:
  created:
    - tests/test_redact_core.py
    - yahir_reusable_bot/redact/__init__.py
    - yahir_reusable_bot/redact/core.py
  modified: []

key-decisions:
  - "Ported WeatherBot's exact boundary regex r'(appid=)[^&\\s\"'\\''<>\\\\]+' with re.IGNORECASE and the r'\\1***' backreference template unchanged — RedactionPattern accepts it as-is, proving the new API does not force a rewrite of the proven pattern (D-48)."
  - "RedactionPattern.__repr__ is explicit and source-eliding (dataclass repr=False): prints <compiled len=N flags=F> instead of the compiled pattern's source text, so a literal-constructed instance can never leak its secret through logging its own registered pattern set (PR-01, T-05-02)."
  - "RedactionPattern.literal('') and literal('   ') raise ValueError at construction, with a message that names the constraint but never echoes the rejected value (the value may itself be a secret in transit) — D-41 precedent, applied with a stricter no-echo rule than panelkit.py's existing guard."
  - "redact_secrets never raises and performs no compilation (D-52) — the strict str -> str contract is enforced by omission: no try/except, no isinstance guard, no re.compile call anywhere in the function body."

patterns-established:
  - "Pure-leaf redact/ subpackage: stdlib only (re, dataclasses, collections.abc), imports no sibling yahir_reusable_bot subpackage — verified via grimp, no test_import_hygiene.py edits needed."

requirements-completed: [REDACT-01, REDACT-02, REDACT-06]

coverage:
  - id: D1
    description: "redact_secrets masks a secret value while preserving surrounding diagnostics (label, following params, quote/URL boundary), ported from WeatherBot's 5-case boundary matrix"
    requirement: "REDACT-01"
    verification:
      - kind: unit
        ref: "tests/test_redact_core.py#test_redact_helper_boundaries"
        status: pass
    human_judgment: false
  - id: D2
    description: "redact_secrets is idempotent, silently no-ops on zero patterns, returns empty string for empty text, applies patterns in registration order, replaces every adjacent occurrence, and never mutates its arguments"
    requirement: "REDACT-01"
    verification:
      - kind: unit
        ref: "tests/test_redact_core.py#test_redact_secrets_idempotent"
        status: pass
      - kind: unit
        ref: "tests/test_redact_core.py#test_redact_secrets_zero_patterns_is_identity"
        status: pass
      - kind: unit
        ref: "tests/test_redact_core.py#test_redact_secrets_empty_text_returns_empty"
        status: pass
      - kind: unit
        ref: "tests/test_redact_core.py#test_redact_secrets_applies_patterns_in_registration_order"
        status: pass
      - kind: unit
        ref: "tests/test_redact_core.py#test_redact_secrets_replaces_every_adjacent_occurrence"
        status: pass
      - kind: unit
        ref: "tests/test_redact_core.py#test_redact_secrets_does_not_mutate_input_or_patterns"
        status: pass
      - kind: unit
        ref: "tests/test_redact_core.py#test_redact_secrets_masks_non_ascii_literal_at_code_point_level"
        status: pass
    human_judgment: false
  - id: D3
    description: "RedactionPattern is a frozen dataclass (mutating a field raises FrozenInstanceError)"
    requirement: "REDACT-02"
    verification:
      - kind: unit
        ref: "tests/test_redact_core.py#test_redaction_pattern_is_frozen"
        status: pass
    human_judgment: false
  - id: D4
    description: "RedactionPattern.literal blocks a registered secret wherever it physically appears (including inside another object's repr()), escapes regex metacharacters, rejects empty/blank values at construction, and its own repr()/str()/!r never leak the secret it holds"
    requirement: "REDACT-06"
    verification:
      - kind: unit
        ref: "tests/test_redact_core.py#test_literal_matches_inside_repr"
        status: pass
      - kind: unit
        ref: "tests/test_redact_core.py#test_literal_escapes_regex_metacharacters"
        status: pass
      - kind: unit
        ref: "tests/test_redact_core.py#test_literal_rejects_empty_or_blank_value"
        status: pass
      - kind: unit
        ref: "tests/test_redact_core.py#test_redaction_pattern_repr_does_not_leak_pattern_source"
        status: pass
    human_judgment: false
  - id: D5
    description: "redact/ stays a pure stdlib leaf (no sibling yahir_reusable_bot import), no compilation inside the hot redact_secrets loop, no os/env read, full suite + import-hygiene + ruff stay green"
    verification:
      - kind: unit
        ref: "uv run pytest -q (93 passed, grown from 80-test baseline)"
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
      - kind: other
        ref: "bytecode co_names check — 'compile' absent from redact_secrets.__code__.co_names"
        status: pass
    human_judgment: false

# Metrics
duration: ~18min
completed: 2026-07-29
status: complete
---

# Phase 5 Plan 1: Redaction core — RedactionPattern, literal mode, redact_secrets Summary

**Ported WeatherBot's proven `_APPID_RX` scrubber into a generic `redact_secrets(text, patterns)` core with a frozen `RedactionPattern` pair type and a source-eliding literal-secret constructor.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-07-29T18:22:00Z (approx.)
- **Completed:** 2026-07-29T18:25:38Z
- **Tasks:** 2
- **Files modified:** 3 (1 test file created, 2 source files created)

## Accomplishments
- `tests/test_redact_core.py` — 13 tests covering REDACT-01 (boundary matrix, idempotence,
  zero-pattern no-op, empty text, registration ordering, adjacent-occurrence replace-all,
  non-mutation, non-ASCII code-point masking), REDACT-02's frozen-type half, and REDACT-06
  (literal-inside-repr, metachar escaping, empty/blank rejection, repr elision)
- `yahir_reusable_bot/redact/core.py` — `RedactionPattern` frozen dataclass with pre-compiled
  `pattern`, `replacement` template, defaulted `skip_redos_check`, a `literal()` classmethod, and
  an explicit source-eliding `__repr__`; `redact_secrets(text, patterns) -> str`, the sequential,
  never-raising, never-mutating substitution loop
- `yahir_reusable_bot/redact/__init__.py` — public re-export (`RedactionPattern`, `redact_secrets`)
- Verified pure-leaf status via grimp (no sibling `yahir_reusable_bot` import), no compilation
  inside the hot loop (bytecode `co_names` check), and no `os`/environment read anywhere in the
  subpackage (D-53)

## Task Commits

Each task was committed atomically:

1. **Task 1: Commit tests/test_redact_core.py RED** - `753f3d5` (test) — genuinely RED:
   `ModuleNotFoundError: No module named 'yahir_reusable_bot.redact'` at collection.
2. **Task 2: GREEN — build redact/core.py and the subpackage re-export** - `104cdbe` (feat) —
   all 13 core tests pass; full suite grew from 80 to 93 passed; import-hygiene and ruff green.

_Note: this plan is not TDD-tagged, but follows the same RED-then-GREEN two-commit discipline
GATE-02 requires: the test commit above is a real collection failure, and the feat commit is the
very next commit with no other commit between them._

## Files Created/Modified
- `tests/test_redact_core.py` - 13-test regression suite for REDACT-01/02/06, ported from
  WeatherBot's `test_redact_hygiene.py` boundary matrix plus new edge-case coverage
- `yahir_reusable_bot/redact/core.py` - `RedactionPattern` + `redact_secrets`, the load-bearing
  public pattern surface
- `yahir_reusable_bot/redact/__init__.py` - re-export surface (`RedactionPattern`, `redact_secrets`)

## Decisions Made
- Ported the exact boundary regex `r"(appid=)[^&\s\"'<>\\]+"` (with `re.IGNORECASE`) and the
  `r"\1***"` backreference template from `weatherbot/_redact.py` into the test's inline
  `RedactionPattern` construction, unchanged — proves `RedactionPattern` doesn't force a rewrite
  of the proven pattern shape it's meant to accept as-is.
- `RedactionPattern.__repr__` is explicit (`repr=False` on the dataclass decorator) and prints
  `<compiled len=N flags=F>` rather than the pattern's source text — the compiled pattern is the
  one place a literal-constructed instance holds a secret verbatim, so the default dataclass repr
  would be a direct leak path (PR-01, T-05-02). `__str__` is deliberately left undefined so Python
  falls back to `__repr__` for both `str()` and `!r` interpolation.
- `RedactionPattern.literal("")`/`literal("   ")` raise `ValueError` at construction (D-41
  fail-loud-at-construction precedent from `panelkit.py`'s empty-marker guard), but the message
  intentionally does NOT echo the rejected value — stricter than `panelkit.py`'s existing guard,
  because a value handed to `literal()` may itself be an in-transit secret.
- `redact_secrets` performs zero validation and never raises (D-52): the strict `str -> str`
  contract and the "no compilation inside the hot loop" requirement are both satisfied by what the
  function does NOT do, not by a defensive check.

## Deviations from Plan

None - plan executed exactly as written. All 13 named test functions match the plan's Artifacts
section exactly; `RedactionPattern` and `redact_secrets` signatures match the plan's specified
shapes; no source file touched in Task 1; no test file touched in Task 2.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `yahir_reusable_bot/redact/core.py` is ready for plan 05-02 to build `redact/registry.py`
  (`register_patterns`) on top of it — `RedactionPattern.skip_redos_check` is already present as
  the carried, unread-by-core opt-out field plan 05-02's registration path will consume.
- `RedactionPattern`'s public shape (pattern/replacement/skip_redos_check, `literal()`,
  `__repr__`) is now locked for the whole phase — plan 05-03's litmus coverage guard and the
  eventual Phase 6 seam both build on this exact surface without needing a rename.
- No blockers.

---
*Phase: 05-redaction-core-pattern-registration*
*Completed: 2026-07-29*

## Self-Check: PASSED

All created files verified present on disk; both task commit hashes (`753f3d5`, `104cdbe`) verified
present in git history.
