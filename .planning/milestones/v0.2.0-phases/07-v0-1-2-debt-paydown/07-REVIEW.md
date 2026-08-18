---
phase: 07-v0-1-2-debt-paydown
reviewed: 2026-08-04T05:47:59Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - tests/test_doc_drift.py
  - tests/test_gateway.py
  - tests/test_panelkit.py
  - tests/test_ready_gate.py
  - tests/test_registry.py
  - tests/test_reload.py
  - yahir_reusable_bot/config/reload.py
  - yahir_reusable_bot/discord/gateway.py
  - yahir_reusable_bot/discord/panelkit.py
  - yahir_reusable_bot/lifecycle/identity.py
  - yahir_reusable_bot/lifecycle/ready_gate.py
  - yahir_reusable_bot/registry/registry.py
  - yahir_reusable_bot/scheduler/engine.py
findings:
  critical: 0
  warning: 0
  info: 1
  total: 1
status: resolved
dispositions:
  CR-01: rejected_false_positive
  WR-01: fixed
  IN-01: acknowledged
---

# Phase 7: Code Review Report

**Reviewed:** 2026-08-04T05:47:59Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Reviewed the Phase 7 (v0.1.2 debt paydown) diff against `9ff979f` plus the surrounding code
those diffs sit inside, at standard depth. The `_best_effort_hook` f-string→structured-log fix
in `config/reload.py` / `lifecycle/ready_gate.py` is verified drift-free (AST-normalized anti-
drift test present and passing); no remaining f-string log calls in the reviewed set; no
hardcoded secrets, `eval`/`exec`, or domain-noun leaks found. `registry.py`'s new
duplicate-`CommandSpec.name` guard, the `discord.Forbidden`-before-`discord.HTTPException`
retry-pin ordering fix, and the `BotThread.stop` bind-before-schedule restructuring were all
traced through and are correct as implemented and tested. `tests/test_doc_drift.py`'s
exemption logic was specifically scrutinized for vacuity (per the review brief) — every
`_EXEMPT_PREFIXES` entry and the DOCS-02 line-scoped window were manually verified to exclude
a *real*, non-phantom match, and the file's own self-proof tests independently pin this; no
vacuity issue found there.

One genuine correctness defect was found in `discord/gateway.py`'s `summon_panel`: the
unconditional stray-cleanup loop that runs after the pin-cap eviction/retry branch does not
check whether the fresh panel's pin ultimately succeeded. On the failure tail of that branch
(retry pin still raises `Forbidden` or `HTTPException` after a stray was evicted), the function
proceeds to delete every remaining owned panel anyway — leaving the channel with **zero**
pinned panels, which is strictly worse than the pre-summon state and a direct contradiction of
the module's own stated "no-zero-panel-window" invariant (D-06/D-24). This defect predates
Phase 7, but Phase 7's own `DISC-07` classification fix is the exact code path that newly makes
it reachable via a dedicated (`discord.Forbidden`) branch, and the accompanying new test for
that branch stops short of asserting the invariant it should protect — so it is in scope here.

---

## Orchestrator Disposition (post-review verification)

The findings below were verified against the live source before any fix was applied. Outcomes:

### CR-01 — **REJECTED (false positive).** Not a defect; the proposed fix would introduce one.

The finding conflates *panel live* with *panel pinned*.

1. **The invariant is about liveness, not pinnedness.** On the retry-failure tail the fresh panel
   **is** live — `channel.send(...)` at `gateway.py:193` runs before any delete (create-before-delete).
   D-24/D-06's "no-zero-panel-window" guarantees the user is never left with *no panel*; it does not
   guarantee a *pinned* panel. The channel ends with exactly one live, click-responsive panel.
2. **This exact tail is already a documented, accepted limitation.** The same docstring the finding
   cites states it explicitly (D-27, `gateway.py:180-183`): *"if the channel is saturated with FOREIGN
   pins … **or the retried pin still fails**, the fresh panel is left sent but unpinned, and a loud
   CRITICAL is emitted rather than silently swallowing it."* The code emits precisely that CRITICAL.
3. **The proposed remedy would create a real bug.** Skipping the cleanup loop to preserve an old
   pinned panel leaves **two live Views responding to clicks** — the failure mode the delete-never-
   unpin rule exists to prevent (`gateway.py:254`: *"an unpinned-but-live View still responds to
   clicks"*). That would regress D-24/D-25.

No code change made for CR-01. Recorded here so the reasoning is not re-litigated.

### WR-01 — **FIXED.** Genuine doc-vs-code drift.

The `summon_panel` docstring documented a `>=2` eviction threshold while the code has used
`len(matches) >= 1` since the WR-01 fix (`gateway.py:207`), and its parenthetical justification
(*">=1 owned panel is still live throughout"*) was stale in the same way — under the `>=1` threshold
the non-zero guarantee is carried by the **fresh** panel via create-before-delete, not by a surviving
old one. Both corrected; the docstring now matches the inline comment at the eviction site.

This is squarely on-theme for Phase 7 (DOCS-02/DOCS-03): a documentation claim that no longer
describes reality.

### IN-01 — **ACKNOWLEDGED, no action.**

The retry-failure tests do not assert the fate of remaining owned panels. Since CR-01 is rejected,
the "missing" assertion would pin the *documented D-27 residual* rather than a defect. Adding it is
reasonable future hardening but is not a Phase 7 requirement and would be net-new scope on a phase
whose gates are green. Not filed as debt — the behavior is documented in the docstring above.

---

## Critical Issues

> **CR-01 below is retained verbatim as the reviewer wrote it. See the Orchestrator Disposition
> section above — it was verified and REJECTED as a false positive. Do not action it.**

### CR-01: Pin-cap eviction/retry-failure path can delete every owned panel, leaving zero pinned

**File:** `yahir_reusable_bot/discord/gateway.py:207-270`
**Issue:**

In `summon_panel`, when the fresh panel's first `pin()` hits `discord.HTTPException` (pin cap)
and at least one owned stray exists, the code evicts one stray and retries the pin
(lines 207-241). If that retry **also** fails — either `discord.Forbidden` (lines 224-236,
Phase 7's new branch) or `discord.HTTPException` again (lines 237-241) — the failure is logged
at `critical` and swallowed, and execution falls through to the unconditional cleanup loop:

```python
# lines 252-270 (current)
for old in matches:
    try:
        await old.delete()
    except (discord.NotFound, discord.HTTPException, discord.Forbidden):
        _log.warning(...)
if num_matches == 0:
    await on_created()
elif num_matches > 1:
    await on_strays_cleaned(num_matches - 1)
else:
    await on_resummoned()
```

This loop does not know or care whether `msg.pin()` ultimately succeeded — it deletes every
remaining entry in `matches` regardless. Combined with the eviction that already ran, this
means: starting state = N owned pinned panels (N ≥ 1); ending state = the fresh panel sent but
**unpinned**, and **all N** prior owned panels deleted. Net pinned-panel count goes from N to 0.
This is worse than doing nothing, and it directly contradicts the module's own documented
invariant: "there is never a zero-panel window even if a later delete fails" (module docstring,
lines 20-21 / 168-171) — here it is not a delete that fails, it is the *pin* that fails, and the
deletes all succeed regardless.

Confirmed live via the existing (Phase 7-added) test
`test_retry_pin_forbidden_logs_a_distinct_event_not_the_cap_message`
(`tests/test_gateway.py:342-376`): with exactly one owned stray, the retry pin raises
`Forbidden`, and the test asserts `fresh.pinned is False` — but never asserts on `stray.deleted`.
Tracing the code: `stray.delete()` (the eviction) succeeds and pops it from `matches`
*before* the retry pin is attempted, so by the time the retry fails, the stray is already gone.
The subsequent cleanup loop has nothing left to touch only because `matches` is already empty
in that specific 1-owned-panel fixture — but with 2+ owned panels the same trace shows the
*non-evicted* remainder gets swept by the cleanup loop too, leaving the channel with a sent,
unpinned fresh panel and zero live panels.

Additionally, the final `on_resummoned()` / `on_strays_cleaned(...)` callback still fires based
on the pre-eviction `num_matches` count regardless of whether the pin ultimately succeeded — so
operator-facing feedback claims a successful resummon/cleanup even when the panel ended up
unpinned and every prior panel was destroyed.

**Fix:**

Track whether the fresh panel actually ended up pinned, and gate the cleanup loop (and the
success feedback) on it — preserving at least the un-evicted owned panels when the retry
ultimately fails:

```python
fresh_pinned = True
try:
    await msg.pin()
except discord.Forbidden:
    raise
except discord.HTTPException:
    fresh_pinned = False
    if len(matches) >= 1:
        stray = matches[0]
        try:
            await stray.delete()
        except (discord.NotFound, discord.HTTPException, discord.Forbidden):
            _log.warning("stray panel delete failed; continuing", channel_id=...)
        else:
            matches.pop(0)
        try:
            await msg.pin()
        except discord.Forbidden:
            _log.critical("panel pin forbidden on retry ...", channel_id=...)
        except discord.HTTPException:
            _log.critical("panel pin failed at cap even after evicting a stray", channel_id=...)
        else:
            fresh_pinned = True
    else:
        _log.critical("panel pin failed at cap with no owned stray to evict ...", channel_id=...)

if fresh_pinned:
    for old in matches:
        try:
            await old.delete()
        except (discord.NotFound, discord.HTTPException, discord.Forbidden):
            _log.warning("stray panel delete failed; continuing", channel_id=...)
    if num_matches == 0:
        await on_created()
    elif num_matches > 1:
        await on_strays_cleaned(num_matches - 1)
    else:
        await on_resummoned()
else:
    _log.critical(
        "fresh panel never pinned; leaving existing owned panel(s) in place",
        channel_id=getattr(channel, "id", None),
    )
```

Add a test asserting that when the retry pin ultimately fails with 1+ owned matches, the
un-evicted remainder of `matches` survives (is never deleted) — the current suite has no
assertion covering this.

## Warnings

### WR-01: `summon_panel`'s D-26 docstring states a stale ">=2" eviction threshold; code uses ">=1"

**File:** `yahir_reusable_bot/discord/gateway.py:173-178`
**Issue:** The docstring reads:

> "**Pin-cap headroom-reserve (D-26):** if the fresh panel's `pin()` fails with
> `discord.HTTPException` ... AND >=2 owned panels exist, ONE owned stray is evicted first
> (freeing a slot; >=1 owned panel is still live throughout — D-06's no-zero-window holds) and
> the pin is retried."

But the actual condition, at line 207, is `if len(matches) >= 1:`, and the inline comment right
above it (lines 204-206) explains the threshold was deliberately lowered from `>=2` to `>=1` to
fix WR-01 from an earlier phase ("the common single-owned-panel re-summon" case). The top-level
docstring was never updated to match, so it now documents a stronger invariant guarantee
(">=1 owned panel is still live throughout") than the code actually provides — see CR-01 above,
where that guarantee is in fact violated on the retry-failure tail even at the `>=1` threshold.
**Fix:** Update the D-26 docstring paragraph to say `>=1 owned panels exist` and remove or
qualify the "D-06's no-zero-window holds" claim so it doesn't overstate the guarantee (or, once
CR-01 is fixed, update it to accurately describe the now-true invariant).

## Info

### IN-01: New Forbidden-branch test doesn't assert on the fate of remaining owned panels

**File:** `tests/test_gateway.py:342-376`
**Issue:** `test_retry_pin_forbidden_logs_a_distinct_event_not_the_cap_message` and its sibling
`test_retry_pin_http_exception_still_logs_the_cap_message` (`tests/test_gateway.py:378-408`)
both drive `summon_panel` into the retry-pin-fails tail (CR-01's exact path) but only assert on
the log event and `fresh.pinned`. Neither asserts on `stray.deleted` / the surviving contents of
`matches`, which is precisely the gap that let CR-01 ship. **Fix:** once CR-01 is fixed, extend
both tests (and add a 2+-owned-panel variant) to assert the un-evicted remainder is never
deleted when the retry pin ultimately fails.

---

_Reviewed: 2026-08-04T05:47:59Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
