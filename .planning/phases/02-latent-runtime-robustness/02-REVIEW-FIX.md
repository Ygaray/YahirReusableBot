---
status: applied
phase: 02-latent-runtime-robustness
source: [02-REVIEW.md]
applied: 2026-07-27
findings_total: 5
fixed: 2
triaged: 3
---

# Phase 2 — Code Review Fixes

Applied against `02-REVIEW.md` (0 Critical, 2 Warning, 3 Info). The two Warnings were
real behavior bugs in the freshly-shipped fixes and were fixed RED-first (D-13) where a
deterministic test was feasible. The three Info findings were triaged with explicit
rationale — none silently dropped.

## Fixed

### WR-01 — pin-cap eviction off-by-one (`gateway.py` summon_panel) — FIXED (RED-first)
- **Defect:** the eviction guard `if len(matches) >= 2:` skipped the **common** re-summon
  case — exactly one existing owned panel — at the pin cap, dropping to the D-27 residual
  and leaving the fresh panel fresh-but-unpinned while logging a false "no owned stray to
  evict" CRITICAL. Directly violated the ROADMAP success criterion "cannot leave a
  fresh-but-unpinned panel."
- **Why >= 1 is correct:** create-before-delete already makes the fresh panel live before
  this eviction, so the no-zero-panel-window invariant (D-24) holds even when the *last*
  owned stray is evicted. This refines D-26's literal "≥2 owned panels" threshold to match
  the create-before-delete ordering the code actually uses.
- **Fix:** `len(matches) >= 2` → `>= 1`; residual branch now fires only when zero owned
  strays exist (genuine foreign-pin saturation).
- **Commits:** `0918db6` (RED: single-owned-panel-at-cap test) → `331e0e5` (GREEN).

### WR-02 — death_reason / _failed write-order race (`gateway.py` `_run`) — FIXED
- **Defect:** `self._failed = True` was written before `self._death_reason`. A host
  park-loop reading `is_alive()` (which reflects `_failed`) could interleave between the
  two writes and observe `is_alive() == False` while `death_reason()` is still `None` — a
  contract violation for the DISC-01 accessor.
- **Fix:** publish `_death_reason` before `_failed` in both except branches.
- **No dedicated RED test:** a cross-thread interleaving window has no deterministic
  single-thread reproduction; the existing DISC-01 death-reason tests assert the
  post-condition (both fields set after `_run`) and remain green.
- **Commit:** `6024336`.

## Triaged (not changed — rationale recorded)

### IN-01 — retry-pin catches `discord.Forbidden` as `HTTPException` (`gateway.py`)
- The headroom-reserve retry `except discord.HTTPException:` also catches `Forbidden`
  (its subclass), so a permission revocation *between* the first pin attempt and the retry
  is labeled "pin failed at cap even after evicting a stray" rather than re-raised to the
  outer TOCTOU backstop the way the first pin's `Forbidden` is.
- **Triage:** ACCEPTED residual. The failure is still **loud** (a CRITICAL log), only the
  label is imprecise; the trigger (permission revoked mid-operation, on the retry only) is
  a very narrow edge. Fixing it is a behavior change (re-raise) with no deterministic test.
  Candidate follow-up if this path ever proves reachable in practice; not chased now to
  avoid an untested behavior change to hub code.

### IN-02 — a failed eviction-delete drops the stray from this call's cleanup (`gateway.py`)
- If the single evicted stray's `delete()` fails, it is `pop`ped from `matches` and so is
  not re-deleted later in this same summon.
- **Triage:** ACCEPTED — self-heals on the next summon (the stray reappears in `matches`
  and is handled), consistent with the D-27 "degrade, don't chase" posture. No change.

### IN-03 — `RuntimeWarning: coroutine 'close' was never awaited` (`tests/test_gateway.py`)
- The DISC-03 stop()-TOCTOU test's fake client leaves a `close()` coroutine un-awaited.
- **Triage:** ACCEPTED test hygiene. The warning faithfully mirrors a genuine (and
  acceptable) narrow production side-effect on `stop()`'s TOCTOU path when the loop is
  already closed; suppressing it in the test would hide that. Suite stays green (the
  warning is non-fatal). No change.

## Verification
- Full suite green after fixes: **35 passed** (`uv run pytest -q`), including GATE-01
  (`tests/test_import_hygiene.py`).
- WR-01 RED→GREEN ancestry: `331e0e5`'s parent is `0918db6`.
