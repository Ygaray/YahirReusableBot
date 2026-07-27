---
status: complete
phase: 01-reachable-reliability
source: [01-VERIFICATION.md]
started: 2026-07-22T23:58:06Z
updated: 2026-07-27T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Concurrent + interrupted retry behavior of build_retrying

expected: Both threads classify the triggering exception identically (`is_transient` is
pure/stateless); the interrupted thread's schedule abandons the pause rather than completing the
full `mid_pause_s` wait (production default 2700s).

why_human: Flagged by Plan 02's own `must_haves` as `verification: backstop` — an assumption
asserted by non-modification of `build_retrying`'s `sleep=stop_event.wait` wiring and
`retry_error_callback`, not exercised by any test in this phase. The plan explicitly states this
abstains to `human_needed` unless explicit evidence is produced. This is by design, not an
oversight: Phase 1's scope was the two live defects, and the concurrency substrate was deliberately
left un-exercised rather than covered by a test that would assert wiring rather than behavior.

result: pass
evidence: |
  User ran a 20-check concurrency harness against the installed package (scratchpad
  uat1_concurrency.py, nothing written into the repo). 20/20 passed:
  - Claim A: 57,600 concurrent is_transient calls (16 threads x 400 iters x 9 exc types) —
    every type collapses to a single stable verdict; the 3 deliberate exclusions
    (LocalProtocolError, ProxyError, UnsupportedProtocol) stay non-transient under load;
    retry.py has no mutable module globals.
  - Claim B (interruptible pause): interrupted mid-pause requested 30s / blocked 1.0s / wait()
    returned True; uninterrupted control blocked the full 1.5s / returned False; two threads on a
    shared stop_event both released in 1.2s. Exhausted RemoteProtocolError escapes as itself, not
    tenacity.RetryError (the D-17 hub-scoped restatement of criterion 1).
verified_by: human (user-run harness), 2026-07-27

## Summary

total: 1
passed: 1
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
