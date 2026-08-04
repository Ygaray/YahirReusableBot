---
phase: 06-insertion-seams-provable-backstop
plan: 01
subsystem: logging
tags: [structlog, redaction, threading, security-backstop]

# Dependency graph
requires:
  - phase: 05-redaction-core-pattern-registration
    provides: "redact_secrets(text, patterns) -> str and RedactionPattern (frozen, slotted, source-eliding __repr__) — the pinned scrub primitive this sink delegates to"
provides:
  - "RedactingWriter — the load-bearing, renderer-agnostic sink wrapper (REDACT-04)"
  - "RedactingWriter.redaction_count / .enabled — lock-guarded telemetry (REDACT-08)"
  - "RedactingWriter.probe_redaction_path() — in-memory-only dry-run proof (D-56 groundwork for plan 06-02's assert_redaction_active)"
  - "Public re-export of RedactingWriter from yahir_reusable_bot.redact"
affects: ["06-02 (verify.py / assert_redaction_active introspects this class by identity)", "06-04 (SEAM-08 doc + test_redact_sink_never_imports_structlog gate)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Non-str/bytes triage owned by the seam, never the pure core (D-52)"
    - "Lock-guarded counter with the hook fired OUTSIDE the lock, swallow-and-continue (D-52/D-57/D-59)"
    - "writelines explicitly re-implemented (never delegated) to close a bypass path"
    - "__getattr__ delegation with an underscore-prefix guard against recursion"
    - "In-memory-only dry-run probe — never calls write()/writelines()/flush() on the real target"

key-files:
  created:
    - tests/test_redact_sink.py
    - yahir_reusable_bot/redact/sink.py
  modified:
    - yahir_reusable_bot/redact/__init__.py

key-decisions:
  - "D-52 non-str/bytes triage order (bytes decode-with-replace, then str+enabled+non-empty-patterns gate, else forward untouched) copied verbatim from WeatherBot's proven _LiveStderr.write"
  - "D-58 counter counts CHANGED WRITES via one `!=` comparison, never re-running patterns with .subn() for an exact substitution total"
  - "D-59 threading.Lock guards only the increment + captured read; the on_redaction hook runs OUTSIDE the lock so a slow/raising hook cannot hold up concurrent writers"
  - "probe_redaction_path() raises two DIFFERENTLY WORDED ValueErrors (disabled vs. empty pattern set) so a caller can tell 'installed but off' from 'nothing to prove' — neither message echoes SENTINEL or pattern source"

patterns-established:
  - "Every new redact/ module opens with a long-form, decision-ID-citing docstring (mirrors core.py/registry.py house voice)"
  - "Test doubles are module-local, hand-written, never a shared conftest.py fixture (D-10)"

requirements-completed: [REDACT-04, REDACT-08]

coverage:
  - id: D1
    description: "RedactingWriter scrubs a logger.exception(...) traceback rendered by dev.ConsoleRenderer with zero exception-formatting processors, asserted against the FULL aggregated write() output"
    requirement: "REDACT-04"
    verification:
      - kind: unit
        ref: "tests/test_redact_sink.py#test_sink_scrubs_full_rendered_traceback"
        status: pass
      - kind: unit
        ref: "tests/test_redact_sink.py#test_sink_aggregates_every_write_call_of_one_emission"
        status: pass
    human_judgment: false
  - id: D2
    description: "A JSONRenderer-produced line carrying the secret still parses with json.loads after redaction, with a neighbouring non-secret field surviving verbatim"
    requirement: "REDACT-04"
    verification:
      - kind: unit
        ref: "tests/test_redact_sink.py#test_sink_scrubbed_json_line_round_trips"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-54 recipe 2 (RedactingWriter installed as sys.stderr before handler construction) scrubs a stdlib logging record and a bare print()"
    requirement: "REDACT-04"
    verification:
      - kind: unit
        ref: "tests/test_redact_sink.py#test_sink_stderr_recipe_scrubs_non_structlog_output"
        status: pass
    human_judgment: false
  - id: D4
    description: "writelines, bytes decoding, non-text forwarding, empty-write, disablement, NFC/NFD non-normalization, and __getattr__ delegation all behave per D-52/D-53 contract"
    requirement: "REDACT-04"
    verification:
      - kind: unit
        ref: "tests/test_redact_sink.py#test_sink_writelines_does_not_bypass_redaction"
        status: pass
      - kind: unit
        ref: "tests/test_redact_sink.py#test_sink_decodes_bytes_before_scrubbing"
        status: pass
      - kind: unit
        ref: "tests/test_redact_sink.py#test_sink_forwards_non_text_payload_untouched"
        status: pass
      - kind: unit
        ref: "tests/test_redact_sink.py#test_sink_empty_write_forwards_and_does_not_count"
        status: pass
      - kind: unit
        ref: "tests/test_redact_sink.py#test_sink_matches_at_code_point_level_without_normalization"
        status: pass
      - kind: unit
        ref: "tests/test_redact_sink.py#test_sink_disabled_forwards_untouched_and_never_counts"
        status: pass
      - kind: unit
        ref: "tests/test_redact_sink.py#test_sink_delegates_unknown_stream_attributes_to_target"
        status: pass
    human_judgment: false
  - id: D5
    description: "Redaction-count telemetry counts changed writes, is monotonic, and is exact under 8 threads x 200 concurrent writes"
    requirement: "REDACT-08"
    verification:
      - kind: unit
        ref: "tests/test_redact_sink.py#test_telemetry_counts_changed_writes_and_is_monotonic"
        status: pass
      - kind: unit
        ref: "tests/test_redact_sink.py#test_telemetry_is_thread_safe_under_concurrent_writes"
        status: pass
    human_judgment: false
  - id: D6
    description: "on_redaction hook receives post-increment counts in order and a raising hook cannot break the write path"
    requirement: "REDACT-08"
    verification:
      - kind: unit
        ref: "tests/test_redact_sink.py#test_on_redaction_hook_receives_count_and_cannot_break_logging"
        status: pass
    human_judgment: false
  - id: D7
    description: "probe_redaction_path() never touches the wrapped target and raises distinct, non-echoing ValueErrors for empty pattern set and disabled states"
    requirement: "REDACT-08"
    verification:
      - kind: unit
        ref: "tests/test_redact_sink.py#test_probe_redaction_path_never_writes_to_target"
        status: pass
      - kind: unit
        ref: "tests/test_redact_sink.py#test_probe_redaction_path_raises_on_empty_pattern_set"
        status: pass
      - kind: unit
        ref: "tests/test_redact_sink.py#test_probe_redaction_path_raises_when_disabled_and_never_echoes_a_value"
        status: pass
    human_judgment: false

duration: ~10min
completed: 2026-08-03
status: complete
---

# Phase 6 Plan 1: Redacting sink Summary

**`RedactingWriter` — a file-like proxy that scrubs the fully-rendered text of any write target (structlog render target or `sys.stderr` itself), with a lock-guarded changed-write counter and an in-memory-only dry-run probe.**

## Performance

- **Duration:** ~10 min
- **Completed:** 2026-08-03T18:08:38-06:00 (GREEN commit)
- **Tasks:** 2 (RED test commit, GREEN implementation commit)
- **Files modified:** 3 (1 created test file, 1 created source file, 1 modified barrel)

## Accomplishments

- `RedactingWriter` built exactly to the researched/pattern-mapped shape: wraps any
  file-like `target`, delegates ALL substitution to `redact_secrets` in one call, and
  owns D-52's non-`str`/`bytes` triage so the Phase-5 core stays strict `str -> str`.
- Proven against the adversarial case a processor-only design structurally cannot see
  (a `logger.exception(...)` under `dev.ConsoleRenderer` with zero exception-formatting
  processors) and against both of D-54's wiring recipes — including the `sys.stderr`
  swap (D-55), which must precede stdlib handler construction (RESEARCH Pitfall 6).
- REDACT-08 telemetry shipped as a `threading.Lock`-guarded, monotonic, changed-write
  counter (D-58) verified exact under 8 threads × 200 concurrent writes (1,601 total,
  including the seed write), with an optional `on_redaction` push hook that cannot
  break the write path even when it raises.
- `probe_redaction_path()` (D-56) proves the scrub code path executes without ever
  calling `write`/`writelines`/`flush` on the real target, and fails loudly with two
  distinctly-worded, non-echoing `ValueError`s for the "empty pattern set" and
  "disabled" silent-off states.

## Task Commits

Each task was committed atomically:

1. **Task 1: Commit tests/test_redact_sink.py RED** - `96ebefd` (test)
2. **Task 2: GREEN — build redact/sink.py and export RedactingWriter** - `5cf35d6` (feat)

**Plan metadata:** (this commit, docs)

## Files Created/Modified

- `tests/test_redact_sink.py` - 17-test REDACT-04/REDACT-08 regression suite (430 lines)
- `yahir_reusable_bot/redact/sink.py` - `RedactingWriter`, `_PROBE_TEXT`, the counter and dry-run probe
- `yahir_reusable_bot/redact/__init__.py` - re-exports `RedactingWriter`, updates the stdlib-only-module enumeration in the docstring

## Decisions Made

- Followed the plan's locked signature and behavior exactly; no discretionary
  deviations. The `_CaptureDouble.pieces` list is typed `list[object]` rather than the
  research sketch's `list[str]` — needed so `test_sink_forwards_non_text_payload_untouched`
  can assert identity-preservation (`capture.pieces[0] is marker`) for a payload that
  is neither `str` nor `bytes`; `all_output` still coerces non-`str` pieces to `str`
  when joining, so every string-based assertion in the other 16 tests behaves
  identically to the research-sketch double.

## RedactingWriter signature (verbatim, for plan 06-02's introspection)

```python
def __init__(
    self,
    target: object,
    patterns: Sequence[RedactionPattern],
    *,
    enabled: bool = True,
    on_redaction: Callable[[int], None] | None = None,
) -> None
```

Public surface: `write(data: object) -> int`, `writelines(lines: Iterable[object]) -> None`,
`flush(self) -> None`, `__getattr__(self, name: str) -> object`, `redaction_count` (property,
`int`), `enabled` (property, `bool`), `probe_redaction_path(self) -> None`.

`_PROBE_TEXT = "redaction-self-check-probe-not-a-secret"` (module-private constant in `sink.py`).

## probe_redaction_path() error messages (verbatim)

**Disabled:**
```
probe_redaction_path: this RedactingWriter is disabled (enabled=False) — installed is
not the same as active, so the dry-run scrub path cannot be proven to run
```

**Empty pattern set:**
```
probe_redaction_path: this RedactingWriter has an empty pattern set — there is nothing
for the dry-run scrub to prove, which is exactly the silent-off state introspection
alone would miss
```

Both verified distinct and non-echoing (neither contains a registered pattern's source
or the sentinel) by `test_probe_redaction_path_raises_when_disabled_and_never_echoes_a_value`
and the plan's own bytecode/message acceptance criterion.

## Measured concurrency-test wall time

`test_telemetry_is_thread_safe_under_concurrent_writes` (8 threads × 200 writes, plus
`test_telemetry_counts_changed_writes_and_is_monotonic`'s earlier 1-write seed against
the same-shaped scenario) completes in **under 5ms** (`pytest --durations=0` reports it
below the 5ms display floor; the full 17-test file runs in 0.04–0.07s total). No
flakiness observed across repeated runs.

## `__getattr__` delegation during the recipe-2 (D-55) test

No surprise surfaced. `logging.StreamHandler()` constructed AFTER the `sys.stderr` swap
resolves the stream at construction time (not lazily), so it bound directly to the
`RedactingWriter` instance; its own `.emit()` calls `stream.write(...)` and
`stream.flush()`, both of which are the writer's own defined methods (not `__getattr__`
delegated), so both routed through the scrub path exactly as designed. `capsys` still
captured everything correctly because the writer's `target` was `capsys`'s own
already-installed `sys.stderr` object, captured at construction time per the plan's
prescribed ordering (`RedactingWriter(sys.stderr, ...)` evaluates the RHS `sys.stderr`
before `monkeypatch.setattr` reassigns it).

## RED / GREEN commit SHAs (for plan 06-04's GATE-02 ancestry re-derivation)

- **RED:** `96ebefd8f0665570ff73e138b982d4e869b07807` — `test(06-01): RED — redacting sink, both wiring recipes, telemetry counter, dry-run probe`
- **GREEN:** `5cf35d633472e2df092467ec5222fb9220d836a3` — `feat(06-01): RedactingWriter sink — rendered-text backstop, counter, dry-run probe`
- Adjacent in `git log` with no intervening commit; `git show --name-only` confirms the
  RED commit touches only `tests/test_redact_sink.py` and the GREEN commit touches only
  `yahir_reusable_bot/redact/sink.py` + `yahir_reusable_bot/redact/__init__.py`.

## Deviations from Plan

None - plan executed exactly as written. All 17 tests, the exact method/property
surface, both wiring recipes, the counter semantics, and the dry-run probe match the
plan's `<action>` and `must_haves.truths` verbatim.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `RedactingWriter` is ready for plan 06-02 (`redact/verify.py`, `assert_redaction_active`)
  to introspect by `isinstance` identity against `structlog.get_config()["logger_factory"]._file`.
- Plan 06-03's `redaction_processor` is independent (additive, structlog-importing) and
  does not depend on anything new from this plan beyond the already-shipped `core.py`.
- Plan 06-04's `EXTENSION-GUIDE.md` SEAM-08 section and
  `test_redact_sink_never_imports_structlog` gate can cite this plan's RED/GREEN SHAs
  and the verified grimp result (no `structlog` edge, no sibling-subpackage edge) above.
- No blockers.

---
*Phase: 06-insertion-seams-provable-backstop*
*Completed: 2026-08-03*

## Self-Check: PASSED

- FOUND: tests/test_redact_sink.py
- FOUND: yahir_reusable_bot/redact/sink.py
- FOUND commit: 96ebefd (RED)
- FOUND commit: 5cf35d6 (GREEN)
