---
phase: 02-latent-runtime-robustness
reviewed: 2026-07-27T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - yahir_reusable_bot/config/reload.py
  - yahir_reusable_bot/discord/gateway.py
  - yahir_reusable_bot/discord/selection.py
  - tests/test_reload.py
  - tests/test_gateway.py
  - tests/test_selection.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-07-27T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the diff from `0b40a2f` implementing CFG-01 and DISC-01..04. The diff is
disciplined and well-documented; I traced each of the five fixes against the specific
checks in the review brief:

- **CFG-01 (`reload.py`)** — correct. `on_rejected` fires exactly once on the PHASE-2
  reconcile-failure path, with the original exception (`exc`), strictly before the bare
  `raise`. The nested `restore` best-effort catch does not rebind `exc`, so the exception
  identity re-raised is provably the original reconcile exception (matches
  `test_reconcile_failure_fires_on_rejected_once_and_rolls_back`). `on_rejected` does not
  fire on the success path. No defect found.
- **DISC-01 (`gateway.py` `death_reason()`)** — mostly correct, but see WR-02: `_failed`
  and `_death_reason` are two separate, unsynchronized attribute writes, opening a narrow
  window where a host reads `is_alive() == False` and `death_reason() is None`.
- **DISC-02 (`gateway.py` `summon_panel`)** — create-before-delete ordering is preserved,
  the pin-cap number is never hardcoded (reacts generically to `discord.HTTPException`),
  and per-item delete failures are isolated. However, the eviction guard's boundary
  condition (`len(matches) >= 2`) is wrong by one — see WR-01 — and two secondary gaps
  (IN-01, IN-02) exist in the retry/eviction-failure sub-paths.
- **DISC-03 (`gateway.py` `stop()`)** — correct: the `run_coroutine_threadsafe` call was
  moved inside the same `try` as `future.result()`, so the TOCTOU race is closed and the
  thread join is always reached. See IN-03 for the associated (non-fatal) unawaited-
  coroutine warning this path produces.
- **DISC-04 (`selection.py` `snapshot()`)** — correct: a faithful, lock-free read-once,
  semantically identical to `.value`, no new synchronization introduced.

None of the findings below are Critical — no security vulnerability, crash, or data-loss
risk. Two are logic/robustness Warnings worth fixing before this ships as the "hardened"
version of these paths; three are minor Info-level polish items.

## Warnings

### WR-01: Pin-cap eviction boundary excludes the exact-one-stray case

**File:** `yahir_reusable_bot/discord/gateway.py:203`

**Issue:** When the fresh panel's `pin()` fails with `discord.HTTPException` (pin cap
reached), the headroom-reserve eviction only runs `if len(matches) >= 2:`. When exactly
**one** owned stray exists (`len(matches) == 1`), the code falls into the `else` branch
(D-27 residual) and emits:

```
"panel pin failed at cap with no owned stray to evict (foreign-pin saturation); "
"fresh panel sent but left unpinned"
```

— which is factually wrong in this case: there **is** one owned stray available to evict.
Evicting it would free exactly the one slot needed and let the retry `pin()` succeed,
exactly as the `len(matches) >= 2` path already does for two-or-more strays. The `>= 2`
threshold's own justification in the docstring ("`>=1` owned panel is still live
throughout — D-06's no-zero-window holds") is satisfied just as well when only one stray
exists, because the fresh (unpinned) panel is already sent and counts as a live owned
message before the eviction runs. There is no test exercising `len(matches) == 1` at the
pin cap — both `summon_panel` tests use 0/2/3 matches, so this off-by-one boundary was
never sampled.

**Fix:**
```python
        except discord.HTTPException:
            # Pin-cap headroom-reserve (D-26): react generically to the HTTPException —
            # never branch on a specific cap count.
            if len(matches) >= 1:
                stray = matches.pop(0)
                ...
```
Add a regression test with exactly one owned match at cap to lock in the corrected
boundary (mirroring the existing `len(matches) == 2` test).

### WR-02: `_failed` / `_death_reason` are two unsynchronized writes — a host can observe a false "reason not yet known" window

**File:** `yahir_reusable_bot/discord/gateway.py:367-368` and `:373-374`

**Issue:** In `_run`'s except branches:

```python
except discord.LoginFailure:
    self._failed = True
    self._death_reason = REASON_LOGIN_FAILURE
    ...
except Exception:
    self._failed = True
    self._death_reason = REASON_CRASHED
    ...
```

`is_alive()` reads `self._failed` and `death_reason()` reads `self._death_reason`
independently, from the host thread, with no lock. Because these are two separate
attribute writes in the bot thread, a context switch can land between them (CPython's
GIL is released on a timer, not only at statement boundaries that "look" atomic). A host
polling both methods in that exact window would see `is_alive() == False` (dead) but
`death_reason() is None` (reason not yet known) — an inconsistent snapshot that
contradicts the "purely additive" contract documented for `death_reason()` (D-22/D-23:
the reason is supposed to always be resolvable once the bot is confirmed dead). This is
a narrow, low-probability race (a handful of bytecode instructions wide), not a crash,
but it is a real correctness gap in a field explicitly added for a host to branch
programmatically on.

**Fix:** Set the reason before flipping the liveness flag, so any host that observes
`is_alive() == False` is guaranteed to already see a populated `death_reason()`:
```python
except discord.LoginFailure:
    self._death_reason = REASON_LOGIN_FAILURE
    self._failed = True
    ...
except Exception:
    self._death_reason = REASON_CRASHED
    self._failed = True
    ...
```
(Reversing the race this way is sufficient because the only host-visible contract is "if
dead, reason must be present" — the reverse ordering, "reason set before dead," is
harmless since a host that hasn't yet seen `is_alive() == False` won't consult the reason
at all.)

## Info

### IN-01: Retry-pin exception handler mislabels a `Forbidden` as a cap failure

**File:** `yahir_reusable_bot/discord/gateway.py:212-218`

**Issue:** After evicting a stray, the retry is guarded only by
`except discord.HTTPException:`. Since `discord.Forbidden` subclasses `HTTPException`,
if the retried `await msg.pin()` fails with `Forbidden` (e.g., the permission was
revoked in the same narrow window as the original TOCTOU backstop is meant to catch), it
is caught here and logged as `"panel pin failed at cap even after evicting a stray"` —
which misattributes a genuine permission revocation to pin-cap exhaustion, and skips the
outer `discord.Forbidden` handler's distinct, more accurate CRITICAL message
(`"panel summon write forbidden (403) despite preflight"`). Cosmetic (log-message
accuracy only); does not change program behavior (the panel is still left unpinned
either way).

**Fix:** Add an explicit `except discord.Forbidden: raise` above the retry's
`except discord.HTTPException:`, mirroring the ordering already used for the first
`pin()` call, so a genuine permission revocation on the retry surfaces through the same
TOCTOU backstop as everywhere else.

### IN-02: A failed eviction-delete silently drops the stray from this call's cleanup

**File:** `yahir_reusable_bot/discord/gateway.py:204-211`

**Issue:** `stray = matches.pop(0)` removes the stray from `matches` before attempting
`await stray.delete()`. If that delete raises (caught and logged as a warning), the
stray is never actually deleted, and — because it was already popped — the subsequent
`for old in matches:` cleanup loop will not attempt it again in this call. It is not
lost forever (the next `summon_panel` invocation's `channel.pins()` scan will pick it up
again as an owned match), but this specific call ends with the stray still live and
unpinned-panel state slightly worse than intended (one extra orphaned owned message).
Untested — no fixture exercises an eviction-delete failure.

**Fix:** Not necessarily worth a structural change (self-heals on next summon), but
consider re-appending the stray to `matches` on delete failure so the existing per-item
delete loop retries it within the same call, and add a regression test for this branch.

### IN-03: Test leaves an unawaited-coroutine `RuntimeWarning` (test hygiene + narrow prod echo)

**File:** `tests/test_gateway.py:242-244` (`_FakeCloseableClient.close`), exercised by
`test_stop_does_not_raise_and_still_joins_when_loop_closes_mid_call`

**Issue:** `stop()` evaluates `self._client.close()` (creating a coroutine object) as
part of the argument to `asyncio.run_coroutine_threadsafe(...)`. In the TOCTOU race this
test reproduces, `run_coroutine_threadsafe` raises `RuntimeError` synchronously (the
loop is closed) *before* the coroutine is ever scheduled — so `_FakeCloseableClient
.close()`'s coroutine is created and then discarded unawaited, producing
`RuntimeWarning: coroutine 'close' was never awaited` at GC time. It does not fail the
suite (pytest doesn't fail on warnings here), but it is noise, and it faithfully mirrors
a real (if equally narrow) production side-effect: in a genuine closed-loop race, the
real `discord.Client.close()` coroutine is likewise created and discarded unawaited —
harmless given `stop()`'s already-documented best-effort/degrade-not-raise contract, but
worth being aware this warning is not test-only.

**Fix (optional, low priority):** Close the coroutine object explicitly on this specific
failure path to silence the warning without changing behavior:
```python
loop = self._loop
if loop is not None and loop.is_running():
    coro = self._client.close()
    try:
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        future.result(timeout=timeout)
    except Exception:
        coro.close()  # never scheduled (or already finished) — avoid GC warning
        _log.warning("bot client.close() did not complete cleanly")
```
Note this `coro.close()` is only safe to call unconditionally if `run_coroutine_threadsafe`
failed before scheduling; if the coroutine was already handed to the loop (e.g., the
exception instead came from `future.result()` timing out on a *running* task), calling
`.close()` on the original coroutine object is a no-op/no-risk since by that point the
task holds its own running frame, not the original object — verify this distinction
before applying, or scope the `coro.close()` call to only the `RuntimeError`
("Event loop is closed") case.

---

_Reviewed: 2026-07-27T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
