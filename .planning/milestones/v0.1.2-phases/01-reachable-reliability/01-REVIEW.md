---
phase: 01-reachable-reliability
reviewed: 2026-07-22T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - tests/conftest.py
  - tests/test_identity.py
  - tests/test_retry.py
  - yahir_reusable_bot/lifecycle/identity.py
  - yahir_reusable_bot/reliability/retry.py
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-07-22T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the RELY-01 fix (`reliability/retry.py`), the LIFE-01 fix
(`lifecycle/identity.py`), and the two new regression suites plus the repo's
first `conftest.py`.

**Verification performed, not just read:**

- Dumped the actual httpx 0.28.1 MRO for every exception name referenced in
  `is_transient` and its docstring. Confirmed: `NetworkError` really is the
  common parent of `ConnectError`/`ReadError`/`WriteError`/`CloseError`;
  `RemoteProtocolError` and `LocalProtocolError` are siblings under
  `ProtocolError` (not parent/child), so naming `RemoteProtocolError`
  explicitly does not accidentally sweep in `LocalProtocolError`;
  `ProxyError`/`UnsupportedProtocol` are direct `TransportError` children,
  outside `NetworkError`, so the D-02 exclusions are real and reachable, not
  vestigial. The new tuple `(TimeoutException, NetworkError,
  RemoteProtocolError)` is precise — it includes exactly what the phase
  claims and nothing more.
- Checked out the pre-fix versions of both files (`git show 6baf992:...`)
  and re-ran both new test files against them: 6 of 14 tests fail pre-fix
  (`test_classification_includes_remote_protocol_error`,
  `test_classification_includes_network_errors`,
  `test_classification_is_pure_and_repeatable`,
  `test_exhausted_transient_escapes_as_itself_after_full_budget`,
  `test_decoy_positional_marker_arg_does_not_match`,
  `test_two_interpreter_flags_before_module_switch_matches`) — confirming
  the RED-first claim is real, not decorative. All 14 pass post-fix.
  `test_exhausted_transient_escapes_as_itself_after_full_budget` genuinely
  asserts attempt count (4, not 1), which is the load-bearing assertion the
  phase claims it is — a type-only assertion would indeed have passed
  identically pre/post-fix, and the suite correctly avoids that trap.
- Confirmed `python -m<module>` (attached, no space) is valid CPython CLI
  grammar (`python3 -mjson.tool` runs fine) — relevant to the WARNING below.
- Re-ran `tests/test_import_hygiene.py`: still green: no domain noun or
  consumer-ward import crept in via these files.

No Critical/blocker-level issues found. Two Warnings and one Info item,
detailed below — none block the fixes' correctness claims, but one
(WARNING 1) is a real gap in the LIFE-01 fix's stated design rationale that
should at least be tracked, not silently assumed covered.

## Warnings

### WR-01: `-m` scan doesn't handle Python's attached `-mmodule` form; D-06's "mirrors Python's CLI grammar" claim is incomplete

**File:** `yahir_reusable_bot/lifecycle/identity.py:170-178`
**Issue:** The fixed `_argv_matches_marker` scans argv for a standalone
`b"-m"` token followed immediately by the marker token. But CPython also
accepts the **attached** form with no separating space —
`python -mjson.tool` is equivalent to `python -m json.tool` (verified: both
run identically). A daemon launched as `python -mexamplebot` would present
argv as a single token `b"-mexamplebot"`, which never equals `b"-m"`, so the
loop never matches it and `is_running_process` reports the live daemon as
**not running** — a false negative.

This is *not a regression*: the pre-fix code (`b"-m" in argv[1:3]`) had the
identical blind spot, so this isn't something the phase broke. But the new
docstring's justification — "THE rule for the `-m` form (D-06, not a
heuristic): ... This mirrors Python's own CLI grammar" — overstates its own
completeness: it mirrors only the space-separated subset of that grammar.
Given D-06 explicitly frames this as evidence-grounded (not a heuristic),
and D-05/D-07 already document two other CLI-grammar edge cases considered
and rejected/accepted, this gap reads as an oversight in the evidence
gathering rather than a deliberate, documented exclusion (there is no
D-decision recorded rejecting the attached form the way D-05/D-07 record
rejected alternatives for other shapes).

**Fix:** Either (a) extend the scan to also match a token of the form
`b"-m" + proc_marker` (attached, no separator) as matching, or (b) if this
form is deliberately out of scope (e.g. because the module's own
`new_consumer.py` scaffolding always generates space-separated systemd
`ExecStart` lines), add an explicit rejected-alternative note (in the style
of D-05/D-07) recording that decision, and add a regression test proving it
is a documented non-goal rather than an untested gap:
```python
def test_attached_module_switch_form_is_not_matched(cmdline_bytes):
    """argv `python -mexamplebot run` (space-less -m form, valid CPython
    grammar). Currently a false negative — the daemon is reported not
    running. Out of scope per D-XX because <reason>, OR needs fixing."""
    cmdline = cmdline_bytes(b"python", b"-mexamplebot", b"run")
    assert is_running_process(1, proc_marker=MARKER, cmdline_reader=lambda _: cmdline) is False  # documents current (possibly unintended) behavior
```

### WR-02: `test_classification_is_pure_and_repeatable` is unlabeled in the self-proof convention the rest of the file follows

**File:** `tests/test_retry.py:80-88`
**Issue:** Every other test in this file's self-proof note explicitly states
whether it is RED or GREEN pre-fix (`test_classification_includes_remote_protocol_error`,
`test_classification_excludes_local_protocol_error`, etc.). This test uses
`httpx.RemoteProtocolError` as its fixture exception — which independently
verified is RED pre-fix (confirmed by running against the pre-fix source:
it fails, since pre-fix `is_transient` returns `[False, False, False]` against
the asserted `[True, True, True]`) — but its docstring never states this,
unlike its siblings. Given the module's own stated design principle (D-11,
"a suite that omitted the decoy row would look like complete truth-table
coverage" — i.e., the file is explicit about self-proof rigor as a first-class
concern), this one test breaks that convention and could give a future reader
the impression it's a GREEN regression guard when it is in fact one of the
load-bearing RED-pre-fix rows.
**Fix:** Add one sentence to the docstring stating this is RED pre-fix (same
mechanism as `test_classification_includes_remote_protocol_error`), e.g.:
"RED pre-fix — pre-fix `is_transient(RemoteProtocolError)` returns `False`
for every call, failing this assertion; this also guards that a future
refactor doesn't introduce per-call nondeterminism (e.g. caching keyed on
identity) into the classifier."

## Info

### IN-01: Stale cross-file line citation in `conftest.py`

**File:** `tests/conftest.py:28`
**Issue:** The `_InstantStopEvent` docstring cites
"`yahir_reusable_bot/reliability/retry.py:241`" as the location of
`sleep=stop_event.wait`. In the current file, line 241 is
`burst_spread_s=burst_spread_s,` inside the `_wait` closure of
`build_retrying` — the actual `sleep=stop_event.wait` wiring is at line 265.
Since this is the repo's first `conftest.py` and is called out in its own
header as the substrate three more phases will inherit, a stale
cross-file line pointer here is worth fixing before it's copied as a
pattern into later fixtures.
**Fix:**
```python
    """A `threading.Event`-shaped double whose `.wait()` returns immediately.

    `build_retrying` (yahir_reusable_bot/reliability/retry.py:265) wires
    ...
```

---

_Reviewed: 2026-07-22T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
