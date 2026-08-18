---
phase: 06-insertion-seams-provable-backstop
plan: 03
subsystem: logging
tags: [structlog, redaction, security-backstop, defense-in-depth]

# Dependency graph
requires:
  - phase: 06-insertion-seams-provable-backstop (plan 06-01)
    provides: "RedactingWriter — the load-bearing sink this processor is explicitly documented as additive to, never a substitute for"
  - phase: 06-insertion-seams-provable-backstop (plan 06-02)
    provides: "REDACTION_PROCESSOR_MARKER — the published opt-in attribute this module's closure sets to participate in assert_redaction_active's D-60 ordering self-check"
provides:
  - "redaction_processor(patterns) -> processor closure — the optional, additive structlog processor scrubbing event_dict string values pre-render (REDACT-05)"
  - "Public re-export of redaction_processor from yahir_reusable_bot.redact — completes the PC-01 public surface"
affects: ["06-04 (EXTENSION-GUIDE.md SEAM-08 quotes this module's docstring warnings; extends test_import_hygiene.py's redact_scanned set to include processor.py; GATE-02 ancestry audit re-derives this plan's RED/GREEN SHAs)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shallow, top-level-only event_dict scrub loop — delegates all substitution to redact_secrets, never recurses into nested containers, never coerces non-string values (mirrors RESEARCH Pattern 2 verbatim)"
    - "Marker-attribute opt-in (REDACTION_PROCESSOR_MARKER, set via setattr on the returned closure) — the same D-60 contract verify.py published, letting a consumer's own hand-written processor opt in identically"
    - "Docstring-as-deliverable: the chain-order precondition and non-substitutability warning are REDACT-05's literal ask, asserted mechanically by a lowercase-substring test rather than left to prose alone"

key-files:
  created:
    - tests/test_redact_processor.py
    - yahir_reusable_bot/redact/processor.py
  modified:
    - yahir_reusable_bot/redact/__init__.py

key-decisions:
  - "D-60's docstring half (loud chain-order precondition + non-substitutability warning) shipped verbatim to RESEARCH.md Architecture Pattern 2's two-warning structure; detection half (plan 06-02's warn-only ordering sub-check) proven wired end-to-end by this plan's marker test"
  - "Processor.py is the second and last redact/ module permitted to import structlog (verify.py, plan 06-02, is the first) — grimp-verified zero import edge to any sibling yahir_reusable_bot subpackage"
  - "WR-02 residual re-checked per CONTEXT.md's deferred-ideas instruction and confirmed it stays correctly closed: no RedactionPattern instance is ever placed into an event_dict (mechanically proven by an acceptance criterion), because the processor reads patterns from its closure and writes only scrubbed strings back"

patterns-established:
  - "Every new redact/ module opens with a long-form, decision-ID-citing docstring, including its own rejected-alternative note (the chain-builder-helper rejection, D-60) — mirrors core.py/registry.py/sink.py/verify.py house voice"

requirements-completed: [REDACT-05]

coverage:
  - id: D1
    description: "redaction_processor scrubs every string event_dict value via the single Phase-5 substitution loop, leaves non-string values (int, None, nested dict, list, live exception-info tuple) untouched by identity, and returns the SAME mapping object handed in"
    requirement: "REDACT-05"
    verification:
      - kind: unit
        ref: "tests/test_redact_processor.py#test_processor_scrubs_string_event_values"
        status: pass
      - kind: unit
        ref: "tests/test_redact_processor.py#test_processor_leaves_non_string_values_untouched"
        status: pass
      - kind: unit
        ref: "tests/test_redact_processor.py#test_processor_returns_the_same_mapping_object"
        status: pass
    human_judgment: false
  - id: D2
    description: "EDGE empty: an empty pattern sequence is an exact, silent identity (no raise, no warning); an empty event_dict returns unchanged"
    requirement: "REDACT-05"
    verification:
      - kind: unit
        ref: "tests/test_redact_processor.py#test_processor_with_no_patterns_is_an_exact_identity"
        status: pass
      - kind: unit
        ref: "tests/test_redact_processor.py#test_processor_with_an_empty_mapping_returns_it_unchanged"
        status: pass
    human_judgment: false
  - id: D3
    description: "EDGE encoding: matches at str code-point level with no Unicode normalization (NFD occurrence of an NFC pattern is not masked); never decodes bytes values (pass through by identity, D-52 boundary respected)"
    requirement: "REDACT-05"
    verification:
      - kind: unit
        ref: "tests/test_redact_processor.py#test_processor_matches_at_code_point_level_without_normalization"
        status: pass
      - kind: unit
        ref: "tests/test_redact_processor.py#test_processor_does_not_decode_bytes_values"
        status: pass
    human_judgment: false
  - id: D4
    description: "The docstring states the chain-order precondition and non-substitutability warning, asserted mechanically at the concept level (order / exception / not-sufficient), not left to editorial goodwill"
    requirement: "REDACT-05"
    verification:
      - kind: unit
        ref: "tests/test_redact_processor.py#test_processor_docstring_states_the_chain_order_precondition"
        status: pass
    human_judgment: false
  - id: D5
    description: "The returned closure carries REDACTION_PROCESSOR_MARKER truthy and is discovered end-to-end: a correctly-wired sink with the real processor placed BEFORE format_exc_info makes assert_redaction_active emit a warning while still returning normally"
    requirement: "REDACT-05"
    verification:
      - kind: unit
        ref: "tests/test_redact_processor.py#test_processor_carries_the_self_check_marker"
        status: pass
    human_judgment: false
  - id: D6
    description: "Positive additive-value case: correctly ordered AFTER format_exc_info, the processor DOES scrub a formatted traceback already rendered into event_dict, with a PLAIN capture double (no sink) attributing the scrub to the processor alone"
    requirement: "REDACT-05"
    verification:
      - kind: unit
        ref: "tests/test_redact_processor.py#test_processor_scrubs_a_formatted_traceback_when_ordered_after_the_exception_formatter"
        status: pass
    human_judgment: false
  - id: D7
    description: "Pinned limitation, tripwire not an endorsement: a processor-only configuration (no sink) under dev.ConsoleRenderer still leaks a formatted traceback, reproducing RESEARCH Pitfall 1 live"
    requirement: "REDACT-05"
    verification:
      - kind: unit
        ref: "tests/test_redact_processor.py#test_processor_only_configuration_still_leaks_a_traceback_without_the_sink"
        status: pass
    human_judgment: false

duration: ~15min
completed: 2026-08-04
status: complete
---

# Phase 6 Plan 3: Optional redaction processor Summary

**`redaction_processor(patterns)` — the optional, additive structlog processor scrubbing `event_dict` string values pre-render, shipped with a loud chain-order precondition and non-substitutability warning in its own docstring, and the pinned live proof of exactly why the sink remains load-bearing.**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-08-04 (GREEN commit)
- **Tasks:** 2 (RED test commit, GREEN implementation commit), plus one follow-up test-fix commit (see Deviations)
- **Files modified:** 3 (1 created test file, 1 created source file, 1 modified barrel), plus 1 test-file follow-up edit

## Accomplishments

- `redaction_processor` built exactly to RESEARCH.md's verified Pattern 2 shape: a
  factory returning a closure that walks `event_dict.items()` and replaces every
  `str` value with `redact_secrets(value, patterns)` — substitution is always
  delegated, never re-implemented, and the closure returns the SAME mapping object
  it was handed.
- The docstring carries both required warnings verbatim in structure (mirroring
  RESEARCH's `⚠ CHAIN-ORDER PRECONDITION` / `⚠ NOT SUFFICIENT ALONE` two-block
  shape) — asserted mechanically by a lowercase-substring test (`order`,
  `exception`, `not sufficient`) so wording can evolve without the test becoming a
  spelling checker.
- `REDACTION_PROCESSOR_MARKER` (plan 06-02's published constant) is set truthy on
  the returned closure via `setattr`, proven discoverable end-to-end: wiring the
  real processor BEFORE `format_exc_info` in a correctly-sink-wired configuration
  makes `assert_redaction_active` emit a warning while still returning normally.
- The positive additive-value case is proven live: correctly ordered AFTER
  `format_exc_info`, the processor DOES scrub a formatted traceback already
  rendered into `event_dict["exception"]` as a flat string — with a PLAIN capture
  double (no sink) so the scrub is attributable to the processor alone.
- The pinned limitation (RESEARCH Pitfall 1) is reproduced live and unchanged: a
  processor-only configuration (no `RedactingWriter`) under `dev.ConsoleRenderer`
  still leaks the secret, because the traceback never passes through `event_dict`
  as a string this processor can see — a tripwire, not a regression, per the
  module's own docstring and the test's explicit "do not delete this test" framing.
- The Phase-5 WR-02 residual was re-checked per `CONTEXT.md`'s deferred-ideas
  instruction and confirmed it stays correctly deferred: the processor never
  places a `RedactionPattern` instance into an `event_dict` (it reads patterns
  from its closure and writes only scrubbed strings back), mechanically proven by
  a Task 2 acceptance criterion.
- The PC-01 public surface is now complete: `RedactionPattern`, `redact_secrets`,
  `register_patterns`, `RedactingWriter`, `assert_redaction_active`,
  `REDACTION_PROCESSOR_MARKER`, `redaction_processor` all re-exported from
  `yahir_reusable_bot.redact`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Commit tests/test_redact_processor.py RED** - `2ce4cd1` (test)
2. **Task 2: GREEN — build redact/processor.py and complete the public surface** - `6bb4241` (feat)
3. **Follow-up: fix RED test's formatter choice (Rule 1 deviation)** - `67a4f42` (test)

**Plan metadata:** (this commit, docs)

## Files Created/Modified

- `tests/test_redact_processor.py` - 11-test REDACT-05 regression suite (277 lines
  after the follow-up fix)
- `yahir_reusable_bot/redact/processor.py` - `redaction_processor`, the shallow
  event_dict scrub closure, the marker opt-in
- `yahir_reusable_bot/redact/__init__.py` - re-exports `redaction_processor`,
  finalizes the module docstring describing the now-complete PC-01 surface and the
  accurate purity rule (`core.py`/`registry.py`/`sink.py` stdlib-only;
  `verify.py`/`processor.py` the two logging-library-coupled modules)

## `redaction_processor` signature (verbatim, for plan 06-04's documentation citation)

```python
def redaction_processor(
    patterns: Sequence[RedactionPattern],
) -> Callable[[object, str, MutableMapping[str, object]], MutableMapping[str, object]]
```

The returned closure signature is structlog's standard three-positional-argument
processor convention: `(logger: object, method_name: str, event_dict: MutableMapping[str, object]) -> MutableMapping[str, object]`.

## Docstring warning headings shipped (verbatim, plan 06-04 quotes these in SEAM-08)

**Chain-order precondition block (opens with):**
```
⚠ CHAIN-ORDER PRECONDITION. Place this AFTER any exception formatter —
structlog.processors.format_exc_info / structlog.processors.dict_tracebacks,
or any other structlog.processors.ExceptionRenderer instance — in your
processors=[...] list, or it will never see traceback text: ...
```

**Non-substitutability block (opens with):**
```
⚠ NOT SUFFICIENT ALONE, even correctly ordered. Some renderers (e.g.
structlog.dev.ConsoleRenderer) format exception information directly into
their own output buffer, bypassing event_dict entirely regardless of where
this processor sits in the chain (RESEARCH Pitfall 1, reproduced live and
pinned by this module's own test suite). RedactingWriter (redact/sink.py) is
the load-bearing backstop; this processor is additive defense-in-depth ...
```

Both are asserted at the concept level (not literal string match) by
`test_processor_docstring_states_the_chain_order_precondition` and by Task 2's own
`uv run python -c` docstring acceptance criterion — checking `after`, `exception`,
`order`, and `not sufficient` all appear (lowercase-normalised).

## WR-02 residual — re-checked and confirmed closed as designed

CONTEXT.md's deferred-ideas list instructed re-checking the `asdict`/`astuple` raw-
pattern-exposure residual "if this phase's processor or telemetry ends up serializing
pattern objects into an `event_dict`." It does not: the processor reads `patterns`
from its closure and writes only `redact_secrets`-scrubbed strings back into the
mapping. Mechanically proven — no `RedactionPattern` instance ever appears among an
`event_dict`'s values after the processor runs. The residual stays correctly deferred,
exactly as CONTEXT.md anticipated.

## Pinned-limitation test — reproduced exactly as RESEARCH Pitfall 1 predicted

`test_processor_only_configuration_still_leaks_a_traceback_without_the_sink`
reproduced the exact live finding RESEARCH.md's Pitfall 1 documented against the
installed `structlog` version: with `redaction_processor` as the only redaction
mechanism (no `RedactingWriter` sink) and `dev.ConsoleRenderer(colors=False)` as the
renderer, `log.exception(...)` still leaks `SENTINEL` into the captured output,
because `ConsoleRenderer` formats the traceback directly into its own output buffer,
bypassing `event_dict` regardless of processor position. No deviation from the
predicted behavior — the pitfall reproduced identically on the first run.

## RED / GREEN commit SHAs (for plan 06-04's GATE-02 ancestry audit)

- **RED:** `2ce4cd1beb752dd09599c592b0a187f67ffd1963` — `test(06-03): RED — optional redaction processor, ordering marker, pinned sink-necessity limitation`
- **GREEN:** `6bb4241b681c5c66bb4c696ff607144c776c98ba` — `feat(06-03): optional redaction processor — additive event-mapping scrubbing`
- Adjacent in `git log` with no intervening commit; `git show --name-only` confirms the
  RED commit touches only `tests/test_redact_processor.py` and the GREEN commit
  touches only `yahir_reusable_bot/redact/processor.py` +
  `yahir_reusable_bot/redact/__init__.py`.
- A third, immediately-following commit `67a4f42` fixes a bug in the RED test
  (see Deviations below) — it postdates the RED→GREEN pair and does not disturb
  their adjacency or purity.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] RED test's `test_processor_scrubs_a_formatted_traceback_when_ordered_after_the_exception_formatter` specified the wrong exception formatter**

- **Found during:** Task 2's GREEN verification (the test failed against a
  spec-compliant, correctly-implemented processor).
- **Issue:** The plan's `<action>` for Task 1, test 10, literally specified
  `structlog.processors.dict_tracebacks` as the exception formatter. Live
  inspection showed `dict_tracebacks` renders the exception into a **nested**
  structure — `event_dict["exception"]` becomes a `list[dict]` with the secret
  buried inside a `frames[].exc_value`/`locals` sub-structure — not a flat string.
  The processor's shallow, top-level-only scrub loop (mandated by the plan's own
  `<action>` text — "walks the mapping's items... for every value that is a str" —
  and by RESEARCH.md's verified Pattern 2 code, and confirmed as the intended
  design by this same suite's `test_processor_leaves_non_string_values_untouched`,
  which pins that non-string top-level values, including nested containers, are
  left opaque) structurally cannot reach a string nested inside a list-of-dicts.
  Recursing into nested containers to reach it would have contradicted the plan's
  explicit shallow-walk spec and that sibling test's own design intent.
- **Fix:** Swapped `dict_tracebacks` for `structlog.processors.format_exc_info`,
  which renders the exception into a single flat `event_dict["exception"]` string —
  the exact shape the shallow scrub loop is designed to reach. `format_exc_info` is
  an equally-recognised `structlog.processors.ExceptionRenderer` instance, so
  plan 06-02's D-60 ordering self-check treats it identically to `dict_tracebacks`;
  nothing about the ordering-warning behavior changes.
- **Files modified:** `tests/test_redact_processor.py` (one test's `processors=[...]`
  list and its docstring).
- **Commit:** `67a4f42` — kept as a separate, immediately-following commit rather
  than amending the RED commit (`2ce4cd1`), preserving the RED→GREEN adjacency and
  per-commit purity invariants plan 06-04's GATE-02 ancestry audit re-derives
  mechanically from git trees. The GREEN commit (`6bb4241`) itself still touches
  only the two source files, satisfying its own acceptance criterion.

## Issues Encountered

None beyond the deviation above, which was caught and closed within Task 2's own
verification loop before the GREEN commit landed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The PC-01 public surface is complete and re-exported:
  `RedactionPattern`, `redact_secrets`, `register_patterns`, `RedactingWriter`,
  `assert_redaction_active`, `REDACTION_PROCESSOR_MARKER`, `redaction_processor`.
- Plan 06-04 can extend `tests/test_import_hygiene.py`'s `redact_scanned` litmus
  coverage guard to include `sink.py`, `verify.py`, and `processor.py`, write the
  `EXTENSION-GUIDE.md` SEAM-08 row/section quoting this plan's docstring warning
  headings above, and re-derive the GATE-02 ancestry for all three of this phase's
  plans (06-01, 06-02, 06-03) from the RED/GREEN SHAs each plan's SUMMARY.md
  records.
- No blockers.

---
*Phase: 06-insertion-seams-provable-backstop*
*Completed: 2026-08-04*

## Self-Check: PASSED

- FOUND: tests/test_redact_processor.py
- FOUND: yahir_reusable_bot/redact/processor.py
- FOUND commit: 2ce4cd1 (RED)
- FOUND commit: 6bb4241 (GREEN)
- FOUND commit: 67a4f42 (test-fix, Rule 1 deviation)
