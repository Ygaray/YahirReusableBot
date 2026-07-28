# Phase 3: Reusable public-surface footguns - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-27
**Phase:** 3-public-surface-footguns
**Areas discussed:** Matcher casefold symmetry, Retry burst_size coupling, Scheduler remove() contract, Identity non-Linux degrade

**Format note:** Advisor mode was active (USER-PROFILE.md present). Per the session directive not
to spawn unsolicited subagents, the comparison tables were produced inline from the source read +
prior-phase decisions rather than via parallel research agents. The four gray areas were presented
with a recommended default each; the user accepted all defaults in one pass ("we can go with ur
defaults") — the developer's established decisive, single-answer style. No deep-dive rounds were
requested.

---

## Matcher casefold symmetry (MATCH-01 + MATCH-02, paired)

| Option | Description | Selected |
|--------|-------------|----------|
| Reject loudly at registration (MATCH-02) | `CommandRegistry.__init__` raises `ValueError` on empty / non-casefolded `spec.name` | ✓ |
| Casefold `spec.name` at match time (MATCH-02) | `folded.startswith(spec.name.casefold())` — tolerant, no registration change | |
| Map boundary to original index, preserve raw arg (MATCH-01) | Compute the original-string index for the folded prefix; never slice from folded | ✓ |
| Slice arg from folded string (MATCH-01) | Rejected — breaks the locked RAW-case `ParsedCommand.arg` contract | |

**User's choice:** Recommended default — reject-loud at registration (D-34) + map-to-original-index (D-35).
**Notes:** MATCH-02 reject-loud matches the codebase's "fails LOUD at construction" idiom and
deny-by-default posture; casefold-at-match-time silently hides an uppercase-name wiring bug.
MATCH-01's length mismatch is an input-side effect (`ßtatus` folds longer), so it bites independent
of name normalization — the pair must land together.

---

## Retry burst_size coupling (RELY-02 + RELY-03, paired)

| Option | Description | Selected |
|--------|-------------|----------|
| Guard `burst_size <= 1` → degrade (RELY-02) | Return the spread base, no division by zero, don't raise | ✓ |
| Document precondition loudly in docstring (RELY-03) | State: pair with `stop_after_attempt(2*burst_size)`; `build_retrying` already couples | ✓ |
| Matched-pair factory (RELY-03) | `build_two_burst_wait() -> (wait, stop)` so a standalone caller can't desync | |
| Hard assert inside `two_burst_wait` (RELY-03) | Rejected — function never receives the stop bound, nothing to assert against | |

**User's choice:** Recommended default — degrade (D-36) + loud docstring precondition (D-37).
**Notes:** `two_burst_wait` structurally can't see the stop bound, so a self-check is physically
impossible; `build_retrying` (the wired path every consumer uses) already couples correctly. The
factory is over-built for an unreachable, low-severity footgun — deferred under
build-in-consumer-then-promote.

---

## Scheduler remove() contract (SCHED-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Idempotent swallow | Catch `JobLookupError` → debug-log + return, like `unlink(missing_ok=True)` | ✓ |
| Keep raising, document as contract | Push `try/except JobLookupError` into every reconcile call site | |

**User's choice:** Recommended default — idempotent swallow (D-38).
**Notes:** Removing an already-gone id is a no-op success (desired end-state reached), not a hidden
error — safe for the reconcile double-remove / misfire-coalesce race, symmetric with `register`'s
tolerant posture. Does not violate the loud-failure preference because nothing real is being masked.

---

## Identity non-Linux degrade (LIFE-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Basename both sides in `_argv_matches_marker` | Compare `prog == Path(proc_marker.decode()).name`, symmetric with the argv0 basenaming | ✓ |
| Validate/normalize `proc_marker` at `LifecycleIdentity` construction | Normalize the struct field to a basename at the boundary | |

**User's choice:** Recommended default — basename both sides (D-39).
**Notes:** One line; fixes both the non-Linux degrade sentinel AND real Linux matching for a
path-shaped marker (currently False even on Linux). No-op for a normal basename marker; does not
touch the `-m` module branch. Construction-time normalization is heavier and touches the deliberately
independent `proc_marker` bytes (D-03) — deferred.

---

## Clear-cut findings (surfaced, folded without a discussion round — covered by "defaults")

| Finding | Fix | Selected |
|--------|-------------|----------|
| DISC-05 (H11) | None-guard `interaction.user` → log reject + `return False` (D-40) | ✓ |
| DISC-06 (H12) | Reject empty/blank `marker` at `PanelKit.__init__` — loud construction guard (D-41) | ✓ |
| LIFE-02 (H14) | Set `fd = -1` after first `os.close`; guard the except-path close (D-42) | ✓ |

**Notes:** The fix direction for these three is unambiguous and matches the established idioms
(fail-loud-at-construction for DISC-06; log-every-reject for DISC-05; the report's exact fd-flag fix
for LIFE-02). Surfaced up front so the developer could pull any into discussion; none were pulled.

---

## Claude's Discretion

- Exact `ValueError` messages (D-34/D-41), the D-35 original-index algorithm, the D-36 degrade
  return value, plan splitting across the five disjoint files (with the two ROADMAP pairings kept
  intact and RED tests staggered off sibling gates), test-function names / `pytest.raises` usage,
  and docstring wording — all delegated to the planner/executor within the stated contracts.

## Deferred Ideas

- Matched-pair `two_burst_wait` factory (RELY-03 Option 2) — build-in-consumer-then-promote.
- `proc_marker` construction-time normalization (LIFE-03 Option 3) — revisit only if marker shape
  becomes a recurring confusion source.
- Refresh stale `.planning/codebase/TESTING.md` (conftest note) — housekeeping, not phase scope.
