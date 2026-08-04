# YahirReusableBot — Hardening Milestone Report → v0.1.2

> **Purpose:** milestone seed for `/gsd-new-milestone` in this repo. Consolidates the 17 hub
> defects (H01–H17) surfaced by WeatherBot's v2.1 whole-project audit, plus the 1 deferred
> enhancement (H18), with **per-finding fix direction verified against current hub source** and a
> **consumer-impact triage** telling you which findings actually bite a live consumer today vs.
> which are latent/reusability hardening.
>
> **Milestone goal (proposed):** ship a hardened **v0.1.2** — close the reachable reliability +
> lifecycle defects, harden the reusable public surface (matcher, panelkit, identity) against
> reuse footguns, and add the first-class `ReadyGate` fatal outcome so consumers can drop their
> app-side `stop`-overload hack.
>
> **Human-gated close-out (per `ECOSYSTEM.md`):** after fixes land + gates pass, **you** cut tag
> `v0.1.2` and repin consumers. WeatherBot then moves `[tool.uv.sources]` `v0.1.1 → v0.1.2`.
>
> Source audit: WeatherBot `.planning/WHOLE-PROJECT-REVIEW.md` + `audit-raw.json`. This report
> supersedes the raw `HUB-FINDINGS-HANDOFF.md` copy for milestone planning (adds fix direction +
> live/latent triage).

---

## 1. Count reconciliation (read this before trusting any bare number)

- **17 audit-surfaced hub defects: H01–H17** — this is the milestone's in-scope defect count.
  Severity: **2 high · 4 medium · 10 low · 1 cleanup**.
- **+1 enhancement: H18** (`ReadyGate.run` fatal outcome) — a documented design improvement from
  WeatherBot Phase 29 (D-09/D-10), **not** an audit defect. Include it in the milestone if you want
  to let consumers de-hack; it inflates the row count to 18 but not the defect count.

So: **17 defects to fix + 1 optional enhancement.**

---

## 2. Consumer-impact triage (from WeatherBot, the only live consumer today)

Verified 2026-07-21 against the WeatherBot working tree. This is the argument for *what to
prioritize* — not every hub defect is reachable from a real consumer.

| Bucket | Findings | Meaning |
|--------|----------|---------|
| 🔴 **Live & unmitigated in a consumer** | **H02**, **H01** | Reachable in WeatherBot right now, no app-side guard. H02 can silently drop a morning briefing. |
| 🟠 **Latent / narrow-condition** | H03, H04, H05 | Real hub bugs; need specific runtime conditions (reconcile-time reload failure, non-recoverable gateway disconnect, non-Forbidden delete error). |
| 🟡 **Unreachable in current consumer** | H06, H09, H13, H10, H11, H12, H14, H15, H16 | Guarded by consumer config validation or simply not exercised (e.g. all command names lowercase ASCII). Pure reusability hardening — will bite a *future* consumer. |
| ⚪ **Cleanup / enhancement** | H17, H18 | Docstring/`__all__` drift (H17); ready-gate design improvement (H18). |

**Consumer mitigation status (what WeatherBot already did, so you don't double-count):**
- **H18** — WeatherBot *works around it* app-side: a dedicated `fatal` `threading.Event` kept
  separate from `stop` (`weatherbot/scheduler/wiring.py`). Fixing it here lets WeatherBot delete
  that hack. It is an enhancement precisely because a workaround exists.
- **H09** — WeatherBot *prevents* it via a config validator pinning `attempts_per_burst >= 2`
  (`weatherbot/config/models.py`). The hub function is still div-by-zero-fragile for other callers.
- **H06 / H13** — *not* mitigated, merely unreachable (WeatherBot command names are lowercase
  ASCII). A rename to any non-ASCII/uppercase name would expose them.
- **H02 / H01 / H03 / H04 / H05** — **no consumer-side workaround.** WeatherBot's
  `reliability/retry.py` is a byte-identical **re-export shim** of this hub's `is_transient`, so
  the H02 defect is live in WeatherBot verbatim. (WeatherBot's `weather/client.py` non-JSON-body →
  `ReadError` remap is a *different* fix and does not cover H02's missing sibling exceptions.)

---

## 3. Proposed milestone shape

Correctness-first, reachable-first, then reusability hardening, cleanup last — mirrors the
sequencing that worked for WeatherBot v2.1.

1. **Reachable reliability (highest real-world impact):** H02, H01.
2. **Latent runtime robustness:** H03, H04, H05, H07, H08.
3. **Reusable public-surface footguns** (matcher / retry-callable / panelkit / identity):
   H06, H09, H10, H11, H12, H13, H14, H15, H16.
4. **Cleanup + enhancement:** H17, then optionally H18.

**Test posture:** every fix ships with a RED-first regression test. Several findings note the
existing tests only cover decoy cases (e.g. `test_reload.py:561` for H01) — those need the missing
adversarial case added, not just a new happy path.

---

## 4. Findings catalog (with verified fix direction)

Each entry: location · severity · verification status · **fix direction** (checked against current
hub source at HEAD `50e8f09`). Full failure scenarios/evidence are in the source audit; condensed
here to the actionable core.

### 🔴 High — reachable

**H01 — `lifecycle/identity.py:149` · high · CONFIRMED — PID-recycling false positive**
`_argv_matches_marker` returns `b"-m" in argv[1:3] and proc_marker in argv[1:4]`. It (a)
false-positives when the marker is a positional arg (`python -m pytest weatherbot` →
`weatherbot reload` can SIGHUP an unrelated recycled PID), and (b) false-negatives when an
interpreter flag precedes `-m` (`python -O -m weatherbot run` → live daemon reported not running).
**Fix:** pin the exact position — `len(argv) >= 3 and argv[1] == b"-m" and argv[2] == proc_marker`.
Add regression cases for the positional-arg decoy and the flag-before-`-m` daemon (current
`test_reload.py:561` only covers non-`-m` decoys).

**H02 — `reliability/retry.py:87` · high · SWEEP-NEW — transient classifier misses siblings**
`is_transient` only matches `(httpx.TimeoutException, httpx.ConnectError, httpx.ReadError)`.
`httpx.RemoteProtocolError` ("Server disconnected without sending a response") and
`httpx.WriteError` — routine mid-response hangups from OpenWeather/Discord — fall through as
non-transient, so the two-burst retry never fires and the outcome is misclassified
`internal_error` instead of `transient_exhausted`. **A realistic network blip silently misses the
briefing.** **Fix:** broaden the isinstance tuple to cover the network/protocol families —
recommend `(httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)` (`NetworkError`
subsumes `ConnectError`/`ReadError`/`WriteError`/`CloseError`; `RemoteProtocolError` added
explicitly). Prefer this over a blanket `httpx.TransportError` so `LocalProtocolError` (a
client-side bug, not transient) stays non-retryable. Add regression tests asserting both new
exception types classify transient and drive `transient_exhausted` on exhaustion.

### 🟠 Medium — latent / narrow

**H03 — `config/reload.py:150` · medium · CONFIRMED — PHASE-2 reconcile failure never alerts**
PHASE-1 config-reject fires `on_rejected`; the PHASE-2 reconcile path (job (de)register raises
`JobLookupError` / register failure) rolls back, restores, logs, re-raises — but never calls the
reject hook. The host's "config reload rejected" Discord alert silently doesn't fire. **Fix:** fire
`_best_effort_hook(self._on_rejected, ...)` on the PHASE-2 failure path before re-raising, matching
PHASE-1.

**H04 — `discord/gateway.py:273` · medium · PLAUSIBLE — no reconnect supervisor**
`_amain` does a single `await self._client.start(token)` with no retry loop. A non-recoverable
disconnect (auth/intents close code, session invalidation, exhausted retries) ends the thread;
`is_alive()` stays False forever and every subsequent panel/interaction is silently dead until a
human restart. **Fix:** wrap `start()` in a bounded supervised reconnect loop, or expose liveness
so the consumer park-loop can respawn. Decide the retry/backoff contract as part of the milestone.

**H05 — `discord/gateway.py:167` · medium · CONFIRMED — non-atomic summon leaves duplicate panels**
`summon_panel` sends+pins the fresh panel first, then deletes old panels catching **only**
`discord.Forbidden`. A `discord.NotFound`/`HTTPException` from `old.delete()` (or a `pin()` at the
50-pin cap) escapes, aborting remaining deletes → 2+ live pinned panels (both routable via static
`custom_id`), or a fresh-but-unpinned panel. **Fix:** delete-then-pin (or reserve pin headroom) and
per-item `try/except` catching `HTTPException`/`NotFound`, not just `Forbidden`.

**H06 — `registry/match.py:61` · medium · CONFIRMED — casefold length-misalignment**
Prefix test uses casefolded input but the arg is sliced from the *un-folded* original with the
folded keyword length. `casefold()` is not length-preserving (`ß`→`ss`, `ﬁ`→`fi`), so a
length-changing fold mis-slices the arg. **Fix:** slice the arg from the *folded* string, or match
on positions that survive folding. Unreachable in WeatherBot (lowercase ASCII names) but a generic
matcher bug. Pairs with **H13**.

### 🟡 Low — reusability footguns

**H07 — `discord/gateway.py:244` · low · PLAUSIBLE — `stop()` TOCTOU**
`is_running()` check then `run_coroutine_threadsafe(...)` outside the `try`; if the loop stops in
the gap, `RuntimeError("Event loop is closed")` escapes `stop()`. Only caller wraps it, so no live
crash. **Fix:** move the schedule inside the guarded block / catch `RuntimeError`.

**H08 — `discord/selection.py:49` · low · PLAUSIBLE — interleaved-await render label race**
`SelectedContext` is re-read after an `await`; a Select tap during an off-loop fetch changes the
render-arg location label (data is location A, 📍 label is location B). Cosmetic. **Fix:** capture
the selection value once pre-await and reuse it (as the argless path already does).

**H09 — `reliability/retry.py:141` · low · SWEEP-NEW — `burst_size == 1` div-by-zero**
`step = burst_spread_s / (burst_size - 1)` raises `ZeroDivisionError` inside the tenacity wait when
`burst_size == 1`; the `==burst_size` early-return only shields the first retry. Public
`two_burst_wait`/`build_retrying` default `burst_size=8` with no `==1` guard. WeatherBot pins `>=2`
so it's unreachable *there*. **Fix:** guard `burst_size <= 1` in `_within_burst_wait` (return the
mid-pause / degrade rather than divide).

**H10 — `reliability/retry.py:146` · low · SWEEP-NEW — standalone `two_burst_wait` desync**
`two_burst_wait` fires its mid-pause at `attempt_number == burst_size` (default 8), independent of
the `stop` bound. A direct caller pairing it with `stop_after_attempt(N)` without a matching
`burst_size` gets the mid-pause at the wrong attempt (or never). `build_retrying` wires it
correctly. **Fix:** couple the two (derive/assert `burst_size` against the stop bound) or document
the precondition loudly.

**H11 — `discord/panelkit.py:309` · low · SWEEP-NEW — `interaction_check` None deref**
`interaction.user.bot`/`.id` dereferenced without a None guard; `interaction.user` can be None in
some contexts, raising `AttributeError` inside `interaction_check` (not covered by
`View.on_error`), so the operator gate throws instead of returning False. **Fix:** None-guard →
return False when user is absent.

**H12 — `discord/panelkit.py:479` · low · SWEEP-NEW — empty marker matches every bot message**
`marker` is required but unvalidated; `cid.startswith("")` is always True, so `marker=""` makes
`is_owned_panel` treat every bot-authored pinned message as owned → `summon_panel` could delete
unrelated bot pins. **Fix:** one-line non-empty `marker` guard at construction.

**H13 — `registry/match.py:59` · low · CONFIRMED — empty/uppercase spec name**
Input is casefolded but `spec.name` compared raw: an empty name matches every input; any uppercase
in a registered name makes the command permanently unmatchable. **Fix:** validate `spec.name`
non-empty + lowercase at registration (or casefold it symmetrically). Pairs with **H06**.

**H14 — `lifecycle/identity.py:83` · low · SWEEP-NEW — `write_pid_atomic` double-close**
On the `os.replace` failure sub-path, `os.close(fd)` runs a second time; between closes the fd
integer can be reused by another thread, so the guarded close silently closes an unrelated
descriptor (`except OSError: pass` hides it). **Fix:** track a `closed` flag / set `fd = -1` after
the first close.

**H15 — `lifecycle/identity.py:162` · low · SWEEP-NEW — non-Linux degrade flips on path marker**
`_read_proc_cmdline` returns the raw `proc_marker` as its `/proc`-absent sentinel, then
`_argv_matches_marker` basenames `argv[0]` before comparing verbatim — so a path-shaped
`proc_marker` (`/usr/bin/thebot`) makes the documented non-Linux "degrade to True" return False.
**Fix:** basename the marker consistently, or compare the sentinel against the un-basenamed form.

**H16 — `scheduler/engine.py:74` · low · SWEEP-NEW — `remove` non-idempotent**
`remove()` forwards straight to `scheduler.remove_job`, raising `JobLookupError` for an
already-gone id — asymmetric with `register()`. A double-remove during reconcile / a
misfire-coalesce race throws uncaught. **Fix:** swallow-on-missing (idempotent) or document the
raise as contract.

### ⚪ Cleanup + enhancement

**H17 — `discord/__init__.py:25` · cleanup · SWEEP-NEW — docstring advertises unexported symbol**
Package `__init__` docstring says it exports "the create-before-delete summon orchestration", and
`gateway.py.__all__` lists `summon_panel`, but the package `__init__` never re-exports it →
`from yahir_reusable_bot.discord import summon_panel` raises `ImportError`. **Fix:** add
`summon_panel` to the package `__init__` imports + `__all__`, or correct the docstring.

**H18 — `lifecycle/ready_gate.py:run` · medium · ENHANCEMENT — no first-class fatal outcome**
`ReadyGate.run(stop)` loops until ok-or-`stop`; a fatal probe result is only logged louder and
re-probed forever. Consumers must overload the `stop` Event to break on fatal. WeatherBot works
around this with a separate `fatal` marker. **Enhancement:** return a distinct fatal outcome (enum
/ dedicated return) so consumers branch on it directly. **Consumer de-hack after ship+repin
(corrected 2026-08-04, DOCS-02/DOCS-03 — see `.planning/v0.1.2-MILESTONE-AUDIT.md` DOC-DRIFT-01 /
DOC-DRIFT-02):** WeatherBot removes its `stop`-overload at `weatherbot/scheduler/wiring.py:_on_fail`
(fatal branch); the gate-return exit-code check at `weatherbot/scheduler/daemon.py` (the correct
gate-return path); and, upstream of both, the classification at
`weatherbot/ops/selfcheck.py:to_health_result` (the PRODUCING site — without it classifying
`CONFIG_INVALID` as fatal, `HealthResult.fatal` is never set and the `ReadyOutcome.FATAL` branch is
unreachable downstream). All three collapse onto the hub outcome. A hub-side deliverable
enumerating consumer de-hack sites must name the site that PRODUCES the input, not only the sites
that CONSUME the outcome.

---

## 5. Close-out checklist (human-gated)

1. **Fixes land** on a milestone branch, each with a RED-first regression test.
2. **Gates green** in this repo: full pytest suite + import-hygiene / litmus / grimp
   layering checks (per `ECOSYSTEM.md`).
3. **Bump** `pyproject.toml` `version = "0.1.1" → "0.1.2"` (match tag; do not loosen the pin).
4. **Cut tag `v0.1.2`** — human step.
5. **Repin WeatherBot:** `[tool.uv.sources]` `tag = "v0.1.1" → "v0.1.2"`, then `uv sync --frozen`
   (host resolves the new sha from the public remote, no credentials).
6. **De-hack (if H18 shipped):** collapse WeatherBot's `fatal`-marker workaround onto the hub's
   first-class fatal outcome at the two sites named in H18.
7. **Verify on WeatherBot:** re-run its suite against the repinned hub; confirm H02/H01 regression
   coverage now exercises the hub fixes end-to-end.

---

_Generated 2026-07-21 from the WeatherBot v2.1 audit + a live-source verification pass against hub
HEAD `50e8f09`. Bring this into `/gsd-new-milestone` here in the hub repo._
