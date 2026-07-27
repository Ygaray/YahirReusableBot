# Phase 2: Latent runtime robustness - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-27
**Phase:** 02-latent-runtime-robustness
**Areas discussed:** Gateway liveness/reconnect (DISC-01), Panel re-summon atomicity (DISC-02),
Selection snapshot API (DISC-04), Reload-reject alert semantics (CFG-01)

Advisor mode (research-backed comparison tables). Owner treated as technical — no product-outcome
reframing; standard calibration (2–4 options/area). Tables built directly from re-read source rather
than spawned research agents (decisions are all this-codebase-internal). DISC-03 (stop() TOCTOU) and
the CFG-01 base hook fire were surfaced as clear-cut and folded without a discussion round.

---

## Gateway liveness/reconnect (DISC-01 / H04)

| Option | Description | Selected |
|--------|-------------|----------|
| Liveness-only + death reason | No hub retry beyond discord.py's own; document `is_alive()` as contract, add death-reason enum; host park-loop owns respawn | ✓ |
| Liveness-only, no death reason | Same but keep only the boolean `is_alive()` + CRITICAL log | |
| Bounded reconnect wrapper | Wrap `start()` in a bounded reconnect loop classifying recoverable vs not | |
| Hybrid injected policy | Liveness default + optional injected reconnect-policy callable | |

**User's choice:** Liveness-only + death reason (Recommended).
**Notes:** Decisive fact — discord.py's default `reconnect=True` already exponential-backoff-
reconnects recoverable disconnects; thread-death is (almost) always a non-recoverable condition
(bad token, disallowed intents, auth-close) that a reconnect wrapper cannot help and would hot-loop
into a Discord ban. The death-reason sub-question is resolved by the pick: yes, add it. → D-21..D-23.

---

## Panel re-summon atomicity (DISC-02 / H05)

| Option | Description | Selected |
|--------|-------------|----------|
| Headroom + broadened catch | Keep create-before-delete (D-06); per-item NotFound/HTTPException/Forbidden catch; reserve pin headroom at cap; document all-foreign-pins residual | ✓ |
| Per-item broadened catch only | Keep create-before-delete, broaden per-item handling only — leaves fresh-but-unpinned possible at the cap | |
| Delete-then-pin (report literal) | Delete old first then send+pin — reverses D-06, opens a zero-panel window | |

**User's choice:** Headroom + broadened catch (Recommended).
**Notes:** The success criterion's "no fresh-but-unpinned panel" and the D-06 no-zero-window
invariant conflict at the 50-pin cap; headroom-reserve reconciles them. The channel-saturated-with-
foreign-pins edge is out of hub authority — document loudly, don't chase. → D-24..D-27.

---

## Selection snapshot API (DISC-04 / H08)

| Option | Description | Selected |
|--------|-------------|----------|
| `snapshot()` method + docstring | Read-once method + explicit await-safety contract docstring | ✓ |
| Docstring/contract-only | Strengthen docstring only, no new method | |
| Immutable snapshot handle | Frozen wrapper / context-manager guard that catches a re-read | |

**User's choice:** `snapshot()` method + docstring (Recommended).
**Notes:** Contract + API only per REQ scope; matches the REQ's "offers a snapshot-safe way to
consume" wording with zero behavior/lock added to a deliberately-minimal lock-free cell. → D-29/D-30.

---

## Reload-reject alert semantics (CFG-01 / H03)

| Option | Description | Selected |
|--------|-------------|----------|
| Same hook, distinct log label | PHASE-2 fires existing `on_rejected(exc)` with a "reconcile-rolled-back" internal label; no surface change | ✓ |
| Distinguish phase to consumer | Add reason/phase enum or a second `on_reconcile_failed` hook | |

**User's choice:** Same hook, distinct log label (Recommended).
**Notes:** Both keep-old outcomes need the same consumer action; the PHASE-2 exception type is
already distinct for any consumer that wants to branch. → D-31/D-32.

---

## Claude's Discretion

- Death-reason representation (str constants vs enum vs `Literal`) within D-22's minimal bound.
- One plan vs split (gateway.py holds three findings — grouping by file is natural); sequence RED
  tests so they don't overlap a sibling's full-suite gate.
- Test-function names; `pytest.raises()` vs `try/except`.
- Synthetic-double shapes (channel/message/client/loop); grow conftest only on a real second caller.
- Docstring wording, given the D-23/D-27/D-30 contracts are stated.

## Deferred Ideas

- Hybrid injected reconnect policy (DISC-01 Opt 3) — promote if a future consumer needs auto-respawn.
- Consumer-side `wiring.py` re-read fix (DISC-04's observed defect) — WeatherBot's, at repin.
- Immutable/enforced snapshot handle — revisit only for a real multi-writer selection.
- Refresh `.planning/codebase/TESTING.md` — housekeeping.
</content>
