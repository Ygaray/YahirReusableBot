# Phase 4: Cleanup + ReadyGate fatal outcome - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-28
**Phase:** 04-cleanup-readygate-fatal
**Areas discussed:** Fatal outcome shape, Fatal trigger, Fatal-path semantics, SURF-01 export scope

> Advisor mode, standard calibration tier (vendor_philosophy = pragmatic-fast). All four gray areas
> presented in one multiSelect; user replied "your recs are fine" — every recommended default
> accepted in a single pass, no per-area back-and-forth requested.

---

## Fatal outcome shape (D-44)

| Option | Description | Selected |
|--------|-------------|----------|
| `ReadyOutcome` enum, ONLINE-only-truthy (`__bool__`) | Three identities; existing `if run():` callers stay byte-compatible; new callers branch on `is FATAL` | ✓ |
| Plain enum, force `run() is ReadyOutcome.ONLINE` everywhere | Crisp but churns all call sites; un-updated `if run():` silently treats non-ONLINE as truthy | |
| Keep `bool`, signal fatal via exception / side attribute | Reintroduces the stop-overload-class hack the enhancement removes | |

**User's choice:** Recommended default (ONLINE-only-truthy `ReadyOutcome` enum).
**Notes:** Truthy-constrained ONLINE is the *safe* choice — a plain enum makes SHUTDOWN/FATAL truthy
too, reversing the locked "clean-shutdown keeps current semantics" contract.

---

## Fatal trigger (D-45)

| Option | Description | Selected |
|--------|-------------|----------|
| New `HealthResult.fatal: bool = False`, app-authored; `Severity` unchanged | Additive, backward-compatible; obeys "app classifies, gate branches" litmus | ✓ |
| Reuse `Severity.CRITICAL` as the fatal trigger | Reverses `Severity`'s documented stay-alive contract; conflates log-level with recoverability | |
| New `Severity.FATAL` rung above CRITICAL | Forces fatalness onto the log-level axis — two orthogonal concerns on one field | |

**User's choice:** Recommended default (new `fatal` field).
**Notes:** Log-level and recoverability are orthogonal → separate fields. Leaving `Severity.CRITICAL`
untouched keeps every existing critical-but-recoverable probe re-probing as before.

---

## Fatal-path semantics (D-46)

| Option | Description | Selected |
|--------|-------------|----------|
| `on_fail` fires → critical log → return FATAL immediately (no re-probe) | Mirrors online path's hook→log→return ordering; preserves durable-row stamp | ✓ |
| Skip `on_fail` on the fatal path | Drops the app's durable-row stamp for the most important (terminal) failure | |
| Return FATAL but still do one `stop.wait()` first | Pointless latency; fatal means stop gating now | |

**User's choice:** Recommended default (fire `on_fail`, then return FATAL, no re-probe).
**Notes:** `on_online` does NOT fire (never went online). Non-fatal failing path stays byte-identical.

---

## SURF-01 export scope (D-47)

| Option | Description | Selected |
|--------|-------------|----------|
| Re-export `summon_panel` from the `discord` subpackage only | Docstring already correct + `gateway.__all__` already lists it → add the missing leg | ✓ |
| Fix the docstring (retract the claim) instead of exporting | Success criterion wants the import to *succeed* | |
| Also re-export at top-level `yahir_reusable_bot` | Unnecessary surface widening for an adapter-specific symbol | |

**User's choice:** Recommended default (subpackage-only re-export).
**Notes:** Fix is purely the missing `__init__` re-export leg; no docstring edit.

---

## Claude's Discretion

- Exact `ReadyOutcome` member values / `Enum`-vs-plain-class impl (any "only ONLINE truthy, three
  distinct identities" impl).
- Fatal-log message wording (structured, weather-noun-free, opaque `reason`/`detail` passthrough).
- Test file placement (new `tests/test_ready_gate.py` for LIFE-04; SURF-01 import assertion location).

## Deferred Ideas

None — discussion stayed within phase scope. PC-01 log secret-redaction promotion remains parked as
backlog Phase 999.5 (out of this milestone).
