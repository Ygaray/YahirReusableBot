# Phase 2: Latent runtime robustness - Research

**Researched:** 2026-07-27
**Domain:** Discord gateway lifecycle (discord.py 2.7.1 internals), config-reload hook semantics, asyncio cross-thread scheduling, single-writer in-memory concurrency
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Decision numbering continues the milestone-wide sequence (Phase 1 reached D-20); Phase 2 starts at D-21.

**Gateway liveness/reconnect contract (DISC-01)**
- **D-21:** The ROADMAP's open "retry/backoff contract" resolves to **liveness-only — the hub adds NO reconnect retry beyond discord.py's own.** `_amain`'s single `client.start(token)` stays; discord.py's default `reconnect=True` already runs an `ExponentialBackoff` for every *recoverable* disconnect. The disconnects that actually reach thread-death (`_run`'s except handlers) are the ones discord.py **deliberately refuses** to retry — `LoginFailure`, disallowed/privileged intents, auth-close (4004/4014). A hub-side reconnect wrapper would hot-loop those *identical non-recoverable* failures straight into a Discord rate-limit/ban. Preserves BotThread's non-owning + failure-isolation design ("die alone; never crash the process").
- **D-22:** Add a **death-reason** signal to `BotThread` so the host park-loop can branch **programmatically**, not just scrape a CRITICAL log. Minimal, following the module's existing constant idiom (`REASON_*` in `retry.py:75`): at least `login_failure` (from the `discord.LoginFailure` handler `:264`) and `crashed` (generic handler `:269`); a clean-exit reason is optional if `asyncio.run` returns without raising. Exposed via a read accessor alongside `is_alive()`. `is_alive()` semantics (`:233-240`) are **unchanged** — the reason is purely additive.
- **D-23:** The contract is made explicit in the docstring: **`is_alive()` is the documented signal the host park-loop consults to decide respawn/alert/exit; the hub never respawns.** Rejected: the bounded-reconnect-wrapper (duplicates discord.py, ban risk on the exact failures that trigger it) and the hybrid-injected-policy (a plug point with no rule-of-three demand).

**Panel re-summon atomicity (DISC-02)**
- **D-24:** **Create-before-delete is preserved (D-06 invariant holds).** Rejected: the report's "delete-then-pin" — it reverses the no-zero-panel-window ordering and, on a send/pin failure, would leave **zero** panels, worse than the current 2+-panels bug.
- **D-25:** **Per-item delete error handling broadened.** Each `old.delete()` (`:171-172`) gets its own `try/except (discord.NotFound, discord.HTTPException, discord.Forbidden)` → log + continue, so one failed delete never aborts the remaining deletes (closes the CONFIRMED "2+ live panels" mode). The outer sole-`Forbidden` block (`:180`) is narrowed/relocated so a preflight-revoked send/pin is still handled without swallowing the per-item cases.
- **D-26:** **Reserve pin headroom for the pin cap.** When the channel is at the pin cap AND ≥2 owned panels exist, delete one owned stray *before* send+pin (still leaves ≥1 live panel, so D-06's no-zero-window holds), freeing a slot so the fresh `pin()` (`:167`) succeeds; then delete the rest. This is the only branch that satisfies the success criterion's "cannot leave a fresh-but-unpinned panel."
- **D-27:** **Residual out-of-authority case: document, don't chase.** A channel saturated with foreign (non-owned) pins cannot be made room for without evicting pins the hub does not own; in that case send the fresh panel + emit a **loud CRITICAL** rather than silently leaving it unpinned. Stated as a docstring limitation.

**stop() TOCTOU (DISC-03 — clear-cut, folded without discussion)**
- **D-28:** In `stop()` (`:242-253`), move `run_coroutine_threadsafe` (`:246`) **inside** a `try` and catch `RuntimeError` ("Event loop is closed") as "loop already stopped" → log + fall through to `join`. The `loop.is_running()` check (`:245`) stays as a fast path but is no longer relied on as a guarantee. `stop()` must never raise.

**Selection snapshot API (DISC-04)**
- **D-29:** Add a `snapshot()` read-once method to `SelectedContext` (`:33-51`) returning the current `_value` — semantically identical to `.value` but **named to carry the contract**: capture once into a local before any `await`; never re-read `.value` across an `await`. Contract + API only per REQ scope — the consumer-side `wiring.py` re-read is **not** touched here.
- **D-30:** **Await-safety contract made explicit** in the class docstring — extend the single-writer note (`:15-22`) to state the interleaved-await hazard and prescribe `snapshot()`-before-`await` as the idiom. Rejected: the immutable-handle / context-manager guard (over-built for a cosmetic single-writer race).

**Reload-reject alert semantics (CFG-01)**
- **D-31:** The PHASE-2 reconcile-failure path (`reload.py:146-158`) fires `_best_effort_hook(self._on_rejected, exc, label="reconcile-rolled-back")` **before** the `raise` at `:158` — change `except Exception:` to `except Exception as exc:`. Mirrors PHASE-1's fire-before-reraise (`:138`). The rollback/restore ordering (`:150-157`) is otherwise byte-identical; the ORIGINAL reconcile error is still the one re-raised.
- **D-32:** **Same hook, no new public surface.** Rejected: a phase/reason enum or a second `on_reconcile_failed` hook.

**RED-first regression coverage (per finding, D-13 two-commit idiom)**
- **D-33:** Each fix ships its RED-first test against **hub-assertable observables**:
  - **DISC-01:** a fake client whose `start()` raises `discord.LoginFailure` → after `_run`, assert `is_alive()` is False AND the death reason reads `login_failure`; a generic-crash variant → reason `crashed`.
  - **DISC-02:** (a) fake `channel.pins()` yielding 2 owned matches where the first `old.delete()` raises `NotFound` → assert BOTH remaining deletes still ran and net state is one live pinned panel; (b) fake channel at the pin cap → assert the fresh panel ends up pinned (headroom reserved).
  - **DISC-03:** a fake loop reporting `is_running()` True but raising `RuntimeError` on `run_coroutine_threadsafe` → assert `stop()` returns without raising and still joins.
  - **DISC-04:** assert a value captured via `snapshot()` is unchanged after an interleaved `set()`, while a re-read of `.value` reflects the write.
  - **CFG-01:** an injected `register_jobs` (or scheduler `remove`) that raises drives reconcile failure → assert `on_rejected` fired **exactly once** with the reconcile exception AND the holder rolled back to `old_cfg` (both levels).

### Claude's Discretion
- Exact death-reason representation (str constants vs enum vs `Literal`) within D-22's minimal bound — follow the module's `REASON_*` constant style.
- Whether the five fixes ship as one plan or split. They touch disjoint files, but `gateway.py` holds three findings (DISC-01/02/03) — grouping by file is natural. Sequence so a deliberately-RED test never overlaps a sibling's full-suite gate.
- Exact test-function names and whether `pytest.raises()` is used.
- Exact shapes of the synthetic inline doubles (fake channel/message/client/loop) per the no-mocking-library house style; grow `tests/conftest.py` only when ≥2 test files actually share a double.
- Exact docstring wording for the fixed functions, provided the D-23/D-27/D-30 contracts are stated.

### Deferred Ideas (OUT OF SCOPE)
- **Hybrid injected reconnect policy (DISC-01 Option 3)** — an optional injected `on_death` / reconnect-policy callable so a consumer can opt into hub-driven auto-respawn. Deferred: no current consumer needs it.
- **Consumer-side `wiring.py` re-read fix (DISC-04's observed defect)** — explicitly out of hub scope; lands in WeatherBot at repin.
- **Immutable/enforced snapshot handle for `SelectedContext`** — rejected now (D-30) as over-built for a cosmetic race.
- **Refresh `.planning/codebase/TESTING.md`** — still stale re: the conftest Phase 1 added; housekeeping, not phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CFG-01 (H03) | PHASE-2 reconcile failure fires `on_rejected` before re-raising | Confirmed by direct source read (`reload.py:146-158`, `:312-327`): `_best_effort_hook` swallows hook raises unconditionally, so firing it before `raise` cannot mask the original reconcile exception. See "CFG-01: `_best_effort_hook` masking-safety" below. |
| DISC-01 (H04) | Non-recoverable gateway disconnect leaves an operator-visible signal | Confirmed by reading `discord/client.py::connect()` and `discord/gateway.py::_can_handle_close()` in the installed 2.7.1 package: the exact exception classes that escape `connect()`/`start()` are `LoginFailure` (from `login()`) and `ConnectionClosed`/`PrivilegedIntentsRequired` for close codes `{4004, 4010, 4011, 4012, 4013, 4014}` — all of which discord.py's own retry loop deliberately does not retry. See "DISC-01: verified non-recoverable disconnect classes" below. |
| DISC-02 (H05) | Re-summon never leaves 2+ live panels or a fresh-but-unpinned panel | Confirmed `Message.pin()` raises `discord.HTTPException` at the pin cap, `NotFound`/`Forbidden` are both `HTTPException` subclasses, and `channel.pins()` is a paginated async iterator (default `limit=50`) as of discord.py 2.6+. See "DISC-02: pin/delete exception hierarchy and cap behavior" below. |
| DISC-03 (H07) | `stop()` never raises `RuntimeError` on a mid-call loop close | Reproduced live in a Python 3.13 REPL: `asyncio.run_coroutine_threadsafe` against a closed loop raises `RuntimeError("Event loop is closed")` — exactly the TOCTOU D-28 guards against. See "DISC-03: reproduced TOCTOU" below. |
| DISC-04 (H08) | `SelectedContext` await-safety contract explicit + snapshot-safe consume | Reproduced live: a plain in-memory cell re-read via `.value` after an `await` observes a concurrent `.set()` that ran during the yield, while a value captured via `.snapshot()` before the `await` does not. See "DISC-04: reproduced interleaved-await hazard" below. |
| GATE-01 | Full suite + import-hygiene gates stay green | No new imports/dependencies introduced by any of the five fixes (verified against `pyproject.toml` — no dependency changes needed); `test_import_hygiene.py`'s `grimp` graph and litmus gates are unaffected by internal control-flow changes in `reload.py`/`gateway.py`/`selection.py`. |
</phase_requirements>

## Summary

All five findings are confirmed, in this session, against the **installed discord.py 2.7.1
package source** (`.venv/lib/python3.13/site-packages/discord/{client,gateway,errors,message,abc}.py`)
and by **live reproduction** in a Python 3.13 REPL — not from training-data recall. This is
stronger verification than a documentation lookup: the exact behavior of the pinned library
version running in this repo's own venv was read and exercised directly.

The headline result is that **D-21's linchpin claim is correct, not merely convenient**:
`discord.Client.connect()`'s own retry loop (`ExponentialBackoff` + resume-on-disconnect)
already retries every recoverable disconnect, and the *only* paths that escape `connect()`/
`start()` as raised exceptions are `LoginFailure` (bad token, raised from `login()`) and
`ConnectionClosed`/`PrivilegedIntentsRequired` for the specific close codes Discord's gateway
uses to signal an unrecoverable session state (`4004` auth failed, `4010`-`4013` shard/intent
errors, `4014` disallowed privileged intents). `gateway.py`'s `_run` except handlers
(`discord.LoginFailure` specifically, then a generic `except Exception`) are exactly — not
approximately — the catch-alls for these non-retryable exits. A hub-side reconnect wrapper
sitting outside `client.start()` would therefore retry precisely the failures discord.py
itself refuses to retry, which is the exact hot-loop/ban risk D-21 names.

One correction surfaced that CONTEXT.md's D-26 should account for at plan time: the discord.py
2.7.1 **docstring** for `Message.pin()` claims the HTTPException-triggering cap is "more than
250 pinned messages," but Discord's own documented JSON error-code taxonomy (error `30003`,
sourced via discord.js's generated error-code reference, which mirrors the same Discord API)
states the cap is **50**. This is flagged as `[ASSUMED]` (see Assumptions Log) — it does not
change the *shape* of the fix (catch `HTTPException` generically, never branch on the exact
cap number), but the planner should not hardcode "250" anywhere in code, docstrings, or test
fixtures purporting to represent "the pin cap." A synthetic test double for "at the pin cap"
should just make `pin()` raise `discord.HTTPException` — it does not need to encode a specific
count either way.

**Primary recommendation:** Implement all five fixes as pure internal control-flow changes to
already-injectable seams (no new dependencies, no new test infrastructure beyond a small
`tests/test_reload.py` and `tests/test_selection.py`); write each RED-first test against the
hub-assertable observable named in D-33, using the exact exception constructors and attribute
names confirmed against the installed discord.py 2.7.1 package (see Code Examples).

## Architectural Responsibility Map

This project is not web-tiered (browser/SSR/API/CDN); its architecture is **hub library →
consumer composition root → external platform (Discord API)**. Tiers below are adapted to that
shape.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Reload-rejection alerting (CFG-01) | Hub library (`ReloadEngine.reload`) | Consumer composition root (`on_rejected` callback body) | Hub owns firing the hook at the correct control-flow point (before re-raise, best-effort); the consumer owns what the hook *does* (post a Discord alert). |
| Gateway liveness + death-reason signal (DISC-01) | Hub library (`BotThread`) | Consumer host (park-loop polling `is_alive()`/death-reason) | Hub owns detecting and exposing a non-recoverable death programmatically; the consumer owns respawn/alert/exit *policy* — the hub never respawns (D-23). |
| Panel re-summon atomicity (DISC-02) | Hub library (`summon_panel`) | External platform (Discord's pin-cap enforcement) | Hub owns ordering + per-item error handling; Discord's API is the resource-limit authority the hub must degrade gracefully against (D-26/D-27). |
| `stop()` degrade-not-raise (DISC-03) | Hub library (`BotThread.stop`) | — | Purely internal thread/event-loop lifecycle; no external or consumer-facing tier involved. |
| `SelectedContext` await-safety contract (DISC-04) | Hub library (`SelectedContext` API + docstring) | Consumer composition root (`wiring.py`'s actual re-read bug) | Hub owns the contract + a snapshot-safe primitive; the consumer owns actually adopting it — the observed defect's fix site is consumer-side and out of scope here. |

## Project Constraints (from CLAUDE.md)

- **One-way dependency:** no file under `yahir_reusable_bot/` may import from `weatherbot` or
  any consumer package. None of the five fixes touch imports; `test_import_hygiene.py`'s grimp
  gate must stay green (already true — no new imports needed).
- **No domain nouns:** all five fixes stay in already-generic modules (`config/reload.py`,
  `discord/gateway.py`, `discord/selection.py`); no new public symbol may name a domain concept.
  `REASON_*`-style death-reason constants (e.g. `login_failure`, `crashed`) are generic Discord/
  process-lifecycle vocabulary, not domain nouns — consistent with the existing `retry.py`
  `REASON_*` precedent.
- **`discord.py==2.7.1` exact pin:** every fact in this document was verified against the
  *installed* 2.7.1 package, not a newer/older version. Do not consult discord.py's `master`
  branch docs or a different pinned version for this phase.
- **Toolchain:** Python 3.12+, `uv`, no console script shipped by this repo. Dev deps already
  include `pytest>=9.0.3`, `ruff`, `grimp>=3.14` — no new dev dependency is needed for this
  phase's tests (no `pytest-asyncio`; the repo's convention is `asyncio.run()` inline).
- **No CI:** "green" means `uv run pytest` run locally by the executor; RED-first proof is via
  git two-commit history (D-13), not a pipeline gate.
- **Human-gated close-out:** do not plan or perform the version bump / tag / repin / deploy
  steps (ECOSYSTEM.md §3) — surface them for confirmation only, after Phase 4.

## Standard Stack

No new libraries are introduced by this phase. All five fixes are internal control-flow changes
using already-pinned dependencies.

### Core (unchanged, pre-existing pins — verified against `pyproject.toml`)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `discord.py` | `==2.7.1` (exact pin) | Gateway client, panel/pin API | Wire-contract exact pin (persistent-view `custom_id`); verified installed via `uv run python -c "import discord; print(discord.__version__)"` → `2.7.1` `[VERIFIED: installed package]` |
| `structlog` | `>=26.1.0` | Structured logging (death-reason log fields, reject-reason logging) | Already the repo's sole logging library; no new call site changes its shape |
| `tenacity` | `>=9.1.4` | (Unrelated to this phase's fixes; listed for completeness) | N/A this phase |
| `httpx` | `>=0.28.1` | (Unrelated to this phase's fixes; listed for completeness) | N/A this phase |

### Dev (unchanged, pre-existing pins)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | `>=9.0.3` | Test runner | All five RED-first regressions |
| `grimp` | `>=3.14` | Import-hygiene gate (GATE-01) | Must stay green; unaffected by this phase's internal changes |

**Installation:** None required — no `pyproject.toml` change for this phase.

**Version verification:** `discord.py==2.7.1` confirmed installed via direct import in this
session (`uv run python -c "import discord; print(discord.__version__)"` → `2.7.1`). No other
package versions need re-verification; this phase adds none.

## Package Legitimacy Audit

**Not applicable this phase.** No external packages are introduced, upgraded, or newly imported
by any of the five fixes (CFG-01, DISC-01..04) or their tests. All work happens inside
already-vetted, already-pinned modules (`discord.py==2.7.1`, `structlog`, `pytest`, `grimp`) —
no `npm view` / `pip index versions` / registry check is needed. If the planner discovers a need
for a new package during planning (none anticipated), run the Package Legitimacy Gate protocol
against it before adding it to any plan.

## Architecture Patterns

### System Architecture Diagram

Three independent runtime flows this phase touches, shown as data/control flow (not file
listings):

```
(A) Config reload path (CFG-01)
  file-watch thread / signal handler
        │  (flag-set only, D-05 precedent)
        ▼
  service_pending(path) on host's main thread
        │
        ▼
  ReloadEngine.reload(path)
        │
        ├─ PHASE 1: validate(path) ──raises──▶ on_rejected hook (fire) ──▶ raise  [unchanged]
        │
        └─ PHASE 2: holder.replace(new) → _reconcile()
                          │
                          ├─ success ──▶ on_applied hook (fire) ──▶ return
                          │
                          └─ raises ──▶ holder.replace(old_cfg) → restore(old_cfg)
                                         │
                                         ▼
                                 [FIX] on_rejected hook (fire) ◀── currently MISSING
                                         │
                                         ▼
                                       raise (ORIGINAL reconcile exception, unmasked)

(B) Gateway lifecycle path (DISC-01, DISC-03)
  BotThread.start() → _run() [own thread]
        │
        ▼
  asyncio.run(_amain())
        │
        ▼
  async with client: await client.start(token)
        │
        ▼
  discord.Client.connect()  ── internal loop ──┐
        │                                       │ ExponentialBackoff + resume
        │  recoverable disconnect (OSError,     │ (discord.py retries these itself —
        │  most ConnectionClosed codes, etc.)   │  NO hub involvement, D-21)
        │◀──────────────────────────────────────┘
        │
        │  NON-recoverable: LoginFailure (login()) OR
        │  ConnectionClosed/PrivilegedIntentsRequired for codes
        │  {4004, 4010, 4011, 4012, 4013, 4014}
        ▼
  _run()'s except handlers
        │
        ├─ except discord.LoginFailure  → _failed=True, [FIX] reason="login_failure"
        └─ except Exception (generic)   → _failed=True, [FIX] reason="crashed"
        │
        ▼
  host park-loop polls is_alive() / [NEW] death_reason accessor → respawn/alert/exit (host policy)

  BotThread.stop() [called from host thread, cross-thread]
        │
        loop.is_running() check (fast path only, not a guarantee)
        │
        ▼
  [FIX] try: run_coroutine_threadsafe(client.close(), loop)
        except RuntimeError ("Event loop is closed"):  ← TOCTOU: loop closed between check and call
              log "loop already stopped" → fall through
        │
        ▼
  self._thread.join(timeout)   [ALWAYS reached — stop() never raises]

(C) Panel re-summon path (DISC-02)
  summon_panel()
        │
        ▼
  matches = [m async for m in channel.pins() if is_owned(m)]   (async iterator, default limit=50)
        │
        ├─ [FIX] at pin cap AND len(matches) >= 2:
        │        delete ONE owned stray FIRST (frees a slot, still ≥1 live panel — D-06 holds)
        │
        ▼
  msg = await channel.send(...); await msg.pin()     (create-before-delete, D-24 preserved)
        │
        ├─ discord.Forbidden (TOCTOU backstop) → CRITICAL log, return
        │
        ▼
  for old in matches:
        [FIX] try: await old.delete()
              except (NotFound, HTTPException, Forbidden): log + continue  (per-item, D-25)
        │
        ▼
  [residual] foreign-pin-saturated channel → send succeeds but fresh panel unpinned
             → [FIX] loud CRITICAL (documented limitation, D-27 — not chased)

(D) Selection await-safety (DISC-04)
  on_select callback (gateway loop)  ──▶  SelectedContext.set(new_item)
                                                  │  (can interleave with any command
                                                  │   handler's await, since both run on
                                                  │   the same single-threaded loop)
                                                  ▼
  command button handler:
        [BUGGY]  await something(); read .value        → may observe a POST-await rebind
        [FIX]    snap = .snapshot(); await something(); use snap  → stable pre-await value
```

### Recommended Project Structure

No new directories. New/changed test files only:
```
tests/
├── test_gateway.py     # grows: DISC-01 death-reason tests, DISC-02 summon tests, DISC-03 stop() tests
├── test_reload.py      # NEW — first coverage for reload.py (CFG-01)
├── test_selection.py   # NEW — first coverage for selection.py (DISC-04)
└── conftest.py         # grows ONLY if a double is shared across ≥2 of the above files (D-10)
```

### Pattern 1: Fire-before-reraise best-effort hook (CFG-01)
**What:** Invoke an optional side-effect hook immediately before re-raising the exception that
triggered a rollback, using a helper that unconditionally swallows the hook's own exceptions.
**When to use:** Any "notify then propagate" path where the notification must never be allowed
to suppress or replace the original failure.
**Example (verified against installed source, `config/reload.py:131-139` — the existing PHASE-1
precedent this phase's fix mirrors):**
```python
# Source: yahir_reusable_bot/config/reload.py:131-139 (PHASE-1, already correct)
try:
    new_cfg = self._validate(path)
except Exception as exc:
    _log.error("reload rejected", reason=str(exc))
    self._best_effort_hook(self._on_rejected, exc, label="reload-rejected")
    raise

# yahir_reusable_bot/config/reload.py:312-327 — the guard that makes this safe
@staticmethod
def _best_effort_hook(hook, arg, *, label):
    if hook is None:
        return
    try:
        hook(arg)
    except Exception:  # noqa: BLE001 — best-effort; never mask the engine result
        _log.warning(f"{label} hook failed; engine result unaffected")
```
The PHASE-2 fix (CFG-01) is the same pattern applied at `reload.py:146-158`'s `except Exception:`
block — change to `except Exception as exc:` and call
`self._best_effort_hook(self._on_rejected, exc, label="reconcile-rolled-back")` before the
existing `raise` at `:158`.

### Pattern 2: Death-reason accessor alongside a liveness flag (DISC-01)
**What:** A boolean liveness check plus a separate, additive string/enum reason accessor set at
each distinct failure branch — following the module's own `REASON_*` string-constant idiom.
**When to use:** When a caller needs to branch on *why* something died, not just *whether*.
**Example (verified against `reliability/retry.py:75-77`, the precedent D-22 explicitly follows):**
```python
# Source: yahir_reusable_bot/reliability/retry.py:75-77
REASON_TRANSIENT_EXHAUSTED = "transient_exhausted"
REASON_AUTH_FAILED = "auth_failed"
REASON_INTERNAL_ERROR = "internal_error"
```
Applied to `gateway.py`, the minimal analog is two module-level constants (e.g.
`REASON_LOGIN_FAILURE = "login_failure"`, `REASON_CRASHED = "crashed"`) set in `_run`'s two
except branches (`:264` and `:269`) and exposed via a read accessor (e.g.
`death_reason() -> str | None`) alongside the existing `is_alive()` (`:233-240`).

### Anti-Patterns to Avoid
- **Hub-side reconnect/backoff wrapper around `client.start()`:** Verified against
  `discord/client.py::connect()` — discord.py already retries every *recoverable* disconnect
  with `ExponentialBackoff`. The only exceptions that escape are the ones discord.py explicitly
  decided are not worth retrying (bad token, disallowed intents, auth-close). Wrapping
  `client.start()` in an outer retry loop would re-attempt those same calls, immediately hitting
  the same non-recoverable close code again — a hot loop that risks a platform-level rate-limit
  or IP/token ban. This is D-21's rationale, now confirmed against source rather than assumed.
- **Hardcoding a specific pin-cap number in code, docstrings, or test fixtures:** The exact cap
  is unresolved between discord.py's bundled docstring (implies 250) and Discord's documented
  JSON error code 30003 (implies 50) — see Assumptions Log. Catch `discord.HTTPException`
  generically (per D-26); do not assert a specific count in production code.
- **A `threading.Lock`/`asyncio.Lock` around `SelectedContext`:** The hazard (D-30) is a
  single-threaded interleaving problem (two coroutines on the same event loop), not a
  cross-thread race — a lock adds ceremony without changing the fix, which is "capture before
  you yield," not "serialize access."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Recoverable gateway disconnect retry | A custom backoff/retry wrapper around `client.start()` | discord.py's own `ExponentialBackoff` + `connect()` resume loop (already active via default `reconnect=True`) | Verified: it already handles `OSError`, most `ConnectionClosed` codes, `aiohttp.ClientError`, timeouts, and gateway-request reconnects. Re-implementing this duplicates working logic and cannot distinguish recoverable from non-recoverable better than discord.py already does. |
| "Is the channel at its pin cap" tracking | A cached pin-count variable updated on every send/delete | Re-derive from the live `channel.pins()` scan each `summon_panel()` call (already the existing pattern) | Discord's pin state is authoritative server-side; a locally cached counter can drift (another process/human pinning/unpinning) and would reintroduce exactly the kind of stale-state bug this phase is fixing elsewhere. |
| Cross-coroutine value staleness guard for `SelectedContext` | A lock, a context manager, or an immutable frozen snapshot type | The `snapshot()` method (D-29) — capture once, use the local | The race is single-writer/single-loop interleaving, not concurrent mutation; a lock would serialize callbacks on the SAME event loop for no benefit (nothing is running in parallel — everything is cooperatively scheduled). |

**Key insight:** Every "don't hand-roll" item in this phase resolves to *use what's already
there and already correct* — discord.py's backoff, the live Discord API as the source of truth
for pin state, and a plain read-before-yield idiom instead of new synchronization primitives.
The fixes are narrow because the underlying platform/library already does the hard part
correctly; the bugs are all in the hub's own glue code around it (missing hook fire, missing
per-item catch, unguarded cross-thread call, unguarded stale value).

## Common Pitfalls

### Pitfall 1: Assuming discord.py's `except Exception` handler in `_run` needs new exception-specific branches
**What goes wrong:** A planner might assume DISC-01 requires catching `discord.ConnectionClosed`
or `discord.PrivilegedIntentsRequired` specifically to set a death reason.
**Why it happens:** Those exception names show up in discord.py's `connect()` source and look
like they need their own `except` clause.
**How to avoid:** They already fall through to `_run`'s existing generic `except Exception:`
branch (neither is a `discord.LoginFailure`) — D-22's minimal bound ("at least `login_failure`
and `crashed`") already accounts for this by collapsing them into `crashed`. Only add a more
granular branch if the plan explicitly wants a third reason value; it is not required by the
success criteria.
**Warning signs:** A plan task that adds an `except discord.PrivilegedIntentsRequired:` branch
without an explicit decision to add a third death-reason value.

### Pitfall 2: Believing `NotFound`/`Forbidden` need separate handling from `HTTPException`
**What goes wrong:** Writing three separate `except` blocks with different bodies for
`discord.NotFound`, `discord.Forbidden`, `discord.HTTPException` when one `except
discord.HTTPException:` would already catch all three (verified: both `NotFound` and
`Forbidden` subclass `HTTPException` in `discord/errors.py`).
**Why it happens:** D-25's decision text lists all three names explicitly (for auditability/
log-clarity), which can read as "they need distinct except clauses."
**How to avoid:** A single `except (discord.NotFound, discord.HTTPException, discord.Forbidden):`
tuple (as D-25 specifies) is fine and arguably clearer for future readers even though
`HTTPException` alone is a strict superset — just don't add per-type *branching logic* unless a
requirement actually needs different behavior per type (none of the five findings do).
**Warning signs:** Three different log messages or three different control-flow outcomes for
what is functionally "the delete failed, log and continue" in every case.

### Pitfall 3: Testing the TOCTOU race by mocking `is_running()` to return True then closing the real loop mid-test
**What goes wrong:** Trying to actually reproduce the timing race (start a real thread, close
the loop at just the right moment) makes the test flaky and slow.
**Why it happens:** "TOCTOU" sounds like it needs real concurrency to prove.
**How to avoid:** The confirmed mechanism doesn't require timing at all — a fake loop object
whose `is_running()` returns `True` (satisfying the fast-path check) but whose
`run_coroutine_threadsafe`-adjacent path raises `RuntimeError("Event loop is closed")`
deterministically reproduces the exact failure mode with zero flakiness. (Verified via direct
REPL reproduction: `asyncio.run_coroutine_threadsafe` against an actually-closed loop raises
this exact `RuntimeError` with this exact message — the synthetic double just needs to raise the
same exception type at the same call site.)
**Warning signs:** A test with `time.sleep()`, thread joins with generous timeouts, or any
non-determinism in the assertion.

### Pitfall 4: Treating the interleaved-await hazard as needing a real gateway/Discord event to prove
**What goes wrong:** Assuming DISC-04's test needs a live `discord.ui.Select` callback and an
actual button interaction to reproduce.
**Why it happens:** The bug's *symptom* (mismatched render label) only appears in a real Discord
interaction.
**How to avoid:** Reproduced directly in this session with plain `asyncio.create_task` +
`asyncio.sleep(0)` — no discord.py objects needed at all. `SelectedContext` is pure in-memory
(D-17's "hub-assertable observable" lesson from Phase 1 applies again): the test only needs two
coroutines and an interleaving point, not a gateway.
**Warning signs:** A test that imports `discord.ui` or constructs a `discord.Client` to test
`selection.py`.

### Pitfall 5: Best-effort hook fire order — firing `on_rejected` AFTER `raise` instead of before
**What goes wrong:** Placing the hook call after the `raise` statement, which is unreachable
code (the `raise` already transferred control), so the hook silently never fires — this
would look like a passing implementation with a test that doesn't check *order*, only that the
hook was eventually called (it wouldn't be, but a badly-written test with a bare `try/except`
around the whole call could miss this).
**Why it happens:** "Fire before re-raising" is easy to get backwards syntactically.
**How to avoid:** Match the PHASE-1 precedent's exact statement order (log → fire hook → raise),
verified at `reload.py:134-139`. The RED-first test should assert the hook fired using a
mutation observed via a side-channel list (`fired: list = []`), then separately assert (via
`pytest.raises` or try/except) that the original exception still propagates — proving both halves,
not just one.

## Code Examples

### DISC-01: verified non-recoverable disconnect classes (installed discord.py 2.7.1 source)
```python
# Source: .venv/.../discord/client.py:695-792 (Client.connect(), read directly this session)
# The retry loop's except clause — everything here is discord.py's OWN retry, no hub involvement:
except (
    OSError,
    HTTPException,
    GatewayNotFound,
    ConnectionClosed,
    aiohttp.ClientError,
    asyncio.TimeoutError,
) as exc:
    self.dispatch('disconnect')
    if not reconnect:
        await self.close()
        if isinstance(exc, ConnectionClosed) and exc.code == 1000:
            return  # clean close, don't re-raise
        raise
    if self.is_closed():
        return
    # ... OSError-54/10054 RESUME branch ...
    if isinstance(exc, ConnectionClosed):
        if exc.code == 4014:
            raise PrivilegedIntentsRequired(exc.shard_id) from None
        if exc.code != 1000:
            await self.close()
            raise          # <-- 4004, 4010, 4011, 4012, 4013 (and any other non-1000/4014 code)
                            #     escape HERE, uncaught by discord.py's own backoff.
    retry = backoff.delay()
    await asyncio.sleep(retry)
    # ... always retries otherwise (RESUME) ...
```
```python
# Source: .venv/.../discord/gateway.py:624-629 (DiscordWebSocketProtocol._can_handle_close)
def _can_handle_close(self) -> bool:
    code = self._close_code or self.socket.close_code
    is_improper_close = self._close_code is None and self.socket.close_code == 1000
    return is_improper_close or code not in (1000, 4004, 4010, 4011, 4012, 4013, 4014)
    # False (cannot handle -> raises ConnectionClosed, escapes the retry loop) ONLY for
    # codes {1000, 4004, 4010, 4011, 4012, 4013, 4014}; every other close code is retried.
```
```python
# Source: .venv/.../discord/errors.py:60-262 (exception hierarchy, imported from top-level `discord`)
class DiscordException(Exception): ...
class ClientException(DiscordException): ...
class LoginFailure(ClientException): ...            # discord.LoginFailure — raised from login()
class ConnectionClosed(ClientException): ...        # discord.ConnectionClosed — .code, .shard_id
class PrivilegedIntentsRequired(ClientException): ... # discord.PrivilegedIntentsRequired — code 4014
# All importable at top level: discord.LoginFailure, discord.ConnectionClosed,
# discord.PrivilegedIntentsRequired — confirmed via `import discord; discord.LoginFailure` etc.
```
**Conclusion for the synthetic test double:** `discord.LoginFailure()` takes no required
constructor args (plain `ClientException` passthrough) — a fake client's `start()` coroutine can
simply `raise discord.LoginFailure()`.

### DISC-03: reproduced TOCTOU (Python 3.13 REPL, this session)
```python
# Reproduced directly: a closed asyncio loop makes run_coroutine_threadsafe raise this exact
# RuntimeError, with this exact message — confirming the mechanism D-28 guards against.
import asyncio, threading, time

loop = asyncio.new_event_loop()
# ... start loop on its own thread, then stop + close it ...
loop.close()

try:
    asyncio.run_coroutine_threadsafe(some_coro(), loop)
except RuntimeError as e:
    print(e)  # -> "Event loop is closed"
```
The fix (D-28): move `run_coroutine_threadsafe` inside the existing `try` in `stop()` and add
`except RuntimeError` alongside the existing `except Exception` around `future.result(...)` —
or a single `try` wrapping both the schedule call and the result wait, since both can now raise
for the same underlying reason (loop closed between check and call).

### DISC-04: reproduced interleaved-await hazard (Python 3.13 REPL, this session)
```python
# Reproduced directly: a coroutine that re-reads `.value` AFTER an `await` observes a
# concurrent `.set()` that happened during the yield; a coroutine that captures via
# `.snapshot()` BEFORE the await does not.
async def button_handler_buggy(cell):
    await asyncio.sleep(0.01)
    return cell.value          # -> "B" (rebound during the await)

async def button_handler_safe(cell):
    snap = cell.snapshot()     # captured BEFORE await
    await asyncio.sleep(0.01)
    return snap                # -> "A" (stable)
```

### DISC-02: pin/delete exception hierarchy (verified against installed source)
```python
# Source: .venv/.../discord/errors.py:113-200
class HTTPException(DiscordException):
    status: int   # HTTP status code
    code: int     # Discord's own JSON error code (e.g. 30003 for pin-cap)
class Forbidden(HTTPException): ...   # discord.Forbidden IS-A HTTPException
class NotFound(HTTPException): ...    # discord.NotFound IS-A HTTPException
```
```python
# Source: .venv/.../discord/message.py:1447-1471 (Message.pin docstring, installed 2.7.1)
"""
Raises
-------
Forbidden
    You do not have permissions to pin the message.
NotFound
    The message or channel was not found or deleted.
HTTPException
    Pinning the message failed, probably due to the channel
    having more than 250 pinned messages.
"""
```
```python
# Source: .venv/.../discord/abc.py:1826-1876 (Messageable.pins, installed 2.7.1)
def pins(self, *, limit: Optional[int] = 50, before=None, oldest_first: bool = False):
    """... versionchanged 2.6: now returns a paginated async iterator (was a flat list) ..."""
```
The default `limit=50` on `channel.pins()` matters for `summon_panel`'s existing
`[m async for m in channel.pins() if is_owned(m)]` scan: if the true pin cap and Discord's
default iterator page size ever diverge, an unbounded channel could theoretically have owned
panels beyond the first page. At today's confirmed cap (50, per Discord's JSON error-code doc —
see Assumptions Log), this is not currently reachable, but it is worth a one-line docstring note
if the planner wants to close the theoretical gap cheaply (not required by any of the five
success criteria).

### CFG-01: `_best_effort_hook` masking-safety (verified against installed source)
```python
# Source: yahir_reusable_bot/config/reload.py:312-327 (read directly this session)
@staticmethod
def _best_effort_hook(hook, arg, *, label):
    if hook is None:
        return
    try:
        hook(arg)
    except Exception:  # noqa: BLE001 — best-effort; never mask the engine result
        _log.warning(f"{label} hook failed; engine result unaffected")
```
This confirms bullet 5 of the research focus directly: the hook call is wrapped in its own
`try/except Exception`, which is *entirely separate* from the reconcile-failure's own
`except Exception as exc:` block. A raising `on_rejected` hook cannot propagate past
`_best_effort_hook` and therefore cannot replace or suppress the `raise` at `:158` that follows
it. This makes D-31's "fire before re-raise" safe by construction, not by convention.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `channel.pins()` returned a flat `list[Message]` | `channel.pins()` returns a paginated async iterator (`limit` param, default `50`); awaiting the returned object directly still works but is deprecated | discord.py 2.6 (per bundled docstring `versionchanged`) | `summon_panel`'s existing `[m async for m in channel.pins() if is_owned(m)]` already uses the async-iterator form correctly — no change needed for this phase, but worth knowing if a future phase raises the scan limit. |
| `MANAGE_MESSAGES` gated pin/unpin | `PIN_MESSAGES` is its own permission bit (`Permissions.pin_messages`) | Discord platform change effective 2026-01-12 (already reflected in this repo's `REQUIRED_PANEL_PERMS` comment, `gateway.py:50-52`) | Already correctly handled by the existing preflight; not part of this phase's fix, noted only as context confirming the codebase is current on this specific platform change. |

**Deprecated/outdated:** None specific to this phase's five findings — all fixes work with
current, non-deprecated discord.py 2.7.1 APIs (`Message.pin()`, `channel.pins()` async iterator,
`asyncio.run_coroutine_threadsafe`, `discord.LoginFailure`/`ConnectionClosed`/
`PrivilegedIntentsRequired`).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The actual Discord channel pin cap is **50**, per Discord's documented JSON error code `30003` ("Maximum number of pins reached for the channel (50)"), sourced via discord.js's generated `RESTJSONErrorCodes` reference (a cross-ecosystem but same-API-surface secondary source) — this contradicts discord.py 2.7.1's own bundled docstring text for `Message.pin()`, which says "more than 250 pinned messages." | Summary; DISC-02 pin/delete exception hierarchy | Low-to-none for the actual fix (D-26 catches `HTTPException` generically, doesn't branch on a count), but if a plan or test hardcodes "250" anywhere (docstring, comment, or a numeric assertion), it would be wrong and should instead avoid stating a specific number, or state "50" with a citation, not "250." |
| A2 | Discord's JSON error code `30003` is the specific code returned when `Message.pin()` fails due to the channel being at its pin cap (not independently confirmed against a live Discord API call in this session — sourced from a generated third-party error-code reference table, not Discord's own developer docs page directly). | DISC-02 Code Examples | Low — no production code in this phase's fixes branches on `.code == 30003`; this is background context only. If a future phase wants to special-case this condition by code number, it should be re-verified against Discord's own developer portal docs first. |

**If this table is empty:** Not applicable — two low-risk assumptions are logged above; neither
blocks or changes the shape of any of the five fixes.

## Open Questions

1. **Should DISC-01's death-reason distinguish `PrivilegedIntentsRequired`/`ConnectionClosed`
   auth-failures from a truly generic crash?**
   - What we know: Both currently fall into `_run`'s generic `except Exception:` handler
     alongside any other unexpected crash; D-22's minimal bound only requires `login_failure`
     and `crashed`.
   - What's unclear: Whether the host park-loop would benefit from a third, more specific reason
     (e.g. `intents_disallowed`) to give a more actionable operator message ("go enable the
     intent in the developer portal" vs. generic "something crashed").
   - Recommendation: Ship the minimal two-reason version per D-22 (already decided); this is a
     candidate for a future phase if a consumer's park-loop wants sharper branching — not a gap
     in this phase's research, just noted as a natural follow-on.

2. **Does the pin-cap discrepancy (A1/A2) warrant a docstring correction inside this phase's
   `summon_panel` fix, or is it purely a background research note?**
   - What we know: The fix itself (D-26) is cap-number-agnostic — it reacts to `HTTPException`
     generically, never checking a specific count.
     What's unclear: Whether the planner wants a one-line docstring note flagging "the exact
     cap is a Discord platform detail, not asserted by this fix" to preempt a future contributor
     hardcoding a wrong number.
   - Recommendation: Optional, low-cost addition; not required by any of the five success
     criteria. Leave to Claude's Discretion (docstring wording is already discretionary per
     CONTEXT.md).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `discord.py` (installed, pinned) | All gateway/pin fixes (DISC-01/02/03) | ✓ | 2.7.1 (confirmed via `import discord; discord.__version__`) | — |
| `pytest` | RED-first regression tests | ✓ | ≥9.0.3 (per `pyproject.toml`) | — |
| `grimp` | GATE-01 import-hygiene gate | ✓ | ≥3.14 | — |
| External network / live Discord gateway | None — all five fixes are tested with synthetic in-process doubles, no live Discord connection needed | N/A | — | N/A (house style: no mocking library, but also no live-network tests) |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None — everything this phase needs is already installed
and pinned.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥9.0.3 (per `pyproject.toml`; no `pytest-asyncio` — repo convention is `asyncio.run()` inline) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = ["."]`) |
| Quick run command | `uv run pytest -q tests/test_gateway.py tests/test_reload.py tests/test_selection.py` |
| Full suite command | `uv run pytest -q` (matches `.planning/config.json` `workflow.test_command`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CFG-01 | `on_rejected` fires exactly once before re-raise on PHASE-2 failure; rollback (holder + restore) unchanged | unit | `uv run pytest tests/test_reload.py -k reject -x` | ❌ Wave 0 — `tests/test_reload.py` does not exist (Phase 1 CONTEXT.md confirmed no coverage exists for `reload.py` in this repo) |
| DISC-01 | Fake `LoginFailure` start → `is_alive()` False, reason `login_failure`; fake generic crash → reason `crashed` | unit | `uv run pytest tests/test_gateway.py -k death -x` | ✅ file exists, new test functions added |
| DISC-02 | (a) NotFound-mid-delete → both remaining deletes still run, net 1 live panel; (b) at-cap → fresh panel ends up pinned | unit | `uv run pytest tests/test_gateway.py -k summon -x` | ✅ file exists, new test functions added |
| DISC-03 | Fake loop: `is_running()` True, `run_coroutine_threadsafe` raises `RuntimeError` → `stop()` returns, still joins | unit | `uv run pytest tests/test_gateway.py -k stop -x` | ✅ file exists, new test functions added |
| DISC-04 | `snapshot()`-captured value unaffected by interleaved `set()`; `.value` re-read reflects the write | unit | `uv run pytest tests/test_selection.py -x` | ❌ Wave 0 — `tests/test_selection.py` does not exist |

### Sampling Rate
- **Per task commit:** the file-scoped quick-run command for whichever finding was just fixed
  (e.g. `uv run pytest tests/test_gateway.py -k death -x` after DISC-01's RED test, then again
  after its fix).
- **Per wave merge:** `uv run pytest -q` (full suite) — must include `test_import_hygiene.py`
  green, since GATE-01 spans the whole milestone.
- **Phase gate:** Full suite green before `/gsd-verify-work`, per D-13's two-commit RED-first
  idiom (test-only commit is a direct parent of the fix commit, for each of the five findings).

### Wave 0 Gaps
- [ ] `tests/test_reload.py` — new file; first-ever unit coverage for `config/reload.py` in this
      repo (confirmed absent by Phase 1 CONTEXT.md's scouting note, re-confirmed by `ls tests/`
      in this session: only `test_gateway.py`, `test_import_hygiene.py`, `test_identity.py`,
      `test_retry.py` currently exist).
- [ ] `tests/test_selection.py` — new file; first-ever unit coverage for `discord/selection.py`.
- [ ] Framework install: none — `pytest` already installed and pinned.
- [ ] `tests/conftest.py` growth: **not required** unless a fake double (client/channel/loop) is
      actually shared across ≥2 test files (D-10's rule). Since DISC-01/02/03 all live in the
      same `tests/test_gateway.py` file, their synthetic doubles likely do NOT need to move to
      `conftest.py` even though they're related — only promote a double if `test_reload.py` or
      `test_selection.py` genuinely need the same fake object (unlikely, since they're
      independent modules with independent injected seams).

### Under-sampling risks (per finding — what a fix could false-green against)
- **CFG-01:** A test that only asserts "the hook was called" without asserting **exactly once**
  and without asserting the **rollback state** (`holder.current() == old_cfg`, per D-16's
  both-levels habit) could false-green a fix that fires the hook twice, or fires it but skips
  the rollback. D-33 already names both assertions explicitly — the planner must keep both in
  the same test, not split them across two under-asserted tests.
- **DISC-01:** A test that only checks `is_alive() is False` without checking the death-reason
  value would false-green a fix that sets `_failed = True` but never sets/exposes the reason
  (i.e., the accessor exists but nothing ever calls it). Sample BOTH the `LoginFailure` branch
  and the generic-crash branch — a fix that only wires the reason for one branch would false-green
  against a test that only samples the other.
- **DISC-02:** Sampling only the NotFound-mid-delete case (a) would false-green a fix that never
  actually reserves pin headroom at the cap (b) — the two success-criteria halves
  ("cannot leave 2+ live panels" vs. "cannot leave a fresh-but-unpinned panel") are proven by
  *different* code paths (per-item catch vs. headroom-reserve-before-send) and need independent
  fixtures. A single fixture covering only one mode would false-green the other.
- **DISC-03:** A test that makes `run_coroutine_threadsafe` raise `RuntimeError` but never
  asserts that `self._thread.join(...)` still ran afterward would false-green a fix that
  swallows the error and then simply `return`s early — the success criterion is "stop() cannot
  raise AND still joins," not just "stop() cannot raise."
- **DISC-04:** A test that only checks `snapshot()` is stable would false-green a "fix" that
  makes `.value` ALSO frozen after first read (over-fixing, breaking the legitimate case where a
  fresh read after a completed callback SHOULD see the new value). D-33 already names both
  halves — the planner must keep the `.value`-still-reflects-the-write assertion in the same
  test as the `snapshot()`-is-stable assertion.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | Bot token authentication is entirely owned by `discord.py`'s `login()`; this phase does not touch token handling. |
| V3 Session Management | No | No session concept in this hub; gateway connection lifecycle is discord.py's own state machine. |
| V4 Access Control | No | No access-control logic is touched by any of the five fixes. |
| V5 Input Validation | No | No new external input parsing introduced; `reload.py`'s PHASE-1 validation path is unchanged by CFG-01 (only the PHASE-2 *rollback* path gains a hook fire). |
| V6 Cryptography | No | No crypto/token handling changed. |
| V7 Error Handling and Logging | Yes | All five findings are, at their core, error-handling correctness fixes. Standard control: never let a best-effort side-effect hook mask or replace the original exception (`_best_effort_hook`, already in place); log operator-actionable failures at `CRITICAL`/`WARNING` with only non-secret structured fields (`channel_id`, `shard_id`) — never the bot token. The new death-reason logging (DISC-01) must follow the same non-secret-field discipline already used elsewhere in `gateway.py`. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Reconnect hot-loop against a non-recoverable failure (bad token / disallowed intents) causing repeated auth attempts | Denial of Service (self-inflicted; risks a Discord-side rate-limit or temporary ban) | Liveness-only (D-21) — verified this session that discord.py already refuses to retry exactly these cases; a hub-side wrapper would defeat that refusal. |
| Silent alert-hook skip on reconcile failure masking an operator-visible signal | Repudiation / silent failure | Fire `on_rejected` before re-raise (D-31), matching the existing PHASE-1 precedent; verified the swallow-guard (`_best_effort_hook`) cannot itself mask the original error. |
| Secret leakage in new log fields | Information Disclosure | The death-reason accessor and its logging must carry only the reason string/enum and non-secret identifiers, never the token — consistent with the existing `_run` CRITICAL logs, which already log no token. |
| Stray unpinned "fresh" panel routable via a stale `custom_id` alongside the true active panel | Spoofing (a user could interact with a panel that is not the operator-intended "current" one) | create-before-delete + per-item delete error handling (D-24/D-25) + headroom-reserve (D-26) collapse the window in which two live/near-live panels can coexist. |

## Sources

### Primary (HIGH confidence — direct source inspection + live reproduction, this session)
- `.venv/lib/python3.13/site-packages/discord/client.py` (installed discord.py 2.7.1) — `connect()` (`:695-792`), `login()` (`:645-688`), `start()` (`:829-849`) read in full.
- `.venv/lib/python3.13/site-packages/discord/gateway.py` (installed discord.py 2.7.1) — `_can_handle_close()` (`:624-629`), `poll_event()` close-code raise sites (`:660-692`).
- `.venv/lib/python3.13/site-packages/discord/errors.py` (installed discord.py 2.7.1) — full exception hierarchy (`DiscordException` → `ClientException`/`HTTPException` → `LoginFailure`/`ConnectionClosed`/`PrivilegedIntentsRequired`/`Forbidden`/`NotFound`), `HTTPException.__init__` `.status`/`.code` attributes (`:113-155`).
- `.venv/lib/python3.13/site-packages/discord/message.py` — `Message.pin()` docstring + implementation (`:1447-1476`).
- `.venv/lib/python3.13/site-packages/discord/abc.py` — `Messageable.pins()` signature + versionchanged note (`:1826-1876`).
- `yahir_reusable_bot/config/reload.py`, `yahir_reusable_bot/discord/gateway.py`, `yahir_reusable_bot/discord/selection.py` — read in full this session at their current (post-Phase-1) state.
- Live Python 3.13 REPL reproductions (this session): `asyncio.run_coroutine_threadsafe` against a closed loop raising `RuntimeError("Event loop is closed")`; interleaved-await rebind hazard on a plain in-memory cell.
- `tests/test_gateway.py`, `tests/conftest.py`, `.planning/codebase/TESTING.md`, `.planning/phases/01-reachable-reliability/01-CONTEXT.md` — house style and prior-phase conventions.
- `uv run pytest --collect-only -q` — confirmed current test inventory (27 tests, no `test_reload.py`/`test_selection.py`).

### Secondary (MEDIUM confidence)
- discord.js's generated `RESTJSONErrorCodes` reference (`discord-api-types.dev`) — cross-ecosystem confirmation of Discord's JSON error code `30003` = "Maximum number of pins reached for the channel (50)".

### Tertiary (LOW confidence — flagged in Assumptions Log)
- discord.py 2.7.1's own bundled docstring for `Message.pin()`, which states the cap trigger is "more than 250 pinned messages" — contradicts the secondary source above; treated as unresolved (see Assumptions Log A1/A2), not authoritative either way for this phase's fix shape.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; every existing pin re-confirmed installed.
- Architecture (DISC-01 non-recoverable disconnect classes): HIGH — read directly from the installed discord.py 2.7.1 source, not recalled from training data.
- Architecture (DISC-03 TOCTOU, DISC-04 interleaved-await): HIGH — reproduced live in a REPL this session, not merely asserted.
- Architecture (DISC-02 exception hierarchy): HIGH for the hierarchy (`NotFound`/`Forbidden` subclass `HTTPException` — read directly). MEDIUM for the exact numeric pin cap (conflicting sources; logged as assumptions, does not affect fix shape).
- Pitfalls: HIGH — each pitfall ties directly to a verified mechanism above, not a generic gotcha list.

**Research date:** 2026-07-27
**Valid until:** 90 days for the discord.py-internals findings (tied to the exact `==2.7.1` pin, which does not change without a deliberate repo decision); 30 days for the pin-cap number if the planner wants to re-verify it against Discord's live developer docs before relying on it for anything more than "catch HTTPException generically."
