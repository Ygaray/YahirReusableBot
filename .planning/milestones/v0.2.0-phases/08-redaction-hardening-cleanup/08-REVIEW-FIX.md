---
phase: 08-redaction-hardening-cleanup
fixed: 2026-08-18
iterations: 1
findings_addressed:
  warning: 3
  info: 3
findings_fixed: 3
findings_documented_skip: 3
status: all_fixed
fix_commit: 5eea410
---

# Phase 08: Code Review Fix Report

**Fixed:** 2026-08-18
**Source review:** `08-REVIEW.md` (0 critical / 3 warning / 3 info)
**Policy:** resolved-or-documented-skip (operator-directed gap-closure during the
milestone execute run; WR-01 design fork decided by the operator — text-mode contract)

All three **warnings** are fixed in code + tests; all three **info** items are addressed
as documented acceptable-skips (the review itself classed each as non-blocking / "no
action required to ship"). Fixes landed atomically in commit **5eea410**; the full suite
(218 tests), `ruff check`, the import-hygiene gate, and the pyright baseline gate are all
green post-fix.

## Warnings — FIXED

### WR-01 — `RedactingWriter` bytes→str asymmetry (binary targets) — FIXED (documented text-mode contract)
**Resolution:** Operator decision = option (b): narrow the documented contract to
text-mode rather than re-encode. `yahir_reusable_bot/redact/sink.py`'s class docstring now
states the TEXT-MODE contract when redaction is active (a `bytes`-like payload is decoded
to `str` and the scrubbed `str` — never a re-encoded `bytes` — is forwarded, so the wrapped
target must accept `str`; a binary-only target works only while disabled/unpatterned and
raises `TypeError` once redaction turns on). A 5th bullet in `EXTENSION-GUIDE.md`'s "Known
limitations" documents it, and a new characterization test
(`test_sink_binary_only_target_raises_when_redaction_active_documented_limitation`) pins
the boundary the review found untested. No runtime change — the behavior is now honest and
tested rather than silent.

### WR-02 — pyright baseline gate raw `JSONDecodeError` traceback — FIXED
**Resolution:** `scripts/pyright_baseline.py::_run_pyright` now wraps `json.loads` and
re-raises an actionable `RuntimeError` naming the exit code and carrying pyright's own
stderr when the invocation produces no valid JSON. New test
(`test_run_pyright_raises_actionable_error_on_non_json_stdout`, monkeypatched subprocess)
proves the actionable message and closes the IN-02 coverage gap for `_run_pyright`.

### WR-03 — `RedactingWriter._patterns` stored by reference — FIXED
**Resolution:** `sink.py` constructor now snapshots the sequence
(`self._patterns = tuple(patterns)`), so a caller's later mutation of a shared `list`
cannot empty the writer's set nor make `redact_secrets`' iteration raise `RuntimeError`
mid-write — upholding the "never raises" invariant. New deterministic test
(`test_sink_snapshots_patterns_against_caller_side_mutation`) proves the snapshot holds
after the caller clears its list. (`tuple()` of an existing tuple keeps identity, so the
common tuple-literal call is unchanged.)

## Info — DOCUMENTED ACCEPTABLE-SKIP (non-blocking)

### IN-01 — `target: object` leaves 5 grandfathered pyright diagnostics — ACCEPTED
The bare-`object` typing preserves the module's deliberate duck-typing design; the 5
`reportAttributeAccessIssue` entries are grandfathered in `pyright-baseline.json` and do
not regress the gate. A local `Protocol` is a reasonable future refinement but is out of
this phase's scope (no requirement asks for it) and would not change runtime behavior.
Deferred as a non-blocking cleanup.

### IN-02 — `_run_pyright()` / `main()` glue-code coverage — PARTIALLY ADDRESSED
The WR-02 fix adds a unit test that drives `_run_pyright`'s subprocess/JSON path via a
monkeypatched `subprocess.run` (no Node dependency), closing the highest-risk part of this
gap. The `--write-baseline` file-write branch and CLI wiring remain by the suite's
deliberate no-Node-runtime design; the review explicitly marked this "no action required
to ship." Accepted.

### IN-03 — `RedactionPattern.__repr__` leaks compiled-source *length* — ACCEPTED
A minor metadata proxy (source length, not text). Within this project's threat model the
repr already elides the source text itself (the stated goal); the residual length signal is
a known, accepted trade-off, consistent with the WR-02 (REDACT-09) reflection-residual
`ACCEPTED` decision recorded for this phase. Non-blocking; not changed.

---

_Fixed: 2026-08-18 — operator-directed gap-closure (milestone execute run)_
_Fix commit: 5eea410 — all warnings fixed, all info documented-skip; suite + gates green_
