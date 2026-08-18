---
phase: 06-insertion-seams-provable-backstop
plan: 02
subsystem: logging
tags: [structlog, redaction, security-backstop, introspection]

# Dependency graph
requires:
  - phase: 06-insertion-seams-provable-backstop (plan 06-01)
    provides: "RedactingWriter (enabled/redaction_count properties, probe_redaction_path()) — the class this module introspects by identity and delegates the deep check to"
provides:
  - "assert_redaction_active(*, deep: bool = False) -> None — the wiring-time proof the Phase-6 backstop is genuinely installed and active (REDACT-07)"
  - "REDACTION_PROCESSOR_MARKER — the published opt-in attribute name for the D-60 processor-ordering sub-check"
  - "Public re-export of both symbols from yahir_reusable_bot.redact"
affects: ["06-03 (redaction_processor sets REDACTION_PROCESSOR_MARKER on its closure to opt into the ordering sub-check)", "06-04 (EXTENSION-GUIDE.md SEAM-08 documentation cites this module; GATE-02 ancestry audit)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fail-loud-at-wiring-time with THREE distinct, individually recognisable ValueError messages (unrecognised factory type / missing private attribute naming the installed library version / wrong writer type naming the fix) — never a collapsed generic message (RESEARCH Pitfall 5)"
    - "Warn-only sub-check (D-60) runs LAST inside a raising function, so an optional-component warning can never pre-empt a genuine wiring failure"
    - "Marker-attribute opt-in contract (REDACTION_PROCESSOR_MARKER) instead of identity/import coupling — lets the ordering sub-check ship before the optional processor it detects exists"
    - "Hard raise, no unwrap convention, for a consumer's nested proxy — a deliberate false negative documented as a pinned limitation, never attempted to be resolved structurally"

key-files:
  created:
    - tests/test_redact_verify.py
    - yahir_reusable_bot/redact/verify.py
  modified:
    - yahir_reusable_bot/redact/__init__.py

key-decisions:
  - "D-56 introspection reads structlog.get_config()['logger_factory']._file (a private attribute, verified present on structlog 26.1.0) and raises on any inconclusive result — never a false pass"
  - "D-60 ordering sub-check locates redaction processors via REDACTION_PROCESSOR_MARKER (not a function identity or import), so verify.py ships with zero dependency on the not-yet-built optional processor (grimp-proven: no edge to redact.processor)"
  - "RESEARCH open question 2 resolved as recommended (assumption A1): hard raise, no unwrap convention, for a writer nested inside a consumer's own proxy — message states the fix (wrap with the hub writer FIRST) rather than attempting to walk the proxy"

patterns-established:
  - "verify.py is the second (of exactly two) redact/ modules permitted to import structlog — enumerated explicitly in the package docstring alongside processor.py (plan 06-03, not yet built)"

requirements-completed: [REDACT-07]

coverage:
  - id: D1
    description: "assert_redaction_active passes silently (returns None, raises nothing, warns nothing, writes nothing) when the hub's own RedactingWriter is the live logger factory's file target, for both PrintLoggerFactory and WriteLoggerFactory"
    requirement: "REDACT-07"
    verification:
      - kind: unit
        ref: "tests/test_redact_verify.py#test_assert_redaction_active_passes_when_the_writer_is_wired"
        status: pass
      - kind: unit
        ref: "tests/test_redact_verify.py#test_assert_redaction_active_passes_for_the_write_logger_factory_too"
        status: pass
    human_judgment: false
  - id: D2
    description: "assert_redaction_active raises when no backstop is installed, and raises again after a second structlog.configure() call drops a previously-wired writer — the exact latent-bypass scenario REDACT-07 exists for"
    requirement: "REDACT-07"
    verification:
      - kind: unit
        ref: "tests/test_redact_verify.py#test_assert_redaction_active_raises_when_no_backstop_is_installed"
        status: pass
      - kind: unit
        ref: "tests/test_redact_verify.py#test_assert_redaction_active_raises_after_a_reconfigure_drops_the_writer"
        status: pass
    human_judgment: false
  - id: D3
    description: "The three failure classes (unrecognised factory type, missing private _file attribute naming the installed structlog version, wrong writer type) each raise a DISTINCT, mutually-differing message — never a collapsed generic one"
    requirement: "REDACT-07"
    verification:
      - kind: unit
        ref: "tests/test_redact_verify.py#test_assert_redaction_active_raises_distinctly_for_an_unrecognised_factory_type"
        status: pass
      - kind: unit
        ref: "tests/test_redact_verify.py#test_assert_redaction_active_raises_distinctly_when_the_private_file_attribute_is_absent"
        status: pass
      - kind: unit
        ref: "tests/test_redact_verify.py#test_assert_redaction_active_raises_distinctly_when_the_file_target_is_not_the_hub_writer"
        status: pass
      - kind: unit
        ref: "tests/test_redact_verify.py#test_the_three_failure_messages_are_mutually_distinct"
        status: pass
    human_judgment: false
  - id: D4
    description: "A consumer's own proxy nested around RedactingWriter is reported as a loud failure whose message states the fix (wrap with the hub writer first) — a deliberate, pinned false negative, never a false pass"
    requirement: "REDACT-07"
    verification:
      - kind: unit
        ref: "tests/test_redact_verify.py#test_assert_redaction_active_raises_when_the_writer_is_nested_inside_a_proxy"
        status: pass
    human_judgment: false
  - id: D5
    description: "The opt-in deep check proves behaviour: it raises on an empty pattern set and on a disabled writer (both cases the plain introspection-only call passes), while producing zero writes to the real destination on a healthy writer"
    requirement: "REDACT-07"
    verification:
      - kind: unit
        ref: "tests/test_redact_verify.py#test_deep_check_raises_on_an_empty_pattern_set"
        status: pass
      - kind: unit
        ref: "tests/test_redact_verify.py#test_deep_check_raises_when_the_wired_writer_is_disabled"
        status: pass
      - kind: unit
        ref: "tests/test_redact_verify.py#test_deep_check_writes_nothing_to_the_configured_destination"
        status: pass
    human_judgment: false
  - id: D6
    description: "The D-60 processor-ordering sub-check warns (never raises) in all four matrix cases (misordered, correctly ordered, no recognised formatter, no marked processor), never echoes the sentinel or pattern source, and always leaves assert_redaction_active returning normally when the writer itself is wired"
    requirement: "REDACT-07"
    verification:
      - kind: unit
        ref: "tests/test_redact_verify.py#test_ordering_check_warns_and_never_raises"
        status: pass
    human_judgment: false

duration: ~12min
completed: 2026-08-04
status: complete
---

# Phase 6 Plan 2: assert_redaction_active — provable backstop Summary

**`assert_redaction_active(*, deep=False)` — live structlog introspection proving the redaction backstop is genuinely wired, with an opt-in in-memory deep probe and a warn-only processor-ordering sub-check, all built RED-first against the exact 13-test spec.**

## Performance

- **Duration:** ~12 min
- **Completed:** 2026-08-04T00:16:16Z (GREEN commit)
- **Tasks:** 2 (RED test commit, GREEN implementation commit)
- **Files modified:** 3 (1 created test file, 1 created source file, 1 modified barrel)

## Accomplishments

- `assert_redaction_active` built exactly to the researched/pattern-mapped shape:
  reads `structlog.get_config()["logger_factory"]`, verifies it is a recognised
  factory type, verifies its private `_file` attribute names the installed
  `RedactingWriter`, and raises `ValueError` with a distinguishable message for each
  of the three inconclusive/negative cases — never a false pass.
- Proven against the exact latent-bypass scenario REDACT-07 exists for: wire, pass,
  then a SECOND `structlog.configure()` call drops the writer, and the check raises
  again (RESEARCH Pitfall 7).
- The three failure messages are individually recognisable and mutually distinct —
  one of them (the missing private `_file` attribute) names the installed structlog
  version explicitly, so a maintainer can tell "the logging library changed" from
  "the consumer forgot to wire it" (RESEARCH Pitfall 5).
- A consumer's own proxy nested around `RedactingWriter` is pinned as a deliberate
  false negative — a hard raise stating the fix, no unwrap convention built
  (RESEARCH open question 2, assumption A1).
- The opt-in `deep=True` path delegates to `RedactingWriter.probe_redaction_path()`,
  catching the empty-pattern-set and disabled-writer silent-off states that plain
  introspection alone passes, while never writing to the real destination.
- `REDACTION_PROCESSOR_MARKER` shipped as the opt-in contract for the D-60 ordering
  sub-check, which warns (never raises) in all four matrix cases and has zero import
  edge to the not-yet-built `redact/processor.py` (plan 06-03) — grimp-verified.

## Task Commits

Each task was committed atomically:

1. **Task 1: Commit tests/test_redact_verify.py RED** - `17ef175` (test)
2. **Task 2: GREEN — build redact/verify.py and export assert_redaction_active** - `c13a9b9` (feat)

**Plan metadata:** (this commit, docs)

## Files Created/Modified

- `tests/test_redact_verify.py` - 13-test REDACT-07 regression suite (347 lines)
- `yahir_reusable_bot/redact/verify.py` - `assert_redaction_active`, `REDACTION_PROCESSOR_MARKER`, `_warn_if_processor_misordered`
- `yahir_reusable_bot/redact/__init__.py` - re-exports the two new public symbols, updates the stdlib-only-module enumeration to record `verify.py` as coupled to `structlog`

## Decisions Made

- Followed the plan's locked signature and behavior exactly; no discretionary
  deviations. `warnings.warn(..., stacklevel=2)` was chosen so a consumer's own
  warning filter attributes the warning to their call site, not to this module's
  internals — an implementation detail not specified by the plan but consistent
  with the house `ValueError` messages naming what was checked and why.

## `assert_redaction_active` signature (verbatim, for downstream reference)

```python
def assert_redaction_active(*, deep: bool = False) -> None
```

Public surface: `assert_redaction_active`, `REDACTION_PROCESSOR_MARKER` (module-level
`str` constant). `_warn_if_processor_misordered() -> None` is module-private.

## `REDACTION_PROCESSOR_MARKER` value (verbatim — plan 06-03 must set exactly this)

```
_is_redaction_processor
```

Any callable in a processors chain that sets this attribute to a truthy value
(`setattr(fn, "_is_redaction_processor", True)`) opts into the D-60 ordering
sub-check.

## Three raise messages (verbatim, `{type}` / `{version}` are runtime-substituted)

**Unrecognised factory type:**
```
assert_redaction_active: the configured logger_factory is {type(factory).__name__}, not PrintLoggerFactory or WriteLoggerFactory — this introspection only knows how to read those two factory types
```

**Missing private `_file` attribute (names the installed structlog version):**
```
assert_redaction_active: the installed structlog {structlog.__version__}'s {type(factory).__name__} no longer exposes the private `_file` attribute this introspection is coupled to — this is a structlog implementation-detail change, not a consumer wiring bug; revisit this module's introspection against the installed version
```

**File target is not `RedactingWriter` (also covers the nested-proxy pinned limitation):**
```
assert_redaction_active: the configured logger_factory's file target is {type(target).__name__}, not RedactingWriter. If RedactingWriter is wrapped inside your own proxy, this check cannot see through it — wrap your stream with RedactingWriter FIRST, then wrap that in any additional proxy your project needs.
```

## Two D-60 warning messages (verbatim)

**Misordered (marked processor before the exception formatter):**
```
assert_redaction_active: a redaction processor is positioned before the exception formatter in the processors chain — it will never see traceback text, which is still a live (type, value, traceback) tuple at that point. Move the redaction processor AFTER the exception formatter (e.g. structlog.processors.format_exc_info / dict_tracebacks) for full defense-in-depth. RedactingWriter remains the load-bearing backstop regardless of this ordering.
```

**No recognised exception-formatter type found:**
```
assert_redaction_active: a redaction processor is present in the processors chain, but no recognised exception-formatter type (structlog.processors.ExceptionRenderer) was found — could not verify the redaction processor's position relative to traceback rendering
```

## Installed logging-library version the missing-attribute branch reports

`structlog 26.1.0` — verified live via `uv run python -c "import structlog; print(structlog.__version__)"` and asserted directly in `test_assert_redaction_active_raises_distinctly_when_the_private_file_attribute_is_absent` (`structlog.__version__ in str(excinfo.value)`).

## RED / GREEN commit SHAs (for plan 06-04's GATE-02 ancestry re-derivation)

- **RED:** `17ef1757598a10d927004ec6750047d7e54e8412` — `test(06-02): RED — assert_redaction_active introspection, deep probe, ordering warning`
- **GREEN:** `c13a9b941e06473afe895cc680a62577ab4aab87` — `feat(06-02): assert_redaction_active — wiring proof, deep probe, ordering warning`
- Adjacent in `git log` with no intervening commit; `git show --name-only` confirms the
  RED commit touches only `tests/test_redact_verify.py` and the GREEN commit touches
  only `yahir_reusable_bot/redact/verify.py` + `yahir_reusable_bot/redact/__init__.py`.

## Deviations from Plan

None - plan executed exactly as written. All 13 tests, the exact `assert_redaction_active`/`REDACTION_PROCESSOR_MARKER` surface, the three distinct raise messages, the deep-probe delegation, and the D-60 warn-only ordering sub-check match the plan's `<action>` and `must_haves.truths` verbatim. Every 15-part mechanical acceptance criterion in Task 2 (signature introspection, reconfigure-drop, three-distinct-messages, deep-check silent-off states, ordering matrix, no-leak, grimp isolation, public re-exports, commit purity, RED→GREEN ancestry) was run verbatim from the plan and passed on the first attempt with zero fix cycles.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `assert_redaction_active` and `REDACTION_PROCESSOR_MARKER` are ready for plan
  06-03's `redaction_processor` to set the marker attribute on its returned closure
  to opt into the D-60 ordering sub-check — no changes to `verify.py` required.
- Plan 06-04's `EXTENSION-GUIDE.md` SEAM-08 section and the GATE-02 ancestry audit
  can cite this plan's RED/GREEN SHAs, the verbatim raise/warning messages above,
  and the verified grimp result (no edge to `redact.processor`) directly.
- No blockers.

---
*Phase: 06-insertion-seams-provable-backstop*
*Completed: 2026-08-04*

## Self-Check: PASSED

- FOUND: tests/test_redact_verify.py
- FOUND: yahir_reusable_bot/redact/verify.py
- FOUND commit: 17ef175 (RED)
- FOUND commit: c13a9b9 (GREEN)
