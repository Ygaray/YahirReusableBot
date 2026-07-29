# Phase 2: Latent runtime robustness - Pattern Map

**Mapped:** 2026-07-27
**Files analyzed:** 6 (3 modified source, 1 modified test, 2 new test)
**Analogs found:** 6 / 6 (all analogs are in-repo, in-file, or sibling-file precedents)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `yahir_reusable_bot/config/reload.py` (CFG-01, `reload()` PHASE-2 block) | service (orchestrator) | event-driven (rollback + best-effort hook fire) | same file: PHASE-1 fire-before-reraise (`:131-139`) + `_best_effort_hook` (`:312-327`) | exact (in-file precedent) |
| `yahir_reusable_bot/discord/gateway.py` (DISC-01, `BotThread`) | service/lifecycle | event-driven (thread death + constant-based reason) | `yahir_reusable_bot/reliability/retry.py:75-77` (`REASON_*` constants) | role-match (constant idiom, different module) |
| `yahir_reusable_bot/discord/gateway.py` (DISC-02, `summon_panel`) | service (CRUD over Discord API) | request-response (create/pin/delete sequence) | same function's existing per-write `discord.Forbidden` backstop (`:180-188`) | exact (in-file precedent, broadened) |
| `yahir_reusable_bot/discord/gateway.py` (DISC-03, `BotThread.stop`) | service/lifecycle | event-driven (cross-thread schedule + degrade) | same file: `_run`'s never-raise except discipline (`:262-271`) + existing `stop()` `except Exception` around `future.result` (`:249`) | exact (in-file precedent) |
| `yahir_reusable_bot/discord/selection.py` (DISC-04, `SelectedContext`) | model (in-memory cell) | transform (read/write accessor) | same file: existing `.value` property + `.set()` (`:44-51`) | exact (in-file precedent, additive method) |
| `tests/test_reload.py` (NEW) | test | request-response (unit, injected collaborators) | `tests/test_retry.py` (fixture use, docstring-first, self-proof note) + `tests/test_gateway.py` (module shape for gateway-adjacent hub code) | role-match (style precedent, no reload-specific test exists yet) |
| `tests/test_selection.py` (NEW) | test | transform (unit, pure in-memory) | `tests/test_retry.py` (`test_classification_is_pure_and_repeatable` — pure-object assertion style) | role-match |
| `tests/test_gateway.py` (MODIFIED — add DISC-01/02/03 tests) | test | request-response / event-driven | itself — `test_on_message_event_dispatches_to_injected_handler_not_itself` (docstring-first, synthetic double, single behavioral assertion) | exact (this file IS the precedent) |

## Pattern Assignments

### `yahir_reusable_bot/config/reload.py` (CFG-01)

**Analog:** same file, PHASE-1 block (`:131-139`) and `_best_effort_hook` (`:312-327`)

**Current PHASE-1 fire-before-reraise pattern to mirror** (lines 131-139):
```python
try:
    new_cfg = self._validate(path)
except Exception as exc:
    _log.error("reload rejected", reason=str(exc))
    # Post the rejection reason BEFORE re-raising (preserve the post-then-raise timing).
    # Best-effort: a hook failure is logged + swallowed; the ORIGINAL validation error
    # below is the one re-raised, keeping keep-old intact.
    self._best_effort_hook(self._on_rejected, exc, label="reload-rejected")
    raise
```

**Current PHASE-2 block that must change** (lines 144-158, verified at HEAD):
```python
old_cfg = self._holder.current()
self._holder.replace(new_cfg)
try:
    summary = self._reconcile()
except Exception:
    self._holder.replace(old_cfg)
    try:
        self._restore(old_cfg)
    except Exception:  # noqa: BLE001 — restore is best-effort; surface the real cause
        _log.exception(
            "reload rollback restore raised; original error re-raised"
        )
    _log.error("reload reconcile failed; rolled back to previous config")
    raise
```

**Fix shape (D-31):** change `except Exception:` to `except Exception as exc:` and add
`self._best_effort_hook(self._on_rejected, exc, label="reconcile-rolled-back")` right before
the `raise` at line 158 — same statement order as the PHASE-1 block (log → restore →
fire hook → raise). The rollback/restore ordering (`:150-157`) is byte-identical otherwise.

**Best-effort hook guard to reuse verbatim** (lines 312-327):
```python
@staticmethod
def _best_effort_hook(
    hook: Callable[[Any], None] | None, arg: Any, *, label: str
) -> None:
    """Invoke an optional hook best-effort: a None hook is a no-op; a raise is swallowed.

    A hook failure is logged (outcome-only) and swallowed so it can NEVER mask the engine's
    own result — the reject path's original error or the applied path's committed swap.
    """
    if hook is None:
        return
    try:
        hook(arg)
    except Exception:  # noqa: BLE001 — best-effort; never mask the engine result
        _log.warning(f"{label} hook failed; engine result unaffected")
```

**Error handling pattern:** bare `except Exception` catches, `_log.error`/`_log.exception`
before re-raise, never swallow the original triggering exception — only the best-effort
hook/restore calls get their own inner swallowing `except Exception`.

---

### `yahir_reusable_bot/discord/gateway.py` (DISC-01 — death-reason accessor)

**Analog:** `yahir_reusable_bot/reliability/retry.py:74-77` (module-level `REASON_*` constants)

**Constant idiom to follow** (retry.py:74-77):
```python
# Reason taxonomy consumed by Plans 03/04 when writing a briefing_missed alert.
REASON_TRANSIENT_EXHAUSTED = "transient_exhausted"
REASON_AUTH_FAILED = "auth_failed"
REASON_INTERNAL_ERROR = "internal_error"
```

**Site to modify — `_run`'s two except branches** (gateway.py:262-271, current):
```python
def _run(self) -> None:
    try:
        asyncio.run(self._amain())
    except discord.LoginFailure:
        self._failed = True
        _log.critical(
            "invalid Discord token; inbound bot disabled, scheduler unaffected"
        )
    except Exception:  # noqa: BLE001 — die alone; never crash the process
        self._failed = True
        _log.critical("inbound bot thread crashed; scheduler unaffected")
```

**Fix shape (D-22):** add module-level constants near the top of `gateway.py` (e.g.
`REASON_LOGIN_FAILURE = "login_failure"`, `REASON_CRASHED = "crashed"`), set
`self._death_reason = REASON_LOGIN_FAILURE` / `REASON_CRASHED` in the two branches above
(alongside the existing `self._failed = True`), initialize `self._death_reason: str | None
= None` next to the existing `self._failed = False` init (`:216`), and add a read accessor
(e.g. `death_reason() -> str | None`) placed next to `is_alive()` (`:233-240`). `is_alive()`
itself is unchanged.

**`is_alive()` accessor shape to mirror for the new accessor** (gateway.py:233-240):
```python
def is_alive(self) -> bool:
    """True unless the bot thread has died in ``_run``.
    ...
    """
    return not self._failed and self._thread.is_alive()
```

---

### `yahir_reusable_bot/discord/gateway.py` (DISC-02 — summon_panel per-item delete + headroom)

**Analog:** same function's existing sole `Forbidden` backstop (gateway.py:159-188, current)

**Current full function to modify:**
```python
try:
    matches = [m async for m in channel.pins() if is_owned(m)]
    msg = await channel.send(embed=idle_embed, view=panel_factory())
    await msg.pin()
    for old in matches:
        await old.delete()
    if not matches:
        await on_created()
    elif len(matches) > 1:
        await on_strays_cleaned(len(matches) - 1)
    else:
        await on_resummoned()
except discord.Forbidden:
    _log.critical(
        "panel summon write forbidden (403) despite preflight",
        channel_id=getattr(channel, "id", None),
    )
    return
```

**Fix shape:**
- D-26 (headroom): before `msg = await channel.send(...)`, if the channel is at the pin cap
  AND `len(matches) >= 2`, delete ONE owned stray first (freeing a slot; ≥1 panel still
  live — D-06 holds), then proceed to send+pin as before.
- D-25 (per-item delete): replace the bare `for old in matches: await old.delete()` loop with
  a per-item try/except:
  ```python
  for old in matches:
      try:
          await old.delete()
      except (discord.NotFound, discord.HTTPException, discord.Forbidden):
          _log.warning("stray panel delete failed; continuing", channel_id=...)
  ```
- D-24: create-before-delete ordering (`send` + `pin` before the delete loop) is preserved
  byte-identical — do not reverse it.
- The outer `except discord.Forbidden` stays as the TOCTOU backstop for the send/pin call
  only, since deletes now have their own per-item catch.
- D-27: on the residual foreign-pin-saturated case (pin() itself raises `HTTPException` at
  cap with no owned stray to evict), log CRITICAL and return rather than raising — same
  logging shape as the existing `Forbidden` backstop above.

**Error handling pattern:** async writes wrapped in narrow except tuples, `_log.critical`
with non-secret structured fields (`channel_id=getattr(channel, "id", None)`) — copy this
exact field-naming convention for any new CRITICAL log line.

---

### `yahir_reusable_bot/discord/gateway.py` (DISC-03 — stop() TOCTOU)

**Analog:** same file's existing `stop()` body (gateway.py:242-253, current) and `_run`'s
never-raise discipline (gateway.py:255-271)

**Current `stop()`:**
```python
def stop(self, timeout: float = 5.0) -> None:
    """Stop the bot: schedule ``client.close()`` cross-thread, then join."""
    loop = self._loop
    if loop is not None and loop.is_running():
        future = asyncio.run_coroutine_threadsafe(self._client.close(), loop)
        try:
            future.result(timeout=timeout)
        except Exception:  # noqa: BLE001 — close best-effort; still join below
            _log.warning("bot client.close() did not complete cleanly")
    self._thread.join(timeout=timeout)
    if self._thread.is_alive():
        _log.warning("bot thread did not stop within timeout")
```

**Fix shape (D-28):** move `run_coroutine_threadsafe(...)` INSIDE the existing `try`, add
`RuntimeError` to the except (either a combined `except (RuntimeError, Exception)`, or,
since `RuntimeError` is already an `Exception`, simply broaden the existing bare
`except Exception:` comment to name both failure modes — the class hierarchy means one
`except Exception:` block already structurally covers it; the fix is purely about *where*
the call is guarded, not adding a new except type):
```python
def stop(self, timeout: float = 5.0) -> None:
    loop = self._loop
    if loop is not None and loop.is_running():
        try:
            future = asyncio.run_coroutine_threadsafe(self._client.close(), loop)
            future.result(timeout=timeout)
        except Exception:  # noqa: BLE001 — close best-effort (incl. "loop already
            # stopped" RuntimeError on the TOCTOU race); still join below
            _log.warning("bot client.close() did not complete cleanly")
    self._thread.join(timeout=timeout)
    if self._thread.is_alive():
        _log.warning("bot thread did not stop within timeout")
```
`self._thread.join(timeout=timeout)` must ALWAYS be reached — this is the "never raise
AND still joins" success criterion from D-33/D-28; do not `return` early inside the new
except block.

---

### `yahir_reusable_bot/discord/selection.py` (DISC-04 — snapshot())

**Analog:** same file's existing `.value` property + `.set()` (selection.py:44-51)

**Current shape:**
```python
@property
def value(self) -> I:
    """Return the currently selected item."""
    return self._value

def set(self, value: I) -> None:
    """Rebind the held selection to ``value`` (called from the dropdown callback)."""
    self._value = value
```

**Fix shape (D-29):** add a `snapshot()` method returning `self._value`, semantically
identical to `.value` but named to carry the await-safety contract:
```python
def snapshot(self) -> I:
    """Read the current selection ONCE, before any ``await`` — see class docstring.

    Semantically identical to ``.value``; the distinct name carries the contract: capture
    into a local before yielding to the event loop, then use the local, never re-read
    ``.value`` (or call ``snapshot()`` again) after an intervening ``await``.
    """
    return self._value
```

**Docstring contract to extend (D-30):** append to the class docstring's existing
single-writer note (lines 15-22) a new paragraph naming the interleaved-await hazard (a
`Select` tap on the gateway loop during an off-loop `await` can rebind `._value` between two
reads) and prescribing `snapshot()`-before-`await` as the idiom — same "Concurrency
contract" heading style already used at lines 15-22.

---

### `tests/test_reload.py` (NEW)

**Analog:** `tests/test_retry.py` (fixture usage + self-proof note style) and
`tests/test_gateway.py` (docstring-first module header referencing the specific bug/finding)

**Module docstring pattern to follow** (test_gateway.py:1-7):
```python
"""Regression tests for the gateway client wiring (yahir_reusable_bot.discord.gateway).

Covers the P27-extraction recursion bug: ...
"""
from __future__ import annotations

import asyncio
```

**Test-function pattern (docstring-first, synthetic double, single assertion focus)** —
model on `test_retry.py`'s `test_exhausted_transient_escapes_as_itself_after_full_budget`
(lines 94-136): construct the `ReloadEngine` with all-injected collaborators (per
`reload.py:74-95`'s `__init__` signature), inject a fake `register_jobs` (or
`scheduler_engine.remove`) that raises to drive the PHASE-2 reconcile-failure path, and a
`fired: list = []`-style side-channel to assert `on_rejected` fired **exactly once** with
the reconcile exception (D-33). Assert `holder.current() == old_cfg` afterward (both-levels
habit, D-16). No mocking library — hand-write the fake collaborators as plain functions/
closures, matching `test_retry.py`'s `_always_hangs_up` closure style (lines 111-115).

**No shared fixture needed:** `ReloadEngine`'s collaborators (`validate`, `desired_jobs`,
`register_jobs`, `restore`, hooks, `scheduler_engine`) are all constructor-injected — no
`conftest.py` double is required unless `test_selection.py` independently needs the exact
same fake (unlikely; D-10 says do not add to `conftest.py` speculatively).

---

### `tests/test_selection.py` (NEW)

**Analog:** `tests/test_retry.py`'s `test_classification_is_pure_and_repeatable` (pure
in-memory object, no fixture, no I/O) and the DISC-04 REPL reproduction in RESEARCH.md.

**Pattern to follow (no discord.py import needed — Pitfall 4):**
```python
"""Regression tests for SelectedContext's await-safety contract (yahir_reusable_bot.discord.selection).

Covers H08: a value re-read via `.value` across an `await` can observe a concurrent
`.set()` that ran during the yield; `.snapshot()` captured before the `await` does not.
"""
from __future__ import annotations

import asyncio

from yahir_reusable_bot.discord.selection import SelectedContext


def test_snapshot_is_stable_across_interleaved_set_but_value_reflects_it():
    """A snapshot() taken before an await is unaffected by a concurrent set() during
    the yield; a plain .value re-read after the same yield reflects the write."""
    cell = SelectedContext("A")

    async def rebind_during_yield():
        await asyncio.sleep(0)
        cell.set("B")

    async def read_via_snapshot():
        snap = cell.snapshot()
        await asyncio.sleep(0)
        return snap

    async def read_via_value():
        await asyncio.sleep(0)
        return cell.value

    async def run():
        ...  # interleave rebind + both readers via asyncio.gather / create_task

    ...
```
Both halves of D-33's assertion must live in the SAME test (per RESEARCH.md's DISC-04
under-sampling risk): `snapshot()`-captured value stable AND `.value` re-read reflects the
write — do not split across two tests.

---

### `tests/test_gateway.py` (MODIFIED — DISC-01/02/03 additions)

**Analog:** itself — `test_on_message_event_dispatches_to_injected_handler_not_itself`
(lines 17-30) is the exact shape to replicate: one docstring naming the specific bug, one
synthetic double, one behavioral assertion.

**DISC-01 test shape:** a fake `discord.Client`-shaped double whose `start()` coroutine
raises `discord.LoginFailure()` (no required constructor args — confirmed in RESEARCH.md),
with `async def __aenter__`/`__aexit__` support (since `_amain` does `async with
self._client:`). Construct `BotThread(token, client=fake_client)`, call `._run()` directly
(no real thread needed — `_run` is a plain sync method), then assert `bot.is_alive() is
False` AND `bot.death_reason() == "login_failure"`. A second test with a fake client whose
`start()` raises a generic `Exception` asserts `death_reason() == "crashed"`.

**DISC-02 test shape (two fixtures per D-33 — do not conflate):**
(a) a fake channel whose `.pins()` is an async generator yielding 2 owned-matching fake
messages, where the FIRST fake message's `.delete()` raises `discord.NotFound`
(`discord.NotFound` needs a fake `response`+`message` per its constructor — check
`discord/errors.py` signature or construct via a minimal stub) → assert the SECOND
message's `.delete()` still ran and net pinned state is 1 panel.
(b) a fake channel where `msg.pin()` raises `discord.HTTPException` (cap simulation) and
≥2 owned matches exist → assert one stray was deleted BEFORE send+pin (headroom reserved)
so the retry-in-fix `pin()` (or the fresh panel's pin) ultimately succeeds.

**DISC-03 test shape:** a fake loop object whose `is_running()` returns `True` but whose
use in `asyncio.run_coroutine_threadsafe` context needs the real stdlib call to raise
`RuntimeError("Event loop is closed")` — per RESEARCH.md Pitfall 3, actually pass a REAL
closed `asyncio.new_event_loop()` (created + immediately `.close()`d) as `bot._loop`, since
`run_coroutine_threadsafe` is a free function that will raise `RuntimeError` against any
closed loop deterministically, with zero timing/flakiness. Assert `bot.stop()` returns
(no raise) AND `bot._thread.join` still ran (assert via a fake `threading.Thread`-shaped
double whose `.join()` sets a `joined: list = []` marker, OR construct with a real
already-finished thread and assert `is_alive()` is False afterward).

## Shared Patterns

### Best-effort hook swallow (CFG-01)
**Source:** `yahir_reusable_bot/config/reload.py:312-327` (`_best_effort_hook`)
**Apply to:** Only `reload.py`'s PHASE-2 block — this is the one call site to add; the
static method itself needs no change.

### Module-level `REASON_*` string constants (DISC-01)
**Source:** `yahir_reusable_bot/reliability/retry.py:74-77`
**Apply to:** `gateway.py`'s new death-reason constants — same bare-string idiom (no enum,
no `Literal`), same location (near top of module, above the class/function that uses them).

### Non-secret structured CRITICAL/WARNING logging
**Source:** `yahir_reusable_bot/discord/gateway.py:184-188` (`summon_panel`'s existing
`Forbidden` backstop: `_log.critical(..., channel_id=getattr(channel, "id", None))`)
**Apply to:** Any new CRITICAL log line in DISC-01 (death-reason) and DISC-02
(pin-cap-saturated residual, D-27) — structured fields only, never the bot token.

### Docstring-carries-decision-rationale
**Source:** every module in this repo (`reload.py:1-41`, `gateway.py:1-28`,
`selection.py:1-22`) — module and function docstrings state the D-XX rationale inline, not
just in commit messages.
**Apply to:** All three modified source files — the D-23/D-27/D-30 contracts belong in the
fixed functions' docstrings.

### Docstring-first, synthetic-double, single-behavioral-assertion test shape
**Source:** `tests/test_gateway.py:17-30`, `tests/test_retry.py:94-136`
**Apply to:** All new/modified test functions across `test_reload.py`, `test_selection.py`,
and the `test_gateway.py` additions — no mocking library, hand-written fake objects,
`pytest.raises()` where appropriate (Phase 1 established both patterns as acceptable).

## No Analog Found

None — all six files in scope have a strong in-repo analog (either the same file's existing
adjacent code, or a clear sibling-module precedent for the idiom being extended).

## Metadata

**Analog search scope:** `yahir_reusable_bot/config/`, `yahir_reusable_bot/discord/`,
`yahir_reusable_bot/reliability/`, `tests/`
**Files scanned:** `reload.py`, `gateway.py`, `selection.py`, `retry.py`, `test_gateway.py`,
`test_retry.py`, `conftest.py` (7 files, full reads — all ≤ 400 lines, no grep-first needed)
**Pattern extraction date:** 2026-07-27
