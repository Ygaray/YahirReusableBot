---
phase: 08-redaction-hardening-cleanup
plan: 02
subsystem: redact
tags: [python, structlog, redaction, observability, re-error]

# Dependency graph
requires:
  - phase: 08-01
    provides: WR-02 rationale-retention gate and Phase-8 ratification framing (no code dependency)
provides:
  - "on_error optional hook on RedactingWriter, mirroring on_redaction's registration shape"
  - "Standing no-leak gate proving the exception payload never carries the secret pattern source"
affects: [08-03 (guide/doc half of REDACT-10), 08-04, 08-05]

# Actuals (#2632)
actuals:
  tokens: 2740
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Guarded observability hook: fire AFTER the fail-closed write completes, inside a swallow-and-continue try/except identical to the sibling on_redaction hook, so a raising/slow callback cannot break the hot logging path"

key-files:
  created: []
  modified:
    - tests/test_redact_sink.py
    - yahir_reusable_bot/redact/sink.py

key-decisions:
  - "on_error signature is Callable[[re.error], None], invoked with exactly the caught exception and nothing else — never the withheld payload, never the offending pattern identity (locked at plan-time in 08-02-PLAN.md, per CONTEXT.md's Claude's-Discretion note)"
  - "The no-leak gate sweeps dir(exc) for every string-valued attribute rather than hardcoding 'pattern' — converts a CPython implementation detail into a tripwire that fails loudly if a future release adds a leaking attribute"

patterns-established:
  - "Sibling-hook symmetry: on_error's constructor param, docstring paragraph, and guard block are structural mirrors of on_redaction's, differing only in payload (int count vs. re.error) and firing condition (fail-closed branch vs. successful substitution)"

requirements-completed: [REDACT-10]

coverage:
  - id: D1
    description: "on_error hook fires with the real re.error when a malformed pattern raises, and the fail-closed write behavior (placeholder out, original withheld, write() never raises) is unperturbed"
    requirement: "REDACT-10"
    verification:
      - kind: unit
        ref: "tests/test_redact_sink.py#test_on_error_hook_fires_with_the_error_when_a_malformed_pattern_raises"
        status: pass
    human_judgment: false
  - id: D2
    description: "Standing no-leak gate: the delivered re.error never carries the secret pattern source in str(), repr(), or any string-valued attribute"
    requirement: "REDACT-10"
    verification:
      - kind: unit
        ref: "tests/test_redact_sink.py#test_on_error_payload_never_carries_the_secret_pattern_source"
        status: pass
    human_judgment: false
  - id: D3
    description: "A raising on_error callback is swallowed — write() still returns normally, placeholder still reaches the target, sentinel never does"
    requirement: "REDACT-10"
    verification:
      - kind: unit
        ref: "tests/test_redact_sink.py#test_on_error_hook_that_raises_cannot_break_the_hot_write_path"
        status: pass
    human_judgment: false
  - id: D4
    description: "on_redaction and on_error never cross-fire on the same write, and the counter stays at 0 on the malformed path"
    requirement: "REDACT-10"
    verification:
      - kind: unit
        ref: "tests/test_redact_sink.py#test_the_two_hooks_never_cross_fire_and_the_counter_ignores_the_malformed_path"
        status: pass
    human_judgment: false

duration: ~15min
completed: 2026-08-17
status: complete
---

# Phase 8 Plan 2: on_error observability hook for the fail-closed malformed-pattern branch Summary

**Added an optional `on_error: Callable[[re.error], None] | None = None` hook to `RedactingWriter`, firing inside the existing `except re.error` branch after the fixed placeholder has already reached the target, guarded by the identical swallow-and-continue wrapper `on_redaction` uses — closing the code half of REDACT-10 under D-01.**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `tests/test_redact_sink.py`: four-test RED-first regression group (`on_error` delivery, standing no-leak gate on the exception payload, raising-hook hot-path survival, no-cross-firing with `on_redaction`) — committed genuinely RED (`TypeError` on the unbuilt keyword), then verified GREEN after the implementation landed.
- `yahir_reusable_bot/redact/sink.py`: `on_error` keyword-only constructor parameter, stored as `self._on_error`; invocation inside the existing `except re.error as exc:` branch, ordered so the placeholder write happens first and the hook fires second, wrapped in a verbatim copy of `on_redaction`'s `except Exception:  # noqa` swallow guard.
- Both constructor and `write`'s docstrings extended with the full `on_error` contract: optional/off-by-default, fires only on the malformed-pattern withholding path, receives only the error (never the payload), fires after the placeholder write, survives a raising/slow callback, and never moves the counter or fires `on_redaction`.
- Zero behavior change to the fail-closed disposition, placeholder text, counter semantics, or D-52 triage order — confirmed by `git diff` showing only 3 deleted lines (the `except re.error:` line and the single `return` statement) across the whole production diff.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the on_error regression group, committed RED** - `724ae55` (test)
2. **Task 2: Wire the guarded on_error hook into the existing fail-closed branch (GREEN)** - `db59297` (feat)

**Plan metadata:** (this commit, made by the orchestrator after wave completion)

## Files Created/Modified
- `tests/test_redact_sink.py` - Added the four-test `on_error` regression group (delivery, no-leak gate, raising-hook survival, no-cross-firing) plus the `_malformed_secret_bearing_pattern()` helper
- `yahir_reusable_bot/redact/sink.py` - Added the `on_error` constructor parameter, its guarded invocation inside the existing `except re.error` branch, and the docstring contract in both the constructor and `write`

## Decisions Made
- `on_error`'s signature and invocation arity mirror `on_redaction` exactly (single positional argument, keyword-only, defaulted `None`) — locked at plan-time in `08-02-PLAN.md` rather than reopened during execution. Passing the offending pattern identity was rejected because `redact_secrets` loops over patterns internally with no per-pattern attribution available without re-running the set (the same cost D-58 already rejected for the counter), and a no-arg notification was rejected as carrying no diagnostic value.
- Added one extra docstring mention of `self._on_error` (beyond the constructor assignment and the invocation-site bind) to satisfy the plan's `grep -c '_on_error' >= 3` acceptance criterion while keeping the addition purely descriptive, not behavioral.

## Deviations from Plan

None - plan executed exactly as written. The one docstring addition beyond the plan's literal prose (an explicit "`stored verbatim as `self._on_error`" clause) was made to satisfy the plan's own `grep -c '_on_error'` acceptance criterion (task 2), not a deviation from intent — the plan's task 2 action already required "at least one docstring mention" per its acceptance criteria table.

## Issues Encountered
None.

## `on_error` payload safety (T-08-02-01)

Observed CPython behavior for the secret-bearing malformed pattern used throughout this plan's tests (`RedactionPattern(pattern=re.compile(re.escape(SENTINEL)), replacement=r"\2")`, applied via `pattern.sub(r"\2", "a secret appid=SENTINELKEY_do_not_leak_123 a")`):

- **Exception type:** `re.PatternError` (the public alias `re.error` still binds to this same type in this Python version)
- **`str(exc)`:** `'invalid group reference 2 at position 1'`
- **`repr(exc)`:** `"PatternError('invalid group reference 2 at position 1')"`
- **String-valued attributes swept via `dir(exc)`:**
  - `msg = 'invalid group reference 2'`
  - `pattern = '\\2'`

Confirms the CPython behavior the plan's design section relies on: the `re.error`/`re.PatternError` raised by a bad replacement template carries the **replacement template** (`\2`) as its `pattern` attribute, not the compiled regex source — so a `literal()`-built secret compiled into the pattern object itself does not travel with the exception. The sentinel (`SENTINELKEY_do_not_leak_123`) is absent from every value above. `test_on_error_payload_never_carries_the_secret_pattern_source` sweeps `dir(exc)` generically (not this hardcoded attribute list) precisely so a future CPython release adding a new leaking attribute is caught rather than assumed away.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The code half of REDACT-10 is closed: the fail-closed malformed-pattern branch is now observable via an optional hook, with a standing gate proving the payload is safe.
- 08-03 (the guide/doc half of REDACT-10) can now document the `on_error` hook's existence and contract in `EXTENSION-GUIDE.md` or equivalent, referencing this plan's docstrings as source of truth.
- No blockers.

---
*Phase: 08-redaction-hardening-cleanup*
*Completed: 2026-08-17*
