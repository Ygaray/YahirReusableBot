# YahirReusableBot — Roadmap

## Milestone v0.1.0 — Initial extraction (DONE)

Imported from the WeatherBot v2.0 "Bot Module Extraction" milestone (Phases 22–28). The module
core, the standing import-hygiene suite, and the `EXTENSION-GUIDE` ship in the single clean
import commit tagged `v0.1.0`.

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | Initial import (module tree, pyproject, re-scoped import-hygiene suite, EXTENSION-GUIDE, GSD init) | done |

## Deferred Extension Points (future milestones)

Built under build-in-consumer-then-promote / rule of three when a consumer needs them.

| Phase (future) | Scope | Tracks |
|----------------|-------|--------|
| EXT-A | Durable `JobStore` impl + serialization contract (promote from a consumer that needs persistence) | EXT-01 |
| EXT-B | Second `Channel` adapter (Telegram / SMS / Slack) | EXT-02 |

## Backlog

Unsequenced parking lot. Source of record for every item below lives in `.planning/backlog/`:

- `HUB-HARDENING-REPORT-v0.1.2.md` — **the planning document.** 17 audit defects (H01–H17) +
  1 enhancement (H18), each with a fix direction verified against hub HEAD `50e8f09`, plus a
  consumer-impact triage. Supersedes the raw handoff for planning.
- `HUB-FINDINGS-HANDOFF.md` — evidence appendix: full failure scenario + evidence per finding.
- `PROMOTION-CANDIDATES.md` — new reusable mechanisms to pull up from consumers (not bugs).

Grouping below follows the report's §3 proposed sequencing: correctness-first, reachable-first,
then reusability hardening, cleanup last. **Test posture for all defect items: every fix ships
with a RED-first regression test** — several findings note the existing tests cover only decoy
cases, so the missing adversarial case must be added, not just a new happy path.

**Close-out is human-gated** (`ECOSYSTEM.md` §3): fixes + green gates are autonomous; the
`v0.1.2` tag cut, the `pyproject.toml` version bump, and the consumer repin are yours.

### Phase 999.1: Reachable reliability — H01, H02 (BACKLOG)

**Goal:** Close the two findings that are live and unmitigated in a real consumer today.
**Requirements:** TBD
**Plans:** 0 plans

- **H02** `reliability/retry.py:87` · high — `is_transient` matches only
  `(TimeoutException, ConnectError, ReadError)`, so `httpx.RemoteProtocolError` (server hangup
  mid-response) and `WriteError` fall through as non-transient: the two-burst retry never fires
  and the outcome is misclassified `internal_error` instead of `transient_exhausted`. **A routine
  network blip silently misses the briefing.** Fix direction: broaden to
  `(TimeoutException, NetworkError, RemoteProtocolError)` — *not* a blanket `TransportError`, so
  client-side `LocalProtocolError` stays non-retryable.
- **H01** `lifecycle/identity.py:149` · high — `b"-m" in argv[1:3] and proc_marker in argv[1:4]`
  both false-positives (marker as a positional arg → `reload` can SIGHUP an unrelated recycled
  PID) and false-negatives (interpreter flag before `-m` → live daemon reported not running).
  Fix direction: pin exact position `len(argv) >= 3 and argv[1] == b"-m" and argv[2] == proc_marker`.

**Why first:** no consumer-side workaround exists for either. WeatherBot's `reliability/retry.py`
is a byte-identical re-export shim of this hub's `is_transient`, so H02 is live there verbatim.

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.2: Latent runtime robustness — H03, H04, H05, H07, H08 (BACKLOG)

**Goal:** Close real hub bugs that need specific runtime conditions to bite.
**Requirements:** TBD
**Plans:** 0 plans

- **H03** `config/reload.py:150` · medium — PHASE-2 reconcile failure rolls back, logs, re-raises
  but never fires `on_rejected`, so the host's "config reload rejected" alert silently doesn't
  fire. Fix: call `_best_effort_hook(self._on_rejected, ...)` before re-raising, matching PHASE-1.
- **H04** `discord/gateway.py:273` · medium — no reconnect supervisor; a non-recoverable
  disconnect ends the thread, `is_alive()` stays False forever, every later interaction is dead
  until a human restart. Fix: bounded supervised reconnect loop, or expose liveness for the
  consumer park-loop. **Retry/backoff contract is an open design decision for this phase.**
- **H05** `discord/gateway.py:167` · medium — `summon_panel` sends+pins before deleting, catching
  only `discord.Forbidden`; a `NotFound`/`HTTPException` aborts remaining deletes → 2+ live pinned
  panels (both routable via static `custom_id`), or a fresh-but-unpinned panel at the 50-pin cap.
  Fix: delete-then-pin + per-item `try/except` on `HTTPException`/`NotFound`.
- **H07** `discord/gateway.py:244` · low — `stop()` TOCTOU: `run_coroutine_threadsafe` sits outside
  the `try`, so `RuntimeError("Event loop is closed")` escapes. Fix: move inside / catch it.
- **H08** `discord/selection.py:49` · low — `SelectedContext` re-read after an `await`; a Select
  tap during a fetch yields an embed whose data is location A but whose 📍 label is location B.
  Cosmetic. Fix: capture the value once pre-await, as the argless path already does.

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.3: Reusable public-surface footguns — H06, H09–H16 (BACKLOG)

**Goal:** Harden the reusable public surface against footguns that are unreachable in the current
consumer but will bite the next one. Pure reusability hardening — this is the hub's whole point.
**Requirements:** TBD
**Plans:** 0 plans

Matcher (`registry/match.py`) — **H06 and H13 must land together**, both are casefold-symmetry:
- **H06** `:61` · medium — arg sliced from the *un-folded* original using the *folded* keyword
  length; `casefold()` is not length-preserving (`ß`→`ss`, `ﬁ`→`fi`) so the slice misaligns.
- **H13** `:59` · low — `spec.name` compared raw against folded input: an empty name matches every
  input, and any uppercase in a registered name makes the command permanently unmatchable.

Retry callable (`reliability/retry.py`) — **H09 and H10 are the same `burst_size` coupling**:
- **H09** `:141` · low — `burst_spread_s / (burst_size - 1)` raises `ZeroDivisionError` when
  `burst_size == 1`; the early-return shields only the first retry.
- **H10** `:146` · low — standalone `two_burst_wait` fires its mid-pause at `attempt_number ==
  burst_size` (default 8) independent of the `stop` bound, so a direct caller desyncs the pause.

Panelkit (`discord/panelkit.py`):
- **H11** `:309` · low — `interaction_check` dereferences `interaction.user.bot`/`.id` with no None
  guard; `AttributeError` there is not covered by `View.on_error`, so the operator gate throws.
- **H12** `:479` · low — `marker` is required but unvalidated; `cid.startswith("")` is always True,
  so `marker=""` makes `is_owned_panel` claim every bot-authored pin → `summon_panel` deletes
  unrelated bot pins. One-line non-empty guard at construction.

Lifecycle (`lifecycle/identity.py`):
- **H14** `:83` · low — `write_pid_atomic` double-closes `fd` on the `os.replace` failure path; the
  fd integer can be reused between closes, silently closing an unrelated descriptor.
- **H15** `:162` · low — path-shaped `proc_marker` makes the documented non-Linux "degrade to True"
  return False, flipping the guard to the opposite of its stated portability behavior.

Scheduler (`scheduler/engine.py`):
- **H16** `:74` · low — `remove()` is non-idempotent (raises `JobLookupError`) while `register()`
  is forgiving. Either swallow-on-missing or document the raise as contract.

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.4: Cleanup + ReadyGate fatal outcome — H17, H18 (BACKLOG)

**Goal:** Fix public-surface drift and give consumers a first-class fatal outcome to de-hack against.
**Requirements:** TBD
**Plans:** 0 plans

- **H17** `discord/__init__.py:25` · cleanup — the package docstring advertises "the
  create-before-delete summon orchestration" and `gateway.py.__all__` lists `summon_panel`, but the
  package `__init__` never re-exports it, so `from yahir_reusable_bot.discord import summon_panel`
  raises `ImportError`. Fix: add it to the imports + `__all__`, or correct the docstring.
- **H18** `lifecycle/ready_gate.py:run` · **enhancement, not a defect** — `run(stop)` loops until
  ok-or-`stop`; a fatal probe result is only logged louder and re-probed forever, so consumers must
  overload the `stop` Event to break out. Return a distinct fatal outcome (enum / dedicated return)
  instead. **Consumer de-hack after ship+repin:** WeatherBot deletes its separate `fatal`
  `threading.Event` at `weatherbot/scheduler/wiring.py:_on_fail` and the gate-return exit-code
  check in `weatherbot/ops/daemon.py`.

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.5: PC-01 — log secret-redaction backstop promotion (BACKLOG)

**Goal:** Promote WeatherBot's app-local secret redactor into a generic hub mechanism.
**Requirements:** TBD
**Plans:** 0 plans

**Separate track — a promotion, not a fix.** WeatherBot ships this app-local in its Phase 30
(`HARD-SEC-01`, origin finding F12) to keep that phase cheap and avoid a mid-phase hub tag cut.

The hub should own a renderer-agnostic backstop that scrubs secrets from **all** rendered log
output — event fields *and* formatted tracebacks — independent of the structlog processor chain:
a `redact_secrets(text, patterns) -> text` core, a drop-in wrapper for a structlog
`PrintLoggerFactory` file target (WeatherBot's seam is the shared `_LiveStderr.write` choke point)
and/or a processor, plus a config-driven pattern list.

**Litmus:** the *mechanism* is fully generic; only the *pattern* (`appid=<key>` for OpenWeather) is
domain-specific. Hub owns mechanism + pattern-registration API; the consumer registers its patterns.
Landing it replaces WeatherBot's app-local copy with a hub import.

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

## Notes

- The first consumer is **WeatherBot**, depending on this module via a uv git dependency
  tag-pinned for deploy (`tag = "v0.1.0"`, reproducible `uv.lock`).
- A real GitHub remote for this repo is a deploy prerequisite for pinning from a host
  (the local `file://` git URL is sufficient for development / Gate-1 verification only).
