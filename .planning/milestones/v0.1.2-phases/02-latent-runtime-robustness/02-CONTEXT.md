# Phase 2: Latent runtime robustness - Context

**Gathered:** 2026-07-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Close the five hub bugs that need specific runtime conditions to bite — each with a RED-first
regression test, GATE-01 (full suite + import-hygiene/litmus/grimp) staying green:

- **CFG-01 (H03)** — `config/reload.py` PHASE-2 reconcile-failure path rolls back, restores, logs,
  re-raises, but **never fires `on_rejected`**, so the host's "reload rejected" alert is silently
  skipped (PHASE-1 fires it correctly).
- **DISC-01 (H04)** — `discord/gateway.py` `_amain` does a single `client.start()` with no
  operator-visible programmatic signal on a non-recoverable death. **The ROADMAP's explicit open
  design decision: the retry/backoff contract** — settled this phase.
- **DISC-02 (H05)** — `discord/gateway.py` `summon_panel` sends+pins the fresh panel first then
  deletes old, catching only `Forbidden`; a `NotFound`/`HTTPException` on delete, or a `pin()` at
  the 50-pin cap, leaves 2+ live panels or a fresh-but-unpinned panel.
- **DISC-03 (H07)** — `discord/gateway.py` `stop()` schedules `run_coroutine_threadsafe` between the
  `loop.is_running()` check and its own `try`; a loop that closes in that gap raises `RuntimeError`
  out of `stop()`.
- **DISC-04 (H08)** — `discord/selection.py` `SelectedContext` re-read across an `await` yields a
  mismatched render label (cosmetic). **Contract + API only** — the observed defect's fix site is
  consumer-side (`wiring.py`); the hub side makes the await-safety contract explicit and offers a
  snapshot-safe consume.

**Not in this phase:** every other H-number. Notably `LIFE-03` (H15, path-shaped `proc_marker`)
touches `identity.py` and `LIFE-02` (H14) touches the same file, but both are Phase 3 — do not fold.
The **consumer-side** `wiring.py` re-read that is DISC-04's actual observed bug is WeatherBot's to
fix at repin, not the hub's (REQUIREMENTS.md:73-76).

</domain>

<decisions>
## Implementation Decisions

> Decision numbering continues the milestone-wide sequence (Phase 1 reached **D-20**), so Phase 2
> starts at **D-21**. Distinct namespace from the module docstrings' own `D-04..D-09` extraction
> decisions.

### Verified fix locations (report line numbers have drifted — use these)

The source was re-read at HEAD during discussion; the `HUB-HARDENING-REPORT` line numbers are stale.
Planner/researcher use these verified locations:

| Finding | Verified location |
|---|---|
| CFG-01 | `config/reload.py:146-158` (PHASE-2 `except Exception:` block); fire point before `raise` at `:158`; PHASE-1 precedent hook fire at `:138` |
| DISC-01 | `gateway.py:273-278` (`_amain`); `is_alive()` `:233-240`; `_run` except handlers `:262-271`; `_failed` init `:216` |
| DISC-02 | `gateway.py:133-188` (`summon_panel`); send+pin `:166-167`; delete loop `:171-172`; sole `Forbidden` catch `:180` |
| DISC-03 | `gateway.py:242-253` (`stop()`); `is_running()` check `:245`; unguarded `run_coroutine_threadsafe` `:246`; `try` wraps only `future.result()` `:247-250` |
| DISC-04 | `selection.py:33-51` (`SelectedContext`); `value` `:44-47`; `set()` `:49-51`; single-writer note `:15-22` |

### Gateway liveness/reconnect contract (DISC-01)

- **D-21:** The ROADMAP's open "retry/backoff contract" resolves to **liveness-only — the hub adds
  NO reconnect retry beyond discord.py's own.** `_amain`'s single `client.start(token)` stays;
  discord.py's default `reconnect=True` already runs an `ExponentialBackoff` for every *recoverable*
  disconnect. The disconnects that actually reach thread-death (`_run`'s except handlers) are the
  ones discord.py **deliberately refuses** to retry — `LoginFailure`, disallowed/privileged intents,
  auth-close (4004/4014). A hub-side reconnect wrapper would hot-loop those *identical
  non-recoverable* failures straight into a Discord rate-limit/ban. Preserves BotThread's non-owning
  + failure-isolation design ("die alone; never crash the process").
- **D-22:** Add a **death-reason** signal to `BotThread` so the host park-loop can branch
  **programmatically**, not just scrape a CRITICAL log. Minimal, following the module's existing
  constant idiom (`REASON_*` in `retry.py:75`): at least `login_failure` (from the
  `discord.LoginFailure` handler `:264`) and `crashed` (generic handler `:269`); a clean-exit reason
  is optional if `asyncio.run` returns without raising. Exposed via a read accessor alongside
  `is_alive()`. `is_alive()` semantics (`:233-240`) are **unchanged** — the reason is purely
  additive.
- **D-23:** The contract is made explicit in the docstring: **`is_alive()` is the documented signal
  the host park-loop consults to decide respawn/alert/exit; the hub never respawns.** Rejected: the
  bounded-reconnect-wrapper (duplicates discord.py, ban risk on the exact failures that trigger it)
  and the hybrid-injected-policy (a plug point with no rule-of-three demand — see Deferred).

### Panel re-summon atomicity (DISC-02)

- **D-24:** **Create-before-delete is preserved (D-06 invariant holds).** Rejected: the report's
  "delete-then-pin" (`HUB-HARDENING-REPORT:130`) — it reverses the no-zero-panel-window ordering and,
  on a send/pin failure, would leave **zero** panels, worse than the current 2+-panels bug. *(A
  single located correction to the report, in the Phase-1 D-05 spirit; the report is otherwise
  authoritative.)*
- **D-25:** **Per-item delete error handling broadened.** Each `old.delete()` (`:171-172`) gets its
  own `try/except (discord.NotFound, discord.HTTPException, discord.Forbidden)` → log + continue, so
  one failed delete never aborts the remaining deletes (closes the CONFIRMED "2+ live panels" mode).
  The outer sole-`Forbidden` block (`:180`) is narrowed/relocated so a preflight-revoked send/pin is
  still handled without swallowing the per-item cases.
- **D-26:** **Reserve pin headroom for the 50-pin cap.** When the channel is at the pin cap AND ≥2
  owned panels exist, delete one owned stray *before* send+pin (still leaves ≥1 live panel, so D-06's
  no-zero-window holds), freeing a slot so the fresh `pin()` (`:167`) succeeds; then delete the rest.
  This is the only branch that satisfies the success criterion's "cannot leave a fresh-but-unpinned
  panel."
- **D-27:** **Residual out-of-authority case: document, don't chase.** A channel saturated with 50
  *foreign* (non-owned) pins cannot be made room for without evicting pins the hub does not own; in
  that case send the fresh panel + emit a **loud CRITICAL** (operator-visible, per the loud-failure
  preference) rather than silently leaving it unpinned. Stated as a docstring limitation.

### stop() TOCTOU (DISC-03 — clear-cut, folded without discussion)

- **D-28:** In `stop()` (`:242-253`), move `run_coroutine_threadsafe` (`:246`) **inside** a `try`
  and catch `RuntimeError` ("Event loop is closed") as "loop already stopped" → log + fall through
  to `join`. The `loop.is_running()` check (`:245`) stays as a fast path but is no longer relied on
  as a guarantee (the loop can close between `:245` and `:246`). `stop()` must never raise.

### Selection snapshot API (DISC-04)

- **D-29:** Add a `snapshot()` read-once method to `SelectedContext` (`:33-51`) returning the current
  `_value` — semantically identical to `.value` but **named to carry the contract**: capture once
  into a local before any `await`; never re-read `.value` across an `await`. Contract + API only per
  REQ scope — the consumer-side `wiring.py` re-read is **not** touched here.
- **D-30:** **Await-safety contract made explicit** in the class docstring — extend the single-writer
  note (`:15-22`) to state the interleaved-await hazard (a Select tap on the gateway loop during an
  off-loop `await` can rebind `.value` between two reads → mismatched render label/data, the H08
  cosmetic race) and prescribe `snapshot()`-before-`await` as the idiom. Rejected: the
  immutable-handle / context-manager guard (over-built for a cosmetic single-writer race; `I` is
  app-defined and may not be freezable; violates the cell's deliberate lock-free minimalism vs
  `ConfigHolder`).

### Reload-reject alert semantics (CFG-01)

- **D-31:** The PHASE-2 reconcile-failure path (`reload.py:146-158`) fires
  `_best_effort_hook(self._on_rejected, exc, label="reconcile-rolled-back")` **before** the `raise`
  at `:158` — change `except Exception:` to `except Exception as exc:`. Mirrors PHASE-1's
  fire-before-reraise (`:138`). The rollback/restore ordering (`:150-157`) is otherwise
  byte-identical; the ORIGINAL reconcile error is still the one re-raised (the best-effort hook can
  never mask it — `_best_effort_hook` swallows hook raises).
- **D-32:** **Same hook, no new public surface.** Rejected: a phase/reason enum or a second
  `on_reconcile_failed` hook. Both keep-old outcomes call for the same consumer action (alert + keep
  running on old config); a consumer that wants to branch already can, because the PHASE-2 exception
  is a distinct type (`JobLookupError` / registrar failure) from a PHASE-1 validation error.
  Distinct-ness lives only in the internal log label for operator clarity.

### RED-first regression coverage (per finding, D-13 two-commit idiom)

- **D-33:** Each fix ships its RED-first test against **hub-assertable observables** (the D-17
  lesson — never a consumer symptom):
  - **DISC-01:** a fake client whose `start()` raises `discord.LoginFailure` (with async-context
    support for `async with self._client`) → after `_run`, assert `is_alive()` is False AND the
    death reason reads `login_failure`; a generic-crash variant → reason `crashed`.
  - **DISC-02:** (a) fake `channel.pins()` yielding 2 owned matches where the first `old.delete()`
    raises `NotFound` → assert BOTH remaining deletes still ran and net state is one live pinned
    panel; (b) fake channel at the pin cap → assert the fresh panel ends up pinned (headroom
    reserved).
  - **DISC-03:** a fake loop reporting `is_running()` True but raising `RuntimeError` on
    `run_coroutine_threadsafe` → assert `stop()` returns without raising and still joins.
  - **DISC-04:** assert a value captured via `snapshot()` is unchanged after an interleaved `set()`,
    while a re-read of `.value` reflects the write — proving the idiom is load-bearing.
  - **CFG-01:** an injected `register_jobs` (or scheduler `remove`) that raises drives reconcile
    failure → assert `on_rejected` fired **exactly once** with the reconcile exception AND the holder
    rolled back to `old_cfg` (both levels, per the D-16 habit).

### Claude's Discretion

- Exact death-reason representation (str constants vs enum vs `Literal`) within D-22's minimal bound
  — follow the module's `REASON_*` constant style.
- Whether the five fixes ship as one plan or split. They touch disjoint files, but `gateway.py`
  holds three findings (DISC-01/02/03) — grouping by file is natural. Sequence so a deliberately-RED
  test never overlaps a sibling's full-suite gate (the Phase-1 "Plan 03 waits on 02" lesson).
- Exact test-function names and whether `pytest.raises()` is used (Phase 1 established it as
  acceptable).
- Exact shapes of the synthetic inline doubles (fake channel/message/client/loop) per the
  no-mocking-library house style (D-11); grow `tests/conftest.py` only when ≥2 test files actually
  share a double (D-10's "when a real second caller appears" rule).
- Exact docstring wording for the fixed functions, provided the D-23/D-27/D-30 contracts are stated.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source of record for the findings
- `.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md` — fix direction per finding. **H03 at :111-116,
  H04 at :118-123, H05 at :125-130, H07 at :141-144, H08 at :146-149.** Note: its line numbers for
  the fix sites are stale — use the "Verified fix locations" table above. Note D-24: the H05
  "delete-then-pin" text (`:130`) is superseded here.
- `.planning/backlog/HUB-FINDINGS-HANDOFF.md` — full failure scenario and evidence per finding.
- `.planning/REQUIREMENTS.md` — CFG-01 `:57-58`, DISC-01 `:63-64`, DISC-02 `:66-68`, DISC-03
  `:70-71`, DISC-04 `:73-76`, GATE-01 `:105-107`.
- `.planning/ROADMAP.md` §"Phase 2: Latent runtime robustness" (`:63-84`) — the five success
  criteria; note the DISC-01 "open design decision" clause (`:76`) settled by D-21..D-23 and the
  DISC-04 "contract + API only" clause (`:83-84`).

### Files being modified
- `yahir_reusable_bot/config/reload.py` — `reload()` `:118-163`; PHASE-1 hook fire `:138`;
  PHASE-2 rollback block `:146-158`; `_best_effort_hook` `:312-327`.
- `yahir_reusable_bot/discord/gateway.py` — `summon_panel` `:133-188`; `BotThread` `:191-278`
  (`is_alive` `:233-240`, `stop` `:242-253`, `_run` `:255-271`, `_amain` `:273-278`).
- `yahir_reusable_bot/discord/selection.py` — `SelectedContext` `:33-51`.

### Prior-phase context (carried forward)
- `.planning/phases/01-reachable-reliability/01-CONTEXT.md` — the D-XX / canonical-refs / RED-first
  conventions this phase inherits (D-11 no-mocking house style, D-13 two-commit proof, D-14 phase
  branch, D-16 both-levels, D-17 hub-assertable-observable discipline).

### Test conventions and standing gates
- `.planning/codebase/TESTING.md` — house style: flat `tests/`, module-level `test_*()` functions,
  docstring-first, no mocking library, synthetic inline doubles, `test_selfproof_*` naming, no CI.
  Stale re: conftest (Phase 1's D-09 added one).
- `tests/conftest.py` — now exists (Phase 1, D-09/D-10): `fake_stop_event`, `cmdline_bytes`. Grow it
  only on a real second caller (D-10).
- `tests/test_gateway.py` — the existing gateway behavioral-test precedent; match its shape.
- `tests/test_import_hygiene.py` — the standing GATE-01 gate + `test_selfproof_*` idiom source.

### Project constitution
- `ECOSYSTEM.md` §3 — human-gated close-out (tags/bump/repin are NOT autonomous).
- `CLAUDE.md` (repo root) — one-way dependency, `discord.py==2.7.1` exact pin, no domain nouns.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (seams already present — no new test hooks needed)
- **DISC-01:** `BotThread._failed` (`:216`) + `is_alive()` (`:233-240`) already expose liveness; the
  `_run` except handlers (`:262-271`) are the two death sites where a death-reason is set. A
  synthetic fake client (async-context + raising `start()`) drives `_run` without a real gateway.
- **CFG-01:** every `ReloadEngine` collaborator is injected (`validate`, `desired_jobs`,
  `register_jobs`, `restore`, `on_rejected`, scheduler_engine) — a fake `register_jobs`/scheduler
  that raises drives the reconcile-failure path in-memory. `_best_effort_hook` (`:312-327`) is the
  exact call to reuse on the PHASE-2 path.
- **DISC-02:** `channel.pins()` is an async iterator and `is_owned` is injected — a synthetic
  channel/message double exercises the ordering and per-item error branches.
- **DISC-04:** `SelectedContext.value`/`set` (`:44-51`) are pure in-memory — the snapshot test needs
  no gateway at all.

### Established Patterns (constrain the fixes)
- **Create-before-delete / no-zero-panel-window ordering (D-06)** — load-bearing; D-24 preserves it
  over the report's contrary text.
- **Best-effort hook guard** (`_best_effort_hook`) — a hook raise is logged + swallowed, never masks
  the engine result; CFG-01's fix reuses it verbatim.
- **Degrade-vs-raise split** — the gateway isolates failures in the thread (`_run` swallows); DISC-01
  keeps that (no new raise), DISC-03 makes `stop()` degrade instead of raising.
- **Single-writer, lock-free cell** — `SelectedContext` is deliberately simpler than `ConfigHolder`
  (no lock); D-29/D-30 add a method + docstring, no lock, preserving that minimalism.
- Module docstrings carry decision rationale inline — the D-21/D-23/D-27/D-30 contracts belong in the
  fixed functions' docstrings, not just commit messages.

### Integration Points
- `is_alive()` is the host park-loop's respawn signal (D-23) — the death-reason accessor is new
  public surface a consumer reads; belongs in the phase summary handed to the human-gated close-out.
- `on_rejected` is the consumer's "reload rejected" Discord alert — CFG-01 makes it fire on PHASE-2,
  a silent-→-loud behavior change at repin (note in the phase summary).
- `summon_panel`'s panels route by static `custom_id`; leaving 2 live panels means 2 routable
  views — the DISC-02 fix is what keeps routing single-panel.
- `SelectedContext` is public surface any consumer parameterizes; `snapshot()` is additive.

</code_context>

<specifics>
## Specific Ideas

- **The linchpin for DISC-01's `must_haves`:** discord.py's default `reconnect=True` already owns
  recoverable-disconnect backoff, so thread-death is (almost) always a non-recoverable condition a
  reconnect wrapper cannot help and would only hot-loop. This is *why* liveness-only is correct, not
  merely convenient — carry it into the plan's rationale the way D-17 was carried in Phase 1.
- **The linchpin for DISC-02:** the D-06 no-zero-panel-window invariant and the success criterion's
  "no fresh-but-unpinned panel" pull in opposite directions at the pin cap; D-26's headroom-reserve
  is the reconciliation, and D-27's foreign-pin-saturation residual is the honestly-unfixable edge to
  document rather than fake a test around.
- DISC-03 and the CFG-01 base fire are clear-cut — surfaced but folded without a discussion round;
  the developer confirmed they ship regardless.

</specifics>

<deferred>
## Deferred Ideas

- **Hybrid injected reconnect policy (DISC-01 Option 3)** — an optional injected `on_death` /
  reconnect-policy callable so a consumer can opt into hub-driven auto-respawn. Deferred under
  build-in-consumer-then-promote: no current consumer needs it (WeatherBot's park-loop polls
  `is_alive()`). Promote if a second consumer actually wants auto-respawn.
- **Consumer-side `wiring.py` re-read fix (DISC-04's observed defect)** — explicitly out of hub
  scope (REQUIREMENTS.md:73-76); it lands in WeatherBot at repin, consuming the hub's new
  `snapshot()` idiom.
- **Immutable/enforced snapshot handle for `SelectedContext`** — rejected now (D-30) as over-built
  for a cosmetic race; revisit only if a real multi-writer selection scenario appears.
- **Refresh `.planning/codebase/TESTING.md`** — still stale re: the conftest Phase 1 added; grows
  further only if Phase 2 adds shared fixtures. Housekeeping, not phase scope.

### Reviewed Todos (not folded)
None — no pending todos matched Phase 2 scope.

</deferred>

---

*Phase: 2-latent-runtime-robustness*
*Context gathered: 2026-07-27*
</content>
</invoke>
